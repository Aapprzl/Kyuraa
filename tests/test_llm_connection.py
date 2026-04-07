import os
import sys
from pathlib import Path
import pytest

# Fix path to include src
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env for testing
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip()

from src.agent.llm_client import LLMClient

@pytest.mark.skipif(not os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("GOOGLE_API_KEY"), 
                    reason="API keys not found in .env")
def test_llm_client_connection():
    print("Testing LLM Client...")
    client = LLMClient()
    response = client.chat(
        system="Kamu adalah asisten terjemahan.",
        messages=[{"role": "user", "content": "Halo, apa kabar?"}]
    )
    
    assert len(response) > 0, "Response should not be empty"
    assert "content" in response, "Response should have 'content' key"
    assert len(response["content"]) > 0, "Response content should not be empty"
    
    print("LLM Client OK:", response["content"][:100])
    print("Model:", response.get("model"))
    print("Usage:", response.get("usage"))
