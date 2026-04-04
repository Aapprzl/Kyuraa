import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Optional

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


class GatewayServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self._host = host
        self._port = port
        self._app = FastAPI(title="Agent Gateway")
        self._active_sessions: dict[str, dict] = {}
        self._agents: dict[str, Any] = {}
        self._running = False
        self._session_buffers: dict[str, list[str]] = {}

        self._setup_routes()

    def _setup_routes(self):
        @self._app.get("/info")
        async def info():
            return {
                "model": os.environ.get("AGENT_MODEL", "unknown"),
                "version": "1.0.0"
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

                        input_tokens = captured_usage.prompt_tokens if captured_usage else 0
                        output_tokens = captured_usage.completion_tokens if captured_usage else 0
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
            return {"sessions": sessions}

        @self._app.delete("/session/{session_id}")
        async def delete_session(session_id: str):
            from src.memory.session_store import SessionStore
            store = SessionStore()
            result = store.clear_session(session_id)
            self._cleanup_session(session_id)
            return {"deleted": result, "session_id": session_id}

        @self._app.get("/files")
        async def list_files():
            output_dir = Path("workspace/output")
            output_dir.mkdir(parents=True, exist_ok=True)
            files = [f.name for f in output_dir.iterdir() if f.is_file()]
            return {"files": files}

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

    port = int(os.environ.get("GATEWAY_PORT", 8765))
    host = os.environ.get("GATEWAY_HOST", "localhost")

    server = GatewayServer(host=host, port=port)

    def signal_handler(sig, frame):
        log("gateway", "Shutting down...")
        server._running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.run()


if __name__ == "__main__":
    main()


app = GatewayServer()._app
