# ForgeFlow AI

> **From “I can build this” to a researched lead, personalized demo, human-approved outreach, and implementation-ready PRD.**

**Hackathon:** PakAngels GenAI & Agentic AI Training — Final Hackathon, 02–04 October 2026

ForgeFlow AI is an agentic workflow for freelancers, students, and small agencies who can build software but struggle to find qualified clients and turn interest into scoped projects.

Instead of stopping at lead generation, ForgeFlow researches a prospect, finds evidence of a real need, builds a personalized website demo, prepares outreach, waits for explicit human approval before sending anything, analyses the customer’s reply, and turns that conversation into structured requirements and a project PRD.

**Live app:** https://forgeflow-ai.streamlit.app

See [MANUAL.md](MANUAL.md) for the user guide and [PRD.md](PRD.md) for the full product requirements document.

---

## Why ForgeFlow?

Most lead tools give you a list.

ForgeFlow moves further:

- **Finds evidence, not just names** — every researched claim is labelled **Verified**, **Likely**, or **Needs review**.
- **Builds before asking** — the system generates a personalized concept website for the selected business before outreach.
- **Turns replies into delivery work** — customer feedback becomes structured requirements, acceptance criteria, open questions, and a downloadable PRD.
- **Keeps the human in control** — no outbound email is sent without explicit approval.
- **Researched, not reinvented** — the team studied leading open-source projects (OpenPage, LangChain Social Media Agent, Hermes Agent, Pydantic AI, Karero Website Builder, Browser Use) and adapted their strongest patterns into ForgeFlow's own lightweight code.
- **Zero running cost** — the whole MVP runs on free tiers, backed by 60 automated tests.

---

## End-to-end workflow

```text
What you can build
        ↓
Find or select a prospect
        ↓
Research the business
        ↓
Identify evidence of a real need
        ↓
Build a personalized website demo
        ↓
Draft proposal + outreach
        ↓
Human reviews and approves
        ↓
Send one email
        ↓
Analyse the customer's reply
        ↓
Extract requirements
        ↓
Generate project PRD
```

The workflow is intentionally deterministic: agents do not call each other directly. A plain-code orchestrator controls stage order, validates prerequisites, records activity, and passes typed outputs between agents.

---

## The four worker agents

| Agent | Responsibility |
|---|---|
| **Opportunity Hunter** | Finds or enriches prospects, researches the business, and labels evidence as Verified, Likely, or Needs review |
| **Builder** | Converts research into a structured website specification and renders a personalized concept site |
| **Growth & Sales** | Drafts the proposal, outreach email, follow-up, and social post; later analyses the customer's reply |
| **Requirements & Delivery** | Turns the reply into structured requirements and a project PRD |

### Orchestrator

The orchestrator is **not** a fifth AI agent.

It is deterministic application code that:

- enforces workflow order,
- prevents stages from running before their inputs exist,
- clears stale downstream outputs when an earlier stage is rerun,
- owns the human approval gate,
- records agent activity,
- saves the workflow state after each successful step.

---

## What makes it agentic?

Each worker has a specific objective, receives structured context, uses external tools where needed, makes bounded decisions, and returns a validated typed result.

Examples:

- Opportunity Hunter decides what counts as evidence and whether a signal is Verified, Likely, or Needs review.
- Builder decides how researched facts should become website copy while staying within evidence constraints.
- Growth & Sales interprets the prospect's response and extracts intent, questions, objections, and requested features.
- Requirements & Delivery converts conversation evidence into implementation-ready scope.

The system combines these specialized workers with deterministic orchestration and human approval rather than using an open-ended autonomous agent loop.

---

## Evidence-first research

ForgeFlow uses public business data and web research to build an opportunity report.

Every business fact and need signal carries one of three labels:

- **Verified** — directly supported by a retrieved source.
- **Likely** — a reasonable inference, with its basis explained.
- **Needs review** — not supported strongly enough by the available research.

A claim cannot remain **Verified** unless its cited URL was actually retrieved by the system.

Contact details receive additional validation:

- an email is kept only if it appears word-for-word in retrieved page content,
- a phone number is kept only when it is supported by the cited source,
- contact details shown in the generated demo come from the prospect record, never from free-form model generation.

---

## Personalized demo generation

The Builder does **not** ask the language model to write arbitrary HTML.

Instead:

```text
Opportunity report
        ↓
Structured DemoSpec
        ↓
Jinja2 template
        ↓
Rendered HTML demo
```

The model writes constrained website copy. The application controls the page structure and renders the final site through a fixed template.

The generated concept includes:

