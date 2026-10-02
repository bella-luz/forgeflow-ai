"""Web research provider. Tavily today; another provider only needs these two functions."""
from __future__ import annotations

import requests
from pydantic import BaseModel

from .. import config

TAVILY = "https://api.tavily.com"


class SearchResult(BaseModel):
    title: str = ""
    url: str
    content: str = ""


class SearchOutcome(BaseModel):
    ok: bool
    results: list[SearchResult] = []
    error: str = ""


def _call(path: str, payload: dict) -> tuple[dict | None, str]:
    key = config.get("TAVILY_API_KEY")
    if not key:
        return None, "TAVILY_API_KEY is not set"
    try:
        resp = requests.post(
            f"{TAVILY}/{path}",
            json=payload,
            headers={"Authorization": f"Bearer {key}"},
            timeout=config.HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        return None, f"network error: {type(exc).__name__}"
    if resp.status_code != 200:
        return None, f"search provider returned HTTP {resp.status_code}"
    try:
        return resp.json(), ""
    except ValueError:
        return None, "search provider returned invalid JSON"


def _http_only(url: str) -> bool:
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def search(query: str, max_results: int = 5) -> SearchOutcome:
    data, error = _call("search", {"query": query, "max_results": max_results, "search_depth": "basic"})
    if data is None:
        return SearchOutcome(ok=False, error=error)
    results = [
        SearchResult(title=r.get("title") or "", url=r["url"], content=(r.get("content") or "")[:1500])
        for r in data.get("results", [])
        if _http_only(r.get("url"))
    ]
    return SearchOutcome(ok=True, results=results)


def extract(url: str) -> SearchOutcome:
    """Fetch the readable text of one page."""
    data, error = _call("extract", {"urls": [url]})
    if data is None:
        return SearchOutcome(ok=False, error=error)
    results = [
        SearchResult(title="Prospect website", url=r["url"], content=(r.get("raw_content") or "")[:4000])
        for r in data.get("results", [])
        if _http_only(r.get("url"))
    ]
    if not results:
        return SearchOutcome(ok=False, error="page could not be read")
    return SearchOutcome(ok=True, results=results)
