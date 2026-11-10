#!/usr/bin/env python3
"""Build the x402 swimlane family page (moitié): K0 plus the case sub-diagrams.

  python3 build_family.py            -> family.html + family.json (all boards, for verify_arrows.py)
  python3 build_family.py --only k0  -> k0.html + k0.json (K0 standalone, same drawing)
  python3 build_family.py --export   -> export/<board>.svg, .html, .png (PNG via headless Chrome, for the Google Doc)

Session 0 (2026-11-09): five lanes (Principal, Buyer, Agent, Seller, Facilitator); a case may merge two lanes
(e.g. principal into buyer for a solo developer); Slot B is the seller's disclosure profile; Slot C is the identifier
anchor with the identity link (4.2.1) a separate dashed step; Slot E is drawn. Old uc1-2/uc1-3 (Nicole's MSA and
flight cases) are now 1c/1d; uc1-2 and uc1-3 are the RFP's UC1.2 and UC1.3 (Nov 9 export).

Every board is K0's STEPS with lane names and slot texts overridden per case; a case may add steps.
"""
import json, html, sys, os, copy, re, subprocess, pathlib

OUT = os.path.dirname(os.path.abspath(__file__))
SPACING, X0, TOP = 170, 85, 54
ROLE_N = 28  # characters of role text that fit the 164px lane head
STYLE = "moitie" if "--style" in sys.argv and sys.argv[sys.argv.index("--style")+1] == "moitie" else "bare"
RX = 6 if STYLE == "bare" else 0

# The cases live one per file in ../use-cases/<id>.json so each use case has its own git history.
# k0.json also carries "steps": the shared spine every case overrides.
# lane = [key, name, role, wallet?]; step kind: msg (solid, protocol) · ident (dashed, mechanism open) · work · slot · region · note
UC_DIR = os.path.join(os.path.dirname(OUT), "use-cases")
def _load(cid):
    return json.load(open(os.path.join(UC_DIR, cid + ".json"), encoding="utf-8"))
ORDER = json.load(open(os.path.join(UC_DIR, "_order.json")))
K0 = _load("k0")
K0_STEPS = K0.pop("steps")
K0_LANES = K0["lanes"]
CASES = [_load(c) for c in ORDER if c != "k0"]

def esc(s):
    return html.escape(s, quote=True)

def wrap(text, n):
    out, cur = [], ""
    for wd in text.split(" "):
        if len(cur) + len(wd) + 1 > n and cur:
            out.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur: out.append(cur)
    return out

def steps_for(case):
    steps = copy.deepcopy(K0_STEPS)
    for sid, ov in case.get("overrides", {}).items():
        for st in steps:
            if st["id"] == sid:
                st.update(ov)
    for ins in case.get("insert", []):
        idx = [i for i, st in enumerate(steps) if st["id"] == ins["after"]][0]
        steps[idx+1:idx+1] = copy.deepcopy(ins["steps"])
    drop = set(case.get("drop", []))
    steps = [st for st in steps if st["id"] not in drop]
    merge = case.get("merge", {})
    if merge:
        for st in steps:
            for k in ("from", "to", "lane"):
                if k in st and st[k] in merge:
                    st[k] = merge[st[k]]
        out = []
        for st in steps:
            if st["kind"] in ("msg", "ident") and st["from"] == st["to"]:
                # a delegation step whose two ends are now one person: draw it as a lettered box on that lane
                st = {"id": st["id"], "kind": "slot" if st.get("slot") else "note", "lane": st["from"],
                      "slot": st.get("slot"), "label": st["label"], "sub": st.get("sub", "")}
            out.append(st)
        steps = out
    return steps

