import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from src.utils.logger import log

class UsageStore:
    def __init__(self, db_path: str | Path = "workspace/memory/usage.db"):
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
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    provider TEXT,
                    model TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    latency REAL DEFAULT 0,
                    status TEXT DEFAULT 'success'
                )
            """)
            conn.commit()

    def log_usage(self, session_id: str, provider: str, model: str, input_tokens: int, output_tokens: int, latency: float = 0, status: str = "success"):
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO usage_logs 
                (timestamp, session_id, provider, model, input_tokens, output_tokens, latency, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (now, session_id, provider, model, input_tokens, output_tokens, latency, status)
            )
            conn.commit()
        log("memory", f"Usage logged — {input_tokens+output_tokens} tokens — model: {model}")

    def get_totals(self) -> dict:
        """Get global total usage."""
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output
                FROM usage_logs
                """
            ).fetchone()
        
        return {
            "total_requests": row["total_requests"] or 0,
            "input_tokens": row["total_input"] or 0,
            "output_tokens": row["total_output"] or 0,
            "total_tokens": (row["total_input"] or 0) + (row["total_output"] or 0)
        }

    def get_daily_usage(self, days: int = 7) -> list[dict]:
        """Get usage grouped by day for charts."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as requests,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens
                FROM usage_logs
                WHERE timestamp >= date('now', ?)
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp) ASC
                """,
                (f"-{days} days",)
            ).fetchall()
            return [dict(row) for row in rows] if rows else []

    def clear_by_models(self, models: list[str]) -> int:
        """Delete usage logs for specified models. Returns count of deleted rows."""
        with self._get_conn() as conn:
            placeholders = ','.join('?' * len(models))
            cursor = conn.execute(
                f"DELETE FROM usage_logs WHERE model IN ({placeholders})",
                models
            )
            conn.commit()
            return cursor.rowcount

    def get_by_model(self) -> list[dict]:
        """Get usage grouped by model for breakdown."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT 
                    model,
                    COUNT(*) as requests,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    SUM(input_tokens) + SUM(output_tokens) as total_tokens
                FROM usage_logs
                GROUP BY model
                ORDER BY total_tokens DESC
                """
            ).fetchall()
        return [dict(row) for row in rows] if rows else []
