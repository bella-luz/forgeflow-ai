"""Visual layer for the Streamlit dashboard: styles, illustrations and HTML building blocks.

Every dynamic value passed in here is escaped with `esc` before it reaches HTML.
"""
from __future__ import annotations

import html

import streamlit as st

from .models import ActivityEvent, EvidenceItem
from .robots import ORDER as ROBOTS, robot


def esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


def safe_url(url: str) -> str:
    return esc(url) if (url or "").startswith(("http://", "https://")) else ""


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root { --bg:#0b1517; --panel:#112427; --panel2:#15302f; --line:rgba(209,232,226,.13); --text:#f2f7f6; --body:#d5e5e1; --muted:#a9c0bb;
        --a1:#2dd4bf; --a2:#a78bfa; --warm:#ffcb9a; --ok:#4ade80; --warn:#fbbf24; --bad:#f87171; }
html, body, [class*="css"], .stMarkdown, .stTextInput, .stTextArea, .stSelectbox, button { font-family:'Plus Jakarta Sans', system-ui, sans-serif !important; }
.stApp { background: radial-gradient(900px 500px at 10% -10%, rgba(17,100,102,.38), transparent 60%),
                     radial-gradient(800px 500px at 100% 0%, rgba(167,139,250,.12), transparent 60%), var(--bg); }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0f2224,#0b1517); border-right:1px solid var(--line); }
.block-container { padding-top:2.2rem; max-width:1200px; }
h1, h2, h3 { letter-spacing:-.02em; }

/* Buttons */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
  border-radius:12px; border:1px solid var(--line); font-weight:600; transition:transform .15s ease, box-shadow .2s ease, border-color .2s; }
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover { transform:translateY(-1px); border-color:rgba(45,212,191,.6); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"], .stFormSubmitButton > button[kind="primary"] {
  background:linear-gradient(135deg,#2dd4bf,#5eead4 50%,#c4b5fd); border:0; color:#04201c !important; box-shadow:0 8px 24px rgba(45,212,191,.28); }

/* Inputs, forms, containers */
[data-testid="stForm"] { background:rgba(17,36,39,.7); border:1px solid var(--line); border-radius:18px; padding:1.4rem 1.4rem .6rem; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px !important; }
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div { border-radius:10px !important; }

/* Tabs (role selectors work across Streamlit versions) */
[role="tablist"] { gap:6px; background:rgba(17,36,39,.75); padding:6px; border-radius:14px; border:1px solid var(--line); overflow-x:auto; }
[role="tab"] { min-height:40px; display:flex; align-items:center; border-radius:10px; padding:0 16px; color:var(--muted); font-weight:600; white-space:nowrap; transition:background .2s, color .2s; }
[role="tab"]:hover { color:#fff; background:rgba(255,255,255,.04); }
[role="tab"][aria-selected="true"] { background:linear-gradient(135deg,rgba(45,212,191,.32),rgba(167,139,250,.2)); color:#fff !important; box-shadow:inset 0 0 0 1px rgba(45,212,191,.45); }
[role="tab"] p { font-weight:600; font-size:14.5px; }
[role="tab"]::after { display:none !important; }
[role="tabpanel"] { animation:fadeUp .45s ease both; padding-top:1.1rem; }

@keyframes fadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
@keyframes drift { 0%,100% { transform:translate(0,0) scale(1); } 50% { transform:translate(30px,-20px) scale(1.08); } }
@keyframes spin { to { transform:rotate(360deg); } }
@keyframes float { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-9px); } }
@keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(45,212,191,.55); } 70% { box-shadow:0 0 0 12px rgba(45,212,191,0); } 100% { box-shadow:0 0 0 0 rgba(45,212,191,0); } }
@keyframes shine { from { background-position:0% 50%; } to { background-position:200% 50%; } }

