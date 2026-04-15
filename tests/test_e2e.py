import pytest
import asyncio
import json
import subprocess
import time
import sys
import os
from pathlib import Path

# Fix path to include src
sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_TOKEN = "test-token-12345"

class TestE2E:
    @classmethod
    def setup_class(cls):
        cls.port = 8780
        # Set fixed token for testing
        env = os.environ.copy()
        env["GATEWAY_TOKEN"] = TEST_TOKEN
        env["KYURAA_TEST_MODE"] = "1"
        # Start server
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.gateway.server:app",
             "--host", "127.0.0.1", "--port", str(cls.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True
        )
        
        # Polling active health check
        import urllib.request
        import urllib.error
        for _ in range(30):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{cls.port}/stats?token={TEST_TOKEN}", timeout=1)
                break
            except (urllib.error.URLError, ConnectionError, urllib.error.HTTPError):
                time.sleep(0.5)
        else:
            cls.server.terminate()
            raise RuntimeError("Test server failed to start within 15 seconds")

    @classmethod
    def teardown_class(cls):
        cls.server.terminate()
        cls.server.wait()
        
        # Cleanup test database
        try:
            import sqlite3
            with sqlite3.connect("workspace/memory/sessions.db") as conn:
                conn.execute("DELETE FROM messages WHERE session_id LIKE 'test-session-%'")
                conn.execute("DELETE FROM sessions WHERE session_id LIKE 'test-session-%'")
                conn.commit()
        except Exception:
            pass

    async def _get_ws_connection(self, session_id: str):
        import websockets
        uri = f"ws://127.0.0.1:{self.port}/ws/{session_id}?token={TEST_TOKEN}"
        return await websockets.connect(uri)

    async def _send_message(self, session_id: str, content: str):
        ws = await self._get_ws_connection(session_id)
        async with ws:
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
    async def test_1_api_auth_failure(self):
        """Test Case: Pastikan API menolak tanpa token valid"""
        import httpx
        async with httpx.AsyncClient() as client:
            # Tanpa header X-API-Key
            response = await client.get(f"http://127.0.0.1:{self.port}/stats")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_2_api_auth_success(self):
        """Test Case: Pastikan API menerima dengan token valid"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://127.0.0.1:{self.port}/stats",
                headers={"X-API-Key": TEST_TOKEN}
            )
            assert response.status_code == 200
            assert "total_requests" in response.json()

    @pytest.mark.asyncio
    async def test_3_translation_flow(self):
        """Test Case: Flow terjemahan dasar"""
        response = await self._send_message("e2e-basic", "Halo, siapa kamu?")
        assert len(response) > 0
        assert "Kyuraa" in response or "asisten" in response.lower()

    @pytest.mark.asyncio
    async def test_4_websocket_reconnection(self):
        """Test Case: Simulasi pemutusan dan penyambungan kembali WebSocket"""
        session_id = "reconnect-test"
        
        # 1. Koneksi pertama
        ws1 = await self._get_ws_connection(session_id)
        await ws1.close() # Putus sengaja
        
        # 2. Koneksi kedua (reconnect) dengan session id sama
        ws2 = await self._get_ws_connection(session_id)
        async with ws2:
            await ws2.send(json.dumps({"type": "message", "content": "Tes reconnect"}))
            # Tunggu respon sedikit untuk pastikan server tidak crash
            msg = await ws2.recv()
            assert msg is not None
