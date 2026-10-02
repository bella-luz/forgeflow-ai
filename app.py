"""ForgeFlow AI dashboard. Run with: streamlit run app.py"""
from __future__ import annotations

import re

import streamlit as st
import streamlit.components.v1 as components
from pydantic import ValidationError

from forgeflow import config, orchestrator, store
from forgeflow.agents import AgentError, hunter
from forgeflow.models import EvidenceItem, OfferProfile, Prospect, WorkflowState

config.load_env()
st.set_page_config(page_title="ForgeFlow AI", layout="wide")

STATUS_STYLE = {"VERIFIED": ("green", "Verified"), "LIKELY": ("orange", "Likely"), "INSUFFICIENT": ("gray", "Needs review")}
ACTIVITY_STYLE = {"ok": ("green", "Done"), "fallback": ("orange", "Fallback"), "error": ("red", "Failed")}


def plain(text: str) -> str:
    """Escape markdown so researched or generated text is shown literally."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>~$:])", r"\\\1", text or "")


def safe_md(text: str) -> str:
    """Allow markdown formatting but not embedded images or raw HTML."""
    return (text or "").replace("![", "[").replace("<", "&lt;")


# --- Public demo page: /?demo=<id> -------------------------------------------------
demo_id = st.query_params.get("demo")
if demo_id:
    st.markdown(
        "<style>header, footer, [data-testid='stSidebar'], [data-testid='stToolbar'] {display:none;}"
        ".block-container {padding:0; max-width:100%;}</style>",
        unsafe_allow_html=True,
    )
    html = orchestrator.demo_html(demo_id)
    if html:
        components.html(html, height=2200, scrolling=True)
    else:
        st.error("This demo link is not available.")
    st.stop()


# --- Helpers -----------------------------------------------------------------------
def current() -> WorkflowState | None:
    return st.session_state.get("state")


def run(step, *args) -> None:
    state = current()
    with st.spinner("Working..."):
        ok = step(state, *args)
    if ok:
        st.rerun()
    st.error(state.activity[-1].message)


def evidence_cards(items: list[EvidenceItem]) -> None:
    if not items:
        st.caption("Nothing recorded.")
    for item in items:
        color, label = STATUS_STYLE[item.status.value]
        with st.container(border=True):
            st.markdown(f":{color}[**{label}**]")
            st.markdown(plain(item.claim))
            if item.excerpt:
                st.caption(plain(item.excerpt))
            if item.source_url:
                st.markdown(f"Source: {item.source_url}")


def bullet_list(title: str, items: list[str]) -> None:
    st.markdown(f"**{title}**")
    if items:
        st.markdown("\n".join(f"- {plain(i)}" for i in items))
    else:
        st.caption("None recorded.")


# --- Sidebar -----------------------------------------------------------------------
with st.sidebar:
    st.title("ForgeFlow AI")
    st.caption("You build. ForgeFlow finds the client, builds the demo and prepares the project.")

    st.subheader("Services")
    for name, ready, on, off in (
        ("LLM", config.llm_available(), "connected", "template mode"),
        ("Web research", config.search_available(), "connected", "demo data only"),
        ("Email", config.email_available(), "live sending", "preview only"),
    ):
        st.markdown(f"{name}: :{'green' if ready else 'orange'}[{on if ready else off}]")

    st.subheader("Missions")
    if st.button("New mission", use_container_width=True):
        st.session_state.pop("state", None)
        st.session_state.pop("candidates", None)
        st.rerun()
    runs = store.list_runs()
    if runs:
        active = current().id if current() else None
        picked = st.selectbox("Open a saved mission", runs, index=runs.index(active) if active in runs else None, placeholder="Select...")
        if picked and picked != active:
            st.session_state["state"] = store.load(picked)
            st.rerun()


# --- Mission form ------------------------------------------------------------------
MODES = [
    "Find potential clients for me",
    "I already have a client in mind",
    "Demo mode (sample client, no API keys needed)",
]


def offer_fields(d: OfferProfile | None) -> dict:
    return {
        "capabilities": st.text_area("What can you build? *", d.capabilities if d else "", placeholder="I build professional websites and booking systems for local shops.").strip(),
        "industry": st.text_input("Type of business to target *", d.industry if d else "", placeholder="Mobile phone shops").strip(),
        "country": st.text_input("Country *", d.country if d else "").strip(),
        "city": st.text_input("City (optional, gives better results)", d.city if d else "").strip(),
        "language": st.selectbox("Language for the demo and email", ["English", "Spanish"]),
        "sender_name": st.text_input("Your name (optional, signs the email)", d.sender_name if d else "").strip(),
        "sender_business": st.text_input("Your business name (optional)", d.sender_business if d else "").strip(),
    }


def make_offer(fields: dict) -> OfferProfile | None:
    try:
        return OfferProfile(**fields)
    except ValidationError:
        st.error("Please fill in the three fields marked *.")
        return None


def hunt_form() -> None:
    st.write("Describe what you can build. ForgeFlow searches for businesses that could need it.")
    with st.form("hunt"):
        fields = offer_fields(None)
        submitted = st.form_submit_button("Find potential clients", type="primary")
    if submitted:
        st.session_state.pop("candidates", None)
        offer = make_offer(fields)
        if offer:
            with st.spinner("Searching and checking each business. This can take up to a minute on the free AI tier..."):
                try:
                    st.session_state["candidates"] = hunter.discover(offer)
                    st.session_state["hunt_offer"] = offer
                except AgentError as exc:
                    st.error(str(exc))

    hunt = st.session_state.get("candidates")
    if not hunt:
        return
    offer = st.session_state["hunt_offer"]
    candidates = hunt.candidates
    no_site = [c for c in candidates if not c.website]
    with_site = [c for c in candidates if c.website]
    if candidates:
        st.subheader(f"{len(candidates)} potential clients found and checked")
        st.caption(
            "Each business was checked with its own search: right type of business, not a chain branch, located in "
            "your target area. Choose one and ForgeFlow researches it in depth before building anything."
        )
    else:
        st.warning(
            f"No suitable independent business was confirmed in {offer.city or offer.country}. "
            "The businesses found and why they were left out are listed below. Try a nearby larger town or a broader business type."
        )
    for c in no_site:
        candidate_card(c, offer, len(candidates))
    if with_site:
        with st.expander(f"Already have their own website ({len(with_site)}), lower priority for a website offer"):
            for c in with_site:
                candidate_card(c, offer, len(candidates))
    if hunt.rejected:
        with st.expander(f"Left out after checking ({len(hunt.rejected)})", expanded=not candidates):
            for c in hunt.rejected:
                st.markdown(f"**{plain(c.name)}**: {plain(c.note)}")
                st.caption(f"Found at: {c.source_url}")


def candidate_card(c, offer: OfferProfile, total: int) -> None:
    with st.container(border=True):
        left, right = st.columns([5, 1])
        with left:
            st.markdown(f"**{plain(c.name)}**")
            st.markdown(plain(c.why))
            if c.location_quote:
                st.caption(f"Location evidence: {plain(c.location_quote)}")
            st.caption(f"Own website: {c.website}" if c.website else "Own website: none found in search (not proof that none exists)")
            st.caption(f"Found at: {c.source_url}")
        if right.button("Select", key=f"pick-{c.name}", use_container_width=True):
            client = Prospect(name=c.name, website=c.website, city=offer.city, country=offer.country)
            note = f"Found {total} potential clients for this offer; {c.name} was selected."
            st.session_state["state"] = orchestrator.new_run(offer, client, "live", hunt_note=note)
            st.session_state.pop("candidates", None)
            st.rerun()


def client_form(demo: bool) -> None:
    fixture = orchestrator.load_fixture() if demo else None
    client_d = fixture["prospect"] if demo else None

    with st.form("mission"):
        left, right = st.columns(2)
        with left:
            st.subheader("Your offer")
            fields = offer_fields(fixture["offer"] if demo else None)
        with right:
            st.subheader("Potential client")
            if demo:
                st.info("Sample data for a fictional business. Research results are bundled, not live.")
            name = st.text_input("Business name *", client_d.name if demo else "", disabled=demo)
            website = st.text_input("Website (optional)", "", disabled=demo)
            p_city = st.text_input("City (optional)", client_d.city if demo else "", disabled=demo)
            p_country = st.text_input("Country (optional)", client_d.country if demo else "", disabled=demo)
            email = st.text_input("Contact email (optional, used only after your approval)", client_d.email if demo else "")
            phone = st.text_input("Phone (optional, shown on the demo)", "")
            address = st.text_input("Address (optional, shown on the demo)", client_d.address if demo else "")
            notes = st.text_area("Notes (optional)", "")
        submitted = st.form_submit_button("Create mission", type="primary")

    if not submitted:
        return
    if email and not config.valid_email(email):
        st.error("The contact email address is not valid.")
        return
    offer = make_offer(fields)
    if offer is None:
        return
    try:
        client = Prospect(
            name=(client_d.name if demo else name).strip(), website=website.strip(),
            city=(client_d.city if demo else p_city).strip(), country=(client_d.country if demo else p_country).strip(),
            email=email.strip(), phone=phone.strip(), address=address.strip(), notes=notes.strip(),
        )
        st.session_state["state"] = orchestrator.new_run(offer, client, "demo" if demo else "live")
    except ValidationError:
        st.error("Please enter the business name.")
        return
    except ValueError as exc:
        st.error(str(exc))
        return
    st.rerun()


def mission_form() -> None:
    st.header("Start a mission")
    live = config.llm_available() and config.search_available()
    mode = st.radio("How do you want to start?", MODES, index=0 if live else 2)
    if mode == MODES[0]:
        hunt_form()
    else:
        client_form(demo=mode == MODES[2])


# --- Mission dashboard -------------------------------------------------------------
def dashboard(state: WorkflowState) -> None:
    st.header(state.prospect.name)
    st.caption(f"{state.offer.industry} · {state.prospect.city} {state.prospect.country} · mission {state.id}")
    if state.mode == "demo":
        st.info("Demo mode: the research below is bundled sample data about a fictional business.")

    for col, (label, done) in zip(st.columns(7), state.progress()):
        with col.container(border=True):
            st.markdown(f"**{label}**")
            st.markdown(":green[Complete]" if done else ":gray[Pending]")

    tabs = st.tabs(["Mission", "Research & Evidence", "Demo", "Outreach & Approval", "Customer Reply", "Requirements & PRD", "Agent Activity"])

    with tabs[0]:
        left, right = st.columns(2)
        with left:
            st.subheader("Offer")
            st.markdown(plain(state.offer.capabilities))
            st.caption(f"Target: {state.offer.industry}, {state.offer.city} {state.offer.country} · Language: {state.offer.language}")
        with right:
            st.subheader("Potential client")
            st.markdown(plain(state.prospect.name))
            for label, value in (("Website", state.prospect.website), ("Email", state.prospect.email), ("Address", state.prospect.address), ("Notes", state.prospect.notes)):
                if value:
                    st.caption(f"{label}: {value}")

    with tabs[1]:
        if st.button("Run research" if state.report is None else "Re-run research", type="primary" if state.report is None else "secondary"):
            run(orchestrator.run_research)
        if state.report:
            st.subheader("Opportunity")
            st.markdown(plain(state.report.summary))
            st.markdown("**Recommended solution**")
            st.markdown(plain(state.report.recommended_solution))
            left, right = st.columns(2)
            with left:
                st.subheader("Business facts")
                evidence_cards(state.report.business_facts)
            with right:
                st.subheader("Need signals")
                evidence_cards(state.report.need_signals)
            with st.expander(f"Sources consulted ({len(state.report.sources)})"):
                for src in state.report.sources:
                    st.markdown(f"{plain(src.title) or 'Source'}: {src.url}")

    with tabs[2]:
        if state.report is None:
            st.caption("Run research first.")
        else:
            if st.button("Build demo" if state.artifact is None else "Rebuild demo", type="primary" if state.artifact is None else "secondary"):
                run(orchestrator.run_demo)
        if state.artifact:
            st.markdown("**Shareable demo link**")
            st.code(state.artifact.url, language=None)
            st.download_button("Download HTML", state.artifact.html, file_name=f"{state.id}.html", mime="text/html")
            components.html(state.artifact.html, height=720, scrolling=True)

    with tabs[3]:
        if state.artifact is None:
            st.caption("Build the demo first.")
        else:
            if st.button("Draft proposal and email" if state.outreach is None else "Redraft", type="primary" if state.outreach is None else "secondary"):
                run(orchestrator.run_outreach)
        if state.outreach:
            with st.expander("Proposal", expanded=True):
                st.markdown(safe_md(state.outreach.proposal))
            left, right = st.columns(2)
            with left:
                st.markdown("**Follow-up draft**")
                st.markdown(plain(state.outreach.follow_up))
            with right:
                st.markdown("**Social post draft**")
                st.markdown(plain(state.outreach.social_post))

            st.subheader("Approval")
            sent = state.send_result is not None and state.send_result.status == "sent"
            if state.send_result:
                if sent:
                    st.success(f"Sent to {state.send_result.recipient}. {state.send_result.detail}")
                else:
                    st.warning(f"Approved as preview. {state.send_result.detail}")
            if not config.email_available():
                st.caption("Email credentials are not configured: approving records the approval and shows a preview. Nothing is sent.")
            recipient = st.text_input("To", state.prospect.email, key=f"to-{state.id}", disabled=sent)
            subject = st.text_input("Subject", state.outreach.email_subject, key=f"subject-{state.id}", disabled=sent)
            body = st.text_area("Email", state.outreach.email_body, height=320, key=f"body-{state.id}", disabled=sent)
            approved = st.checkbox("I have read this email and approve sending it to the address above.", key=f"approve-{state.id}", disabled=sent)
            if st.button("Approve and send", type="primary", disabled=sent or not approved):
                run(orchestrator.approve_and_send, approved, recipient, subject, body)

    with tabs[4]:
        if state.outreach is None:
            st.caption("Draft the outreach first.")
        else:
            reply_key = f"reply-{state.id}"
            st.session_state.setdefault(reply_key, state.reply_text)
            if state.mode == "demo" and st.button("Insert sample reply"):
                st.session_state[reply_key] = orchestrator.load_fixture()["sample_reply"]
            reply = st.text_area("Paste the customer's reply", height=160, key=reply_key)
            if st.button("Analyse reply", type="primary"):
                run(orchestrator.run_reply, reply)
        if state.reply_analysis:
            a = state.reply_analysis
            st.subheader(f"Intent: {a.intent.replace('_', ' ')}")
            st.markdown(plain(a.summary))
            left, right = st.columns(2)
            with left:
                bullet_list("Questions", a.questions)
                bullet_list("Objections", a.objections)
            with right:
                bullet_list("Requested features", a.requested_features)
                bullet_list("Still to find out", a.missing_information)
            st.markdown("**Suggested response (draft, not sent)**")
            st.markdown(plain(a.suggested_response))

    with tabs[5]:
        if state.reply_analysis is None:
            st.caption("Analyse a customer reply first.")
        else:
            if st.button("Generate requirements and PRD" if state.prd is None else "Regenerate", type="primary" if state.prd is None else "secondary"):
                run(orchestrator.run_requirements)
        if state.requirements and state.prd:
            r = state.requirements
            left, right = st.columns(2)
            with left:
                bullet_list("Functional requirements", r.functional)
                bullet_list("Pages", r.pages)
                bullet_list("Integrations", r.integrations)
                bullet_list("Content needed", r.content_needed)
            with right:
                bullet_list("Assumptions", r.assumptions)
                bullet_list("Open questions", r.open_questions)
                bullet_list("Acceptance criteria", r.acceptance_criteria)
                bullet_list("Out of scope", r.out_of_scope)
            st.download_button("Download PRD (Markdown)", state.prd.markdown, file_name=f"{state.id}-prd.md", mime="text/markdown")
            with st.expander("Full PRD", expanded=True):
                st.markdown(safe_md(state.prd.markdown))

    with tabs[6]:
        for event in reversed(state.activity):
            color, label = ACTIVITY_STYLE[event.status]
            st.markdown(f"`{event.time}` **{event.agent}** :{color}[{label}] {plain(event.message)}")


if current() is None:
    mission_form()
else:
    dashboard(current())
