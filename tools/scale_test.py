#!/usr/bin/env python3
"""Timing/memory at catalogue sizes 30 -> 10,000 using SYNTHETIC cards (sentences recombined from the 30 real
cards). Measures cost only; says nothing about accuracy at that size. Writes raw_outputs/scale_test.csv."""
import csv, json, random, resource, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from storydna.catalogue import StoryCard, load_catalogue
from storydna.matcher import StoryIndex
from storydna.textproc import split_sentences

random.seed(7)
base = load_catalogue(ROOT / "data/catalogue.json")
pool = [s for c in base for s in c.beats]
queries = [q["text"] for q in json.loads((ROOT / "data/benchmark/queries.json").read_text())["queries"]][:20]

def synth(n):
    cards = list(base)
    while len(cards) < n:
        k = len(cards)
        beats = random.sample(pool, random.randint(5, 8))
        cards.append(StoryCard("X%05d" % k, "Synthetic %d" % k, " ".join(beats)))
    return cards[:n]

rows = []
for n in (30, 300, 3000, 10000):
    cards = synth(n)
    t0 = time.perf_counter(); ix = StoryIndex(cards); build = time.perf_counter() - t0
    lat = []
    for q in queries:
        t0 = time.perf_counter(); ix.score(q, top_k=5); lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    rows.append({"catalogue_size": n, "index_build_s": round(build, 2), "query_median_ms": round(lat[len(lat)//2], 1),
                 "query_p95_ms": round(lat[int(len(lat)*0.95)-1], 1), "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)})
    print(rows[-1])
with open(ROOT / "raw_outputs/scale_test.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
