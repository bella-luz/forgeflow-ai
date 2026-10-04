# ForgeFlow AI — Product Requirements Document

**Tagline:** You build. ForgeFlow finds the client, builds the demo and prepares the project.

**Category:** Agentic AI / AI-powered business automation

**Status:** Hackathon MVP (PakAngels GenAI & Agentic AI Training, Cohort 11, final hackathon, 02–04 October 2026)

**Team:** six members (one team leader and five members); names and roles are listed in the submission form.

**Live app:** https://forgeflow-ai.streamlit.app

**Source code:** https://github.com/bella-luz/forgeflow-ai

## 1. Problem

AI tools have made building software cheap. Freelancers, students, small agencies and no-code builders can now produce a website or an app in hours. The hard part has moved: they can build, but they do not know who will pay for it.

Existing lead tools hand over a list of businesses. A list does not say whether a business actually has a need, and it gives the builder nothing to show.

## 2. Solution

ForgeFlow AI starts from what the user can build and works forward to a signed-off project:

```
What you can build
  → research a prospect
  → find evidence of a real need
  → build a personalized demo website for that prospect
  → write the proposal and outreach email
  → human approves, email is sent
  → analyse the customer's reply
  → structured requirements
  → project PRD ready for a developer or coding agent
```

The differentiator is the demo. ForgeFlow does not only find a lead; it builds the thing being sold, for that specific business, before the first contact.

### Why ForgeFlow stands out

- **A complete AI sales team in one app.** Lead tools stop at a list. ForgeFlow covers the whole journey: finding the client, proving the need, building a personalized demo, writing the pitch, reading the reply and delivering a ready-to-build PRD.
- **It shows instead of tells.** Every pitch arrives with a working website made for that business, in the client's own language.
- **Trustworthy by design.** Every fact carries its evidence label and source, safeguards are enforced in code and covered by 60 automated tests, and nothing is sent without human approval.
- **Real businesses, real addresses.** Client search uses map listings with street addresses and sets chains aside.
- **Production habits from day one.** Typed data between agents, saved state after every step, graceful fallbacks, and a demo mode that runs with no API keys.
- **Zero running cost.** The entire MVP runs on free tiers.

## 3. Target users

- Freelance web and app developers
- Small agencies
- Students and AI-assisted builders who can ship but have no sales pipeline

## 4. Scope of the MVP

### In scope

| # | Feature | Status |
|---|---|---|
| 1 | User describes their offer, target industry and geography | Built |
| 2 | Hunt Mode: search the web for businesses that match the offer and list them as potential clients to choose from | Built |
| 2a | Target Mode: start from a potential client the user already knows | Built |
| 3 | Opportunity report with evidence labelled Verified, Likely or Needs review, each with its source | Built |
| 4 | Personalized website demo generated from the report, with a shareable link | Built |
| 5 | Proposal, outreach email, follow-up and social post drafts | Built |
| 6 | Human approval gate before any email is sent; preview-only without email credentials | Built |
| 7 | Customer reply analysis: intent, questions, objections, requested features | Built |
| 8 | Structured requirements and a generated project PRD (downloadable) | Built |
| 9 | Demo mode that runs the whole workflow with no API keys | Built |
| 10 | Agent activity timeline | Built |

### Out of scope for the MVP

- Continuous or large-scale client hunting, and ranking of potential clients
- Mass or automated outreach
- Phone, WhatsApp or LinkedIn automation
- Social media publishing
- Generating products other than a website (booking systems, apps, AI agents)
- User accounts and multi-user data separation

These are listed under Future scope.

## 5. Functional requirements

