"""Agent 2 - Builder: turn an opportunity report into a personalized website demo."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote, quote_plus

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from pydantic import BaseModel

from .. import config, i18n
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

SYSTEM = """You write the copy for a modern one-page website, a free concept demo for a small local business. \
It must feel made for this business, and it must be honest.

Rules:
- Facts about the business: use only items marked VERIFIED or LIKELY.
- Never invent testimonials, reviews, ratings, prices, awards, years in business, staff names, statistics, \
brands stocked or guarantees.
- No superlatives or quality claims anywhere: not "best", "top", "leading", "cheapest", "fastest", "expert", \
"wide range", "huge catalogue" or similar. Describe what is offered, not how good it is.
- In Spanish, Italian and Portuguese address customers informally (tú / tu / você); in French and German use vous / Sie.
- services: first every service in known_services (example=false), each with one helpful sentence. If there are \
fewer than 4, add typical services for this type of business with example=true, up to 6 in total.
- highlights: exactly 3. Each describes something the new website lets customers do (for example book online, \
find the shop on the map, message in one tap). Never claim anything about the business's quality.
- eyebrow: short label such as the business type and town. tagline: under 9 words, warm and specific to the \
business type and town. hero_text: one or two sentences. about: one paragraph, 2 to 4 sentences, only from facts.
- cta_text: 2 to 4 words. booking_title: 2 to 5 words for the appointment or order request section that fits this \
business type. booking_text: one sentence on why booking online helps customers.
- Write everything in the requested language."""

PALETTE = ["#2563eb", "#0f766e", "#7c3aed", "#c2410c", "#0e7490", "#be123c", "#4d7c0f"]

# Simple line icons (24x24, stroke). Static markup, chosen by keyword.
_ICON_PATHS = {
    "phone": '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
    "wrench": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
    "battery": '<rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 11v2M6 10v4M10 10v4"/>',
    "headphones": '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><rect x="3" y="15" width="4" height="6" rx="1"/><rect x="17" y="15" width="4" height="6" rx="1"/>',
    "sim": '<path d="M6 2h9l5 5v15H6z"/><rect x="9" y="11" width="8" height="7" rx="1"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "shield": '<path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/>',
    "cart": '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.5 12h11L21 7H6"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "pin": '<path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "chat": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "whatsapp": '<path d="M20.5 11.6a8.5 8.5 0 0 1-12.6 7.4L3.5 20.5l1.5-4.3a8.5 8.5 0 1 1 15.5-4.6z"/><path d="M9 8.5c0 3.5 2.6 6.5 6.5 7l1.2-1.6-2-1-1 .9c-1.2-.5-2.3-1.6-2.8-2.8l.9-1-1-2z"/>',
}

_SERVICE_KEYWORDS = [
    ("wrench", ("repair", "repar", "fix", "screen", "pantalla", "écran", "bildschirm", "schermo", "ecrã", "reparatur", "riparaz")),
    ("battery", ("battery", "bater", "batter", "akku", "pila")),
    ("headphones", ("accessor", "accesor", "zubehör", "accessori", "acessór", "headphone", "auricular", "case", "funda")),
    ("sim", ("sim", "plan", "tarif", "contract", "contrato", "operator", "operador", "line", "línea", "fibra", "fiber")),
    ("lock", ("unlock", "liberac", "desbloq", "entsperr", "sblocc", "débloc")),
    ("shield", ("insurance", "seguro", "protect", "garant", "warranty", "versicher")),
    ("cart", ("sale", "venta", "buy", "compra", "sell", "vende", "shop", "tienda", "new", "nuevo", "second", "segunda", "refurb", "reacond")),
    ("phone", ("phone", "móvil", "movil", "mobile", "smartphone", "tablet", "handy", "telef")),
    ("calendar", ("appointment", "cita", "booking", "reserva", "termin", "rendez")),
]


def _svg(name: str) -> Markup:
    path = _ICON_PATHS.get(name, _ICON_PATHS["check"])
    return Markup(f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>')


def service_icon(name: str) -> str:
    low = (name or "").lower()
    for icon, words in _SERVICE_KEYWORDS:
        if any(w in low for w in words):
            return icon
    return "star"


_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
    autoescape=select_autoescape(default=True, default_for_string=True),
)
_env.globals.update(icon=_svg, service_icon=service_icon)


class _Highlight(BaseModel):
    title: str
    text: str = ""


class _Copy(BaseModel):
    eyebrow: str = ""
    tagline: str
    hero_text: str
    about: str
    services: list[ServiceItem] = []
    highlights: list[_Highlight] = []
    cta_text: str = "Get in touch"
    booking_title: str = ""
    booking_text: str = ""


_TEMPLATE_COPY = {
    "English": ("Visit us in {place}", "Get in touch", "Request an appointment", "Choose a time that suits you and we will confirm it.",
                [("Book online", "Request a visit any time, day or night."), ("Find us easily", "Address and directions in one tap."), ("Message us", "Call or write straight from your phone.")]),
    "Spanish": ("Visítanos en {place}", "Contacta", "Pide tu cita", "Elige el momento que mejor te venga y te lo confirmamos.",
                [("Reserva online", "Pide cita a cualquier hora."), ("Encuéntranos fácilmente", "Dirección y ruta en un toque."), ("Escríbenos", "Llama o escribe desde tu móvil.")]),
}


def _template_copy(offer: OfferProfile, prospect: Prospect, report: OpportunityReport) -> _Copy:
    place = prospect.city or prospect.country or offer.country
    tagline, cta, booking, booking_text, highlights = _TEMPLATE_COPY.get(offer.language, _TEMPLATE_COPY["English"])
    return _Copy(
        eyebrow=", ".join(x for x in (offer.industry, place) if x),
        tagline=tagline.format(place=place) if place else prospect.name,
        hero_text=report.summary,
        about=report.summary,
        services=[ServiceItem(name=s) for s in report.services],
        highlights=[_Highlight(title=a, text=b) for a, b in highlights],
        cta_text=cta,
        booking_title=booking,
        booking_text=booking_text,
    )


def build_spec(offer: OfferProfile, prospect: Prospect, report: OpportunityReport) -> tuple[DemoSpec, str]:
    usable = [
        f.model_dump(include={"claim", "status"})
        for f in report.business_facts + report.need_signals
        if f.status != EvidenceStatus.INSUFFICIENT
    ]
    user = json.dumps(
        {
            "language": offer.language,
            "business_name": prospect.name,
            "business_type": offer.industry,
            "town": prospect.city or offer.city,
            "country": prospect.country or offer.country,
            "summary": report.summary,
            "facts": usable,
            "known_services": report.services,
        },
        ensure_ascii=False,
    )
    copy, note = llm_or_fallback(
        lambda: complete_json(SYSTEM, user, _Copy, temperature=0.5),
        lambda: _template_copy(offer, prospect, report),
    )
    # Services found in research can never be marked as examples.
    known = {s.lower() for s in report.services}
    services = [s.model_copy(update={"example": s.example and s.name.lower() not in known}) for s in copy.services][:6]
    language = offer.language if offer.language in i18n.LABELS else "English"
    # Name, contact details and location come from the prospect record only, never from generated text.
    spec = DemoSpec(
        business_name=prospect.name,
        eyebrow=copy.eyebrow,
        tagline=copy.tagline,
        hero_text=copy.hero_text,
        about=copy.about,
        services=services,
        highlights=[ServiceItem(name=h.title, description=h.text) for h in copy.highlights[:3]],
        cta_text=copy.cta_text,
        booking_title=copy.booking_title,
        booking_text=copy.booking_text,
        language=language,
        address=prospect.address,
        phone=prospect.phone,
        email=prospect.email,
        opening_hours=prospect.opening_hours,
        whatsapp=i18n.whatsapp_number(prospect.phone, prospect.country or offer.country),
        lat=prospect.lat,
        lon=prospect.lon,
        accent=PALETTE[int(hashlib.md5(prospect.name.encode("utf-8")).hexdigest(), 16) % len(PALETTE)],
        prepared_by=offer.sender_business or offer.sender_name,
    )
    return spec, note


def _map_links(spec: DemoSpec) -> tuple[str, str]:
    """Embedded map and directions link: OpenStreetMap when coordinates are known, else a Google Maps address search."""
    if spec.lat is not None and spec.lon is not None:
        d = 0.004
        embed = (
            "https://www.openstreetmap.org/export/embed.html?layer=mapnik"
            f"&bbox={spec.lon - d * 1.5},{spec.lat - d},{spec.lon + d * 1.5},{spec.lat + d}&marker={spec.lat},{spec.lon}"
        )
        return embed, f"https://www.google.com/maps/dir/?api=1&destination={spec.lat},{spec.lon}"
    if spec.address:
        query = f"{spec.business_name}, {spec.address}"
        return f"https://maps.google.com/maps?q={quote(query)}&output=embed", f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
    return "", ""


def render(spec: DemoSpec) -> str:
    words = [w for w in re.findall(r"\w+", spec.business_name) if w]
    initials = "".join(w[0] for w in words[:2]).upper() or "•"
    map_src, directions = _map_links(spec)
    tel = re.sub(r"[^\d+]", "", spec.phone)
    return _env.get_template("site.html.j2").render(
        spec=spec, t=i18n.LABELS.get(spec.language, i18n.LABELS["English"]),
        initials=initials, map_src=map_src, directions=directions, tel=tel,
    )


def build(demo_id: str, offer: OfferProfile, prospect: Prospect, report: OpportunityReport) -> tuple[DemoSpec, DemoArtifact, str]:
    spec, note = build_spec(offer, prospect, report)
    html = render(spec)
    config.DEMOS_DIR.mkdir(parents=True, exist_ok=True)
    (config.DEMOS_DIR / f"{demo_id}.html").write_text(html, encoding="utf-8")
    artifact = DemoArtifact(demo_id=demo_id, html=html, url=f"{config.base_url()}/?demo={demo_id}")
    return spec, artifact, note
