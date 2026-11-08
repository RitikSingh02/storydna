"""Guards the shipped scorer against regressions on the frozen final-test set (round 4) and the dev sets."""
import json
from pathlib import Path
from storydna.catalogue import load_catalogue
from storydna.matcher import StoryIndex
from storydna.report import review_pitch

ROOT = Path(__file__).resolve().parent.parent


def test_round4_final_set_behaviour():
    ix = StoryIndex(load_catalogue(ROOT / "data/catalogue.json"))
    qs = json.loads((ROOT / "data/benchmark/queries_round4_test.json").read_text())["queries"]
    for q in qs:
        r = review_pitch(ix, q["text"], query_id=q["qid"])
        top = r["top_candidates"][0]
        if q["relevant"]:
            assert top["candidate_id"] in q["relevant"], q["qid"]
            assert top["review_priority"] in q["expected"], q["qid"]
        else:
            assert all(c["review_priority"] != "High" for c in r["top_candidates"]), q["qid"]
        assert r["validation"]["ok"], q["qid"]