def render_board(bid, lanes, steps):
    keys = [l[0] for l in lanes]
    lane_x = lambda k: X0 + keys.index(k) * SPACING
    W = X0 + (len(lanes) - 1) * SPACING + 85
    # a role longer than the lane head wraps to a second line; the head and everything under it move down to fit
    roles = {l[0]: wrap(l[2], ROLE_N) for l in lanes}
    grow = 13 * (max(len(r) for r in roles.values()) - 1)
    top = TOP + grow
    y = top + 34
    parts = []
    regions = []
    for st in steps:
        k = st["kind"]
        for rg in regions:
            if rg["before"] == st.get("id") and "y1" not in rg:
                rg["y1"] = y - 14
                y += 10
        if k == "region":
            rg = dict(st); rg["y0"] = y - 6
            rx0 = lane_x("agent") - 92; rx1 = lane_x("seller") + 100
            rg["x0"], rg["x1"] = rx0, rx1
            lines = wrap(st["label"], 44) + [("sub", ln) for ln in wrap(st.get("sub", ""), 50)] if st.get("sub") else wrap(st["label"], 44)
            ty = y + 10
            parts.append(f'<rect x="{rx0 + 8}" y="{ty - 11}" width="14" height="14" rx="3" class="slotbox"/>')
            parts.append(f'<text x="{rx0 + 15}" y="{ty}" text-anchor="middle" class="slotl">{st["slot"]}</text>')
            for ln in lines:
                if isinstance(ln, tuple):
                    parts.append(f'<text x="{rx0 + 30}" y="{ty}" class="sub">{esc(ln[1])}</text>'); ty += 14
                else:
                    parts.append(f'<text x="{rx0 + 30}" y="{ty}" class="lbl">{esc(ln)}</text>'); ty += 15
            y = ty + 14
            regions.append(rg)
            continue
        if k in ("msg", "ident"):
            x1, x2 = lane_x(st["from"]), lane_x(st["to"])
            mid = (x1 + x2) / 2
            d = 1 if x2 > x1 else -1
            if st.get("slot"):
                parts.append(f'<rect x="{mid-7:.0f}" y="{y-11}" width="14" height="14" rx="3" class="slotbox"/>')
                parts.append(f'<text x="{mid:.0f}" y="{y}" text-anchor="middle" class="slotl">{st["slot"]}</text>')
                ty = y + 16
            else:
                ty = y
            lcls = "msg" if k == "msg" else "lbl"
            for ln in wrap(st["label"], 44):
                parts.append(f'<text x="{mid:.0f}" y="{ty}" text-anchor="middle" class="{lcls}">{esc(ln)}</text>')
                ty += 14
            ty -= 14
            if st.get("sub"):
                for ln in wrap(st["sub"], 44):
                    parts.append(f'<text x="{mid:.0f}" y="{ty+14}" text-anchor="middle" class="sub">{esc(ln)}</text>')
                    ty += 14
            ay = ty + 8
            cls = "a-msg" if k == "msg" else "a-ident"
            mk = f"{bid}-p" if k == "msg" else f"{bid}-i"
            parts.append(f'<path d="M{x1} {ay}H{x2 - d*4}" class="{cls}" marker-end="url(#{mk})"/>')
            y = ay + 34
        else:
            x = lane_x(st["lane"])
            w = SPACING + 20 if k == "slot" else SPACING - 10
            n_lbl, n_sub = (23, 22) if k == "slot" else (22, 23)
            wrapped = [(ln, "lbl") for ln in wrap(st["label"], n_lbl)]
            if st.get("sub"):
                wrapped += [(ln, "sub") for ln in wrap(st["sub"], n_sub)]
            h = 12 + 15 * len(wrapped) + 4
            if k == "slot":
                parts.append(f'<rect x="{x - w/2}" y="{y-10}" width="{w}" height="{h}" rx="{RX}" class="slot"/>')
                parts.append(f'<rect x="{x - w/2 + 8}" y="{y-3}" width="14" height="14" rx="3" class="slotbox"/>')
                parts.append(f'<text x="{x - w/2 + 15}" y="{y+8}" text-anchor="middle" class="slotl">{st["slot"]}</text>')
                tx, anchor = x - w/2 + 30, "start"
            elif k == "work":
                parts.append(f'<rect x="{x - w/2}" y="{y-10}" width="{w}" height="{h}" rx="{RX}" class="work"/>')
                tx, anchor = x, "middle"
            else:
                parts.append(f'<rect x="{x - w/2}" y="{y-10}" width="{w}" height="{h}" rx="{RX}" class="notebg"/>')
                tx, anchor = x, "middle"
            ty = y + 8
            for ln, cls in wrapped:
                parts.append(f'<text x="{tx}" y="{ty}" text-anchor="{anchor}" class="{cls}{" note" if k=="note" else ""}">{esc(ln)}</text>')
                ty += 15
            y = y - 10 + h + 22
    for rg in regions:
        rg.setdefault("y1", y)
    H = y + 6
    out = [f'<svg viewBox="-12 0 {W+12} {H}" style="--w:{W+12}px" role="img" aria-label="{esc(bid)} swimlane">']
    out.append(f'<defs><marker id="{bid}-p" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="h-msg"/></marker>'
               f'<marker id="{bid}-i" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="h-ident"/></marker></defs>')
    sx = lane_x("seller")
    out.append(f'<rect x="{sx-58}" y="0" width="116" height="{H}" class="tint"/>')
    out.append(f'<line x1="0" x2="{W}" y1="{top}" y2="{top}" class="counter"/>')
    for rg in regions:
        out.append(f'<rect x="{rg["x0"]}" y="{rg["y0"]}" width="{rg["x1"] - rg["x0"]}" height="{rg["y1"] - rg["y0"]}" rx="{RX}" class="region"/>')
    for lane in lanes:
        key, name, role = lane[0], lane[1], lane[2]
        wallet = len(lane) > 3 and lane[3]
        x = lane_x(key)
        out.append(f'<line x1="{x}" x2="{x}" y1="{top+8}" y2="{H-14}" class="life"/>')
        if wallet:
            out.append(f'<rect x="{x-27}" y="{top+6}" width="54" height="15" rx="7.5" class="wallet"/>')
            out.append(f'<text x="{x}" y="{top+17}" text-anchor="middle" class="walletl">wallet</text>')
        if STYLE == "bare":
            out.append(f'<rect x="{x-82}" y="6" width="164" height="{46 + grow}" rx="{RX}" class="lanebox"/>')
            out.append(f'<text x="{x}" y="26" text-anchor="middle" class="lane">{esc(name)}</text>')
            for i, ln in enumerate(roles[key]):
                out.append(f'<text x="{x}" y="{42 + 13*i}" text-anchor="middle" class="role">{esc(ln)}</text>')
        else:
            out.append(f'<text x="{x}" y="22" text-anchor="middle" class="lane">{esc(name)}</text>')
            out.append(f'<text x="{x}" y="39" text-anchor="middle" class="role serif">{esc(role)}</text>')
    out.extend(parts)
    out.append('</svg>')
    return "\n".join(out)

