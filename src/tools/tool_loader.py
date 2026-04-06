import importlib.util
import re
from pathlib import Path
from typing import Callable

from src.utils.logger import log

# Pola berbahaya yang dilarang ada di source code tool
_DANGEROUS_PATTERNS = [
    r'\bos\.system\s*\(',
    r'\bsubprocess\.',
    r'\bshutil\.rmtree\s*\(',
    r'\bshutil\.rmdir\s*\(',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'__import__\s*\(',
    r'\bopen\s*\(.*["\']w["\']',   # open() mode write
    r'\bos\.remove\s*\(',
    r'\bos\.unlink\s*\(',
    r'\bos\.rmdir\s*\(',
]

_COMPILED_PATTERNS = [re.compile(p) for p in _DANGEROUS_PATTERNS]


def _check_security(source: str) -> list[str]:
    """Kembalikan daftar pelanggaran keamanan yang ditemukan di source code."""
    violations = []
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(source):
            violations.append(pattern.pattern)
    return violations


def _parse_metadata(source: str) -> dict:
    """
    Ekstrak metadata dari komentar header di file tool.
    Format: # key: value
    """
    metadata = {}
    for line in source.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            # Baris non-komentar pertama = akhir header
            if line and not line.startswith('"""') and not line.startswith("'''"):
                break
            continue
        # Strip '#' dan spasi
        content = line.lstrip("#").strip()
        if ":" in content:
            key, _, value = content.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key in ("name", "description", "version", "author"):
                metadata[key] = value

    return metadata


class ToolLoader:
    """
    Memuat tool Python secara dinamis dari file .py di workspace/tools/.
    Setiap file harus memiliki:
      - Komentar metadata (# name:, # description:, ...)
      - Fungsi `run(**kwargs) -> str | dict`
    """

    @staticmethod
    def load_from_file(filepath: Path) -> dict | None:
        """
        Load satu tool dari file .py.

        Returns:
            dict dengan keys: name, description, version, author, func, source_file
            None jika gagal load atau tidak valid.
        """
        try:
            source = filepath.read_text(encoding="utf-8")
        except Exception as e:
            log("tools", f"[ToolLoader] Gagal baca file {filepath.name}: {e}")
            return None

        # 1. Cek keamanan
        violations = _check_security(source)
        if violations:
            log("tools", f"[ToolLoader] ⚠️  Tool {filepath.name} DITOLAK — "
                         f"mengandung pola berbahaya: {violations}")
            return None

        # 2. Parse metadata dari komentar
        metadata = _parse_metadata(source)
        tool_name = metadata.get("name") or filepath.stem

        # 3. Load modul secara dinamis
        try:
            spec = importlib.util.spec_from_file_location(
                f"kyuraa_tool_{tool_name}", str(filepath)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            log("tools", f"[ToolLoader] Gagal import {filepath.name}: {e}")
            return None

        # 4. Pastikan fungsi run() ada
        run_func: Callable | None = getattr(module, "run", None)
        if run_func is None or not callable(run_func):
            log("tools", f"[ToolLoader] {filepath.name} tidak memiliki fungsi run() — dilewati")
            return None

        log("tools", f"[ToolLoader] ✅ Tool dimuat: '{tool_name}' dari {filepath.name}")
        return {
            "name": tool_name,
            "description": metadata.get("description", "Custom tool"),
            "version": metadata.get("version", "1.0"),
            "author": metadata.get("author", "Unknown"),
            "func": run_func,
            "source_file": str(filepath),
            "source": "custom",
        }

    @staticmethod
    def scan_tools_dir(tools_dir: Path) -> list[dict]:
        """
        Scan semua .py file di tools_dir (kecuali TOOL_TEMPLATE.py).

        Returns:
            List of tool dicts yang berhasil di-load.
        """
        if not tools_dir.exists():
            tools_dir.mkdir(parents=True, exist_ok=True)
            log("tools", f"[ToolLoader] Folder dibuat: {tools_dir}")
            return []

        tools = []
        for filepath in sorted(tools_dir.glob("*.py")):
            # Lewati template dan file yang diawali underscore
            if filepath.name.startswith("_") or filepath.name == "TOOL_TEMPLATE.py":
                continue

            tool = ToolLoader.load_from_file(filepath)
            if tool:
                tools.append(tool)

        log("tools", f"[ToolLoader] Scan selesai — {len(tools)} custom tool ditemukan")
        return tools
