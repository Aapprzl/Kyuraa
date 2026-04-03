import os
import time
from pathlib import Path
from typing import Any, Generator, Sequence

from openai import OpenAI


def _load_env():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
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
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is required. Set it in .env or pass api_key parameter."
            )

        self._client = OpenAI(
            api_key=self._api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=timeout,
        )
        self._model_name = model or os.environ.get("AGENT_MODEL", "qwen/qwen3.6-plus:free")
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

        openai_messages = self._build_openai_messages(system, list(messages))

        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self._model_name,
                    messages=openai_messages,
                    max_tokens=self._max_tokens,
                    temperature=0.7,
                )
                content = response.choices[0].message.content or ""
                usage = response.usage
                return {
                    "content": content,
                    "model": self._model_name,
                    "usage": {
                        "input_tokens": usage.prompt_tokens if usage else tokens,
                        "output_tokens": usage.completion_tokens if usage else self.count_tokens([{"content": content}]),
                    },
                    "stop_reason": response.choices[0].finish_reason or "stop",
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

    def _build_openai_messages(
        self, system: str, messages: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        result = [{"role": "system", "content": system}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            result.append({"role": role, "content": content})
        return result

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

        openai_messages = self._build_openai_messages(system, list(messages))

        try:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=openai_messages,
                max_tokens=self._max_tokens,
                temperature=0.7,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content
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
