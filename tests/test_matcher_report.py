import copy
import json
import re
from pathlib import Path
import pytest
from storydna.catalogue import load_catalogue, StoryCard
from storydna.matcher import StoryIndex
from storydna.report import review_pitch, validate_report, report_to_csv

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def ix():
    return StoryIndex(load_catalogue(ROOT / "data/catalogue.json"))


def test_exact_text_ranks_first_and_high(ix):
    c = ix.cards[5]
    r = review_pitch(ix, c.synopsis, query_id="t")
    assert r["top_candidates"][0]["candidate_id"] == c.story_id
    assert r["top_candidates"][0]["review_priority"] == "High"
    assert r["validation"]["ok"]


def test_renamed_text_still_matches(ix):
    c = ix.cards[0]
    text = re.sub(r"Arjun", "Karthik", c.synopsis)
    text = re.sub(r"Meera", "Divya", text)
    r = review_pitch(ix, text)
    assert r["top_candidates"][0]["candidate_id"] == c.story_id


def test_unrelated_is_not_high(ix):
    r = review_pitch(ix, "Two brothers run a tea stall at a railway station. They add a rooftop screen during the world cup. "
                         "The stall becomes a hit. The brothers argue about expanding.")
    assert all(c["review_priority"] != "High" for c in r["top_candidates"])


def test_deterministic(ix):
    t = ix.cards[3].synopsis
    a = review_pitch(ix, t)
    b = review_pitch(ix, t)
    assert [c["candidate_id"] for c in a["top_candidates"]] == [c["candidate_id"] for c in b["top_candidates"]]
    assert [c["retrieval_score"] for c in a["top_candidates"]] == [c["retrieval_score"] for c in b["top_candidates"]]


def test_report_schema_and_json(ix):
    r = review_pitch(ix, ix.cards[2].synopsis, top_k=5)
    assert len(r["top_candidates"]) == 5
    assert [c["rank"] for c in r["top_candidates"]] == [1, 2, 3, 4, 5]
    json.loads(json.dumps(r))
    for k in ("matched_plot_beats", "differentiating_beats", "supporting_excerpt_or_scene_id", "reviewer_decision", "failure_notes"):
        assert k in r["top_candidates"][0]
    assert report_to_csv(r).count("\n") == 6


def test_validator_catches_fabricated_evidence(ix):
    r = review_pitch(ix, ix.cards[1].synopsis)
    bad = copy.deepcopy(r)
    bad["top_candidates"][0]["matched_plot_beats"][0]["candidate_text"] = "An event that never happens."
    assert any("does not match catalogue" in p for p in validate_report(bad, ix))
    bad2 = copy.deepcopy(r)
    bad2["top_candidates"][0]["candidate_id"] = "S999"
    assert any("not in catalogue" in p for p in validate_report(bad2, ix))
    bad3 = copy.deepcopy(r)
    bad3["top_candidates"][1]["rank"] = 1
    assert any("duplicate ranks" in p for p in validate_report(bad3, ix))


def test_redact_input_stores_only_hash(ix):
    r = review_pitch(ix, ix.cards[4].synopsis, redact_input=True)
    assert r["input_text"] is None and len(r["input_sha256"]) == 64


def test_one_card_catalogue_and_one_sentence_pitch():
    ix1 = StoryIndex([StoryCard("A", "Only", "A man loses his job. He opens a shop. The shop thrives.")])
    r = review_pitch(ix1, "A man opens a shop.")
    assert len(r["top_candidates"]) == 1
    assert any("Very short" in w for w in r["input_warnings"])


def test_old_english_only_warning_still_available(ix):
    """translate='off' keeps the original English-only behaviour and warnings."""
    r = review_pitch(ix, "एक अमीर लड़का गरीब बनकर नौकरी करता है। उसका अपमान होता है। वह सच बताता है।", translate="off")
    assert any("non-English" in w for w in r["input_warnings"])
    r = review_pitch(ix, "Ek ameer ladka garib banke driver ki naukri karta hai. Ladki ka parivar uska apmaan karta hai. "
                         "Shaadi mein woh sabko sach batata hai. Ladki usse maaf kar deti hai.", translate="off")
    assert any("does not look like English" in w for w in r["input_warnings"])
    assert not review_pitch(ix, ix.cards[0].synopsis)["input_warnings"]
