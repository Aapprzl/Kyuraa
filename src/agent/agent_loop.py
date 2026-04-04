import re
import uuid
from pathlib import Path
from typing import Any, Generator

from src.agent.skill_manager import SkillManager
from src.agent.prompt_builder import PromptBuilder
from src.agent.llm_client import LLMClient
from src.memory.session_store import SessionStore
from src.tools.registry import ToolRegistry


TOOL_CALL_PATTERN = re.compile(
    r'\[TOOL:\s*(\w+)\](?:\s*(\w+)="([^"]*)")*',
    re.IGNORECASE
)


def parse_tool_calls(response_text: str) -> list[dict[str, Any]]:
    tool_calls = []
    pattern = re.compile(r'\[TOOL:\s*(\w+)\](.*?)(?=\[TOOL:|$)', re.IGNORECASE | re.DOTALL)

    for match in pattern.finditer(response_text):
        tool_name = match.group(1).strip().lower()
        params_str = match.group(2) or ""

        params = {}
        param_pattern = re.compile(r'(\w+)="([^"]*)"')
        for param_match in param_pattern.finditer(params_str):
            params[param_match.group(1)] = param_match.group(2)

        tool_calls.append({"tool_name": tool_name, "params": params})

    return tool_calls


from src.utils.logger import log


