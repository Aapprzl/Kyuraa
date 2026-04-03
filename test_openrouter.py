"""Quick test script untuk validasi koneksi OpenRouter dengan model qwen3.6-plus:free."""
import os
from pathlib import Path

for line in Path(".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

api_key = os.environ.get("OPENROUTER_API_KEY", "")
model = os.environ.get("AGENT_MODEL", "qwen/qwen3.6-plus:free")

print(f"API Key  : {api_key[:20]}...{api_key[-6:]}")
print(f"Model    : {model}")
print("-" * 60)

from openai import OpenAI
client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

print("Mengirim permintaan test...")
try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Kamu adalah penerjemah Arab-Indonesia yang handal."},
            {"role": "user", "content": "Terjemahkan 'metodologi penelitian kualitatif' ke Bahasa Arab. Jawab singkat."}
        ],
        max_tokens=200,
    )
    content = response.choices[0].message.content
    print(f"✅ SUKSES!")
    print(f"Response : {content}")
    print(f"Model    : {response.model}")
except Exception as e:
    print(f"❌ GAGAL: {type(e).__name__}: {e}")
