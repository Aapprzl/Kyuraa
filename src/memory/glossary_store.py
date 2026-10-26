import json
from datetime import datetime
from pathlib import Path


from src.utils.logger import log

class GlossaryStore:
    def __init__(self, storage_path: str | Path = "workspace/glossary/glossary.json"):
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict = {"version": "1.0", "last_updated": "", "terms": []}
        self._index_arabic: dict[str, list[int]] = {}
        self._index_indonesian: dict[str, list[int]] = {}
        self._load()

    def _load(self) -> None:
        if self._storage_path.exists():
            self._data = json.loads(self._storage_path.read_text(encoding="utf-8"))
        self._build_indexes()

    def _build_indexes(self) -> None:
        self._index_arabic = {}
        self._index_indonesian = {}
        for i, term in enumerate(self._data["terms"]):
            arabic = term.get("arabic", "")
            indonesian = term.get("indonesian", "").lower()
            if arabic:
                self._index_arabic.setdefault(arabic, []).append(i)
            if indonesian:
                self._index_indonesian.setdefault(indonesian, []).append(i)

    def _save(self) -> None:
        self._data["last_updated"] = datetime.now().isoformat()
        self._storage_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add_term(self, arabic: str, indonesian: str, context: str = "", style: str = "") -> None:
        entry = {
            "arabic": arabic,
            "indonesian": indonesian,
            "context": context,
            "style": style,
            "added_at": datetime.now().isoformat(),
        }
        self._data["terms"].append(entry)
        self._build_indexes()
        self._save()
        log("memory", "Glossary updated — 1 new term")

    def lookup(self, arabic: str) -> list[dict] | None:
        indices = self._index_arabic.get(arabic)
        if indices is None:
            return None
        return [self._data["terms"][i] for i in indices]

    def lookup_reverse(self, indonesian: str) -> list[dict] | None:
        indices = self._index_indonesian.get(indonesian.lower())
        if indices is None:
            return None
        return [self._data["terms"][i] for i in indices]

    def get_all(self) -> dict:
        return self._data

    def export_to_text(self) -> str:
        lines = ["# Glosarium Arab-Indonesia\n"]
        for term in sorted(self._data["terms"], key=lambda x: x.get("arabic", "")):
            context = f" ({term.get('context', '')})" if term.get('context') else ""
            style = f" [{term.get('style', '')}]" if term.get('style') else ""
            lines.append(f"- {term['arabic']} = {term['indonesian']}{context}{style}")
        return "\n".join(lines)
