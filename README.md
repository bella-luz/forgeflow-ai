# ForgeFlow AI

You build. ForgeFlow finds the client, builds the demo and prepares the project.

ForgeFlow AI is an agentic system for freelancers and small agencies. You describe what you can build. It finds potential clients (or takes one you already know), researches the business, finds evidence of a need, builds a personalized demo website, drafts the proposal and email, waits for your approval, analyses the customer's reply, and produces a project PRD.

See [PRD.md](PRD.md) for the full product document.

## How it works

Four worker agents run under a deterministic orchestrator:

| Agent | Does |
|---|---|
| Opportunity Hunter | Researches the prospect and labels every claim Verified, Likely or Needs review |
| Builder | Generates a personalized website demo from the research |
| Growth & Sales | Writes the proposal, email, follow-up and social post; analyses the reply |
| Requirements & Delivery | Turns the reply into requirements and a PRD |

No email is sent without explicit human approval.

## Run locally

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m streamlit run app.py
```

On macOS or Linux use `.venv/bin/python`.

The app works with no configuration: choose **Demo mode** to run the whole workflow on a bundled sample prospect.

## Configuration

Copy `.env.example` to `.env` and fill in what you have. Every key is optional.

| Variable | Enables |
|---|---|
| `GROQ_API_KEY` | AI-written output (otherwise templates are used) |
| `TAVILY_API_KEY` | Live research on a real prospect |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Real email sending (otherwise preview only) |
| `APP_BASE_URL` | The public address used in demo links |

## Deploy to Streamlit Community Cloud

1. Push this repository to GitHub.
2. At https://share.streamlit.io choose **Create app**, select the repository, branch `main`, main file `app.py`.
3. Under **Advanced settings → Secrets**, paste the same keys as in `.env`, in TOML form, for example `GROQ_API_KEY = "..."`.
4. Set `APP_BASE_URL` to the app's public address once it is assigned.

Storage on Streamlit Community Cloud is temporary: saved missions and demo links are lost when the app restarts.

## Tests

```bash
.venv/Scripts/python -m pytest
```

Tests run without credentials and block all network and email calls.

## Project layout

```
app.py                  Streamlit dashboard and public demo page
forgeflow/models.py     Typed objects passed between stages
forgeflow/orchestrator.py  Workflow order, approval gate, activity log
forgeflow/agents/       The four worker agents
forgeflow/tools/        Search and email providers
forgeflow/templates/    Demo website template
data/demo_prospect.json Sample prospect for demo mode
tests/                  Test suite
```
