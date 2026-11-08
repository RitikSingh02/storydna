from storydna.textproc import split_sentences, find_names, normalise_tokens
from storydna.events import tag_beat


def test_split_keeps_honorifics_and_bullets():
    s = split_sentences("Mr. Rao enters. He sits.\n- She leaves.\n2) They fight.")
    assert s == ["Mr. Rao enters.", "He sits.", "She leaves.", "They fight."]


def test_run_on_text_is_chunked():
    text = " ".join(["word"] * 10 + ["and"] + ["word"] * 40)
    assert len(split_sentences(text)) >= 2


def test_sentence_initial_common_words_are_not_names():
    sents = ["Billionaire Kabir Rao takes a job.", "Kabir finds proof.", "Widow Lakshmi leaves."]
    names = find_names(sents, set())
    assert "kabir" in names and "rao" in names
    assert "billionaire" not in names and "widow" not in names


def test_normalise_drops_names_and_folds_synonyms():
    toks = normalise_tokens("Arjun hires a chauffeur", {"arjun"})
    assert "arjun" not in toks and "driver" in toks


def test_event_tagging_order_and_negation():
    ev = tag_beat("She is humiliated, then reveals the recording in front of the guests.")
    assert "HUMILIATION" in ev and "PUBLIC_REVEAL" in ev
    assert tag_beat("A hidden clause in the will names the heir.") .count("HIDDEN_IDENTITY") == 0
    assert tag_beat("Nothing dramatic happens in this sentence.") == []
