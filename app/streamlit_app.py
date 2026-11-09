"""StoryDNA review site.  Run:  streamlit run app/streamlit_app.py"""
import json
import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))
import theme as T  # noqa: E402
from storydna.catalogue import InputError, parse_catalogue  # noqa: E402
from storydna.llm import AdapterError, adapter_from_env  # noqa: E402
from storydna.matcher import StoryIndex  # noqa: E402
from storydna.report import report_to_csv, review_pitch  # noqa: E402
from storydna.translate import prepare_catalogue  # noqa: E402

st.set_page_config(page_title="StoryDNA | story redundancy review", page_icon="\U0001F3AC", layout="wide")
st.markdown(T.CSS, unsafe_allow_html=True)


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


SAMPLES = {
    "(paste your own)": "",
    "Sample: hotel heiress (unseen pitch)": read("samples/unseen_pitch_01.txt"),
    "Sample: oil dumping (original, expect no match)": read("samples/unseen_pitch_02_original.txt"),
    "Sample: Hindi (Devanagari) pitch": read("samples/pitch_hindi_devanagari.txt"),
    "Sample: Hinglish (Hindi in Roman letters) pitch": read("samples/pitch_hinglish.txt"),
    "Sample: Spanish (needs a model - shows the 'not assessed' message)": read("samples/pitch_spanish_unsupported_demo.txt"),
    "Sample: hidden-wealth tutor (same trope, different plot)":
        "CEO Vedant disguises himself as a struggling tutor to teach the daughter of a rival family. The relatives insult his "
        "clothes and refuse to let him eat at their table. Vedant keeps teaching the shy girl until she passes her board exams. "
        "At the school fair he reveals that he owns the town's only school and announces that tuition will be free for every child.",
}
DEMO = "Sample: hotel heiress (unseen pitch)"
DECISIONS = ["(undecided)", "Relevant - needs editorial review", "False alarm", "Safe to proceed"]


@st.cache_resource(show_spinner=False)
def build_index(raw: bytes, name: str, use_model: bool = False):
    cards, _notes = prepare_catalogue(parse_catalogue(raw, name), adapter_from_env() if use_model else None)
    return StoryIndex(cards)


# ----------------------------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### Catalogue")
    up = st.file_uploader("Story-card catalogue (.json or .csv)", type=["json", "csv"], label_visibility="collapsed")
    st.caption("Columns: story_id, title, synopsis (+ genre, source_url, provenance, language). Default: 30 original story cards written for this assignment.")
    st.markdown("### Display")
    top_k = st.slider("Candidates to show", 3, 10, 5)
    redact = st.checkbox("Store only a hash of the pitch in exports", value=False)
    st.markdown("### Model (optional)")
    use_llm = st.checkbox("Double-check the top 3 with a model", value=False,
                          help="Needs STORYDNA_PROVIDER / STORYDNA_MODEL / STORYDNA_API_KEY in the environment. Off = free and offline.")
    use_tr = st.checkbox("Translate non-English text with the model", value=False,
                         help="Hindi and Hinglish work offline. Other languages need this plus a configured model.")
    use_ideas = st.checkbox("Ask the model for fresh angles", value=False,
                            help="Adds model-written ideas next to the built-in ones. Each idea is validated and never copied from the existing story.")

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

# ----------------------------------------------------------------------------------------------- header + input
def _showcase(cards, k):
    """k posters with different looks, so the hero/shelf do not show three identical tiles."""
    seen, out = set(), []
    for c in cards:
        key = (c.genre or "").split(" ")[-1]
        if key not in seen:
            seen.add(key)
            out.append((c.title, c.genre))
        if len(out) == k:
            break
    return out


GENRE = {c.title: c.genre for c in index.cards}
st.markdown(T.topbar(), unsafe_allow_html=True)
st.markdown(T.hero(_showcase(index.cards, 3)), unsafe_allow_html=True)
st.markdown(T.features(), unsafe_allow_html=True)

if st.query_params.get("demo") == "1" and "_demo_init" not in st.session_state:   # shareable demo link: ?demo=1
    st.session_state["sample_choice"] = DEMO
    st.session_state["_demo_init"] = True

st.markdown('<div id="check-a-pitch"></div>' + T.section("Check a pitch", "paste 4 to 12 event sentences, or pick a sample"), unsafe_allow_html=True)
left, right = st.columns([1.6, 1], gap="large")
with left:
    choice = st.selectbox("Try a sample", list(SAMPLES), key="sample_choice")
    if choice != st.session_state.get("_last_choice"):
        st.session_state["pitch"] = SAMPLES[choice]
        st.session_state["_last_choice"] = choice
    pitch = st.text_area("Your pitch or synopsis (event by event works best)", key="pitch", height=230,
                         placeholder="Paste 4 to 12 sentences describing what happens, in order. English, Hindi or Hinglish.")
    with st.expander("Upload a .txt file instead, or add a title"):
        pitch_file = st.file_uploader("Pitch file", type=["txt", "md"], key="pf", label_visibility="collapsed")
        if pitch_file is not None and st.session_state.get("_pf") != pitch_file.file_id:
            st.session_state["pitch"] = pitch_file.getvalue().decode("utf-8", errors="replace")
            st.session_state["_pf"] = pitch_file.file_id
            st.rerun()
        title = st.text_input("Pitch title (optional)", "")
    go = st.button("Compare stories", type="primary")
with right:
    st.markdown(T.shelf(_showcase(index.cards, 4), index.n, cat_name), unsafe_allow_html=True)

