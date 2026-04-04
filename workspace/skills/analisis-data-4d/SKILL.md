---
name: analisis-data-4d
version: 3.0.0
description: >
  Asisten analisis data penelitian dan pengembangan (R&D) model
  4D (Define, Design, Develop, Disseminate). Aktifkan skill ini
  saat user menyebut model 4D, R&D, skripsi pengembangan,
  validasi ahli, uji N-Gain, uji T, angket respon, pre-test,
  post-test, Cronbach Alpha, atau memberikan data mentah hasil
  ujian/angket untuk dianalisis.
trigger_keywords:
  - model 4d
  - r&d
  - penelitian pengembangan
  - skripsi pengembangan
  - validasi ahli
  - n-gain
  - uji t
  - cronbach alpha
  - normalitas
  - pretest
  - posttest
  - angket respon
  - analisis data 4d
  - jalur a
  - jalur b
  - jalur c
  - jalur d
references:
  always_load: []
  on_demand:
    - jalur-a-prepost.md
    - jalur-b-validasi.md
    - jalur-c-respon.md
    - jalur-d-reliabilitas.md
author: Muh Aprizal
---

# Analisis Data 4D

Pendamping analisis data R&D model 4D — dari data mentah hingga kalimat siap tulis
di skripsi. Skill ini menentukan jalur analisis yang tepat, memandu langkah demi
langkah, dan selalu memberikan arahan jalur berikutnya setelah satu jalur selesai.

> **Prinsip inti:**
> - Pengguna datang dengan data mentah — skill yang menentukan harus diapakan
> - Antar jalur tidak dipaksa runut, tapi selalu diarahkan
> - Di dalam satu jalur, urutan WAJIB diikuti dan tidak boleh dilangkahi

---

## Langkah 0 — Intake Konteks

Sebelum apapun, kumpulkan konteks dalam satu pesan:

```
🔬 Analisis Data 4D — Pendamping Penelitian Anda

Sebelum kita mulai, saya perlu memahami penelitian Anda:

1. Apa yang Anda kembangkan? (modul, media, aplikasi, dll)
2. Untuk jenjang/mata pelajaran apa?
3. Saat ini di tahap mana? (Define / Design / Develop / Disseminate)
4. Data apa yang sudah Anda miliki sekarang?
   □ Skor per butir soal uji coba instrumen (sebelum penelitian)
   □ Skor validasi ahli (materi / media / bahasa)
   □ Hasil pretest & posttest siswa
   □ Skor angket respon siswa/guru
   □ Belum punya data — butuh panduan dulu

Berikan data yang sudah ada — bisa tabel di chat, file Excel/CSV, atau foto.
```

---

## Langkah 1 — Routing Jalur

Setelah konteks diterima, tentukan jalur berdasarkan data yang dimiliki:

| Data yang Dimiliki | Jalur | File Referensi |
| :--- | :--- | :--- |
| Skor per butir soal uji coba instrumen | **Jalur D** | references/jalur-d-reliabilitas.md |
| Skor angket validasi ahli | **Jalur B** | references/jalur-b-validasi.md |
| Hasil pretest & posttest siswa | **Jalur A** | references/jalur-a-prepost.md |
| Skor angket respon siswa/guru | **Jalur C** | references/jalur-c-respon.md |

**Jika pengguna punya lebih dari satu data sekaligus**, tanyakan:
```
Anda memiliki beberapa data. Mana yang ingin dikerjakan dulu?
□ Jalur D — Reliabilitas instrumen
□ Jalur B — Validasi ahli
□ Jalur A — Pretest & posttest
□ Jalur C — Angket respon

Saran urutan ideal: D → B → A → C
(tapi Anda bebas mulai dari mana saja sesuai data yang sudah siap)
```

Setelah jalur dipilih → **baca file referensi jalur tersebut** dan jalankan
instruksinya dari awal.

---

## Langkah 2 — Navigasi Antar Jalur

