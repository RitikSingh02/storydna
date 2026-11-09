# StoryDNA: what each file is, what to push, how to put it on the web

## 1. File map (push everything below unless it says "optional")
| Path | What it is | Needed to run the website? |
|---|---|---|
| `app/streamlit_app.py` | **The website.** One Streamlit page: upload/select catalogue, paste or upload a pitch, compare, read evidence, record decisions, download reports | **yes (entry file)** |
| `app/theme.py` | The look of the site: all colours, fonts and card styles (change colours at the top of the CSS to re-brand) | **yes** |
| `storydna/` | The engine (a Python package). `suggest.py` the "make it more original" ideas, `textproc.py` sentence/name/stem handling, `events.py` 31 story-event rules, `matcher.py` scoring, `calibration.json` fitted weights, `report.py` report + validation + CSV/Markdown, `catalogue.py` loading/validation, `lang.py` + `translate.py` + `glossary_hi.py` language layer, `llm.py` + `prompts/` optional swappable model, `cli.py` command line | **yes** |
| `data/catalogue.json` | The 30 AI-written story cards the site compares against (default catalogue) | **yes** |
| `samples/` | Pitches for the sample dropdown (English, Hindi, Hinglish, Spanish demo) | **yes** (the app reads them at start) |
| `requirements.txt` | Libraries the site needs (numpy, scikit-learn, streamlit) | **yes** |
| `.streamlit/config.toml` | Dark theme colours, usage stats off, 5 MB upload cap | recommended |
| `README.md` | How to run, how to use your own catalogue, limits | for reviewers |
| `raw_outputs/` | Unedited outputs of every evaluation run (brief requires this) + its README | for reviewers |
| `docs/StoryDNA_Solution.pdf` | The 2-page solution document you submit | for reviewers |
| `docs/video_script.md`, `docs/make_solution_pdf.py`, `docs/img/` | video notes, PDF builder, screenshots | optional |
| `data/benchmark/` | Frozen test pitches + `FROZEN.sha256` (proves they were fixed before the runs) | for reviewers |
| `tests/`, `tools/`, `run_eval.py` | 57 tests, calibration/robustness/scale/multilingual scripts, the benchmark runner | for reviewers |
| `requirements-dev.txt`, `CHANGELOG.md`, `DEPLOY.md`, `.gitignore` | dev dependencies, version notes, this file, ignore rules | optional |

**Never push:** Kuku's input pack (confidential), any API key, `.env`, `.streamlit/secrets.toml` (all covered by `.gitignore`; the pack is not in this folder anyway).

## 2. Push to GitHub (one time)
1. Create an empty repo on github.com (name e.g. `storydna`, no README/licence/gitignore; public or private; if private, give the Kuku reviewer access).
2. In a terminal, inside the unzipped project folder:
```bash
git init -b main
git add .
git status            # check: no .env, no keys, no Kuku files
git commit -m "StoryDNA: cross-catalogue narrative redundancy reviewer (Kuku Problem 3)"
git remote add origin https://github.com/<your-username>/storydna.git
git push -u origin main
```
3. Later changes: `git add . && git commit -m "what changed" && git push`.

## 3. Put the website on the internet (free, ~5 minutes): Streamlit Community Cloud
1. Go to share.streamlit.io, sign in with GitHub.
2. **Create app -> Deploy a public app from GitHub**: repository `<you>/storydna`, branch `main`, **main file path `app/streamlit_app.py`**.
3. *Advanced settings*: Python 3.11, 3.12 or 3.13. Click **Deploy**. First build takes 2-4 minutes; you get `https://<name>.streamlit.app`.
4. Test the link: open `https://<name>.streamlit.app/?demo=1` (pre-filled hotel-heiress demo, shows results immediately), then the Hindi sample.
5. Put the URL (and the GitHub URL) in the submission form.
Alternative: Hugging Face Spaces -> New Space -> SDK **Streamlit** -> upload the repo; set the app file to `app/streamlit_app.py`.

**Keep the public site key-free.** The site works with no API key (offline matcher + Hindi/Hinglish glossary). If you add model keys as app *Secrets* (Settings -> Secrets: `STORYDNA_PROVIDER="anthropic"`, `STORYDNA_MODEL="..."`, `STORYDNA_API_KEY="..."`; top-level secrets become environment variables), then anyone with the link can spend your credits by ticking the model boxes. Only do that on a private/app-restricted deployment, for the interview demo, and rotate the key afterwards. The live model adapters are untested.

## 4. Run locally instead (also works for the interview)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest -q tests                                # expect 57 passed
streamlit run app/streamlit_app.py                       # opens http://localhost:8501
python -m storydna compare --pitch samples/unseen_pitch_01.txt --out out/
```

## 5. What the website contains
* **Header + caveat** - "editorial triage signal, not a plagiarism or legal verdict".
* **Sidebar** - catalogue uploader (.json/.csv; default = 30 bundled cards, shows how many stories are loaded), number of candidates (3-10), "store only a hash of the pitch" switch, two optional model checkboxes (double-check the top 3; translate non-English text).
* **Pitch box** - sample dropdown (hotel heiress, oil dumping = original, hidden-wealth tutor = same trope/different plot, Hindi, Hinglish, Spanish = "not assessed" demo), file upload for a .txt pitch, free text, optional title, **Compare stories** button.
* **After Compare**
  - language banner (when Hindi/Hinglish was converted) + expander with the English text actually compared;
  - warnings (short pitch, unreadable language, unrecognised words) and a red "low reliability" box when needed;
  - ranked table: story, review priority (High / Medium / Low / Not assessed), score, distinctive shared events, generic tropes shared;
  - a verdict card (closest story, tier badge, score gauge) and four stat tiles;
  - one expander per candidate with three tabs: **Evidence** (matching beats side by side, trope-only flags, beats that differ, optional model verdict), **Make it more original** (what-if score, beat-level ideas, story levers, optional model angles; only for High/Medium) and **Your review** (needs review / false alarm / safe to proceed);
  - downloads: full report (JSON, with run id, catalogue fingerprint, scores, evidence, decisions) and summary (CSV).
* **No database, no login, nothing stored on the server** - each visitor's session lives in their browser tab; the demo link is `?demo=1`.
