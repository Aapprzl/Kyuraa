import atexit
import json
import logging
import os
import signal
import socket
import sys
from pathlib import Path
from typing import Any

import psutil

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import log
from src.utils.security import SecurityManager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Suppress uvicorn access logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


class SettingsSchema(BaseModel):
    provider: str  # 'openrouter' or 'google'
    model: str
    api_key: str


class SkillActivateSchema(BaseModel):
    skill_name: str


# ============================================
# SINGLE INSTANCE ENFORCEMENT
# ============================================

def check_port_available(host: str, port: int) -> bool:
    """Try to bind a port; return True if available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except OSError:
            return False


def write_pid_lock(port: int) -> Path:
    lock_file = Path(f'.kyuraa-lock-{port}')
    if lock_file.exists():
        try:
            old_pid = int(lock_file.read_text().strip())
            if psutil.pid_exists(old_pid):
                print(f"\n⚠️  Kyuraa sudah berjalan (PID: {old_pid})")
                choice = input("   Tutup paksa instance lama dan mulai baru? [Y/n]: ").strip().lower()
                
                if choice == 'y' or choice == '':
                    print(f"   Menutup PID {old_pid}...")
                    try:
                        p = psutil.Process(old_pid)
                        p.terminate()
                        p.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        try: p.kill() 
                        except: pass
                    lock_file.unlink(missing_ok=True)
                    log("gateway", f"Forced termination of old instance (PID {old_pid})")
                else:
                    print("   Dibatalkan. Silakan gunakan instance yang sudah ada.\n")
                    sys.exit(0)
            else:
                # PID tidak ada lagi — lock file basi, hapus dan lanjutkan
                lock_file.unlink(missing_ok=True)
                log("warn", f"Stale lock file dihapus (PID {old_pid} sudah tidak ada)")
        except (ValueError, OSError):
            # File corrupt atau tidak bisa dibaca → hapus saja
            lock_file.unlink(missing_ok=True)

    lock_file.write_text(str(os.getpid()))
    atexit.register(lambda: lock_file.unlink(missing_ok=True))
    return lock_file


# Load env at module level so `app` below respects .env
def _load_env_early():
    SecurityManager.initialize()  # Inisialisasi kunci master & gateway token
    
    settings_path = Path("workspace/settings.json")
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Dekripsi data sensitif (API Keys) sebelum dipasang ke os.environ
                data = SecurityManager.decrypt_dict(data)
                for key, value in data.items():
                    os.environ[key] = str(value)
        except Exception as e:
            log("error", f"Gagal memuat settings terenkripsi: {e}")
            pass
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env_early()
_DEFAULT_PORT = int(os.environ.get("GATEWAY_PORT", "8766"))


def _purge_old_sessions(days: int = 30) -> int:
    """Hapus session dan message yang lebih tua dari `days` hari. Dipanggil saat startup."""
    import sqlite3
    from datetime import datetime, timedelta
    db_path = Path("workspace/memory/sessions.db")
    if not db_path.exists():
        return 0
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "DELETE FROM messages WHERE session_id IN "
                "(SELECT session_id FROM sessions WHERE updated_at < ?)",
                (cutoff,)
            )
            cursor = conn.execute(
                "DELETE FROM sessions WHERE updated_at < ?", (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted
    except Exception as e:
        log("warn", f"Session purge error: {e}")
        return 0


class GatewayServer:
    def __init__(self, host: str = "localhost", port: int = _DEFAULT_PORT):
        self._host = host
        self._port = port

        # Enforce single instance — check BEFORE creating app
        if not check_port_available(self._host, self._port):
            print(f"\n❌ ERROR: Port {self._port} sudah digunakan!")
            print("   Kemungkinan Kyuraa sudah berjalan di instance lain.")
            print("   Tutup instance yang lama terlebih dahulu.\n")
            sys.exit(1)
        write_pid_lock(self._port)

        self._app = FastAPI(title="Agent Gateway")
        self._active_sessions: dict[str, dict] = {}
        self._agents: dict[str, Any] = {}
        self._system_agent: Any = None  # Agent khusus untuk endpoint non-chat (skills, dll)
        self._running = False
        self._session_buffers: dict[str, list[str]] = {}
        self._active_skill: str | None = None
        self._stats = {
            'total_requests': 0,
            'input_tokens': 0,
            'output_tokens': 0
        }

        self._setup_routes()

    def _verify_token(self, request):
        """Validasi token gateway dari header atau query param."""
        # Jika request adalah query (untuk WS), token ada di url params
        cli_token = request.headers.get("X-API-Key") or request.query_params.get("token")
        srv_token = SecurityManager.get_gateway_token()
        
        if not cli_token or cli_token != srv_token:
            raise HTTPException(status_code=401, detail="❌ Akses dilarang: Token tidak valid.")

    def _setup_routes(self):
        @self._app.get("/info")
        async def info():
            # Try to load from settings.json first to reflect manual edits
            settings_path = Path("workspace/settings.json")
            model = ""
            active = ""

            if settings_path.exists():
                try:
                    with open(settings_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        active = data.get("ACTIVE_PROVIDER", "openrouter")
                        if active == "google":
                            model = data.get("GOOGLE_MODEL", "")
                        else:
                            model = data.get("OPENROUTER_MODEL") or data.get("AGENT_MODEL", "")
                except Exception:
                    pass

            # Fallback to environment variables if file read failed or missing values
            if not active:
                active = os.environ.get("ACTIVE_PROVIDER", "openrouter")
            if not model:
                if active == "google":
                    model = os.environ.get("GOOGLE_MODEL", "")
                else:
                    model = os.environ.get("OPENROUTER_MODEL") or os.environ.get("AGENT_MODEL", "")

            return {
                "model": model or "Unknown",
                "provider": active,
                "version": "1.0.0"
            }

        @self._app.get("/stats")
        async def get_stats(request: Request):
            self._verify_token(request)
            return {
                "total_requests": self._stats['total_requests'],
                "input_tokens": self._stats['input_tokens'],
                "output_tokens": self._stats['output_tokens'],
                "total_tokens": self._stats['input_tokens'] + self._stats['output_tokens'],
            }

        @self._app.get("/settings")
        async def get_settings(request: Request):
            self._verify_token(request)
            # OpenRouter
            or_model = os.environ.get("OPENROUTER_MODEL") or os.environ.get("AGENT_MODEL", "")
            or_key = os.environ.get("OPENROUTER_API_KEY", "")

            # Google
            google_model = os.environ.get("GOOGLE_MODEL", "")
            google_key = os.environ.get("GOOGLE_API_KEY", "")

            # Active
            active = os.environ.get("ACTIVE_PROVIDER", "openrouter")

            def mask(key):
                return key[:6] + "********" if len(key) > 6 else "********" if key else ""

            return {
                "openrouter": {
                    "model": or_model,
                    "api_key": mask(or_key)
                },
                "google": {
                    "model": google_model,
                    "api_key": mask(google_key)
                },
                "active_provider": active
            }

        @self._app.post("/settings/validate-and-save")
        async def save_settings(settings: SettingsSchema, request: Request):
            self._verify_token(request)
            # 1. Resolve Masked API Key & Determine Prefix
            provider = settings.provider.lower()
            api_key = settings.api_key

            key_env = "OPENROUTER_API_KEY" if provider == "openrouter" else "GOOGLE_API_KEY"
            model_env = "OPENROUTER_MODEL" if provider == "openrouter" else "GOOGLE_MODEL"

            if "********" in api_key:
                api_key = os.environ.get(key_env, "")

            # 2. Validate Connection
            from src.agent.llm_client import LLMClient

            try:
                # Determine model name and URL for validation
                is_google = (provider == "google")
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai/" if is_google else "https://openrouter.ai/api/v1"

                # Correct model name for Google validation (strip google/ and :free etc)
                valid_model = settings.model
                if is_google:
                    valid_model = valid_model.replace("google/", "").split(":")[0]

                test_client = LLMClient(api_key=api_key, model=valid_model)
                # Overwrite base_url for validation
                test_client._client.base_url = base_url

                # Simple test call
                test_client.chat(
                    system="You are a validator.",
                    messages=[{"role": "user", "content": "hi"}]
                )
            except Exception as e:
                err_msg = str(e).lower()
                log("error", f"Validation failed for {provider}: {e}")
                if "api_key" in err_msg or "401" in err_msg or "unauthorized" in err_msg:
                    raise HTTPException(status_code=400, detail=f"❌ API Key {provider} tidak valid.")
                elif "model" in err_msg or "404" in err_msg:
                    raise HTTPException(status_code=400, detail=f"❌ Model {settings.model} tidak ditemukan di {provider}.")
                else:
                    raise HTTPException(status_code=400, detail=f"❌ Kesalahan {provider}: {str(e)}")

            # 3. Load existing settings to merge
            settings_path = Path("workspace/settings.json")
            current_settings = {}
            if settings_path.exists():
                try:
                    with open(settings_path, "r", encoding="utf-8") as f:
                        current_settings = json.load(f)
                except Exception:
                    log("warn", "settings.json corrupt atau tidak bisa dibaca, akan di-overwrite")

            # 4. Update settings & Encrypt
            if provider == "openrouter":
                current_settings["OPENROUTER_API_KEY"] = api_key
                current_settings["OPENROUTER_MODEL"] = settings.model
                current_settings["ACTIVE_PROVIDER"] = "openrouter"
            else:
                current_settings["GOOGLE_API_KEY"] = api_key
                current_settings["GOOGLE_MODEL"] = settings.model
                current_settings["ACTIVE_PROVIDER"] = "google"

            # Sync AGENT_MODEL
            current_settings["AGENT_MODEL"] = settings.model
            
            # Enkripsi sebelum tulis ke disk
            encrypted_settings = SecurityManager.encrypt_dict(current_settings)

            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(encrypted_settings, f, indent=4)

            # 5. Update os.environ
            os.environ[key_env] = api_key
            os.environ[model_env] = settings.model
            os.environ["ACTIVE_PROVIDER"] = provider
            os.environ["AGENT_MODEL"] = settings.model

            # 6. Reset Agents (termasuk system agent agar reload config)
            self._agents.clear()
            self._system_agent = None

            log("gateway", f"Settings updated for {provider} — model: {settings.model}")
            return {"status": "ok", "message": f"✅ Koneksi {provider} berhasil! Setting disimpan."}

        @self._app.get("/")
        async def index():
            return FileResponse("src/gateway/static/index.html")

        @self._app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            token = websocket.query_params.get("token")
            expected = SecurityManager.get_gateway_token()
            
            if token != expected:
                log("ws", f"⚠️  Autentikasi WebSocket DITOLAK — session: {session_id}")
                log("ws", f"   Diterima: '{token}'")
                log("ws", f"   Diharapkan: '{expected}'")
                await websocket.accept() # Terima dulu lalu tutup agar browser melihat kodenya
                await websocket.close(code=4001)
                return

            await websocket.accept()
            log("ws", f"✅ Client tersambung — session: {session_id}")
            self._session_buffers[session_id] = []
            log("ws", f"Client connected — session: {session_id}")

            try:
                agent = self._create_agent(session_id)
                self._active_sessions[session_id] = {"websocket": websocket}

                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    msg_type = message.get("type", "")

                    if msg_type == "message":
                        user_input = message.get("content", "")
                        self._session_buffers[session_id] = []

                        captured_usage = None
                        for item in agent.run_stream(user_input):
                            token = item[0] if isinstance(item, tuple) else item
                            usage = item[1] if isinstance(item, tuple) and len(item) > 1 else None
                            if usage:
                                captured_usage = usage
                            await websocket.send_json({
                                "type": "token",
                                "content": token,
                            })
                            self._session_buffers[session_id].append(token)

                        if captured_usage:
                            input_tokens = captured_usage.prompt_tokens if hasattr(captured_usage, "prompt_tokens") else captured_usage.get("prompt_tokens", 0)
                            output_tokens = captured_usage.completion_tokens if hasattr(captured_usage, "completion_tokens") else captured_usage.get("completion_tokens", 0)
                        else:
                            input_tokens = max(1, len(user_input) // 4)
                            output_tokens = max(1, len("".join(self._session_buffers.get(session_id, []))) // 4)

                        self._stats['total_requests'] += 1
                        self._stats['input_tokens'] += input_tokens
                        self._stats['output_tokens'] += output_tokens

                        await websocket.send_json({
                            "type": "done",
                            "session_id": session_id,
                            "usage": {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                            },
                        })

                    elif msg_type == "reset":
                        agent.clear_history()
                        self._session_buffers[session_id] = []
                        await websocket.send_json({
                            "type": "done",
                            "session_id": session_id,
                            "message": "Session reset",
                        })

                    elif msg_type == "save":
                        filename = message.get("filename", "output.txt")
                        content = "".join(self._session_buffers.get(session_id, []))
                        saved_path = agent.save_translation(filename, content)
                        await websocket.send_json({
                            "type": "file_saved",
                            "path": saved_path,
                        })

                    elif msg_type == "clear":
                        agent.clear_history()
                        self._session_buffers[session_id] = []
                        await websocket.send_json({"type": "done", "session_id": session_id})

            except WebSocketDisconnect:
                log("ws", f"Client disconnected — session: {session_id}")
                self._cleanup_session(session_id)
            except Exception as e:
                log("error", f"WebSocket error: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                    })
                except Exception:
                    pass  # WS mungkin sudah tutup
                self._cleanup_session(session_id)

        @self._app.get("/health")
        async def health():
            return {
                "status": "ok",
                "sessions": len(self._active_sessions),
                "active_sessions": list(self._active_sessions.keys()),
            }

        @self._app.get("/sessions")
        async def list_sessions(request: Request):
            self._verify_token(request)
            from src.memory.session_store import SessionStore
            store = SessionStore()
            sessions = store.list_sessions()
            log("gateway", f"Listed sessions: {len(sessions)}")
            return {"sessions": sessions}

        @self._app.delete("/sessions/cleanup")
        async def cleanup_empty_sessions():
            import sqlite3
            from pathlib import Path
            db_path = Path("workspace/memory/sessions.db")
            if db_path.exists():
                with sqlite3.connect(str(db_path)) as conn:
                    cursor = conn.execute("""
                        DELETE FROM sessions
                        WHERE session_id NOT IN (
                            SELECT DISTINCT session_id FROM messages
                        )
                    """)
                    deleted = cursor.rowcount
                    conn.commit()
                    log("gateway", f"Cleaned up {deleted} empty sessions")
                    return {"deleted": deleted}
            return {"deleted": 0}

        @self._app.get("/sessions/{session_id}/messages")
        async def get_session_messages(session_id: str):
            from src.memory.session_store import SessionStore
            store = SessionStore()
            sessions = store.list_sessions()
            session = next((s for s in sessions if s["session_id"] == session_id), None)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            messages = store.get_session_messages(session_id)
            log("gateway", f"Retrieved messages for session: {session_id}")
            return {
                "session_id": session_id,
                "name": session.get("name"),
                "messages": messages
            }

        @self._app.delete("/sessions/{session_id}")
        async def delete_session(session_id: str):
            from src.memory.session_store import SessionStore
            store = SessionStore()
            store.delete_session(session_id)
            self._cleanup_session(session_id)
            log("gateway", f"Deleted session: {session_id}")
            return {"success": True}

        @self._app.patch("/sessions/{session_id}/name")
        async def update_session_name(session_id: str, body: dict):
            from src.memory.session_store import SessionStore
            store = SessionStore()
            new_name = body.get("name", "").strip()
            if not new_name:
                raise HTTPException(status_code=400, detail="Name cannot be empty")
            store.update_session_name(session_id, new_name)
            log("gateway", f"Updated session name: {session_id} -> {new_name}")
            return {"success": True}

        @self._app.get("/files")
        async def list_files():
            output_dir = Path("workspace/output")
            output_dir.mkdir(parents=True, exist_ok=True)
            files = [f.name for f in output_dir.iterdir() if f.is_file()]
            return {"files": files}

        @self._app.get("/skills")
        async def list_skills(request: Request):
            self._verify_token(request)
            agent = self._get_system_agent()
            skills_data = []
            for name, info in agent._skill_manager.available_skills.items():
                desc = info.get("description", "")
                if isinstance(desc, list):
                    desc = " ".join(desc)
                skills_data.append({
                    "name": name,
                    "description": desc,
                    "is_active": self._active_skill == name,
                })
            return {
                "skills": skills_data,
                "active_skill": self._active_skill,
            }

        @self._app.post("/skills/activate")
        async def activate_skill(payload: SkillActivateSchema):
            agent = self._get_system_agent()
            skill_name = payload.skill_name.strip()
            try:
                agent._skill_manager.activate(skill_name)
                self._active_skill = skill_name
                log("gateway", f"Skill activated via API: {skill_name}")
                return {
                    "success": True,
                    "message": f"✅ Skill **{skill_name}** berhasil diaktifkan!",
                }
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))

        @self._app.post("/skills/deactivate")
        async def deactivate_skill():
            agent = self._get_system_agent()
            agent._skill_manager.deactivate()
            self._active_skill = None
            log("gateway", "Skill deactivated")
            return {"success": True}

        @self._app.get("/skills/template")
        async def get_skill_template():
            template_path = Path("workspace/skills/SKILL_TEMPLATE.md")
            if not template_path.exists():
                raise HTTPException(status_code=404, detail="Template file tidak ditemukan")
            return FileResponse(
                template_path,
                media_type="text/markdown",
                filename="SKILL_TEMPLATE.md",
                headers={"Content-Disposition": "attachment; filename=SKILL_TEMPLATE.md"}
            )

        @self._app.get("/skills/list-detail")
        async def list_skills_detail():
            agent = self._get_system_agent()
            skills_data = []
            for name, info in agent._skill_manager.available_skills.items():
                desc = info.get("description", "")
                if isinstance(desc, list):
                    desc = " ".join(desc)

                folder_path = Path(info.get("folder_path", ""))
                refs_count = 0
                refs_list = []
                references_dir = folder_path / "references"
                if references_dir.exists() and references_dir.is_dir():
                    refs_list = [f.name for f in references_dir.iterdir() if f.is_file()]
                    refs_count = len(refs_list)

                version = "1.0"

                skills_data.append({
                    "name": name,
                    "description": desc.replace("\n", " ").strip() if isinstance(desc, str) else str(desc),
                    "version": version,
                    "references_count": refs_count,
                    "references": refs_list,
                    "is_active": self._active_skill == name,
                })
            return {
                "skills": skills_data,
                "active_skill": self._active_skill,
                "total": len(skills_data),
            }

    def _get_system_agent(self) -> Any:
        """Dapatkan agent __system__ khusus untuk endpoint non-chat.
        Agent ini di-cache tapi tidak menyimpan history chat untuk mencegah memory leak.
        """
        if self._system_agent is None:
            from src.agent.agent_loop import AgentLoop
            self._system_agent = AgentLoop(session_id="__system__")
        return self._system_agent

    def _create_agent(self, session_id: str) -> Any:
        """Buat atau dapatkan agent untuk session chat. __system__ ditangani terpisah."""
        if session_id == "__system__":
            return self._get_system_agent()
        if session_id not in self._agents:
            from src.agent.agent_loop import AgentLoop
            self._agents[session_id] = AgentLoop(session_id=session_id)
        return self._agents[session_id]

    def _cleanup_session(self, session_id: str):
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
        if session_id in self._agents:
            del self._agents[session_id]
        if session_id in self._session_buffers:
            del self._session_buffers[session_id]

    def run(self):
        self._running = True
        log("gateway", f"Server running on http://{self._host}:{self._port}")
        uvicorn.run(self._app, host=self._host, port=self._port, log_level="warning")


def print_banner(skill_count: int = 0, port: int = _DEFAULT_PORT):
    banner = """
