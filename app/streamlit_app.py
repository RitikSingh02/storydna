"""StoryDNA review UI.  Run:  streamlit run app/streamlit_app.py"""
import hashlib
import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from storydna.catalogue import InputError, load_catalogue, parse_catalogue  # noqa: E402
from storydna.llm import AdapterError, adapter_from_env  # noqa: E402
from storydna.matcher import StoryIndex  # noqa: E402
from storydna.report import CAVEAT, report_to_csv, review_pitch  # noqa: E402
from storydna.translate import prepare_catalogue  # noqa: E402

st.set_page_config(page_title="StoryDNA - redundancy review", layout="wide")

# --- StoryDNA cinematic interface. Presentation-only; inference code is unchanged. ---
import streamlit.components.v1 as components

st.markdown(r"""
<style>
:root { --sd-red:#ff344f; --sd-pink:#ff647a; --sd-bg:#0d0e12; --sd-panel:#191b23; --sd-line:rgba(255,255,255,.11); }
html, body, [data-testid="stAppViewContainer"] { background:#0d0e12 !important; }
[data-testid="stAppViewContainer"] {
 background: radial-gradient(ellipse 65% 32% at 78% -8%, rgba(250,48,78,.19), transparent 72%),
             radial-gradient(ellipse 45% 38% at 15% 99%, rgba(180,35,66,.08), transparent 80%), #0d0e12 !important;
}
[data-testid="stSidebar"] { background:linear-gradient(175deg,#17191f,#1d1a22 80%,#251921) !important; border-right:1px solid rgba(255,69,98,.13); }
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 { letter-spacing:.02em; }
.block-container { max-width:1250px; padding-top:2.4rem !important; padding-bottom:4rem !important; }
/* Polished header and section spacing */
.sd-hero { position:relative; overflow:hidden; padding:2.3rem 2.35rem 2.2rem; border:1px solid rgba(255,92,113,.22); border-radius:24px;
 background:linear-gradient(115deg,rgba(251,49,79,.16) 0%,rgba(28,27,35,.97) 52%,rgba(19,20,26,.98) 100%);
 box-shadow:0 22px 65px rgba(0,0,0,.24); margin:0 0 1.4rem; isolation:isolate; }
.sd-hero:before {content:"";position:absolute;width:390px;height:390px;right:-170px;top:-220px;pointer-events:none;border-radius:50%;background:radial-gradient(circle,rgba(255,56,90,.28),transparent 70%);}
.sd-eyebrow {display:flex;align-items:center;gap:9px;color:#ff7183;font-size:.72rem;letter-spacing:.19em;text-transform:uppercase;font-weight:800;margin-bottom:17px;}
.sd-dot {width:7px;height:7px;border-radius:50%;background:#ff435e;box-shadow:0 0 15px #ff435e;}
.sd-hero h1 {font-size:clamp(2rem,4vw,3.4rem);line-height:1.08;font-weight:790;letter-spacing:-.055em;color:#f8f7fb;margin:0;max-width:800px;}
.sd-hero h1 em {font-style:normal;color:#ff536e;}
.sd-hero p {font-size:.98rem;line-height:1.75;color:#bcb9c3;max-width:760px;margin:1rem 0 0;}
.sd-hero-tags {display:flex;gap:8px;flex-wrap:wrap;margin-top:1.4rem;}
.sd-hero-tags span {background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10);padding:7px 12px;border-radius:50px;font-size:.72rem;color:#e4dfe6;}
.sd-section {margin:1.9rem 0 1rem;display:flex;align-items:center;gap:11px;color:#f5f2f7;font-weight:750;letter-spacing:-.02em;font-size:1.17rem;}
.sd-section small {font-weight:600;font-size:.67rem;letter-spacing:.12em;color:#ff637c;background:rgba(255,69,98,.09);border:1px solid rgba(255,69,98,.18);padding:6px 9px;border-radius:7px;}
/* Responsive input panels + tasteful hover glow */
[data-testid="stTextArea"] textarea,[data-testid="stTextInput"] input,[data-baseweb="select"] > div,[data-testid="stFileUploader"] section {
 background:rgba(30,32,42,.84) !important;border:1px solid rgba(198,197,211,.15) !important;
 border-radius:13px !important;transition:border-color .22s ease,box-shadow .25s ease,transform .25s ease !important;
}
[data-testid="stTextArea"] textarea:hover,[data-testid="stTextInput"] input:hover,[data-baseweb="select"] > div:hover,[data-testid="stFileUploader"] section:hover {
 border-color:rgba(255,93,124,.6) !important;box-shadow:0 0 0 1px rgba(255,75,110,.12),0 0 26px rgba(255,59,99,.11) !important;
}
[data-testid="stTextArea"] textarea:focus,[data-testid="stTextInput"] input:focus,[data-baseweb="select"] > div:focus-within {
 border-color:#ff5f7b !important;box-shadow:0 0 0 2px rgba(255,70,109,.22),0 0 35px rgba(255,59,99,.10) !important;
}
[data-testid="stButton"] button[kind="primary"],button[data-testid="stBaseButton-primary"] {
 border:none !important;background:linear-gradient(110deg,#ff3154,#e72148) !important;color:white !important;border-radius:12px !important;
 box-shadow:0 8px 24px rgba(239,39,80,.24) !important;font-weight:750 !important;padding-inline:1.8rem !important;
 transition:transform .22s,box-shadow .22s,filter .22s !important;
}
[data-testid="stButton"] button[kind="primary"]:hover,button[data-testid="stBaseButton-primary"]:hover {
 transform:translateY(-2px);filter:brightness(1.13);box-shadow:0 12px 38px rgba(247,44,85,.45) !important;
}
[data-testid="stDownloadButton"] button,[data-testid="stExpander"] details,[data-testid="stDataFrame"] {
 border:1px solid rgba(255,255,255,.10) !important;border-radius:14px !important;
 transition:border-color .24s, box-shadow .24s,transform .24s;
}
[data-testid="stDownloadButton"] button:hover,[data-testid="stExpander"] details:hover,[data-testid="stDataFrame"]:hover {
 border-color:rgba(255,76,115,.46) !important;box-shadow:0 0 25px rgba(255,54,93,.095) !important;
}
[data-testid="stAlert"] {border-radius:14px !important;}
[data-testid="stSlider"] [role="slider"] {box-shadow:0 0 12px rgba(255,59,99,.3);}
/* Reduced motion, touch accessibility */
@media (prefers-reduced-motion:reduce) { *,*::before,*::after {animation-duration:.01ms !important;transition-duration:.01ms !important;} }
@media (max-width:700px) {.sd-hero{padding:1.45rem 1.25rem;border-radius:17px}.block-container{padding-top:1rem!important}.sd-hero h1{font-size:2.1rem}}
</style>
""", unsafe_allow_html=True)

