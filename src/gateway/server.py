import json
import os
import signal
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn


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
        @self._app.get("/")
        async def index():
            return FileResponse("src/gateway/static/index.html")

        @self._app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            await websocket.accept()
            self._session_buffers[session_id] = []

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

                        for token in agent.run_stream(user_input):
                            await websocket.send_json({
                                "type": "token",
                                "content": token,
                            })
                            self._session_buffers[session_id].append(token)

                        await websocket.send_json({
                            "type": "done",
                            "session_id": session_id,
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
                self._cleanup_session(session_id)
            except Exception as e:
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

        @self._app.get("/glossary")
        async def get_glossary():
            from src.memory.glossary_store import GlossaryStore
            store = GlossaryStore()
            return store.get_all()

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
        print(f"Gateway starting on http://{self._host}:{self._port}")
        print(f"WebSocket endpoint: ws://{self._host}:{self._port}/ws/{{session_id}}")
        print(f"Health check: http://{self._host}:{self._port}/health")

        uvicorn.run(self._app, host=self._host, port=self._port, log_level="info")


def main():
    from pathlib import Path
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

    port = int(os.environ.get("GATEWAY_PORT", 8765))
    host = os.environ.get("GATEWAY_HOST", "localhost")

    server = GatewayServer(host=host, port=port)

    def signal_handler(sig, frame):
        print("\nShutting down...")
        server._running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.run()


if __name__ == "__main__":
    main()


app = GatewayServer()._app
