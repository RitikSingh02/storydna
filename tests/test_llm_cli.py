import json
from pathlib import Path
import pytest
from storydna.catalogue import load_catalogue
from storydna.matcher import StoryIndex
from storydna.report import review_pitch
from storydna import llm
from storydna.cli import main

ROOT = Path(__file__).resolve().parent.parent
Q = ["A man hides his wealth.", "He is mocked.", "He reveals himself at the wedding."]
C = ["A rich heir poses as a driver.", "The family mocks him.", "He announces who he is at the engagement."]


def test_good_model_answer_is_kept():
    ad = llm.MockAdapter(lambda s, u: json.dumps({"verdict": "same_plot", "confidence": "high", "differences": ["setting"],
        "matched": [{"pitch_beat": 0, "candidate_beat": 0, "why": "both hide wealth"}, {"pitch_beat": 2, "candidate_beat": 2, "why": "public reveal"}]}))
    r = llm.llm_compare(Q, C, ad)
    assert r["status"] == "ok" and r["verdict"] == "same_plot" and len(r["matched"]) == 2
    assert r["matched"][0]["candidate_text"] == C[0]


def test_hallucinated_evidence_is_dropped_and_verdict_downgraded():
    ad = llm.MockAdapter(lambda s, u: json.dumps({"verdict": "same_plot", "confidence": "high",
        "matched": [{"pitch_beat": 9, "candidate_beat": 0, "why": "x"}, {"pitch_beat": 1, "candidate_beat": 77, "why": "y"}, {"pitch_beat": 1, "candidate_beat": 1, "why": ""}]}))
    r = llm.llm_compare(Q, C, ad)
    assert r["verdict"] == "unverified" and r["matched"] == [] and r["invalid_evidence_dropped"] == 3


def test_garbage_and_failing_models_never_raise():
    r = llm.llm_compare(Q, C, llm.MockAdapter(lambda s, u: "I cannot do that."))
    assert r["status"] == "error"
    def boom(s, u): raise llm.AdapterError("network down")
    r = llm.llm_compare(Q, C, llm.MockAdapter(boom))
    assert r["status"] == "error" and "network down" in r["error"]
    r = llm.llm_compare(Q, C, llm.MockAdapter(lambda s, u: '{"verdict": "banana"}'))
    assert r["status"] == "error"


def test_fenced_json_is_parsed():
    ad = llm.MockAdapter(lambda s, u: "```json\n" + json.dumps({"verdict": "unrelated", "matched": []}) + "\n```")
    assert llm.llm_compare(Q, C, ad)["verdict"] == "unrelated"


def test_extract_beats_rejects_ungrounded():
    src = "Meera hides her wealth and takes a job at a cafe. The owner mocks her. She buys the cafe and fires him."
    ad = llm.MockAdapter(lambda s, u: json.dumps({"beats": [
        "Meera hides her wealth and takes a job at a cafe.", "The owner mocks her.", "She buys the cafe and fires the owner.",
        "A dragon destroys the city of Atlantis during a thunderstorm."]}))
    beats = llm.llm_extract_beats(src, ad)
    assert len(beats) == 3 and not any("dragon" in b for b in beats)


def test_adapter_from_env():
    assert llm.adapter_from_env({}).name == "none"
    with pytest.raises(llm.AdapterError):
        llm.adapter_from_env({"STORYDNA_PROVIDER": "anthropic"})
    with pytest.raises(llm.AdapterError):
        llm.adapter_from_env({"STORYDNA_PROVIDER": "anthropic", "STORYDNA_MODEL": "m"})
    a = llm.adapter_from_env({"STORYDNA_PROVIDER": "groq", "STORYDNA_MODEL": "m", "STORYDNA_API_KEY": "k", "STORYDNA_BASE_URL": "https://api.groq.com/openai/v1"})
    assert "groq" in a.name


def test_pipeline_flags_model_heuristic_disagreement():
    ix = StoryIndex(load_catalogue(ROOT / "data/catalogue.json"))
    ad = llm.MockAdapter(lambda s, u: json.dumps({"verdict": "shared_tropes_only", "confidence": "medium", "matched": [], "differences": ["different plot"]}))
    r = review_pitch(ix, ix.cards[0].synopsis, adapter=ad)
    top = r["top_candidates"][0]
    assert top["llm_review"]["verdict"] == "shared_tropes_only" and "disagree" in top["failure_notes"]
    assert top["review_priority"] == "High"   # the model never silently overrides the tier
    assert r["llm"]["adapter"] == "mock"


def test_cli_ok_and_errors(tmp_path, capsys):
    p = tmp_path / "pitch.txt"
    p.write_text(Path(ROOT / "samples/unseen_pitch_01.txt").read_text())
    assert main(["compare", "--pitch", str(p), "--out", str(tmp_path / "o")]) == 0
    assert (tmp_path / "o" / "report.json").exists()
    e = tmp_path / "empty.txt"; e.write_text("")
    assert main(["compare", "--pitch", str(e)]) == 2
    assert main(["compare", "--pitch", str(tmp_path / "nope.txt")]) == 2
    bad = tmp_path / "bad.csv"; bad.write_text("x,y\n1,2\n")
    assert main(["compare", "--pitch", str(p), "--catalogue", str(bad)]) == 2
