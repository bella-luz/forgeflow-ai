"""Agent 3 - Growth & Sales: proposal, outreach email, follow-up, social draft, reply analysis."""
from __future__ import annotations

import json
import re

from .. import i18n
from ..llm import complete_json
from ..models import (
    CustomerReplyAnalysis,
    EvidenceStatus,
    OfferProfile,
    OpportunityReport,
    OutreachDraft,
    Prospect,
)
from . import llm_or_fallback

OUTREACH_SYSTEM = """You write honest, low-pressure sales material for a freelancer who has built a free concept \
demo website for a local business.

Rules:
- Refer only to the supplied evidence. Do not invent facts, numbers, results, prices or guarantees.
- Present LIKELY items as observations ("it looks like"), not as facts.
- email_body: plain text, under 140 words, greeting, one specific observation, the demo link exactly as given, \
one clear call to action. No signature and no unsubscribe line; those are added automatically.
- email_subject: under 9 words, no clickbait.
- proposal: short markdown with headings Observation, Proposed solution, What is included, Next step.
- follow_up: a polite two-sentence follow-up email body for a week later.
- social_post: a short post the freelancer could publish about building this kind of demo, without naming the business.
- Write the email, follow-up and proposal in the requested language."""

REPLY_SYSTEM = """You analyse a customer's reply to a website proposal. Extract only what the reply actually says.

- intent: interested, needs_info, not_interested, or unclear.
- questions: questions the customer asked.
- objections: concerns or hesitations they expressed.
- requested_features: features or changes they asked for.
- missing_information: what the builder still needs to learn before scoping the work. These are gaps, not guesses.
- suggested_response: a short, polite draft answer that does not promise prices or dates.
Never attribute a requirement to the customer that is not in their reply."""



def finalize_email(body: str, demo_url: str, offer: OfferProfile) -> str:
    """Guarantee the demo link, sender identity and opt-out line, whatever the draft contained."""
    body = body.strip()
    if demo_url not in body:
        body += f"\n\nDemo: {demo_url}"
    signature = "\n".join(p for p in (offer.sender_name, offer.sender_business) if p)
    if signature:
        body += f"\n\n{signature}"
    return f"{body}\n\n{i18n.OPT_OUT.get(offer.language, i18n.OPT_OUT['English'])}"


def _template_outreach(offer: OfferProfile, prospect: Prospect, report: OpportunityReport, demo_url: str) -> OutreachDraft:
    signals = "\n".join(f"- {s.claim} ({s.status.value.lower()})" for s in report.need_signals) or "- No specific signals recorded."
    return OutreachDraft(
        proposal=(
            f"## Observation\n{signals}\n\n## Proposed solution\n{report.recommended_solution}\n\n"
            f"## What is included\nA working concept demo is ready to view: {demo_url}\n\n"
            "## Next step\nA short call to confirm requirements and scope."
        ),
        email_subject=f"A website concept for {prospect.name}",
        email_body=(
            f"Hello,\n\nI put together a short concept website for {prospect.name}. "
            f"You can view it here: {demo_url}\n\n"
            "If it looks useful, I would be glad to adapt it to what you actually need. Would a short call suit you?"
        ),
        follow_up=f"Hello, I wanted to check whether you had a chance to look at the concept site for {prospect.name}. Happy to answer any questions.",
        social_post=f"Built a concept website for a local {offer.industry} business this week. Showing beats telling.",
    )


def draft_outreach(offer: OfferProfile, prospect: Prospect, report: OpportunityReport, demo_url: str) -> tuple[OutreachDraft, str]:
    evidence = [
        e.model_dump(include={"claim", "status"})
        for e in report.business_facts + report.need_signals
        if e.status != EvidenceStatus.INSUFFICIENT
    ]
    user = json.dumps(
        {
            "language": offer.language,
            "freelancer_offer": offer.capabilities,
            "business_name": prospect.name,
            "evidence": evidence,
            "recommended_solution": report.recommended_solution,
            "demo_link": demo_url,
        },
        ensure_ascii=False,
    )
    draft, note = llm_or_fallback(
        lambda: complete_json(OUTREACH_SYSTEM, user, OutreachDraft, temperature=0.5),
        lambda: _template_outreach(offer, prospect, report, demo_url),
    )
    draft.email_body = finalize_email(draft.email_body, demo_url, offer)
    return draft, note


_NEGATIVE = ("not interested", "no thanks", "no, thanks", "unsubscribe", "stop contacting", "no gracias", "no me interesa")
_POSITIVE = ("like", "love", "great", "interested", "sounds good", "let's", "yes", "gusta", "interesa")
_REQUEST = re.compile(r"\b(add|need|want|include|can you|could you|would like|también|añadir|necesit)", re.I)


def _template_reply(reply: str) -> CustomerReplyAnalysis:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", reply.strip()) if s.strip()]
    low = reply.lower()
    questions = [s for s in sentences if s.endswith("?")]
    if any(k in low for k in _NEGATIVE):
        intent = "not_interested"
    elif any(k in low for k in _POSITIVE):
        intent = "interested"
    elif questions:
        intent = "needs_info"
    else:
        intent = "unclear"
    return CustomerReplyAnalysis(
        intent=intent,
        summary=reply.strip()[:300],
        questions=questions,
        requested_features=[s for s in sentences if _REQUEST.search(s)],
        missing_information=["Budget", "Timeline", "Who provides text and photos"],
        suggested_response="Thank you for your reply. I will come back to you with answers and a few short questions.",
    )


def analyze_reply(reply: str, outreach: OutreachDraft) -> tuple[CustomerReplyAnalysis, str]:
    user = json.dumps({"our_email": outreach.email_body, "customer_reply": reply}, ensure_ascii=False)
    return llm_or_fallback(
        lambda: complete_json(REPLY_SYSTEM, user, CustomerReplyAnalysis, temperature=0.1),
        lambda: _template_reply(reply),
    )