def checker_steps(steps):
    out = []
    for st in steps:
        if st["kind"] in ("msg", "ident"):
            out.append({"from": st["from"], "to": st["to"], "label": (st.get("slot", "") + " " + st["label"]).strip(), "dashed": 1 if st["kind"] == "ident" else 0})
        else:
            out.append({"self": st.get("lane", "seller"), "label": st["label"]})
    return out

def section(case):
    steps = steps_for(case)
    svg = render_board(case["id"], case["lanes"], steps)
    slot_html = "".join(f'<div class="frow"><dt><span class="sl">{a}</span> {esc(t)}</dt><dd>{esc(d)}</dd></div>' for a, t, d in case["slots"] if a in ("A", "B", "C", "E", "F"))
    foot_html = "".join(f'<div class="frow"><dt>{esc(a)}</dt><dd>{d}</dd></div>' for a, d in case["footer"])
    unrev = '<p class="instance warn">Unreviewed by the WG: Nicole will share this case for async feedback.</p>' if case.get("unreviewed") else ''
    differs = f'<p class="instance">{esc(case["differs"])}</p>' if case.get("differs") else ''
    return f'''<section class="uc" id="{case["id"]}" aria-labelledby="{case["id"]}-h">
<header class="uc-head"><p class="uc-no">{esc(case["no"])}</p>
<h2 id="{case["id"]}-h">{esc(case["title"])}</h2>
<p class="instance">{case["instance"]}</p>{unrev}{differs}
</header>
<div class="split">
<div class="board" tabindex="0" aria-label="{esc(case["no"])} swimlane, scrolls sideways on small screens">{svg}</div>
<aside class="side" aria-label="Legend and slots">
<div class="legend" aria-label="Legend"><span>Legend</span><span><svg viewBox="0 0 30 14" aria-hidden="true"><rect x="1" y="1" width="28" height="12" rx="3" class="slot"/></svg>identity slot</span><span><svg viewBox="0 0 30 14" aria-hidden="true"><rect x="1" y="1" width="28" height="12" rx="3" class="work"/></svg>local work</span><span><svg viewBox="0 0 30 14" aria-hidden="true"><path d="M0 7H30" class="a-msg"/></svg>protocol message</span><span><svg viewBox="0 0 30 14" aria-hidden="true"><path d="M0 7H30" class="a-ident"/></svg>identity step</span></div>
<dl class="sheet slots">{slot_html}</dl>
</aside>
</div>
<h3 class="eyebrow">Today · Fills it with · Still open</h3>
<dl class="sheet">{foot_html}</dl>
</section>'''

