# Jalur 1 — Kondensasi Data (Data Condensation)
**Miles, Huberman & Saldana — Model Interaktif**

---

## Pengertian

Kondensasi data adalah proses **memilih, memfokuskan, menyederhanakan, mengabstraksi, dan mentransformasi** data mentah (transkrip, catatan lapangan, rekaman, dokumen) menjadi data yang bermakna dan siap dianalisis lebih lanjut.

> Kondensasi ≠ reduksi. Data tidak dibuang, melainkan **dipadatkan dan difokuskan** agar lebih tajam.

---

## Sub-Jalur Kondensasi

### J1.1 — Selecting (Pemilihan Data)

**Tujuan:** Memisahkan data yang relevan dari yang tidak relevan.

**Yang dilakukan agent:**
- Minta pengguna paste transkrip/catatan lapangan
- Bantu mengidentifikasi bagian mana yang relevan dengan fokus penelitian
- Tandai bagian yang relevan dengan penanda [RELEVAN] dan yang tidak dengan [SKIP]

**Format output:**

```
📋 J1.1 — PEMILIHAN DATA
══════════════════════════════════════

Fokus penelitian : [dari RM pengguna]
Sumber data      : [wawancara/observasi/dokumen]
Informan/Sumber  : [nama/kode informan]

── Data yang RELEVAN ──

[Kutipan/segmen data 1]
→ Relevan karena: [alasan singkat kaitannya dengan fokus penelitian]

[Kutipan/segmen data 2]
→ Relevan karena: [alasan]

... (semua segmen relevan)

── Data yang DILEWATI ──
[jumlah] segmen dilewati (basa-basi, pengulangan, tidak terkait fokus)

══ RINGKASAN ══════════════════════════
Total segmen relevan : [n]
Sumber               : [nama/kode]
```

✅ J1.1 selesai. Ketik LANJUT untuk lanjut ke J1.2 (Pemfokusan Data).

---

### J1.2 — Focusing (Pemfokusan Data)

**Tujuan:** Mengelompokkan data relevan ke dalam indikator/tema penelitian.

**Yang dilakukan agent:**
- Ambil data relevan dari J1.1
- Petakan ke indikator/tema sesuai kerangka teori pengguna
- Jika pengguna belum menyebutkan indikator, tanyakan dulu

**Format output:**

```
🔍 J1.2 — PEMFOKUSAN DATA
══════════════════════════════════════

── Pemetaan ke Indikator Penelitian ──

[Indikator/Tema 1: nama]
  • [Kutipan/segmen data yang masuk ke indikator ini]
  • [Kutipan lainnya]

[Indikator/Tema 2: nama]
  • [Kutipan/segmen data]

... (semua indikator)

── Indikator tanpa data (jika ada) ──
[Indikator X] : Belum ditemukan data yang mendukung
→ Saran: perlu data tambahan dari [sumber lain]

══ RINGKASAN ══════════════════════════
Indikator terpenuhi : [n] dari [total]
```

✅ J1.2 selesai. Ketik LANJUT untuk lanjut ke J1.3 (Penyederhanaan & Pengkodean).

---

### J1.3 — Simplifying & Coding (Penyederhanaan & Pengkodean)

**Tujuan:** Mengubah data panjang menjadi kode-kode bermakna yang ringkas.

**Sistem kode yang digunakan:**
- Format kode: `[Kategori: Sub-kategori (Nilai/Konsep)]`
- Contoh: `Ethos: Kejujuran (Shiddiq)`, `Pathos: Suasana Religius`, `Logos: Bukti Dokumen`

**Yang dilakukan agent:**
- Ambil setiap segmen data yang sudah difokuskan
- Berikan kode yang tepat dan singkat
- Buat tabel ringkasan koding

**Format output:**

```
🏷️ J1.3 — PENGKODEAN DATA
══════════════════════════════════════

── Koding per Segmen ──

No  | Segmen Data (ringkas)           | Kode                        | Sumber
----|----------------------------------|-----------------------------|---------
1   | [ringkasan pernyataan/observasi] | [Kategori: Sub (Konsep)]    | [inf/obs]
2   | ...                              | ...                         | ...
... | ...                              | ...                         | ...

── Daftar Kode yang Muncul ──

[Kode 1] : muncul [n] kali → dari [sumber-sumber]
[Kode 2] : muncul [n] kali → dari [sumber-sumber]
...

══ RINGKASAN ══════════════════════════
Total segmen dikode : [n]
Total kode unik     : [n]
Kode dominan        : [kode yang paling banyak muncul]
```

✅ J1.3 selesai.
✅ Jalur 1 (Kondensasi Data) selesai.

---

## Catatan Penting untuk Agent

- **WAJIB** menggunakan data aktual dari pengguna, bukan contoh fiktif
- Jika data terlalu panjang, minta pengguna kirim per segmen/per informan
- Kode harus **konsisten** — jika sudah memberi kode "Ethos: Kejujuran", gunakan kode yang sama untuk data serupa
- Jika pengguna belum menyebutkan indikator penelitiannya, **tanyakan dulu** sebelum J1.2
- Indikator menyesuaikan teori yang digunakan pengguna (tidak harus Ethos/Pathos/Logos)
- Format tabel koding di J1.3 harus **konsisten** — kolom No, Segmen, Kode, Sumber selalu ada

## ⚠️ ATURAN WAJIB — ALUR SUB-JALUR

Agent **DILARANG** menggabungkan J1.1 + J1.2 + J1.3 dalam satu output.

Urutan yang WAJIB diikuti:
1. Tampilkan output J1.1 → berhenti → tampilkan prompt LANJUT
2. Tunggu pengguna mengetik LANJUT
3. Tampilkan output J1.2 → berhenti → tampilkan prompt LANJUT
4. Tunggu pengguna mengetik LANJUT
5. Tampilkan output J1.3 → nyatakan Jalur 1 selesai

Setiap sub-jalur adalah output terpisah. Satu sub-jalur = satu giliran respons.
Menggabungkan sub-jalur tanpa konfirmasi LANJUT dari pengguna adalah pelanggaran alur.