# Optional pointer halo. Runs in Streamlit's isolated component; if a browser blocks
# parent access, all other CSS hover effects remain functional.
components.html(r"""
<script>
(function(){
 try {
  const d = window.parent.document, w = window.parent;
  if (!w.matchMedia('(pointer:fine)').matches || w.matchMedia('(prefers-reduced-motion:reduce)').matches) return;
  if (d.getElementById('sd-pointer-halo')) return;
  const halo = d.createElement('div'); halo.id='sd-pointer-halo';
  halo.style.cssText='position:fixed;z-index:2147480000;left:0;top:0;width:240px;height:240px;border-radius:50%;pointer-events:none;opacity:0;transform:translate(-50%,-50%);background:radial-gradient(circle,rgba(255,50,90,.14) 0%,rgba(255,50,90,.055) 33%,transparent 70%);mix-blend-mode:screen;transition:opacity .35s ease;will-change:left,top;';
  d.body.appendChild(halo);
  let x=-500,y=-500,tx=-500,ty=-500,active=false;
  d.addEventListener('pointermove', e=>{x=e.clientX;y=e.clientY;halo.style.opacity='.85';active=true;},{passive:true});
  d.addEventListener('pointerleave',()=>{halo.style.opacity='0';active=false;},{passive:true});
  function animate(){tx+=(x-tx)*.2;ty+=(y-ty)*.2;halo.style.left=tx+'px';halo.style.top=ty+'px';w.requestAnimationFrame(animate)}
  animate();
 }catch(e){/* sandbox/browser restriction: keep CSS-only hover */}
})();
</script>
""", height=0)
# --- End presentation-only enhancement. ---

