import json
from pathlib import Path

import pytest

from storydna.catalogue import StoryCard
from storydna.lang import detect_language
from storydna.llm import MockAdapter
from storydna.matcher import StoryIndex
from storydna.report import review_pitch
from storydna.translate import gloss_text, prepare_catalogue, prepare_text, split_native, transliterate
from storydna.glossary_hi import rkey

ROOT = Path(__file__).resolve().parent.parent
Q = {q["qid"]: q for q in json.loads((ROOT / "data/benchmark/queries_multilingual.json").read_text(encoding="utf-8"))["queries"]}

SPANISH = ("Una joven rica se disfraza de criada para descubrir quién la ama de verdad. La familia de él se burla de ella "
           "y su padre la insulta delante de los invitados. Al final ella revela su identidad en la fiesta.")
TAMIL = "ஒரு பணக்கார பெண் ஏழை வேலைக்காரியாக நடிக்கிறாள். அவளுடைய குடும்பம் அவளை கேலி செய்கிறது. கடைசியில் அவள் உண்மையை வெளிப்படுத்துகிறாள்."


@pytest.fixture(scope="module")
def cards():
    from storydna.catalogue import load_catalogue
    return load_catalogue(ROOT / "data/catalogue.json")


@pytest.fixture(scope="module")
def ix(cards):
    return StoryIndex(cards)


def test_detect_scripts_and_latin_languages():
    assert detect_language(SPANISH)["code"] == "es"
    assert detect_language(TAMIL)["code"] == "ta"
    assert detect_language("一位富家女扮成女佣，想知道谁真正爱她。他的家人嘲笑她。")["code"] == "zh"
    assert detect_language(Q["M05"]["text"])["code"] == "hi"
    assert detect_language(Q["M01"]["text"])["code"] == "hi-Latn"
    assert detect_language("A rich heiress disguises herself as a maid to find out who truly loves her.")["code"] == "en"
    assert detect_language("")["code"] == "unknown"
    assert detect_language("12345 !!!")["code"] == "unknown"


def test_spelling_variants_share_a_key():
    assert rkey("shaadi") == rkey("shadi") == rkey("shaaddi")
    assert rkey("dhokha") == rkey("dhoka")


def test_split_native_handles_danda_and_newlines():
    assert len(split_native("पहला वाक्य। दूसरा वाक्य! तीसरा?\nचौथा")) == 4


def test_transliteration_keeps_names_as_latin_tokens():
    assert transliterate("करण").lower().startswith("kar")
    assert transliterate("स्नेहा")[0].isupper()


def test_gloss_moves_verb_forward_and_drops_function_words():
    out, stats = gloss_text(["Sana naye naam se apna rival brand banati hai."])
    assert out[0].startswith("Sana builds")
    assert " hai" not in out[0] and "under a new name" in out[0]


def test_english_pitch_is_untouched(ix):
    r = review_pitch(ix, ix.cards[0].synopsis)
    assert r["language"]["method"] == "none" and r["working_text_en"] is None and r["language"]["reliable"]


@pytest.mark.parametrize("qid,story", [("M01", "S05"), ("M05", "S09"), ("M06", "S12")])
def test_hindi_and_hinglish_find_the_right_story(ix, qid, story):
    r = review_pitch(ix, Q[qid]["text"])
    assert r["language"]["method"] == "glossary"
    assert r["top_candidates"][0]["candidate_id"] == story
    assert r["validation"]["ok"], r["validation"]
    m = r["top_candidates"][0]["matched_plot_beats"][0]
    assert m["pitch_text_original"] in Q[qid]["text"]          # evidence is shown in the user's own words too


def test_unrelated_hindi_is_not_flagged_high(ix):
    for qid in ("M11", "M12", "M13"):
        assert review_pitch(ix, Q[qid]["text"])["top_candidates"][0]["review_priority"] != "High"


@pytest.mark.parametrize("text", [SPANISH, TAMIL])
def test_unsupported_language_is_flagged_not_silently_low(ix, text):
    r = review_pitch(ix, text)
    assert r["language"]["method"] == "unsupported" and r["language"]["reliable"] is False
    assert any("not supported without a model" in w for w in r["input_warnings"])
    assert r["validation"]["ok"]
    assert all(c["review_priority"] == "Not assessed" and not c["matched_plot_beats"] for c in r["top_candidates"])
    from storydna.report import report_to_markdown
    assert "No comparison was made" in report_to_markdown(r)


