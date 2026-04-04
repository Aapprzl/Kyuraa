import frontmatter
from pathlib import Path
from typing import Any


from src.utils.logger import log

class SkillLoader:
    def __init__(self):
        self._metadata: dict[str, Any] = {}
        self._instructions: str = ""
        self._references_dir: Path | None = None

    def load(self, skill_path: str | Path) -> "SkillLoader | None":
        path = Path(skill_path)
        if not path.exists():
            return None

        try:
            post = frontmatter.load(str(path))
        except Exception:
            return None

        self._metadata = dict(post.metadata)
        self._instructions = post.content

        ref_dir = path.parent / "references"
        self._references_dir = ref_dir if ref_dir.exists() else None

        log("agent", f"Skill loaded: {path.name}")
        return self

    def get_name(self) -> str | None:
        return self._metadata.get("name")

    def get_description(self) -> str | None:
        return self._metadata.get("description")

    def get_system_prompt(self) -> str:
        name = self.get_name() or "Untitled Skill"
        description = self.get_description() or ""
        instructions = self._instructions.strip()

        parts = [f"# {name}\n"]
        if description:
            parts.append(f"{description}\n\n")
        parts.append("## Instructions\n\n")
        parts.append(instructions)

        return "".join(parts)

    def load_reference(self, name: str) -> str | None:
        if self._references_dir is None:
            return None

        ref_path = self._references_dir / f"{name}.md"
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8")

        return None

    @property
    def metadata(self) -> dict[str, Any]:
        return self._metadata

    @property
    def instructions(self) -> str:
        return self._instructions
