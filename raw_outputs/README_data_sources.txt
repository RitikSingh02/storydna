StoryDNA raw outputs  (all produced by running the code in this repo; nothing edited by hand)
==========================================================================================

DATA PROVENANCE
- data/catalogue.json: 30 story cards WRITTEN BY AN AI ASSISTANT (Claude) for this assignment, imitating common
  microdrama patterns. They are NOT real shows and nothing was scraped. provenance field says so on every card.
- Kuku's confidential 50-episode input pack was NOT used and is NOT in this repo.
- Test pitches (data/benchmark/*.json) were written by the same assistant, so scores are optimistic.

HOW EACH FOLDER WAS PRODUCED  (python run_eval.py --round <name> --queries <file>)
  round1_apriori/                 40 pitches, thresholds set before seeing any result. Early scorer version.
                                  Exposed: unpunctuated text collapsed to one beat; Medium tier far too loose.
  round2_tuned_in_sample/         same 40 pitches after bug fix + tighter rules. IN-SAMPLE, proves nothing.
  round3_fresh_heldout_like/      14 NEW pitches, new vocabulary, run ONCE on the round-2 tool. Showed overfitting
                                  (hit@1 6/7, 2 false High). Kept as-is on purpose.
  (then) name-detection fix + beat-alignment feature + calibration; see calibration_loqo_crossval.txt
  round4_final_test/              16 NEW pitches, scorer files hash-frozen first (data/benchmark/FROZEN.sha256), run ONCE.
  dev_set_A/B_shipped_tool_IN_SAMPLE/   the shipped tool on the dev sets (used for calibration, so in-sample).
  robustness/                     16 odd/hostile inputs incl. errors, Hinglish, Hindi, emoji, 300k chars, broken CSV/JSON.
  unseen_pitch_cli_runs/          the CLI run on two pitches that are not in the catalogue (the "interview input" path).
  scale_test.csv                  timing/memory at 30 -> 10,000 SYNTHETIC cards (cost only, not accuracy).
  calibration_loqo_crossval.txt   leave-one-query-out cross-validation on the 54 dev pitches.
  multilingual_layer/run1_first_and_only/
                                  22 Hindi/Hinglish pitches (3 frozen sets, written BEFORE the language layer) run twice:
                                  off/ = old English-only behaviour, auto/ = with the language layer. results.csv +
                                  summary.json. Re-running gives identical numbers (checked). Same AI author as the glossary.
  evaluation_summary_all_rounds.csv   every round's metrics side by side.

Rounds 1-3 were produced by earlier scorer versions that are not shipped; the changes between versions are
listed in CHANGELOG.md. Files per round: run_NNN_<qid>.json (full report), evaluation_results.csv,
test_case_manifest.csv, metrics.json.
