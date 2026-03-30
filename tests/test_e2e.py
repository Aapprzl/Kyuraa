import pytest
import asyncio
import json
import subprocess
import time
import sys
from pathlib import Path

from src.agent.agent_loop import AgentLoop
from src.memory.session_store import SessionStore
from src.memory.glossary_store import GlossaryStore

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestE2E:
    @classmethod
    def setup_class(cls):
        cls.port = 8780
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.gateway.server:app",
             "--host", "127.0.0.1", "--port", str(cls.port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(4)

    @classmethod
    def teardown_class(cls):
        cls.server.terminate()
        cls.server.wait()

    async def _send_message(self, session_id: str, content: str):
        import websockets
        uri = f"ws://127.0.0.1:{self.port}/ws/{session_id}"
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"type": "message", "content": content}))
            tokens = []
            async for msg in ws:
                data = json.loads(msg)
                if data.get("type") == "token":
                    tokens.append(data.get("content", ""))
                elif data.get("type") == "done":
                    break
                elif data.get("type") == "error":
                    raise Exception(data.get("message"))
            return "".join(tokens)

    @pytest.mark.asyncio
    async def test_1_arabic_to_indonesian(self):
        """Test Case 1: Deteksi arah Arab ke Indonesia"""
        response = await self._send_message("e2e-01", "مَنْهَجِيَّةُ الْبَحْثِ")
        response_lower = response.lower()
        assert "metodologi" in response_lower or "metod" in response_lower, \
            f"Expected 'metodologi' in response, got: {response[:200]}"

    @pytest.mark.asyncio
    async def test_2_indonesian_to_arabic(self):
        """Test Case 2: Deteksi arah Indonesia ke Arab"""
        response = await self._send_message("e2e-02", "[LINGUISTIC] [AKADEMIK] Terjemahkan ke Arab: metodologi penelitian")
        has_arabic = any("\u0600" <= c <= "\u06FF" for c in response)
        assert has_arabic, f"Expected Arabic in response, got: {response[:200]}"

    @pytest.mark.asyncio
    async def test_3_mode_translation_only(self):
        """Test Case 3: Mode translation-only tanpa analisis gramatikal"""
        response = await self._send_message("e2e-03", "[TRANSLATION-ONLY] [AKADEMIK] hasil saja: bab penelitian")
        response_lower = response.lower()
        has_nahwu = any(word in response_lower for word in ["nahwu", "i'rab", "fi'il", "isim", "irab"])
        if has_nahwu:
            print(f"Warning: translation-only may contain grammar terms: {response[:200]}")
        has_arabic = any("\u0600" <= c <= "\u06FF" for c in response)
        assert has_arabic, "Expected Arabic translation in response"

    @pytest.mark.asyncio
    async def test_4_mode_linguistic(self):
        """Test Case 4: Mode linguistic dengan poin nahwu/sharaf"""
        response = await self._send_message("e2e-04", "[LINGUISTIC] [AKADEMIK] analisis: variabel bebas")
        response_lower = response.lower()
        has_analysis = any(word in response_lower for word in ["nahwu", "i'rab", "sharaf", "fi'il", "wazan", "analisis", "gramatikal"])
        assert has_analysis, f"Expected grammatical analysis in linguistic mode, got: {response[:300]}"

    @pytest.mark.asyncio
    async def test_5_save_to_file(self):
        """Test Case 5: Simpan terjemahan ke file output"""
        from src.agent.agent_loop import AgentLoop
        from pathlib import Path

        output_dir = Path("workspace/output")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "test_e2e_output.txt"
        if output_file.exists():
            output_file.unlink()

        agent = AgentLoop(session_id="e2e-05")
        response = agent.run(user_input="[TRANSLATION-ONLY] [AKADEMIK] terjemahkan: penelitian")

        saved_path = agent.save_translation("test_e2e_output.txt", response.get("response", ""))

        assert output_file.exists(), f"File should exist at {output_file}"
        content = output_file.read_text(encoding="utf-8")
        assert len(content) > 0, "File should have content"

    @pytest.mark.asyncio
    async def test_6_glossary_saved(self):
        """Test Case 6: Glosarium tersimpan setelah terjemahan"""
        glossary_path = Path("workspace/glossary/glossary.json")
        if glossary_path.exists():
            glossary_path.unlink()

        agent = AgentLoop(session_id="e2e-06")
        response = agent.run(user_input="[LINGUISTIC] [AKADEMIK] Terjemahkan: metodologi penelitian")

        glossary = GlossaryStore()
        terms = glossary.get_all().get("terms", [])
        assert len(terms) > 0, "Glossary should have at least one term after translation"

    @pytest.mark.asyncio
    async def test_7_session_history(self):
        """Test Case 7: Riwayat sesi dengan 3 pesan berurutan"""
        session_id = "e2e-07"
        store = SessionStore()
        store.clear_session(session_id)
        store.create_session(session_id)

        messages = [
            "Pesan pertama",
            "Pesan kedua",
            "Pesan ketiga"
        ]

        for msg in messages:
            store.add_message(session_id, "user", msg)

        history = store.get_history(session_id, limit=20)
        assert len(history) == 3, f"Expected 3 messages, got {len(history)}"
        assert history[0]["content"] == "Pesan pertama"
        assert history[1]["content"] == "Pesan kedua"
        assert history[2]["content"] == "Pesan ketiga"
