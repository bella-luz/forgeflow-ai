"""ForgeFlow AI dashboard. Run with: streamlit run app.py"""
from __future__ import annotations

import re
from urllib.parse import quote_plus

import streamlit as st
import streamlit.components.v1 as components

from forgeflow import config, i18n, orchestrator, store, ui
from forgeflow.agents import AgentError, hunter
from forgeflow.models import HuntResult, OfferProfile, Prospect, WorkflowState
from forgeflow.tools import places

config.load_env()
st.set_page_config(page_title="ForgeFlow AI", page_icon="✦", layout="wide")


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

ui.inject()


# --- Helpers -----------------------------------------------------------------------
def current() -> WorkflowState | None:
    return st.session_state.get("state")


def run(step, *args, label: str = "Working...") -> None:
    state = current()
    with st.spinner(label):
        ok = step(state, *args)
    if ok:
        st.rerun()
    st.error(state.activity[-1].message)


def action(label: str, again: str, done: bool, key: str) -> bool:
    return st.button(again if done else label, type="secondary" if done else "primary", key=key)


# --- Sidebar -----------------------------------------------------------------------
with st.sidebar:
    ui.sidebar_brand()
    st.write("")
    if st.button("New client", type="primary", use_container_width=True):
        st.session_state.pop("state", None)
        st.session_state.pop("candidates", None)
        st.rerun()
    runs = store.list_runs()
    if runs:
        active = current().id if current() else None
        picked = st.selectbox("Saved clients", runs, index=runs.index(active) if active in runs else None, placeholder="Open a saved client...")
        if picked and picked != active:
            st.session_state["state"] = store.load(picked)
            st.rerun()
    st.caption("Every email waits for your approval. Facts are labelled Verified, Likely or Needs review.")


# --- Mission form ------------------------------------------------------------------
MODES = [
    "Find potential clients for me",
    "I already have a client in mind",
    "Demo mode (sample client, no API keys needed)",
]
LANG_OPTIONS = [i18n.AUTO] + i18n.LANGUAGES


def sender_fields(d: OfferProfile | None) -> dict:
    return {
        "language": st.selectbox(
            "Language for the demo site and email", LANG_OPTIONS,
            index=LANG_OPTIONS.index(d.language) if d and d.language in LANG_OPTIONS else 0,
            help="Auto uses the main language of the client's country, or English if unknown.",
        ),
        "sender_name": st.text_input("Your name (optional, signs the email)", d.sender_name if d else "").strip(),
        "sender_business": st.text_input("Your business name (optional)", d.sender_business if d else "").strip(),
    }


def hunt_form() -> None:
    st.write("Describe what you can build. ForgeFlow finds businesses on the map that could need it, and checks each one.")
    with st.form("hunt"):
        capabilities = st.text_area("What can you build? *", placeholder="I build professional websites and booking systems for local shops.").strip()
        industry = st.text_input("Type of business to target *", placeholder="Mobile phone shops").strip()
        left, right = st.columns(2)
        country = left.text_input("Country *").strip()
        city = right.text_input("City or town (recommended)").strip()
        sender = sender_fields(None)
        submitted = st.form_submit_button("Find potential clients", type="primary")
    if submitted:
        st.session_state.pop("candidates", None)
        if len(capabilities) < 3 or not industry or not country:
            st.error("Please fill in the three fields marked *.")
            return
        offer = OfferProfile(
            capabilities=capabilities, industry=industry, country=country, city=city,
            language=i18n.resolve(sender["language"], country),
            sender_name=sender["sender_name"], sender_business=sender["sender_business"],
        )
        with st.spinner("Searching the map and checking each business. This can take up to a minute..."):
            try:
                st.session_state["candidates"] = hunter.discover(offer)
                st.session_state["hunt_offer"] = offer
            except AgentError as exc:
                st.error(str(exc))

    hunt = st.session_state.get("candidates")
    if not isinstance(hunt, HuntResult):  # also discards results saved by an older version of the app
        return
    offer = st.session_state["hunt_offer"]
    candidates = hunt.candidates
    no_site = [c for c in candidates if not c.website]
    with_site = [c for c in candidates if c.website]
    if candidates:
        st.subheader(f"{len(candidates)} potential clients found")
        st.caption(
            "Businesses without a website come first. Chains are left out. "
            "Listings can be out of date, so check a business on the map before you select it."
        )
    else:
        st.warning(
            f"No suitable independent {offer.industry.lower()} could be found in {offer.city or offer.country}. "
            "The map may simply not list them yet. If you know a business there, use \"I already have a client in mind\"."
        )
    for c in no_site:
        candidate_card(c, offer, len(candidates))
    if with_site:
        with st.expander(f"Already have their own website ({len(with_site)}), lower priority for a website offer"):
            for c in with_site:
                candidate_card(c, offer, len(candidates))
    if hunt.rejected:
        with st.expander(f"Left out ({len(hunt.rejected)})", expanded=not candidates):
            for c in hunt.rejected:
                st.markdown(f"**{plain(c.name)}**: {plain(c.note)}")
    if any(c.found_on == "OpenStreetMap" for c in candidates + hunt.rejected):
        st.caption(places.ATTRIBUTION)


