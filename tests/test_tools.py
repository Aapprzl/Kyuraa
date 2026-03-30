import pytest
from pathlib import Path
import tempfile
import shutil

from src.tools.registry import ToolRegistry, ALLOWED_PATHS


class TestToolRegistry:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ToolRegistry()
        self.test_file = Path(self.temp_dir) / "test.txt"
        self.allowed_file = Path("workspace/output") / "test_output.txt"
        Path("workspace/output").mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        if self.test_file.exists():
            self.test_file.unlink()
        if self.allowed_file.exists():
            self.allowed_file.unlink()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_language_arabic(self):
        result = self.registry.execute("detect_language", teks="مرحبا")
        assert result["success"] is True
        assert result["result"] == "arabic"

    def test_detect_language_indonesian(self):
        result = self.registry.execute("detect_language", teks="Selamat pagi")
        assert result["success"] is True
        assert result["result"] == "indonesian"

    def test_write_file_to_disallowed_path_raises_permission_error(self):
        result = self.registry.execute("write_file", path=str(self.test_file), content="test")
        assert result["success"] is False
        assert "PermissionError" in result["error"] or "not allowed" in result["error"]

    def test_write_file_to_allowed_path_succeeds(self):
        result = self.registry.execute("write_file", path=str(self.allowed_file), content="test content")
        assert result["success"] is True
        assert result["result"] is True
        assert self.allowed_file.exists()

    def test_read_file_returns_correct_content(self):
        self.allowed_file.write_text("hello world", encoding="utf-8")
        result = self.registry.execute("read_file", path=str(self.allowed_file))
        assert result["success"] is True
        assert result["result"] == "hello world"

    def test_list_tools(self):
        tools = self.registry.list_tools()
        assert "detect_language" in tools
        assert "read_file" in tools
        assert "write_file" in tools

    def test_execute_nonexistent_tool(self):
        result = self.registry.execute("nonexistent_tool")
        assert result["success"] is False
        assert "not found" in result["error"]
