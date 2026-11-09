"""Look and feel of the StoryDNA site: one CSS block + small HTML helpers.

TO RE-BRAND: change the colour variables in the first :root block of CSS (and primaryColor in .streamlit/config.toml).
The palette is a dark, cinematic, warm-orange style typical of short-drama apps. It is INSPIRED by that genre, not copied
from Kuku's brand book (I could not read it), and no Kuku logo or trademark is used.
"""
from __future__ import annotations

import html

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root{
  --bg:#0E0A15; --surface:#171120; --surface2:#1F1829; --line:rgba(255,255,255,.09); --line2:rgba(255,255,255,.16);
  --text:#F6F2FB; --muted:#A99FBA; --faint:#7C7290;
  --accent:#FF7A1A; --accent2:#FF3D77; --glow:rgba(255,122,26,.18);
  --high:#FF5468; --med:#FFB020; --low:#2FD39B; --na:#8C86A0; --radius:18px;
}
html, body, [class*="css"], .stApp {font-family:'Plus Jakarta Sans',-apple-system,'Segoe UI',Roboto,sans-serif !important;}
.stApp{background:radial-gradient(1100px 520px at 12% -8%, rgba(255,122,26,.16), transparent 60%),
       radial-gradient(900px 480px at 100% 0%, rgba(255,61,119,.13), transparent 55%), var(--bg);color:var(--text);}
header[data-testid="stHeader"]{background:transparent;}
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"]{visibility:hidden;display:none;}
.block-container{max-width:1180px;padding-top:1.2rem;padding-bottom:4rem;}
h1,h2,h3,h4{letter-spacing:-.01em;}

/* top bar + hero */
.topbar{display:flex;align-items:center;justify-content:space-between;padding:.4rem 0 1.1rem;}
.brand{display:flex;align-items:center;gap:.65rem;font-weight:800;font-size:1.25rem;letter-spacing:-.02em;}
.logo{width:34px;height:34px;border-radius:11px;background:linear-gradient(135deg,var(--accent),var(--accent2));display:grid;place-items:center;
      box-shadow:0 8px 24px var(--glow);font-size:1.05rem;}
.brand small{display:block;font-weight:500;font-size:.72rem;color:var(--muted);letter-spacing:0;margin-top:-2px;}
.tag{border:1px solid var(--line2);color:var(--muted);padding:.28rem .7rem;border-radius:999px;font-size:.74rem;font-weight:600;}
.hero{padding:1.2rem 0 1.6rem;}
.hero h1{font-size:2.55rem;line-height:1.1;font-weight:800;margin:.2rem 0 .7rem;}
.grad{background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;background-clip:text;color:transparent;}
.hero p{color:var(--muted);font-size:1.05rem;max-width:760px;line-height:1.6;margin:0 0 1rem;}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;}
.chip{background:var(--surface);border:1px solid var(--line);color:var(--text);padding:.38rem .8rem;border-radius:999px;font-size:.8rem;font-weight:600;}
.chip b{color:var(--accent);}

/* cards */
.card{background:linear-gradient(180deg,var(--surface),var(--surface2));border:1px solid var(--line);border-radius:var(--radius);padding:1.15rem 1.25rem;}
.card h4{margin:0 0 .35rem;font-size:1rem;}
.muted{color:var(--muted);font-size:.88rem;line-height:1.55;}
.steps{display:grid;gap:.7rem;margin-top:.6rem;}
.step{display:flex;gap:.75rem;align-items:flex-start;}
.num{min-width:26px;height:26px;border-radius:50%;background:var(--glow);color:var(--accent);display:grid;place-items:center;font-weight:800;font-size:.8rem;border:1px solid rgba(255,122,26,.35);}
.step span{font-size:.88rem;color:var(--muted);line-height:1.5;}.step b{color:var(--text);}

/* verdict */
.verdict{display:grid;grid-template-columns:1.5fr 1fr;gap:1.4rem;align-items:center;border-radius:22px;padding:1.5rem 1.6rem;border:1px solid var(--line2);
         background:linear-gradient(135deg,rgba(255,122,26,.10),rgba(255,61,119,.07)),var(--surface);margin:.5rem 0 1rem;}
.verdict .eyebrow{font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);font-weight:700;}
.verdict h2{font-size:1.65rem;margin:.25rem 0 .5rem;font-weight:800;}
.verdict p{margin:.4rem 0 0;color:var(--muted);line-height:1.55;font-size:.95rem;}
.big{font-size:3rem;font-weight:800;line-height:1;}
.big small{font-size:.9rem;color:var(--muted);font-weight:600;margin-left:.3rem;}
@media (max-width:820px){.verdict{grid-template-columns:1fr;}.hero h1{font-size:1.9rem;}}