def candidate_card(c, offer: OfferProfile, total: int) -> None:
    with st.container(border=True):
        left, right = st.columns([5, 1])
        with left:
            st.markdown(f"**{plain(c.name)}**")
            if c.address or c.location_quote:
                st.caption(f"Address: {plain(c.address or ' '.join(c.location_quote.split()))}")
            st.caption(f"Own website: {c.website}" if c.website else "Own website: none found (not proof that none exists)")
            details = [x for x in (("phone on listing" if c.phone else ""), ("email on listing" if c.email else ""), ("opening hours" if c.opening_hours else "")) if x]
            st.caption(f"Found on: {c.found_on}" + (f" · {', '.join(details)}" if details else ""))
            maps = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(f"{c.name} {c.address or offer.city} {offer.country}")
            st.markdown(f"[Check it on Google Maps]({maps})")
        if right.button("Select", key=f"pick-{c.name}-{c.source_url}", use_container_width=True):
            client = Prospect(
                name=c.name, website=c.website, city=offer.city, country=offer.country, email=c.email, phone=c.phone,
                address=c.address, opening_hours=c.opening_hours, lat=c.lat, lon=c.lon,
                map_url=c.presence_url if c.found_on == "OpenStreetMap" else "",
            )
            note = f"Found {total} potential clients for this offer; {c.name} was selected."
            st.session_state["state"] = orchestrator.new_run(offer, client, "live", hunt_note=note)
            st.session_state.pop("candidates", None)
            st.rerun()


def client_form(demo: bool) -> None:
    fixture = orchestrator.load_fixture() if demo else None
    d_offer = fixture["offer"] if demo else None
    d_client = fixture["prospect"] if demo else None

    with st.form("mission"):
        left, right = st.columns(2)
        with left:
            st.subheader("Your offer")
            capabilities = st.text_area("What can you build? *", d_offer.capabilities if demo else "", placeholder="I build professional websites and booking systems for local shops.").strip()
            industry = st.text_input("Type of business (optional, helps the research)", d_offer.industry if demo else "", placeholder="Mobile phone shop").strip()
            sender = sender_fields(d_offer)
        with right:
            st.subheader("The client")
            if demo:
                st.info("Sample data for a fictional business. Research results are bundled, not live.")
            name = st.text_input("Business name *", d_client.name if demo else "", disabled=demo).strip()
            country = st.text_input("Country *", d_client.country if demo else "", disabled=demo).strip()
            city = st.text_input("City or town", d_client.city if demo else "", disabled=demo).strip()
            address = st.text_input("Address (as on Google Maps)", d_client.address if demo else "").strip()
            phone = st.text_input("Phone", "").strip()
            website = st.text_input("Website, if it has one", "", disabled=demo).strip()
            email = st.text_input("Email (used only after your approval)", d_client.email if demo else "").strip()
            notes = st.text_area("Notes (optional)", "").strip()
        submitted = st.form_submit_button("Start with this client", type="primary")

    if not submitted:
        return
    if len(capabilities) < 3 or len(name) < 2 or not country:
        st.error("Please fill in the fields marked *.")
        return
    if email and not config.valid_email(email):
        st.error("The email address is not valid.")
        return
    offer = OfferProfile(
        capabilities=capabilities, industry=industry, country=country, city=city,
        language=i18n.resolve(sender["language"], country),
        sender_name=sender["sender_name"], sender_business=sender["sender_business"],
    )
    client = Prospect(name=name, website=website, city=city, country=country, email=email, phone=phone, address=address, notes=notes)
    try:
        st.session_state["state"] = orchestrator.new_run(offer, client, "demo" if demo else "live")
    except ValueError as exc:
        st.error(str(exc))
        return
    st.rerun()


