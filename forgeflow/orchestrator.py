"""Deterministic workflow. Plain code decides the order; agents only fill in typed results."""
from __future__ import annotations

import json
import re
import uuid
from typing import Callable

from . import config, store
from .agents import AgentError, builder, hunter, requirements, sales
from .models import ActivityEvent, OfferProfile, OpportunityReport, Prospect, WorkflowState
from .tools import email as email_tool

HUNTER = "Opportunity Hunter"
BUILDER = "Builder"
SALES = "Growth & Sales"
DELIVERY = "Requirements & Delivery"
ORCHESTRATOR = "Orchestrator"

# Result fields in workflow order. Re-running a step clears everything after it.
_ORDER = ["report", "spec", "artifact", "outreach", "send_result", "reply_analysis", "requirements", "prd"]


def load_fixture() -> dict:
    """The bundled demo prospect: offer, prospect, research report and a sample reply."""
    raw = json.loads(config.DEMO_FIXTURE.read_text(encoding="utf-8"))
    return {
        "offer": OfferProfile.model_validate(raw["offer"]),
        "prospect": Prospect.model_validate(raw["prospect"]),
        "report": OpportunityReport.model_validate(raw["report"]),
        "sample_reply": str(raw.get("sample_reply", "")),
    }


def new_run(offer: OfferProfile, prospect: Prospect, mode: str = "live", hunt_note: str = "") -> WorkflowState:
    if prospect.website:
        prospect = prospect.model_copy(update={"website": config.clean_url(prospect.website)})
    slug = re.sub(r"[^a-z0-9]+", "-", prospect.name.lower()).strip("-")[:30] or "run"
    state = WorkflowState(id=f"{slug}-{uuid.uuid4().hex[:6]}", mode=mode, offer=offer, prospect=prospect)
    if hunt_note:
        _log(state, HUNTER, "ok", hunt_note)
    _log(state, ORCHESTRATOR, "ok", f"Mission created in {mode} mode.")
    store.save(state)
    return state


def _log(state: WorkflowState, agent: str, status: str, message: str) -> None:
    state.activity.append(ActivityEvent(agent=agent, status=status, message=message))


def _clear_from(state: WorkflowState, field: str) -> None:
    for name in _ORDER[_ORDER.index(field):]:
        setattr(state, name, None)
    if _ORDER.index(field) <= _ORDER.index("send_result"):
        state.approved = False


def _step(state: WorkflowState, agent: str, done: str, action: Callable[[], str]) -> bool:
    """Run one stage. The action mutates state only after its agent call succeeded."""
    try:
        note = action()
    except AgentError as exc:
        _log(state, agent, "error", str(exc))
        store.save(state)
        return False
    except Exception as exc:  # keep the app usable whatever an agent or tool does
        _log(state, agent, "error", f"Unexpected failure: {type(exc).__name__}")
        store.save(state)
        return False
    _log(state, agent, "fallback" if note else "ok", f"{done} {note}".strip())
    store.save(state)
    return True


def run_research(state: WorkflowState) -> bool:
    def action() -> str:
        if state.mode == "demo":
            report = load_fixture()["report"]
            note = "bundled sample research used (demo mode)"
        else:
            prospect, found = hunter.enrich(state.prospect)
            report = hunter.research(state.offer, prospect)
            state.prospect = prospect
            note = ""
            if found:
                _log(state, HUNTER, "ok", f"OpenStreetMap: {found}.")
        _clear_from(state, "report")
        state.report = report
        if report.contact_email and not state.prospect.email:
            state.prospect.email = report.contact_email
            _log(state, HUNTER, "ok", f"Public contact email found on {report.contact_email_source}.")
        if report.contact_phone and not state.prospect.phone:
            state.prospect.phone = report.contact_phone
            _log(state, HUNTER, "ok", f"Public phone number found on {report.contact_phone_source}.")
        return note

    return _step(state, HUNTER, "Opportunity report ready.", action)


def run_demo(state: WorkflowState) -> bool:
    def action() -> str:
        if state.report is None:
            raise AgentError("Research must finish before the demo can be built.")
        spec, artifact, note = builder.build(state.id, state.offer, state.prospect, state.report)
        _clear_from(state, "spec")
        state.spec, state.artifact = spec, artifact
        return note

    return _step(state, BUILDER, "Personalized demo built.", action)


def run_outreach(state: WorkflowState) -> bool:
    def action() -> str:
        if state.report is None or state.artifact is None:
            raise AgentError("The demo must be built before outreach is drafted.")
        draft, note = sales.draft_outreach(state.offer, state.prospect, state.report, state.artifact.url)
        _clear_from(state, "outreach")
        state.outreach = draft
        return note

    return _step(state, SALES, "Proposal and email drafted, waiting for approval.", action)


def approve_and_send(state: WorkflowState, approved: bool, recipient: str, subject: str, body: str) -> bool:
    """The only path to outbound email. Requires an explicit human approval flag."""

    def action() -> str:
        if state.outreach is None:
            raise AgentError("There is no email draft to send.")
        if not approved:
            raise AgentError("Email was not sent: human approval is required.")
        if state.send_result is not None and state.send_result.status == "sent":
            raise AgentError("This email was already sent. One email per mission.")
        result = email_tool.send(recipient, subject, body)
        if result.status == "failed":
            raise AgentError(result.detail)
        state.outreach.email_subject, state.outreach.email_body = subject, body
        state.approved = True
        state.send_result = result
        return "" if result.status == "sent" else "preview only, nothing was sent"

    return _step(state, SALES, "Email approved by human.", action)


def run_reply(state: WorkflowState, reply: str) -> bool:
    def action() -> str:
        if state.outreach is None:
            raise AgentError("Outreach must exist before a reply can be analysed.")
        if not reply.strip():
            raise AgentError("The customer reply is empty.")
        analysis, note = sales.analyze_reply(reply, state.outreach)
        _clear_from(state, "reply_analysis")
        state.reply_text, state.reply_analysis = reply.strip(), analysis
        return note

    return _step(state, SALES, "Customer reply analysed.", action)


def run_requirements(state: WorkflowState) -> bool:
    def action() -> str:
        if state.reply_analysis is None or state.report is None or state.spec is None or state.artifact is None:
            raise AgentError("A customer reply must be analysed before requirements are written.")
        req, note = requirements.extract(state.prospect, state.report, state.spec, state.reply_text, state.reply_analysis)
        prd = requirements.build_prd(state.prospect, state.report, state.artifact.url, state.reply_text, req)
        state.requirements, state.prd = req, prd
        return note

    return _step(state, DELIVERY, "Requirements and PRD generated.", action)


def demo_html(demo_id: str) -> str | None:
    """HTML for the public demo link, from the saved file or the run store."""
    if not re.fullmatch(r"[a-z0-9-]{1,40}", demo_id or ""):
        return None
    path = config.DEMOS_DIR / f"{demo_id}.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    state = store.load(demo_id)
    return state.artifact.html if state and state.artifact else None
