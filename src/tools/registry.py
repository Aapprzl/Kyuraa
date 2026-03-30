import subprocess
from pathlib import Path
from typing import Any, Callable

from src.memory.glossary_store import GlossaryStore


ALLOWED_PATHS = [
    "C:\\agent-arab\\workspace\\output",
    "C:\\agent-arab\\workspace\\glossary",
    "C:\\Users\\Muh Aprizal\\Documents\\terjemahan",
]


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._output_dir = Path("workspace/output")
        self._reference_dir = Path("src/skills/references")
        self._glossary = GlossaryStore()
        self._register_tools()

    def _register_tools(self) -> None:
        self._tools = {
            "detect_language": self._detect_language,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "save_translation": self._save_translation,
            "list_output_files": self._list_output_files,
            "load_reference": self._load_reference,
            "save_glossary_term": self._save_glossary_term,
            "open_output_folder": self._open_output_folder,
        }

    def _is_safe_path(self, path: str) -> bool:
        resolved = Path(path).resolve()
        return any(
            str(resolved).startswith(str(Path(ap).resolve()))
            for ap in ALLOWED_PATHS
        )

    def register(self, name: str, func: Callable) -> None:
        self._tools[name] = func

    def get(self, name: str) -> Callable | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, **kwargs) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"success": False, "error": f"Tool '{name}' not found"}

        try:
            result = tool(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _detect_language(self, teks: str) -> str:
        arabic_chars = sum(1 for c in teks if "\u0600" <= c <= "\u06FF")
        ratio = arabic_chars / max(len(teks.strip()), 1)
        if ratio > 0.3:
            return "arabic"
        elif ratio > 0.05:
            return "mixed"
        else:
            return "indonesian"

    def _read_file(self, path: str) -> str:
        if not self._is_safe_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        return Path(path).read_text(encoding="utf-8")

    def _write_file(self, path: str, content: str) -> bool:
        if not self._is_safe_path(path):
            raise PermissionError(f"Path not allowed: {path}")
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return True

    def _save_translation(self, filename: str, content: str) -> str:
        output_path = self._output_dir / filename
        if not self._is_safe_path(str(output_path)):
            raise PermissionError(f"Path not allowed: {output_path}")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return str(output_path)

    def _list_output_files(self) -> list[str]:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return [f.name for f in self._output_dir.iterdir() if f.is_file()]

    def _load_reference(self, nama_referensi: str) -> str | None:
        ref_path = self._reference_dir / f"{nama_referensi}.md"
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8")
        return None

    def _save_glossary_term(self, arab: str, indo: str, konteks: str = "") -> bool:
        self._glossary.add_term(arab, indo, konteks)
        return True

    def _open_output_folder(self) -> bool:
        try:
            if Path("output").exists():
                subprocess.run(["explorer", str(Path("output").resolve())])
            return True
        except Exception:
            return False