KEY_HTML = '''<div class="front">
  <aside class="keys">
    <h3>Key</h3>
    <ul class="key">
      <li><svg viewBox="0 0 34 10" aria-hidden="true"><defs><marker id="kp" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="h-msg"/></marker></defs><path d="M1 5H28" class="a-msg" marker-end="url(#kp)"/></svg>protocol message, M1 to M8 (whitelisted)</li>
      <li><svg viewBox="0 0 34 10" aria-hidden="true"><defs><marker id="ki" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="h-ident"/></marker></defs><path d="M1 5H28" class="a-ident" marker-end="url(#ki)"/></svg>identity step, mechanism open</li>
      <li><svg viewBox="0 0 34 18" aria-hidden="true"><rect x="2" y="2" width="30" height="14" rx="3" class="slot"/><rect x="6" y="5" width="8" height="8" rx="2" class="slotbox"/></svg>lettered slot, A to F</li>
      <li><svg viewBox="0 0 34 18" aria-hidden="true"><rect x="3" y="2" width="28" height="14" rx="7" class="wallet"/></svg>lane that may hold a wallet</li>
      <li><svg viewBox="0 0 34 18" aria-hidden="true"><rect x="2" y="2" width="30" height="14" rx="3" class="work"/></svg>local work, not a message</li>
    </ul>
  </aside>
  <div class="keys">
    <h3>Messages</h3>
    <ol class="stages">
<li><span class="st-k">M1</span><span>request <em>(optional)</em></span></li>
<li><span class="st-k">M2</span><span>402 + PAYMENT-REQUIRED</span></li>
<li><span class="st-k">M3</span><span>PAYMENT-SIGNATURE (payment payload)</span></li>
<li><span class="st-k">M4</span><span>POST /verify <em>(optional)</em></span></li>
<li><span class="st-k">M5</span><span>VerifyResponse</span></li>
<li><span class="st-k">M6</span><span>POST /settle</span></li>
<li><span class="st-k">M7</span><span>SettlementResponse</span></li>
<li><span class="st-k">M8</span><span>200 + PAYMENT-RESPONSE</span></li>
    </ol>
  </div>
</div>'''

def page(boards, family):
    css = open(os.path.join(OUT, f"{STYLE}.css"), encoding="utf-8").read()
    if family:
        title = "x402 Swimlane Family"
        h1 = "K0 and its cases"
        count = f"1 key diagram · {len(boards)-1} cases · 5 lanes · x402 v2 header names"
        topline = "Every board is the key diagram with the lanes renamed and the slots filled for one case. Solid arrows are the eight messages the x402 specification defines; dashed lines and boxes are identity slots whose mechanism the working group has not decided. Lane names follow the RFP actor list pending the glossary; the wallet mark shows which lanes may hold one."
        def ix(b):
            cls = ' class="unrev"' if b.get("unreviewed") else ""
            tag = "unreviewed" if b.get("unreviewed") else ""
            return f'<li><a href="#{b["id"]}"{cls}><span class="ix-uc">{esc(b["no"])}</span><span class="ix-name">{esc(b["title"])}</span><span class="ix-n">{tag}</span></a></li>'
        index = '<nav aria-label="Boards"><ol class="index">' + "".join(ix(b) for b in boards) + '</ol></nav>'
        eyebrow = "x402 Identity WG · swimlane family · session 0 draft"
    else:
        title = "x402 K0 Key Diagram"
        h1 = "K0: the x402 spine with three identity slots"
        count = "5 lanes · 8 protocol messages · 4 drawn identity slots · x402 v2 header names"
        topline = "Solid arrows are the eight messages the x402 specification defines. Dashed lines and boxes are identity slots whose mechanism the working group has not decided. Nothing in the protocol touches the Principal or Buyer lanes; the Agent is the x402 client."
        index = ""
        eyebrow = "x402 Identity WG · key diagram · session 0 draft"
    body = "\n".join(section(b) for b in boards)
    style_line = 'bare styling after Rob\u2019s reference diagrams' if STYLE == 'bare' else 'moiti\u00e9 \u00b7 placeholder palette and type'
    fonts = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif&display=swap">' if STYLE == "bare" else ''
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
{fonts}
<style>
{css}
</style>
</head>
<body>
<main class="page">
<header class="mast">
  <p class="eyebrow">{eyebrow}</p>
  <h1>{h1}</h1>
  <p class="count">{count}</p>
  <p class="topline">{topline}</p>