if go:
    try:
        adapter = adapter_from_env() if (use_llm or use_tr or use_ideas) else None
        t0 = time.perf_counter()
        with st.spinner("Comparing against %d stories..." % index.n):
            st.session_state["report"] = review_pitch(index, pitch, title=title, top_k=top_k, adapter=adapter,
                                                      redact_input=redact, query_id=(title or "pitch"),
                                                      translate_with_model=use_tr, suggest_with_model=use_ideas, llm_compare=use_llm)
        st.session_state["ms"] = (time.perf_counter() - t0) * 1000
        st.session_state["decisions"] = {}
    except (InputError, AdapterError) as e:
        st.session_state.pop("report", None)
        st.error(str(e))

if st.query_params.get("demo") == "1" and "report" not in st.session_state:
    t0 = time.perf_counter()
    st.session_state["report"] = review_pitch(index, SAMPLES[DEMO], title="demo", top_k=top_k)
    st.session_state["ms"] = (time.perf_counter() - t0) * 1000
    st.session_state["decisions"] = {}

# ----------------------------------------------------------------------------------------------- results
rep = st.session_state.get("report")
if rep:
    cands = rep["top_candidates"]
    lg = rep.get("language", {})
    notes = []
    if lg.get("method") in ("glossary", "llm"):
        notes.append(T.note("Language detected: %s. Compared as English using the %s route." % (lg["name"], lg["method"]), "info"))
    if not lg.get("reliable", True):
        notes.append(T.note("Low reliability for this language or text. A Low result is NOT evidence of originality.", "bad"))
    notes += [T.note(w, "info") for w in rep["input_warnings"]]
    if not rep["validation"]["ok"]:
        notes.append(T.note("Report failed validation: %s" % rep["validation"]["problems"], "bad"))
    st.markdown(T.section("Result", "run %s" % rep["run_id"]), unsafe_allow_html=True)
    if lg.get("method") != "unsupported":
        st.markdown(T.verdict(cands[0], rep, GENRE.get(cands[0]["candidate_title"], "")), unsafe_allow_html=True)
    st.markdown(T.kpis(rep, st.session_state.get("ms")), unsafe_allow_html=True)
    if notes:
        st.markdown("".join(notes), unsafe_allow_html=True)
    if lg.get("method") in ("glossary", "llm"):
        with st.expander("English text the matcher actually compared"):
            st.text(rep.get("working_text_en") or "(hidden: redaction is on)")

    st.markdown(T.section("Closest stories", "open one to see the evidence and ideas"), unsafe_allow_html=True)
    dec = st.session_state.setdefault("decisions", {})
    for c in cands:
        tier = c["review_priority"]
        label = "#%d  ·  %s  ·  %s  ·  %.2f" % (c["rank"], c["candidate_title"], tier, c["retrieval_score"])
        with st.expander(label, expanded=(c["rank"] == 1)):
            st.markdown('%s<div class="muted" style="margin-top:.5rem">%s</div>' % (T.pill(tier), T.esc(c["recommendation"])), unsafe_allow_html=True)
            names = ["Evidence"] + (["Make it more original"] if c.get("differentiation") else []) + ["Your review"]
            tabs = st.tabs(names)
            with tabs[0]:
                if tier == "Not assessed":
                    st.markdown(T.note("No comparison was made for this language.", "bad"), unsafe_allow_html=True)
                elif c["matched_plot_beats"]:
                    st.markdown(T.tags(c), unsafe_allow_html=True)
                    st.markdown("".join(T.evidence(m, c["candidate_title"]) for m in c["matched_plot_beats"]), unsafe_allow_html=True)
                else:
                    st.markdown(T.note("No beat-level evidence worth showing: the overlap is vocabulary or genre only.", "ok"), unsafe_allow_html=True)
                if c["differentiating_beats"]:
                    st.markdown("<div class='fine' style='margin:.8rem 0 .2rem'>Beats that differ</div>" + T.differing(c), unsafe_allow_html=True)
                if "llm_review" in c:
                    lr = c["llm_review"]
                    st.markdown(T.note("Model check: %s (%s)" % (lr.get("verdict"), lr.get("status")), "info"), unsafe_allow_html=True)
                    for m in lr.get("matched", []):
                        st.markdown("- %s — *%s*" % (m["why"], m["candidate_text"]))
                if c.get("failure_notes"):
                    st.warning(c["failure_notes"])
                st.markdown("<div class='fine'>Source: %s &middot; %s &middot; input: %s</div>" % (
                    T.esc(c["source_url"]), T.esc(c["candidate_provenance"] or "provenance n/a"), T.esc(c["candidate_input_granularity"])), unsafe_allow_html=True)
            if c.get("differentiation"):
                with tabs[1]:
                    st.markdown(T.improve(c["differentiation"]), unsafe_allow_html=True)
            with tabs[-1]:
                dec[c["candidate_id"]] = st.radio("Your decision", DECISIONS, key="dec_" + c["candidate_id"], horizontal=True)
    final = json.loads(json.dumps(rep))
    for c in final["top_candidates"]:
        d = dec.get(c["candidate_id"])
        c["reviewer_decision"] = None if d in (None, "(undecided)") else d
    st.markdown(T.section("Take it with you"), unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 2])
    c1.download_button("Download report (JSON)", json.dumps(final, indent=2, ensure_ascii=False), file_name="storydna_%s.json" % rep["run_id"])
    c2.download_button("Download summary (CSV)", report_to_csv(final), file_name="storydna_%s.csv" % rep["run_id"])

st.markdown(T.footer(), unsafe_allow_html=True)
