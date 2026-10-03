"""End-to-end workflow through the orchestrator, and a smoke test of the Streamlit app."""
import pytest

from forgeflow import config, orchestrator, store
from forgeflow.models import OfferProfile, Prospect


@pytest.fixture
def demo_state():
    fixture = orchestrator.load_fixture()
    return orchestrator.new_run(fixture["offer"], fixture["prospect"], "demo"), fixture


def test_demo_mode_end_to_end_without_any_credentials(demo_state):
    state, fixture = demo_state
    assert orchestrator.run_research(state)
    assert orchestrator.run_demo(state)
    assert state.prospect.name in state.artifact.html
    assert state.artifact.url.endswith(f"/?demo={state.id}")
    assert orchestrator.demo_html(state.id) == state.artifact.html

    assert orchestrator.run_outreach(state)
    assert state.artifact.url in state.outreach.email_body

    assert orchestrator.approve_and_send(state, True, state.prospect.email, state.outreach.email_subject, state.outreach.email_body)
    assert state.send_result.status == "preview" and state.approved

    assert orchestrator.run_reply(state, fixture["sample_reply"])
    assert state.reply_analysis.intent == "interested"

    assert orchestrator.run_requirements(state)
    for heading in ("## Functional requirements", "## Open questions", "## Acceptance criteria", "## Evidence"):
        assert heading in state.prd.markdown
    assert "WhatsApp" in state.prd.markdown

    assert all(done for _, done in state.progress())
    assert store.load(state.id) == state
    agents = {e.agent for e in state.activity}
    assert {"Opportunity Hunter", "Builder", "Growth & Sales", "Requirements & Delivery"} <= agents
    assert not [e for e in state.activity if e.status == "error"]


def test_steps_refuse_to_run_out_of_order(demo_state):
    state, _ = demo_state
    assert not orchestrator.run_demo(state)
    assert not orchestrator.run_outreach(state)
    assert not orchestrator.run_reply(state, "hello")
    assert not orchestrator.run_requirements(state)
    assert state.artifact is None and state.prd is None
    assert state.activity[-1].status == "error"


def test_no_email_without_approval(demo_state, monkeypatch):
    state, _ = demo_state
    orchestrator.run_research(state), orchestrator.run_demo(state), orchestrator.run_outreach(state)
    sent = []
    monkeypatch.setattr("forgeflow.tools.email.send", lambda *a: sent.append(a))
    assert not orchestrator.approve_and_send(state, False, "owner@example.com", "s", "b")
    assert sent == [] and state.send_result is None and not state.approved


def test_failed_send_is_reported_and_state_kept(demo_state):
    state, _ = demo_state
    orchestrator.run_research(state), orchestrator.run_demo(state), orchestrator.run_outreach(state)
    before = state.outreach.model_copy()
    assert not orchestrator.approve_and_send(state, True, "not-an-email", "changed", "changed")
    assert state.send_result is None and state.outreach == before
    assert "invalid" in state.activity[-1].message


def test_live_research_failure_leaves_state_intact():
    state = orchestrator.new_run(
        OfferProfile(capabilities="websites", industry="shops", country="Spain"), Prospect(name="Some Shop"), "live"
    )
    assert not orchestrator.run_research(state)
    assert state.report is None
    assert "TAVILY_API_KEY" in state.activity[-1].message


def test_rerunning_research_clears_later_stages(demo_state):
    state, fixture = demo_state
    orchestrator.run_research(state), orchestrator.run_demo(state), orchestrator.run_outreach(state)
    assert orchestrator.run_research(state)
    assert state.report is not None and state.artifact is None and state.outreach is None


def test_malformed_prospect_url_is_rejected():
    with pytest.raises(ValueError):
        orchestrator.new_run(
            OfferProfile(capabilities="websites", industry="shops", country="Spain"),
            Prospect(name="Shop", website="javascript:alert(1)"),
        )


@pytest.mark.parametrize("bad", ["../../etc/passwd", "UPPER", "", "a" * 50, "x.html"])
def test_demo_link_rejects_unsafe_ids(bad):
    assert orchestrator.demo_html(bad) is None


def test_app_renders_form_and_full_demo_run():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(config.ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert at.radio[0].value.startswith("Demo")  # no keys, so demo mode is preselected

    next(b for b in at.button if b.label == "Start with this client").click().run()
    assert not at.exception and not at.error
    assert at.session_state["state"].mode == "demo"

    def click(label):
        next(b for b in at.button if b.label == label).click().run()
        assert not at.exception, at.exception
        assert not at.error, [e.value for e in at.error]

    click("Run research")
    click("Build demo website")
    click("Draft proposal and email")
    at.checkbox[0].check().run()
    click("Approve and send")
    click("Insert sample reply")
    click("Analyse reply")
    click("Generate requirements and PRD")
    state = at.session_state["state"]
    assert state.prd is not None and state.send_result.status == "preview"
