"""Typed objects passed between the orchestrator and the four worker agents."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    LIKELY = "LIKELY"
    INSUFFICIENT = "INSUFFICIENT"


class OfferProfile(BaseModel):
    capabilities: str = Field(min_length=3)
    industry: str = Field(min_length=2)
    country: str = Field(min_length=2)
    city: str = ""
    price_range: str = ""
    language: str = "English"
    sender_name: str = ""
    sender_business: str = ""


class Prospect(BaseModel):
    name: str = Field(min_length=2)
    website: str = ""
    city: str = ""
    country: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""


class Candidate(BaseModel):
    """A business found in Hunt Mode, before any in-depth research."""

    name: str = Field(min_length=2)
    website: str = ""
    why: str = ""
    source_url: str = ""
    location_quote: str = ""
    note: str = ""


class HuntResult(BaseModel):
    candidates: list[Candidate] = []
    rejected: list[Candidate] = []


class Source(BaseModel):
    title: str = ""
    url: str


class EvidenceItem(BaseModel):
    claim: str
    status: EvidenceStatus = EvidenceStatus.INSUFFICIENT
    source_url: str = ""
    excerpt: str = ""


class OpportunityReport(BaseModel):
    summary: str
    business_facts: list[EvidenceItem] = []
    need_signals: list[EvidenceItem] = []
    services: list[str] = []
    recommended_solution: str
    contact_email: str = ""
    contact_email_source: str = ""
    sources: list[Source] = []


class ServiceItem(BaseModel):
    name: str
    description: str = ""


class DemoSpec(BaseModel):
    """Structured description of the demo site. The HTML is rendered from this, never written by the LLM."""

    business_name: str
    tagline: str
    hero_text: str
    about: str
    services: list[ServiceItem] = []
    highlights: list[str] = []
    cta_text: str = "Get in touch"
    language: str = "English"
    address: str = ""
    phone: str = ""
    email: str = ""
    prepared_by: str = ""


class DemoArtifact(BaseModel):
    demo_id: str
    html: str
    url: str


class OutreachDraft(BaseModel):
    proposal: str
    email_subject: str
    email_body: str
    follow_up: str = ""
    social_post: str = ""


class SendResult(BaseModel):
    status: Literal["sent", "preview", "failed"]
    detail: str = ""
    recipient: str = ""


class CustomerReplyAnalysis(BaseModel):
    intent: Literal["interested", "needs_info", "not_interested", "unclear"] = "unclear"
    summary: str = ""
    questions: list[str] = []
    objections: list[str] = []
    requested_features: list[str] = []
    missing_information: list[str] = []
    suggested_response: str = ""


class Requirements(BaseModel):
    overview: str
    functional: list[str] = []
    pages: list[str] = []
    integrations: list[str] = []
    content_needed: list[str] = []
    assumptions: list[str] = []
    open_questions: list[str] = []
    acceptance_criteria: list[str] = []
    out_of_scope: list[str] = []


class ProjectPRD(BaseModel):
    title: str
    markdown: str


class ActivityEvent(BaseModel):
    time: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%H:%M:%S UTC"))
    agent: str
    status: Literal["ok", "fallback", "error"]
    message: str


class WorkflowState(BaseModel):
    id: str
    mode: Literal["live", "demo"] = "live"
    offer: OfferProfile
    prospect: Prospect
    report: Optional[OpportunityReport] = None
    spec: Optional[DemoSpec] = None
    artifact: Optional[DemoArtifact] = None
    outreach: Optional[OutreachDraft] = None
    approved: bool = False
    send_result: Optional[SendResult] = None
    reply_text: str = ""
    reply_analysis: Optional[CustomerReplyAnalysis] = None
    requirements: Optional[Requirements] = None
    prd: Optional[ProjectPRD] = None
    activity: list[ActivityEvent] = []

    def progress(self) -> list[tuple[str, bool]]:
        """Stage labels shown in the UI and whether each is complete."""
        return [
            ("Research", self.report is not None),
            ("Opportunity", self.report is not None),
            ("Demo", self.artifact is not None),
            ("Outreach", self.send_result is not None),
            ("Reply", self.reply_analysis is not None),
            ("Requirements", self.requirements is not None),
            ("PRD", self.prd is not None),
        ]