class AgentLoop:
    def __init__(
        self,
        session_id: str | None = None,
    ):
        self._session_id = session_id or str(uuid.uuid4())

        self._skill_manager = SkillManager()
        self._skill_manager.discover()

        self._prompt_builder = PromptBuilder()
        self._llm_client = LLMClient()
        self._session_store = SessionStore()
        self._tool_registry = ToolRegistry()

        self._session_store.create_session(self._session_id)

    def handle_skill_command(self, user_message: str) -> tuple[bool, str | None, str | None]:
        msg_lower = user_message.lower()

        activate_patterns = [
            r'aktifkan\s+skill\s+(\S+)',
            r'gunakan\s+skill\s+(\S+)',
            r'pakai\s+skill\s+(\S+)',
            r'enable\s+skill\s+(\S+)',
            r'use\s+skill\s+(\S+)',
        ]

        deactivate_patterns = [
            'nonaktifkan skill',
            'matikan skill',
            'keluar dari skill',
            'exit skill',
            'deactivate skill',
            'disable skill',
            'keluar skill',
        ]

        for pattern in activate_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                skill_name = match.group(1).strip()
                try:
                    self._skill_manager.activate(skill_name)
                    return (True, 'activated', skill_name)
                except ValueError as e:
                    return (True, 'error', str(e))

        for pattern in deactivate_patterns:
            if pattern in msg_lower:
                self._skill_manager.deactivate()
                return (True, 'deactivated', None)

        detected = self._skill_manager.detect_trigger(user_message)
        if detected:
            return (True, 'suggest', detected)

        return (False, None, None)

    def _detect_style(self, user_input: str) -> str:
        input_lower = user_input.lower()
        if any(kw in input_lower for kw in ["akademik", "skripsi", "tesis", "jurnal", "abstrak"]):
            return "akademik"
        elif any(kw in input_lower for kw in ["formal", "baku", "ilmiah"]):
            return "semi-formal"
        return "non-formal"

    def run(self, user_input: str) -> dict[str, Any]:
        log("agent", f"Processing request — session: {self._session_id}")

        is_skill_cmd, action, data = self.handle_skill_command(user_input)

        if action == 'activated':
            skill_info = self._skill_manager.available_skills.get(data, {})
            desc = skill_info.get("description", "")
            if isinstance(desc, list):
                desc = " ".join(desc)
            return {
                "session_id": self._session_id,
                "language": "mixed",
                "style": "command",
                "response": f"✅ Skill **{data}** aktif!\n\n{desc}\n\nSilakan kirim teks yang ingin diterjemahkan.",
                "skill_activated": data,
                "tool_results": [],
            }

        if action == 'deactivated':
            return {
                "session_id": self._session_id,
                "language": "mixed",
                "style": "command",
                "response": "✅ Skill dinonaktifkan. Saya kembali sebagai asisten biasa.",
                "skill_deactivated": True,
                "tool_results": [],
            }

        if action == 'error':
            return {
                "session_id": self._session_id,
                "language": "mixed",
                "style": "command",
                "response": f"❌ {data}",
                "tool_results": [],
            }

        lang = self._detect_language(user_input)
        style = self._detect_style(user_input)

        self._session_store.add_message(self._session_id, "user", user_input)

        history = self._session_store.get_history(self._session_id, limit=10)

        needed_refs = self._prompt_builder.detect_needed_references(user_input, self._skill_manager)
        references = self._load_references(needed_refs)

        system = self._prompt_builder.build_system_with_references(
            self._skill_manager, references
        )

        messages = self._prompt_builder.build_messages(history, user_input)

        response = self._llm_client.chat(system=system, messages=messages)
        assistant_content = response.get("content", "")

        self._session_store.add_message(self._session_id, "assistant", assistant_content)

        tool_results = self._execute_tool_calls(assistant_content)

        log("agent", f"Response complete — {len(assistant_content.split())} words")
        return {
            "session_id": self._session_id,
            "language": lang,
            "style": style,
            "response": assistant_content,
            "usage": response.get("usage", {}),
            "references_loaded": list(references.keys()),
            "tool_results": tool_results,
        }

    def run_stream(self, user_input: str) -> Generator[tuple[str, dict | None], None, dict[str, Any]]:
        log("agent", f"Processing request — session: {self._session_id}")

        is_skill_cmd, action, data = self.handle_skill_command(user_input)

        if action == 'activated':
            skill_info = self._skill_manager.available_skills.get(data, {})
            desc = skill_info.get("description", "")
            if isinstance(desc, list):
                desc = " ".join(desc)
            response_text = f"✅ Skill **{data}** aktif!\n\n{desc}\n\nSilakan kirim teks yang ingin diterjemahkan."
            for char in response_text:
                yield (char, None)
            return {
                "session_id": self._session_id,
                "language": "mixed",
                "style": "command",
                "response": response_text,
                "skill_activated": data,
                "tool_results": [],
            }

        if action == 'deactivated':
            response_text = "✅ Skill dinonaktifkan. Saya kembali sebagai asisten biasa."
            for char in response_text:
                yield (char, None)
            return {
                "session_id": self._session_id,
                "language": "mixed",
                "style": "command",
                "response": response_text,
                "skill_deactivated": True,
                "tool_results": [],
            }

        if action == 'error':
            response_text = f"❌ {data}"
            for char in response_text:
                yield (char, None)
            return {
                "session_id": self._session_id,
                "language": "mixed",
                "style": "command",
                "response": response_text,
                "tool_results": [],
            }

        lang = self._detect_language(user_input)
        style = self._detect_style(user_input)

        self._session_store.add_message(self._session_id, "user", user_input)

        history = self._session_store.get_history(self._session_id, limit=10)

        needed_refs = self._prompt_builder.detect_needed_references(user_input, self._skill_manager)
        references = self._load_references(needed_refs)

        system = self._prompt_builder.build_system_with_references(
            self._skill_manager, references
        )

        messages = self._prompt_builder.build_messages(history, user_input)

        full_response = []
        captured_usage = None
        for token, usage in self._llm_client.stream(system=system, messages=messages):
            full_response.append(token)
            if usage:
                captured_usage = usage
            yield (token, usage)

        assistant_content = "".join(full_response)
        self._session_store.add_message(self._session_id, "assistant", assistant_content)

        tool_results = self._execute_tool_calls(assistant_content)

        log("agent", f"Response complete — {len(assistant_content.split())} words")
        return {
            "session_id": self._session_id,
            "language": lang,
            "style": style,
            "response": assistant_content,
            "references_loaded": list(references.keys()),
            "tool_results": tool_results,
            "usage": captured_usage,
        }

    def _detect_language(self, text: str) -> str:
        result = self._tool_registry.execute("detect_language", teks=text)
        return result.get("result", "indonesian")

    def _load_references(self, ref_names: list[str]) -> dict[str, str]:
        references = {}
        for ref in ref_names:
            content = self._skill_manager.load_reference(ref)
            if content:
                references[ref] = content
                log("agent", f"Reference loaded: {ref}")
        return references

    def _execute_tool_calls(self, text: str) -> list[dict[str, Any]]:
        tool_calls = parse_tool_calls(text)
        results = []
        for call in tool_calls:
            tool_name = call["tool_name"]
            params = call["params"]
            result = self._tool_registry.execute(tool_name, **params)
            results.append({
                "tool": tool_name,
                "params": params,
                "result": result,
            })
        return results

    def execute_tool(self, tool_name: str, **kwargs) -> dict[str, Any]:
        return self._tool_registry.execute(tool_name, **kwargs)

    def save_translation(self, filename: str, content: str) -> str:
        result = self._tool_registry.execute(
            "save_translation", filename=filename, content=content
        )
        return result.get("result", "")

    def get_history(self, limit: int = 20) -> list[dict]:
        return self._session_store.get_history(self._session_id, limit=limit)

    def clear_history(self) -> bool:
        return self._session_store.clear_session(self._session_id)

    @property
    def session_id(self) -> str:
        return self._session_id
