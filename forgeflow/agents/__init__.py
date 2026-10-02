"""The four worker agents. Each takes typed input and returns typed output plus a fallback note."""
from __future__ import annotations

from typing import Callable, TypeVar

from .. import config
from ..llm import LLMError

T = TypeVar("T")


class AgentError(Exception):
    """An agent could not produce a result. The message is safe to show to the user."""


def llm_or_fallback(with_llm: Callable[[], T], without_llm: Callable[[], T]) -> tuple[T, str]:
    """Run the LLM path; on failure use the deterministic template path and say why."""
    if config.llm_available():
        try:
            return with_llm(), ""
        except LLMError as exc:
            reason = str(exc)
    else:
        reason = "no LLM key configured"
    return without_llm(), f"template output used ({reason})"
