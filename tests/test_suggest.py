import json
from pathlib import Path

import pytest

from storydna.catalogue import load_catalogue
from storydna.events import EVENT_LABELS
from storydna.llm import MockAdapter
from storydna.matcher import StoryIndex
from storydna.report import review_pitch, report_to_markdown
from storydna.suggest import IDEAS, LEVERS, llm_ideas, suggest_for_candidate

ROOT = Path(__file__).resolve().parent.parent
HOTEL = (ROOT / "samples/unseen_pitch_01.txt").read_text()


@pytest.fixture(scope="module")
def ix():
    return StoryIndex(load_catalogue(ROOT / "data/catalogue.json"))


def test_every_event_has_writer_ideas():
    assert set(IDEAS) == set(EVENT_LABELS)
    assert all(len(v) >= 2 and all(len(x.split()) >= 8 for x in v) for v in IDEAS.values())
    assert len(LEVERS) >= 6


def test_high_candidate_gets_suggestions_low_does_not(ix):
    r = review_pitch(ix, HOTEL)
    top = r["top_candidates"][0]
    assert top["review_priority"] == "High" and top["differentiation"]["beat_fixes"] and top["differentiation"]["angles"]
    assert all("differentiation" not in c for c in r["top_candidates"] if c["review_priority"] == "Low")
    assert r["validation"]["ok"]


def test_suggestions_never_change_scores(ix):
    a = review_pitch(ix, HOTEL, suggest=True)
    b = review_pitch(ix, HOTEL, suggest=False)
    assert [(c["candidate_id"], c["retrieval_score"], c["review_priority"]) for c in a["top_candidates"]] == \
           [(c["candidate_id"], c["retrieval_score"], c["review_priority"]) for c in b["top_candidates"]]


def test_the_advice_actually_works_when_followed(ix):
    """Rewrite the two flagged beats the way the suggestions say (different mechanism, different world) and re-check."""
    before = review_pitch(ix, HOTEL)["top_candidates"][0]
    assert before["review_priority"] == "High"
    flagged = {f["pitch_beat_index"] for f in before["differentiation"]["beat_fixes"]}
    beats = [b for b in HOTEL.replace("\n", " ").split(". ") if b.strip()]
    rewrites = {
        1: "The duty manager, Colin, never raises his voice; he simply leaves her name off the rota until she is forgotten.",
        4: "Rhea says nothing at the gala; her mother, an old cleaner, quietly hands the board a letter that explains who she is.",
    }
    new = [rewrites.get(i, b.rstrip(".") + ".") if i in flagged else b.rstrip(".") + "." for i, b in enumerate(beats)]
    after = review_pitch(ix, "\n".join(new))["top_candidates"][0]
    assert after["review_priority"] != "High" and after["retrieval_score"] < before["retrieval_score"]


def test_preview_numbers_come_from_the_scorer(ix):
    r = review_pitch(ix, HOTEL)
    pv = r["top_candidates"][0]["differentiation"]["rewrite_preview"]
    assert pv["before"]["score"] == r["top_candidates"][0]["retrieval_score"]
    assert pv["after"]["score"] < pv["before"]["score"] and "re-check" in pv["note"]
    assert pv["per_beat"] == sorted(pv["per_beat"], key=lambda x: -x["drop"])


def test_unsupported_language_gets_no_suggestions(ix):
    r = review_pitch(ix, "ஒரு பணக்கார பெண் ஏழை வேலைக்காரியாக நடிக்கிறாள். அவளுடைய குடும்பம் அவளை கேலி செய்கிறது. கடைசியில் அவள் உண்மையை வெளிப்படுத்துகிறாள். அவள் எல்லோர் முன்னிலையிலும் அறிவிக்கிறாள்.")
    assert all("differentiation" not in c for c in r["top_candidates"])


def test_markdown_contains_the_advice(ix):
    assert "How to make this pitch more original" in report_to_markdown(review_pitch(ix, HOTEL))


P = ["A hotel heiress works as a cleaner.", "Her manager humiliates her.", "She reveals herself at the gala."]
C = ["Naina is an unpaid intern.", "Sunil takes credit for her sketches and publicly calls her useless.", "She shows the sketchbook on the big screen."]


def test_model_ideas_are_validated():
    good = {"ideas": [
        {"idea": "What if the heiress is a trainee chef and the secret surfaces when a rival critic recognises her mother's recipe?", "changes_beats": [0, 2], "why_less_similar": "new world and new reveal"},
        {"idea": "Let the manager be her secret mentor who is testing whether she will quit before the board visits.", "changes_beats": [1], "why_less_similar": "no humiliation"},
        {"idea": "copy: Sunil takes credit for her sketches and publicly calls her useless again and again", "changes_beats": [1]},   # copied
        {"idea": "too short", "changes_beats": [1]},
        {"idea": "Move everything to a village school where the heiress teaches and the reveal is a letter from the trust.", "changes_beats": [99, 1]},
    ]}
    r = llm_ideas(P, C, ["HUMILIATION"], MockAdapter(lambda s, u: json.dumps(good)))
    assert r["status"] == "ok" and len(r["ideas"]) == 3 and r["invalid_ideas_dropped"] == 2
    assert all(b < 3 for i in r["ideas"] for b in i["changes_beats"])
    assert llm_ideas(P, C, [], MockAdapter(lambda s, u: "no json"))["status"] == "error"
    assert llm_ideas(P, C, [], MockAdapter(lambda s, u: json.dumps({"ideas": []})))["status"] == "error"

    def boom(s, u):
        from storydna.llm import AdapterError
        raise AdapterError("down")
    assert "down" in llm_ideas(P, C, [], MockAdapter(boom))["error"]


def test_model_ideas_only_when_requested(ix):
    calls = []
    ad = MockAdapter(lambda s, u: calls.append("differentiate" in s.lower() or "angles" in s.lower()) or json.dumps(
        {"verdict": "unrelated", "confidence": "low", "matched": [], "differences": []}))
    review_pitch(ix, HOTEL, adapter=ad)                              # compare stage may call the model, ideas must not
    assert not any(calls)
    top = suggest_for_candidate(ix, review_pitch(ix, HOTEL)["top_candidates"][0], HOTEL, adapter=MockAdapter(lambda s, u: "x"))
    assert top["model_ideas"]["status"] == "error"                  # asked, model failed -> readable error, no crash
