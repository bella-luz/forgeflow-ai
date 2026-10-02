"""Models, config helpers and each tool's failure behaviour."""
import json
import smtplib

import pytest
import requests
from pydantic import BaseModel, ValidationError

from forgeflow import config, llm, store
from forgeflow.agents import builder, hunter, sales
from forgeflow.models import (
    DemoSpec,
    EvidenceItem,
    EvidenceStatus,
    OfferProfile,
    Prospect,
    ServiceItem,
    WorkflowState,
)
from forgeflow.tools import email as email_tool
from forgeflow.tools import search as search_tool


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data

    def json(self):
        if self._data is None:
            raise ValueError("no json")
        return self._data


def chat(content: str) -> FakeResponse:
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


# --- models and config ---
def test_models_reject_empty_required_fields():
    with pytest.raises(ValidationError):
        OfferProfile(capabilities="", industry="x", country="y")
    with pytest.raises(ValidationError):
        Prospect(name="")
    with pytest.raises(ValidationError):
        EvidenceItem(claim="x", status="CERTAIN")


def test_state_round_trips_through_store():
    state = WorkflowState(id="abc", offer=OfferProfile(capabilities="sites", industry="shops", country="ES"), prospect=Prospect(name="Shop"))
    store.save(state)
    assert store.load("abc") == state
    assert store.list_runs() == ["abc"]
    assert store.load("missing") is None


@pytest.mark.parametrize("bad", ["", "javascript:alert(1)", "ftp://x.com", "not a url", "http://localhost", 'https://x.com/"><script>'])
def test_clean_url_rejects_malformed(bad):
    with pytest.raises(ValueError):
        config.clean_url(bad)


def test_clean_url_adds_scheme():
    assert config.clean_url("example.com/shop") == "https://example.com/shop"


def test_valid_email():
    assert config.valid_email("owner@example.com")
    assert not config.valid_email("owner@example")
    assert not config.valid_email("a@b.com, c@d.com")


# --- llm ---
class _Out(BaseModel):
    answer: str


def test_llm_without_key_raises():
    with pytest.raises(llm.LLMError, match="not set"):
        llm.complete_json("s", "u", _Out)


def test_llm_repairs_invalid_json_once(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    replies = iter([chat('{"wrong": 1}'), chat('{"answer": "ok"}')])
    monkeypatch.setattr("requests.post", lambda *a, **k: next(replies))
    assert llm.complete_json("s", "u", _Out).answer == "ok"


def test_llm_http_failure_raises_without_leaking_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "secret-key")
    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse(401, {}))
    with pytest.raises(llm.LLMError) as exc:
        llm.complete_json("s", "u", _Out)
    assert "401" in str(exc.value) and "secret-key" not in str(exc.value)


