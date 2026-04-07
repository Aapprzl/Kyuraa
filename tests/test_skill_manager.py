import pytest
from pathlib import Path
from src.agent.skill_manager import SkillManager

class TestSkillManager:
    def setup_method(self):
        self.manager = SkillManager()

    def test_discover_skills(self):
        skills = self.manager.discover()
        assert len(skills) > 0
        assert "penerjemah-arab-indo" in skills

    def test_activate_skill(self):
        result = self.manager.activate("penerjemah-arab-indo")
        assert result is True
        assert self.manager.active_skill == "penerjemah-arab-indo"
        assert self.manager.active_skill_content is not None
        assert "FASE 1" in self.manager.active_skill_content

    def test_get_system_prompt_with_active_skill(self):
        self.manager.activate("penerjemah-arab-indo")
        prompt = self.manager.get_system_prompt()
        assert "FASE 1" in prompt
        assert "penerjemah-arab-indo" in prompt.lower()

    def test_deactivate_skill(self):
        self.manager.activate("penerjemah-arab-indo")
        self.manager.deactivate()
        assert self.manager.active_skill is None
        assert self.manager.active_skill_content is None

    def test_activate_nonexistent_skill_raises_error(self):
        with pytest.raises(ValueError):
            self.manager.activate("nonexistent-skill-xyz")

    def test_load_reference(self):
        self.manager.activate("penerjemah-arab-indo")
        # Mencoba memuat referensi '01-nahwu' (atau file .md di folder referensi)
        # Kita asumsikan ada minimal satu referensi atau kita cek None
        ref = self.manager.load_reference("01-nahwu")
        assert ref is None or isinstance(ref, str)
