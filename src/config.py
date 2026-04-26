"""
Konstanta konfigurasi global Kyuraa.
Ubah nilai di sini untuk menyesuaikan perilaku sistem.
"""

# ─── LLM Settings ───────────────────────────────
LLM_MAX_TOKENS: int = 8192          # Batas output token per respons
LLM_MAX_INPUT_TOKENS: int = 30000   # Estimasi batas konteks input
LLM_TEMPERATURE: float = 0.7        # Kreativitas model (0=deterministik, 1=kreatif)
LLM_TIMEOUT_SECONDS: int = 120      # Timeout request ke LLM
LLM_MAX_RETRIES: int = 3            # Maks percobaan ulang saat error

# ─── Memory / History ────────────────────────────
SESSION_HISTORY_LIMIT: int = 10     # Jumlah pesan riwayat yang dimuat per request

# ─── File Upload ─────────────────────────────────
MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
MAX_PDF_TOKENS: int = 25000                    # Batas estimasi token isi PDF

# ─── File Reader ─────────────────────────────────
FILE_CHUNK_MAX_CHARS: int = 6000    # Ukuran maksimal satu chunk file

# ─── Server ──────────────────────────────────────
DEFAULT_GATEWAY_PORT: int = 8766
DEFAULT_GATEWAY_HOST: str = "localhost"
MAX_USER_INPUT_CHARS: int = 10000   # ~2500 kata, batas pesan user
