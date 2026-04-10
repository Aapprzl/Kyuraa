import sqlite3
import json

db_path = "d:/PROJECT_APP/Kyuraa/workspace/memory/sessions.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT role, content, metadata FROM messages ORDER BY id DESC LIMIT 5").fetchall()
for r in rows:
    meta = r["metadata"]
    if meta:
        meta_dict = json.loads(meta)
        text_len = len(meta_dict.get("text", "")) if meta_dict.get("text") else 0
        print(f"[{r['role']}] Content length: {len(r['content'])} | Metadata has file: {meta_dict.get('filename')} | Extracted text len: {text_len}")
    else:
        print(f"[{r['role']}] Content length: {len(r['content'])} | No metadata")
