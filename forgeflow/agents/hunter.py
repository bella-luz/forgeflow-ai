"""Agent 1 - Opportunity Hunter: research a prospect and report evidence-backed opportunities."""
from __future__ import annotations

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from pydantic import BaseModel

from .. import config
from ..llm import LLMError, complete_json
from ..models import Candidate, EvidenceItem, HuntResult, EvidenceStatus, OfferProfile, OpportunityReport, Prospect, Source
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
- contact_email: a business email address only if it appears word for word in a result, with that result's URL in \
contact_email_source. Otherwise leave both empty.
- If the results are about a different business, say so in summary and mark items INSUFFICIENT."""


class _Draft(BaseModel):
    summary: str
    business_facts: list[EvidenceItem] = []
    need_signals: list[EvidenceItem] = []
    services: list[str] = []
    recommended_solution: str
    contact_email: str = ""
    contact_email_source: str = ""


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
    email, email_source = draft.contact_email.strip(), ""
    for r in results:
        if email and config.valid_email(email) and email.lower() in r.content.lower():
            email_source = r.url
            break
    return OpportunityReport(
        contact_email=email if email_source else "",
        contact_email_source=email_source,
        summary=draft.summary,
        business_facts=enforce_evidence(draft.business_facts, urls),
        need_signals=enforce_evidence(draft.need_signals, urls),
        services=draft.services,
        recommended_solution=draft.recommended_solution,
        sources=[Source(title=r.title, url=r.url) for r in results],
    )



# --- Hunt Mode ---------------------------------------------------------------------

DISCOVER_SYSTEM = """You pick out individual businesses from web search results, for a builder looking for \
potential clients.

Rules:
- List only specific businesses that are named in the search results. Never add a business from memory.
- Each business must be of the target business type, serving customers directly. Exclude wholesalers, \
distributors, suppliers and manufacturers unless that is the target type.
- Each business must be located in the target location according to the result. If the result does not show \
where it is, leave it out.
- Skip directories, marketplaces, review sites, news sites and large national or international chains.
- name: exactly as written in the result. source_url: the exact URL of the result that names it.
- why: one sentence, based only on the result, on why the builder's offer could help this business.
- Return at most 6 businesses."""

CHECK_SYSTEM = """You verify businesses found by a client search. For each business you get the search results \
about that business. Judge only from those results.