/* Hero */
.ff-hero { position:relative; overflow:hidden; border-radius:24px; padding:44px 44px 40px; border:1px solid var(--line);
  background:linear-gradient(135deg,#123234 0%,#0b1517 100%); animation:fadeUp .6s ease both; }
.ff-hero .blob { position:absolute; border-radius:50%; filter:blur(50px); opacity:.55; animation:drift 12s ease-in-out infinite; }
.ff-hero .b1 { width:320px; height:320px; background:#116466; top:-120px; right:8%; }
.ff-hero .b2 { width:260px; height:260px; background:var(--a2); bottom:-140px; right:30%; animation-delay:-4s; }
.ff-hero .grid { position:relative; display:grid; grid-template-columns:1.25fr .75fr; gap:28px; align-items:center; }
.ff-kicker { display:inline-flex; gap:8px; align-items:center; font-size:12.5px; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
  color:#a7f3d0; background:rgba(45,212,191,.12); border:1px solid rgba(45,212,191,.4); padding:6px 12px; border-radius:999px; }
.ff-hero h1 { font-size:clamp(32px,4.6vw,52px); line-height:1.05; margin:18px 0 14px; color:#fff; }
.ff-grad { background:linear-gradient(90deg,#5eead4,#c4b5fd,#ffcb9a,#5eead4); background-size:200% auto; -webkit-background-clip:text; background-clip:text; color:transparent; animation:shine 6s linear infinite; }
.ff-hero p { color:var(--body); font-size:17px; max-width:560px; margin:0; }
.ff-stats { display:flex; gap:26px; margin-top:26px; flex-wrap:wrap; }
.ff-stats div b { display:block; font-size:24px; color:#fff; }
.ff-stats div span { color:var(--muted); font-size:13px; }

/* Orbit illustration */
.ff-orbit { position:relative; width:240px; height:240px; margin:0 auto; }
.ff-orbit .ring { position:absolute; inset:0; border:1px dashed rgba(255,255,255,.18); border-radius:50%; animation:spin 30s linear infinite; }
.ff-orbit .ring .node { position:absolute; width:46px; height:46px; border-radius:14px; display:grid; place-items:center; background:#15302f; border:1px solid var(--line); box-shadow:0 8px 20px rgba(0,0,0,.35); }
.ff-orbit .ring .node svg { width:22px; height:22px; animation:spin 30s linear infinite reverse; }
.ff-orbit .n1 { top:-23px; left:97px; } .ff-orbit .n2 { top:97px; right:-23px; } .ff-orbit .n3 { bottom:-23px; left:97px; } .ff-orbit .n4 { top:97px; left:-23px; }
.ff-orbit .core { position:absolute; inset:70px; border-radius:28px; display:grid; place-items:center; color:#06201d; font-weight:800; font-size:14px; text-align:center;
  background:linear-gradient(135deg,#2dd4bf,#a78bfa); box-shadow:0 16px 40px rgba(45,212,191,.35); animation:pulse 2.6s infinite; }

/* Flip cards */
.ff-section-title { margin:34px 0 14px; font-size:22px; font-weight:800; color:#fff; }
.ff-section-title span { color:var(--muted); font-weight:500; font-size:15px; margin-left:8px; }
.ff-cards { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
.ff-flip { perspective:1000px; height:310px; animation:fadeUp .6s ease both; }
.ff-flip:nth-child(2) { animation-delay:.08s; } .ff-flip:nth-child(3) { animation-delay:.16s; } .ff-flip:nth-child(4) { animation-delay:.24s; }
.ff-flip .inner { position:relative; width:100%; height:100%; transition:transform .7s cubic-bezier(.2,.8,.2,1); transform-style:preserve-3d; }
.ff-flip:hover .inner { transform:rotateY(180deg); }
.ff-face { position:absolute; inset:0; backface-visibility:hidden; border-radius:18px; padding:22px; border:1px solid var(--line); }
.ff-front { background:linear-gradient(160deg,#15302f,#0f2224); }
.ff-back { background:linear-gradient(160deg,#0f766e,#5b21b6); color:#ffffff; transform:rotateY(180deg); }
.ff-front .ic { width:52px; height:52px; border-radius:14px; display:grid; place-items:center; background:rgba(45,212,191,.16); border:1px solid rgba(45,212,191,.35); margin-bottom:16px; }
.ff-front .ic svg { width:26px; height:26px; }
.ff-front .bot { height:150px; margin:-6px 0 10px; display:flex; justify-content:center; animation:float 4.5s ease-in-out infinite; }
.ff-flip:nth-child(2) .bot { animation-delay:-1.1s; } .ff-flip:nth-child(3) .bot { animation-delay:-2.2s; } .ff-flip:nth-child(4) .bot { animation-delay:-3.3s; }
.ff-front .bot svg { height:100%; width:auto; filter:drop-shadow(0 14px 18px rgba(0,0,0,.35)); }
.ff-front { text-align:center; } .ff-front h4 { font-size:18px; }
.ff-front .num { position:absolute; top:18px; right:20px; color:rgba(209,232,226,.4); font-weight:800; font-size:28px; }
.ff-front h4, .ff-back h4 { margin:0 0 6px; font-size:17px; color:#fff; }
.ff-front p { margin:0; color:var(--body); font-size:13.5px; }
.ff-back p { margin:0; font-size:14px; line-height:1.55; }
.ff-hint { color:var(--muted); font-size:12px; margin-top:8px; }

/* Steps strip on landing */
.ff-flow { display:grid; grid-template-columns:repeat(7,1fr); gap:10px; }
.ff-flow .s { background:rgba(17,36,39,.8); border:1px solid var(--line); border-radius:14px; padding:14px; animation:fadeUp .6s ease both; }
.ff-flow .s b { display:block; color:#fff; font-size:14px; } .ff-flow .s span { color:var(--body); font-size:12.5px; }
.ff-flow .s i { font-style:normal; font-size:12px; font-weight:800; color:var(--a1); }

/* Client header and stepper */
.ff-client { display:flex; justify-content:space-between; align-items:center; gap:18px; flex-wrap:wrap; padding:22px 26px; border-radius:20px;
  border:1px solid var(--line); background:linear-gradient(135deg,#123234,#0b1517); animation:fadeUp .5s ease both; }
.ff-client h2 { margin:0; color:#fff; font-size:28px; }
.ff-chips { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
.ff-chip { font-size:12.5px; padding:5px 10px; border-radius:999px; background:rgba(209,232,226,.08); border:1px solid var(--line); color:var(--body); }
.ff-chip.demo { color:#fde68a; border-color:rgba(251,191,36,.4); background:rgba(251,191,36,.08); }
.ff-progress { min-width:200px; }
.ff-progress .bar { height:8px; border-radius:99px; background:rgba(255,255,255,.08); overflow:hidden; }
.ff-progress .fill { height:100%; border-radius:99px; background:linear-gradient(90deg,var(--a1),var(--a2)); transition:width .8s ease; }
.ff-progress small { color:var(--muted); }
.ff-steps { display:grid; grid-template-columns:repeat(7,1fr); gap:8px; margin:16px 0 8px; }
.ff-step { position:relative; text-align:center; padding:12px 6px; border-radius:14px; background:rgba(17,36,39,.8); border:1px solid var(--line); }
.ff-step .dot { width:30px; height:30px; margin:0 auto 6px; border-radius:50%; display:grid; place-items:center; font-size:13px; font-weight:800;
  background:rgba(255,255,255,.06); color:var(--muted); border:1px solid var(--line); }
.ff-step.done .dot { background:linear-gradient(135deg,#10b981,#34d399); color:#04130c; border:0; }
.ff-step.now { border-color:rgba(45,212,191,.6); }
.ff-step.now .dot { background:#7c3aed; color:#ffffff; border:0; animation:pulse 2s infinite; }
.ff-step span { font-size:12.5px; color:var(--muted); font-weight:600; } .ff-step.done span, .ff-step.now span { color:#fff; }

/* Cards */
.ff-card { background:rgba(17,36,39,.85); border:1px solid var(--line); border-radius:16px; padding:18px 18px 14px; margin-bottom:12px; animation:fadeUp .45s ease both; }
.ff-card h4 { margin:0 0 6px; color:#fff; font-size:16px; }
.ff-card p { margin:0 0 6px; color:var(--body); font-size:14.5px; }
.ff-card small, .ff-card a { color:var(--muted); font-size:12.5px; word-break:break-all; }
.ff-card a:hover { color:var(--a2); }
.ff-badge { display:inline-block; font-size:11.5px; font-weight:800; letter-spacing:.05em; text-transform:uppercase; padding:3px 9px; border-radius:999px; margin-bottom:8px; }
.ff-badge.VERIFIED { color:#052e1c; background:var(--ok); } .ff-badge.LIKELY { color:#3a2600; background:var(--warn); } .ff-badge.INSUFFICIENT { color:#0b1517; background:#b6c7c3; }
.ff-callout { border-radius:16px; padding:18px 20px; background:linear-gradient(135deg,rgba(45,212,191,.16),rgba(167,139,250,.08)); border:1px solid rgba(45,212,191,.35); margin-bottom:14px; }
.ff-callout b { color:#fff; } .ff-callout p { color:var(--body); margin:6px 0 0; }
.ff-empty { text-align:center; padding:40px 20px; border:1px dashed rgba(255,255,255,.14); border-radius:18px; color:var(--muted); }
.ff-empty svg { width:44px; height:44px; opacity:.7; margin-bottom:8px; }

/* Activity timeline */
.ff-timeline { border-left:2px solid rgba(45,212,191,.35); margin-left:8px; padding-left:20px; }
.ff-event { position:relative; margin-bottom:16px; animation:fadeUp .4s ease both; }
.ff-event::before { content:""; position:absolute; left:-27px; top:5px; width:12px; height:12px; border-radius:50%; background:var(--ok); box-shadow:0 0 0 4px var(--bg); }
.ff-event.fallback::before { background:var(--warn); } .ff-event.error::before { background:var(--bad); }
.ff-event b { color:#fff; } .ff-event small { color:var(--muted); } .ff-event p { margin:2px 0 0; color:var(--body); font-size:14px; }

/* Sidebar brand */
.ff-brand { display:flex; align-items:center; gap:10px; margin:4px 0 6px; }
.ff-brand .logo { width:38px; height:38px; border-radius:12px; display:grid; place-items:center; background:linear-gradient(135deg,var(--a1),var(--a2)); box-shadow:0 8px 20px rgba(45,212,191,.4); }
.ff-brand .logo svg { width:22px; height:22px; }
.ff-brand b { font-size:19px; color:#fff; } .ff-brand small { display:block; color:var(--muted); font-size:12px; }

@media (max-width: 900px) {
  .ff-hero { padding:28px 22px; } .ff-hero .grid { grid-template-columns:1fr; } .ff-orbit { display:none; }
  .ff-cards { grid-template-columns:repeat(2,1fr); } .ff-steps, .ff-flow { grid-template-columns:repeat(4,1fr); }
}
@media (max-width: 560px) { .ff-cards { grid-template-columns:1fr; } }
</style>
"""

_ICONS = {
    "radar": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="M12 12l6-6"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/>',
    "blocks": '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><path d="M17 13v8M13 17h8"/>',
    "send": '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/>',
    "doc": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
    "spark": '<path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4z"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13l3.5 7v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
}


def icon(name: str, color: str = "currentColor") -> str:
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{_ICONS[name]}</svg>')


AGENTS = [
    ("radar", "Opportunity Hunter", "Finds the client", "Searches the map for businesses that match what you build, sets chains aside, then researches the one you pick and labels every fact Verified, Likely or Needs review."),
    ("blocks", "Builder", "Builds the demo", "Creates a personalized website for that business, in its own language, with services, booking form, map and WhatsApp. Ready to share as a link."),
    ("send", "Growth & Sales", "Starts the sale", "Writes the proposal, the email with the demo link, a follow-up and a social post. Nothing is sent until you approve. Later it reads the client's reply."),
    ("doc", "Requirements & Delivery", "Prepares the project", "Turns the client's reply into requirements, open questions and acceptance criteria, and writes a PRD you can build from."),
]


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.markdown(
        f'<div class="ff-brand"><div class="logo">{icon("spark", "#04201c")}</div>'
        '<div><b>ForgeFlow AI</b><small>From skill to signed client</small></div></div>',
        unsafe_allow_html=True,
    )


def landing() -> None:
    nodes = "".join(f'<div class="node n{i}">{icon(a[0], c)}</div>' for i, (a, c) in enumerate(zip(AGENTS, ["#5eead4", "#c4b5fd", "#ffcb9a", "#86efac"]), 1))
    cards = "".join(
        f'<div class="ff-flip"><div class="inner">'
        f'<div class="ff-face ff-front"><span class="num">0{i}</span><div class="bot">{robot(ROBOTS[i - 1])}</div><h4>{esc(name)}</h4><p>{esc(short)}</p></div>'
        f'<div class="ff-face ff-back"><h4>{esc(name)}</h4><p>{esc(long)}</p></div>'
        f'</div></div>'
        for i, (ic, name, short, long) in enumerate(AGENTS, 1)
    )
    steps = [("Hunt", "Find businesses"), ("Research", "Evidence + sources"), ("Demo", "Personal website"), ("Outreach", "Proposal + email"),
             ("Approve", "You decide"), ("Reply", "Read the answer"), ("PRD", "Ready to build")]
    flow = "".join(f'<div class="s" style="animation-delay:{i * .05:.2f}s"><i>0{i + 1}</i><b>{a}</b><span>{b}</span></div>' for i, (a, b) in enumerate(steps))
    st.markdown(
        f"""
<div class="ff-hero"><div class="blob b1"></div><div class="blob b2"></div>
  <div class="grid">
    <div>
      <span class="ff-kicker">{icon("spark", "#a7f3d0").replace('<svg', '<svg width="14" height="14"')} Agentic AI for builders</span>
      <h1>You build.<br><span class="ff-grad">ForgeFlow finds the client.</span></h1>
      <p>Tell it what you can make. Four AI agents find a business that needs it, build that business a personalized demo website,
      write the proposal, and turn the reply into a project plan.</p>
      <div class="ff-stats"><div><b>4</b><span>specialist agents</span></div><div><b>7</b><span>steps, one flow</span></div><div><b>1</b><span>click to approve</span></div></div>
    </div>
    <div class="ff-orbit"><div class="ring">{nodes}</div><div class="core">Forge<br>Flow</div></div>
  </div>
</div>
<div class="ff-section-title">Meet the agents <span>hover a robot to see what it does</span></div>
<div class="ff-cards">{cards}</div>
<div class="ff-section-title">How it works</div>
<div class="ff-flow">{flow}</div>
<div class="ff-section-title">Start with a new client</div>
""",
        unsafe_allow_html=True,
    )


def client_header(name: str, chips: list[str], demo: bool, progress: list[tuple[str, bool]]) -> None:
    done = sum(1 for _, d in progress if d)
    pct = int(done / len(progress) * 100)
    chip_html = "".join(f'<span class="ff-chip">{esc(c)}</span>' for c in chips if c)
    if demo:
        chip_html += '<span class="ff-chip demo">Demo data</span>'
    now = next((i for i, (_, d) in enumerate(progress) if not d), None)
    steps = "".join(
        f'<div class="ff-step {"done" if d else ("now" if i == now else "")}"><div class="dot">{"✓" if d else i + 1}</div><span>{esc(label)}</span></div>'
        for i, (label, d) in enumerate(progress)
    )
    st.markdown(
        f'<div class="ff-client"><div><h2>{esc(name)}</h2><div class="ff-chips">{chip_html}</div></div>'
        f'<div class="ff-progress"><small>Progress · {done} of {len(progress)} steps</small><div class="bar"><div class="fill" style="width:{pct}%"></div></div></div></div>'
        f'<div class="ff-steps">{steps}</div>',
        unsafe_allow_html=True,
    )


def evidence(items: list[EvidenceItem]) -> None:
    labels = {"VERIFIED": "Verified", "LIKELY": "Likely", "INSUFFICIENT": "Needs review"}
    if not items:
        st.markdown('<div class="ff-empty">Nothing recorded.</div>', unsafe_allow_html=True)
    for item in items:
        status = item.status.value
        source = safe_url(item.source_url)
        st.markdown(
            f'<div class="ff-card"><span class="ff-badge {status}">{labels[status]}</span><p>{esc(item.claim)}</p>'
            + (f"<small>{esc(item.excerpt)}</small><br>" if item.excerpt else "")
            + (f'<a href="{source}" target="_blank" rel="noopener">{source}</a>' if source else "")
            + "</div>",
            unsafe_allow_html=True,
        )


def callout(title: str, body: str) -> None:
    st.markdown(f'<div class="ff-callout"><b>{esc(title)}</b><p>{esc(body)}</p></div>', unsafe_allow_html=True)


def empty(text: str, icon_name: str = "inbox") -> None:
    st.markdown(f'<div class="ff-empty">{icon(icon_name)}<div>{esc(text)}</div></div>', unsafe_allow_html=True)


def bullet_card(title: str, items: list[str]) -> None:
    body = "".join(f"<p>• {esc(i)}</p>" for i in items) or '<p style="color:var(--muted)">None recorded.</p>'
    st.markdown(f'<div class="ff-card"><h4>{esc(title)}</h4>{body}</div>', unsafe_allow_html=True)


def timeline(events: list[ActivityEvent]) -> None:
    labels = {"ok": "Done", "fallback": "Fallback", "error": "Failed"}
    rows = "".join(
        f'<div class="ff-event {e.status}"><b>{esc(e.agent)}</b> <small>· {esc(e.time)} · {labels[e.status]}</small><p>{esc(e.message)}</p></div>'
        for e in reversed(events)
    )
    st.markdown(f'<div class="ff-timeline">{rows}</div>', unsafe_allow_html=True)
