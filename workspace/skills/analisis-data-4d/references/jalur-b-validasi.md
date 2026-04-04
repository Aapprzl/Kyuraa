# Jalur B — Validasi Ahli

---

## B1 — Penerimaan Data

Tanya jika belum jelas:
- Berapa ahli yang menilai? (materi / media / bahasa)
- Apakah data per aspek atau hanya total?
- Skala: 1–4 atau 1–5?

Format yang diterima:
```
Aspek              | Skor | Maks
-------------------|------|------
Kesesuaian Materi  | 18   | 20
Kebenaran Konsep   | 16   | 20
Kedalaman Materi   | 14   | 20
```
Atau cukup total: "Skor 48 dari 60"

---

## B2 — Script Python

```python
# Data dari pengguna
aspek = [
    # ("Nama Aspek", skor, maks),
]

# Persentase per aspek
hasil = []
for nama, skor, maks in aspek:
    persen = (skor / maks) * 100
    if persen >= 81:   kat = "Sangat Valid"
    elif persen >= 61: kat = "Valid"
    elif persen >= 41: kat = "Cukup Valid"
    elif persen >= 21: kat = "Kurang Valid"
    else:              kat = "Tidak Valid"
    hasil.append((nama, skor, maks, round(persen, 2), kat))

# Total
total_skor = sum(s for _,s,_,_,_ in hasil) if hasil else skor_total
total_maks = sum(m for _,_,m,_,_ in hasil) if hasil else maks_total
total_persen = (total_skor / total_maks) * 100
```

---

## B3 — Format Output

```
📊 B — VALIDASI AHLI [MATERI/MEDIA/BAHASA]
══════════════════════════════════════

Rumus : Persentase = (Skor Diperoleh / Skor Maksimal) × 100%

── Perhitungan per Aspek ──
1. [Aspek 1] : ([skor] / [maks]) × 100% = [hasil]%
2. [Aspek 2] : ([skor] / [maks]) × 100% = [hasil]%
3. [Aspek 3] : ([skor] / [maks]) × 100% = [hasil]%
... (semua aspek)

── Perhitungan Total ──
Total Skor = [s1] + [s2] + [s3] + ... = [total]
Total Maks = [m1] + [m2] + [m3] + ... = [total]
Persentase = ([total skor] / [total maks]) × 100% = [hasil]%

══ TABEL HASIL ════════════════════════
Aspek              | Skor | Maks | Persentase | Kategori
-------------------|------|------|------------|----------
[Aspek 1]          | [n]  | [n]  | [n]%       | [kat]
[Aspek 2]          | [n]  | [n]  | [n]%       | [kat]
...
TOTAL              | [n]  | [n]  | [n]%       | [kat]

══ KESIMPULAN ═════════════════════════
Persentase Total : [nilai]%
Kategori         : [kategori]

Interpretasi:
Produk dinyatakan [kategori] berdasarkan penilaian ahli [jenis]
dengan persentase [nilai]%. [Kalimat sesuai kategori.]

```

Jika ada saran dari validator:
> "Sampaikan saran/komentar dari validator — saya bantu susun
> sebagai dasar revisi produk (Draf I → Draf II)."

---

## B4 — Rekapitulasi Keseluruhan

Setelah **semua ahli selesai**, WAJIB tampilkan blok rekap ini:

```
📊 B — VALIDASI AHLI KESELURUHAN
══════════════════════════════════════

Total Skor Keseluruhan : [jumlah semua skor ahli]
Total Maks Keseluruhan : [jumlah semua maks ahli]
Persentase Keseluruhan : ([total skor] / [total maks]) × 100% = [hasil]%
Kategori Keseluruhan   : [kategori]

Interpretasi:
Berdasarkan penilaian dari seluruh ahli ([daftar jenis ahli]),
produk secara keseluruhan dinyatakan [kategori] dengan persentase [nilai]%.

```

> ⚠️ Blok rekap ini WAJIB muncul meskipun hanya ada 1 jenis ahli.