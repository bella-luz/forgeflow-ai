"""Groq chat completions returning validated Pydantic objects."""
from __future__ import annotations

import json
import time
from typing import TypeVar

import requests
from pydantic import BaseModel, ValidationError

from . import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """The LLM is not configured, unreachable, or returned unusable output."""


def _wait_seconds(resp: requests.Response | None, attempt: int) -> float:
    """Groq says how long to wait on HTTP 429; otherwise back off a little."""
    if resp is not None and resp.status_code == 429:
        try:
            return min(float(resp.headers.get("retry-after", "")), 30.0)
        except ValueError:
            return 15.0
    return 2.0 * (attempt + 1)


def _post(messages: list[dict], temperature: float, fast: bool = False) -> str:
    key = config.get("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY is not set")
    payload = {
        "model": config.get("GROQ_FAST_MODEL", config.DEFAULT_FAST_MODEL) if fast else config.get("GROQ_MODEL", config.DEFAULT_GROQ_MODEL),
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    last = ""
    for attempt in range(3):
        resp = None
        try:
            resp = requests.post(
                GROQ_URL,
                json=payload,
                headers={"Authorization": f"Bearer {key}"},
                timeout=config.HTTP_TIMEOUT * 2,
            )
        except requests.RequestException as exc:
            last = f"network error: {type(exc).__name__}"
        else:
            if resp.status_code == 200:
                try:
                    return resp.json()["choices"][0]["message"]["content"]
                except (ValueError, KeyError, IndexError):
                    raise LLMError("Groq returned an unexpected response shape")
            last = f"HTTP {resp.status_code}"
            # json_validate_failed: the model produced malformed JSON; a fresh attempt usually succeeds.
            retry_400 = resp.status_code == 400 and "json_validate_failed" in resp.text
            if resp.status_code not in (429, 500, 502, 503) and not retry_400:
                break
        time.sleep(_wait_seconds(resp, attempt))
    if last == "HTTP 429":
        raise LLMError("the free AI quota is busy (HTTP 429); wait a minute and try again")
    raise LLMError(f"Groq request failed ({last})")


def complete_json(system: str, user: str, model_cls: type[T], temperature: float = 0.3, fast: bool = False) -> T:
    """Ask for JSON matching model_cls. With fast=True, try the small model first and fall back to the main one."""
    if fast:
        try:
            return _complete_json(system, user, model_cls, temperature, fast=True)
        except LLMError:
            pass
    return _complete_json(system, user, model_cls, temperature, fast=False)


def _complete_json(system: str, user: str, model_cls: type[T], temperature: float, fast: bool) -> T:
    """One model, one repair attempt on invalid output."""
    schema = json.dumps(model_cls.model_json_schema())
    messages = [
        {
            "role": "system",
            "content": f"{system}\n\nRespond with one JSON object only, matching this JSON schema:\n{schema}",
        },
        {"role": "user", "content": user},
    ]
    error = ""
    for _ in range(2):
        raw = _post(messages, temperature, fast)
        try:
            return model_cls.model_validate_json(raw)
        except ValidationError as exc:
            error = str(exc)[:600]
            messages += [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"That JSON was invalid: {error}\nReturn corrected JSON only."},
            ]
    raise LLMError(f"Model output did not match {model_cls.__name__}: {error}")
