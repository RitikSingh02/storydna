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


st.title("StoryDNA — cross-catalogue narrative redundancy review")
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
