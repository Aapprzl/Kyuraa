from pathlib import Path
import yaml

from src.utils.logger import log

SKILLS_DIR = Path("workspace/skills")


class SkillManager:
    def __init__(self):
        self.skills_dir = SKILLS_DIR
        self.available_skills: dict = {}
        self.active_skill: str | None = None
        self.active_skill_content: str | None = None
        self.active_references: dict[str, str] = {}

    def discover(self) -> dict:
        if not self.skills_dir.exists():
            log("skill", f"Skills directory not found: {self.skills_dir}")
            return {}

        self.available_skills = {}

        for folder in self.skills_dir.iterdir():
            if not folder.is_dir():
                continue

            skill_md_path = folder / "SKILL.md"
            if not skill_md_path.exists():
                continue

            try:
                content = skill_md_path.read_text(encoding="utf-8")
                metadata = self._parse_frontmatter(content)
                if not metadata:
                    continue

                name = metadata.get("name", folder.name)
                self.available_skills[name] = {
                    "name": name,
                    "description": metadata.get("description", ""),
                    "trigger_keywords": metadata.get("trigger_keywords", []),
                    "references": metadata.get("references", {}),
                    "folder_path": str(folder),
                    "skill_md_path": str(skill_md_path),
                }
            except Exception as e:
                log("skill", f"Failed to load skill from {folder}: {e}")
                continue

        skill_names = ", ".join(self.available_skills.keys())
        log("skill", f"Discovered {len(self.available_skills)} skills: {skill_names}")

        return self.available_skills

    def _parse_frontmatter(self, content: str) -> dict | None:
        if not content.startswith("---"):
            return None

        try:
            parts = content.split("---", 2)
            if len(parts) < 3:
                return None
            yaml_content = parts[1]
            metadata = yaml.safe_load(yaml_content)
            return metadata if isinstance(metadata, dict) else None
        except Exception:
            return None

    def get_skills_summary(self) -> str:
        if not self.available_skills:
            return ""

        lines = ["## Skill Tersedia\n"]

        for name, info in self.available_skills.items():
            desc = info.get("description", "")
            if isinstance(desc, list):
                desc = " ".join(desc)
            desc_clean = desc.replace("\n", " ").strip()
            lines.append(f"- {name}: {desc_clean}")

        lines.append("")
        lines.append("Gunakan: 'aktifkan skill [nama]' atau")
        lines.append("         'gunakan skill [nama]'")

        return "\n".join(lines)

    def activate(self, skill_name: str) -> bool:
        if skill_name not in self.available_skills:
            available = ", ".join(self.available_skills.keys()) if self.available_skills else "none"
            raise ValueError(
                f"Skill '{skill_name}' tidak ditemukan. "
                f"Available skills: {available}"
            )

        skill_info = self.available_skills[skill_name]
        skill_md_path = Path(skill_info["skill_md_path"])

        try:
            self.active_skill_content = skill_md_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ValueError(f"Gagal membaca SKILL.md untuk '{skill_name}': {e}")

        self.active_skill = skill_name
        self.active_references = {}

        log("skill", f"Activated: {skill_name}")
        return True

    def deactivate(self):
        if self.active_skill:
            log("skill", f"Deactivated: {self.active_skill}")

        self.active_skill = None
        self.active_skill_content = None
        self.active_references = {}

    def load_reference(self, ref_name: str) -> str | None:
        if not self.active_skill:
            return None

        if ref_name in self.active_references:
            return self.active_references[ref_name]

        skill_info = self.available_skills.get(self.active_skill)
        if not skill_info:
            return None

        folder_path = Path(skill_info["folder_path"])
        references_dir = folder_path / "references"

        ref_file = references_dir / ref_name
        if not ref_file.exists():
            ref_file = references_dir / f"{ref_name}.md"
        if not ref_file.exists():
            ref_file = folder_path / ref_name
        if not ref_file.exists():
            ref_file = folder_path / f"{ref_name}.md"

        if ref_file.exists():
            try:
                content = ref_file.read_text(encoding="utf-8")
                self.active_references[ref_name] = content
                log("skill", f"Reference loaded: {ref_name}")
                return content
            except Exception as e:
                log("skill", f"Failed to load reference {ref_name}: {e}")

        return None

    def load_always_references(self) -> dict[str, str]:
        if not self.active_skill:
            return {}

        skill_info = self.available_skills.get(self.active_skill)
        if not skill_info:
            return {}

        refs = skill_info.get("references", {})
        always_load = refs.get("always_load", [])

        result = {}
        for ref_name in always_load:
            content = self.load_reference(ref_name)
            if content:
                result[ref_name] = content

        return result

    def detect_trigger(self, user_message: str) -> str | None:
        user_lower = user_message.lower()

        for name, info in self.available_skills.items():
            keywords = info.get("trigger_keywords", [])
            for kw in keywords:
                if kw.lower() in user_lower:
                    return name

        return None

    def get_system_prompt(self) -> str:
        if not self.active_skill_content:
            return ""

        prompt_parts = [self.active_skill_content]

        always_refs = self.load_always_references()
        if always_refs:
            ref_section = "\n\n## Referensi Aktif:\n"
            for ref_name, ref_content in always_refs.items():
                ref_section += f"\n### {ref_name}\n{ref_content}\n"
            prompt_parts.append(ref_section)

        return "\n\n".join(prompt_parts)

    def is_active(self) -> bool:
        return self.active_skill is not None
