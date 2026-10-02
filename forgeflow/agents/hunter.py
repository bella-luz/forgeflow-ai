"""Agent 1 - Opportunity Hunter: research a prospect and report evidence-backed opportunities."""
from __future__ import annotations

import json

from pydantic import BaseModel

from .. import config
from ..llm import LLMError, complete_json
from ..models import EvidenceItem, EvidenceStatus, OfferProfile, OpportunityReport, Prospect, Source
from ..tools import search as search_tool
from ..tools.search import SearchResult
from . import AgentError

SYSTEM = """You are a careful business researcher. You are given search results about one business and \
a description of what a builder can offer. Report only what the search results support.

Rules:
- Never invent facts, contact details, reviews, prices or problems.
- Each item needs a status:
  VERIFIED = stated directly in a search result; set source_url to that result's exact URL and excerpt to the supporting words.
  LIKELY = a reasonable inference from the results; explain the basis in excerpt.
  INSUFFICIENT = you looked for it and the results do not say.
- business_facts: what the business is, where, what it sells or does, its online presence.
- need_signals: evidence that the builder's offer could help (for example no website, outdated site, no online booking).
- services: only services or products the results actually mention.
- recommended_solution: one short paragraph proposing what the builder should offer, tied to the need_signals.
- If the results are about a different business, say so in summary and mark items INSUFFICIENT."""


class _Draft(BaseModel):
    summary: str
    business_facts: list[EvidenceItem] = []
    need_signals: list[EvidenceItem] = []
    services: list[str] = []
    recommended_solution: str


def _norm(url: str) -> str:
    return url.strip().rstrip("/").lower()


def enforce_evidence(items: list[EvidenceItem], allowed_urls: set[str]) -> list[EvidenceItem]:
    """VERIFIED is only kept when the cited URL is one we actually retrieved."""
    allowed = {_norm(u) for u in allowed_urls}
    checked = []
    for item in items:
        cited = _norm(item.source_url) in allowed if item.source_url else False
        if not cited:
            item = item.model_copy(update={"source_url": ""})
            if item.status == EvidenceStatus.VERIFIED:
                item = item.model_copy(update={"status": EvidenceStatus.LIKELY})
        checked.append(item)
    return checked


def gather(prospect: Prospect) -> tuple[list[SearchResult], list[str]]:
    """Collect public information. Returns results and any tool errors."""
    results: list[SearchResult] = []
    errors: list[str] = []

    if prospect.website:
        try:
            page = search_tool.extract(config.clean_url(prospect.website))
            results += page.results
            if not page.ok:
                errors.append(f"website: {page.error}")
        except ValueError as exc:
            errors.append(f"website: {exc}")

    place = " ".join(p for p in (prospect.city, prospect.country) if p)
    for query in (f'"{prospect.name}" {place}', f"{prospect.name} {place} reviews contact opening hours"):
        outcome = search_tool.search(query.strip())
        results += outcome.results
        if not outcome.ok:
            errors.append(f"search: {outcome.error}")

    unique: dict[str, SearchResult] = {}
    for r in results:
        unique.setdefault(_norm(r.url), r)
    return list(unique.values()), errors


def research(offer: OfferProfile, prospect: Prospect) -> OpportunityReport:
    """Live research. Raises AgentError rather than returning a made-up report."""
    if not config.search_available():
        raise AgentError("Live research needs a search API key (TAVILY_API_KEY). Use demo mode or add the key.")
    if not config.llm_available():
        raise AgentError("Live research needs an LLM key (GROQ_API_KEY). Use demo mode or add the key.")

    results, errors = gather(prospect)
    if not results:
        raise AgentError("Research found no public information. " + "; ".join(errors))

    user = json.dumps(
        {
            "builder_offer": offer.capabilities,
            "target_industry": offer.industry,
            "prospect": prospect.model_dump(include={"name", "website", "city", "country", "notes"}),
            "search_results": [r.model_dump() for r in results],
        },
        ensure_ascii=False,
    )
    try:
        draft = complete_json(SYSTEM, user, _Draft, temperature=0.1)
    except LLMError as exc:
        raise AgentError(f"Research analysis failed: {exc}")

    urls = {r.url for r in results}
    return OpportunityReport(
        summary=draft.summary,
        business_facts=enforce_evidence(draft.business_facts, urls),
        need_signals=enforce_evidence(draft.need_signals, urls),
        services=draft.services,
        recommended_solution=draft.recommended_solution,
        sources=[Source(title=r.title, url=r.url) for r in results],
    )