\033[96m██╗  ██╗██╗   ██╗██╗   ██╗██████╗  █████╗  █████╗
██║ ██╔╝╚██╗ ██╔╝██║   ██║██╔══██╗██╔══██╗██╔══██╗
█████╔╝  ╚████╔╝ ██║   ██║██████╔╝███████║███████║
██╔═██╗   ╚██╔╝  ██║   ██║██╔══██╗██╔══██║██╔══██║
██║  ██╗   ██║   ╚██████╔╝██║  ██║██║  ██║██║  ██║
╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
\033[0m
\033[96mv1.0.0 — Personal AI Agent\033[0m
\033[90mSkill aktif:\033[0m \033[92m{skill_count} skill terdeteksi\033[0m
\033[90mGateway:\033[0m \033[96mhttp://127.0.0.1:{port}\033[0m
\033[90mToken Akses:\033[0m \033[93m{token}\033[0m
\033[90m─────────────────────────────────────────────────────\033[0m
""".format(skill_count=skill_count, port=port, token=SecurityManager.get_gateway_token())
    print(banner)


def main():
    from pathlib import Path

    # Ensure project root is in sys.path for direct execution
    sys.path.append(str(Path(__file__).parent.parent.parent))

    # 1. Load from settings.json (Highest priority)
    settings_path = Path("workspace/settings.json")
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
                for key, value in settings.items():
                    os.environ[key] = value
            log("gateway", f"Loaded config from {settings_path}")
        except Exception as e:
            log("error", f"Error loading settings.json: {e}")

    # 2. Load from .env (Fallback)
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

    port = int(os.environ.get("GATEWAY_PORT", _DEFAULT_PORT))
    host = os.environ.get("GATEWAY_HOST", "localhost")

    server = GatewayServer(host=host, port=port)

    # Purge session lama saat startup
    purged = _purge_old_sessions(days=30)
    if purged > 0:
        log("gateway", f"Purged {purged} sessions older than 30 days")

    from src.agent.agent_loop import AgentLoop
    temp_agent = AgentLoop(session_id="__system__")
    skill_count = len(temp_agent._skill_manager.available_skills)
    print_banner(skill_count, port)

    def signal_handler(sig, frame):
        log("gateway", "Shutting down...")
        server._running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.run()


if __name__ == "__main__":
    main()


if __name__ != "__main__":
    app = GatewayServer()._app
