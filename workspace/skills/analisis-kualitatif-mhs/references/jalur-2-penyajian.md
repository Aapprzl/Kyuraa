# Jalur 2 — Penyajian Data (Data Display)
**Miles, Huberman & Saldana — Model Interaktif**

---

## Pengertian

Penyajian data adalah proses **menyusun dan mengorganisasi informasi** yang sudah dikondensasi agar mudah dipahami dan memungkinkan penarikan kesimpulan. Penyajian dapat berupa teks naratif, tabel/matriks, atau diagram alur.

---

## Sub-Jalur Penyajian

### J2.1 — Teks Naratif

**Tujuan:** Menyusun temuan menjadi narasi deskriptif yang kaya dan akademik.

**Yang dilakukan agent:**
- Ambil hasil koding dari Jalur 1 (atau data yang diberikan pengguna)
- Susun per tema/indikator dalam bentuk paragraf naratif
- Hubungkan data dari berbagai sumber (wawancara + observasi + dokumen)
- Sertakan kutipan langsung dari informan sebagai penguat (dalam tanda petik)

**Format output:**

```
📝 J2.1 — TEKS NARATIF
══════════════════════════════════════

── [Tema/Indikator 1: nama] ──

[Paragraf naratif yang mendeskripsikan temuan pada tema ini.
Menggabungkan data dari wawancara, observasi, dan dokumen.
Sertakan kutipan langsung: "...[pernyataan informan]..." (Informan X, dd/mm/yyyy).
Hubungkan dengan konteks penelitian.]

── [Tema/Indikator 2: nama] ──

[Paragraf naratif tema 2...]

... (semua tema)

══ CATATAN ════════════════════════════
Narasi di atas dapat langsung digunakan sebagai draft sub-bab
"Hasil Penelitian" pada Bab IV skripsi/tesis Anda.
```

✅ J2.1 selesai. Ketik LANJUT untuk lanjut ke J2.2 (Tabel/Matriks).

---

### J2.2 — Tabel / Matriks Perbandingan (Opsional tapi Dianjurkan)

**Tujuan:** Mempermudah pembaca melihat pola lintas sumber/informan secara visual.

**Yang dilakukan agent:**
- Buat tabel dengan kolom: Elemen/Indikator | Data Sumber 1 | Data Sumber 2 | Data Sumber 3
- Sumber disesuaikan dengan jenis data pengguna (misal: Wawancara Pemilik | Wawancara Konsumen | Observasi)
- Isi sel tabel dengan ringkasan temuan (bukan kutipan panjang)

**Format output:**

```
📊 J2.2 — TABEL/MATRIKS PERBANDINGAN
══════════════════════════════════════

Elemen/Indikator | [Sumber 1]           | [Sumber 2]           | [Sumber 3/Observasi]
-----------------|----------------------|----------------------|----------------------
[Indikator 1]    | [temuan dari S1]     | [temuan dari S2]     | [temuan dari obs]
[Indikator 2]    | [temuan dari S1]     | [temuan dari S2]     | [temuan dari obs]
[Indikator 3]    | [temuan dari S1]     | [temuan dari S2]     | [temuan dari obs]
...              | ...                  | ...                  | ...

══ INTERPRETASI TABEL ════════════════
[Paragraf singkat menjelaskan pola yang terlihat dari tabel:
apakah data dari berbagai sumber saling mendukung, bertentangan,
atau melengkapi satu sama lain]
```

✅ J2.2 selesai. Ketik LANJUT untuk lanjut ke J2.3 (Diagram Alur) atau ketik SKIP untuk lewati.

---

### J2.3 — Diagram Alur / Peta Konsep (Opsional)

**Tujuan:** Menggambarkan hubungan antar tema/elemen secara visual dalam bentuk teks.

**Yang dilakukan agent:**
- Buat representasi teks dari hubungan antar elemen
- Gunakan format ASCII sederhana yang mudah dibaca
- Jelaskan arah hubungan (menyebabkan, mendukung, bertentangan)

**Format output:**

```
🔗 J2.3 — DIAGRAM HUBUNGAN ANTAR ELEMEN
══════════════════════════════════════

[Elemen A]
    │
    ▼ [menyebabkan/mendukung]
[Elemen B] ──────────────────► [Elemen C]
    │                               │
    ▼ [memperkuat]                  ▼ [menghasilkan]
[Elemen D]                     [Elemen E]

Keterangan:
→ [Elemen A] ke [Elemen B]: [penjelasan hubungan]
→ [Elemen B] ke [Elemen C]: [penjelasan hubungan]
... dst
```

✅ J2.3 selesai.
✅ Jalur 2 (Penyajian Data) selesai.

---

## Catatan Penting untuk Agent

- **Teks naratif (J2.1) WAJIB** — tabel dan diagram bersifat pelengkap
- Kutipan langsung informan harus ditulis dalam **tanda petik** dan disertai identitas informan (nama/kode + tanggal jika ada)
- Narasi harus **menghubungkan** data dari berbagai sumber, bukan sekadar mendaftar
- Gunakan kalimat akademik: "Berdasarkan hasil observasi...", "Hal ini diperkuat oleh pernyataan...", "Senada dengan temuan di lapangan..."
- Jika pengguna hanya memiliki satu jenis sumber data (misal hanya wawancara), tabel tetap bisa dibuat dengan kolom per informan
- J2.2 dan J2.3 bersifat opsional — tanyakan kepada pengguna apakah ingin dibuat
