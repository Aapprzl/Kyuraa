import os
import time
from pathlib import Path
from typing import Any, Generator, Sequence

from google import genai


def _load_env():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_env()


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: int = 120,
    ):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY is required. Set it in .env or pass api_key parameter.")

        self._client = genai.Client(api_key=self._api_key)
        self._model_name = model or os.environ.get("AGENT_MODEL", "gemini-2.0-flash")
        self._max_tokens = max_tokens or 4096
        self._timeout = timeout

    def chat(
        self,
        system: str,
        messages: Sequence[dict[str, str]],
        truncate_history: bool = True,
    ) -> dict[str, Any]:
        tokens = self.count_tokens(messages)
        if tokens > self._max_tokens * 3:
            if truncate_history:
                print(f"[WARN] Context too long ({tokens} tokens), truncating history...")
                messages = self._truncate_history(list(messages))
            else:
                print(f"[WARN] Context length ({tokens} tokens) exceeds recommended limit")

        full_prompt = self._build_prompt(system, list(messages))

        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=full_prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system,
                        max_output_tokens=self._max_tokens,
                        temperature=0.7,
                    ),
                )
                return {
                    "content": response.text,
                    "model": self._model_name,
                    "usage": {
                        "input_tokens": tokens,
                        "output_tokens": self.count_tokens([{"content": response.text or ""}]),
                    },
                    "stop_reason": str(response.finish_reason) if hasattr(response, 'finish_reason') else "stop",
                }
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                    if attempt < 2:
                        print(f"[WARN] Rate limit hit, retrying in 5 seconds... (attempt {attempt + 1}/3)")
                        time.sleep(5)
                    else:
                        raise
                elif "timeout" in error_str.lower() or "deadline" in error_str.lower():
                    raise TimeoutError(f"Request timed out after {self._timeout}s")
                elif "connection" in error_str.lower() or "network" in error_str.lower():
                    if attempt < 1:
                        print(f"[WARN] Network error, retrying... (attempt {attempt + 1}/2)")
                        time.sleep(2)
                    else:
                        raise ConnectionError(f"Network error after 2 retries: {e}")
                elif "api_key" in error_str.lower() or "401" in error_str or "403" in error_str:
                    raise ValueError(f"Invalid API key: {e}")
                else:
                    raise

    def _build_prompt(self, system: str, messages: list[dict[str, str]]) -> str:
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                parts.append(f"User: {content}")
            else:
                parts.append(f"Assistant: {content}")
        return "\n\n".join(parts)

    def _truncate_history(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        half = len(messages) // 2
        return messages[-half:]

    def stream(
        self,
        system: str,
        messages: Sequence[dict[str, str]],
    ) -> Generator[str, None, None]:
        tokens = self.count_tokens(messages)
        if tokens > self._max_tokens * 3:
            print(f"[WARN] Context too long ({tokens} tokens), truncating history for stream...")
            messages = self._truncate_history(list(messages))

        full_prompt = self._build_prompt(system, list(messages))

        try:
            response = self._client.models.generate_content_stream(
                model=self._model_name,
                contents=full_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=self._max_tokens,
                    temperature=0.7,
                ),
            )
            for chunk in response:
                if hasattr(chunk, "text") and chunk.text:
                    yield chunk.text
        except Exception as e:
            if "timeout" in str(e).lower() or "deadline" in str(e).lower():
                raise TimeoutError(f"Stream request timed out after {self._timeout}s")
            raise

    def count_tokens(self, messages: Sequence[dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += len(content) // 4
        return total
