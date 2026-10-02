"""Agent 2 - Builder: turn an opportunity report into a personalized website demo."""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from .. import config
from ..llm import complete_json
from ..models import (
    DemoArtifact,
    DemoSpec,
    EvidenceStatus,
    OfferProfile,
    OpportunityReport,
    Prospect,
    ServiceItem,
)
from . import llm_or_fallback

SYSTEM = """You write website copy for a small business demo site. You are given facts about the business, \
each with an evidence status.

Rules:
- Use only facts marked VERIFIED or LIKELY. Ignore INSUFFICIENT items.
- Never invent testimonials, reviews, ratings, prices, awards, years in business, staff names, statistics or guarantees.
- services: use only the listed services, each with a one-sentence neutral description.
- highlights: up to three short general statements that do not assert unverified facts.
- tagline: under 10 words. hero_text: one or two sentences. about: one short paragraph.
- Write in the requested language."""

LABELS = {
    "English": {
        "lang": "en", "services": "Services", "about": "About", "contact": "Contact",
        "address": "Address", "phone": "Phone", "email": "Email",
        "notice": "Concept demo. This is not the official website of this business.",
        "prepared_by": "Prepared by",
        "contact_pending": "Contact details will be added once confirmed with the business.",
        "footer": "Concept demo",
    },
    "Spanish": {
        "lang": "es", "services": "Servicios", "about": "Sobre nosotros", "contact": "Contacto",
        "address": "Dirección", "phone": "Teléfono", "email": "Correo electrónico",
        "notice": "Demostración conceptual. Este no es el sitio web oficial de este negocio.",
        "prepared_by": "Preparado por",
        "contact_pending": "Los datos de contacto se añadirán cuando se confirmen con el negocio.",
        "footer": "Demostración conceptual",
    },
}

_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
    autoescape=select_autoescape(default=True, default_for_string=True),
)


class _Copy(BaseModel):
    tagline: str
    hero_text: str
    about: str
    services: list[ServiceItem] = []
    highlights: list[str] = []
    cta_text: str = "Get in touch"


def _template_copy(offer: OfferProfile, prospect: Prospect, report: OpportunityReport) -> _Copy:
    place = prospect.city or prospect.country or offer.country
    return _Copy(
        tagline=f"{prospect.name} in {place}" if place else prospect.name,
        hero_text=report.summary,
        about=report.summary,
        services=[ServiceItem(name=s) for s in report.services],
        cta_text="Contactar" if offer.language == "Spanish" else "Get in touch",
    )


def build_spec(offer: OfferProfile, prospect: Prospect, report: OpportunityReport) -> tuple[DemoSpec, str]:
    usable = [
        f.model_dump(include={"claim", "status"})
        for f in report.business_facts
        if f.status != EvidenceStatus.INSUFFICIENT
    ]
    user = json.dumps(
        {
            "language": offer.language,
            "business_name": prospect.name,
            "industry": offer.industry,
            "location": f"{prospect.city} {prospect.country}".strip(),
            "summary": report.summary,
            "facts": usable,
            "services": report.services,
        },
        ensure_ascii=False,
    )
    copy, note = llm_or_fallback(
        lambda: complete_json(SYSTEM, user, _Copy, temperature=0.5),
        lambda: _template_copy(offer, prospect, report),
    )
    # Name and contact details come from the prospect record only, never from generated text.
    spec = DemoSpec(
        business_name=prospect.name,
        language=offer.language if offer.language in LABELS else "English",
        address=prospect.address,
        phone=prospect.phone,
        email=prospect.email,
        prepared_by=offer.sender_business or offer.sender_name,
        **copy.model_dump(),
    )
    return spec, note


def render(spec: DemoSpec) -> str:
    return _env.get_template("site.html.j2").render(spec=spec, t=LABELS.get(spec.language, LABELS["English"]))


def build(demo_id: str, offer: OfferProfile, prospect: Prospect, report: OpportunityReport) -> tuple[DemoSpec, DemoArtifact, str]:
    spec, note = build_spec(offer, prospect, report)
    html = render(spec)
    config.DEMOS_DIR.mkdir(parents=True, exist_ok=True)
    (config.DEMOS_DIR / f"{demo_id}.html").write_text(html, encoding="utf-8")
    artifact = DemoArtifact(demo_id=demo_id, html=html, url=f"{config.base_url()}/?demo={demo_id}")
    return spec, artifact, note