/* pills + gauge */
.pill{display:inline-flex;align-items:center;gap:.4rem;padding:.28rem .72rem;border-radius:999px;font-size:.78rem;font-weight:800;letter-spacing:.02em;border:1px solid;}
.pill-high{color:var(--high);background:rgba(255,84,104,.12);border-color:rgba(255,84,104,.45);}
.pill-medium{color:var(--med);background:rgba(255,176,32,.12);border-color:rgba(255,176,32,.45);}
.pill-low{color:var(--low);background:rgba(47,211,155,.10);border-color:rgba(47,211,155,.4);}
.pill-na{color:var(--na);background:rgba(140,134,160,.12);border-color:rgba(140,134,160,.4);}
.gauge{position:relative;height:10px;border-radius:999px;background:rgba(255,255,255,.08);margin:.9rem 0 .35rem;overflow:visible;}
.gauge i{position:absolute;left:0;top:0;bottom:0;border-radius:999px;background:linear-gradient(90deg,var(--low),var(--med) 55%,var(--high));}
.gauge u{position:absolute;top:-4px;width:2px;height:18px;background:rgba(255,255,255,.55);border-radius:2px;text-decoration:none;}
.gl{display:flex;justify-content:space-between;font-size:.7rem;color:var(--faint);font-weight:600;}

/* kpis */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem;margin-bottom:1.2rem;}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:.8rem 1rem;}
.kpi .v{font-size:1.35rem;font-weight:800;}.kpi .l{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;font-weight:700;}
@media (max-width:820px){.kpis{grid-template-columns:repeat(2,1fr);}}

/* section titles */
.sec{display:flex;align-items:baseline;justify-content:space-between;margin:1.6rem 0 .6rem;}
.sec h3{margin:0;font-size:1.2rem;font-weight:800;}.sec span{color:var(--muted);font-size:.82rem;}

