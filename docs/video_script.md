# 3-minute walkthrough - say it in your own words (about 450 words total)

**0:00-0:20 Why.** "Kuku releases well over a hundred microdramas a month, and viewers and analysts say repetitive storylines hurt retention. Before a pitch is produced, an editor can't remember every earlier plot. StoryDNA answers: is this pitch the same *story* as one we've made, or just the same *genre*?" (Show page 1 of the PDF.)

**0:20-0:45 Setup.** Open the app (`streamlit run app/streamlit_app.py` or your hosted link). "The catalogue is 30 story cards I generated with AI for this test, not Kuku's data. I didn't use the confidential pack." Point at the sidebar: "30 stories loaded; I can upload my own CSV."

**0:45-1:25 Live run.** Pick *Sample: hotel heiress*, press **Compare stories**. "Top match is The Intern Who Owns the Floor, High. Look at the table: distinctive shared events versus generic tropes. Open the card: the matching beats sit side by side, same order. Below it, the beats that *differ*." Optionally paste a brand-new pitch you typed during the video.

**1:25-1:45 (optional) Hindi.** Pick *Sample: Hindi (Devanagari) pitch*, Compare. "It detected Hindi, converted it with a small offline glossary, and still found the right story. Other languages need a model."

**1:45-2:00 False alarm.** Pick *hidden-wealth tutor*. "Same trope, different plot. It is not High. Each card has my decision buttons; the tool never auto-rejects."

**2:00-2:30 Evidence.** Open `raw_outputs/` and `evaluation_summary_all_rounds.csv`. "Round 3 is my honest failure: tuned on my own set, 100%, then on 14 fresh pitches it hit 6 of 7 with two false Highs. I rebuilt it and ran a final test once: 7 of 7 overlaps, 0 of 9 false Highs. n is tiny and plain TF-IDF also does well, so I don't oversell it."

**2:30-3:00 Limits and swap.** "Model is optional and swappable via three env vars; I only tested it with mocks. English only: Hinglish gets a warning. Next step: Kuku's catalogue and editor-labelled pairs."

Don't show the Kuku pack. Record at 1080p; keep the browser zoomed to ~110%.