1. The user enters what they can build and their sender identity, and chooses the language for the demo and email: automatic (from the client's country: English, Spanish, French, German, Italian or Portuguese) or a specific one.
2. The user chooses how to start:
   - **Find potential clients:** the system looks up the target town on OpenStreetMap and lists the businesses of the target type mapped there, with their street address and any website, phone, email and opening hours on the listing. Branches of chains and network operators are set aside with the reason. For listings without a website, a web search checks whether the business has one. Businesses without a website are listed first. Each has a Google Maps link so the user can confirm it is still there. If the map lists fewer than three, a web search adds businesses that pass strict checks (named in a result, right type, not a chain, located in the town, with a page of their own). The user selects one.
   - **Known client:** the user enters the business name and country, and optionally town, address, phone, website and email. The type of business is optional. Before research, the system looks the business up on OpenStreetMap to add its exact location and any missing details; values the user entered are never overwritten.
3. The system researches the prospect with a web search provider and reads the prospect's website when one is given.
4. The system produces an opportunity report containing a summary, business facts, need signals, services found, a recommended solution and the list of sources consulted.
5. Every fact and need signal carries one of three labels:
   - **Verified** — stated in a retrieved source, with that source's URL.
   - **Likely** — a reasonable inference, with its basis explained.
   - **Needs review** — the research did not find it.
6. A claim can only be labelled Verified if its cited URL is one the system actually retrieved. Otherwise the system downgrades it automatically.
6a. If the business publishes a contact email on a retrieved page, the system records it with its source and uses it as the default recipient. An email address that does not appear word for word in a retrieved page is discarded.
7. The system builds a single-page demo website for the business in the chosen language: header with call button, hero, three website benefits, services with icons, about with address and opening hours, an appointment request form, an embedded map with the shop's location, directions link, and a WhatsApp button when a phone number is known. Services found in research are shown as they are; typical services added to fill the page are labelled as examples. The copy contains no superlatives or quality claims. The page carries a visible notice that it is a concept demo and not the business's official site.
7a. Business details already on record (entered by the user or from the map listing) are shown in the research as verified, with their origin. Search results about other businesses with similar names are ignored. A phone number or email found in research is used only if it appears in the cited page.
8. Contact details on the demo come only from the prospect record entered by the user, never from generated text.
9. The system drafts a proposal, an outreach email containing the demo link, a follow-up and a social post.
10. The email always includes the sender's identity and an opt-out line.
11. No email is sent unless the user ticks an approval box and presses the send button. The user can edit the recipient, subject and body first. One email per mission.
12. Without email credentials the approval is recorded and the email is shown as a preview; the system states that nothing was sent.
13. The user pastes the customer's reply. The system extracts intent, questions, objections, requested features and information still missing, and drafts a response.
14. The system produces structured requirements (functional requirements, pages, integrations, content needed, assumptions, open questions, acceptance criteria, out of scope) and a project PRD in Markdown.
15. Anything the customer did not say is recorded as an assumption or open question, not as a requirement.
16. Each mission is saved and can be reopened.

## 6. Non-functional requirements

- **Honesty:** the system never invents company facts, contact details, reviews, prices or customer requirements. When research fails it reports the failure instead of producing a report.
- **Reliability:** every external call has a timeout and returns a structured failure. A failed step leaves the mission's saved state unchanged and can be retried.
- **Graceful fallback:** if the language model is unavailable, the Builder, Sales and Requirements agents fall back to deterministic templates and the activity log says so.
- **Security:** API keys come from environment variables or Streamlit secrets. Text from the web and from the model is escaped before display. Generated code is never executed on the server.
- **Compliance:** only public information is used. The system does not scrape or automate platforms whose terms forbid it. Outreach is one human-approved email with sender identity and opt-out.
- **Cost:** the MVP runs entirely on free tiers.

## 7. Architecture

```
                 Streamlit dashboard (app.py)
                            |
              Orchestrator (deterministic workflow)
                            |
   +------------+-----------+-----------+----------------+
   |            |                       |                |
Opportunity   Builder            Growth & Sales     Requirements
  Hunter                                              & Delivery
   |            |                       |                |
Tavily       Jinja2 HTML           SMTP email        Markdown PRD
search       template              (after approval)
   |            |                       |                |
   +------------+-----------+-----------+----------------+
                            |
                 Groq LLM (structured JSON output)
                            |
                 SQLite (one saved state per mission)
```

**Four worker agents**

| Agent | Input | Output |
|---|---|---|
| Opportunity Hunter | Offer; then the chosen potential client | List of potential clients; opportunity report with labelled evidence and sources |
| Builder | Opportunity report | Demo specification, rendered HTML site, shareable link |
| Growth & Sales | Report, demo link; later the customer's reply | Proposal, email, follow-up, social post; reply analysis |
| Requirements & Delivery | Reply analysis, report, demo specification | Structured requirements, project PRD |

**Orchestrator.** Plain application code, not a fifth AI agent. It fixes the order of the stages, refuses to run a stage before its inputs exist, owns the approval gate, records every agent action, and saves state after each step. Agents never call each other; they return typed objects that the orchestrator passes on.

**Why this is agentic.** Each agent pursues its own goal using tools (search, page extraction, site rendering, email) and makes judgements (what counts as evidence, what the business needs, what the customer is asking for). The chain runs from a one-line statement of capability to a project specification, with a human deciding only at the approval gate.

**Structured data.** All data passed between stages is a validated Pydantic model. The demo website is rendered from a structured specification through a fixed template, so the language model writes copy, not code.

### User interface

The dashboard is a dark "mission control" interface rather than a chatbot:

- **Landing page:** animated hero, four flip cards introducing the agents, and the seven workflow steps.
- **Three ways to start:** find potential clients, start from a known client, or demo mode.
- **Client dashboard:** a header with progress bar, an animated seven-step tracker (done, current, pending), and tabs for Overview, Research, Demo website, Outreach, Client reply, Project PRD and Agent activity.
- **Evidence cards** with Verified, Likely and Needs review badges and source links; an activity timeline showing every agent action.
- **Live preview** of the generated website inside the dashboard, with a shareable link and HTML download.

Saved clients can be reopened from the sidebar. Technical service status is kept out of the interface.

## 8. Tools and technologies

| Purpose | Tool | Cost for the MVP |
|---|---|---|
| Language | Python 3.11 | Free |
| Dashboard | Streamlit | Free, open source |
| Data models and validation | Pydantic | Free, open source |
| LLM | Groq API, model `openai/gpt-oss-120b` | Free tier |
| Business listings and maps | OpenStreetMap (Nominatim search, map embed) | Free, open data (ODbL), 1 request per second |
| Web research | Tavily API | Free tier |
| Website rendering | Jinja2 template | Free, open source |
| Email | Brevo SMTP relay (free plan; any SMTP account works) | Free tier |
| Storage | SQLite | Free |
| Hosting | Streamlit Community Cloud | Free |
| Source control | GitHub | Free |
| Tests | pytest | Free, open source |
| Development | Claude Code | Existing subscription |

Framework decision: plain Python, Pydantic and direct HTTP calls. Agent frameworks (CrewAI, LangGraph, AutoGen, Pydantic AI) were considered and not used, because the workflow is a fixed sequence and typed function calls are simpler to test and debug. The application has four runtime dependencies.

Rather than rebuild pieces that already exist, the team first researched leading open-source projects and adapted their strongest ideas. The patterns were reimplemented in ForgeFlow's own code (no code was copied and none was added as a dependency):

| Project | What it informed |
|---|---|
| OpenPage (github.com/buildingopen/openpage) | Generating a site from a structured JSON specification instead of letting the model write HTML |
| Website Builder (github.com/karero/website-builder) | Website quality checklist: responsive layout, accessibility, clear calls to action |
| Social Media Agent (github.com/langchain-ai/social-media-agent) | Human-in-the-loop approval before anything is published or sent |
| Hermes Agent (github.com/NousResearch/hermes-agent) | Separating tools from agents, with typed tool results |
| Pydantic AI (github.com/pydantic/pydantic-ai) | Typed, validated outputs from the language model |
| Browser Use (github.com/browser-use/browser-use) | Research approach for public web data; full browsing was not needed because search and map data cover the MVP |

These projects are full applications in other stacks (TypeScript, LangGraph). Embedding them would have added large dependencies to a 48-hour Streamlit MVP, so the patterns were reimplemented in a few hundred lines of Python.

## 9. Finance

### Cost of the MVP

The MVP has no running cost. Every service is used on its free tier, and development used a subscription the team already had.

### Cost when scaling

The first paid items, in the order they are expected to be needed:

| Item | Why it becomes necessary |
|---|---|
| A domain name and verified email sending | Deliverability and a professional sender address |
| Paid LLM usage | Free-tier rate limits cap the number of missions per day |
| Paid search usage | Free-tier monthly allowance caps research volume |
| Hosted database and app hosting | Streamlit Community Cloud storage is temporary and single-instance |
| Demo site hosting | Permanent public links for many demos |

Prices are not stated here because they change; they will be taken from each provider's price list when the decision is made.

### Revenue model (planned)

1. **Own use first.** The team uses ForgeFlow to win its own website and automation projects. Each project won is direct revenue at near-zero acquisition cost.
2. **Subscription for builders.** A monthly plan for freelancers and small agencies, tiered by missions per month.
3. **Agency plan.** Multiple users and campaigns, with shared prospect history.

These are plans, not validated figures. The first validation step after the hackathon is to run real missions and measure reply rate and projects won.

## 10. Demo scenario

1. The user enters: "I build professional websites and booking systems for local shops", business type "Mobile phone shops", country "Spain", town "Pamplona", language English.
2. Opportunity Hunter lists the phone shops mapped in Pamplona (16 independent shops in testing, two chains set aside); the user checks one on Google Maps and selects it.
3. Opportunity Hunter researches it and shows evidence cards with sources.
4. Builder generates the personalized website; the user opens the shareable link.
5. Growth & Sales drafts the proposal and email.
6. The user reviews, edits, ticks approval and sends.
7. The customer's reply is pasted in, for example: "Yes, I want the website. Can you also add online booking and a WhatsApp button?"
8. The reply is analysed and turned into requirements and a PRD.

## 11. Success criteria

| Criterion | Target | Result |
|---|---|---|
| End-to-end workflow | One prospect through to PRD | Achieved in live and demo modes |
| Agents | Four worker agents visibly participate | Achieved, shown in the activity timeline |
| Evidence quality | No unsupported claim labelled Verified | Enforced in code and tested |
| Demo | A real, clickable personalized website | Achieved |
| Outreach | One human-approved email | Achieved: approval gate built and a real email sent through Brevo |
| Works without keys | Full demo mode | Achieved and tested |
| Quality | Automated tests | 60 tests passing, covering failures as well as the happy path |
| Cost | Free tiers only | Achieved |

## 12. Risks and limitations

- Research quality depends on what is publicly findable. A business with a common name may return results about a different business; the user must review the evidence before building on it.
- Free-tier rate limits can slow or block the language model (the free tier allows about 8,000 tokens per minute per model). The system waits and retries, uses a smaller model for light steps, and the template fallback keeps the later stages running.
- Map coverage varies. Some towns have few or no shops on OpenStreetMap (for example Estella-Lizarra had no phone shops mapped), and listings can be out of date. The app says so and offers the known-client path; every result links to Google Maps for a check.
- The web check for a business's own website matches the business name in the domain, so it can occasionally match a different business with the same name.
- Storage on Streamlit Community Cloud is temporary, so missions and demo links on the hosted app do not survive a restart.
- "No website found" is an inference from search results, not proof, and is labelled Likely.
- Outreach law differs by country. The MVP sends one human-approved email with identity and opt-out; a compliance layer is needed before any larger volume.

## 13. Future scope

ForgeFlow's roadmap turns the hackathon MVP into a full AI sales team for builders and agencies.

### Planned tools

These are for after the hackathon. The MVP itself runs entirely on free tiers.

| Next capability | Tool | Cost |
|---|---|---|
| Build the final product from the PRD | Claude API with a coding agent | Paid |
| Richer business data where map coverage is thin | Google Places API | Paid |
| Verified business contact details | Licensed data provider (for example Hunter.io) | Paid |
| WhatsApp follow-ups with the client's consent | WhatsApp Business Platform | Paid |
| Branded email from the team's own domain | Custom domain with Brevo or Resend | Paid |
| Permanent links for every demo site | Vercel or Netlify hosting | Free tier, paid at scale |
| Accounts, teams and lasting data | Supabase (Postgres and authentication) | Free tier, paid at scale |
| Subscriptions and usage analytics | Stripe and PostHog | Transaction fees / free tier |

### Planned features


- **Deeper hunting:** rank potential clients by strength of need, run searches continuously, and find contact details from licensed data sources.
- **More builders:** booking systems, ordering apps, AI customer-service agents, automations.
- **PRD to build:** hand the generated PRD to a coding agent to produce the final product.
- **Iterative requirements:** follow-up questions to the customer until open questions are closed.
- **Permanent demo hosting** on a custom domain.
- **Scheduled follow-ups** with compliance controls per country.
- **Social publishing** through official APIs.
- **Accounts, teams and a hosted database.**
- **Analytics:** opportunities found, demos built, replies, projects won.
- **Quotes and estimates** generated from the requirements.
- **More languages** for demos and outreach.
- **Contribute back to OpenStreetMap:** suggest missing shops found by users.
- **Licensed business data** (paid place APIs) where map coverage is thin.
