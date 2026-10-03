"""Original robot illustrations for the four agents (inline SVG, no external images)."""
from __future__ import annotations

# name: (accent, accent_dark)
_STYLE = {
    "hunter": ("#2dd4bf", "#0f766e"),
    "builder": ("#a78bfa", "#6d28d9"),
    "sales": ("#ffb27a", "#c2410c"),
    "delivery": ("#4ade80", "#15803d"),
}


def _prop(name: str, a: str, d: str) -> str:
    if name == "hunter":  # magnifying glass and radar waves
        return (
            f'<path d="M100 18 a26 26 0 0 1 26 -8" stroke="{a}" stroke-width="3" fill="none" opacity=".7"/>'
            f'<path d="M100 10 a40 40 0 0 1 40 -6" stroke="{a}" stroke-width="3" fill="none" opacity=".4"/>'
            f'<line x1="150" y1="140" x2="166" y2="158" stroke="{d}" stroke-width="7" stroke-linecap="round"/>'
            f'<circle cx="142" cy="128" r="17" fill="{a}" fill-opacity=".18" stroke="{a}" stroke-width="5"/>'
            f'<circle cx="137" cy="123" r="4" fill="#ffffff" opacity=".8"/>'
        )
    if name == "builder":  # hard hat and wrench
        return (
            f'<path d="M58 54 a42 30 0 0 1 84 0 z" fill="{a}"/>'
            f'<rect x="52" y="50" width="96" height="9" rx="4.5" fill="{d}"/>'
            f'<rect x="94" y="30" width="12" height="14" rx="4" fill="{d}"/>'
            f'<path d="M146 112 l18 -18 a9 9 0 1 1 8 8 l-18 18 z" fill="#d7dee9" stroke="{d}" stroke-width="3" stroke-linejoin="round"/>'
            f'<circle cx="170" cy="96" r="4" fill="{d}"/>'
        )
    if name == "sales":  # paper plane with dashed trail
        return (
            f'<path d="M150 122 q18 -26 40 -40" stroke="{a}" stroke-width="3" stroke-dasharray="4 6" fill="none"/>'
            f'<path d="M168 70 l28 -10 -10 30 -6 -12 z" fill="{a}" stroke="{d}" stroke-width="2.5" stroke-linejoin="round"/>'
            f'<path d="M180 78 l6 -18" stroke="{d}" stroke-width="2.5"/>'
        )
    # delivery: clipboard with check marks
    return (
        f'<rect x="22" y="112" width="40" height="52" rx="7" fill="#f4f7fb" stroke="{d}" stroke-width="3"/>'
        f'<rect x="33" y="106" width="18" height="10" rx="3" fill="{a}"/>'
        f'<path d="M30 130 l4 4 7 -8" stroke="{d}" stroke-width="3" fill="none" stroke-linecap="round"/>'
        f'<line x1="44" y1="131" x2="55" y2="131" stroke="#9aa9bf" stroke-width="3" stroke-linecap="round"/>'
        f'<path d="M30 148 l4 4 7 -8" stroke="{d}" stroke-width="3" fill="none" stroke-linecap="round"/>'
        f'<line x1="44" y1="149" x2="55" y2="149" stroke="#9aa9bf" stroke-width="3" stroke-linecap="round"/>'
    )


def robot(name: str) -> str:
    a, d = _STYLE[name]
    k = f"rb-{name}"
    hat = name == "builder"
    antenna = "" if hat else (
        f'<line x1="100" y1="30" x2="100" y2="46" stroke="#9aa9bf" stroke-width="4"/>'
        f'<circle cx="100" cy="26" r="7" fill="{a}" filter="url(#{k}-glow)"/>'
    )
    # Arms: the right arm reaches to the prop, except delivery which holds the clipboard on the left.
    left_arm = (
        f'<rect x="44" y="124" width="18" height="40" rx="9" fill="url(#{k}-metal)" transform="rotate({40 if name == "delivery" else 16} 53 124)"/>'
    )
    right_arm = (
        f'<rect x="138" y="122" width="18" height="40" rx="9" fill="url(#{k}-metal)" transform="rotate({-50 if name != "delivery" else -16} 147 122)"/>'
    )
    return f"""<svg viewBox="0 0 210 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{name} robot">
<defs>
  <linearGradient id="{k}-metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#c3cedf"/></linearGradient>
  <radialGradient id="{k}-aura" cx="50%" cy="55%" r="50%"><stop offset="0" stop-color="{a}" stop-opacity=".45"/><stop offset="1" stop-color="{a}" stop-opacity="0"/></radialGradient>
  <filter id="{k}-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<circle cx="102" cy="112" r="92" fill="url(#{k}-aura)"/>
<ellipse cx="100" cy="190" rx="46" ry="6" fill="#000000" opacity=".35"/>
{antenna}
{left_arm}
{right_arm}
<rect x="90" y="110" width="20" height="10" rx="3" fill="#8f9db3"/>
<rect x="64" y="116" width="72" height="60" rx="24" fill="url(#{k}-metal)"/>
<rect x="82" y="130" width="36" height="24" rx="9" fill="#0b1517"/>
<circle cx="93" cy="142" r="4" fill="{a}" filter="url(#{k}-glow)"/><rect x="101" y="139" width="12" height="6" rx="3" fill="{a}" opacity=".7"/>
<rect x="48" y="70" width="12" height="24" rx="5" fill="{d}"/><rect x="140" y="70" width="12" height="24" rx="5" fill="{d}"/>
<rect x="56" y="46" width="88" height="68" rx="26" fill="url(#{k}-metal)"/>
<rect x="66" y="60" width="68" height="38" rx="17" fill="#0b1517"/>
<ellipse cx="86" cy="78" rx="7" ry="8.5" fill="{a}" filter="url(#{k}-glow)"/>
<ellipse cx="114" cy="78" rx="7" ry="8.5" fill="{a}" filter="url(#{k}-glow)"/>
<path d="M92 90 q8 6 16 0" stroke="{a}" stroke-width="3" fill="none" stroke-linecap="round"/>
<rect x="70" y="50" width="30" height="6" rx="3" fill="#ffffff" opacity="{0 if hat else .7}"/>
{_prop(name, a, d)}
</svg>"""


ORDER = ["hunter", "builder", "sales", "delivery"]