</header>
{index}
{KEY_HTML}
{body}
<section class="uc" aria-label="Method">
<header class="uc-head"><p class="uc-no">Method</p><h2>How these were drawn</h2></header>
<p class="prose">Session 0 draft, 2026-11-09. Protocol messages and header names come from the x402 v2 specification (reference sheet, 23 sources); slot placements come from the Oct 13 meeting; the Oct 27 feedback is applied throughout: five lanes with the Buyer (a person) separated from the Agent (the x402 client), wallet marks on both, Slot B as the seller’s configurable disclosure profile, Slot C as an identifier anchor with the identity link (RFP 4.2.1) a separate dashed step, and a gloss on delegation in Slot A. Lane names follow the RFP actor list; the official glossary has not yet been checked (see <code>analysis/13-provisional-glossary.md</code>). 1c and 1d carry Nicole’s page forward and are unreviewed; UC1.2 and UC1.3 are skeletons from the Nov 9 RFP export. Every board is generated from one step list by <code>build_family.py</code>, and every arrow passed <code>verify_arrows.py</code>: a solid arrow is always one of M1 to M8, in the spec’s direction; anything touching the Principal or Buyer lane is dashed.</p>
</section>
<footer class="colophon">
  <p>{style_line} · x402 Identity WG · {title}, 2026-11-09</p>
</footer>
</main>
</body>
</html>
'''

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def export_boards(boards):
    """Write export/<id>.svg (standalone, CSS inlined), export/<id>.html (one board on the page palette) and
    export/<id>.png (2x, headless Chrome). The PNGs are what goes into the RFP Google Doc for comments."""
    exp = os.path.join(OUT, "export"); os.makedirs(exp, exist_ok=True)
    css = open(os.path.join(OUT, f"{STYLE}.css"), encoding="utf-8").read()
    svg_css = "\n".join(ln for ln in css.splitlines() if ln.startswith((":root", "svg ", ".lanebox", ".counter", ".life", ".a-", ".h-", ".tint", ".notebg", ".work", ".region", ".slot", ".wallet")))
    fonts = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif&display=swap">' if STYLE == "bare" else ""
    written = []
    for b in boards:
        svg = render_board(b["id"], b["lanes"], steps_for(b))
        m = re.search(r'viewBox="-12 0 (\d+) (\d+)"', svg)
        w, h = int(m.group(1)) + 12, int(m.group(2))
        standalone = svg.replace(">", f' xmlns="http://www.w3.org/2000/svg"><style>{svg_css}</style>', 1)
        open(os.path.join(exp, f"{b['id']}.svg"), "w", encoding="utf-8").write(standalone)
        doc = (f'<!doctype html><meta charset="utf-8"><title>{esc(b["no"])} {esc(b["title"])}</title>{fonts}<style>{css}\n'
               f'html,body{{margin:0;background:var(--bg)}} .one{{padding:16px}} .one svg{{display:block;width:{w}px;height:{h}px}}</style>'
               f'<div class="one">{svg}</div>')
        hpath = os.path.join(exp, f"{b['id']}.html")
        open(hpath, "w", encoding="utf-8").write(doc)
        ppath = os.path.join(exp, f"{b['id']}.png")
        if os.path.exists(CHROME):
            r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                                f"--window-size={w+32},{h+32}", f"--screenshot={ppath}", pathlib.Path(hpath).as_uri()],
                               capture_output=True, text=True, timeout=90)
            ok = os.path.exists(ppath) and os.path.getsize(ppath) > 0
            written.append((b["id"], w, h, "png" if ok else f"png FAILED: {r.stderr.strip()[-200:]}"))
        else:
            written.append((b["id"], w, h, "png skipped: Chrome not found"))
    for row in written:
        print("export", *row)

if __name__ == "__main__":
    only_k0 = "--only" in sys.argv and "k0" in sys.argv
    boards = [K0] if only_k0 else [K0] + CASES
    name = "k0" if only_k0 else "family"
    if "--export" in sys.argv:
        export_boards(boards)
    json.dump({b["id"]: {"lanes": b["lanes"], "steps": checker_steps(steps_for(b))} for b in boards},
              open(os.path.join(OUT, f"{name}.json"), "w"), indent=1)
    open(os.path.join(OUT, f"{name}.html"), "w", encoding="utf-8").write(page(boards, not only_k0))
    print("wrote", name, len(boards), "boards")