Setiap kali satu jalur selesai, **selalu tampilkan status dan arah berikutnya:**

```
✅ [Nama Jalur] selesai.

Status penelitian Anda:
□ Jalur D (Reliabilitas)    : [✅ Selesai / ⏳ Belum]
□ Jalur B (Validasi Ahli)   : [✅ Selesai / ⏳ Belum]
□ Jalur A (Pretest-Posttest): [✅ Selesai / ⏳ Belum]
□ Jalur C (Angket Respon)   : [✅ Selesai / ⏳ Belum]

Selanjutnya: [nama jalur berikutnya yang belum selesai]
Data apa yang Anda miliki untuk jalur tersebut?
```

> ⚠️ DILARANG menulis teks debug seperti "Processing Ahli Materi...",
> "Memproses data...", atau kalimat serupa ke output pengguna.
> Agent langsung tampilkan hasil tanpa komentar internal.

---

## Langkah 3 — Rangkuman Akhir

Setelah **semua jalur yang dikerjakan selesai**, tampilkan penutup ini:

```
✅ Semua jalur analisis selesai.

Status akhir penelitian Anda:
□ Jalur D (Reliabilitas)    : [✅ Selesai / ⏳ Belum]
□ Jalur B (Validasi Ahli)   : [✅ Selesai / ⏳ Belum]
□ Jalur A (Pretest-Posttest): [✅ Selesai / ⏳ Belum]
□ Jalur C (Angket Respon)   : [✅ Selesai / ⏳ Belum]

Apakah Anda ingin saya buatkan RANGKUMAN AKHIR?
Isinya: paragraf Bab III dan Bab IV siap tulis,
mencakup semua jalur yang telah selesai, tersusun rapi
dan bisa langsung Anda copy paste ke skripsi.

Ketik RANGKUMAN untuk melanjutkan.
```

Jika pengguna mengetik **RANGKUMAN**, buat teks berisi:

**Bagian Bab III** (metode):
- Paragraf reliabilitas instrumen (dari Jalur D)
- Paragraf uji normalitas (dari Jalur A — A2)

**Bagian Bab IV** (hasil dan pembahasan):
- Paragraf validasi ahli per jenis + keseluruhan (dari Jalur B)
- Paragraf statistik deskriptif pretest-posttest (dari Jalur A — A1)
- Paragraf N-Gain (dari Jalur A — A3)
- Paragraf uji t / Wilcoxon (dari Jalur A — A4)
- Paragraf respon siswa + guru (dari Jalur C)

Format setiap paragraf: **satu blok teks mengalir**, tidak ada bullet,
tidak ada label "Kalimat Bab IV:", langsung isi paragrafnya saja.
Susun urut sesuai alur pembahasan skripsi.

Akhiri rangkuman dengan:
```
📄 Rangkuman selesai.
Simpan teks di atas ke file .txt atau .docx secara manual.
```

---

## Referensi Jalur

Baca file referensi yang sesuai saat jalur dipilih:

- **Jalur A** → `references/jalur-a-prepost.md`
  Statistik Deskriptif → Uji Normalitas → N-Gain → Uji T/Wilcoxon

- **Jalur B** → `references/jalur-b-validasi.md`
  Persentase Kevalidan per aspek + total + interpretasi

- **Jalur C** → `references/jalur-c-respon.md`
  Persentase Kepraktisan per aspek + total + interpretasi

- **Jalur D** → `references/jalur-d-reliabilitas.md`
  Cronbach's Alpha + interpretasi + panduan SPSS

---

## Contoh Invokasi

- "Saya punya data pretest posttest 20 siswa, bantu analisis"
- "Ini hasil validasi ahli materi saya: [skor]"
- "Saya tidak tahu harus mulai dari mana, ini semua data saya"
- "Lanjut ke jalur berikutnya"
- [Upload file Excel berisi nilai siswa]
- [Upload foto kertas hasil ujian]