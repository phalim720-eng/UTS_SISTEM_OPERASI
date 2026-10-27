# Proses, Thread, dan Manajemen Memori

### Sistem Operasi — UTS Ganjil 2026/2027

**Universitas Negeri Surabaya — S1 Kecerdasan Artifisial**

* * *

## Penyusun Proyek

| Nama                    | NIM           |
|-------------------------|---------------|
| Muhamad Halim Pratama   | 25032014016   |
| Fitri Nur Aini          | 25032014080   |
| Muhammad Husnul Istighfar| 25032014048  |

* * *

## Deskripsi Proyek

Proyek ini mendemonstrasikan tiga konsep inti sistem operasi beserta implementasinya:

| No | Topik | Teknologi | Konsep OS |
|----|-------|-----------|-----------|
| 1 | `fork()`, `wait()`, `exec()` | C (POSIX) | Pembuatan proses, memori terpisah, pola fork-exec-wait |
| 2 | Multithreading vs Multiprocessing | Python (`threading`, `multiprocessing`) | Berbagi memori, GIL, overhead pembuatan proses |
| 3 | AI Pipeline | Python + NumPy | Chunking, out-of-memory, optimasi alokasi memori |

### Fitur

- Tiga demo `fork()`, `wait()`, dan `exec()` yang dipilih lewat argumen
- Perbandingan sequential vs thread vs process pada tugas CPU-bound dan I/O-bound
- Demo bukti memori dibagi (thread) vs terpisah (process)
- Pipeline logistic regression versi naif (memuat semua ke RAM) vs versi optimasi
- Optimasi memori: chunking, `np.memmap`, float32, buffer dipakai ulang, operasi in-place
- Simulasi out-of-memory dengan batas RAM yang dapat diatur
- Kompatibel dengan macOS (Intel)

* * *

## Cara Build & Run (macOS)

### Prasyarat

```
# Pastikan Xcode Command Line Tools ter-install (untuk compiler C)
xcode-select --install

# Cek compiler dan Python
clang --version
python3 --version

# Install NumPy (untuk demo 3)
pip3 install numpy
```

### 1. fork(), wait(), exec()

```
cd 1_fork_wait_exec
gcc fork_wait_exec.c -o fork_wait_exec

./fork_wait_exec 1   # fork: memori parent dan child terpisah
./fork_wait_exec 2   # wait: parent menunggu child, membaca exit code
./fork_wait_exec 3   # exec: child berubah menjadi "ls -l"
```

### 2. Multithreading vs Multiprocessing

```
cd 2_thread_vs_process
python3 thread_vs_process.py
```

### 3. AI Pipeline

```
cd 3_ai_pipeline
python3 pipeline.py
# File data.f32 (~200 MB) dibuat otomatis saat pertama dijalankan
```

Konstanta `N_ROWS`, `CHUNK`, dan `BUDGET_MB` di bagian atas `pipeline.py` dapat diubah untuk menyesuaikan ukuran data dan batas memori simulasi.

* * *

## Struktur Repository

```
tugas_os/
├── 1_fork_wait_exec/
│   └── fork_wait_exec.c          # Demo fork, wait, exec
├── 2_thread_vs_process/
│   └── thread_vs_process.py      # Thread vs process
├── 3_ai_pipeline/
│   └── pipeline.py               # Pipeline AI: naif vs optimasi
└── README.md
```

* * *

## 🎥 Video Demo
https://youtu.be/bNIBWoGq45w 

* * *

## Hasil

### Demo 1 — fork(), wait(), exec()

| Argumen | Konsep | Hasil |
|---------|--------|-------|
| 1 | `fork()` | `x` di child menjadi 150, di parent tetap 100 |
| 2 | `wait()` | Parent menunggu child, lalu mencetak exit code 7 |
| 3 | `exec()` | Child menjalankan `ls -l`, parent melanjutkan setelahnya |

### Demo 2 — Thread vs Process

*(Dijalankan di MacBook Intel Core i5, 2 core, 4 worker)*

| Eksperimen | Sequential | Multithreading | Multiprocessing |
|------------|------------|----------------|-----------------|
| CPU-bound  | 3.52 s     | 3.46 s         | 2.14 s          |
| I/O-bound  | 4.00 s     | 1.00 s         | 1.03 s          |

Eksperimen memori: setelah thread, `counter` = 10 (dibagi); setelah process, `counter` = 0 (terpisah).

### Demo 3 — AI Pipeline

| Versi | Hasil | Waktu | Puncak RAM |
|-------|-------|-------|------------|
| V1 Naif (float64, load semua) | [isi dari run] | [isi] | [isi] |
| V2 Optimasi (chunk + memmap + float32) | [isi dari run] | [isi] | [isi] |

* * *

## Analisis Singkat

- **fork()** menduplikasi proses; child mendapat salinan memori sendiri sehingga perubahan di child tidak memengaruhi parent. `exec()` mengganti isi proses dengan program lain, dan `wait()` mencegah child menjadi zombie
- **Thread** tidak mempercepat tugas CPU-bound di Python karena GIL, tetapi efektif untuk I/O-bound karena GIL dilepas saat menunggu
- **Multiprocessing** benar-benar paralel, tetapi percepatannya (~1.6×) di bawah ideal karena hanya ada 2 core dan ada overhead `spawn` di macOS
- **Pipeline naif** membutuhkan memori berlipat karena konversi tipe dan standardisasi membuat salinan data; **chunking + memmap** menjaga penggunaan RAM tetap kecil dan konstan terhadap ukuran data

* * *

## Catatan Teknis

- `fork()` tidak tersedia di Windows native; gunakan macOS, Linux, atau WSL
- Blok `if __name__ == "__main__"` pada demo 2 wajib karena macOS memakai metode `spawn` untuk multiprocessing
- Batasan GIL berlaku untuk CPython standar; Python 3.13 memiliki mode eksperimental tanpa GIL yang tidak aktif secara default
- **OOM pada demo 3 adalah simulasi**: fungsi `check_budget` menolak alokasi yang melewati `BUDGET_MB` (500 MB). OOM sungguhan terjadi saat kernel mematikan proses
- Memori diukur dengan `tracemalloc` (alokasi array NumPy), bukan total RSS; halaman `memmap` yang dimuat OS tidak ikut terhitung
- Waktu eksekusi bergantung pada perangkat
