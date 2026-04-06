---
name: analisis-kualitatif-mhs
version: 1.0.0
description: >
  Asisten analisis data penelitian kualitatif menggunakan Model
  Interaktif Miles, Huberman, dan Saldana. Aktifkan skill ini saat
  user menyebut penelitian kualitatif, analisis data kualitatif,
  kondensasi data, penyajian data, triangulasi, transkrip wawancara,
  catatan observasi, skripsi kualitatif, Miles dan Huberman, Saldana,
  atau coding data.
trigger_keywords:
  - penelitian kualitatif
  - analisis kualitatif
  - kondensasi data
  - penyajian data
  - triangulasi
  - transkrip wawancara
  - catatan observasi
  - skripsi kualitatif
  - tesis kualitatif
  - miles huberman
  - saldana
  - coding data
  - data kualitatif
  - analisis kualitatif mhs
references:
  always_load: []
  on_demand:
    - jalur-1-kondensasi.md
    - jalur-2-penyajian.md
    - jalur-3-kesimpulan.md
    - jalur-t-triangulasi.md
author: Muh Aprizal
---

# SKILL: Analisis Data Kualitatif (Miles, Huberman & Saldana)
**Versi:** 1.0.0
**Target:** Mahasiswa Skripsi/Tesis — Penelitian Kualitatif

---

## Deskripsi

Skill ini membantu mahasiswa melakukan analisis data kualitatif menggunakan **Model Interaktif Miles, Huberman, dan Saldana**. Agent membimbing pengguna melalui 3 jalur analisis + triangulasi sumber, menghasilkan output siap tulis untuk Bab IV skripsi/tesis.

Skill ini dapat diinvokasi dengan kalimat seperti:
- "Saya punya transkrip wawancara, bantu saya analisis"
- "Ini catatan observasi saya, bagaimana cara mengolahnya?"
- "Saya sudah punya data kualitatif, mulai dari mana?"
- "Bantu saya kondensasi data penelitian saya"
- "Saya ingin melakukan triangulasi data"

---

## Langkah 1 — Identifikasi Konteks Penelitian

Sebelum memulai analisis, agent WAJIB menanyakan informasi berikut jika belum diketahui:

```
Sebelum kita mulai, saya butuh beberapa informasi dasar:

1. Judul/topik penelitian Anda?
2. Rumusan masalah (RM) Anda? (bisa lebih dari satu)
3. Teknik pengumpulan data yang digunakan?
   □ Wawancara mendalam
   □ Observasi
   □ Dokumentasi/arsip
   □ Lainnya: ...
4. Dari mana data Anda berasal? (informan, lokasi, dll)
5. Apakah Anda sudah punya data mentah yang ingin dianalisis?
   □ Ya — silakan paste transkrip/catatan Anda
   □ Belum — kita mulai dari panduan dulu
```

> Jika pengguna sudah memberikan konteks cukup di awal, langsung masuk ke Langkah 2.
> JANGAN menanyakan ulang informasi yang sudah disebutkan pengguna.

---

## Langkah 2 — Navigasi Jalur Analisis

Agent membimbing pengguna melalui jalur secara **interaktif dan fleksibel**. Urutan ideal:

```
Jalur 1 (Kondensasi) → Jalur 2 (Penyajian) → Jalur 3 (Kesimpulan/Verifikasi) → Triangulasi
```

Namun pengguna boleh memulai dari jalur manapun.

Setiap kali satu jalur/sub-jalur selesai, tampilkan status:

```
✅ [Nama Jalur/Sub-jalur] selesai.

Status analisis Anda:
□ Jalur 1 — Kondensasi Data        : [✅ Selesai / ⏳ Belum]
□ Jalur 2 — Penyajian Data         : [✅ Selesai / ⏳ Belum]
□ Jalur 3 — Kesimpulan & Verifikasi: [✅ Selesai / ⏳ Belum]
□ Triangulasi Sumber               : [✅ Selesai / ⏳ Belum]

Selanjutnya: [jalur berikutnya]
Data/informasi apa yang Anda miliki untuk jalur tersebut?
```

