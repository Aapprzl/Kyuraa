# Jalur 3 — Penarikan Kesimpulan & Verifikasi
**Miles, Huberman & Saldana — Model Interaktif**

---

## Pengertian

Penarikan kesimpulan adalah proses **menemukan makna, pola, penjelasan, dan proposisi** dari data yang sudah disajikan. Verifikasi adalah proses **menguji kebenaran** kesimpulan dengan kembali ke data mentah untuk memastikan tidak ada yang terlewat atau bias.

> Dalam model interaktif, kesimpulan bersifat **tentatif di awal** dan terus diverifikasi hingga benar-benar solid.

---

## Sub-Jalur Kesimpulan & Verifikasi

### J3.1 — Mencari Pola & Klaim

**Tujuan:** Mengidentifikasi pola, hubungan, dan tema dominan dari data yang sudah dikondensasi dan disajikan.

**Yang dilakukan agent:**
- Analisis kode-kode dari J1.3 dan narasi dari J2.1
- Identifikasi kode/tema yang paling sering muncul
- Identifikasi hubungan antar tema
- Temukan pola yang konsisten lintas sumber/informan

**Format output:**

```
🔍 J3.1 — POLA & KLAIM AWAL
══════════════════════════════════════

── Pola yang Ditemukan ──

Pola 1: [nama pola]
→ Ditemukan pada: [kode/tema yang mendukung]
→ Muncul di sumber: [sumber 1, sumber 2, ...]
→ Klaim awal: [pernyataan tentang pola ini]

Pola 2: [nama pola]
→ Ditemukan pada: [kode/tema]
→ Muncul di sumber: [sumber-sumber]
→ Klaim awal: [pernyataan]

... (semua pola)

── Temuan Kontradiktif (jika ada) ──
[Jika ada data yang bertentangan dengan pola utama, catat di sini]
→ [Deskripsi temuan kontradiktif]
→ Implikasi: [bagaimana ini mempengaruhi kesimpulan]

══ RINGKASAN ══════════════════════════
Total pola ditemukan   : [n]
Pola dominan           : [pola yang paling kuat didukung data]
Temuan kontradiktif    : [ada/tidak ada]
```

✅ J3.1 selesai. Ketik LANJUT untuk lanjut ke J3.2 (Menjawab Rumusan Masalah).

---

### J3.2 — Menjawab Rumusan Masalah

**Tujuan:** Menyusun jawaban eksplisit dan terstruktur untuk setiap rumusan masalah penelitian.

**Yang dilakukan agent:**
- Ambil setiap RM yang disebutkan pengguna di awal
- Susun jawaban berdasarkan temuan/pola dari J3.1
- Dukung setiap jawaban dengan data spesifik
- Hubungkan dengan teori yang digunakan pengguna

**Format output:**

```
✍️ J3.2 — JAWABAN RUMUSAN MASALAH
══════════════════════════════════════

── Rumusan Masalah 1 ──
RM: [kutip RM pengguna]

Jawaban:
[Paragraf jawaban yang lengkap dan akademik. Menyebutkan
temuan spesifik yang menjawab RM ini. Didukung data dari
wawancara, observasi, atau dokumen. Dihubungkan dengan
teori yang relevan.]

Didukung oleh:
• [Data/kutipan spesifik 1]
• [Data/kutipan spesifik 2]
• [Kode yang relevan]

── Rumusan Masalah 2 ──
RM: [kutip RM pengguna]

Jawaban:
[Paragraf jawaban RM 2...]

Didukung oleh:
• [Data spesifik...]

... (semua RM)
```

✅ J3.2 selesai. Ketik LANJUT untuk lanjut ke J3.3 (Verifikasi).

---

### J3.3 — Verifikasi

**Tujuan:** Mengecek kembali apakah kesimpulan yang ditarik benar-benar didukung data mentah dan tidak ada data penting yang terlewat atau disembunyikan.

**Yang dilakukan agent:**
- Cek ulang setiap klaim/jawaban terhadap data yang tersedia
- Identifikasi apakah ada data yang bertentangan yang belum dibahas
- Pastikan kesimpulan tidak melebihi apa yang data tunjukkan (over-claiming)
- Catat keterbatasan temuan jika ada

**Format output:**

```
✅ J3.3 — VERIFIKASI KESIMPULAN
══════════════════════════════════════

── Cek Konsistensi ──

Klaim 1: [klaim dari J3.2]
→ Didukung data: ✅ Ya — [sebutkan data pendukungnya]
→ Ada data bertentangan: [Ya/Tidak] — [jika ya, sebutkan]
→ Status: [KUAT / PERLU CATATAN]

Klaim 2: [klaim]
→ Didukung data: ✅/⚠️
→ Ada data bertentangan: [Ya/Tidak]
→ Status: [KUAT / PERLU CATATAN]

... (semua klaim)

── Temuan yang Perlu Dicatat ──
[Jika ada temuan yang tidak sesuai ekspektasi atau bertentangan
dengan hipotesis awal, catat di sini secara jujur]

── Keterbatasan Temuan ──
[Hal-hal yang membatasi generalisasi kesimpulan, misal:
jumlah informan terbatas, waktu observasi singkat, dll]

══ KESIMPULAN FINAL ══════════════════
[Paragraf ringkas yang menyatakan kesimpulan akhir penelitian
setelah verifikasi — ini adalah "kesimpulan yang solid"]
```

✅ J3.3 selesai.
✅ Jalur 3 (Penarikan Kesimpulan & Verifikasi) selesai.

---

## Catatan Penting untuk Agent

- **Kesimpulan harus berbasis data** — tidak boleh menambahkan interpretasi yang tidak didukung data
- **Temuan kontradiktif WAJIB dicatat** — bukan disembunyikan. Ini justru menunjukkan kualitas penelitian
- Jawaban RM harus **spesifik** — hindari jawaban yang terlalu umum/normatif
- Gunakan frasa akademik: "Berdasarkan temuan penelitian...", "Data menunjukkan...", "Hal ini mengindikasikan..."
- **Over-claiming dilarang** — jangan simpulkan sesuatu yang data tidak cukup buktikan
- Jika pengguna belum menyebutkan RM di awal, tanyakan sebelum memulai J3.2

## ⚠️ ATURAN WAJIB — IDENTIFIKASI TEMUAN KONTRADIKTIF

Saat J3.1 dan J3.3, agent WAJIB menelusuri **seluruh data mentah** yang diberikan pengguna untuk mencari:

- Pengalaman negatif yang dilaporkan informan (keluhan, kekecewaan, masalah)
- Pernyataan antar informan yang berbeda atau bertentangan
- Data observasi yang tidak sesuai dengan klaim wawancara
- Hal-hal yang tidak berjalan sempurna meski secara umum positif

Contoh: jika ada informan yang menyebut masalah kecil (produk rusak, pelayanan kurang, dsb),
maka J3.1 WAJIB mencatat temuan ini di bagian "── Temuan Kontradiktif ──"
dan J3.3 WAJIB mengevaluasi apakah temuan ini mempengaruhi klaim utama.

**Tidak ada temuan kontradiktif** hanya boleh dinyatakan setelah agent benar-benar
menelusuri semua data — bukan karena tidak mencarinya.