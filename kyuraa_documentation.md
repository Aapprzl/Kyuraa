# 📘 Dokumentasi Sistem Kyuraa AI Agent

> **Versi:** 1.0.3 · **Author:** Muh Aprizal · **Platform:** Python + FastAPI + WebSocket

---

## 📋 Daftar Isi

1. [Gambaran Umum](#1-gambaran-umum)
2. [Arsitektur Sistem](#2-arsitektur-sistem)
3. [Struktur Direktori](#3-struktur-direktori)
4. [Modul: Agent (`src/agent/`)](#4-modul-agent-srcagent)
5. [Modul: Gateway (`src/gateway/`)](#5-modul-gateway-srcgateway)
6. [Modul: Memory (`src/memory/`)](#6-modul-memory-srcmemory)
7. [Modul: Tools (`src/tools/`)](#7-modul-tools-srctools)
8. [Modul: Utils (`src/utils/`)](#8-modul-utils-srcutils)
9. [Workspace](#9-workspace)
10. [Sistem Skills](#10-sistem-skills)
11. [Sistem Custom Tools](#11-sistem-custom-tools)
12. [Keamanan](#12-keamanan)
13. [API Endpoints](#13-api-endpoints)
14. [Alur Kerja Sistem](#14-alur-kerja-sistem)
15. [Konfigurasi & Lingkungan](#15-konfigurasi--lingkungan)
16. [Instalasi & Menjalankan Proyek](#16-instalasi--menjalankan-proyek)
17. [Testing](#17-testing)
18. [Dependensi](#18-dependensi)

---

## 1. Gambaran Umum

**Kyuraa** adalah sistem AI Agent lokal berbasis Python yang dirancang sebagai **asisten pribadi yang dapat dikustomisasi**. Sistem ini menggabungkan kecerdasan model bahasa besar (LLM) dengan kemampuan eksekusi tools dan sistem Skills yang fleksibel.

### Fitur Utama

| Fitur | Keterangan |
|-------|-----------|
| 💬 **Chat Multi-Sesi** | Percakapan disimpan di SQLite per sesi, mendukung banyak percakapan terpisah |
| 🔌 **Multi-Provider LLM** | Mendukung Google Gemini (native) dan OpenRouter (ratusan model) |
| 🌊 **Streaming Real-time** | Respons dikirim token demi token via WebSocket, dengan auto-reconnect |
| 🛠️ **Tool Call System** | AI dapat memanggil tool (baca/tulis file, deteksi bahasa, dll.) via tag khusus |
| 🎓 **Skill System** | Kepribadian/instruksi AI dapat diubah-ubah via file Markdown tanpa coding |
| 📄 **Upload PDF** | Mendukung unggah PDF dengan ekstraksi teks + OCR fallback untuk PDF scan |
| 🔒 **Keamanan** | Token gateway, enkripsi API key (Fernet), path sandboxing, static code analysis |
| 📊 **Usage Analytics** | Pencatatan token input/output per sesi, per model, per hari |
| 🗂️ **Custom Tools** | Pengguna dapat menambah tool Python sendiri di `workspace/tools/` |

### Target Pengguna

Kyuraa didesain untuk pengguna yang ingin memiliki asisten AI **lokal dan terkontrol**, dengan kemampuan untuk menyesuaikan perilaku AI (via Skills) dan menambah kemampuan baru (via Custom Tools) tanpa memerlukan keahlian teknis mendalam.

---

## 2. Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER / KLIEN UI                       │
│  index.html + script.js + style.css                         │
│  settings.html + settings.js + settings.css                 │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTP REST + WebSocket (ws://)
                  │ Auth: X-API-Key header / ?token=
┌─────────────────▼───────────────────────────────────────────┐
│               GATEWAY SERVER (FastAPI + uvicorn)            │
│  src/gateway/server.py → GatewayServer                      │
│                                                             │
│  Routers:                                                   │
│  ┌──────────────┐ ┌─────────────┐ ┌──────────┐ ┌────────┐  │
│  │settings_router│ │upload_router│ │session_  │ │stats_  │  │
│  │              │ │             │ │router    │ │router  │  │
│  └──────────────┘ └─────────────┘ └──────────┘ └────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │ instansiasi per sesi
┌─────────────────▼───────────────────────────────────────────┐
│                   AGENT LOOP                                │
│  src/agent/agent_loop.py → AgentLoop                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SkillManager │  │PromptBuilder │  │  LLMClient   │      │
│  │(skill system)│  │(sys.prompt)  │  │  (OpenAI     │      │
│  └──────────────┘  └──────────────┘  │  compatible) │      │
│                                      └──────┬───────┘      │
│  ┌──────────────┐  ┌──────────────┐         │              │
│  │ SessionStore │  │ ToolRegistry │  ┌───────▼──────┐      │
│  │ (SQLite)     │  │ (tool exec)  │  │  LLM Provider│      │
│  └──────────────┘  └──────────────┘  │ Google/OpenR │      │
│                                      └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
         │                  │
┌────────▼──────┐  ┌────────▼──────────┐
│  MEMORY LAYER │  │    TOOLS LAYER    │
│  sessions.db  │  │ Built-in: 9 tools │
│  usage.db     │  │ Custom: *.py files│
│  glossary.json│  │ PDF: pdfplumber   │
└───────────────┘  │        + PyMuPDF  │
                   │        + EasyOCR  │
                   └───────────────────┘
```

### Komponen Inti

| Komponen | File | Peran |
|---------|------|-------|
| **GatewayServer** | `src/gateway/server.py` | Entry point, FastAPI app, WebSocket handler |
| **AgentLoop** | `src/agent/agent_loop.py` | Orkestrator utama per sesi |
| **LLMClient** | `src/agent/llm_client.py` | Komunikasi dengan LLM provider |
| **PromptBuilder** | `src/agent/prompt_builder.py` | Menyusun system prompt + riwayat |
| **SkillManager** | `src/agent/skill_manager.py` | Mengelola sistem Skills |
| **ToolRegistry** | `src/tools/registry.py` | Mendaftarkan & mengeksekusi tools |
| **SessionStore** | `src/memory/session_store.py` | Persistensi riwayat percakapan |
| **UsageStore** | `src/memory/usage_store.py` | Pencatatan penggunaan token |
| **GlossaryStore** | `src/memory/glossary_store.py` | Kamus istilah Arab-Indonesia |
| **SecurityManager** | `src/utils/security.py` | Enkripsi dan autentikasi |

---

## 3. Struktur Direktori

```
d:\PROJECT_APP\Kyuraa\
│
├── .env                          # Konfigurasi API Key & environment (plaintext)
├── .gitignore                    # File yang diabaikan Git
├── .kyuraa-lock-8766             # PID lock file (single-instance enforcement)
├── requirements.txt              # Daftar dependensi Python
├── run.bat                       # Script Windows untuk menjalankan server
│
├── src/                          # Source code utama
│   ├── __init__.py
│   │
│   ├── agent/                    # Logika inti AI Agent
│   │   ├── agent_loop.py         # Orkestrator utama (AgentLoop class)
│   │   ├── llm_client.py         # Client LLM (Google / OpenRouter)
│   │   ├── prompt_builder.py     # Pembangun system prompt & message history
│   │   └── skill_manager.py      # Manajemen sistem Skills
│   │
│   ├── gateway/                  # Web server & API
│   │   ├── server.py             # FastAPI app, WebSocket handler, GatewayServer
│   │   ├── routers/              # Router API terpisah
│   │   │   ├── settings_router.py  # Endpoint konfigurasi model/API key
│   │   │   ├── upload_router.py    # Endpoint upload & proses PDF
│   │   │   ├── session_router.py   # Endpoint manajemen sesi
│   │   │   └── stats_router.py     # Endpoint statistik penggunaan
│   │   └── static/               # File statis UI
│   │       ├── index.html          # Halaman chat utama
│   │       ├── script.js           # Logika UI chat (~72 KB)
│   │       ├── style.css           # Styling halaman chat (~52 KB)
│   │       ├── settings.html       # Halaman pengaturan
│   │       ├── settings.js         # Logika UI pengaturan (~24 KB)
│   │       └── settings.css        # Styling halaman pengaturan
│   │
│   ├── memory/                   # Lapisan persistensi data
│   │   ├── session_store.py      # Simpan/ambil riwayat percakapan (SQLite)
│   │   ├── usage_store.py        # Log penggunaan token (SQLite)
│   │   └── glossary_store.py     # Kamus istilah (JSON)
│   │
│   ├── tools/                    # Sistem tools
│   │   ├── registry.py           # Registri dan eksekutor tools
│   │   ├── file_reader.py        # Pembaca file besar berbasis chunk
│   │   ├── pdf_processor.py      # Ekstraksi teks PDF (+ OCR)
│   │   └── tool_loader.py        # Dynamic loader untuk custom tools
│   │
│   └── utils/                    # Utilitas bersama
│       ├── logger.py             # Colored terminal logger
│       └── security.py           # Enkripsi Fernet + token autentikasi
│
├── tests/                        # Suite pengujian
│   ├── test_e2e.py               # End-to-end: server, WebSocket, auth
│   ├── test_llm_connection.py    # Koneksi ke LLM provider
│   ├── test_memory.py            # SessionStore & GlossaryStore
│   ├── test_security_boundaries.py  # Keamanan path dan tool
│   ├── test_skill_manager.py     # SkillManager discover & activate
│   └── test_tools.py             # Built-in tools & ToolRegistry
│
├── venv/                         # Virtual environment Python
│
└── workspace/                    # Data runtime (bisa diubah pengguna)
    ├── .kyuraa-secret            # Kunci enkripsi master (Fernet key)
    ├── settings.json             # Konfigurasi aktif (terenkripsi)
    │
    ├── memory/                   # Database runtime
    │   ├── sessions.db           # Riwayat percakapan (SQLite)
    │   └── usage.db              # Log penggunaan token (SQLite)
    │
    ├── skills/                   # Skill packages
    │   ├── SKILL_TEMPLATE.md     # Template membuat skill baru
    │   └── penerjemah-arab-indo/ # Contoh skill bawaan
    │       ├── SKILL.md          # Definisi & instruksi skill
    │       └── references/       # Dokumen referensi skill
    │
    ├── tools/                    # Custom tools Python
    │   ├── TOOL_TEMPLATE.py      # Template membuat tool baru
    │   └── word-counter.py       # Contoh custom tool
    │
    ├── output/                   # Hasil ekspor/terjemahan
    └── tempat_baca/              # File PDF yang diunggah
        └── uploaded_pdfs/        # Direktori upload PDF
```

---

## 4. Modul: Agent (`src/agent/`)

### 4.1 `agent_loop.py` — AgentLoop

Kelas utama yang mengorkestrasikan seluruh alur pemrosesan permintaan pengguna per sesi.

#### Konstruktor
```python
AgentLoop(session_id: str | None = None)
```
- Jika `session_id` tidak diberikan, UUID baru dibuat otomatis.
- Menginisialisasi: `SkillManager`, `PromptBuilder`, `LLMClient`, `SessionStore`, `ToolRegistry`.
- Membuat sesi baru di database jika belum ada.

#### Method Utama

| Method | Keterangan |
|--------|-----------|
| `run(user_input, metadata)` | Pemrosesan sinkron — mengembalikan dict hasil lengkap |
| `run_stream(user_input, metadata)` | Generator — yield `(token, usage, finish_reason)` per token; auto-resume jika koneksi putus (maks 3x percobaan) |
| `execute_tool(tool_name, **kwargs)` | Eksekusi tool secara langsung |
| `save_translation(filename, content)` | Shortcut simpan hasil terjemahan ke `workspace/output/` |
| `get_history(limit)` | Ambil riwayat percakapan sesi ini |
| `clear_history()` | Hapus seluruh riwayat sesi ini |

#### Alur `run()` / `run_stream()`

```
Input Pengguna
    │
    ├── _detect_language()     → deteksi bahasa (Arab/Indonesia/Campuran)
    ├── _detect_style()        → deteksi gaya (akademik/semi-formal/non-formal)
    │
    ├── SessionStore.add_message()    → simpan pesan user ke DB
    ├── SessionStore.get_history()    → ambil 20 pesan terakhir
    │
    ├── detect_needed_references()    → tentukan referensi yang dibutuhkan
    ├── _load_references()            → muat konten referensi dari disk
    │
    ├── build_system_with_references() → susun system prompt lengkap
    ├── build_messages()              → susun message history untuk LLM
    │
    ├── LLMClient.chat() / .stream()  → kirim ke LLM, terima respons
    │
    ├── SessionStore.add_message()    → simpan respons AI ke DB
    └── _execute_tool_calls()         → parsing & eksekusi tool calls dari respons
```

#### Tool Call Syntax
AI memanggil tool dengan format khusus dalam respons teksnya:
```
[TOOL: nama_tool] param1="nilai1" param2="nilai2"
```
Pola ini di-parse oleh `parse_tool_calls()` menggunakan regex.

#### Auto-resume Stream
Jika koneksi stream terputus karena timeout/rate-limit/network error:
- Respons parsial disimpan di `full_response`.
- Percobaan ulang dimulai dengan melanjutkan teks di mana koneksi putus.
- Maksimum 3 kali percobaan, delay 3 detik antar percobaan.

#### Deteksi Gaya Bahasa
```python
_detect_style(user_input) → "akademik" | "semi-formal" | "non-formal"
```
Berdasarkan kata kunci: `akademik`, `skripsi`, `tesis`, `jurnal`, `formal`, `ilmiah`.

---

### 4.2 `llm_client.py` — LLMClient

Menangani komunikasi dengan LLM provider menggunakan OpenAI-compatible API.

#### Konstruktor
```python
LLMClient(api_key=None, model=None, max_tokens=None, timeout=120)
```

#### Multi-Provider Support

| Provider | Env Var | Base URL |
|----------|---------|----------|
| `google` | `GOOGLE_API_KEY`, `GOOGLE_MODEL` | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `openrouter` | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | `https://openrouter.ai/api/v1` |

Provider aktif dikontrol oleh env var `ACTIVE_PROVIDER`.

#### Method Utama

| Method | Keterangan |
|--------|-----------|
| `chat(system, messages, truncate_history)` | Request non-streaming, retry 3x untuk error rate-limit/network/timeout |
| `stream(system, messages)` | Generator streaming per token; yield `(token, usage, finish_reason)` |
| `count_tokens(messages)` | Estimasi jumlah token (heuristik: `len(content) // 3` — lebih konservatif untuk Arab/Indonesia) |
| `summarize(messages)` | Merangkum percakapan dalam bahasa Indonesia (untuk sesi lanjutan) |

#### Error Handling

| Jenis Error | Penanganan |
|------------|-----------|
| Rate limit (429) | Retry 3x, delay 5 detik |
| Network error | Retry 2x, delay 2 detik |
| Timeout | Raise `TimeoutError` |
| API Key invalid (401/403) | Raise `ValueError` |

#### Context Window Safety
- Estimasi token dihitung sebelum request.
- Jika melebihi `_max_input_estimate` (30.000 token): riwayat dipotong setengah (`_truncate_history`).

---

### 4.3 `prompt_builder.py` — PromptBuilder

Bertanggung jawab menyusun **system prompt** dan **message history** yang dikirim ke LLM.

#### Method Utama

| Method | Output |
|--------|--------|
| `build_system_prompt(skill_manager, tool_registry)` | System prompt dasar + daftar tools + status/instruksi skill |
| `build_system_with_references(skill_manager, references, tool_registry)` | Seperti di atas + konten referensi aktif |
| `build_messages(session_history, user_input, current_metadata)` | List message (format OpenAI) dengan metadata file yang diformat |
| `detect_needed_references(user_input, skill_manager)` | List nama referensi yang perlu dimuat berdasarkan konteks |

#### Sistem Prompt Dasar
```
Kamu adalah asisten AI pribadi cerdas. Gunakan skill/tool sesuai instruksi.

ATURAN:
- Jika obrolan biasa → jawab natural.
- Skill diaktifkan via Settings UI, jangan coba aktifkan via chat.
- Jika ada skill aktif, patuhi instruksinya secara ketat.
- AKSES FILE: Seluruh aksi file WAJIB menggunakan path yang berawalan 'workspace/'.

## TOOLS:
Gunakan tag: [TOOL: nama_tool] param="nilai"
```

#### Manajemen Metadata File
Jika pesan memiliki metadata file (PDF yang diunggah), konten diformat sebagai:
- **File normal:** `[CONTEXT - File: nama.pdf]\n--- FILE CONTENT ---\n{teks}\n---\n[USER MESSAGE]: ...`
- **PDF scan (tanpa teks):** Peringatan bahwa file tidak dapat dibaca.
- **File terhapus:** Notifikasi bahwa file sudah dihapus.

#### Deteksi Referensi
- `always_load`: selalu dimuat jika skill aktif.
- `on_demand`: dimuat kecuali input-nya salam/kata pendek (< 20 karakter).

---

### 4.4 `skill_manager.py` — SkillManager

Mengelola sistem **Skills** — paket instruksi AI yang dapat diaktifkan/nonaktifkan.

#### Konstruktor
```python
SkillManager()
```
1. Scan folder `workspace/skills/` → `discover()`.
2. Restore state skill aktif dari `workspace/settings.json` → `_restore_state()`.

#### Method Utama

| Method | Keterangan |
|--------|-----------|
| `discover()` | Scan ulang semua skill dari disk; update `available_skills` |
| `reload()` | Re-scan skill; pertahankan skill aktif jika masih ada |
| `activate(skill_name)` | Aktifkan skill; simpan state ke `settings.json` |
| `deactivate()` | Nonaktifkan skill aktif; simpan state ke `settings.json` |
| `load_reference(ref_name)` | Muat satu file referensi dari folder `references/` aktif skill |
| `load_always_references()` | Muat semua referensi yang ada di `always_load` |
| `get_system_prompt()` | Kembalikan isi `SKILL.md` + referensi `always_load` |
| `get_skills_summary()` | Ringkasan semua skill (untuk dimasukkan ke prompt saat tidak ada skill aktif) |
| `list_skills_detail()` | List lengkap skill + metadata (untuk API/UI) |
| `is_active()` | `True` jika ada skill yang sedang aktif |

#### Format Skill (`SKILL.md`)
Setiap skill adalah folder di `workspace/skills/` berisi file `SKILL.md` dengan YAML frontmatter:

```yaml
---
name: nama-skill
version: "1.0"
author: Nama Pembuat
category: Kategori
description: Deskripsi singkat skill
trigger_keywords:
  - kata1
  - kata2
references:
  always_load:
    - file-selalu-dimuat.md
  on_demand:
    - file-saat-butuh.md
---

# Instruksi Skill
[isi instruksi untuk AI...]
```

#### State Persistence
State skill aktif disimpan di `workspace/settings.json`:
```json
{ "active_skill": "nama-skill" }
```
Saat server restart, state ini di-restore otomatis.

---

## 5. Modul: Gateway (`src/gateway/`)

### 5.1 `server.py` — GatewayServer

Entry point aplikasi. Menginisialisasi FastAPI app, menangani WebSocket, dan mendaftarkan seluruh router.

#### Inisialisasi
```python
GatewayServer(host="localhost", port=8766)
```
- Load environment dari `settings.json` (terdesenkripsi) dan `.env`.
- **Single Instance Enforcement:** Cek port tersedia; jika ada instance lama, terminate via PID lock.
- Mount static files di `/static`.
- Tampilkan banner startup di terminal.

#### Single Instance via PID Lock
File `.kyuraa-lock-{port}` menyimpan PID proses aktif:
- Jika file ada dan PID masih berjalan → proses lama di-terminate.
- File dihapus otomatis saat server berhenti (`atexit`).

#### WebSocket Handler (`/ws/{session_id}`)
```
Client → connect (dengan ?token=)
       → send JSON: {type: "message", content: "...", file_context: {...}}
       ← receive JSON: {type: "token", content: "..."} (berulang)
       ← receive JSON: {type: "done", usage: {...}, tool_results: [...]}
```

**Alur pesan masuk:**
1. Validasi token WebSocket.
2. Buat/ambil `AgentLoop` untuk sesi.
3. Jalankan `agent.run_stream()` → kirim token satu per satu.
4. Log usage ke `UsageStore`.
5. Proses tool calls dengan **HITL (Human-in-the-Loop)** jika tool sensitif.
6. Kirim event `done`.

#### HITL (Human-in-the-Loop) untuk Tool Sensitif
Untuk tool yang masuk daftar `SENSITIVE_TOOLS` (`write_file`, `save_translation`, `delete_session`):
1. Server kirim event `approval_request` ke klien.
2. Tunggu konfirmasi `approval_response` dari klien.
3. Eksekusi tool hanya jika klien menyetujui.

#### Inisialisasi Agents
- **System Agent** (`__system__`): Satu agent shared untuk operasi admin (skill/tool management).
- **Per-Session Agent**: Satu `AgentLoop` per `session_id` WebSocket.

---

### 5.2 Routers

#### `settings_router.py`

| Endpoint | Method | Auth | Fungsi |
|----------|--------|------|--------|
| `/info` | GET | ❌ | Info model aktif & provider (publik) |
| `/settings` | GET | ✅ | Lihat konfigurasi (API key dimasking) |
| `/settings/validate-and-save` | POST | ✅ | Validasi koneksi LLM + simpan setting terenkripsi |

**Proses simpan setting:**
1. Terima `{provider, model, api_key}`.
2. Test koneksi ke LLM dengan pesan "hi".
3. Jika berhasil: simpan ke `settings.json` (API key dienkripsi Fernet).
4. Update env vars untuk sesi aktif.

#### `upload_router.py`

| Endpoint | Method | Auth | Fungsi |
|----------|--------|------|--------|
| `/upload` | POST | ✅ | Upload PDF, ekstrak teks, kembalikan metadata |
| `/upload/partial` | POST | ✅ | Ekstrak halaman tertentu dari PDF yang sudah terupload |
| `/upload/{file_id}` | GET | ✅ | Unduh file PDF yang tersimpan |
| `/upload/{file_id}` | DELETE | ✅ | Hapus file PDF + tandai metadata sebagai "deleted" |

**Batasan upload:**
- Hanya format `.pdf`.
- Maksimum ukuran: **5 MB**.
- Peringatan jika estimasi token > **25.000** (PDF terlalu panjang).

**Proses upload PDF:**
1. Nama file di-UUID untuk keamanan: `{uuid}_{original_name}`.
2. Teks diekstrak via `extract_text_from_pdf()` (async via `asyncio.to_thread`).
3. Estimasi token dikembalikan ke klien.

#### `session_router.py`

| Endpoint | Method | Auth | Fungsi |
|----------|--------|------|--------|
| `/sessions` | GET | ✅ | Daftar semua sesi (id, nama, waktu, jumlah pesan) |
| `/sessions/{id}/messages` | GET | ❌ | Semua pesan dalam satu sesi |
| `/sessions/{id}/messages/last` | DELETE | ❌ | Hapus pesan user terakhir |
| `/sessions/{id}/name` | PATCH | ❌ | Ubah nama sesi |
| `/sessions/cleanup` | DELETE | ❌ | Hapus sesi kosong (tanpa pesan) |
| `/files` | GET | ❌ | Daftar file di `workspace/output/` |

#### `stats_router.py`

| Endpoint | Method | Auth | Fungsi |
|----------|--------|------|--------|
| `/stats` | GET | ✅ | Total penggunaan (requests, input/output tokens) |
| `/stats/history` | GET | ✅ | Penggunaan per hari (default 7 hari) |
| `/stats/by-model` | GET | ✅ | Penggunaan dikelompokkan per model |
| `/stats/clear-models` | POST | ✅ | Hapus log penggunaan untuk model tertentu |

---

## 6. Modul: Memory (`src/memory/`)

### 6.1 `session_store.py` — SessionStore

Persistensi riwayat percakapan berbasis **SQLite**.

#### Skema Database (`workspace/memory/sessions.db`)

**Tabel `sessions`:**
```sql
session_id TEXT PRIMARY KEY
name       TEXT              -- auto-set dari 50 karakter pertama pesan user pertama
created_at TEXT
updated_at TEXT
```

**Tabel `messages`:**
```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT
session_id  TEXT REFERENCES sessions(session_id)
role        TEXT              -- 'user' | 'assistant'
content     TEXT
metadata    TEXT              -- JSON: {filename, file_id, text, script, deleted}
timestamp   TEXT
token_count INTEGER
```

#### Method Utama

| Method | Keterangan |
|--------|-----------|
| `create_session(session_id)` | Buat sesi baru (`INSERT OR IGNORE`) |
| `add_message(session_id, role, content, metadata)` | Simpan pesan; auto-set nama sesi dari pesan user pertama |
| `get_history(session_id, limit=20)` | Ambil N pesan terakhir, diurutkan ASC |
| `get_session_messages(session_id)` | Seluruh pesan sesi (untuk export/summary) |
| `list_sessions()` | Semua sesi + jumlah pesan, diurutkan `updated_at DESC` |
| `update_session_name(session_id, name)` | Beri nama sesi secara manual |
| `delete_session(session_id)` | Hapus sesi + semua pesannya |
| `delete_last_user_message(session_id)` | Hapus pesan user terakhir (untuk fitur "edit pesan") |
| `remove_file_metadata(file_id)` | Tandai metadata file sebagai `deleted: true` tanpa menghapus pesan |
| `auto_name_session(session_id)` | Set nama sesi dari konten pesan user pertama |

#### Migrasi Schema (Idempotent)
Saat `_init_db()`, kolom baru ditambahkan dengan `ALTER TABLE ... ADD COLUMN` yang dibungkus try-except, sehingga aman dijalankan berulang kali.

---

### 6.2 `usage_store.py` — UsageStore

Pencatatan statistik penggunaan token berbasis **SQLite**.

#### Skema Database (`workspace/memory/usage.db`)

**Tabel `usage_logs`:**
```sql
id            INTEGER PRIMARY KEY AUTOINCREMENT
timestamp     TEXT
session_id    TEXT
provider      TEXT    -- 'google' | 'openrouter'
model         TEXT    -- nama model yang digunakan
input_tokens  INTEGER
output_tokens INTEGER
latency       REAL
status        TEXT    -- 'success' | 'error'
```

#### Method Utama

| Method | Keterangan |
|--------|-----------|
| `log_usage(session_id, provider, model, input_tokens, output_tokens, latency, status)` | Catat satu entri penggunaan |
| `get_totals()` | Total kumulatif: jumlah request + total token |
| `get_daily_usage(days=7)` | Penggunaan per hari untuk N hari terakhir |
| `get_by_model()` | Penggunaan dikelompokkan per model, diurutkan total token DESC |
| `clear_by_models(models)` | Hapus log untuk model tertentu |

---

### 6.3 `glossary_store.py` — GlossaryStore

Kamus istilah Arab-Indonesia berbasis **JSON**.

#### Format Data (`workspace/glossary/glossary.json`)
```json
{
  "version": "1.0",
  "last_updated": "2026-...",
  "terms": [
    {
      "arabic":     "البحث",
      "indonesian": "penelitian",
      "context":    "akademik",
      "style":      "akademik",
      "added_at":   "2026-..."
    }
  ]
}
```

#### Method Utama

| Method | Keterangan |
|--------|-----------|
| `add_term(arabic, indonesian, context, style)` | Tambah istilah baru; rebuild index; simpan ke disk |
| `lookup(arabic)` | Cari berdasarkan kata Arab → `list[dict]` atau `None` |
| `lookup_reverse(indonesian)` | Cari berdasarkan kata Indonesia (case-insensitive) |
| `get_all()` | Kembalikan seluruh data kamus |
| `export_to_text()` | Format teks `# Glosarium Arab-Indonesia\n- kata = terjemahan` |

#### Indexing
Dibangun dua index in-memory saat load:
- `_index_arabic`: `{kata_arab: [idx,...]}` 
- `_index_indonesian`: `{kata_indo_lower: [idx,...]}`

---

## 7. Modul: Tools (`src/tools/`)

### 7.1 `registry.py` — ToolRegistry

Registri pusat untuk semua tools (built-in dan custom).

#### Inisialisasi
1. `_register_builtin_tools()` — Daftarkan 9 tool bawaan.
2. `_load_custom_tools()` — Scan & load file .py dari `workspace/tools/`.
3. `_sync_state()` — Sinkronisasi status enabled/disabled dari `settings.json`.

#### Built-in Tools

| Nama Tool | Fungsi |
|-----------|--------|
| `detect_language` | Deteksi bahasa teks berdasarkan rasio karakter Arab (Unicode U+0600–U+06FF) |
| `read_file` | Baca seluruh isi file dari `workspace/` (path sandboxed) |
| `write_file` | Tulis konten ke file di `workspace/` |
| `save_translation` | Simpan teks ke `workspace/output/{filename}` |
| `list_output_files` | Daftar file di `workspace/output/` |
| `load_reference` | Muat file referensi dari `src/skills/references/` |
| `scan_file` | Analisis file besar → kembalikan info chunk (judul, ukuran) |
| `read_chunk` | Baca satu chunk spesifik dari file berdasarkan indeks |
| `open_output_folder` | Buka folder output di Windows Explorer (via `subprocess.Popen`) |

#### Algoritma Deteksi Bahasa
```python
arabic_chars / total_chars:
  > 0.30  → "arabic"
  > 0.05  → "mixed"
  else    → "indonesian"
```

#### Path Sandboxing
Semua operasi file divalidasi dengan `_is_safe_path()`:
- Path di-resolve ke absolut menggunakan `Path.resolve()`.
- Harus dimulai dari `{cwd}/workspace/`.
- Jika di luar → `PermissionError`.

#### State Management (Enable/Disable)
- State disimpan di `workspace/settings.json` key `TOOLS_STATE`.
- `toggle(name)` → balik state + simpan ke disk.
- Tool baru default: enabled (`True`).

#### Method Utama

| Method | Keterangan |
|--------|-----------|
| `execute(name, **kwargs)` | Eksekusi tool; cek state enabled; return `{success, result/error}` |
| `toggle(name)` | Enable/disable tool; simpan ke settings.json |
| `reload()` | Reload custom tools dari disk tanpa restart |
| `list_tools_detail()` | List lengkap semua tools + metadata + status enabled |
| `register(name, func, description)` | Register tool secara programatik |

---

### 7.2 `tool_loader.py` — ToolLoader

Memuat custom tool Python secara dinamis dari file `.py`.

#### Format Custom Tool
```python
# name:        nama-tool
# description: Deskripsi singkat
# version:     1.0
# author:      Nama

def run(**kwargs) -> str | dict:
    """Implementasi tool"""
    ...
```

#### Proses Load
1. **Baca source code** dari file.
2. **Security scan** — tolak jika ada pola berbahaya.
3. **Parse metadata** dari komentar `# key: value` di header.
4. **Dynamic import** via `importlib.util`.
5. **Validasi** ada fungsi `run()`.

#### Pola Berbahaya yang Ditolak
```python
os.system(...)         # Shell command
subprocess.*           # Subprocess
shutil.rmtree/rmdir()  # Hapus folder
eval() / exec()        # Dynamic execution
__import__()           # Dynamic import
open(..., 'w')         # Tulis file langsung
os.remove/unlink/rmdir # Hapus file
```

---

### 7.3 `file_reader.py` — FileReader

Membaca file besar secara bertahap (chunk-by-chunk) dengan kesadaran paragraf.

#### Konfigurasi
```python
FileReader(max_chars=6000)  # Ukuran maksimal per chunk
```

#### Method Utama

| Method | Output |
|--------|--------|
| `read_file(filepath)` | Baca & bagi jadi chunks; simpan ke cache; return metadata |
| `get_chunk(filepath, chunk_index)` | Ambil satu chunk berisi content + metadata navigasi |
| `get_file_info(filepath)` | Metadata file + daftar chunks (tanpa cache) |

#### Algoritma Chunking
1. Coba split berdasarkan `\n\n` (paragraf).
2. Fallback ke `\n` (baris).
3. Fallback ke fixed-size split.
4. Chunk terlalu kecil di-merge.
5. Chunk terlalu besar dipecah per kalimat.

#### Output `get_chunk()`
```python
{
    "chunk_index":    0,
    "chunk_total":    5,
    "chunk_title":    "Judul atau teks pertama chunk",
    "chunk_content":  "...",
    "chunk_chars":    4500,
    "has_next":       True,
    "is_complete":    False,
    "progress_percent": 20
}
```

---

### 7.4 `pdf_processor.py`

Mengekstrak teks dari file PDF dengan sistem fallback berlapis.

#### Library Hierarki
```
PyMuPDF (fitz)        ← Utama: cepat, akurasi tinggi
    └─ EasyOCR        ← Fallback jika halaman kosong (untuk PDF scan)
pdfplumber            ← Alternatif jika PyMuPDF tidak tersedia
```

#### Fungsi Utama

```python
extract_text_from_pdf(file_path, page_start=None, page_end=None) → PDFAnalysis
```

**`PDFAnalysis` (TypedDict):**
```python
{
    "text":       str,        # Teks gabungan semua halaman
    "page_count": int,        # Jumlah halaman yang diproses
    "word_count": int,        # Jumlah kata
    "script":     str,        # "arabic" | "latin" | "mixed" | "unknown"
    "warnings":   list[str]   # Peringatan per halaman (OCR error, dll.)
}
```

**Deteksi Script (`detect_script`):**
- `arabic_ratio > 0.30` → `"arabic"`
- `latin_ratio > 0.50` → `"latin"`
- `arabic_ratio > 0.10` → `"mixed"`
- Else → `"latin"`

**EasyOCR** diinisialisasi **lazy** (hanya saat dibutuhkan) untuk efisiensi memori.

---

## 8. Modul: Utils (`src/utils/`)

### 8.1 `logger.py`

Logger sederhana dengan pewarnaan ANSI per kategori.

```python
log("category", "message")
# Output: HH:MM:SS [category] message
```

| Kategori | Warna | Penggunaan |
|----------|-------|-----------|
| `gateway` | Cyan | Event server/WebSocket |
| `agent` | Green | Pemrosesan agent |  
| `llm` | Yellow | Komunikasi LLM |
| `memory` | Magenta | Operasi database |
| `tools` | White | Eksekusi tools |
| `error` | Red Bold | Error kritikal |
| `warn` | Yellow Bold | Peringatan |

---

### 8.2 `security.py` — SecurityManager

Manajemen keamanan: enkripsi data sensitif dan autentikasi gateway.

#### Alur Inisialisasi
```
initialize()
    │
    ├── Baca/Buat workspace/.kyuraa-secret (Fernet key)
    │   └── Fernet key: 32-byte URL-safe base64-encoded key
    │
    └── Generate gateway token (UUID hex 16 karakter)
        └── Simpan ke env var GATEWAY_TOKEN
```

#### Method

| Method | Keterangan |
|--------|-----------|
| `initialize()` | Setup Fernet key + gateway token |
| `encrypt(text)` | Enkripsi string → string (Fernet) |
| `decrypt(token)` | Dekripsi string Fernet → string original |
| `encrypt_dict(data)` | Enkripsi nilai `OPENROUTER_API_KEY` dan `GOOGLE_API_KEY` dalam dict |
| `decrypt_dict(data)` | Dekripsi nilai API key dalam dict (detect prefix `enc:`) |
| `get_gateway_token()` | Kembalikan token autentikasi aktif |

#### Format API Key Terenkripsi
```
"enc:{fernet_encrypted_base64_string}"
```
Hanya nilai yang belum berawalan `enc:` yang akan dienkripsi (idempotent).

#### Autentikasi Request
Semua endpoint sensitif memerlukan token di:
- Header: `X-API-Key: {token}`
- Query param: `?token={token}`

---

## 9. Workspace

Direktori `workspace/` adalah area kerja runtime yang sepenuhnya dapat dimodifikasi pengguna tanpa menyentuh source code.

### 9.1 `settings.json`

File konfigurasi utama sistem. Diperbarui via endpoint `/settings/validate-and-save`.

```json
{
    "OPENROUTER_API_KEY": "enc:...",    // API key OpenRouter (terenkripsi)
    "OPENROUTER_MODEL":   "z-ai/...",  // Nama model OpenRouter
    "ACTIVE_PROVIDER":    "google",    // Provider aktif: "google" | "openrouter"
    "AGENT_MODEL":        "gemini-...", // Nama model aktif (alias)
    "GOOGLE_API_KEY":     "enc:...",   // API key Google (terenkripsi)
    "GOOGLE_MODEL":       "gemini-...", // Nama model Google
    "TOOLS_STATE": {                   // Status enabled/disabled per tool
        "detect_language":   false,
        "read_file":         true,
        "write_file":        true,
        ...
    },
    "active_skill": null               // Nama skill aktif atau null
}
```

### 9.2 Database

| File | Berisi |
|------|--------|
| `workspace/memory/sessions.db` | Sesi dan riwayat pesan |
| `workspace/memory/usage.db` | Log penggunaan token |
| `workspace/glossary/glossary.json` | Kamus istilah Arab-Indonesia |

### 9.3 Output & Upload

| Folder | Berisi |
|--------|--------|
| `workspace/output/` | Hasil terjemahan yang disimpan AI |
| `workspace/tempat_baca/uploaded_pdfs/` | File PDF yang diunggah pengguna |

---

## 10. Sistem Skills

Skills adalah paket instruksi yang mengubah kepribadian dan kemampuan AI.

### Struktur Folder Skill
```
workspace/skills/
└── nama-skill/               # Nama folder = identitas skill
    ├── SKILL.md              # File instruksi utama (wajib)
    └── references/           # Folder referensi (opsional)
        ├── referensi-a.md    # Referensi always_load
        └── referensi-b.md    # Referensi on_demand
```

### Format `SKILL.md`
```markdown
---
name: nama-skill
version: "2.0.0"
author: Nama Pembuat
category: Kategori
description: >
  Deskripsi satu/dua kalimat.
trigger_keywords:
  - kata-pemicu
references:
  always_load:
    - referensi-wajib.md
  on_demand:
    - referensi-opsional.md
---

# Instruksi untuk AI
[Semua teks di bawah frontmatter akan dimuat sebagai system prompt]
```

### Mekanisme Loading Referensi
- **`always_load`**: Dimuat setiap kali ada request (kecuali salam singkat < 20 karakter).
- **`on_demand`**: Dimuat untuk request substantif (bukan salam/kata pendek).
- File dicari di: `{skill_folder}/references/{nama}`, `{skill_folder}/references/{nama}.md`, `{skill_folder}/{nama}`, `{skill_folder}/{nama}.md`.

### Skill Bawaan: `penerjemah-arab-indo`

| Atribut | Nilai |
|---------|-------|
| Versi | 2.0.0 |
| Author | Muh Aprizal |
| Fungsi | Terjemah dua arah Indonesia-Arab untuk karya ilmiah |

**Referensi always_load:**
- `05-akademik.md` — Kosakata & frasa transisi akademik
- `06-kolokasi.md` — Kolokasi Arab akademik

**Referensi on_demand:**
- `01-nahwu.md` — Ilmu tata bahasa Arab (nahwu)
- `02-sharaf.md` — Ilmu morfologi Arab (sharaf)
- `03-balaghah.md` — Ilmu retorika Arab (balaghah)
- `04-special-cases.md` — Kasus-kasus khusus terjemahan
- `00-bahasa-indonesia.md` — Panduan bahasa Indonesia formal
- `examples.md` — Contoh output lengkap
- `quick-ref.md` — Panduan referensi cepat

**Mode Output:**
| Mode | Isi |
|------|-----|
| `linguistic` | Terjemahan + analisis gramatikal lengkap (default) |
| `default` | Terjemahan + poin kritis |
| `translation-only` | Hanya hasil terjemahan |

---

## 11. Sistem Custom Tools

Pengguna dapat menambahkan tools Python sendiri ke `workspace/tools/`.

### Format Custom Tool
```python
# name:        nama-tool-saya
# description: Deskripsi singkat fungsi tool ini
# version:     1.0
# author:      Nama Pembuat

def run(**kwargs) -> str | dict:
    """
    Implementasi tool.
    
    Args:
        param (str): Parameter yang diterima dari AI
    Returns:
        str | dict: Hasil yang dikembalikan ke AI
    """
    param = kwargs.get("param", "")
    return f"Hasil: {param}"
```

### Cara Menggunakan
1. Buat file `.py` di `workspace/tools/`.
2. Ikuti format di atas (metadata header + fungsi `run()`).
3. Buka Settings UI → tab Tools → klik **"↺ Reload"**.
4. Toggle ON tool yang baru muncul di daftar.
5. AI dapat memanggil tool dengan: `[TOOL: nama-tool-saya] param="nilai"`

### Contoh Custom Tool (`word-counter.py`)
```python
# name:        word-counter
# description: Menghitung jumlah kata dan karakter dalam teks
# version:     1.0
# author:      Kyuraa

def run(teks: str) -> str:
    words = len(teks.strip().split())
    chars = len(teks)
    sentences = teks.count('.') + teks.count('!') + teks.count('?')
    return (
        f"📊 Statistik Teks:\n"
        f"- Kata     : {words}\n"
        f"- Karakter : {chars}\n"
        f"- Kalimat  : {sentences or 1}"
    )
```

### Sandbox Keamanan Custom Tools
Tool yang mengandung pola berbahaya (lihat bagian ToolLoader) akan otomatis **DITOLAK** saat dimuat dan tidak akan pernah terdaftar di sistem.

---

## 12. Keamanan

### 12.1 Autentikasi Gateway

Semua endpoint sensitif dilindungi token 16-karakter hexadecimal yang di-generate saat startup:
```
GATEWAY_TOKEN: abc123def456789a  (contoh)
```
Token ditampilkan di banner terminal saat server pertama kali berjalan.

### 12.2 Enkripsi Data Sensitif

API key disimpan terenkripsi di `settings.json` menggunakan **Fernet** (symmetric encryption):
- Kunci enkripsi master disimpan di `workspace/.kyuraa-secret`.
- Format: `"enc:{base64_encrypted}"`.
- API key hanya didekripsi saat diperlukan di memory, tidak pernah dikembalikan ke klien secara plaintext.

### 12.3 Path Sandboxing

Semua operasi file hanya diizinkan di dalam `workspace/`:
```python
ALLOWED_PATHS = [str(Path.cwd() / "workspace")]
```
Percobaan akses di luar path ini akan menghasilkan `PermissionError`.

### 12.4 Static Code Analysis untuk Custom Tools

Sebelum tool Python di-load, source code-nya di-scan menggunakan regex untuk mendeteksi pola berbahaya. Tool yang mengandung pola tersebut langsung ditolak.

### 12.5 WebSocket Authentication

Koneksi WebSocket memerlukan `?token={gateway_token}` di URL. Jika token salah, koneksi ditutup dengan kode `4001`.

### 12.6 Single Instance Lock

File PID lock mencegah pengulangan instance server. Jika server baru dijalankan sementara yang lama masih berjalan, proses lama di-terminate secara graceful.

---

## 13. API Endpoints

### Publik (Tanpa Auth)

| Method | Path | Fungsi |
|--------|------|--------|
| GET | `/` | Halaman chat (index.html) |
| GET | `/settings-page` | Halaman pengaturan (settings.html) |
| GET | `/health` | Status server: `{status, sessions}` |
| GET | `/info` | Info model & provider aktif |
| GET | `/sessions/{id}/messages` | Pesan dalam sesi |
| DELETE | `/sessions/{id}/messages/last` | Hapus pesan user terakhir |
| PATCH | `/sessions/{id}/name` | Ubah nama sesi |
| DELETE | `/sessions/cleanup` | Hapus sesi kosong |
| GET | `/files` | Daftar file di output/ |
| WS | `/ws/{session_id}?token=` | WebSocket chat |

### Memerlukan Auth (`X-API-Key` / `?token=`)

| Method | Path | Fungsi |
|--------|------|--------|
| GET | `/settings` | Lihat konfigurasi saat ini |
| POST | `/settings/validate-and-save` | Simpan konfigurasi baru |
| GET | `/sessions` | Daftar semua sesi |
| POST | `/sessions/{id}/connected` | Buat sesi lanjutan dengan ringkasan |
| DELETE | `/sessions/{id}` | Hapus sesi beserta file upload-nya |
| POST | `/upload` | Upload PDF |
| POST | `/upload/partial` | Ekstrak halaman tertentu dari PDF |
| GET | `/upload/{file_id}` | Unduh file PDF |
| DELETE | `/upload/{file_id}` | Hapus file PDF |
| GET | `/skills` | Daftar skills + status |
| POST | `/skills/{name}/activate` | Aktifkan skill |
| POST | `/skills/deactivate` | Nonaktifkan skill |
| GET | `/tools` | Daftar tools + status |
| POST | `/tools/{name}/toggle` | Enable/disable tool |
| GET | `/stats` | Total penggunaan token |
| GET | `/stats/history?days=7` | Penggunaan per hari |
| GET | `/stats/by-model` | Penggunaan per model |
| POST | `/stats/clear-models` | Hapus log model tertentu |

---

## 14. Alur Kerja Sistem

### 14.1 Startup Server
```
run.bat
  │
  ├── Bebaskan port 8766 (taskkill)
  └── uvicorn src.gateway.server:app --host 127.0.0.1 --port 8766 --reload
        │
        ├── load_system_env()
        │   ├── SecurityManager.initialize()  → buat/baca Fernet key + gateway token
        │   ├── Baca settings.json → decrypt API keys → set env vars
        │   └── Baca .env → set env vars (hanya yang belum ada)
        │
        ├── GatewayServer.__init__()
        │   ├── Cek port tersedia
        │   ├── Tulis PID lock
        │   ├── Mount static files
        │   ├── Setup routes (4 router)
        │   └── Init system AgentLoop → SkillManager.discover() → print banner
        │
        └── uvicorn start listening on :8766
```

### 14.2 Alur Chat (WebSocket)
```
Browser → WebSocket connect /ws/{session_id}?token=xxx
Server  → Validasi token → accept()
        → AgentLoop(session_id) dibuat

Browser → send: {type: "message", content: "Terjemahkan ini...", file_context: {...}}

Server (AgentLoop.run_stream()):
  1. detect_language + detect_style
  2. SessionStore.add_message(user)
  3. SessionStore.get_history(limit=20)
  4. detect_needed_references → load references dari disk
  5. PromptBuilder.build_system_with_references()
  6. PromptBuilder.build_messages()
  7. LLMClient.stream() → yield token per token
  
Server → send: {type: "token", content: "token..."} × N
       → (jika ada tool call sensitif)
       → send: {type: "approval_request", tool: "...", params: {...}}
Browser→ send: {type: "approval_response", approved: true}
       → eksekusi tool
       
Server → UsageStore.log_usage()
       → send: {type: "done", usage: {...}, tool_results: [...]}
```

### 14.3 Alur Upload PDF
```
Browser → POST /upload (multipart/form-data, file=...)
Server:
  1. Validasi token + ekstensi (.pdf) + ukuran (≤5MB)
  2. Simpan ke workspace/tempat_baca/uploaded_pdfs/{uuid}_{nama}.pdf
  3. extract_text_from_pdf() → PyMuPDF → EasyOCR (jika halaman kosong)
  4. estimate_tokens(text) → peringatan jika > 25.000 token
  5. Return: {file_id, page_count, word_count, script, text, estimated_tokens, warnings}

Browser → kirim pesan chat dengan file_context = {file_id, filename, text, script}
```

### 14.4 Alur Aktivasi Skill
```
Browser (Settings) → POST /skills/{nama}/activate
Server:
  1. Validasi token
  2. SkillManager.activate(nama)
     ├── Cek skill ada di available_skills
     ├── Baca SKILL.md → simpan ke active_skill_content
     └── Simpan active_skill ke settings.json
  3. Sinkronisasi aktivasi ke semua AgentLoop aktif
  4. Return: {success: true}
```

---

## 15. Konfigurasi & Lingkungan

### File `.env` (Konfigurasi Awal)
```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=qwen/qwen3-8b:free
GOOGLE_API_KEY=AIzaSy...
GOOGLE_MODEL=gemini-2.0-flash
ACTIVE_PROVIDER=google
GATEWAY_HOST=localhost
GATEWAY_PORT=8766
```

> ⚠️ File `.env` adalah konfigurasi default. Setelah pertama kali setup via UI, nilai disimpan (terenkripsi) di `workspace/settings.json` dan file `.env` tidak lagi digunakan untuk API key.

### Environment Variables

| Variable | Default | Keterangan |
|----------|---------|-----------|
| `ACTIVE_PROVIDER` | `google` | Provider LLM aktif |
| `GOOGLE_API_KEY` | — | Google AI Studio API key |
| `GOOGLE_MODEL` | `gemini-2.0-flash` | Model Google yang digunakan |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `OPENROUTER_MODEL` | `qwen/qwen2.5-72b-instruct` | Model OpenRouter |
| `GATEWAY_PORT` | `8766` | Port server |
| `GATEWAY_HOST` | `localhost` | Host server |
| `GATEWAY_TOKEN` | (auto-generated) | Token autentikasi |
| `KYURAA_TEST_MODE` | — | Set ke `"1"` saat testing (skip PID lock) |

### Prioritas Konfigurasi
```
settings.json (terenkripsi) > .env > default hardcoded
```

---

## 16. Instalasi & Menjalankan Proyek

### Prasyarat
- Python 3.10 atau lebih baru
- Windows (run.bat), atau Linux/Mac (jalankan manual)

### Langkah Instalasi

```bash
# 1. Clone atau masuk ke direktori proyek
cd D:\PROJECT_APP\Kyuraa

# 2. Buat virtual environment
python -m venv venv

# 3. Aktifkan virtual environment
venv\Scripts\activate        # Windows
# atau: source venv/bin/activate  # Linux/Mac

# 4. Install dependensi
pip install -r requirements.txt

# 5. Konfigurasi API key
# Salin dan edit file .env
# Isi GOOGLE_API_KEY atau OPENROUTER_API_KEY
```

### Menjalankan Server

**Via run.bat (Windows, direkomendasikan):**
```
Double-click run.bat
```

**Manual:**
```bash
cd D:\PROJECT_APP\Kyuraa
venv\Scripts\activate
uvicorn src.gateway.server:app --host 127.0.0.1 --port 8766 --reload
```

### Akses UI
Buka browser → `http://127.0.0.1:8766`

### Banner Startup
```
   __                        
  / /_____  __ _________ ____
 /  '_/ / / / / __/ _  / _  /
/_/\_\_, / /_/ / /\_,_/\_,_/ 
     /___/  v1.0.3

─────────────────────────────────────────
STATUS: ONLINE
SKILLS: 1 Active
URL   : http://127.0.0.1:8766
TOKEN : abc123def456789a
─────────────────────────────────────────
```

> **Penting:** Salin TOKEN dari banner. Token ini dibutuhkan untuk semua akses via API.

---

## 17. Testing

### Menjalankan Test

```bash
# Semua test
pytest tests/ -v

# Test spesifik
pytest tests/test_memory.py -v
pytest tests/test_e2e.py -v
pytest tests/test_tools.py -v
```

### Deskripsi Test

| File | Kelas/Fungsi | Yang Diuji |
|------|-------------|-----------|
| `test_memory.py` | `TestSessionStore` | create session, add message, get history, delete last message |
| `test_memory.py` | `TestGlossaryStore` | add term, lookup Arab/Indonesia, export text |
| `test_e2e.py` | `TestE2E` | Auth gagal (401), auth sukses (200), flow terjemahan, WebSocket reconnect |
| `test_security_boundaries.py` | — | Path traversal, akses di luar workspace |
| `test_tools.py` | — | Built-in tools, ToolRegistry execute |
| `test_skill_manager.py` | — | discover, activate, deactivate |
| `test_llm_connection.py` | — | Koneksi ke LLM provider |

### Mode Testing
Test E2E menggunakan env var khusus:
```python
KYURAA_TEST_MODE = "1"   # Skip PID lock
GATEWAY_TOKEN = "test-token-12345"  # Token tetap untuk test
```
Server dijalankan di port `8780` (beda dari port produksi `8766`).

---

## 18. Dependensi

### Dependensi Utama

| Package | Versi | Kegunaan |
|---------|-------|----------|
| `openai` | 1.13.3 | Client OpenAI-compatible API (Google + OpenRouter) |
| `fastapi` | 0.111.0 | Framework web gateway |
| `uvicorn[standard]` | 0.29.0 | ASGI server production |
| `websockets` | 12.0 | Dukungan WebSocket |
| `python-multipart` | 0.0.9 | Parsing form upload file |
| `pyyaml` | 6.0.1 | Parsing frontmatter SKILL.md |
| `python-frontmatter` | 1.1.0 | Parse YAML frontmatter Markdown |
| `python-dotenv` | 1.0.1 | Load variabel dari `.env` |
| `pdfplumber` | 0.11.0 | Ekstrak teks dari PDF |
| `PyMuPDF` | 1.24.1 | Render PDF ke gambar untuk OCR |
| `easyocr` | 1.7.1 | OCR lokal multilingual (Arab + Inggris) |
| `aiofiles` | 23.2.1 | Async file I/O |
| `psutil` | 5.9.8 | Monitoring proses (PID lock) |
| `python-docx` | 1.1.0 | Buat/baca file Word .docx |
| `chardet` | 5.2.0 | Deteksi encoding file |
| `cryptography` | 42.0.5 | Enkripsi Fernet |
| `pytest` | 8.1.1 | Framework testing |
| `pytest-asyncio` | 0.23.5 | Dukungan test async |

---

## Catatan Pengembangan

### Menambah Skill Baru
1. Buat folder di `workspace/skills/nama-skill-baru/`.
2. Buat `SKILL.md` dengan YAML frontmatter sesuai template.
3. Tambahkan file referensi di subfolder `references/` (opsional).
4. Buka Settings UI → Skills → klik **Refresh** → aktifkan skill.

### Menambah Custom Tool
1. Buat file `.py` di `workspace/tools/`.
2. Ikuti format template: header metadata + fungsi `run(**kwargs)`.
3. Buka Settings UI → Tools → klik **↺ Reload** → toggle ON.

### Menambah Built-in Tool
Edit `src/tools/registry.py`:
1. Tambahkan implementasi method di class `ToolRegistry`.
2. Daftarkan di `_register_builtin_tools()` dengan `(name, func, description)`.

### Menambah Provider LLM Baru
Edit `src/agent/llm_client.py`:
1. Tambahkan kondisi baru di `__init__()`.
2. Set `_api_key`, `_model_name`, `_base_url` sesuai provider.
3. Provider harus kompatibel dengan OpenAI API format.

---

*Dokumentasi ini dibuat berdasarkan analisis lengkap source code Kyuraa v1.0.3.*  
*Dihasilkan pada: 15 April 2026*
