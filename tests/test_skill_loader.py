import pytest
from pathlib import Path

from src.agent.skill_loader import SkillLoader

SKILL_PATH = Path(__file__).parent.parent / "src" / "skills" / "SKILL.md"


class TestSkillLoader:
    def test_load_skill_md_without_error(self):
        loader = SkillLoader()
        result = loader.load(SKILL_PATH)
        assert result is not None
        assert loader.get_name() is not None

    def test_name_is_penerjemah_arab_indo(self):
        loader = SkillLoader()
        loader.load(SKILL_PATH)
        assert loader.get_name() == "penerjemah-arab-indo"

    def test_get_system_prompt_contains_fase_1(self):
        loader = SkillLoader()
        loader.load(SKILL_PATH)
        prompt = loader.get_system_prompt()
        assert "FASE 1" in prompt

    def test_load_reference_returns_string_or_none(self):
        loader = SkillLoader()
        loader.load(SKILL_PATH)
        result = loader.load_reference("01-nahwu")
        assert result is None or isinstance(result, str)

    def test_nonexistent_file_returns_none(self):
        loader = SkillLoader()
        result = loader.load(Path("/nonexistent/file/SKILL.md"))
        assert result is None

    def test_get_reference_from_nonexistent_returns_none(self):
        loader = SkillLoader()
        loader.load(SKILL_PATH)
        result = loader.load_reference("nonexistent-reference")
        assert result is None
