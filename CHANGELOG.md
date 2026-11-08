# Scorer versions behind the raw outputs
- v0 (round 1): event-lexicon + weighted ordered-LCS + lexical/rare-detail features; hand-set weights; rule tiers (thresholds fixed beforehand).
- v1 (round 2): split run-on/unpunctuated text into beats (bug found in round 1); catalogue names also masked in queries; tighter High/Medium rules. Tuned on the same 40 pitches.
- v1 on fresh data (round 3): failed to generalise (see raw_outputs/round3_*).
- v2 (shipped, round 4): sentence-initial words are no longer treated as names unless they recur; new lexicon-free `beat_alignment` feature; logistic combination of six features
  (storydna/calibration.json, fitted by tools/calibrate.py on 54 dev pitches, leave-one-out CV reported); tiers High >= 0.80, Medium >= 0.30.
- After the round-4 freeze, only presentation/safety changes: trimmed weak evidence rows, language warning for Roman-script Hindi, Streamlit demo link. Scoring files unchanged (hashes in data/benchmark/FROZEN.sha256).
- Language layer (added after round 4; scorer files untouched): `lang.py` (script + function-word detection), `glossary_hi.py` + `translate.py` (offline Hindi/Hinglish gloss, optional model translation with validation, catalogue translation), 'Not assessed' for unsupported languages. Evaluated once on three frozen Hindi/Hinglish sets (`raw_outputs/multilingual_layer/`); hashes of the evaluated files are in `data/benchmark/FROZEN.sha256`.
