#!/usr/bin/env python3
"""Robustness runs: odd, hostile and unseen inputs. Every outcome (including errors) is written, unedited,
to raw_outputs/robustness/. Success = a readable error or a flagged, valid report; never a crash."""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from storydna.catalogue import InputError, load_catalogue, parse_catalogue  # noqa: E402
from storydna.matcher import StoryIndex  # noqa: E402
from storydna.report import review_pitch  # noqa: E402

OUT = ROOT / "raw_outputs" / "robustness"
OUT.mkdir(parents=True, exist_ok=True)
cards = load_catalogue(ROOT / "data/catalogue.json")
ix = StoryIndex(cards)
sample = (ROOT / "samples/unseen_pitch_01.txt").read_text()

PITCH_CASES = {
    "r01_empty": "",
    "r02_whitespace_only": "   \n\t  \n",
    "r03_single_sentence": "A rich man pretends to be poor.",
    "r04_huge_input_300k_chars": "A rich man pretends to be poor. " * 10000,
    "r05_hindi_devanagari": "एक अमीर लड़का गरीब बनकर नौकरी करता है। उसका अपमान होता है। वह शादी में सच बताता है। लड़की उसे माफ़ कर देती है।",
    "r06_hinglish_roman": "Ek ameer ladka garib banke driver ki naukri karta hai. Ladki ka parivar uska apmaan karta hai. Shaadi mein woh sabko sach batata hai. Ladki usse maaf kar deti hai.",
    "r07_control_chars_and_emoji": "Rich \x00heir\x07 poses as a driver \U0001F697. He is mocked \U0001F622. At the wedding he reveals the truth \U0001F389. Everyone gasps.",
    "r08_no_punctuation_lowercase": "arjun the heir poses as a chauffeur to test his fiancee meera her family mocks him and her father insults him in front of guests meera pays his debts in secret on engagement day he reveals he is the investor who saves the firm",
    "r09_bullet_outline": "- Heir poses as driver\n- Family humiliates him\n- Fiancee stands by him\n- He reveals identity at engagement party and saves her father's firm",
    "r10_unseen_pitch_1_hotel_heiress": sample,
    "r11_unseen_pitch_2_original_oil_dumping": (ROOT / "samples/unseen_pitch_02_original.txt").read_text(),
}
CATALOGUE_CASES = {
    "c01_broken_csv_header": ("story_id,name\n1,x\n", "c.csv"),
    "c02_broken_json": ('[{"story_id": "A", "title": "x", "synopsis": ', "c.json"),
    "c03_duplicate_ids": (json.dumps([{"story_id": "A", "title": "x", "synopsis": "One. Two."}] * 2), "c.json"),
    "c04_missing_synopsis": (json.dumps([{"story_id": "A", "title": "x"}]), "c.json"),
    "c05_empty_list": ("[]", "c.json"),
}
summary = []
for name, text in PITCH_CASES.items():
    rec = {"case": name, "kind": "pitch", "input_chars": len(text)}
    try:
        rep = review_pitch(ix, text, query_id=name, redact_input=len(text) > 5000)
        top = rep["top_candidates"][0]
        rec.update(outcome="report", warnings=rep["input_warnings"], validation_ok=rep["validation"]["ok"],
                   top1=top["candidate_id"], top1_title=top["candidate_title"], top1_tier=top["review_priority"],
                   top1_score=top["retrieval_score"], tiers=[c["review_priority"] for c in rep["top_candidates"]])
        (OUT / (name + ".json")).write_text(json.dumps(rep, indent=2))
    except InputError as e:
        rec.update(outcome="readable_error", message=str(e))
    except Exception as e:  # a crash would be a bug; record it
        rec.update(outcome="CRASH", message=repr(e), trace=traceback.format_exc())
    summary.append(rec)
for name, (raw, fname) in CATALOGUE_CASES.items():
    rec = {"case": name, "kind": "catalogue"}
    try:
        parse_catalogue(raw, fname)
        rec.update(outcome="accepted")
    except InputError as e:
        rec.update(outcome="readable_error", message=str(e))
    except Exception as e:
        rec.update(outcome="CRASH", message=repr(e), trace=traceback.format_exc())
    summary.append(rec)
(OUT / "robustness_summary.json").write_text(json.dumps(summary, indent=2))
for r in summary:
    print("%-34s %-15s %s" % (r["case"], r["outcome"], r.get("message") or (
        "top1=%s %s score=%.2f warnings=%d" % (r["top1"], r["top1_tier"], r["top1_score"], len(r["warnings"])))))
print("crashes:", sum(r["outcome"] == "CRASH" for r in summary))