- hero section,
- business services,
- three website-focused highlights,
- about section,
- address and opening hours,
- appointment/request form,
- map and directions,
- phone / WhatsApp actions when available,
- a visible concept-demo notice.

Services discovered in research are treated as known services. Any typical services added only to complete the concept are marked as examples.

---

## Human-in-the-loop outreach

ForgeFlow drafts:

- a short proposal,
- outreach email,
- one-week follow-up,
- social post.

But the system cannot send the email automatically.

The user must:

1. review the recipient,
2. review or edit the subject and body,
3. explicitly tick the approval checkbox,
4. press **Approve and send**.

Only then can the SMTP tool run.

Without SMTP credentials, the same flow remains available in preview mode and nothing is sent.

Each client allows at most one successful outbound email.

---

## Reply → requirements → PRD

When the prospect replies, the user pastes the response into ForgeFlow.

Growth & Sales extracts:

- intent,
- questions,
- objections,
- requested features,
- missing information,
- a suggested response.

Requirements & Delivery then produces:

- functional requirements,
- pages,
- integrations,
- content required from the customer,
- assumptions,
- open questions,
- acceptance criteria,
- out-of-scope items.

Anything the customer did not actually request must remain an assumption or open question rather than being presented as a confirmed requirement.

The final PRD is generated in a fixed Markdown structure and can be downloaded.

---

## Architecture

```text
                    Streamlit dashboard
                 user actions │ ▲ evidence, demo, email, PRD
                              ▼ │
                 Deterministic orchestrator ──── SQLite (state saved after every step)
                              │
          typed task in,      │      typed result out
                              ▼
  1. Opportunity Hunter → 2. Builder → 3. Growth & Sales → 4. Requirements & Delivery
     OpenStreetMap,         Jinja2        SMTP email,          Markdown PRD
     Tavily search          template      after approval

  Results are handed on by the orchestrator: research report → website spec → email draft → PRD.
  Agents never call each other directly. All four use the Groq LLM for structured output.
```

---

## Tech stack

| Purpose | Technology |
|---|---|
| App | Python 3.11 |
| UI | Streamlit |
| Structured models | Pydantic |
| LLM | Groq API |
| Web research | Tavily |
| Business listings / maps | OpenStreetMap / Nominatim |
| Website rendering | Jinja2 |
| Email | SMTP |
| Persistence | SQLite |
| Testing | pytest |

The MVP intentionally avoids a heavy agent framework. Because the workflow is fixed, plain Python + typed models make it easier to test, debug, and enforce safety constraints.

---

## Demo mode

No API keys are required to understand or present the complete product flow.

Choose:

**Demo mode (sample client, no API keys needed)**

ForgeFlow loads a bundled fictional prospect and lets you run the workflow through:

```text
Research → Demo → Outreach → Reply analysis → Requirements → PRD
```

This makes the hackathon demo reproducible even when external free-tier services are unavailable.

---

## Run locally

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m streamlit run app.py
```

On macOS or Linux use `.venv/bin/python`.

---

## Configuration

Copy `.env.example` to `.env`.

Every external key is optional because the bundled Demo mode works without configuration.

| Variable | Enables |
|---|---|
| `GROQ_API_KEY` | AI-written structured output; later stages fall back to deterministic templates when possible |
| `TAVILY_API_KEY` | Live research on a real prospect |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Real email sending |
| `APP_BASE_URL` | Public address used in generated demo links |

---

## Deploy to Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create an app from branch `main`.
3. Set the main file to `app.py`.
4. Add the required values from `.env` under **Advanced settings → Secrets**.
5. Once deployed, set `APP_BASE_URL` to the public application address.

Storage on Streamlit Community Cloud is temporary. Saved clients and generated demo files may be lost when the app restarts.

---

## Tests

```bash
.venv/Scripts/python -m pytest
```

The test suite runs without credentials and blocks real network and email calls.

The 60 automated tests cover, among other things:

- evidence validation,
- safe contact handling,
- deterministic stage ordering,
- human approval before email,
- graceful fallbacks,
- typed state transitions.

---

## Project structure

```text
app.py                         Streamlit dashboard and public demo page
forgeflow/models.py            Typed objects passed between stages
forgeflow/orchestrator.py      Workflow order, approval gate, activity log
forgeflow/agents/              Four specialized worker agents
forgeflow/tools/               Search, map and email providers
forgeflow/templates/           Fixed demo website template
data/demo_prospect.json        Bundled sample prospect
tests/                         Test suite
MANUAL.md                      Plain-language user guide
PRD.md                         Full product document
```

---

**ForgeFlow AI**

*You build. ForgeFlow finds the client, proves the need, builds the demo, and prepares the project.*
