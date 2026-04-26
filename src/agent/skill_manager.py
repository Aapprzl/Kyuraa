from pathlib import Path
import json
import yaml

from src.utils.logger import log

SKILLS_DIR = Path("workspace/skills")
SETTINGS_PATH = Path("workspace/settings.json")


def _load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


class SkillManager:
    def __init__(self):
        self.skills_dir = SKILLS_DIR
        self.available_skills: dict = {}
        self.active_skill: str | None = None
        self.active_skill_content: str | None = None
        self.active_references: dict[str, str] = {}

        # Discover skills terlebih dahulu, lalu restore state persisten
        self.discover()
        self._restore_state()

    def _restore_state(self):
        """Muat state active_skill dari settings.json saat init."""
        settings = _load_settings()
        saved_skill = settings.get("active_skill")
        if saved_skill and saved_skill in self.available_skills:
            try:
                self._do_activate(saved_skill)
                log("skill", f"Restored active skill from settings: {saved_skill}")
            except Exception as e:
                log("skill", f"Failed to restore skill '{saved_skill}': {e}")

    def _save_state(self):
        """Simpan active_skill ke settings.json."""
        settings = _load_settings()
        settings["active_skill"] = self.active_skill
        _save_settings(settings)

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
                desc = metadata.get("description", "")
                if isinstance(desc, list):
                    desc = " ".join(desc)

                self.available_skills[name] = {
                    "name": name,
                    "description": str(desc).replace("\n", " ").strip(),
                    "version": str(metadata.get("version", "1.0")),
                    "author": metadata.get("author", "Unknown"),
                    "category": metadata.get("category", "Umum"),
                    "trigger_keywords": metadata.get("trigger_keywords", []),
                    "references": metadata.get("references", {}),
                    "folder_path": str(folder),
                    "skill_md_path": str(skill_md_path),
                }
            except Exception as e:
                log("skill", f"Failed to load skill from {folder}: {e}")
                continue

        skill_names = ", ".join(self.available_skills.keys())
        log("skill", f"Discovered {len(self.available_skills)} skills: {skill_names or 'none'}")
        return self.available_skills

    def reload(self) -> dict:
        """Rescan folder skills tanpa restart server. Pertahankan skill aktif jika masih ada."""
        current_active = self.active_skill
        self.discover()

        # Jika skill yang aktif masih ada setelah reload, re-aktifkan
        if current_active and current_active in self.available_skills:
            try:
                self._do_activate(current_active)
            except Exception:
                self.active_skill = None
                self._save_state()
        elif current_active and current_active not in self.available_skills:
            # Skill aktif hilang (folder dihapus) — nonaktifkan
            log("skill", f"Active skill '{current_active}' no longer exists after reload, deactivating.")
            self.active_skill = None
            self.active_skill_content = None
            self.active_references = {}
            self._save_state()

        log("skill", f"Reload selesai — {len(self.available_skills)} skill ditemukan")
        return {
            "total": len(self.available_skills),
            "active_skill": self.active_skill,
        }

    def list_skills_detail(self) -> list[dict]:
        """Kembalikan metadata lengkap semua skills beserta status aktif."""
        result = []
        for name, info in self.available_skills.items():
            folder_path = Path(info.get("folder_path", ""))
            refs_dir = folder_path / "references"
            refs_count = len(list(refs_dir.glob("*"))) if refs_dir.exists() else 0

            result.append({
                "name": name,
                "description": info.get("description", ""),
                "version": info.get("version", "1.0"),
                "author": info.get("author", "Unknown"),
                "category": info.get("category", "Umum"),
                "references_count": refs_count,
                "is_active": self.active_skill == name,
            })
        return sorted(result, key=lambda x: x["name"])

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

    def _do_activate(self, skill_name: str):
        """Internal: lakukan aktivasi tanpa menyimpan state (digunakan oleh restore)."""
        skill_info = self.available_skills[skill_name]
        skill_md_path = Path(skill_info["skill_md_path"])
        self.active_skill_content = skill_md_path.read_text(encoding="utf-8")
        self.active_skill = skill_name
        self.active_references = {}

    def activate(self, skill_name: str) -> bool:
        if skill_name not in self.available_skills:
            available = ", ".join(self.available_skills.keys()) if self.available_skills else "none"
            raise ValueError(f"Skill '{skill_name}' tidak ditemukan. Tersedia: {available}")

        try:
            self._do_activate(skill_name)
        except Exception as e:
            raise ValueError(f"Gagal membaca SKILL.md untuk '{skill_name}': {e}")

        self._save_state()
        log("skill", f"Activated: {skill_name}")
        return True

    def deactivate(self):
        if self.active_skill:
            log("skill", f"Deactivated: {self.active_skill}")
        self.active_skill = None
        self.active_skill_content = None
        self.active_references = {}
        self._save_state()

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

        for candidate in [
            references_dir / ref_name,
            references_dir / f"{ref_name}.md",
            folder_path / ref_name,
            folder_path / f"{ref_name}.md",
        ]:
            if candidate.exists():
                try:
                    content = candidate.read_text(encoding="utf-8")
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

    def get_skills_summary(self) -> str:
        """Ringkasan skill tersedia untuk dimasukkan ke system prompt (saat tidak ada skill aktif)."""
        if not self.available_skills:
            return ""
        lines = ["## Skill Tersedia\n"]
        for name, info in self.available_skills.items():
            desc = info.get("description", "")
            lines.append(f"- **{name}**: {desc}")
        lines.append("\nSkill dapat diaktifkan dari panel Pengaturan.")
        return "\n".join(lines)

    def get_system_prompt(self) -> str:
        """Kembalikan isi SKILL.md saja. Referensi diurus oleh agent_loop dan
        diinjeksi oleh PromptBuilder.build_system_with_references() agar tidak
        ada referensi yang dimuat dua kali."""
        if not self.active_skill_content:
            return ""
        return self.active_skill_content

    def is_active(self) -> bool:
        return self.active_skill is not None
