import atexit
import json
import logging
import os
import signal
import socket
import sys
from pathlib import Path
from typing import Any, Optional

import psutil

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import log

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Suppress uvicorn access logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


class SettingsSchema(BaseModel):
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
        old_pid = int(lock_file.read_text().strip())
        if psutil.pid_exists(old_pid):
            print(f"\n❌ Kyuraa sudah berjalan (PID: {old_pid})")
            print(f"   Tutup instance yang lama terlebih dahulu.\n")
            sys.exit(1)
        else:
            lock_file.unlink(missing_ok=True)

    lock_file.write_text(str(os.getpid()))
    atexit.register(lambda: lock_file.unlink(missing_ok=True))
    return lock_file


# Load env at module level so `app` below respects .env
def _load_env_early():
    settings_path = Path("workspace/settings.json")
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                for key, value in json.load(f).items():
                    os.environ[key] = value
        except Exception:
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


class GatewayServer:
    def __init__(self, host: str = "localhost", port: int = _DEFAULT_PORT):
        self._host = host
        self._port = port

        # Enforce single instance — check BEFORE creating app
        if not check_port_available(self._host, self._port):
            print(f"\n❌ ERROR: Port {self._port} sudah digunakan!")
            print(f"   Kemungkinan Kyuraa sudah berjalan di instance lain.")
            print(f"   Tutup instance yang lama terlebih dahulu.\n")
            sys.exit(1)
        write_pid_lock(self._port)

        self._app = FastAPI(title="Agent Gateway")
        self._active_sessions: dict[str, dict] = {}
        self._agents: dict[str, Any] = {}
        self._running = False
        self._session_buffers: dict[str, list[str]] = {}
        self._active_skill: str | None = None
        self._stats = {
            'total_requests': 0,
            'input_tokens': 0,
            'output_tokens': 0
        }

        self._setup_routes()

    def _setup_routes(self):
        @self._app.get("/info")
        async def info():
            return {
                "model": os.environ.get("AGENT_MODEL", "qwen/qwen3.6-plus:free"),
                "version": "1.0.0"
            }

        @self._app.get("/stats")
        async def get_stats():
            return {
                "total_requests": self._stats['total_requests'],
                "input_tokens": self._stats['input_tokens'],
                "output_tokens": self._stats['output_tokens'],
                "total_tokens": self._stats['input_tokens'] + self._stats['output_tokens'],
            }

        @self._app.get("/settings")
        async def get_settings():
            model = os.environ.get("AGENT_MODEL", "")
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
            masked_key = ""
            if api_key:
                masked_key = api_key[:6] + "********" if len(api_key) > 6 else "********"
            return {
                "model": model,
                "api_key": masked_key
            }

        @self._app.post("/settings/validate-and-save")
        async def save_settings(settings: SettingsSchema):
            # 1. Resolve Masked API Key
            api_key = settings.api_key
            if "********" in api_key:
                api_key = os.environ.get("OPENROUTER_API_KEY", "")

            # 2. Validate Connection
            from src.agent.llm_client import LLMClient
            
            try:
                # Temporary client for validation
                test_client = LLMClient(api_key=api_key, model=settings.model)
                # Simple test call
                test_client.chat(
                    system="You are a validator.",
                    messages=[{"role": "user", "content": "hi"}]
                )
            except Exception as e:
                err_msg = str(e).lower()
                log("error", f"Validation failed: {e}")
                if "api_key" in err_msg or "401" in err_msg or "unauthorized" in err_msg:
                    raise HTTPException(status_code=400, detail="❌ API Key tidak valid. Pastikan key dari OpenRouter sudah benar.")
                elif "model" in err_msg or "404" in err_msg:
                    raise HTTPException(status_code=400, detail="❌ Model tidak ditemukan. Cek ejaan nama model di openrouter.ai/models")
                elif "connection" in err_msg or "network" in err_msg or "timeout" in err_msg:
                    raise HTTPException(status_code=400, detail="❌ Tidak dapat terhubung ke server. Periksa koneksi internet.")
                else:
                    raise HTTPException(status_code=400, detail=f"❌ Terjadi kesalahan: {str(e)}")

            # 3. Save to settings.json
            settings_path = Path("workspace/settings.json")
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump({
                    "AGENT_MODEL": settings.model,
                    "OPENROUTER_API_KEY": api_key
                }, f, indent=4)

            # 4. Update os.environ
            os.environ["AGENT_MODEL"] = settings.model
            os.environ["OPENROUTER_API_KEY"] = api_key

            # 5. Reset Agents (force creation with new config)
            self._agents.clear()
            
            log("gateway", f"Settings updated — model: {settings.model}")
            return {"status": "ok", "message": "✅ Koneksi berhasil! Setting disimpan."}

        @self._app.get("/")
        async def index():
            return FileResponse("src/gateway/static/index.html")

        @self._app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            await websocket.accept()
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
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
                self._cleanup_session(session_id)

        @self._app.get("/health")
        async def health():
            return {
                "status": "ok",
                "sessions": len(self._active_sessions),
                "active_sessions": list(self._active_sessions.keys()),
            }

        @self._app.get("/sessions")
        async def list_sessions():
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
            result = store.delete_session(session_id)
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
        async def list_skills():
            agent = self._create_agent("__system__")
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
            agent = self._create_agent("__system__")
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
            agent = self._create_agent("__system__")
            agent._skill_manager.deactivate()
            self._active_skill = None
            log("gateway", f"Skill deactivated")
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
            agent = self._create_agent("__system__")
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
                version_match = desc.split("version", 1) if desc else []
                
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

    def _create_agent(self, session_id: str) -> Any:
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
\033[90m─────────────────────────────────────────────────────\033[0m
""".format(skill_count=skill_count, port=port)
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
