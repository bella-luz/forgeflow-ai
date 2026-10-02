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


def _post(messages: list[dict], temperature: float) -> str:
    key = config.get("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY is not set")
    payload = {
        "model": config.get("GROQ_MODEL", config.DEFAULT_GROQ_MODEL),
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    last = ""
    for attempt in range(3):
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
            if resp.status_code not in (429, 500, 502, 503):
                break
        time.sleep(2 * (attempt + 1))
    raise LLMError(f"Groq request failed ({last})")


def complete_json(system: str, user: str, model_cls: type[T], temperature: float = 0.3) -> T:
    """Ask for JSON matching model_cls. One repair attempt on invalid output."""
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
        raw = _post(messages, temperature)
        try:
            return model_cls.model_validate_json(raw)
        except ValidationError as exc:
            error = str(exc)[:600]
            messages += [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"That JSON was invalid: {error}\nReturn corrected JSON only."},
            ]
    raise LLMError(f"Model output did not match {model_cls.__name__}: {error}")