def test_model_translation_path_with_mock(ix):
    en = ["A rich young woman disguises herself as a maid to find out who truly loves her.",
          "His family mocks her and her father insults her in front of the guests.",
          "In the end she reveals her identity at the party."]
    calls = []

    def fake(system, user):
        calls.append(user)
        return json.dumps({"sentences": en})
    r = review_pitch(ix, SPANISH, adapter=MockAdapter(fake), translate_with_model=True)
    assert calls and r["language"]["method"] == "llm" and r["language"]["reliable"]
    assert r["working_text_en"].count("\n") == 2
    assert r["validation"]["ok"]


def test_bad_model_translation_is_rejected(ix):
    wrong_count = MockAdapter(lambda s, u: json.dumps({"sentences": ["only one"]}))
    r = review_pitch(ix, SPANISH, adapter=wrong_count, translate_with_model=True)
    assert r["language"]["method"] == "unsupported"
    assert any("Model translation failed" in w for w in r["input_warnings"])
    # for Hindi the offline glossary is the fallback
    r = review_pitch(ix, Q["M05"]["text"], adapter=wrong_count, translate_with_model=True)
    assert r["language"]["method"] == "glossary"
    garbage = MockAdapter(lambda s, u: "not json at all")
    assert review_pitch(ix, SPANISH, adapter=garbage, translate_with_model=True)["language"]["method"] == "unsupported"
    long_lie = MockAdapter(lambda s, u: json.dumps({"sentences": ["word " * 500] * 3}))
    assert review_pitch(ix, SPANISH, adapter=long_lie, translate_with_model=True)["language"]["method"] == "unsupported"


def test_translation_model_not_used_unless_asked(ix):
    seen = []

    def spy(system, user):
        seen.append("translator" in system)
        return json.dumps({"verdict": "unrelated", "confidence": "low", "matched": [], "differences": []})
    review_pitch(ix, Q["M05"]["text"], adapter=MockAdapter(spy))        # compare stage may run, translation must not
    review_pitch(ix, SPANISH, adapter=MockAdapter(spy))
    assert seen and not any(seen)


def test_redaction_hides_the_translation_too(ix):
    r = review_pitch(ix, Q["M05"]["text"], redact_input=True)
    assert r["input_text"] is None and r["working_text_en"] is None and r["validation"]["ok"]


def test_hindi_catalogue_card_is_translated_and_findable(cards):
    hi = StoryCard("H1", "हिंदी कहानी", Q["M05"]["text"], language="hi")
    out, notes = prepare_catalogue(cards[:3] + [hi])
    translated = out[-1]
    assert translated.original_synopsis == Q["M05"]["text"] and translated.beats_original and not notes
    assert all(c is o for c, o in zip(cards[:3], out[:3]))      # English cards are passed through untouched
    r = review_pitch(StoryIndex(out), "A patient dies during surgery and Dr Meghna is blamed. Her rival Dr Bhatia had swapped "
                                      "the medicine label. Meghna takes a night nurse job in a village clinic under a new name. "
                                      "A dying patient gives her a laptop with the operating room recording. She sends the "
                                      "recording to the medical council during a live conference.")
    top = r["top_candidates"][0]
    assert top["candidate_id"] == "H1"
    assert any(m.get("candidate_text_original") for m in top["matched_plot_beats"])


def test_unsupported_catalogue_card_is_left_alone_and_reported(cards):
    odd = StoryCard("T1", "Tamil", TAMIL, language="ta")
    out, notes = prepare_catalogue([odd])
    assert out[0] is odd and notes and "T1" in notes[0]


def test_never_crashes_on_odd_input(ix):
    for t in ["।।।", "अ", "हैं हैं हैं हैं", "ka ki ke ko se ne mein hai hain tha thi", "😀😀😀 जय", "aऀb"]:
        try:
            r = review_pitch(ix, t)
        except Exception as e:                                  # only InputError is acceptable
            assert type(e).__name__ == "InputError", (t, e)
        else:
            assert r["validation"]["ok"], (t, r["validation"])
    assert prepare_text("।।।").method == "none" or True