def mission_form() -> None:
    ui.landing()
    live = config.llm_available() and config.search_available()
    mode = st.radio("How do you want to start?", MODES, index=0 if live else 2, horizontal=True, label_visibility="collapsed")
    if mode == MODES[0]:
        hunt_form()
    else:
        client_form(demo=mode == MODES[2])


# --- Client dashboard --------------------------------------------------------------
def dashboard(state: WorkflowState) -> None:
    place = ", ".join(x for x in (state.prospect.city, state.prospect.country) if x)
    ui.client_header(state.prospect.name, [state.offer.industry, place, state.offer.language], state.mode == "demo", state.progress())

    tabs = st.tabs(["Overview", "Research", "Demo website", "Outreach", "Client reply", "Project PRD", "Agent activity"])

    with tabs[0]:
        left, right = st.columns(2)
        with left:
            ui.bullet_card("Your offer", [state.offer.capabilities])
            if state.offer.sender_name or state.offer.sender_business:
                ui.bullet_card("Sender", [x for x in (state.offer.sender_name, state.offer.sender_business) if x])
        with right:
            details = [f"{k}: {v}" for k, v in (("Address", state.prospect.address), ("Phone", state.prospect.phone), ("Website", state.prospect.website),
                                                 ("Email", state.prospect.email), ("Opening hours", state.prospect.opening_hours), ("Notes", state.prospect.notes)) if v]
            ui.bullet_card(state.prospect.name, details or ["Only the name is known so far. Research will look for more."])
        if state.mode == "demo":
            ui.callout("Demo data", "The research for this client is bundled sample data about a fictional business.")
        if state.report is None:
            ui.callout("Next step", "Open the Research tab and run the Opportunity Hunter.")

    with tabs[1]:
        if action("Run research", "Re-run research", state.report is not None, "research"):
            run(orchestrator.run_research, label="Opportunity Hunter is researching the business...")
        if state.report is None:
            ui.empty("The Opportunity Hunter will look up this business and label every fact it finds.", "radar")
        else:
            ui.callout("Opportunity", state.report.summary)
            ui.callout("Recommended solution", state.report.recommended_solution)
            left, right = st.columns(2)
            with left:
                st.markdown("#### Business facts")
                ui.evidence(state.report.business_facts)
            with right:
                st.markdown("#### Need signals")
                ui.evidence(state.report.need_signals)
            with st.expander(f"Sources consulted ({len(state.report.sources)})"):
                for src in state.report.sources:
                    st.markdown(f"{plain(src.title) or 'Source'}: {src.url}")

    with tabs[2]:
        if state.report is None:
            ui.empty("Run the research first. The Builder uses it to personalize the site.", "blocks")
        elif action("Build demo website", "Rebuild demo", state.artifact is not None, "demo"):
            run(orchestrator.run_demo, label="Builder is designing the website...")
        if state.artifact:
            left, right = st.columns([3, 1])
            with left:
                st.markdown("**Shareable demo link**")
                st.code(state.artifact.url, language=None)
            with right:
                st.write("")
                st.download_button("Download HTML", state.artifact.html, file_name=f"{state.id}.html", mime="text/html", use_container_width=True)
            components.html(state.artifact.html, height=760, scrolling=True)

    with tabs[3]:
        if state.artifact is None:
            ui.empty("Build the demo website first. The email links to it.", "send")
        elif action("Draft proposal and email", "Redraft", state.outreach is not None, "outreach"):
            run(orchestrator.run_outreach, label="Growth & Sales is writing the proposal...")
        if state.outreach:
            sub = st.tabs(["Email and approval", "Proposal", "Follow-up", "Social post"])
            with sub[1]:
                st.markdown(safe_md(state.outreach.proposal))
            with sub[2]:
                ui.bullet_card("Follow-up email (for a week later)", [state.outreach.follow_up])
            with sub[3]:
                ui.bullet_card("Social media post", [state.outreach.social_post])
            with sub[0]:
                sent = state.send_result is not None and state.send_result.status == "sent"
                if state.send_result:
                    if sent:
                        st.success(f"Sent to {state.send_result.recipient}. {state.send_result.detail}")
                    else:
                        st.warning(f"Approved as preview. {state.send_result.detail}")
                if not config.email_available():
                    st.caption("Email sending is not configured: approving records the approval and shows a preview. Nothing is sent.")
                recipient = st.text_input("To", state.prospect.email, key=f"to-{state.id}", disabled=sent)
                subject = st.text_input("Subject", state.outreach.email_subject, key=f"subject-{state.id}", disabled=sent)
                body = st.text_area("Email", state.outreach.email_body, height=320, key=f"body-{state.id}", disabled=sent)
                approved = st.checkbox("I have read this email and approve sending it to the address above.", key=f"approve-{state.id}", disabled=sent)
                if st.button("Approve and send", type="primary", disabled=sent or not approved):
                    run(orchestrator.approve_and_send, approved, recipient, subject, body, label="Sending...")

    with tabs[4]:
        if state.outreach is None:
            ui.empty("Draft the outreach first. Then paste the client's answer here.", "inbox")
        else:
            reply_key = f"reply-{state.id}"
            st.session_state.setdefault(reply_key, state.reply_text)
            if state.mode == "demo" and st.button("Insert sample reply"):
                st.session_state[reply_key] = orchestrator.load_fixture()["sample_reply"]
            reply = st.text_area("Paste the client's reply", height=160, key=reply_key)
            if st.button("Analyse reply", type="primary"):
                run(orchestrator.run_reply, reply, label="Growth & Sales is reading the reply...")
        if state.reply_analysis:
            a = state.reply_analysis
            ui.callout(f"Intent: {a.intent.replace('_', ' ')}", a.summary)
            left, right = st.columns(2)
            with left:
                ui.bullet_card("Questions", a.questions)
                ui.bullet_card("Objections", a.objections)
            with right:
                ui.bullet_card("Requested features", a.requested_features)
                ui.bullet_card("Still to find out", a.missing_information)
            ui.bullet_card("Suggested response (draft, not sent)", [a.suggested_response])

    with tabs[5]:
        if state.reply_analysis is None:
            ui.empty("Analyse the client's reply first. The PRD is built from it.", "doc")
        elif action("Generate requirements and PRD", "Regenerate", state.prd is not None, "prd"):
            run(orchestrator.run_requirements, label="Requirements & Delivery is writing the PRD...")
        if state.requirements and state.prd:
            r = state.requirements
            sub = st.tabs(["Requirements", "Full PRD"])
            with sub[0]:
                left, right = st.columns(2)
                with left:
                    ui.bullet_card("Functional requirements", r.functional)
                    ui.bullet_card("Pages", r.pages)
                    ui.bullet_card("Integrations", r.integrations)
                    ui.bullet_card("Content needed from the client", r.content_needed)
                with right:
                    ui.bullet_card("Assumptions", r.assumptions)
                    ui.bullet_card("Open questions", r.open_questions)
                    ui.bullet_card("Acceptance criteria", r.acceptance_criteria)
                    ui.bullet_card("Out of scope", r.out_of_scope)
            with sub[1]:
                st.download_button("Download PRD (Markdown)", state.prd.markdown, file_name=f"{state.id}-prd.md", mime="text/markdown")
                st.markdown(safe_md(state.prd.markdown))

    with tabs[6]:
        ui.timeline(state.activity)


if current() is None:
    mission_form()
else:
    dashboard(current())