/* evidence */
.ev{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin:.55rem 0;}
.ev .side{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:.8rem .95rem;font-size:.9rem;line-height:1.55;}
.ev .side small{display:block;text-transform:uppercase;letter-spacing:.1em;font-size:.66rem;color:var(--muted);font-weight:800;margin-bottom:.25rem;}
.ev .pitch{border-left:3px solid var(--accent);}.ev .cat{border-left:3px solid var(--accent2);}
.ev .orig{color:var(--muted);font-size:.8rem;margin-top:.35rem;}
.tags{display:flex;flex-wrap:wrap;gap:.35rem;margin:.9rem 0 .2rem;}
.tag-d,.tag-t{padding:.18rem .6rem;border-radius:8px;font-size:.72rem;font-weight:700;}
.tag-d{background:rgba(255,84,104,.13);color:#FF8896;border:1px solid rgba(255,84,104,.35);}
.tag-t{background:rgba(255,255,255,.05);color:var(--muted);border:1px solid var(--line);}
.diff{background:var(--surface);border:1px dashed var(--line2);border-radius:12px;padding:.55rem .85rem;margin:.35rem 0;font-size:.86rem;color:var(--muted);}
.diff b{color:var(--text);}
@media (max-width:820px){.ev{grid-template-columns:1fr;}}

/* improve panel */
.imp{border:1px solid rgba(255,122,26,.35);background:linear-gradient(135deg,rgba(255,122,26,.09),rgba(255,61,119,.05));border-radius:18px;padding:1.1rem 1.25rem;margin-bottom:1rem;}
.imp h4{margin:0 0 .3rem;font-size:1.05rem;}
.flow{display:flex;align-items:center;gap:.8rem;flex-wrap:wrap;margin:.7rem 0 .2rem;}
.flow .box{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:.55rem .9rem;text-align:center;min-width:118px;}
.flow .box .n{font-size:1.4rem;font-weight:800;}.flow .box .l{font-size:.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;font-weight:700;}
.arrow{color:var(--accent);font-size:1.5rem;font-weight:800;}
.fix{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:.85rem 1rem;margin:.6rem 0;}
.fix .top{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;}
.fix .q{font-size:.88rem;color:var(--text);line-height:1.5;}.fix .m{font-size:.8rem;color:var(--muted);margin-top:.2rem;}
.drop{white-space:nowrap;color:var(--low);font-weight:800;font-size:.8rem;background:rgba(47,211,155,.1);border:1px solid rgba(47,211,155,.35);border-radius:999px;padding:.2rem .6rem;}
.idea{margin-top:.55rem;padding:.6rem .8rem;background:rgba(255,122,26,.07);border-left:3px solid var(--accent);border-radius:8px;font-size:.88rem;line-height:1.55;}
.idea small{color:var(--accent);font-weight:800;text-transform:uppercase;letter-spacing:.08em;font-size:.64rem;display:block;margin-bottom:.1rem;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.8rem;margin-top:.6rem;}
.angle{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:.85rem 1rem;}
.angle h5{margin:0 0 .3rem;font-size:.9rem;color:var(--accent);font-weight:800;}.angle p{margin:0;font-size:.86rem;line-height:1.55;color:var(--muted);}
.fine{font-size:.74rem;color:var(--faint);margin-top:.8rem;line-height:1.5;}

/* warnings */
.note{border-radius:12px;padding:.7rem .95rem;font-size:.86rem;line-height:1.5;margin:.45rem 0;border:1px solid;}
.note-info{background:rgba(255,176,32,.08);border-color:rgba(255,176,32,.35);color:#FFD27A;}
.note-bad{background:rgba(255,84,104,.09);border-color:rgba(255,84,104,.4);color:#FF9AA6;}
.note-ok{background:rgba(47,211,155,.08);border-color:rgba(47,211,155,.35);color:#7DE8C2;}

/* streamlit widgets */
section[data-testid="stSidebar"]{background:#120C1B;border-right:1px solid var(--line);}
section[data-testid="stSidebar"] h2,section[data-testid="stSidebar"] h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);}
.stTextArea textarea{background:var(--surface) !important;border:1px solid var(--line2) !important;border-radius:14px !important;color:var(--text) !important;font-size:.95rem;line-height:1.6;}
.stTextArea textarea:focus{border-color:var(--accent) !important;box-shadow:0 0 0 3px var(--glow) !important;}
div[data-baseweb="select"] > div{background:var(--surface) !important;border-color:var(--line2) !important;border-radius:12px !important;}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"]{background:linear-gradient(90deg,var(--accent),var(--accent2));border:0;color:#fff;font-weight:800;border-radius:12px;padding:.6rem 1.4rem;
      box-shadow:0 10px 28px var(--glow);}
.stButton > button[kind="primary"]:hover{filter:brightness(1.08);transform:translateY(-1px);}
.stButton > button, .stDownloadButton > button{border-radius:12px;border:1px solid var(--line2);font-weight:700;}
div[data-testid="stExpander"]{background:var(--surface);border:1px solid var(--line) !important;border-radius:16px !important;margin-bottom:.7rem;}
div[data-testid="stExpander"] summary{font-weight:700;padding:.35rem .4rem;}
button[data-baseweb="tab"]{font-weight:700;}
div[data-baseweb="tab-highlight"]{background:var(--accent) !important;}
div[data-testid="stRadio"] label p{font-size:.88rem;}
</style>
"""

TIERS = {
    "High": ("pill-high", "●", "Likely the same story"),
    "Medium": ("pill-medium", "◐", "Partial overlap"),
    "Low": ("pill-low", "○", "Looks different"),
    "Not assessed": ("pill-na", "–", "Not assessed"),
}
NEXT_STEP = {
    "High": "Pause before greenlighting. Compare the full outlines, and use the ideas below to steer the pitch toward its own story.",
    "Medium": "Some beats repeat. A few targeted changes (see the ideas below) should make the pitch clearly its own.",
    "Low": "Nothing in the catalogue follows the same chain of events. Still a human call, but no overlap worth flagging.",
    "Not assessed": "The pitch language is not supported without a model, so no comparison was made.",
}


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def pill(tier: str) -> str:
    cls, dot, _ = TIERS.get(tier, TIERS["Not assessed"])
    return '<span class="pill %s">%s %s</span>' % (cls, dot, esc(tier))


def gauge(score: float, tiers: dict | None = None) -> str:
    t = tiers or {"medium": 0.3, "high": 0.8}
    s = max(0.0, min(1.0, float(score)))
    return ('<div class="gauge"><i style="width:%.1f%%"></i><u style="left:%.1f%%"></u><u style="left:%.1f%%"></u></div>'
            '<div class="gl"><span>0</span><span>Medium %.2f</span><span>High %.2f</span><span>1</span></div>'
            % (s * 100, t["medium"] * 100, t["high"] * 100, t["medium"], t["high"]))


def topbar() -> str:
    return ('<div class="topbar"><div class="brand"><div class="logo">&#127916;</div><div>StoryDNA<small>Story redundancy review</small></div></div>'
            '<span class="tag">Prototype &middot; AI Generalist assignment &middot; not an official Kuku product</span></div>')


def hero() -> str:
    return ('<div class="hero"><h1>Is this pitch a <span class="grad">new story</span>, or one we have already told?</h1>'
            '<p>Paste a microdrama pitch. StoryDNA checks it against your catalogue, separates a <b>repeated plot</b> from a harmless '
            '<b>repeated trope</b>, shows the evidence beat by beat, and suggests ways to make the pitch more original.</p>'
            '<div class="chips"><span class="chip"><b>&#10003;</b> Plot vs trope</span><span class="chip"><b>&#10003;</b> Evidence you can read</span>'
            '<span class="chip"><b>&#10003;</b> Fresh-angle ideas</span><span class="chip"><b>&#10003;</b> English, Hindi &amp; Hinglish</span></div></div>')


def how_it_works(n_stories: int, cat_name: str) -> str:
    return ('<div class="card"><h4>How it works</h4><div class="steps">'
            '<div class="step"><div class="num">1</div><span><b>Paste a pitch</b> of 4 to 12 event sentences, or pick a sample.</span></div>'
            '<div class="step"><div class="num">2</div><span><b>Compare.</b> Every sentence is tagged with story events and matched in order against each catalogue story.</span></div>'
            '<div class="step"><div class="num">3</div><span><b>Read the evidence</b> and the &ldquo;make it more original&rdquo; ideas, then record your decision.</span></div></div>'
            '<div class="fine"><b style="color:var(--text)">%d stories</b> loaded &middot; %s</div></div>' % (n_stories, esc(cat_name)))


def verdict(c: dict, rep: dict) -> str:
    tier = c["review_priority"]
    sc = c["retrieval_score"]
    tiers = rep["config"]["tiers"]
    shared = c["shared_distinctive_events"]
    why = ("Shared distinctive events: <b>%s</b>." % esc(", ".join(e.replace("_", " ").title() for e in shared))) if shared else "No distinctive shared events."
    return ('<div class="verdict"><div><div class="eyebrow">Closest story in the catalogue</div><h2>%s</h2>%s'
            '<p>%s %s</p></div><div><div class="big">%.2f<small>review score</small></div>%s</div></div>'
            % (esc(c["candidate_title"]), pill(tier), why, esc(NEXT_STEP.get(tier, "")), sc, gauge(sc, tiers)))


def kpis(rep: dict, ms: float | None) -> str:
    lg = rep.get("language", {})
    route = {"none": "English", "glossary": "Hindi glossary", "llm": "Model translation", "unsupported": "Unsupported"}.get(lg.get("method"), "English")
    cells = [(str(rep["catalogue"]["n_cards"]), "Stories compared"), (str(rep["input_beats"]), "Beats in your pitch"),
             (route, "Language route"), ("%d ms" % ms if ms is not None else "-", "Time to compare")]
    return '<div class="kpis">%s</div>' % "".join('<div class="kpi"><div class="v">%s</div><div class="l">%s</div></div>' % (esc(v), esc(l)) for v, l in cells)


def section(title: str, sub: str = "") -> str:
    return '<div class="sec"><h3>%s</h3><span>%s</span></div>' % (esc(title), esc(sub))


def note(text: str, kind: str = "info") -> str:
    return '<div class="note note-%s">%s</div>' % (kind, esc(text))


def tags(c: dict) -> str:
    d = "".join('<span class="tag-d">%s</span>' % esc(e.replace("_", " ").title()) for e in c["shared_distinctive_events"])
    t = "".join('<span class="tag-t">%s</span>' % esc(e.replace("_", " ").title()) for e in c["shared_generic_tropes"])
    if not (d or t):
        return ""
    return '<div class="tags">%s%s</div><div class="fine" style="margin-top:0">Red = distinctive shared events &middot; grey = generic tropes (not a concern on their own)</div>' % (d, t)


def evidence(m: dict, cand_title: str) -> str:
    kind = ("<span class='tag-t'>trope only</span>" if m["generic_trope_only"] else
            "".join("<span class='tag-d'>%s</span>" % esc(e.replace("_", " ").title()) for e in m["events"]))
    pt = esc(m.get("pitch_text_original") or m["pitch_text"])
    ct = esc(m.get("candidate_text_original") or m["candidate_text"])
    eng = ("<div class='orig'>English used for matching: %s</div>" % esc(m["pitch_text"])) if m.get("pitch_text_original") else ""
    head = ("<div class='tags' style='margin:.9rem 0 0'>%s</div>" % kind) if kind else ""
    return ('%s<div class="ev"><div class="side pitch"><small>Your pitch</small>%s%s</div>'
            '<div class="side cat"><small>%s</small>%s</div></div>' % (head, pt, eng, esc(cand_title), ct))


def differing(c: dict) -> str:
    return "".join('<div class="diff"><b>%s:</b> %s</div>' % ("Only in your pitch" if d["side"] == "pitch" else "Only in the existing story", esc(d["text"]))
                   for d in c["differentiating_beats"])


def improve(df: dict) -> str:
    out = ['<div class="imp"><h4>How to make this pitch more original</h4><div class="muted">%s</div>' % esc(df["headline"])]
    pv = df.get("rewrite_preview") or {}
    if pv.get("after"):
        b, a = pv["before"], pv["after"]
        ids = pv["beats_to_rewrite"]
        label = "If beat%s %s %s rewritten" % ("s" if len(ids) > 1 else "", ", ".join(str(i + 1) for i in ids), "are" if len(ids) > 1 else "is")
        out.append('<div class="flow"><div class="box"><div class="n">%.2f</div><div class="l">Now</div>%s</div><div class="arrow">&rarr;</div>'
                   '<div class="box"><div class="n">%.2f</div><div class="l">%s</div>%s</div></div>'
                   % (b["score"], pill(b["tier"]), a["score"], esc(label), pill(a["tier"])))
        cl = pv["closest_after"]
        out.append('<div class="fine">What-if estimate from the scorer with those beats removed; closest story afterwards: <b>%s</b> (%s, %.2f). '
                   'Replacement beats can add new overlap, so run the rewrite through StoryDNA again.</div>' % (esc(cl["title"]), esc(cl["tier"]), cl["score"]))
    elif pv.get("note"):
        out.append('<div class="fine">%s</div>' % esc(pv["note"]))
    out.append("</div>")
    for f in df["beat_fixes"]:
        drop = ('<span class="drop">&minus;%.2f if rewritten</span>' % f["score_drop_if_rewritten"]) if f.get("score_drop_if_rewritten") else ""
        ideas = "".join('<div class="idea"><small>Idea%s</small>%s</div>' % ((" &middot; " + esc(i["event"].replace("_", " ").title())) if i["event"] else "", esc(i["idea"])) for i in f["ideas"])
        out.append('<div class="fix"><div class="top"><div><div class="q"><b>Beat %d:</b> %s</div><div class="m">Mirrors: %s</div></div>%s</div>%s</div>'
                   % (f["pitch_beat_index"] + 1, esc(f.get("pitch_text_original") or f["pitch_text"]), esc(f["mirrors"]), drop, ideas))
    out.append('<div class="sec" style="margin-top:1.1rem"><h3 style="font-size:1rem">Bigger levers to try</h3><span>pick one or two</span></div><div class="grid">')
    for a in df["angles"]:
        out.append('<div class="angle"><h5>%s</h5><p>%s</p></div>' % (esc(a["title"]), esc(a["idea"])))
    out.append("</div>")
    mi = df.get("model_ideas")
    if mi:
        if mi.get("status") == "ok":
            out.append('<div class="sec" style="margin-top:1.1rem"><h3 style="font-size:1rem">Fresh angles from the model</h3><span>validated, not copied from the existing story</span></div><div class="grid">')
            for i in mi["ideas"]:
                beats = ("Rewrites beat %s" % ", ".join(str(b + 1) for b in i["changes_beats"])) if i["changes_beats"] else ""
                out.append('<div class="angle"><h5>%s</h5><p>%s</p><p style="margin-top:.4rem;color:var(--faint)">%s</p></div>' % (esc(beats or "Idea"), esc(i["idea"]), esc(i["why_less_similar"])))
            out.append("</div>")
        else:
            out.append(note("The model could not produce usable ideas (%s). The built-in ideas above are unaffected." % mi.get("error", "unknown error"), "info"))
    out.append('<div class="fine">%s</div>' % esc(df["disclaimer"]))
    return "".join(out)


def footer() -> str:
    return ('<div class="fine" style="margin-top:2.5rem;border-top:1px solid var(--line);padding-top:1rem">'
            'StoryDNA gives an <b>editorial review priority</b>, not a probability of copying and not a legal finding. Ideas and genre tropes are not protectable; a human decides. '
            'The bundled catalogue is 30 original story cards written by an AI assistant for this assignment, not real shows. Unofficial prototype: no Kuku logo, data or trademark is used.</div>')
