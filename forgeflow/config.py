"""Settings come from environment variables, a local .env file, or Streamlit secrets."""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEMO_FIXTURE = DATA_DIR / "demo_prospect.json"
DEMOS_DIR = DATA_DIR / "demos"

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
HTTP_TIMEOUT = 30


def load_env(path: Path = ROOT / ".env") -> None:
    """Load .env and Streamlit secrets into os.environ without overriding existing values."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    try:
        import streamlit as st

        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:
        # No secrets file is the normal case for local runs.
        pass


def get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def llm_available() -> bool:
    return bool(get("GROQ_API_KEY"))


def search_available() -> bool:
    return bool(get("TAVILY_API_KEY"))


def email_available() -> bool:
    return all(get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"))


def base_url() -> str:
    return get("APP_BASE_URL", "http://localhost:8501").rstrip("/")


def clean_url(text: str) -> str:
    """Return a normalised http(s) URL, or raise ValueError."""
    text = (text or "").strip()
    if not text:
        raise ValueError("URL is empty")
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = parsed.hostname or ""
    if parsed.scheme not in ("http", "https") or "." not in host or re.search(r"[\s<>\"']", text):
        raise ValueError(f"Not a valid web address: {text[:80]}")
    return text


EMAIL_RE = re.compile(r"^[^@\s<>\"',;]+@[^@\s<>\"',;]+\.[A-Za-z]{2,}$")


def valid_email(text: str) -> bool:
    return bool(EMAIL_RE.match((text or "").strip()))
