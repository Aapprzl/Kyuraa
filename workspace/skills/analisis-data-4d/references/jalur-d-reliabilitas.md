# Jalur D — Reliabilitas Instrumen (Cronbach's Alpha)

Dijalankan sebelum penelitian sesungguhnya — saat instrumen baru selesai
dibuat dan perlu diuji konsistensinya.

---

## D1 — Penerimaan Data

Data yang dibutuhkan — **skor per butir per responden**:
```
Siswa | B1 | B2 | B3 | B4 | ... | Total
  1   |  1 |  0 |  1 |  1 | ... |
  2   |  1 |  1 |  0 |  1 | ... |
```

> ⚠️ Jalur D butuh skor per butir — bukan hanya skor total.
> Jika hanya ada skor total → informasikan bahwa Alpha tidak bisa dihitung.

Tanya jika belum jelas:
- Berapa butir soal / pernyataan?
- Berapa responden uji coba?
- Jenis: soal tes (0/1) atau angket (skala Likert)?

---

## D2 — Cek Library

Sebelum hitung, jalankan dulu:
```powershell
python -c "import numpy; print('OK')"
```
Jika gagal:
```powershell
pip install numpy
```

---

## D3 — Script Python

```python
import numpy as np

# Data: baris = responden, kolom = butir soal
# Substitusi data aktual dari pengguna
data = np.array([
    # [b1, b2, b3, ...],  # responden 1
    # [b1, b2, b3, ...],  # responden 2
])

n_responden, k = data.shape  # k = jumlah butir

# Varians per butir
var_butir = data.var(axis=0, ddof=0)
sum_var_butir = var_butir.sum()

# Varians skor total
skor_total = data.sum(axis=1)
var_total  = skor_total.var(ddof=0)

# Cronbach's Alpha
alpha = (k / (k - 1)) * (1 - sum_var_butir / var_total)
```

---

## D4 — Format Output

```
🔍 D — UJI RELIABILITAS CRONBACH'S ALPHA
══════════════════════════════════════

Rumus : α = (k / (k-1)) × (1 - Σσi² / σt²)

Keterangan:
k    = jumlah butir = [nilai]
σi²  = varians tiap butir
σt²  = varians skor total
n    = jumlah responden = [nilai]

── Varians per Butir ──
Tampilkan dalam tabel ringkas — JANGAN satu baris per butir memanjang ke bawah:

Butir | Varians (σi²)
------|---------------
B1    | [nilai]
B2    | [nilai]
...semua butir dalam tabel...
Bk    | [nilai]
──────|───────────────
Σσi²  | [total]

── Varians Skor Total ──
Tampilkan skor total dalam format baris ringkas — BUKAN daftar R1, R2, R3 memanjang:

Skor total: [s1] [s2] [s3] ... [sn] (semua dalam satu baris atau maks 2 baris)
x̄ total = [nilai]
σt²     = [hasil]

── Substitusi ke Rumus ──
α = ([k] / ([k]-1)) × (1 - [Σσi²] / [σt²])
  = [k/(k-1)] × (1 - [rasio])
  = [k/(k-1)] × [sisa]
  = [hasil]

══ HASIL ══════════════════════════════
Jumlah Butir     : [k]
Jumlah Responden : [n]
Σ Varians Butir  : [nilai]
Varians Total    : [nilai]
Cronbach's Alpha : [nilai]
Kategori         : [kategori]

Tabel Kriteria:
0,80–1,00 = Sangat Reliabel
0,60–0,79 = Reliabel
0,40–0,59 = Cukup Reliabel
0,20–0,39 = Kurang Reliabel
< 0,20    = Tidak Reliabel

Interpretasi:
Instrumen dinyatakan [kategori] dengan nilai Alpha [nilai].
[Kalimat sesuai kategori — layak/tidak layak digunakan.]

```

Jika Alpha rendah, nol, atau negatif — diagnosis lanjutan:

> ⚠️ Alpha negatif BUKAN error rumus — ini hasil valid yang menunjukkan
> masalah serius pada instrumen. Wajib dijelaskan, bukan diabaikan.

Jalankan diagnosis tambahan:

```python
from scipy.stats import pearsonr

# Hitung korelasi antar butir
print("── Korelasi Antar Butir ──")
for i in range(k):
    for j in range(i+1, k):
        r, p = pearsonr(data[:,i], data[:,j])
        tanda = "⚠️ negatif" if r < 0 else "✓"
        print(f"B{i+1}-B{j+1}: r={r:.3f} {tanda}")

# Cek distribusi skor total
print(f"\n── Distribusi Skor Total ──")
import collections
dist = collections.Counter(skor_total.tolist())
for skor, jumlah in sorted(dist.items()):
    print(f"Skor {skor}: {jumlah} responden")
```

Format output jika Alpha negatif atau < 0,20:
```
⚠️ D — DIAGNOSIS INSTRUMEN

Alpha = [nilai] → [negatif / sangat rendah]

Ini menunjukkan salah satu atau beberapa kondisi berikut:

1. VARIASI SKOR TOTAL RENDAH
   Skor total responden hanya berkisar [min]–[maks] dari [maks_mungkin]
   → Soal terlalu mudah/sulit sehingga semua responden skor mirip
   → Varians total kecil, membuat Alpha tidak bisa dihitung dengan baik

2. KORELASI BUTIR NEGATIF
   Butir-butir yang saling berkorelasi negatif:
   [daftar pasangan butir dengan r negatif]
   → Butir-butir ini mengukur konstruk yang BERBEDA atau berlawanan

3. INSTRUMEN TIDAK HOMOGEN
   Butir-butir tidak konsisten mengukur satu konstruk yang sama

── Rekomendasi ──
• Tinjau butir dengan korelasi negatif — kemungkinan perlu direvisi/dihapus
• Pastikan semua butir mengukur konstruk yang sama (keterampilan membaca)
• Uji coba ulang dengan data yang memiliki variasi lebih baik

Catatan untuk skripsi:
"Hasil uji reliabilitas menunjukkan nilai Cronbach's Alpha sebesar [nilai].
Nilai ini mengindikasikan bahwa instrumen perlu direvisi karena beberapa
butir tidak mengukur konstruk yang homogen. Revisi dilakukan dengan
[langkah revisi] sehingga diperoleh instrumen final yang digunakan
dalam penelitian."
```