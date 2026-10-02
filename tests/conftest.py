import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forgeflow import config, llm  # noqa: E402

KEYS = ("GROQ_API_KEY", "TAVILY_API_KEY", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "APP_BASE_URL")


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """Every test runs with no credentials, a temporary database and no real network or mail."""
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("FORGEFLOW_DB", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "DEMOS_DIR", tmp_path / "demos")
    monkeypatch.setattr(config, "load_env", lambda *a, **k: None)

    def blocked(*args, **kwargs):
        raise AssertionError("unexpected network call in a test")

    monkeypatch.setattr("requests.post", blocked)
    monkeypatch.setattr("requests.get", blocked)
    monkeypatch.setattr("smtplib.SMTP", blocked)
    monkeypatch.setattr(llm, "time", SimpleNamespace(sleep=lambda s: None))
