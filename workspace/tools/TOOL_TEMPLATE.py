"""
================================================================
KYURAA TOOL TEMPLATE — Panduan Resmi Pembuatan Tool Kustom
================================================================

Bagikan file ini ke AI manapun (ChatGPT, Claude, Gemini, dll.)
agar mereka memahami cara membuat tool untuk Kyuraa Agent.

================================================================
INSTRUKSI UNTUK AI YANG MENERIMA TEMPLATE INI:
================================================================

Kamu diminta membuat sebuah "Tool" untuk Kyuraa Agent System.
Kyuraa adalah AI Agent yang berjalan secara lokal dengan Python.

Tools adalah file Python (.py) yang memiliki struktur standar berikut:
  1. Komentar metadata di bagian atas
  2. Import library yang dibutuhkan
  3. Satu fungsi utama bernama `run(**kwargs) -> str | dict`

Cara agent memanggil tool via teks di dalam percakapan:
  [TOOL: nama-tool] param1="nilai1" param2="nilai2"

================================================================
FORMAT WAJIB — METADATA HEADER (jangan dihapus):
================================================================

# name:        nama-tool-anda        ← huruf kecil, boleh pakai dash (-)
# description: Deskripsi singkat apa yang dilakukan tool ini
# version:     1.0
# author:      Nama Pembuat

================================================================
ATURAN WAJIB (HARUS DIPATUHI):
================================================================

✅ BOLEH:
  - Fungsi utama HARUS bernama `run()` (bukan main, execute, dsb.)
  - `run()` HARUS mengembalikan string atau dict
  - Import standard library Python (math, json, re, datetime, pathlib, dll.)
  - Import library eksternal yang sudah install (`import requests`, dll.)
  - Fungsi helper tambahan di luar `run()` diperbolehkan
  - Type hints dianjurkan untuk kejelasan

❌ DILARANG KERAS:
  - os.system(...)         ← eksekusi perintah shell
  - subprocess.run(...)    ← spawn proses baru
  - shutil.rmtree(...)     ← hapus folder
  - os.remove(...) / os.unlink(...)  ← hapus file
  - eval(...) / exec(...)  ← eksekusi kode dinamis
  - __import__(...)        ← dynamic import tidak aman
  - open(..., 'w') / open(..., 'a') ← tulis file sembarangan
    (gunakan tool bawaan save_translation jika perlu simpan hasil)

  ⚠️  File tool yang mengandung pola di atas akan
      OTOMATIS DITOLAK saat dimuat oleh Kyuraa.

================================================================
CARA PENGGUNAAN SETELAH SELESAI:
================================================================

1. Simpan file ini dengan nama: nama-tool-anda.py
   Contoh: word-counter.py, currency-converter.py

2. Taruh file di dalam folder:
   workspace/tools/

3. Buka Kyuraa di browser → Settings → tab Tools

4. Klik tombol "↺ Reload" 
   → Tool baru akan muncul di list "Custom Tools"

5. Toggle ON tool tersebut agar agent bisa menggunakannya

6. Selesai! Agent bisa memanggil tool dengan:
   [TOOL: nama-tool-anda] param="nilai"

================================================================
TEMPLATE KOSONG — MULAI DARI SINI:
================================================================
"""

# name:        nama-tool-anda
# description: Deskripsi singkat apa yang dilakukan tool ini
# version:     1.0
# author:      Nama Anda

# ── Tambahkan import yang diperlukan di bawah ini ──
import json


def run(param1: str, param2: str = "nilai_default") -> str:
    """
    Deskripsi lengkap fungsi ini.

    Args:
        param1 (str): Penjelasan parameter pertama [WAJIB]
        param2 (str): Penjelasan parameter kedua [OPSIONAL]

    Returns:
        str: Penjelasan nilai yang dikembalikan.
             Boleh juga return dict jika butuh struktur data.
    """
    # ── Tulis logika tool di sini ──────────────────
    result = f"Tool berjalan: param1={param1}, param2={param2}"
    return result


# ================================================================
# CONTOH IMPLEMENTASI NYATA — Hapus bagian ini setelah dipahami
# ================================================================
#
# CONTOH 1: Word Counter (Penghitung Kata)
# ──────────────────────────────────────────
# File: workspace/tools/word-counter.py
#
# # name:        word-counter
# # description: Menghitung jumlah kata dan karakter dalam teks
# # version:     1.0
# # author:      Contoh
#
# def run(teks: str) -> str:
#     words = len(teks.strip().split())
#     chars = len(teks)
#     sentences = teks.count('.') + teks.count('!') + teks.count('?')
#     return (
#         f"📊 Statistik Teks:\n"
#         f"- Kata     : {words}\n"
#         f"- Karakter : {chars}\n"
#         f"- Kalimat  : {sentences}"
#     )
#
# ──────────────────────────────────────────
# CONTOH 2: Date Formatter
# ──────────────────────────────────────────
# File: workspace/tools/date-formatter.py
#
# # name:        date-formatter
# # description: Format tanggal ke berbagai format (Indonesia, ISO, dll.)
# # version:     1.0
# # author:      Contoh
#
# from datetime import datetime
#
# BULAN_ID = [
#     "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
#     "Juli", "Agustus", "September", "Oktober", "November", "Desember"
# ]
#
# def run(tanggal: str, format_output: str = "indonesia") -> str:
#     dt = datetime.fromisoformat(tanggal)
#     if format_output == "indonesia":
#         return f"{dt.day} {BULAN_ID[dt.month]} {dt.year}"
#     elif format_output == "iso":
#         return dt.strftime("%Y-%m-%d")
#     return str(dt)
#
# ================================================================
