# Penerjemah Arab-Indonesia

Agent AI untuk menerjemahkan teks antara Bahasa Indonesia dan Bahasa Arab dengan akurasi gramatikal tinggi.

## Fitur Utama

- **Terjemahan Dua Arah** - Indonesia ↔ Arab dengan deteksi otomatis
- **3 Mode Output** - Linguistic (dengan analisis), Default (ringkas), Translation-only (hasil saja)
- **3 Gaya Terjemahan** - Akademik, Semi-formal, Non-formal
- **Referensi Nahwu & Sharaf** - Analisis gramatikal otomatis
- **Streaming Real-time** - Response muncul token per token
- **Auto-save** - Glosarium dan hasil terjemahan tersimpan otomatis

## Cara Install

```bash
# Clone repo
git clone https://github.com/Aapprzl/agent-arab.git
cd agent-arab

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env dan isi GEMINI_API_KEY kamu
```

## Cara Menjalankan

### Opsi 1: Double-click
```
Double-click run.bat
```

### Opsi 2: Manual
```bash
python -m uvicorn src.gateway.server:app --host 127.0.0.1 --port 8765
```

Buka browser: **http://localhost:8765**

## Struktur Proyek

```
C:\agent-arab\
├── run.bat                    # Jalankan agent
├── requirements.txt            # Dependencies
├── .env                       # API Key (jangan di-commit!)
├── src\
│   ├── agent\                 # Core agent
│   │   ├── skill_loader.py    # Load SKILL.md
│   │   ├── prompt_builder.py # Bangun prompt
│   │   ├── llm_client.py    # Koneksi Gemini API
│   │   └── agent_loop.py    # Main loop
│   ├── gateway\               # Web server
│   │   ├── server.py        # FastAPI + WebSocket
│   │   └── static\index.html # WebChat UI
│   ├── tools\                 # Tools registry
│   │   └── registry.py       # OS access tools
│   └── memory\               # Persistent storage
│       ├── session_store.py   # Riwayat sesi (SQLite)
│       └── glossary_store.py  # Glosarium (JSON)
├── workspace\
│   ├── references\           # Nahwu, Sharaf, Balaghah
│   ├── output\              # File hasil terjemahan
│   └── glossary\            # Glosarium tersimpan
└── tests\                    # Unit & E2E tests
```

## Penggunaan

1. **Pilih Mode**: Linguistic / Default / Translation-only
2. **Pilih Gaya**: Akademik / Semi-formal / Non-formal
3. **Ketik teks** yang ingin diterjemahkan
4. Tekan **Enter** atau klik **Kirim**
5. Response streaming muncul real-time
6. Klik **💾 Simpan** untuk simpan hasil

### Contoh Input

```
[LINGUISTIC] [AKADEMIK] Terjemahkan ke Arab: metodologi penelitian kualitatif
```

## API Endpoints

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/` | GET | WebChat UI |
| `/health` | GET | Health check |
| `/sessions` | GET | List semua sesi |
| `/glossary` | GET | Ambil glosarium (JSON) |
| `/files` | GET | List file output |
| `/ws/{session_id}` | WS | WebSocket chat |

## Keamanan

- Tool registry menggunakan **ALLOWED_PATHS** - agent hanya bisa akses folder tertentu
- `.env` tidak di-commit ke repo
- Session dan glossary tersimpan lokal

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run E2E tests
python -m pytest tests/test_e2e.py -v
```

## Tech Stack

- **LLM**: Google Gemini Flash
- **Web**: FastAPI + Uvicorn + WebSocket
- **UI**: Tailwind CSS + Vanilla JS
- **Storage**: SQLite (sessions) + JSON (glossary)
- **Testing**: Pytest + pytest-asyncio

## Lisensi

MIT License