TIER_ICON = {"High": "\U0001F534 High", "Medium": "\U0001F7E0 Medium", "Low": "⚪ Low", "Not assessed": "⛔ Not assessed"}
SAMPLES = {
    "(paste your own)": "",
    "Sample: hotel heiress (unseen pitch)": (ROOT / "samples/unseen_pitch_01.txt").read_text(encoding="utf-8"),
    "Sample: oil dumping (original, expect no match)": (ROOT / "samples/unseen_pitch_02_original.txt").read_text(encoding="utf-8"),
    "Sample: Hindi (Devanagari) pitch": (ROOT / "samples/pitch_hindi_devanagari.txt").read_text(encoding="utf-8"),
    "Sample: Hinglish (Hindi in Roman letters) pitch": (ROOT / "samples/pitch_hinglish.txt").read_text(encoding="utf-8"),
    "Sample: Spanish (needs a model - shows the 'not assessed' message)": (ROOT / "samples/pitch_spanish_unsupported_demo.txt").read_text(encoding="utf-8"),
    "Sample: hidden-wealth tutor (same trope, different plot)":
        "CEO Vedant disguises himself as a struggling tutor to teach the daughter of a rival family. The relatives insult his "
        "clothes and refuse to let him eat at their table. Vedant keeps teaching the shy girl until she passes her board exams. "
        "At the school fair he reveals that he owns the town's only school and announces that tuition will be free for every child.",
}


@st.cache_resource(show_spinner=False)
def build_index(raw: bytes, name: str, use_model: bool = False):
    cards, _notes = prepare_catalogue(parse_catalogue(raw, name), adapter_from_env() if use_model else None)
    return StoryIndex(cards)


st.markdown("""
<div class="sd-hero">
  <div class="sd-eyebrow"><span class="sd-dot"></span> STORY INTELLIGENCE / EDITORIAL STUDIO</div>
  <h1>Every story deserves<br><em>its own DNA.</em></h1>
  <p>Compare new microdrama pitches against an existing catalogue. Spot overlapping plot patterns, discover meaningful differences, and review the evidence before production.</p>
  <div class="sd-hero-tags"><span>◆ Narrative overlap</span><span>◆ Beat-by-beat evidence</span><span>◆ Human-reviewed decisions</span></div>
</div>
""", unsafe_allow_html=True)
st.caption(CAVEAT)

with st.sidebar:
    st.header("Catalogue")
    up = st.file_uploader("Story-card catalogue (.json or .csv)", type=["json", "csv"])
    st.caption("Columns: story_id, title, synopsis (+ optional genre, source_url, provenance). "
               "Default: 30 original story cards written for this assignment (not real shows).")
    top_k = st.slider("Candidates to show", 3, 10, 5)
    redact = st.checkbox("Store only a hash of the pitch in exports", value=False)
    st.header("Model (optional)")
    use_llm = st.checkbox("Ask a model to double-check the top 3", value=False,
                          help="Needs STORYDNA_PROVIDER / STORYDNA_MODEL / STORYDNA_API_KEY in the environment. Off = free, offline.")
    use_tr = st.checkbox("Translate non-English text with the model (any language)", value=False,
                         help="Hindi / Hinglish work offline via a built-in glossary. Every other language needs this option "
                              "plus a configured model (same environment variables).")

try:
    if up is not None:
        index = build_index(up.getvalue(), up.name, use_tr)
        cat_name = up.name
    else:
        p = ROOT / "data/catalogue.json"
        index = build_index(p.read_bytes(), p.name)
        cat_name = "bundled sample catalogue"
except InputError as e:
    st.error("Catalogue problem: %s" % e)
    st.stop()
st.sidebar.success("%d stories loaded (%s)" % (index.n, cat_name))

DEMO = "Sample: hotel heiress (unseen pitch)"
if st.query_params.get("demo") == "1" and "_demo_init" not in st.session_state:   # shareable demo link: ?demo=1
    st.session_state["sample_choice"] = DEMO
    st.session_state["_demo_init"] = True
st.markdown('<div class="sd-section"><small>01 / INPUT</small> New story analysis</div>', unsafe_allow_html=True)
choice = st.selectbox("Start from a sample or paste below", list(SAMPLES), key="sample_choice")
if choice != st.session_state.get("_last_choice"):
    st.session_state["pitch"] = SAMPLES[choice]
    st.session_state["_last_choice"] = choice
pitch_file = st.file_uploader("...or upload a .txt pitch", type=["txt", "md"], key="pf")
if pitch_file is not None and st.session_state.get("_pf") != pitch_file.file_id:
    st.session_state["pitch"] = pitch_file.getvalue().decode("utf-8", errors="replace")
    st.session_state["_pf"] = pitch_file.file_id
pitch = st.text_area("New pitch / synopsis (event-by-event works best)", key="pitch", height=190)
title = st.text_input("Pitch title (optional)", "")

