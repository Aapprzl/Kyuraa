import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from src.utils.logger import log
from src.tools.tool_loader import ToolLoader
from src.tools.file_reader import FileReader


# Path yang diizinkan untuk akses file (relatif terhadap working directory)
_BASE = Path.cwd()
ALLOWED_PATHS = [
    str(_BASE / "workspace"),
]

# Daftar tool yang memerlukan persetujuan user sebelum eksekusi (HITL)
SENSITIVE_TOOLS = {"write_file", "save_translation", "delete_session"}

_CUSTOM_TOOLS_DIR = Path("workspace/tools")
_SETTINGS_PATH = Path("workspace/settings.json")


def _load_tools_state() -> dict[str, bool]:
    """Baca state enabled/disabled tools dari settings.json."""
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("TOOLS_STATE", {})
        # Pastikan semua value adalah bool
        return {k: bool(v) for k, v in raw.items()}
    except Exception as e:
        log("tools", f"Gagal baca TOOLS_STATE dari settings.json: {e}")
        return {}


def _save_tools_state(state: dict[str, bool]) -> None:
    """Simpan state enabled/disabled tools ke settings.json."""
    current: dict = {}
    if _SETTINGS_PATH.exists():
        try:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            pass
    current["TOOLS_STATE"] = state
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=4, ensure_ascii=False)


