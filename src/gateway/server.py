import atexit
import json
import logging
import os
import signal
import socket
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import psutil
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import log
from src.utils.security import SecurityManager
from src.memory.usage_store import UsageStore

# ============================================
# INITIALIZATION (Load Env & Settings)
# ============================================

def load_system_env():
    SecurityManager.initialize()
    settings_path = Path("workspace/settings.json")
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = SecurityManager.decrypt_dict(json.load(f))
                for k, v in data.items(): os.environ[k] = str(v)
        except: pass
    
    env_p = Path(".env")
    if env_p.exists():
        for line in env_p.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_system_env()

# Suppress uvicorn logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

# ============================================
# SINGLE INSTANCE ENFORCEMENT
# ============================================

def check_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except OSError:
            return False

def write_pid_lock(port: int) -> Path:
    if os.environ.get("KYURAA_TEST_MODE") == "1":
        return Path(f'.test-lock-{port}')
    lock_file = Path(f'.kyuraa-lock-{port}')
    if lock_file.exists():
        try:
            old_pid = int(lock_file.read_text().strip())
            if psutil.pid_exists(old_pid):
                log("gateway", f"Closing old instance (PID {old_pid})")
                try:
                    p = psutil.Process(old_pid)
                    p.terminate()
                    p.wait(timeout=3)
                except:
                    try: p.kill() 
                    except: pass
                lock_file.unlink(missing_ok=True)
        except:
            lock_file.unlink(missing_ok=True)
    lock_file.write_text(str(os.getpid()))
    atexit.register(lambda: lock_file.unlink(missing_ok=True))
    return lock_file