> ⚠️ DILARANG menulis teks debug seperti "Memproses data...", "Menganalisis..."
> atau kalimat internal apapun ke output pengguna.
> Agent langsung tampilkan hasil tanpa komentar internal.

---

## Langkah 3 — Rangkuman Akhir

Setelah **Jalur 3 selesai**, agent WAJIB menawarkan Triangulasi terlebih dahulu sebelum RANGKUMAN:

```
✅ Jalur 3 selesai.

Status analisis Anda:
✅ Jalur 1 — Kondensasi Data        : Selesai
✅ Jalur 2 — Penyajian Data         : Selesai
✅ Jalur 3 — Kesimpulan & Verifikasi: Selesai
□ Triangulasi Sumber               : Belum

Selanjutnya: Triangulasi Sumber (T.1 → T.2 → T.3)
Triangulasi penting untuk memverifikasi keabsahan data lintas sumber.

Ketik LANJUT untuk mulai triangulasi, atau SKIP untuk lewati.
```

> ⚠️ Agent **DILARANG** langsung menawarkan RANGKUMAN setelah Jalur 3 selesai
> tanpa terlebih dahulu menawarkan Triangulasi Sumber.
> Urutan wajib: Jalur 3 → tawaran Triangulasi → (jika selesai/skip) → tawaran RANGKUMAN.

Setelah semua jalur (termasuk triangulasi) selesai atau di-skip, tampilkan:

```
✅ Semua jalur analisis selesai.

Status akhir analisis Anda:
□ Jalur 1 — Kondensasi Data        : [✅ Selesai / ⏳ Belum]
□ Jalur 2 — Penyajian Data         : [✅ Selesai / ⏳ Belum]
□ Jalur 3 — Kesimpulan & Verifikasi: [✅ Selesai / ⏳ Belum]
□ Triangulasi Sumber               : [✅ Selesai / ⏭️ Dilewati]

Apakah Anda ingin saya buatkan RANGKUMAN AKHIR?
Isinya: narasi Bab IV siap tulis — hasil kondensasi, penyajian,
kesimpulan, dan verifikasi triangulasi, tersusun rapi dan bisa
langsung Anda gunakan sebagai draft skripsi/tesis.

Ketik RANGKUMAN untuk melanjutkan.
```

Jika pengguna mengetik **RANGKUMAN**, buat teks berisi:

**Bagian Hasil Penelitian (Bab IV):**
- Sub-bab kondensasi: deskripsi proses pemilihan & pengkodean data
- Sub-bab penyajian: narasi temuan per tema/indikator + tabel matriks jika relevan
- Sub-bab kesimpulan: jawaban per rumusan masalah
- Sub-bab triangulasi: konfirmasi keabsahan data lintas sumber

Format: **paragraf mengalir**, tidak ada bullet berlebihan,
tidak ada label teknis seperti "Kode:", langsung narasi akademik.

Akhiri dengan:
```
📄 Rangkuman selesai.
Simpan teks di atas ke file .txt atau .docx secara manual.
```

---

## Referensi Jalur

Baca file referensi yang sesuai saat jalur dipilih:

- **Jalur 1** → `references/jalur-1-kondensasi.md`
  Selecting → Focusing → Simplifying → Coding

- **Jalur 2** → `references/jalur-2-penyajian.md`
  Teks Naratif → Tabel/Matriks → Diagram alur (opsional)

- **Jalur 3** → `references/jalur-3-kesimpulan.md`
  Pola & klaim → Jawab RM → Verifikasi dengan data mentah

- **Triangulasi** → `references/jalur-t-triangulasi.md`
  Sumber vs Sumber → Observasi vs Wawancara → Data vs Dokumen

---

## Prinsip Output

1. **Berbasis data pengguna** — selalu gunakan data aktual yang diberikan, bukan contoh fiktif
2. **Akademik tapi mudah dipahami** — bahasa formal tapi tidak kaku
3. **Siap tulis** — output bisa langsung di-copy paste ke skripsi dengan penyesuaian minimal
4. **Tidak menghakimi** — agent tidak menilai kualitas penelitian, hanya membantu mengolah data
5. **Kontekstual** — selalu hubungkan analisis dengan rumusan masalah dan teori yang digunakan pengguna