class ToolRegistry:
    def __init__(self):
        self._output_dir = Path("workspace/output")
        self._reference_dir = Path("src/skills/references")

        # _tools: name → callable
        self._tools: dict[str, Callable] = {}
        # _tool_meta: name → {description, source, source_file, version, author}
        self._tool_meta: dict[str, dict] = {}
        # _state: name → bool (True = enabled)
        self._state: dict[str, bool] = {}

        self._reader = FileReader()

        self._init()

    # ──────────────────────────────────────────
    # Init
    # ──────────────────────────────────────────

    def _init(self) -> None:
        """Daftarkan built-in tools lalu load custom tools dari disk."""
        self._register_builtin_tools()
        self._load_custom_tools()
        self._sync_state()

    def _register_builtin_tools(self) -> None:
        """Daftarkan semua built-in tools beserta metadatanya."""
        builtin = [
            ("detect_language",    self._detect_language,    "Deteksi bahasa teks (Arab/Indonesia/Campuran)"),
            ("read_file",          self._read_file,          "Baca seluruh isi file sekaligus (disarankan hanya untuk file kecil)"),
            ("write_file",         self._write_file,          "Tulis konten ke file di workspace"),
            ("save_translation",   self._save_translation,    "Simpan hasil terjemahan ke workspace/output/"),
            ("list_output_files",  self._list_output_files,   "Tampilkan daftar file di folder output"),
            ("load_reference",     self._load_reference,      "Muat file referensi dari folder skills"),
            ("scan_file",          self._scan_file,           "Analisis file besar untuk melihat daftar bagian (chunk) yang tersedia"),
            ("read_chunk",         self._read_chunk,          "Baca satu bagian (chunk) spesifik dari file berdasarkan nomor index"),
            ("open_output_folder", self._open_output_folder,  "Buka folder output di Windows Explorer"),
        ]
        for name, func, desc in builtin:
            self._tools[name] = func
            self._tool_meta[name] = {
                "description": desc,
                "source": "built-in",
                "source_file": None,
                "version": "1.0",
                "author": "Kyuraa",
            }

    def _load_custom_tools(self) -> None:
        """Scan workspace/tools/ dan load semua custom tool."""
        custom_tools = ToolLoader.scan_tools_dir(_CUSTOM_TOOLS_DIR)
        loaded = 0
        for tool in custom_tools:
            name = tool["name"]
            # Hindari tumpang tindih dengan built-in
            if name in self._tools:
                name = f"{name}_custom"
                log("tools", f"Nama konflik — custom tool direname jadi '{name}'")
            self._tools[name] = tool["func"]
            self._tool_meta[name] = {
                "description": tool["description"],
                "source": "custom",
                "source_file": tool.get("source_file"),
                "version": tool.get("version", "1.0"),
                "author": tool.get("author", "Unknown"),
            }
            loaded += 1
        if loaded:
            log("tools", f"{loaded} custom tool berhasil dimuat")

    def _sync_state(self) -> None:
        """
        Sinkronisasi state dari settings.json.
        Tool baru yang belum ada di settings → default True (aktif).
        """
        saved_state = _load_tools_state()
        for name in self._tools:
            # Jika tool sudah ada di state yang disimpan, pakai itu
            # Jika belum (tool baru), default aktif
            self._state[name] = saved_state.get(name, True)
        # Simpan state yang sudah disinkron (agar tool baru masuk ke settings.json)
        _save_tools_state(self._state)

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def register(self, name: str, func: Callable, description: str = "") -> None:
        """Register tool secara programatik (untuk kebutuhan internal)."""
        self._tools[name] = func
        self._tool_meta[name] = {
            "description": description,
            "source": "built-in",
            "source_file": None,
            "version": "1.0",
            "author": "Kyuraa",
        }
        if name not in self._state:
            self._state[name] = True

    def get(self, name: str) -> Callable | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def list_tools_detail(self) -> list[dict]:
        """Kembalikan metadata lengkap semua tools beserta state enabled."""
        result = []
        for name, func in self._tools.items():
            meta = self._tool_meta.get(name, {})
            result.append({
                "name": name,
                "description": meta.get("description", ""),
                "source": meta.get("source", "built-in"),
                "source_file": meta.get("source_file"),
                "version": meta.get("version", "1.0"),
                "author": meta.get("author", "Kyuraa"),
                "enabled": self._state.get(name, True),
            })
        # Built-in dulu, baru custom
        return sorted(result, key=lambda x: (0 if x["source"] == "built-in" else 1, x["name"]))

    def toggle(self, name: str) -> bool:
        """
        Toggle state enabled/disabled untuk satu tool.
        Returns state baru (True = aktif, False = nonaktif).
        Raises KeyError jika tool tidak ditemukan.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' tidak ditemukan")
        self._state[name] = not self._state.get(name, True)
        _save_tools_state(self._state)
        new_state = self._state[name]
        log("tools", f"Tool '{name}' {'diaktifkan' if new_state else 'dinonaktifkan'}")
        return new_state

    def is_sensitive(self, name: str) -> bool:
        """
        Cek apakah tool termasuk dalam daftar tool sensitif yang memerlukan
        persetujuan user (Human-in-the-Loop) sebelum dieksekusi.
        """
        return name in SENSITIVE_TOOLS

    def reload(self) -> dict:
        """
        Reload custom tools dari disk tanpa restart server.
        Built-in tools tidak tersentuh.
        Returns ringkasan: jumlah tool setelah reload.
        """
        # Hapus custom tools lama dari registry
        to_remove = [n for n, m in self._tool_meta.items() if m.get("source") == "custom"]
        for name in to_remove:
            self._tools.pop(name, None)
            self._tool_meta.pop(name, None)
            # Pertahankan state lama di self._state (tidak dihapus)

        # Load ulang
        self._load_custom_tools()
        self._sync_state()

        custom_count = sum(1 for m in self._tool_meta.values() if m.get("source") == "custom")
        builtin_count = sum(1 for m in self._tool_meta.values() if m.get("source") == "built-in")
        log("tools", f"Reload selesai — {builtin_count} built-in, {custom_count} custom")
        return {
            "builtin": builtin_count,
            "custom": custom_count,
            "total": builtin_count + custom_count,
        }

    def execute(self, name: str, **kwargs) -> dict[str, Any]:
        """
        Eksekusi tool berdasarkan nama.
        Cek state enabled dulu sebelum menjalankan.
        """
        tool = self._tools.get(name)
        if tool is None:
            return {"success": False, "error": f"Tool '{name}' tidak ditemukan"}

        # Cek state
        if not self._state.get(name, True):
            return {
                "success": False,
                "error": f"Tool '{name}' sedang dinonaktifkan. Aktifkan di Settings → Tools."
            }

        try:
            result = tool(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            log("tools", f"Error saat eksekusi tool '{name}': {e}")
            return {"success": False, "error": str(e)}

    # ──────────────────────────────────────────
    # Built-in Tool Implementations
    # ──────────────────────────────────────────

    def _is_safe_path(self, path: str) -> bool:
        resolved = Path(path).resolve()
        return any(
            str(resolved).startswith(str(Path(ap).resolve()))
            for ap in ALLOWED_PATHS
        )

    def _detect_language(self, teks: str) -> str:
        arabic_chars = sum(1 for c in teks if "\u0600" <= c <= "\u06FF")
        ratio = arabic_chars / max(len(teks.strip()), 1)
        res = "indonesian"
        if ratio > 0.3:
            res = "arabic"
        elif ratio > 0.05:
            res = "mixed"
        log("tools", f"Language detected: {res}")
        return res

    def _read_file(self, path: str) -> str:
        if not self._is_safe_path(path):
            raise PermissionError(f"Path tidak diizinkan: {path}")
        log("tools", f"File read: {path}")
        return Path(path).read_text(encoding="utf-8")

    def _scan_file(self, path: str) -> dict:
        if not self._is_safe_path(path):
            raise PermissionError(f"Path tidak diizinkan: {path}")
        log("tools", f"File scan: {path}")
        return self._reader.get_file_info(path)

    def _read_chunk(self, path: str, index: Any) -> dict:
        if not self._is_safe_path(path):
            raise PermissionError(f"Path tidak diizinkan: {path}")
        idx = int(index)
        log("tools", f"File read chunk {idx}: {path}")
        return self._reader.get_chunk(path, idx)

    def _write_file(self, path: str, content: str) -> bool:
        if not self._is_safe_path(path):
            raise PermissionError(f"Path tidak diizinkan: {path}")
        log("tools", f"File saved: {path}")
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return True

    def _save_translation(self, filename: str, content: str) -> str:
        output_path = self._output_dir / filename
        if not self._is_safe_path(str(output_path)):
            raise PermissionError(f"Path tidak diizinkan: {output_path}")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        log("tools", f"Translation saved: {output_path}")
        return str(output_path)

    def _list_output_files(self) -> list[str]:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return [f.name for f in self._output_dir.iterdir() if f.is_file()]

    def _load_reference(self, nama_referensi: str) -> str | None:
        ref_path = self._reference_dir / f"{nama_referensi}.md"
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8")
        return None

    def _open_output_folder(self) -> bool:
        try:
            folder = self._output_dir.resolve()
            folder.mkdir(parents=True, exist_ok=True)
            subprocess.Popen(["explorer", str(folder)])
            return True
        except Exception:
            return False


registry = ToolRegistry()
