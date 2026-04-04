# Jalur A — Analisis Pretest & Posttest

Urutan wajib — tidak boleh dilangkahi dalam kondisi apapun:
```
A1 → A2 → A3 → A4
Statistik    Normalitas   N-Gain    Uji T /
Deskriptif                          Wilcoxon
```

> ⚠️ WAJIB: Meskipun semua data sudah tersedia sekaligus, tetap jalankan
> A1 → A2 → A3 → A4 secara berurutan dan tampilkan output setiap tahap.
> JANGAN melompat langsung ke A4 meskipun data sudah lengkap.
> Setiap tahap harus selesai dan ditampilkan outputnya sebelum lanjut ke tahap berikutnya.

---

## A1 — Statistik Deskriptif

### Penerimaan Data

Terima dalam format apapun:
- Tabel di chat: `Nama | Pretest | Posttest`
- File Excel/CSV: baca dengan Python
- Foto: baca nilai dari gambar, konfirmasi ke pengguna sebelum lanjut

Verifikasi sebelum hitung:
- Jumlah pretest = posttest?
- Ada nilai kosong atau > skor maksimal?
- Jika anomali → informasikan dan tanya penanganan

### Script Python

```python
import math

# Data dari pengguna — substitusi aktual
data = [
    # ("Nama", pretest, posttest),
]
skor_maks = 100  # tanya jika belum disebutkan

pretest  = [d[1] for d in data]
posttest = [d[2] for d in data]
n = len(pretest)

def mean(lst): return sum(lst) / len(lst)
def sd(lst):
    m = mean(lst)
    return math.sqrt(sum((x - m)**2 for x in lst) / len(lst))

pre_mean  = mean(pretest)
post_mean = mean(posttest)
pre_sd    = sd(pretest)
post_sd   = sd(posttest)
```

### Format Output

```
📊 A1 — STATISTIK DESKRIPTIF
══════════════════════════════════════

Rumus rata-rata : x̄ = Σxi / n
Rumus SD        : SD = √( Σ(xi - x̄)² / n )

── Pretest ──
Σxi = [40+55+60+...semua nilai...] = [total]
x̄   = [total] / [n] = [hasil]

Deviasi per siswa (xi - x̄)²:
No | Nama      | xi  | (xi-x̄)  | (xi-x̄)²
---|-----------|-----|---------|----------
1  | [nama]    | [n] | [n]     | [n]
2  | [nama]    | [n] | [n]     | [n]
...semua siswa dalam tabel...
   | Σ(xi-x̄)²|     |         | [total]

SD = √([total] / [n]) = [hasil]

── Posttest ──
[proses yang sama dalam format tabel]

══ HASIL ══════════════════════════════
              | Pretest  | Posttest
--------------|----------|----------
Nilai Min     | [nilai]  | [nilai]
Nilai Maks    | [nilai]  | [nilai]
Rata-rata     | [nilai]  | [nilai]
Std. Deviasi  | [nilai]  | [nilai]
Jumlah Siswa  | [n]      | [n]

Interpretasi:
Sebelum menggunakan produk, rata-rata nilai siswa adalah [nilai].
Setelah menggunakan produk, rata-rata meningkat menjadi [nilai],
dengan selisih [nilai] poin ([persen]% peningkatan).
```

Setelah output A1 ditampilkan, **BERHENTI dan tunggu konfirmasi** dengan pesan:
```
✅ A1 selesai. Ketik LANJUT untuk lanjut ke A2 (Uji Normalitas).
```

---

## A2 — Uji Normalitas

### Penentuan Uji

- n < 30  → **Shapiro-Wilk**
- n ≥ 30  → **Kolmogorov-Smirnov**

### Script Python

