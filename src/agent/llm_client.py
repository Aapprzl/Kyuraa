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
                if key.strip() not in os.environ:
                    os.environ[key.strip()] = value.strip()


_load_env()


from src.utils.logger import log
from src.config import (
    LLM_MAX_TOKENS, LLM_MAX_INPUT_TOKENS, LLM_TEMPERATURE, 
    LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES
)

class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        timeout: int = LLM_TIMEOUT_SECONDS,
    ):
        # 1. Determine Provider
        self._provider = os.environ.get("ACTIVE_PROVIDER", "openrouter").lower()
        
        # 2. Get Credentials based on Provider
        if self._provider == "google":
            self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
            raw_model = model or os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")
            # Strip 'google/' prefix if coming from OpenRouter config
            self._model_name = raw_model.replace("google/", "").split(":")[0]

            self._base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        else:
            self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
            self._model_name = model or os.environ.get("OPENROUTER_MODEL") or os.environ.get("AGENT_MODEL", "qwen/qwen2.5-72b-instruct")
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
        self._max_tokens = max_tokens or LLM_MAX_TOKENS
        # Max input context estimation limit (context window saftey)
        self._max_input_estimate = LLM_MAX_INPUT_TOKENS 
        self._timeout = timeout

    def chat(
        self,
        system: str,
        messages: Sequence[dict[str, str]],
        truncate_history: bool = True,
    ) -> dict[str, Any]:
        tokens = self.count_tokens(messages)
        if tokens > self._max_input_estimate:
            if truncate_history:
                log("warn", f"Context too long (~{tokens} tokens), truncating history...")
                messages = self._truncate_history(list(messages))
            else:
                log("warn", f"Context length (~{tokens} tokens) exceeds recommended limit")

        openai_messages = self._build_openai_messages(system, list(messages))

        for attempt in range(LLM_MAX_RETRIES):
            try:
                log("llm", f"Request sent → {self._model_name}")
                start_time = time.time()
                response = self._client.chat.completions.create(
                    model=self._model_name,
                    messages=openai_messages,
                    max_tokens=self._max_tokens,
                    temperature=LLM_TEMPERATURE,
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
                    if attempt < LLM_MAX_RETRIES - 1:
                        log("warn", f"Rate limit hit, retrying in 5 seconds... (attempt {attempt + 1}/{LLM_MAX_RETRIES})")
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
    ) -> Generator[tuple[str, dict | None, str | None], None, None]:
        tokens = self.count_tokens(messages)
        if tokens > self._max_input_estimate:
            log("warn", f"Context too long (~{tokens} tokens), truncating history for stream...")
            messages = self._truncate_history(list(messages))

        openai_messages = self._build_openai_messages(system, list(messages))

        try:
            log("llm", f"Request sent (stream) → {self._model_name}")
            start_time = time.time()
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=openai_messages,
                max_tokens=self._max_tokens,
                temperature=LLM_TEMPERATURE,
                stream=True,
            )
            first_token = True
            usage = None
            finish_reason = None
            for chunk in response:
                if first_token:
                    duration = round(time.time() - start_time, 2)
                    log("llm", f"First token received — {duration}s")
                    first_token = False
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = chunk.usage
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason
                if hasattr(delta, "content") and delta.content:
                    yield (delta.content, usage, finish_reason)
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
            # More conservative estimation for Indonesian/Arabic (divide by 3 instead of 4)
            total += len(content) // 3
        return total

    def summarize(self, messages: Sequence[dict[str, str]]) -> str:
        """Merangkum percakapan dalam bahasa Indonesia."""
        if not messages:
            return "Tidak ada percakapan untuk dirangkum."
            
        summary_prompt = "Tolong buat ringkasan eksekutif yang sangat singkat dan padat (maksimal 2 paragraf) dari percakapan di atas dalam Bahasa Indonesia. Fokus pada poin-poin utama yang sudah dibahas dan riwayat dokumen yang dilampirkan agar sesi berikutnya bisa langsung nyambung."
        
        # Buat request khusus untuk merangkum
        temp_messages = list(messages)
        temp_messages.append({"role": "user", "content": summary_prompt})
        
        try:
            res = self.chat("Anda adalah asisten perangkum yang handal.", temp_messages, truncate_history=True)
            return res.get("content", "Gagal menghasilkan ringkasan.")
        except Exception as e:
            log("error", f"Summarization failed: {e}")
            return "Terjadi kesalahan saat merangkum percakapan."
