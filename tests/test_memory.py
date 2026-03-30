import pytest
from pathlib import Path
import tempfile
import shutil

from src.memory.session_store import SessionStore
from src.memory.glossary_store import GlossaryStore


class TestSessionStore:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "sessions.db"
        self.store = SessionStore(self.db_path)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_session_and_add_message(self):
        self.store.create_session("test-session-1")
        result = self.store.add_message("test-session-1", "user", "Halo")
        assert result is True
        history = self.store.get_history("test-session-1")
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Halo"

    def test_get_history_returns_ordered_messages(self):
        self.store.create_session("test-session-2")
        self.store.add_message("test-session-2", "user", "Pesan 1")
        self.store.add_message("test-session-2", "assistant", "Balasan 1")
        self.store.add_message("test-session-2", "user", "Pesan 2")
        history = self.store.get_history("test-session-2")
        assert len(history) == 3
        assert history[0]["content"] == "Pesan 1"
        assert history[1]["content"] == "Balasan 1"
        assert history[2]["content"] == "Pesan 2"

    def test_get_history_with_limit(self):
        self.store.create_session("test-session-3")
        for i in range(5):
            self.store.add_message("test-session-3", "user", f"Pesan {i}")
        history = self.store.get_history("test-session-3", limit=3)
        assert len(history) == 3
        assert history[-1]["content"] == "Pesan 4"

    def test_list_sessions(self):
        self.store.create_session("session-a")
        self.store.create_session("session-b")
        sessions = self.store.list_sessions()
        session_ids = [s["session_id"] for s in sessions]
        assert "session-a" in session_ids
        assert "session-b" in session_ids


class TestGlossaryStore:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.glossary_path = Path(self.temp_dir) / "glossary.json"
        self.store = GlossaryStore(self.glossary_path)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_lookup_term(self):
        self.store.add_term("البحث", "penelitian", "akademik", "akademik")
        result = self.store.lookup("البحث")
        assert result is not None
        assert result[0]["indonesian"] == "penelitian"

    def test_lookup_reverse(self):
        self.store.add_term("البحث", "penelitian", "akademik", "akademik")
        result = self.store.lookup_reverse("penelitian")
        assert result is not None
        assert result[0]["arabic"] == "البحث"

    def test_get_all(self):
        self.store.add_term("البحث", "penelitian", "akademik", "akademik")
        self.store.add_term("المنهج", "metode", "akademik", "akademik")
        all_data = self.store.get_all()
        assert "terms" in all_data
        assert len(all_data["terms"]) == 2

    def test_glossary_file_created_on_disk(self):
        self.store.add_term("البحث", "penelitian", "akademik", "akademik")
        assert self.glossary_path.exists()
        content = self.glossary_path.read_text(encoding="utf-8")
        assert "البحث" in content
        assert "penelitian" in content

    def test_export_to_text(self):
        self.store.add_term("البحث", "penelitian", "akademik", "akademik")
        text = self.store.export_to_text()
        assert "Glosarium" in text
        assert "البحث" in text
        assert "penelitian" in text