def test_llm_network_error_raises(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")

    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr("requests.post", boom)
    with pytest.raises(llm.LLMError, match="network"):
        llm.complete_json("s", "u", _Out)


# --- search ---
def test_search_without_key_is_structured_failure():
    outcome = search_tool.search("anything")
    assert not outcome.ok and "TAVILY_API_KEY" in outcome.error


def test_search_timeout_is_structured_failure(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")

    def boom(*a, **k):
        raise requests.Timeout()

    monkeypatch.setattr("requests.post", boom)
    outcome = search_tool.search("anything")
    assert not outcome.ok and "Timeout" in outcome.error


def test_search_drops_non_http_urls(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    data = {"results": [{"title": "a", "url": "https://a.com", "content": "x"}, {"title": "b", "url": "javascript:x"}]}
    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse(200, data))
    assert [r.url for r in search_tool.search("q").results] == ["https://a.com"]


# --- email ---
def test_email_preview_without_credentials():
    result = email_tool.send("owner@example.com", "Hi", "Body")
    assert result.status == "preview"


def test_email_invalid_recipient_fails():
    assert email_tool.send("not-an-email", "Hi", "Body").status == "failed"


def test_email_smtp_failure_is_reported(monkeypatch):
    for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"):
        monkeypatch.setenv(key, "x@example.com")

    def boom(*a, **k):
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr("smtplib.SMTP", boom)
    result = email_tool.send("owner@example.com", "Hi", "Body")
    assert result.status == "failed" and "not sent" in result.detail


# --- hunter evidence rules ---
def test_verified_requires_a_retrieved_source():
    items = [
        EvidenceItem(claim="real", status="VERIFIED", source_url="https://a.com/page/"),
        EvidenceItem(claim="made up source", status="VERIFIED", source_url="https://invented.com"),
        EvidenceItem(claim="no source", status="VERIFIED"),
        EvidenceItem(claim="unknown", status="INSUFFICIENT"),
    ]
    checked = hunter.enforce_evidence(items, {"https://a.com/page"})
    assert [i.status for i in checked] == [EvidenceStatus.VERIFIED, EvidenceStatus.LIKELY, EvidenceStatus.LIKELY, EvidenceStatus.INSUFFICIENT]
    assert checked[1].source_url == ""


OFFER = OfferProfile(capabilities="websites", industry="shops", country="Spain", sender_name="Sam")
PROSPECT = Prospect(name="Shop", city="Valencia", country="Spain")


def test_live_research_without_keys_fails_clearly():
    with pytest.raises(hunter.AgentError, match="TAVILY_API_KEY"):
        hunter.research(OFFER, PROSPECT)


def test_live_research_with_failed_search_does_not_invent(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse(500))
    with pytest.raises(hunter.AgentError, match="no public information"):
        hunter.research(OFFER, PROSPECT)


def test_live_research_downgrades_unsupported_claims(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    draft = {
        "summary": "A shop.",
        "business_facts": [
            {"claim": "Sells phones", "status": "VERIFIED", "source_url": "https://dir.example/shop"},
            {"claim": "Founded 1990", "status": "VERIFIED", "source_url": "https://nowhere.example"},
        ],
        "need_signals": [],
        "services": ["Phones"],
        "recommended_solution": "A website.",
    }

    def fake_post(url, **kwargs):
        if "tavily" in url:
            return FakeResponse(200, {"results": [{"title": "Dir", "url": "https://dir.example/shop", "content": "phones"}]})
        return chat(json.dumps(draft))

    monkeypatch.setattr("requests.post", fake_post)
    report = hunter.research(OFFER, PROSPECT)
    assert [f.status.value for f in report.business_facts] == ["VERIFIED", "LIKELY"]
    assert [s.url for s in report.sources] == ["https://dir.example/shop"]


# --- builder and sales guards ---
def test_demo_html_escapes_untrusted_text():
    spec = DemoSpec(
        business_name="<script>alert(1)</script>", tagline="T", hero_text="H", about="A",
        services=[ServiceItem(name="<img src=x onerror=alert(1)>")],
    )
    html = builder.render(spec)
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html


def test_demo_contact_details_come_only_from_prospect(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    copy = {"tagline": "T", "hero_text": "H", "about": "A", "phone": "+34 600 000 000", "email": "fake@invented.com"}
    monkeypatch.setattr("requests.post", lambda *a, **k: chat(json.dumps(copy)))
    report = hunter.OpportunityReport(summary="s", recommended_solution="r")
    spec, note = builder.build_spec(OFFER, PROSPECT, report)
    assert note == "" and spec.phone == "" and spec.email == ""
    assert "invented" not in builder.render(spec)


def test_email_always_has_link_identity_and_opt_out():
    body = sales.finalize_email("Hello there.", "https://app/?demo=x", OFFER)
    assert "https://app/?demo=x" in body and "Sam" in body and "no thanks" in body


def test_reply_heuristics():
    a = sales._template_reply("We like it. Can you also add online booking? What does it cost?")
    assert a.intent == "interested" and len(a.questions) == 2
    assert any("booking" in f for f in a.requested_features)
    assert sales._template_reply("No thanks, not interested.").intent == "not_interested"


# --- hunt mode ---
def test_discover_without_keys_fails_clearly():
    with pytest.raises(hunter.AgentError, match="TAVILY_API_KEY"):
        hunter.discover(OFFER)


HUNT_OFFER = OfferProfile(capabilities="websites", industry="Mobile shops", country="Spain", city="Estella-Lizarra")


def test_discover_verifies_type_location_and_website(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    broad = [
        {"title": "Phone shops in Estella", "url": "https://dir.example/a",
         "content": "Movil Rapido, phone shop in Estella. Tienda Sol, Estella. Tienda Luna, Estella. Vodafone, Estella."},
        {"title": "Distribuidora Navarra", "url": "https://dir.example/b", "content": "Food distributor in Fontellas, Navarra."},
    ]
    per_business = {
        "Movil Rapido": [{"title": "Movil Rapido", "url": "https://movilrapido.example", "content": "Calle Mayor 3, Estella-Lizarra"}],
        "Tienda Sol": [{"title": "Tienda Sol", "url": "https://x.example", "content": "Tienda Sol, Avenida Costa Blanca, Alicante"}],
        "Tienda Luna": [{"title": "Luna", "url": "https://facebook.com/luna", "content": "Tienda Luna, Plaza Fueros 1, Estella"}],
        "Vodafone": [{"title": "Vodafone Estella", "url": "https://vodafone.example", "content": "Vodafone, Calle Mayor 9, Estella"}],
    }
    found = {"candidates": [
        {"name": "Movil Rapido", "source_url": "https://dir.example/a"},
        {"name": "Tienda Sol", "source_url": "https://dir.example/a"},
        {"name": "Tienda Luna", "source_url": "https://dir.example/a"},
        {"name": "Distribuidora Navarra", "source_url": "https://dir.example/b"},
        {"name": "Invented Phones", "source_url": "https://dir.example/a"},
        {"name": "Vodafone", "source_url": "https://dir.example/a"},
    ]}
    checks = {"checks": [
        {"name": "Movil Rapido", "is_target_type": True, "in_target_location": True,
         "location_quote": "Calle Mayor 3, Estella-Lizarra", "own_website": "https://movilrapido.example"},
        {"name": "Tienda Sol", "is_target_type": True, "in_target_location": True,
         "location_quote": "Calle Inventada, Estella", "own_website": ""},
        {"name": "Tienda Luna", "is_target_type": True, "in_target_location": True,
         "location_quote": "Plaza Fueros 1, Estella", "own_website": "https://facebook.com/luna"},
        {"name": "Vodafone", "is_target_type": True, "is_chain": True, "in_target_location": True,
         "location_quote": "Calle Mayor 9, Estella", "own_website": ""},
    ]}

    def fake_post(url, json=None, **kwargs):
        if "tavily" in url:
            q = json["query"]
            if q.startswith('"'):
                name = q.split('"')[1]
                return FakeResponse(200, {"results": per_business.get(name, [])})
            return FakeResponse(200, {"results": broad})
        system = json["messages"][0]["content"]
        return chat(__import__("json").dumps(found if system.startswith("You pick out") else checks))

    monkeypatch.setattr("requests.post", fake_post)
    hunt = hunter.discover(HUNT_OFFER)
    got = hunt.candidates
    # Distribuidora: place not in its result. Invented: not named in the result. Both dropped before checking.
    assert [c.name for c in got] == ["Tienda Luna", "Movil Rapido"]  # no own website listed first
    assert got[0].website == ""  # a Facebook page is not an own website
    assert got[1].website == "https://movilrapido.example"
    assert "Estella" in got[1].location_quote
    # Tienda Sol: its own results place it in Alicante. Vodafone: chain branch.
    notes = {c.name: c.note for c in hunt.rejected}
    assert set(notes) == {"Tienda Sol", "Vodafone"}
    assert "located" in notes["Tienda Sol"] and "chain" in notes["Vodafone"]


def test_research_keeps_only_public_emails_that_appear_in_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")

    def run_with(email):
        draft = {"summary": "s", "recommended_solution": "r", "contact_email": email}

        def fake_post(url, **kwargs):
            if "tavily" in url:
                return FakeResponse(200, {"results": [{"title": "Shop", "url": "https://shop.example", "content": "Write to info@shop.example"}]})
            return chat(json.dumps(draft))

        monkeypatch.setattr("requests.post", fake_post)
        return hunter.research(OFFER, PROSPECT)

    found = run_with("info@shop.example")
    assert found.contact_email == "info@shop.example" and found.contact_email_source == "https://shop.example"
    assert run_with("guess@shop.example").contact_email == ""


def test_discover_with_failed_search_reports_it(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setattr("requests.post", lambda *a, **k: FakeResponse(500))
    with pytest.raises(hunter.AgentError, match="returned nothing"):
        hunter.discover(OFFER)
