"""Headless UI tests with Streamlit's AppTest."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app/streamlit_app.py")


def md(at):
    return " ".join(m.value for m in at.markdown)


def tab_labels(at):
    return " ".join(t.label for t in at.tabs)


def fresh():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def test_compare_sample_end_to_end():
    at = fresh()
    at.selectbox[0].select("Sample: hotel heiress (unseen pitch)").run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    assert "The Intern Who Owns the Floor" in md(at) and "Make it more original" in tab_labels(at)
    assert at.session_state["report"]["validation"]["ok"]
    assert len(at.session_state["report"]["top_candidates"]) == 5


def test_empty_pitch_shows_readable_error():
    at = fresh()
    at.button[0].click().run()
    assert any("empty" in e.value.lower() for e in at.error)
    assert "report" not in at.session_state


def test_original_pitch_gets_no_high():
    at = fresh()
    at.selectbox[0].select("Sample: oil dumping (original, expect no match)").run()
    at.button[0].click().run()
    tiers = [c["review_priority"] for c in at.session_state["report"]["top_candidates"]]
    assert "High" not in tiers


def test_llm_toggle_without_config_is_clear_error():
    at = fresh()
    at.selectbox[0].select("Sample: hotel heiress (unseen pitch)").run()
    at.sidebar.checkbox[1].check().run()
    at.button[0].click().run()
    assert not at.exception
    # No provider configured -> adapter is the Null adapter -> comparison simply has no model section, never a crash.


def test_hindi_sample_end_to_end():
    at = fresh()
    at.selectbox[0].select("Sample: Hindi (Devanagari) pitch").run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    rep = at.session_state["report"]
    assert rep["language"]["method"] == "glossary" and rep["top_candidates"][0]["candidate_id"] == "S12"
    assert "Language detected" in md(at)


def test_spanish_sample_is_not_assessed_with_clear_error():
    at = fresh()
    at.selectbox[0].select("Sample: Spanish (needs a model - shows the 'not assessed' message)").run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    assert all(c["review_priority"] == "Not assessed" for c in at.session_state["report"]["top_candidates"])
    assert "Low reliability" in md(at) and "Not assessed" in md(at)
