import sqlite3
import json

db_path = "d:/PROJECT_APP/Kyuraa/workspace/memory/sessions.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Get the latest user message
row = conn.execute("SELECT role, content, metadata FROM messages WHERE role='user' ORDER BY id DESC LIMIT 1").fetchone()
from src.agent.prompt_builder import PromptBuilder

history = []
pb = PromptBuilder()
msgs = pb.build_messages(history, row["content"], current_metadata=json.loads(row["metadata"]))
print(msgs[-1])
