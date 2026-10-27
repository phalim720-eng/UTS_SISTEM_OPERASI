"""AI pipeline dengan konsep OS: chunking, out-of-memory, optimasi alokasi memori.
Jalankan: python3 pipeline.py          (default 1 juta baris x 50 fitur)
Hanya butuh numpy. Memori diukur dengan tracemalloc (alokasi RAM numpy)."""
import os, time, tracemalloc
import numpy as np

N_ROWS, N_FEAT = 1_000_000, 50
CHUNK = 50_000                       # jumlah baris per chunk
BUDGET_MB = 500                      # SIMULASI batas RAM (lihat check_budget)
DATA = "data.f32"                    # file biner di disk (float32)
rng = np.random.default_rng(0)

def check_budget(nbytes, label):
    """Simulasi OOM: tolak alokasi yang melewati batas RAM kita.
    (OOM asli = kernel OOM-killer mematikan proses; ini versi aman untuk demo.)"""
    mb = nbytes / 1e6
    if mb > BUDGET_MB:
        raise MemoryError(f"{label}: butuh {mb:.0f} MB > batas {BUDGET_MB} MB")

def make_data():
    """Buat dataset sintetis langsung ke disk, per chunk (tidak memenuhi RAM)."""
    w_true = rng.normal(size=N_FEAT).astype(np.float32)
    mm = np.memmap(DATA, dtype=np.float32, mode="w+", shape=(N_ROWS, N_FEAT + 1))
    for i in range(0, N_ROWS, CHUNK):
        x = rng.normal(5, 3, size=(min(CHUNK, N_ROWS - i), N_FEAT)).astype(np.float32)
        y = (x @ w_true > 5 * w_true.sum()).astype(np.float32)
        mm[i:i + len(x), :N_FEAT], mm[i:i + len(x), N_FEAT] = x, y
    mm.flush(); del mm

def peak(fn):
    """Jalankan fn, kembalikan (hasil, waktu, puncak memori MB)."""
    tracemalloc.start(); t = time.perf_counter()
    try: out = fn()
    except MemoryError as e: out = f"OOM! {e}"
    dt = time.perf_counter() - t
    mb = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop(); return out, dt, mb

# ---------- V1: NAIF — muat semua ke RAM sebagai float64 ----------
def naive():
    check_budget(N_ROWS * (N_FEAT + 1) * 8, "load float64")   # 1jt x 51 x 8B = 408 MB
    raw = np.fromfile(DATA, dtype=np.float32).reshape(N_ROWS, N_FEAT + 1)
    data = raw.astype(np.float64)                             # salinan #2 (2x lipat)
    check_budget(data.nbytes + raw.nbytes + data.nbytes, "standardisasi (salinan lagi)")
    X = (data[:, :N_FEAT] - data[:, :N_FEAT].mean(0)) / data[:, :N_FEAT].std(0)
    return train(X, data[:, N_FEAT])

# ---------- V2: TEROPTIMASI — memmap + chunking + float32 + buffer dipakai ulang ----------
def chunks():
    """Generator: baca file per chunk lewat memmap (OS memuat page sesuai kebutuhan)."""
    mm = np.memmap(DATA, dtype=np.float32, mode="r", shape=(N_ROWS, N_FEAT + 1))
    for i in range(0, N_ROWS, CHUNK):
        yield mm[i:i + CHUNK]

def optimized():
    # Pass 1: mean & std secara streaming (tanpa menyimpan seluruh data)
    s = np.zeros(N_FEAT); s2 = np.zeros(N_FEAT)
    for c in chunks():
        x = c[:, :N_FEAT].astype(np.float64); s += x.sum(0); s2 += (x ** 2).sum(0)
    mean = s / N_ROWS; std = np.sqrt(s2 / N_ROWS - mean ** 2)
    mean, std = mean.astype(np.float32), std.astype(np.float32)
    # Pass 2: latih logistic regression mini-batch per chunk
    w = np.zeros(N_FEAT, np.float32); b = np.float32(0)
    buf = np.empty((CHUNK, N_FEAT), np.float32)         # buffer dialokasi SEKALI
    for c in chunks():
        n = len(c)
        np.subtract(c[:, :N_FEAT], mean, out=buf[:n])   # in-place: tanpa salinan baru
        np.divide(buf[:n], std, out=buf[:n])
        w, b = sgd_step(buf[:n], c[:, N_FEAT], w, b)
    return accuracy_chunked(w, b, mean, std)

# ---------- Model sederhana: logistic regression ----------
def sigmoid(z): return 1 / (1 + np.exp(-z))

def sgd_step(X, y, w, b, lr=0.1):
    p = sigmoid(X @ w + b)
    return w - lr * X.T @ (p - y) / len(y), b - lr * (p - y).mean()

def train(X, y):                                        # dipakai versi naif
    w = np.zeros(X.shape[1]); b = 0.0
    for i in range(0, len(X), CHUNK): w, b = sgd_step(X[i:i+CHUNK], y[i:i+CHUNK], w, b)
    return f"akurasi={((sigmoid(X @ w + b) > .5) == y).mean():.3f}"

def accuracy_chunked(w, b, mean, std):
    ok = 0
    for c in chunks():
        X = (c[:, :N_FEAT] - mean) / std
        ok += ((sigmoid(X @ w + b) > .5) == c[:, N_FEAT]).sum()
    return f"akurasi={ok / N_ROWS:.3f}"

if __name__ == "__main__":
    if not os.path.exists(DATA):
        print("Membuat dataset di disk..."); make_data()
    print(f"Dataset: {os.path.getsize(DATA)/1e6:.0f} MB di disk | batas RAM simulasi: {BUDGET_MB} MB\n")
    for name, fn in [("V1 Naif (load semua, float64)", naive),
                     ("V2 Optimasi (chunk+memmap+float32)", optimized)]:
        out, dt, mb = peak(fn)
        print(f"{name}\n  hasil: {out}\n  waktu: {dt:.1f}s | puncak RAM: {mb:.1f} MB\n")
