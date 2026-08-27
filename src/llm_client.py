"""
Single wrapper around the Gemini API call used by both Task 1 and Task 2.

Centralising this in one place means:
  - one spot to swap providers (see Task 4 design note on vendor lock-in)
  - one spot to enforce determinism (temperature=0, fixed nothing-random)
  - one spot to strip PII before it leaves the process, if that policy
    is ever added (see Task 4 design note on data sensitivity)
  - one spot to handle transient failures (free-tier rate limits, the
    model occasionally omitting a required field) with retries, instead
    of every caller reimplementing its own retry logic
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Type, TypeVar

import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted
from pydantic import BaseModel

load_dotenv()

_MODEL_NAME = "gemini-3.5-flash-lite"
_configured = False

T = TypeVar("T")

# Global call pacing: the free tier's per-minute quota is tight enough that
# back-to-back calls WITHIN a single test case (e.g. triage call -> judge
# call, with no gap) were enough to trigger 429s even with inter-case
# delays. Enforce a minimum spacing between every outbound call, globally,
# rather than relying on callers to remember to sleep.
_MIN_CALL_INTERVAL_SECONDS = 8.0
_last_call_time: float = 0.0


def _pace_call() -> None:
    global _last_call_time
    now = time.monotonic()
    elapsed = now - _last_call_time
    if elapsed < _MIN_CALL_INTERVAL_SECONDS:
        time.sleep(_MIN_CALL_INTERVAL_SECONDS - elapsed)
    _last_call_time = time.monotonic()


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add "
            "your free Gemini API key (https://aistudio.google.com/apikey)."
        )
    genai.configure(api_key=api_key)
    _configured = True


def _with_retries(fn: Callable[[], T], max_retries: int = 3) -> T:
    """Retry on rate limits (long backoff) and schema/validation flakes
    (short backoff). The free tier's per-minute quota is the most common
    failure mode observed in practice when running the eval harness."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except ResourceExhausted as e:
            last_error = e
            if attempt < max_retries:
                wait = 20 * (attempt + 1)
                print(f"  [rate limited, retrying in {wait}s...]")
                time.sleep(wait)
        except ValueError as e:
            last_error = e
            if attempt < max_retries:
                print(f"  [schema mismatch, retrying (attempt {attempt + 1})...]")
                time.sleep(3)
    raise last_error  # type: ignore[misc]


def call_structured(
    system_prompt: str,
    user_prompt: str,
    response_model: Type[BaseModel],
    temperature: float = 0.0,
) -> dict:
    """Call Gemini with a Pydantic-model-constrained JSON response.

    temperature=0.0 by default for determinism (Task 2 requirement).
    Retries automatically on rate limits and schema-validation flakes.
    """
    _ensure_configured()

    def _do_call() -> dict:
        _pace_call()
        model = genai.GenerativeModel(
            model_name=_MODEL_NAME,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=response_model,
            ),
        )

        try:
            raw = json.loads(response.text)
        except (json.JSONDecodeError, AttributeError) as e:
            raise ValueError(
                f"LLM did not return valid JSON: {e}\n"
                f"Raw response: {getattr(response, 'text', response)!r}"
            ) from e

        try:
            validated = response_model.model_validate(raw)
        except Exception as e:  # noqa: BLE001
            raise ValueError(
                f"LLM output didn't match the expected schema: {e}\n"
                f"Raw parsed JSON was: {json.dumps(raw, indent=2)}"
            ) from e
        return validated.model_dump()

    return _with_retries(_do_call)


def call_structured_list(
    system_prompt: str,
    user_prompt: str,
    item_model: Type[BaseModel],
    temperature: float = 0.0,
) -> list[dict]:
    """Same as call_structured but for a top-level JSON array of `item_model`.
    Retries automatically on rate limits and schema-validation flakes."""
    _ensure_configured()

    def _do_call() -> list[dict]:
        _pace_call()
        model = genai.GenerativeModel(
            model_name=_MODEL_NAME,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=list[item_model],
            ),
        )

        try:
            raw = json.loads(response.text)
        except (json.JSONDecodeError, AttributeError) as e:
            raise ValueError(
                f"LLM did not return valid JSON: {e}\n"
                f"Raw response: {getattr(response, 'text', response)!r}"
            ) from e

        try:
            return [item_model.model_validate(item).model_dump() for item in raw]
        except Exception as e:  # noqa: BLE001
            raise ValueError(
                f"LLM output didn't match the expected schema: {e}\n"
                f"Raw parsed JSON was: {json.dumps(raw, indent=2)}"
            ) from e

    return _with_retries(_do_call)