For each business return:
- name: as given.
- is_target_type: true only if the results show it is the target business type, serving customers directly \
(not a wholesaler, distributor or supplier unless that is the target).
- is_chain: true if it is a branch of a national or international chain or operator (for example a mobile network operator's store).
- in_target_location: true only if the results show its address or premises in the target location.
- location_quote: the exact words from a result that show its location (for example a street address). Empty if none.
- own_website: the business's own website URL if it appears in the results. Not a directory, social network, \
map or marketplace page. Empty if none appears.
- reason: one short sentence explaining the verdict."""

# Pages that list or describe businesses but are not a business's own website.
DIRECTORY_HOSTS = (
    "facebook.", "instagram.", "twitter.", "x.com", "tiktok.", "linkedin.", "youtube.", "google.", "apple.com",
    "yelp.", "tripadvisor.", "foursquare.", "kompass.", "europages.", "wheree.", "iberinform.", "einforma.",
    "infoempresa.", "axesor.", "empresite.", "paginasamarillas.", "cylex", "infobel.", "wikipedia.", "amazon.",
    "ebay.", "wallapop.", "milanuncios.", "waze.", "bing.", "yandex.", "booking.", "glovo", "justeat", "ubereats",
)


QUERY_SYSTEM = """Write web search queries that a local person would type to find individual businesses of \
the given type in the given place. Use the main local language of that place. Return 3 short queries; each must \
include the place name."""


class _Queries(BaseModel):
    queries: list[str] = []


def _brief_results(results: list[SearchResult], chars: int = 600) -> list[dict]:
    """Shortened results, to stay within the free-tier token budget."""
    return [{"title": r.title, "url": r.url, "content": r.content[:chars]} for r in results]


# Pages dedicated to one business that suggest it is currently trading: a map pin, its own social or review page.
PRESENCE_HOSTS = ("maps.apple.com", "google.com/maps", "maps.google.", "facebook.com", "instagram.com", "yelp.", "tripadvisor.", "tiktok.com")


def _presence(name: str, results: list[SearchResult]) -> str:
    """URL of a page dedicated to this business (own website, map listing or social profile), or empty.

    Aggregator directories alone are not enough: they often keep businesses that have closed.
    """
    flat_name = _flat(name)
    words = [w for w in flat_name.split() if len(w) >= 4]
    for r in results:
        host = (urlparse(r.url).hostname or "").lower()
        if any(h in r.url.lower() for h in PRESENCE_HOSTS) and flat_name in _flat(r.title):
            return r.url
        if not _is_directory(r.url) and words and any(w in host for w in words):
            return r.url
    return ""


class _Found(BaseModel):
    name: str
    source_url: str = ""
    why: str = ""


class _FoundList(BaseModel):
    candidates: list[_Found] = []


class _Check(BaseModel):
    name: str
    is_target_type: bool = False
    is_chain: bool = False
    in_target_location: bool = False
    location_quote: str = ""
    own_website: str = ""
    reason: str = ""


class _CheckList(BaseModel):
    checks: list[_Check] = []


def _flat(text: str) -> str:
    """Lowercase, no accents, single spaces: for robust substring checks."""
    text = unicodedata.normalize("NFKD", text or "")
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).lower().split())


def _place_tokens(offer: OfferProfile) -> list[str]:
    source = offer.city or offer.country
    return [w for w in (_flat(x) for x in re.split(r"[-/,()]", source)) if len(w) >= 4] or [_flat(source)]


def _is_directory(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(d in host for d in DIRECTORY_HOSTS)


def _search_all(queries: list[str], max_results: int) -> tuple[list[list[SearchResult]], list[str]]:
    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(lambda q: search_tool.search(q, max_results=max_results), queries))
    return [o.results for o in outcomes], [o.error for o in outcomes if not o.ok]


def discover(offer: OfferProfile) -> HuntResult:
    """Hunt Mode: find businesses matching the offer, then verify each one with its own search.

    A business is accepted only if it is named in a retrieved result, is the target type, is not a chain branch,
    its own search results place it in the target location, and it has a page of its own (website, map listing
    or social profile) rather than only directory entries. Rejected businesses are returned with the reason.
    Accepted businesses without their own website come first.
    """
    if not config.search_available() or not config.llm_available():
        raise AgentError("Finding clients needs both a search key (TAVILY_API_KEY) and an LLM key (GROQ_API_KEY).")

    place = ", ".join(p for p in (offer.city, offer.country) if p)
    tokens = _place_tokens(offer)

    # 1. Broad search, in English and in the local language.
    queries = [f"{offer.industry} in {place}"]
    try:
        local = complete_json(QUERY_SYSTEM, json.dumps({"business_type": offer.industry, "place": place}, ensure_ascii=False), _Queries, temperature=0.2, fast=True)
        queries += [q for q in local.queries if q.strip()][:3]
    except LLMError:
        queries.append(f"{offer.industry} {place} address phone")
    batches, errors = _search_all(queries, 6)
    results: dict[str, SearchResult] = {}
    for r in (r for batch in batches for r in batch):
        results.setdefault(_norm(r.url), r)
    if not results:
        raise AgentError("The search returned nothing. " + "; ".join(errors))

    brief = {"builder_offer": offer.capabilities, "target_business_type": offer.industry, "target_location": place}
    try:
        found = complete_json(
            DISCOVER_SYSTEM,
            json.dumps({**brief, "search_results": _brief_results(list(results.values()), 500)}, ensure_ascii=False),
            _FoundList,
            temperature=0.1,
        )
    except LLMError as exc:
        raise AgentError(f"Could not read the search results: {exc}")

    candidates: dict[str, tuple[_Found, SearchResult]] = {}
    for c in found.candidates:
        source = results.get(_norm(c.source_url))
        if source is None:
            continue
        text = _flat(f"{source.title} {source.content}")
        if _flat(c.name) not in text or not any(t in text for t in tokens):
            continue  # not named in the cited result, or the result does not mention the place
        candidates.setdefault(_flat(c.name), (c, source))
    if not candidates:
        raise AgentError(f"No {offer.industry} could be found in {place}. Try a nearby larger town or a broader business type.")

    # 2. Verify each candidate with a search of its own.
    picks = list(candidates.values())[:6]
    batches, _ = _search_all([f'"{c.name}" {offer.city or offer.country}' for c, _ in picks], 4)
    own = {_flat(c.name): batch for (c, _), batch in zip(picks, batches)}
    evidence = {_flat(c.name): [source, *own[_flat(c.name)]] for c, source in picks}
    payload = [{"name": c.name, "search_results": _brief_results(evidence[_flat(c.name)], 350)} for c, _ in picks]
    try:
        checks = complete_json(CHECK_SYSTEM, json.dumps({**brief, "businesses": payload}, ensure_ascii=False), _CheckList, temperature=0, fast=True)
    except LLMError as exc:
        raise AgentError(f"Could not verify the businesses found: {exc}")
    verdicts = {_flat(ch.name): ch for ch in checks.checks}

    kept: list[Candidate] = []
    rejected: list[Candidate] = []
    for c, source in picks:
        ch = verdicts.get(_flat(c.name))
        own_text = _flat(" ".join(f"{r.title} {r.content}" for r in own[_flat(c.name)]))
        all_text = _flat(" ".join(f"{r.title} {r.url} {r.content}" for r in evidence[_flat(c.name)]))
        # The verdict must agree with the business's own search results, which must mention the target place.
        located = bool(
            ch and ch.in_target_location
            and any(tok in _flat(ch.location_quote) for tok in tokens)
            and any(tok in own_text for tok in tokens)
        )
        if ch is None:
            reason = "Could not be verified."
        elif not ch.is_target_type:
            reason = f"Not a {offer.industry.lower()} business. {ch.reason}"
        elif ch.is_chain:
            reason = f"Branch of a large chain, so it already has a corporate website. {ch.reason}"
        elif not located:
            reason = f"Could not confirm it is located in {place}. {ch.reason}"
        elif not (presence := _presence(c.name, own[_flat(c.name)])):
            reason = (
                "Only listed in business directories, which are often out of date. "
                "No website, map listing or social page of its own was found."
            )
        else:
            reason = ""
        website = ""
        if ch:
            try:
                url = config.clean_url(ch.own_website)
                host = (urlparse(url).hostname or "").lower().removeprefix("www.")
                if not _is_directory(url) and host in all_text:
                    website = url
            except ValueError:
                pass
        candidate = Candidate(
            name=c.name, website=website, why=c.why, source_url=source.url,
            location_quote=ch.location_quote.strip() if ch else "", note=reason.strip(),
            presence_url="" if reason else presence,
        )
        (rejected if reason else kept).append(candidate)

    return HuntResult(candidates=sorted(kept, key=lambda c: bool(c.website)), rejected=rejected)
