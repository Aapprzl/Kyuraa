from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from src.memory.session_store import SessionStore
from src.utils.logger import log
from src.utils.security import SecurityManager

router = APIRouter()
store = SessionStore()

def verify_token(request: Request):
    cli_token = request.headers.get("X-API-Key") or request.query_params.get("token")
    srv_token = SecurityManager.get_gateway_token()
    if not cli_token or cli_token != srv_token:
        raise HTTPException(status_code=401, detail="❌ Akses dilarang: Token tidak valid.")

@router.get("/sessions")
async def list_sessions(request: Request):
    verify_token(request)
    sessions = store.list_sessions()
    return {"sessions": sessions}

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, request: Request):
    verify_token(request)
    sessions = store.list_sessions()
    session = next((s for s in sessions if s["session_id"] == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = store.get_session_messages(session_id)
    return {
        "session_id": session_id,
        "name": session.get("name"),
        "messages": messages
    }

@router.delete("/sessions/{session_id}/messages/last")
async def delete_last_message(session_id: str, request: Request):
    verify_token(request)
    deleted = store.delete_last_user_message(session_id)
    if deleted:
        return {"success": True}
    raise HTTPException(status_code=404, detail="No user message found to delete")

@router.patch("/sessions/{session_id}/name")
async def update_session_name(session_id: str, body: dict, request: Request):
    verify_token(request)
    new_name = body.get("name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    store.update_session_name(session_id, new_name)
    return {"success": True}

@router.delete("/sessions/cleanup")
async def cleanup_empty_sessions(request: Request):
    verify_token(request)
    import sqlite3
    db_path = Path("workspace/memory/sessions.db")
    if db_path.exists():
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE session_id NOT IN (SELECT DISTINCT session_id FROM messages)")
            deleted = cursor.rowcount
            conn.commit()
            return {"deleted": deleted}
    return {"deleted": 0}

@router.get("/files")
async def list_files(request: Request):
    verify_token(request)
    output_dir = Path("workspace/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    files = [f.name for f in output_dir.iterdir() if f.is_file()]
    return {"files": files}
