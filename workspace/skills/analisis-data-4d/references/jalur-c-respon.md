# Jalur C — Angket Respon Siswa/Guru

---

## C1 — Penerimaan Data

Tanya jika belum jelas:
- Responden: siswa / guru / keduanya?
- Skala: 1–4 atau 1–5?
- Data per butir pernyataan atau sudah per aspek?

Format per butir:
```
Siswa | B1 | B2 | B3 | B4 | B5 | ...
  1   |  4 |  3 |  4 |  4 |  3 | ...
  2   |  3 |  4 |  3 |  4 |  4 | ...
```

Format per aspek (sudah dikelompokkan):
```
Aspek Tampilan    : 87 dari 120
Aspek Kemudahan   : 79 dari 100
Aspek Kemanfaatan : 95 dari 120
```

---

## C2 — Script Python

```python
# Jika data per butir — kelompokkan per aspek dulu
# Contoh: butir 1-3 = Tampilan, butir 4-6 = Kemudahan, dst.

aspek = [
    # ("Nama Aspek", skor_total, skor_maks),
]

hasil = []
for nama, skor, maks in aspek:
    persen = (skor / maks) * 100
    if persen >= 81:   kat = "Sangat Praktis"
    elif persen >= 61: kat = "Praktis"
    elif persen >= 41: kat = "Cukup Praktis"
    elif persen >= 21: kat = "Kurang Praktis"
    else:              kat = "Tidak Praktis"
    hasil.append((nama, skor, maks, round(persen, 2), kat))

total_skor   = sum(s for _,s,_,_,_ in hasil)
total_maks   = sum(m for _,_,m,_,_ in hasil)
total_persen = (total_skor / total_maks) * 100
```

---

## C3 — Format Output

```
📋 C — ANGKET RESPON [SISWA/GURU]
══════════════════════════════════════

Rumus : Persentase = (Skor Diperoleh / Skor Maksimal) × 100%
Jumlah Responden : [n] [siswa/guru]
Skala            : 1–[4/5]

── Perhitungan per Aspek ──
1. [Aspek 1] : ([skor] / [maks]) × 100% = [hasil]%
2. [Aspek 2] : ([skor] / [maks]) × 100% = [hasil]%
... (semua aspek)

── Perhitungan Total ──
Total Skor = [s1] + [s2] + ... = [total]
Total Maks = [m1] + [m2] + ... = [total]
Persentase = ([total skor] / [total maks]) × 100% = [hasil]%

══ TABEL HASIL ════════════════════════
Aspek             | Skor | Maks | Persentase | Kategori
------------------|------|------|------------|----------
[Aspek 1]         | [n]  | [n]  | [n]%       | [kat]
[Aspek 2]         | [n]  | [n]  | [n]%       | [kat]
...
TOTAL             | [n]  | [n]  | [n]%       | [kat]

══ KESIMPULAN ═════════════════════════
Persentase Total : [nilai]%
Kategori         : [kategori]
Jumlah Responden : [n] [siswa/guru]

Interpretasi:
Produk [nama] mendapatkan respon [kategori] dari [n] [siswa/guru]
dengan persentase kepraktisan [nilai]%.

```