if st.button("Compare stories", type="primary"):
    try:
        adapter = adapter_from_env() if (use_llm or use_tr) else None
        with st.spinner("Comparing..."):
            st.session_state["report"] = review_pitch(index, pitch, title=title, top_k=top_k,
                                                      adapter=adapter if use_llm else (adapter if use_tr else None),
                                                      redact_input=redact, query_id=(title or "pitch"),
                                                      translate_with_model=use_tr)
        st.session_state["decisions"] = {}
    except (InputError, AdapterError) as e:
        st.session_state.pop("report", None)
        st.error(str(e))

if st.query_params.get("demo") == "1" and "report" not in st.session_state:
    st.session_state["report"] = review_pitch(index, SAMPLES[DEMO], title="demo", top_k=top_k)
    st.session_state["decisions"] = {}

rep = st.session_state.get("report")
if rep:
    lg = rep.get("language", {})
    if lg.get("method") in ("glossary", "llm"):
        st.info("Language detected: **%s** - compared as English using the **%s** route." % (lg["name"], lg["method"]))
        with st.expander("English text the matcher actually compared"):
            st.text(rep.get("working_text_en") or "(hidden: redaction is on)")
    if not lg.get("reliable", True):
        st.error("Low reliability for this language/text. A Low result is NOT evidence of originality.")
    for w in rep["input_warnings"]:
        st.warning(w)
    if not rep["validation"]["ok"]:
        st.error("Report failed validation: %s" % rep["validation"]["problems"])
    st.markdown('<div class="sd-section"><small>02 / RESULTS</small> Editorial matches</div>', unsafe_allow_html=True)
    st.subheader("Top %d review candidates" % len(rep["top_candidates"]))
    st.dataframe([{"#": c["rank"], "Story": c["candidate_title"], "Review priority": TIER_ICON[c["review_priority"]],
                   "Score": c["retrieval_score"], "Distinctive shared events": ", ".join(c["shared_distinctive_events"]) or "-",
                   "Generic tropes shared": ", ".join(c["shared_generic_tropes"]) or "-"} for c in rep["top_candidates"]],
                 hide_index=True)
    dec = st.session_state.setdefault("decisions", {})
    for c in rep["top_candidates"]:
        with st.expander("#%d  %s — %s" % (c["rank"], c["candidate_title"], TIER_ICON[c["review_priority"]]),
                         expanded=(c["rank"] == 1)):
            st.write(c["recommendation"])
            st.caption("Source: %s | %s | input: %s" % (c["source_url"], c["candidate_provenance"] or "provenance n/a",
                                                         c["candidate_input_granularity"]))
            if c["matched_plot_beats"]:
                st.markdown("**Matching beats (same order)**")
                st.dataframe([{"Events": ", ".join(m["events"]) or "(wording)", "Trope-only?": "yes" if m["generic_trope_only"] else "",
                               "New pitch": m.get("pitch_text_original") or m["pitch_text"],
                               "Catalogue story": m.get("candidate_text_original") or m["candidate_text"]}
                              for m in c["matched_plot_beats"]], hide_index=True)
            else:
                st.info("No beat-level evidence worth showing: overlap is vocabulary/genre only.")
            if c["differentiating_beats"]:
                st.markdown("**Beats that differ**")
                for d in c["differentiating_beats"]:
                    st.write("- *%s:* %s" % (d["side"], d["text"]))
            if "llm_review" in c:
                lr = c["llm_review"]
                st.markdown("**Model check:** `%s` (%s)" % (lr.get("verdict"), lr.get("status")))
                for m in lr.get("matched", []):
                    st.write("- %s — *%s*" % (m["why"], m["candidate_text"]))
            if c.get("failure_notes"):
                st.warning(c["failure_notes"])
            dec[c["candidate_id"]] = st.radio("Your decision", ["(undecided)", "Relevant - needs editorial review", "False alarm",
                                                                 "Safe to proceed"], key="dec_" + c["candidate_id"],
                                              horizontal=True)
    final = json.loads(json.dumps(rep))
    for c in final["top_candidates"]:
        d = dec.get(c["candidate_id"])
        c["reviewer_decision"] = None if d in (None, "(undecided)") else d
    c1, c2 = st.columns(2)
    c1.download_button("Download report (JSON)", json.dumps(final, indent=2), file_name="storydna_%s.json" % rep["run_id"])
    c2.download_button("Download summary (CSV)", report_to_csv(final), file_name="storydna_%s.csv" % rep["run_id"])
