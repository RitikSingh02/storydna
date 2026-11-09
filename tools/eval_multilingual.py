#!/usr/bin/env python3
"""Run the frozen multilingual sets with the language layer OFF (old behaviour) and ON, saving every raw report.

usage: python tools/eval_multilingual.py --label run1
Writes raw_outputs/multilingual_layer/<label>/{off,auto}/<qid>.json + results.csv + summary.json
"""
import argparse, csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from storydna.catalogue import load_catalogue
from storydna.matcher import StoryIndex
from storydna.report import review_pitch

SETS = ["queries_multilingual.json", "queries_multilingual_roman_pure.json", "queries_multilingual_hard.json"]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--label", required=True); a = ap.parse_args()
    ix = StoryIndex(load_catalogue(ROOT / "data/catalogue.json"))
    base = ROOT / "raw_outputs/multilingual_layer" / a.label
    rows = []
    for setname in SETS:
        for q in json.loads((ROOT / "data/benchmark" / setname).read_text(encoding="utf-8"))["queries"]:
            for mode in ("off", "auto"):
                rep = review_pitch(ix, q["text"], query_id=q["qid"], top_k=10, translate=mode, run_label="%s/%s" % (a.label, mode), suggest=False)
                d = base / mode; d.mkdir(parents=True, exist_ok=True)
                (d / ("%s.json" % q["qid"])).write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
                ids = [c["candidate_id"] for c in rep["top_candidates"]]
                rel = q["relevant"]
                rk = next((i + 1 for i, s in enumerate(ids) if s in rel), None) if rel else None
                t = rep["top_candidates"][0]
                rows.append({"set": setname.replace("queries_", "").replace(".json", ""), "qid": q["qid"], "script": q["language"], "category": q["category"],
                             "mode": mode, "relevant": ";".join(rel), "rank_of_relevant": rk, "top1": t["candidate_id"], "top1_tier": t["review_priority"],
                             "top1_score": t["retrieval_score"], "any_high": any(c["review_priority"] == "High" for c in rep["top_candidates"]),
                             "detected": rep["language"]["detected"], "method": rep["language"]["method"],
                             "reliable": rep["language"]["reliable"], "recognised_share": rep["language"]["recognised_share"],
                             "valid": rep["validation"]["ok"], "n_warnings": len(rep["input_warnings"])})
    with open(base / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summ = {}
    for mode in ("off", "auto"):
        r = [x for x in rows if x["mode"] == mode]
        pos = [x for x in r if x["relevant"]]; neg = [x for x in r if not x["relevant"]]
        summ[mode] = {
            "positives": len(pos), "pos_rank1": sum(x["rank_of_relevant"] == 1 for x in pos),
            "pos_rank1_and_High": sum(x["rank_of_relevant"] == 1 and x["top1_tier"] == "High" for x in pos),
            "pos_top1_Low": sum(x["top1_tier"] == "Low" for x in pos),
            "negatives": len(neg), "neg_any_High": sum(x["any_high"] for x in neg),
            "neg_top1_Medium_or_High": sum(x["top1_tier"] in ("Medium", "High") for x in neg),
            "invalid_reports": sum(not x["valid"] for x in r),
            "by_set_positives_rank1_and_High": {s: "%d/%d" % (sum(x["rank_of_relevant"] == 1 and x["top1_tier"] == "High" for x in pos if x["set"] == s), sum(1 for x in pos if x["set"] == s))
                                                 for s in sorted({x["set"] for x in pos})}}
    (base / "summary.json").write_text(json.dumps(summ, indent=2)); print(json.dumps(summ, indent=2))
    for x in rows:
        if x["mode"] == "auto":
            print(x["qid"], x["script"], x["detected"], x["method"], "rel", x["relevant"], "rank", x["rank_of_relevant"], x["top1"], x["top1_tier"], x["top1_score"], "recog", x["recognised_share"])
main()