```python
from scipy import stats

stat_pre,  p_pre  = stats.shapiro(pretest)   # n < 30
stat_post, p_post = stats.shapiro(posttest)

# Atau untuk n >= 30:
# stat_pre,  p_pre  = stats.kstest(pretest,  'norm', args=(mean(pretest),  sd(pretest)))
# stat_post, p_post = stats.kstest(posttest, 'norm', args=(mean(posttest), sd(posttest)))
```

Cek library dulu sebelum jalankan:
```powershell
python -c "import scipy, numpy; print('OK')"
```
Jika gagal → `pip install scipy numpy` lalu jalankan ulang.

### Format Output

```
🔍 A2 — UJI NORMALITAS
══════════════════════════════════════

Uji yang digunakan : [Shapiro-Wilk / Kolmogorov-Smirnov]
Jumlah sampel      : n = [n]
Alpha              : 0,05

── Pretest ──
Statistik W = [nilai]
p-value     = [nilai]
p > 0,05?   → [Ya / Tidak] → Data [Normal / Tidak Normal]

── Posttest ──
Statistik W = [nilai]
p-value     = [nilai]
p > 0,05?   → [Ya / Tidak] → Data [Normal / Tidak Normal]

══ KESIMPULAN ═════════════════════════
Kedua data [normal / tidak normal]
Tindak lanjut: lanjut ke [Uji T / Uji Wilcoxon]

```

Setelah output A2 ditampilkan → **BERHENTI dan tunggu konfirmasi:**
```
✅ A2 selesai. Ketik LANJUT untuk lanjut ke A3 (N-Gain).
```

---

## A3 — Uji N-Gain

### Script Python

```python
hasil_ngain = []
for nama, pre, post in data:
    if skor_maks - pre == 0:
        ng = 0  # hindari pembagian nol
    else:
        ng = (post - pre) / (skor_maks - pre)
    kat = "Tinggi" if ng > 0.7 else "Sedang" if ng >= 0.3 else "Rendah"
    hasil_ngain.append((nama, pre, post, round(ng, 4), kat))

rata_ng  = mean([h[3] for h in hasil_ngain])
kat_kelas = "Tinggi" if rata_ng > 0.7 else "Sedang" if rata_ng >= 0.3 else "Rendah"
tinggi = sum(1 for h in hasil_ngain if h[4] == "Tinggi")
sedang = sum(1 for h in hasil_ngain if h[4] == "Sedang")
rendah = sum(1 for h in hasil_ngain if h[4] == "Rendah")
```

### Format Output

```
📈 A3 — UJI N-GAIN
══════════════════════════════════════

Rumus : N-Gain = (Posttest - Pretest) / (Skor Maks - Pretest)
Skor Maksimal = [nilai]

── Perhitungan per Siswa ──
1. [Nama]: ([post] - [pre]) / ([maks] - [pre]) = [selisih] / [sisa] = [hasil]
2. [Nama]: ([post] - [pre]) / ([maks] - [pre]) = [selisih] / [sisa] = [hasil]
... (semua siswa ditampilkan)

── Tabel Hasil ──
No | Nama   | Pretest | Posttest | N-Gain | Kategori
---|--------|---------|----------|--------|----------
1  | [nama] | [nilai] | [nilai]  | [nilai]| [kat]
2  | [nama] | [nilai] | [nilai]  | [nilai]| [kat]
...

── Rata-rata N-Gain Kelas ──
Σ N-Gain = [n1] + [n2] + ... = [total]
Rata-rata = [total] / [n] = [hasil]

══ RINGKASAN ══════════════════════════
Rata-rata N-Gain : [nilai]
Kategori Kelas   : [Tinggi/Sedang/Rendah]
Distribusi       : Tinggi=[n] | Sedang=[n] | Rendah=[n]

Interpretasi:
Produk [nama] terbukti efektif meningkatkan hasil belajar siswa
dengan rata-rata N-Gain [nilai] yang berada pada kategori [kategori].

```

