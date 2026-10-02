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
from forgeflow.tools import places
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
def test_discover_reports_unknown_place(monkeypatch):
    monkeypatch.setattr(places, "geocode", lambda text: None)
    with pytest.raises(hunter.AgentError, match="Could not find"):
        hunter.discover(OFFER)


def test_web_discovery_without_keys_fails_clearly():
    with pytest.raises(hunter.AgentError, match="TAVILY_API_KEY"):
        hunter._discover_web(OFFER)


HUNT_OFFER = OfferProfile(capabilities="websites", industry="Mobile shops", country="Spain", city="Estella-Lizarra")


def test_discover_verifies_type_location_and_website(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    broad = [
        {"title": "Phone shops in Estella", "url": "https://dir.example/a",
         "content": "Movil Rapido, phone shop in Estella. Tienda Sol, Estella. Tienda Luna, Estella. Vodafone, Estella. Center Max, Estella."},
        {"title": "Distribuidora Navarra", "url": "https://dir.example/b", "content": "Food distributor in Fontellas, Navarra."},
    ]
    per_business = {
        "Movil Rapido": [{"title": "Movil Rapido", "url": "https://movilrapido.example", "content": "Calle Mayor 3, Estella-Lizarra"}],
        "Tienda Sol": [{"title": "Tienda Sol", "url": "https://x.example", "content": "Tienda Sol, Avenida Costa Blanca, Alicante"}],
        "Tienda Luna": [{"title": "Tienda Luna | Facebook", "url": "https://facebook.com/luna", "content": "Tienda Luna, Plaza Fueros 1, Estella"}],
        "Center Max": [{"title": "Center Max - Estella", "url": "https://dir.example/centermax", "content": "Center Max, Calle Mayor 1, Estella"}],
        "Vodafone": [{"title": "Vodafone Estella", "url": "https://vodafone.example", "content": "Vodafone, Calle Mayor 9, Estella"}],
    }
    found = {"candidates": [
        {"name": "Movil Rapido", "source_url": "https://dir.example/a"},
        {"name": "Tienda Sol", "source_url": "https://dir.example/a"},
        {"name": "Tienda Luna", "source_url": "https://dir.example/a"},
        {"name": "Distribuidora Navarra", "source_url": "https://dir.example/b"},
        {"name": "Invented Phones", "source_url": "https://dir.example/a"},
        {"name": "Vodafone", "source_url": "https://dir.example/a"},
        {"name": "Center Max", "source_url": "https://dir.example/a"},
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
        {"name": "Center Max", "is_target_type": True, "in_target_location": True,
         "location_quote": "Calle Mayor 1, Estella", "own_website": ""},
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
    hunt = hunter._discover_web(HUNT_OFFER)
    got = hunt.candidates
    # Distribuidora: place not in its result. Invented: not named in the result. Both dropped before checking.
    assert [c.name for c in got] == ["Tienda Luna", "Movil Rapido"]  # no own website listed first
    assert got[0].website == ""  # a Facebook page is not an own website
    assert got[1].website == "https://movilrapido.example"
    assert "Estella" in got[1].location_quote
    assert got[0].presence_url == "https://facebook.com/luna"
    # Tienda Sol: its own results place it in Alicante. Vodafone: chain branch. Center Max: directory listing only.
    notes = {c.name: c.note for c in hunt.rejected}
    assert set(notes) == {"Tienda Sol", "Vodafone", "Center Max"}
    assert "located" in notes["Tienda Sol"] and "chain" in notes["Vodafone"] and "directories" in notes["Center Max"]


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
        hunter._discover_web(OFFER)


# --- map-based discovery and enrichment ---
AREA = places.Area(name="Pamplona", south=42.7, north=42.9, west=-1.8, east=-1.5)


def test_nominatim_item_is_parsed():
    item = {
        "name": "Max Móvil", "category": "shop", "type": "mobile_phone", "lat": "42.81", "lon": "-1.64",
        "osm_type": "node", "osm_id": 5,
        "address": {"road": "Calle Paulino Caballero", "house_number": "26", "postcode": "31002", "city": "Pamplona"},
        "extratags": {"website": "maxmovil.es", "email": "not-an-email", "phone": "+34 948 000 000;+34 600 000 000"},
    }
    p = places.to_place(item)
    assert p.address == "Calle Paulino Caballero 26, 31002 Pamplona"
    assert p.website == "https://maxmovil.es" and p.email == "" and p.phone == "+34 948 000 000"
    assert p.osm_url == "https://www.openstreetmap.org/node/5" and p.lat == 42.81
    assert places.to_place({"name": ""}) is None


def test_map_discovery_sets_chains_aside_and_checks_websites(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")  # no LLM key: no AI phrases and no web fallback
    shops = [
        places.Place(name="Hajra Moviles", category="shop=mobile_phone", address="Av. Carlos III 45", osm_url="https://www.openstreetmap.org/node/1"),
        places.Place(name="Phone House", category="shop=mobile_phone", osm_url="https://www.openstreetmap.org/node/2"),
        places.Place(name="Max Movil", category="shop=mobile_phone", osm_url="https://www.openstreetmap.org/node/3"),
        places.Place(name="Celular Uno", category="shop=mobile_phone", brand="Q123", osm_url="https://www.openstreetmap.org/node/4"),
        places.Place(name="Tienda Web", category="shop=mobile_phone", website="https://tiendaweb.es", osm_url="https://www.openstreetmap.org/node/5"),
    ]
    monkeypatch.setattr(places, "geocode", lambda text: AREA)
    monkeypatch.setattr(places, "search_in_area", lambda phrase, area: shops)

    def fake_post(url, json=None, **kwargs):
        if '"Max Movil"' in json["query"]:
            return FakeResponse(200, {"results": [{"title": "Max Movil", "url": "https://www.maxmovil.es/contacto", "content": ""}]})
        return FakeResponse(200, {"results": [{"title": "Hajra", "url": "https://www.facebook.com/hajra", "content": ""}]})

    monkeypatch.setattr("requests.post", fake_post)
    hunt = hunter.discover(OfferProfile(capabilities="websites", industry="Mobile shops", country="Spain", city="Pamplona"))
    assert [c.name for c in hunt.candidates] == ["Hajra Moviles", "Max Movil", "Tienda Web"]
    assert hunt.candidates[0].website == "" and hunt.candidates[0].address == "Av. Carlos III 45"
    assert hunt.candidates[1].website == "https://www.maxmovil.es"
    assert {c.name for c in hunt.rejected} == {"Phone House", "Celular Uno"}
    assert all(c.found_on == "OpenStreetMap" for c in hunt.candidates)


def test_enrich_fills_gaps_but_keeps_user_values(monkeypatch):
    listing = places.Place(name="5G Mobiles", phone="+34 948 111 111", website="https://5gmobiles.es", opening_hours="Mo-Sa 10:00-20:00",
                           address="Calle Mayor 1, Estella", lat=42.67, lon=-2.03, osm_url="https://www.openstreetmap.org/node/9")
    monkeypatch.setattr(places, "lookup", lambda text: listing)
    prospect = Prospect(name="5G Mobiles", city="Estella-Lizarra", country="Spain", phone="+34 600 000 000", address="Calle Mayor 1")
    enriched, note = hunter.enrich(prospect)
    assert enriched.phone == "+34 600 000 000" and enriched.address == "Calle Mayor 1"
    assert enriched.website == "https://5gmobiles.es" and enriched.lat == 42.67 and enriched.map_url.endswith("/node/9")
    assert "map listing" in note


def test_enrich_ignores_a_different_business(monkeypatch):
    monkeypatch.setattr(places, "lookup", lambda text: places.Place(name="Vodafone", website="https://vodafone.es", lat=1.0, lon=1.0))
    monkeypatch.setattr(places, "locate", lambda text: (42.67, -2.03))
    enriched, note = hunter.enrich(Prospect(name="5G Mobiles", country="Spain", address="Calle Mayor 1, Estella"))
    assert enriched.website == "" and enriched.map_url == "" and enriched.lat == 42.67


def test_research_uses_known_details_when_search_finds_nothing_relevant(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    draft = {"summary": "No search result is about this shop.", "recommended_solution": "A website.",
             "need_signals": [{"claim": "No website of its own was found", "status": "LIKELY"}]}

    def fake_post(url, **kwargs):
        if "tavily" in url:
            return FakeResponse(200, {"results": [{"title": "Movistar", "url": "https://movistar.example", "content": "other shop"}]})
        return chat(json.dumps(draft))

    monkeypatch.setattr("requests.post", fake_post)
    report = hunter.research(OFFER, Prospect(name="5G Mobiles", city="Estella", country="Spain", address="Calle Mayor 1", phone="+34 600"))
    claims = [f.claim for f in report.business_facts]
    assert claims == ["Address: Calle Mayor 1", "Phone: +34 600"]
    assert all(f.status == EvidenceStatus.VERIFIED and f.excerpt == "Entered by you" for f in report.business_facts)


# --- languages and demo site ---
from forgeflow import i18n  # noqa: E402


@pytest.mark.parametrize("country,language", [("Spain", "Spanish"), ("españa", "Spanish"), ("France", "French"), ("Pakistan", "English"), ("", "English")])
def test_language_follows_country(country, language):
    assert i18n.resolve(i18n.AUTO, country) == language
    assert i18n.resolve("German", country) == "German"


def test_whatsapp_number():
    assert i18n.whatsapp_number("948 55 12 34", "Spain") == "34948551234"
    assert i18n.whatsapp_number("+34 600 11 22 33", "") == "34600112233"
    assert i18n.whatsapp_number("12345", "Spain") == ""
    assert i18n.whatsapp_number("948 55 12 34", "Atlantis") == ""


def test_demo_site_has_map_booking_whatsapp_and_marks_examples():
    spec = DemoSpec(
        business_name="5G Mobiles", tagline="T", hero_text="H", about="A", language="Spanish",
        services=[ServiceItem(name="Reparación de pantallas"), ServiceItem(name="Fundas", example=True)],
        booking_title="Pida su cita", address="Calle Mayor 1, Estella", phone="948 55 12 34", whatsapp="34948551234",
        lat=42.67, lon=-2.03,
    )
    html = builder.render(spec)
    assert "openstreetmap.org/export/embed.html" in html and "marker=42.67,-2.03" in html
    assert 'href="https://wa.me/34948551234"' in html and 'href="tel:948551234"' in html
    assert 'id="booking"' in html and "Servicios de ejemplo" in html and 'lang="es"' in html


def test_demo_site_without_coordinates_uses_address_search():
    html = builder.render(DemoSpec(business_name="Shop", tagline="T", hero_text="H", about="A", address="Calle Mayor 1, Estella"))
    assert "maps.google.com/maps?q=Shop%2C%20Calle%20Mayor%201%2C%20Estella&amp;output=embed" in html
    assert "wa.me" not in html and "Example services" not in html


def test_research_keeps_a_phone_only_if_it_appears_in_the_cited_result(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("GROQ_API_KEY", "k")

    def run_with(phone):
        draft = {"summary": "s", "recommended_solution": "r", "contact_phone": phone, "contact_phone_source": "https://shop.example"}

        def fake_post(url, **kwargs):
            if "tavily" in url:
                return FakeResponse(200, {"results": [{"title": "Shop", "url": "https://shop.example", "content": "Llámanos: 948 54 39 54"}]})
            return chat(json.dumps(draft))

        monkeypatch.setattr("requests.post", fake_post)
        return hunter.research(OFFER, PROSPECT)

    assert run_with("+34 948 54 39 54").contact_phone == "+34 948 54 39 54"
    assert run_with("+34 600 00 00 00").contact_phone == ""
