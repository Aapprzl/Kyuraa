import uuid
from typing import Any, Generator
import re

from src.agent.skill_manager import SkillManager
from src.agent.prompt_builder import PromptBuilder
from src.agent.llm_client import LLMClient
from src.memory.session_store import SessionStore
from src.tools.registry import ToolRegistry
from src.utils.logger import log


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


class AgentLoop:
    def __init__(
        self,
        session_id: str | None = None,
    ):
        self._session_id = session_id or str(uuid.uuid4())

        # SkillManager sekarang mengelola persistensi sendiri di __init__
        self._skill_manager = SkillManager()

        self._prompt_builder = PromptBuilder()
        self._llm_client = LLMClient()
        self._session_store = SessionStore()
        self._tool_registry = ToolRegistry()

        self._session_store.create_session(self._session_id)

    def _detect_style(self, user_input: str) -> str:
        input_lower = user_input.lower()
        if any(kw in input_lower for kw in ["akademik", "skripsi", "tesis", "jurnal", "abstrak"]):
            return "akademik"
        elif any(kw in input_lower for kw in ["formal", "baku", "ilmiah"]):
            return "semi-formal"
        return "non-formal"

    def run(self, user_input: str) -> dict[str, Any]:
        log("agent", f"Processing request — session: {self._session_id}")

        lang = self._detect_language(user_input)
        style = self._detect_style(user_input)

        self._session_store.add_message(self._session_id, "user", user_input)
        history = self._session_store.get_history(self._session_id, limit=20)

        needed_refs = self._prompt_builder.detect_needed_references(user_input, self._skill_manager)
        references = self._load_references(needed_refs)

        system = self._prompt_builder.build_system_with_references(
            self._skill_manager, references, self._tool_registry
        )

        messages = self._prompt_builder.build_messages(history, user_input)

        response = self._llm_client.chat(system=system, messages=messages)
        assistant_content = response.get("content", "")
        finish_reason = response.get("finish_reason")

        if finish_reason == "length":
            # Don't append warning to content, let UI handle it via finish_reason
            pass

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
            "finish_reason": finish_reason,
        }

    def run_stream(self, user_input: str) -> Generator[tuple[str, dict | None], None, dict[str, Any]]:
        log("agent", f"Processing request — session: {self._session_id}")

        lang = self._detect_language(user_input)
        style = self._detect_style(user_input)

        self._session_store.add_message(self._session_id, "user", user_input)
        history = self._session_store.get_history(self._session_id, limit=20)

        needed_refs = self._prompt_builder.detect_needed_references(user_input, self._skill_manager)
        references = self._load_references(needed_refs)

        system = self._prompt_builder.build_system_with_references(
            self._skill_manager, references, self._tool_registry
        )

        messages = self._prompt_builder.build_messages(history, user_input)

        full_response = []
        captured_usage = None
        last_finish_reason = None

        for token, usage, finish_reason in self._llm_client.stream(system=system, messages=messages):
            full_response.append(token)
            if usage:
                captured_usage = usage
            if finish_reason:
                last_finish_reason = finish_reason
            yield (token, usage, finish_reason)

        assistant_content = "".join(full_response)

        if last_finish_reason == "length":
            # Don't stream warning char by char, UI already knows it's truncated via the finish signal
            pass

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
            "finish_reason": last_finish_reason,
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