Setelah output A3 ditampilkan → **BERHENTI dan tunggu konfirmasi:**
```
✅ A3 selesai. Ketik LANJUT untuk lanjut ke A4 (Uji T/Wilcoxon).
```

---

## A4 — Uji T Berpasangan / Uji Wilcoxon

### Script Python

```python
# Jika normal → Uji T
# PENTING: urutan (posttest, pretest) agar nilai t positif
t_stat, p_value = stats.ttest_rel(posttest, pretest)
t_stat = abs(t_stat)  # pastikan selalu positif

# Jika tidak normal → Wilcoxon
# t_stat, p_value = stats.wilcoxon(posttest, pretest)

selisih = [post - pre for pre, post in zip(pretest, posttest)]
mean_selisih = mean(selisih)
sd_selisih   = sd(selisih)
se           = sd_selisih / math.sqrt(n)

# Format p-value secara akademis — JANGAN tulis "0.0"
if p_value == 0 or p_value < 1e-10:
    p_str = "< 0,001 (sangat kecil, mendekati nol)"
elif p_value < 0.001:
    p_str = "< 0,001"
else:
    p_str = f"{p_value:.3f}"
```

> ⚠️ Nilai t HARUS positif dalam laporan skripsi karena menunjukkan
> arah peningkatan (posttest > pretest). Gunakan `abs(t_stat)`.
>
> ⚠️ p-value JANGAN ditulis "0.0" — gunakan `p_str` di atas.
> Nilai "0.0" muncul karena Python membulatkan angka yang sangat kecil.

### Format Output — Uji T

```
📊 A4 — UJI T BERPASANGAN
══════════════════════════════════════

Rumus : t = D̄ / (SD_d / √n)
D̄    = rata-rata selisih (posttest - pretest)
SD_d = standar deviasi selisih
n    = jumlah sampel

── Selisih per Siswa (D = Posttest - Pretest) ──
1. [nama]: [post] - [pre] = [selisih]
2. [nama]: [post] - [pre] = [selisih]
... (semua siswa)

── Perhitungan ──
D̄    = ([d1] + [d2] + ...) / [n] = [hasil]
SD_d = √(Σ(Di - D̄)² / n)
     = √([proses]) = [hasil]
SE   = [SD_d] / √[n] = [hasil]

── Derajat Kebebasan ──
df = n - 1 = [n] - 1 = [hasil]

> ⚠️ JANGAN tampilkan baris "t = D̄ / SE = ..." secara manual.
> Nilai t dihitung Python (ttest_rel), gunakan HANYA nilai dari Python.
> JANGAN tulis komentar seperti "(nilai dari Python adalah X, akan digunakan...)"
> Langsung tampilkan nilai Python di kotak HASIL di bawah.

══ HASIL ══════════════════════════════
Statistik t : [t_stat dari Python — abs(t_stat) — selalu positif]
df          : [nilai]
p-value     : [p_str — misal "< 0,001" bukan "0.0"]
Alpha       : 0,05
p < 0,05?   → [Ya/Tidak]
Kesimpulan  : Terdapat perbedaan [signifikan/tidak signifikan]
```

### Format Output — Wilcoxon (jika data tidak normal)

```
📊 A4 — UJI WILCOXON
══════════════════════════════════════

Digunakan karena data tidak berdistribusi normal (hasil A2).

── Selisih dan Peringkat ──
1. [nama]: D=[selisih], |D|=[abs], Rank=[rank], Tanda=[+/-]
2. [nama]: D=[selisih], |D|=[abs], Rank=[rank], Tanda=[+/-]
...

── Perhitungan ──
W+ (jumlah rank positif) = [nilai]
W- (jumlah rank negatif) = [nilai]
W  = min(W+, W-)         = [nilai]

══ HASIL ══════════════════════════════
Statistik W : [nilai]
p-value     : [nilai]
p < 0,05?   → [Ya/Tidak]
Kesimpulan  : Terdapat perbedaan [signifikan/tidak signifikan]

```