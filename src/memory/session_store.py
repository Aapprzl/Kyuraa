import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


from src.utils.logger import log

class SessionStore:
    def __init__(self, db_path: str | Path = "workspace/memory/sessions.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    timestamp DATETIME,
                    token_count INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            # Migrasi kolom tambahan (idempotent)
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN name TEXT")
            except Exception:
                pass  # Kolom sudah ada
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN timestamp TEXT")
            except Exception:
                pass  # Kolom sudah ada
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN metadata TEXT")
            except Exception:
                pass  # Kolom sudah ada
            conn.commit()

    def create_session(self, session_id: str) -> dict:
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, created_at, updated_at) VALUES (?, ?, ?)",
                (session_id, now, now)
            )
            conn.commit()
        log("memory", f"New session created: {session_id}")
        return {"session_id": session_id, "created_at": now, "updated_at": now}

    def add_message(self, session_id: str, role: str, content: str, token_count: int | None = None, metadata: dict | None = None) -> bool:
        if role not in ("user", "assistant"):
            return False

        now = datetime.now().isoformat()
        meta_json = json.dumps(metadata) if metadata else None
        
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata, timestamp, token_count) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, role, content, meta_json, now, token_count)
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )
            
            if role == "user":
                row = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'user'",
                    (session_id,)
                ).fetchone()
                if row and row[0] == 1:
                    name = content[:50].strip()
                    conn.execute(
                        "UPDATE sessions SET name = ?, updated_at = ? WHERE session_id = ?",
                        (name, now, session_id)
                    )
            
            conn.commit()
        
        log("memory", f"Message saved — session: {session_id}")
        return True

    def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, role, content, metadata, timestamp, token_count FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit)
            ).fetchall()
            
        result = []
        for row in reversed(rows):
            d = dict(row)
            if d.get("metadata"):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    d["metadata"] = None
            result.append(d)
        return result

    def clear_session(self, session_id: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        return True

    def list_sessions(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT s.session_id, s.name, s.created_at, s.updated_at, COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
                """
            ).fetchall()
        result = []
        for row in rows:
            try:
                result.append({
                    "session_id": row["session_id"],
                    "name": row["name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": row["message_count"]
                })
            except Exception:
                continue
        return result

    def get_session_messages(self, session_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT role, content, metadata, timestamp FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,)
            ).fetchall()
        
        result = []
        for row in rows:
            d = dict(row)
            if d.get("metadata"):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    d["metadata"] = None
            result.append(d)
        return result

    def update_session_name(self, session_id: str, name: str) -> bool:
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE sessions SET name = ?, updated_at = ? WHERE session_id = ?",
                (name, now, session_id)
            )
            conn.commit()
        return True

    def delete_session(self, session_id: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        return True

    def delete_last_user_message(self, session_id: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM messages WHERE session_id = ? AND role = 'user' ORDER BY id DESC LIMIT 1",
                (session_id,)
            ).fetchone()
            
            if row:
                message_id = row["id"]
                conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
                conn.commit()
                log("memory", f"Deleted last user message (id: {message_id}) in session: {session_id}")
                return True
        return False

    def auto_name_session(self, session_id: str) -> str | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT content FROM messages WHERE session_id = ? AND role = 'user' ORDER BY id ASC LIMIT 1",
                (session_id,)
            ).fetchone()
        if row:
            name = row[0][:50].strip()
            self.update_session_name(session_id, name)
            return name
        return None

    def remove_file_metadata(self, file_id: str) -> bool:
        """Menandai metadata file sebagai 'deleted' di database."""
        with self._get_conn() as conn:
            # Ambil semua pesan yang merujuk file_id ini
            pattern = f'%"{file_id}"%'
            rows = conn.execute(
                "SELECT id, metadata FROM messages WHERE metadata LIKE ?",
                (pattern,)
            ).fetchall()
            
            for row in rows:
                try:
                    meta = json.loads(row["metadata"])
                    if meta.get("file_id") == file_id:
                        meta["deleted"] = True
                        # Jangan hapus filename agar UI bisa menampilkan nama file yang pernah ada
                        conn.execute(
                            "UPDATE messages SET metadata = ? WHERE id = ?",
                            (json.dumps(meta), row["id"])
                        )
                except Exception as e:
                    log("error", f"Failed to update metadata during deletion: {e}")
            
            conn.commit()
        log("memory", f"Marked metadata as deleted for file: {file_id}")
        return True
