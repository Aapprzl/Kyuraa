---
# ============================================================
# FRONTMATTER - Metadata Skill
# Wajib diisi! Ini adalah konfigurasi utama skill.
# ============================================================

name: template-skill          # Nama unik skill (tanpa spasi, gunakan hyphen)
version: "1.0"                # Versi skill (format: "X.Y")
description: >                # Deskripsi singkat skill (1-2 kalimat)
  Deskripsi skill di sini. Jelaskan apa yang skill ini lakukan
  dan kapan harus digunakan oleh pengguna.

# Kata kunci pemicu otomatis (trigger)
# Jika user message mengandung kata ini, skill akan disarankan
trigger_keywords:
  - contoh
  - template
  - test

# Konfigurasi referensi файлов
# always_load: referensi yang selalu dimuat saat skill aktif
# on_demand: referensi yang bisa dimuat saat dibutuhkan
references:
  always_load:                # Dipanggil di load_always_references()
    - intro.md                #akan dimuat otomatis setiap kali skill diaktifkan
    
  on_demand:                  # Dipanggil via load_reference(nama)
    - terminologi.md
    - contoh-kalimat.md

---

# ============================================================
# INSTRUKSI SKILL
# Bagian utama yang akan dimuat ke system prompt AI.
# Semua instruksi di bawah ini akan menjadi konteks AI.
# ============================================================

## Peran (Role)

<INSTRUKSI PERAN DI SINI>
Contoh: Anda adalah penerjemah akademik Arab-Indonesia...


## Aturan Terjemahan

<ATURAN KHUSUS TERJEMAHAN>
Contoh:
- Gunakan istilah akademik formal
- Pertahankan struktur kalimat asli
- Hindari kata serapan yang tidak baku


## Langkah Kerja

<PROSES/LANGKAH YANG HARUS DILAKUKAN>
Contoh:
1. Analisis teks sumber (identifikasi tema, istilah kunci)
2. Identifikasi struktur gramatikal (jenis kalimat, hubungan antar kalimat)
3. Terjemahkan dengan mempertimbangkan konteks
4. Review hasil terjemahan (cek kelengkapan, keakuratan)
5. Format output sesuai template yang ditentukan


## Terminologi Khusus

<DAFTAR ISTILAH KHUSUS>
Format: `istilah_asli -> istilah_terjemahan`

Contoh:
- علم النفس -> psikologi
- الفقه الإسلامي -> fikih Islam


## Contoh Input-Output

### Contoh 1
**Input:** <teks bahasa Arab>

**Output:** <terjemahan Indonesia>


### Contoh 2
**Input:** <teks bahasa Arab>

**Output:** <terjemahan Indonesia>


## Catatan Penting

- Jangan mengubah makna asli teks
- Konsistensi terminologi sangat penting

## Efisiensi & Kontinuitas (Penting untuk Teks Panjang)

> ⚠️ **PRINSIP DASAR:** Fokus pada hasil akhir yang berkualitas. Hindari pengulangan teks input yang terlalu panjang agar tidak menghabiskan kuota karakter (token).

**Aturan Efisiensi:**
- Jika input pengguna sangat panjang (paragraf penuh), **JANGAN** tulis ulang seluruh teks input di bagian awal jawaban. Cukup kutip ringkasannya saja.
- Jika output terhenti karena batas panjang teks, tunggu pengguna mengetik **"Lanjut"** untuk meneruskan sisa jawaban.
- Prioritaskan kelengkapan informasi utama daripada analisis tambahan yang repetitif jika kuota token menipis.


---

# ============================================================
# STRUKTUR FOLDER SKILL
# ============================================================
#
# NamaFolderSkill/
# ├── SKILL.md              <- File ini (instruksi utama)
# └── references/           <- Folder untuk file referensi
#     ├── intro.md           <- Contoh: selalu dimuat
#     ├── terminologi.md     <- Contoh: on-demand
#     └── contoh-kalimat.md  <- Contoh: on-demand
#
# Referensi di folder "references" akan dicari saat:
# - load_always_references() dipanggil (untuk always_load)
# - load_reference(nama_file) dipanggil (untuk on_demand)
#
# ============================================================
