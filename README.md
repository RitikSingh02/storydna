# StoryDNA - cross-catalogue narrative redundancy review for microdrama pitches
Kuku AI Generalist Assignment, **Problem 3**. Given a new pitch, StoryDNA ranks the most similar stories in a catalogue and shows
*evidence*: matching beats in order, generic-trope events separated from distinctive ones, and the beats that differ.
It is an **editorial triage aid, not a plagiarism or legal tool**; a human always decides.

## Run (Python 3.10+; tested on 3.13)
```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py                 # UI (add ?demo=1 to the URL for a pre-filled demo)
python -m storydna compare --pitch samples/unseen_pitch_01.txt --out out/   # CLI -> report.json/.csv/.md
python -m pytest -q tests                          # 57 tests (needs: pip install -r requirements-dev.txt)
python run_eval.py --round my_run --queries data/benchmark/queries_round4_test.json   # reproduce an evaluation
```
No API key is needed. Network is only needed to `pip install`.

## Use your own catalogue / a new pitch
Catalogue: `.json` list or `.csv` with columns `story_id,title,synopsis` (optional `genre,source_url,provenance,language`).
Pitch: any `.txt` of 4-12 event-by-event sentences. Both can be uploaded in the app; no code changes.

## Make a pitch more original (new)
For every High/Medium match the report adds a `differentiation` block and the site shows it in the **Make it more original** tab:
a what-if score (the scorer re-run with the overlapping beats removed, per beat and together), beat-by-beat writer prompts chosen from the
events that actually matched, and bigger story levers (change who/where/what is at stake/the villain's reason/the ending). Optional:
`--llm-ideas` (or the sidebar box) adds model-written angles, each validated (length, beat numbers, not copied from the existing story).
These are prompts for writers, not instructions; the what-if is an estimate, so re-run the rewrite. `--no-suggest` turns it off. Code: `storydna/suggest.py`.

## Languages
| Input | What happens | Needs a model? |
|---|---|---|
| English | compared directly | no |
| Hindi (Devanagari) and Hinglish (Hindi in Roman letters) | detected, converted to English with an offline glossary (~400 word forms, verb-fronting), compared, evidence shown in your original sentences | no (a model gives better results) |
| Any other language (Spanish, Tamil, Arabic, Chinese, ...) | detected; translated by the model if you tick *Translate with model* / pass `--llm-translate`; otherwise the report says **"Not assessed"** instead of a misleading Low | yes |
The catalogue can also contain non-English cards (set `language` or just write them in Hindi): they are translated the same way and the original sentence is kept next to the English one. The scoring code itself is unchanged and still sees English only.
Measured: 22 frozen Hindi/Hinglish runs, right story ranked 1st and High for 16/16 true overlaps (8/16 with the layer off), 0/6 false Highs. The glossary and the test pitches have the same AI author, so treat this as optimistic. Model translation is mock-tested only.

## Optional model layer (swappable, off by default)
```bash
export STORYDNA_PROVIDER=anthropic          # or openai / groq / openrouter / gemini (OpenAI-compatible)
export STORYDNA_MODEL=<model name>          # required: the model is configuration, not code
export STORYDNA_API_KEY=<key>
export STORYDNA_BASE_URL=<for OpenAI-compatible endpoints>
python -m storydna compare --pitch my.txt --llm [--llm-extract] [--llm-translate]
```
Prompts: `storydna/prompts/*.txt`. Every answer is validated (`storydna/llm.py`). **The live HTTP adapters were not tested against a real API**
(mock models only, including one that fabricates evidence); first run with your key may need small fixes.

## Layout
`storydna/` package (textproc, events, matcher, report, suggest, lang, translate, llm, cli) | `app/` Streamlit site (`streamlit_app.py` pages, `theme.py` look and colours) | `data/` catalogue + frozen benchmarks + hashes |
`tools/` calibration, robustness, scale, summaries | `raw_outputs/` all unedited run outputs (see its README) | `docs/` solution PDF, video script | `tests/`.

## Deploy
Streamlit Community Cloud: push to GitHub -> New app -> main file `app/streamlit_app.py`. Hugging Face Spaces: Streamlit SDK, same entry file.

## Honest limits
Offline language support is limited to Hindi/Hinglish (a few hundred words; glossed text is crude, and a long tail of words is unrecognised - the report lists them). Other languages need a model that I have not tested live. Catalogue and test pitches are AI-written (30 cards), so results are optimistic and say
nothing about Kuku's real catalogue. Event lexicon is hand-written (31 events). Plain TF-IDF is a strong baseline on this corpus. Synopsis-level input only.
