# Kyuraa

Asisten AI penerjemah Arab-Indonesia berkualitas akademik dengan sistem skill dinamis.

## Fitur Utama

- **Terjemahan Dua Arah** - Indonesia ↔ Arab dengan deteksi otomatis arah
- **3 Mode Output** - Linguistic (dengan analisis), Default (ringkasan), Translation-only (hasil saja)
- **3 Gaya Terjemahan** - Akademik, Semi-formal, Non-formal
- **Analisis Gramatikal** - Referensi Nahwu, Sharaf, dan Balaghah terintegrasi
- **Dynamic Skill System** - Sistem skill dinamis dengan Progressive Disclosure
- **Streaming Real-time** - Response muncul token per token
- **Web UI Modern** - Dark theme dengan Tailwind CSS

## Dynamic Skill System

Kyuraa menggunakan sistem skill dinamis dengan 3-level Progressive Disclosure:

### L1 - Discovery (~100 token)
Agent memindai semua skill yang tersedia dan menampilkan daftar skill ke user.

### L2 - Activation (~full SKILL.md)
Saat skill diaktifkan, SKILL.md lengkap dimuat beserta referensi wajib.

### L3 - Reference Loading (on-demand)
Referensi tambahan dimuat sesuai kebutuhan saat proses terjemahan.

### Cara Menambah Skill Baru

```bash
workspace/skills/
├── penerjemah-arab-indo/      # Skill terjemahan
│   ├── SKILL.md               # Metadata & instruksi skill
│   └── references/            # Referensi skill ini
│       ├── 01-nahwu.md
│       ├── 02-sharaf.md
│       └── ...
└── skill-baru-lain/            # Skill baru
    ├── SKILL.md
    └── references/
```

## Cara Install

```bash
# Clone repo
git clone https://github.com/Aapprzl/Kyuraa.git
cd Kyuraa

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env dan isi OPENROUTER_API_KEY kamu
```

## Cara Menjalankan

### Opsi 1: Double-click
```
Double-click run.bat
```

### Opsi 2: Manual
```bash
python -m uvicorn src.gateway.server:app --host 127.0.0.1 --port 8766
```

Buka browser: **http://localhost:8766**

## Penggunaan

### Aktivasi Skill

Ketik salah satu perintah berikut untuk mengaktifkan skill:
- `aktifkan skill penerjemah-arab-indo`
- `gunakan skill penerjemah-arab-indo`
- `pakai skill penerjemah-arab-indo`

Atau cukup kirim teks Arab untuk auto-trigger.

### Deaktivasi Skill

Ketik:
- `nonaktifkan skill`
- `matikan skill`
- `keluar dari skill`

### Chat Biasa

Tanpa skill aktif, Kyuraa bisa diajak ngobrol seperti asisten biasa.

## Struktur Proyek

```
Kyuraa/
├── run.bat                    # Jalankan server
├── requirements.txt            # Dependencies
├── .env                       # API Key (jangan di-commit!)
├── src\
│   ├── agent\                 # Core agent
│   │   ├── skill_manager.py   # Dynamic skill system
│   │   ├── prompt_builder.py  # Bangun prompt
│   │   ├── llm_client.py      # Koneksi OpenRouter API
│   │   └── agent_loop.py      # Main loop
│   ├── gateway\               # Web server
│   │   ├── server.py          # FastAPI + WebSocket
│   │   └── static\index.html  # WebChat UI
│   ├── tools\                 # Tools registry
│   │   └── registry.py        # OS access tools
│   └── memory\                # Persistent storage
│       ├── session_store.py   # Riwayat sesi (SQLite)
│       └── glossary_store.py  # Glosarium (JSON)
├── workspace\
│   ├── skills\                # Dynamic skills
│   │   └── penerjemah-arab-indo\
│   │       ├── SKILL.md       # Skill metadata
│   │       └── references\   # Nahwu, Sharaf, Balaghah
│   ├── output\                # File hasil terjemahan
│   ├── memory\                # sessions.db
│   └── settings.json          # Konfigurasi runtime
└── tests\                     # Unit & E2E tests
```

## API Endpoints

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/` | GET | WebChat UI |
| `/health` | GET | Health check |
| `/info` | GET | Info model |
| `/settings` | GET | Settings info |
| `/settings/validate-and-save` | POST | Simpan settings |
| `/sessions` | GET | List semua sesi |
| `/files` | GET | List file output |
| `/skills` | GET | Daftar skill tersedia |
| `/skills/activate` | POST | Aktifkan skill |
| `/skills/deactivate` | POST | Nonaktifkan skill |
| `/ws/{session_id}` | WS | WebSocket chat |

## Skill: Penerjemah Arab-Indonesia

Skill utama untuk menerjemahkan teks akademik antara Bahasa Indonesia dan Bahasa Arab.

### Trigger Keywords
- terjemahkan, terjemah, apa artinya
- arab-kan, indonesia-kan
- nahwu, sharaf, balaghah
- karya ilmiah arab, skripsi arab, tesis arab
- abstrak arab

### Mode Output

| Mode | Deskripsi |
|------|-----------|
| `linguistic` | Terjemahan + analisis gramatikal lengkap |
| `default` | Terjemahan + ringkasan poin penting |
| `translation-only` | Hanya teks terjemahan |

### Gaya Terjemahan

| Gaya | Penggunaan |
|------|------------|
| `Akademik` | Skripsi, tesis, jurnal, makalah |
| `Semi-formal` | Artikel, presentasi, laporan |
| `Non-formal` | Blog, media sosial, percakapan |

## Keamanan

- Tool registry menggunakan **ALLOWED_PATHS** - agent hanya bisa akses folder tertentu
- `.env` tidak di-commit ke repo
- Session dan glossary tersimpan lokal

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_skill_loader.py -v
```

## Tech Stack

- **LLM**: OpenRouter API (qwen3.6-plus:free)
- **Web**: FastAPI + Uvicorn + WebSocket
- **UI**: Tailwind CSS (CDN) + Vanilla JS
- **Storage**: SQLite (sessions) + JSON (glossary)
- **Testing**: Pytest + pytest-asyncio

## Lisensi

MIT License

## Credits

Dibuat oleh Muh Aprizal
