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


from src.utils.logger import log

class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: int = 120,
    ):
        # 1. Determine Provider
        self._provider = os.environ.get("ACTIVE_PROVIDER", "openrouter").lower()
        
        # 2. Get Credentials based on Provider
        if self._provider == "google":
            self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
            raw_model = model or os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")
            # Strip 'google/' prefix and OpenRouter ':free' or ':online' suffixes for Google Direct API
            self._model_name = raw_model.replace("google/", "").split(":")[0]
            self._base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        else:
            self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
            self._model_name = model or os.environ.get("OPENROUTER_MODEL") or os.environ.get("AGENT_MODEL", "qwen/qwen3.6-plus:free")
            self._base_url = "https://openrouter.ai/api/v1"

        if not self._api_key:
            prefix = "GOOGLE" if self._provider == "google" else "OPENROUTER"
            raise ValueError(
                f"{prefix}_API_KEY is required for {self._provider}. Set it in .env or settings."
            )

        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=timeout,
        )
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
                log("warn", f"Context too long ({tokens} tokens), truncating history...")
                messages = self._truncate_history(list(messages))
            else:
                log("warn", f"Context length ({tokens} tokens) exceeds recommended limit")

        openai_messages = self._build_openai_messages(system, list(messages))

        for attempt in range(3):
            try:
                log("llm", f"Request sent → {self._model_name}")
                start_time = time.time()
                response = self._client.chat.completions.create(
                    model=self._model_name,
                    messages=openai_messages,
                    max_tokens=self._max_tokens,
                    temperature=0.7,
                )
                duration = round(time.time() - start_time, 2)
                content = response.choices[0].message.content or ""
                usage = response.usage
                
                input_tokens = usage.prompt_tokens if usage else tokens
                output_tokens = usage.completion_tokens if usage else self.count_tokens([{"content": content}])
                log("llm", f"Response received — {input_tokens + output_tokens} tokens — {duration}s")
                
                return {
                    "content": content,
                    "model": self._model_name,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    },
                    "stop_reason": response.choices[0].finish_reason or "stop",
                }
            except Exception as e:
                error_str = str(e)
                log("error", f"LLM error: {error_str}")
                if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                    if attempt < 2:
                        log("warn", f"Rate limit hit, retrying in 5 seconds... (attempt {attempt + 1}/3)")
                        time.sleep(5)
                    else:
                        raise
                elif "timeout" in error_str.lower() or "deadline" in error_str.lower():
                    raise TimeoutError(f"Request timed out after {self._timeout}s")
                elif "connection" in error_str.lower() or "network" in error_str.lower():
                    if attempt < 1:
                        log("warn", f"Network error, retrying... (attempt {attempt + 1}/2)")
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
    ) -> Generator[tuple[str, dict | None], None, None]:
        tokens = self.count_tokens(messages)
        if tokens > self._max_tokens * 3:
            log("warn", f"Context too long ({tokens} tokens), truncating history for stream...")
            messages = self._truncate_history(list(messages))

        openai_messages = self._build_openai_messages(system, list(messages))

        try:
            log("llm", f"Request sent (stream) → {self._model_name}")
            start_time = time.time()
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=openai_messages,
                max_tokens=self._max_tokens,
                temperature=0.7,
                stream=True,
            )
            first_token = True
            usage = None
            for chunk in response:
                if first_token:
                    duration = round(time.time() - start_time, 2)
                    log("llm", f"First token received — {duration}s")
                    first_token = False
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = chunk.usage
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield (delta.content, usage)
            if usage is None:
                log("llm", "Usage not captured during stream, may not be available for this model")
        except Exception as e:
            log("error", f"LLM Stream error: {e}")
            if "timeout" in str(e).lower() or "deadline" in str(e).lower():
                raise TimeoutError(f"Stream request timed out after {self._timeout}s")
            raise

    def count_tokens(self, messages: Sequence[dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += len(content) // 4
        return total