class GatewayServer:
    def __init__(self, host: str = "localhost", port: int = 8766):
        self._host = host
        self._port = port
        if os.environ.get("KYURAA_TEST_MODE") != "1" and not check_port_available(self._host, self._port):
            log("error", f"Port {self._port} already in use")
            sys.exit(1)
        write_pid_lock(self._port)

        self._app = FastAPI(title="Agent Gateway")
        self._active_sessions: dict[str, dict] = {}
        self._agents: dict[str, Any] = {}
        self._system_agent: Any = None
        self._running = False
        self._session_buffers: dict[str, list[str]] = {}
        self._usage_store = UsageStore()
        self._upload_dir = Path("workspace/tempat_baca/uploaded_pdfs")
        self._upload_dir.mkdir(parents=True, exist_ok=True)

        self._app.mount("/static", StaticFiles(directory="src/gateway/static"), name="static")
        self._setup_routes()

        # Show banner even when running via uvicorn
        from src.agent.agent_loop import AgentLoop
        sa = AgentLoop(session_id="__system__")
        print_banner(len(sa._skill_manager.available_skills), self._port)

    def _verify_token(self, request):
        token = request.headers.get("X-API-Key") or request.query_params.get("token")
        if not token or token != SecurityManager.get_gateway_token():
            raise HTTPException(status_code=401, detail="❌ Akses dilarang: Token tidak valid.")

    def _setup_routes(self):
        from src.gateway.routers import settings_router, upload_router, session_router, stats_router
        self._app.include_router(settings_router.router)
        self._app.include_router(upload_router.router)
        self._app.include_router(session_router.router)
        self._app.include_router(stats_router.router)

        @self._app.get("/")
        async def get_index():
            return FileResponse("src/gateway/static/index.html")

        @self._app.get("/settings-page")
        async def get_settings_page():
            return FileResponse("src/gateway/static/settings.html")

        @self._app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            token = websocket.query_params.get("token")
            if token != SecurityManager.get_gateway_token():
                await websocket.accept() 
                await websocket.close(code=4001)
                return

            await websocket.accept()
            self._session_buffers[session_id] = []
            try:
                agent = self._create_agent(session_id)
                self._active_sessions[session_id] = {"websocket": websocket}
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    if message.get("type") == "message":
                        user_input = message.get("content", "")
                        file_context = message.get("file_context")
                        self._session_buffers[session_id] = []
                        captured_usage = None
                        captured_finish_reason = None
                        res = None
                        for item in agent.run_stream(user_input, metadata=file_context):
                            token_val, usage, finish_reason = item
                            if usage: captured_usage = usage
                            if finish_reason: captured_finish_reason = finish_reason
                            if token_val == "__SYSTEM_RECONNECT__": continue
                            await websocket.send_json({"type": "token", "content": token_val})
                            self._session_buffers[session_id].append(token_val)
                            res = item

                        # Log usage Safely
                        it, ot = 0, 0
                        if captured_usage:
                            it = getattr(captured_usage, "prompt_tokens", captured_usage.get("prompt_tokens", 0) if isinstance(captured_usage, dict) else 0)
                            ot = getattr(captured_usage, "completion_tokens", captured_usage.get("completion_tokens", 0) if isinstance(captured_usage, dict) else 0)
                        if it == 0: it = max(1, (len(user_input) + (len(file_context.get("text", "")) if file_context else 0)) // 4)
                        if ot == 0: ot = max(1, len("".join(self._session_buffers.get(session_id, []))) // 4)

                        self._usage_store.log_usage(session_id, os.environ.get("ACTIVE_PROVIDER", "google"), agent.model_name, it, ot, "success")

                        # --- HITL TOOL APPROVAL LOGIC ---
                        final_result = agent.run(user_input, metadata=file_context)
                        tool_calls = final_result.get("tool_calls", [])
                        tool_results = []

                        for call in tool_calls:
                            name = call["tool_name"]
                            params = call["params"]
                            
                            if agent._tool_registry.is_sensitive(name):
                                await websocket.send_json({
                                    "type": "approval_request",
                                    "tool": name,
                                    "params": params
                                })
                                try:
                                    resp_raw = await websocket.receive_text()
                                    resp = json.loads(resp_raw)
                                    if resp.get("type") == "approval_response" and resp.get("approved"):
                                        exec_result = agent.execute_tool(name, **params)
                                    else:
                                        exec_result = {"success": False, "error": "Aksi ditolak oleh pengguna."}
                                except Exception as e:
                                    exec_result = {"success": False, "error": f"Error approval: {e}"}
                            else:
                                exec_result = agent.execute_tool(name, **params)
                            
                            tool_results.append({"tool": name, "params": params, "result": exec_result})

                        await websocket.send_json({
                            "type": "done", 
                            "usage": {"input_tokens": it, "output_tokens": ot},
                            "tool_results": tool_results
                        })
                    elif message.get("type") == "reset":
                        agent.clear_history()
                        self._session_buffers[session_id] = []
                        await websocket.send_json({"type": "done", "session_id": session_id})
            except WebSocketDisconnect:
                self._cleanup_session(session_id)
            except Exception as e:
                log("error", f"WS error: {e}")
                self._cleanup_session(session_id)

        @self._app.get("/health")
        async def health():
            return {"status": "ok", "sessions": len(self._active_sessions)}

        @self._app.post("/sessions/{session_id}/connected")
        async def create_connected_session(session_id: str, request: Request):
            self._verify_token(request)
            from src.memory.session_store import SessionStore
            store = SessionStore()
            messages = store.get_session_messages(session_id)
            if not messages: raise HTTPException(404, "Sesi tidak ditemukan")
            agent = self._get_system_agent()
            summary = agent._llm_client.summarize([{"role": m["role"], "content": m["content"]} for m in messages])
            new_id = f"s-{int(time.time()*1000)}-{uuid.uuid4().hex[:7]}"
            store.create_session(new_id)
            intro = f"Lanjutan sesi sebelumnya.\n\n**Ringkasan:**\n{summary}"
            store.add_message(new_id, "assistant", intro)
            return {"session_id": new_id, "summary": summary, "intro": intro}

        @self._app.delete("/sessions/{session_id}")
        async def delete_session(session_id: str, request: Request):
            self._verify_token(request)
            from src.memory.session_store import SessionStore
            store = SessionStore()
            messages = store.get_session_messages(session_id)
            for msg in messages:
                meta = msg.get("metadata")
                if meta and isinstance(meta, dict) and meta.get("file_id"):
                    fp = self._upload_dir / meta["file_id"]
                    if fp.exists(): fp.unlink()
            store.delete_session(session_id)
            self._cleanup_session(session_id)
            return {"success": True}

        @self._app.get("/skills")
        async def list_skills(request: Request):
            self._verify_token(request)
            return {"skills": self._get_system_agent()._skill_manager.list_skills_detail(), "active_skill": self._get_system_agent()._skill_manager.active_skill}

        @self._app.post("/skills/{skill_name}/activate")
        async def activate_skill(skill_name: str, request: Request):
            self._verify_token(request)
            self._get_system_agent()._skill_manager.activate(skill_name)
            for a in self._agents.values():
                try: a._skill_manager.activate(skill_name)
                except: pass
            return {"success": True}

        @self._app.post("/skills/deactivate")
        async def deactivate_skill(request: Request):
            self._verify_token(request)
            self._get_system_agent()._skill_manager.deactivate()
            for a in self._agents.values():
                try: a._skill_manager.deactivate()
                except: pass
            return {"success": True}

        @self._app.get("/tools")
        async def list_tools(request: Request):
            self._verify_token(request)
            return {"tools": self._get_system_agent()._tool_registry.list_tools_detail()}

        @self._app.post("/tools/{tool_name}/toggle")
        async def toggle_tool(tool_name: str, request: Request):
            self._verify_token(request)
            st = self._get_system_agent()._tool_registry.toggle(tool_name)
            for a in self._agents.values():
                try: a._tool_registry._state[tool_name] = st
                except: pass
            return {"success": True, "enabled": st}

    def _get_system_agent(self) -> Any:
        if self._system_agent is None:
            from src.agent.agent_loop import AgentLoop
            self._system_agent = AgentLoop(session_id="__system__")
        return self._system_agent

    def _create_agent(self, session_id: str) -> Any:
        if session_id == "__system__": return self._get_system_agent()
        if session_id not in self._agents:
            from src.agent.agent_loop import AgentLoop
            self._agents[session_id] = AgentLoop(session_id=session_id)
        return self._agents[session_id]

    def _cleanup_session(self, session_id: str):
        if session_id in self._active_sessions: del self._active_sessions[session_id]
        if session_id in self._agents: del self._agents[session_id]
        if session_id in self._session_buffers: del self._session_buffers[session_id]

    def run(self):
        self._running = True
        log("gateway", f"Server running on http://{self._host}:{self._port}")
        uvicorn.run(self._app, host=self._host, port=self._port, log_level="warning")

def print_banner(skill_count: int = 0, port: int = 8766):
    token = SecurityManager.get_gateway_token()
    banner = f"""
\033[96m
   __                        
  / /_____  __ _________ ____
 /  '_/ / / / / __/ _  / _  /
/_/\_\\_, / /_/ / /\_,_/\_,_/ 
     /___/  \033[90mv1.0.3\033[0m
\033[94m─────────────────────────────────────────────────────\033[0m
\033[90mSTATUS:\033[0m \033[92mONLINE\033[0m
\033[90mSKILLS:\033[0m \033[92m{skill_count} Active\033[0m
\033[90mURL   :\033[0m \033[96mhttp://127.0.0.1:{port}\033[0m
\033[90mTOKEN :\033[0m \033[93m{token}\033[0m
\033[94m─────────────────────────────────────────────────────\033[0m
"""
    print(banner)

def main():
    port = int(os.environ.get("GATEWAY_PORT", 8766))
    
    # Hitung skill secara ringan untuk banner awal
    skill_count = 0
    try:
        s_dir = Path("workspace/skills")
        if s_dir.exists():
            skill_count = len([d for d in s_dir.iterdir() if d.is_dir()])
    except:
        pass

    print_banner(skill_count, port)
    
    server = GatewayServer(port=port)
    # Background initialization of system agent
    from src.agent.agent_loop import AgentLoop
    sa = AgentLoop(session_id="__system__")
    
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    server.run()

if __name__ == "__main__":
    main()

if __name__ != "__main__":
    app = GatewayServer()._app
