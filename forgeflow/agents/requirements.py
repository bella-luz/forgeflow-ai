"""Agent 4 - Requirements & Delivery: turn the customer's reply into requirements and a PRD."""
from __future__ import annotations

import json
from datetime import date

from ..llm import complete_json
from ..models import (
    CustomerReplyAnalysis,
    DemoSpec,
    OpportunityReport,
    ProjectPRD,
    Prospect,
    Requirements,
)
from . import llm_or_fallback

SYSTEM = """You are a delivery lead turning a customer conversation into project requirements for a small \
business website.

Rules:
- functional: testable requirements. Include only what the demo already shows and what the customer explicitly asked for.
- Do not add features the customer did not mention (for example confirmations, tracking, payments). Raise those in open_questions instead.
- Anything the customer did not say must go in assumptions or open_questions, never in functional as if they asked.
- pages: the pages the site needs. integrations: third-party services implied by the requests.
- content_needed: text, photos and details the customer must supply.
- acceptance_criteria: concrete checks, one per major requirement.
- out_of_scope: sensible exclusions for a first version.
- Do not state prices, dates or effort estimates."""


def _template_requirements(prospect: Prospect, spec: DemoSpec, analysis: CustomerReplyAnalysis) -> Requirements:
    functional = [f"Service section for: {s.name}" for s in spec.services]
    functional += [f"Customer request: {f}" for f in analysis.requested_features]
    return Requirements(
        overview=f"Website for {prospect.name}, based on the concept demo and the customer's reply.",
        functional=functional or ["Single-page business website based on the approved demo"],
        pages=["Home", "Services", "About", "Contact"],
        content_needed=["Logo", "Photos", "Confirmed contact details", "Service descriptions"],
        assumptions=["The demo layout is accepted as the starting point."],
        open_questions=analysis.questions + analysis.missing_information,
        acceptance_criteria=[
            "Site displays correctly on mobile and desktop",
            "All contact details are confirmed by the customer",
            "Each customer-requested feature is demonstrated and accepted",
        ],
        out_of_scope=["Online payments", "Native mobile app"],
    )


def extract(prospect: Prospect, report: OpportunityReport, spec: DemoSpec, reply: str, analysis: CustomerReplyAnalysis) -> tuple[Requirements, str]:
    user = json.dumps(
        {
            "business": prospect.name,
            "proposed_solution": report.recommended_solution,
            "demo_sections": {"services": [s.name for s in spec.services], "has_contact": True, "has_about": True},
            "customer_reply": reply,
            "reply_analysis": analysis.model_dump(exclude={"suggested_response"}),
        },
        ensure_ascii=False,
    )
    return llm_or_fallback(
        lambda: complete_json(SYSTEM, user, Requirements, temperature=0.2),
        lambda: _template_requirements(prospect, spec, analysis),
    )


def _section(title: str, items: list[str], numbered: bool = False) -> str:
    if not items:
        return f"## {title}\n\nNone recorded.\n"
    lines = [f"{i}. {x}" if numbered else f"- {x}" for i, x in enumerate(items, 1)]
    return f"## {title}\n\n" + "\n".join(lines) + "\n"


def build_prd(prospect: Prospect, report: OpportunityReport, demo_url: str, reply: str, req: Requirements) -> ProjectPRD:
    """The PRD layout is fixed in code; only the structured content varies."""
    title = f"Project PRD: {prospect.name}"
    evidence = [
        f"{e.claim} ({e.status.value}{', ' + e.source_url if e.source_url else ''})"
        for e in report.business_facts + report.need_signals
    ]
    quoted_reply = "\n".join(f"> {line}" for line in reply.strip().splitlines()) or "> (none)"
    parts = [
        f"# {title}\n\nGenerated {date.today().isoformat()} by ForgeFlow AI. Concept demo: {demo_url}\n",
        f"## Overview\n\n{req.overview}\n",
        f"## Background\n\n{report.summary}\n\n**Proposed solution:** {report.recommended_solution}\n",
        _section("Evidence", evidence),
        f"## Customer reply\n\n{quoted_reply}\n",
        _section("Functional requirements", req.functional, numbered=True),
        _section("Pages", req.pages),
        _section("Integrations", req.integrations),
        _section("Content and assets needed from the customer", req.content_needed),
        _section("Assumptions", req.assumptions),
        _section("Open questions", req.open_questions),
        _section("Acceptance criteria", req.acceptance_criteria, numbered=True),
        _section("Out of scope", req.out_of_scope),
    ]
    return ProjectPRD(title=title, markdown="\n".join(parts))
