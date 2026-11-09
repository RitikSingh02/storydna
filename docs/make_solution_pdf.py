#!/usr/bin/env python3
"""Builds StoryDNA_Solution.pdf (2 pages). All numbers are copied from raw_outputs/ (see evaluation_summary_all_rounds.csv)."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepInFrame
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.lib.enums import TA_LEFT

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "StoryDNA_Solution.pdf"
INK, ACC, GREY = colors.HexColor("#1b1b1f"), colors.HexColor("#b3263e"), colors.HexColor("#5b5b66")
B = ParagraphStyle("b", fontName="Helvetica", fontSize=8.3, leading=10.3, textColor=INK, alignment=TA_LEFT, spaceAfter=2.2)
H = ParagraphStyle("h", parent=B, fontName="Helvetica-Bold", fontSize=9.6, leading=11.5, textColor=ACC, spaceBefore=4.5, spaceAfter=2)
T = ParagraphStyle("t", parent=B, fontName="Helvetica-Bold", fontSize=14.5, leading=17, spaceAfter=1)
S = ParagraphStyle("s", parent=B, fontSize=7.9, textColor=GREY, spaceAfter=3)
BL = ParagraphStyle("bl", parent=B, leftIndent=8, bulletIndent=0, spaceAfter=1.4)
C = ParagraphStyle("c", parent=B, fontSize=7.2, leading=8.6, spaceAfter=0)
CB = ParagraphStyle("cb", parent=C, fontName="Helvetica-Bold")
SM = ParagraphStyle("sm", parent=B, fontSize=7, leading=8.4, textColor=GREY)


def p(t, s=B): return Paragraph(t, s)
def bl(t): return Paragraph(t, BL, bulletText="•")


def arch():
    d = Drawing(520, 76)
    boxes = [("New pitch\n(text / .txt)", 0, "#e8eefc"), ("Beats + normalise\nnames out, stems,\nsynonyms", 88, "#e8eefc"),
             ("Retrieve\nTF-IDF top-50", 183, "#e8eefc"), ("Features per pair\nlexical, rare-detail,\nbeat-align, events", 262, "#fbe9ec"),
             ("Calibrated score\nHigh ≥.80  Med ≥.30", 366, "#fbe9ec"), ("Evidence card\n+ human decision", 455, "#e6f4e8")]
    for txt, x, col in boxes:
        w = {0: 76, 88: 84, 183: 70, 262: 94, 366: 80, 455: 62}[x]
        d.add(Rect(x, 22, w, 44, rx=4, ry=4, fillColor=colors.HexColor(col), strokeColor=colors.HexColor("#888"), strokeWidth=.6))
        for i, line in enumerate(txt.split("\n")):
            d.add(String(x + w / 2, 54 - i * 9.5, line, fontName="Helvetica", fontSize=6.3, textAnchor="middle"))
    for a, b in [(76, 88), (172, 183), (253, 262), (356, 366), (446, 455)]:
        d.add(Line(a, 44, b, 44, strokeColor=colors.HexColor("#555"), strokeWidth=1))
    d.add(Rect(262, 4, 184, 13, rx=3, ry=3, fillColor=colors.HexColor("#fff7d6"), strokeColor=colors.HexColor("#c9a800"), strokeWidth=.5))
    d.add(String(354, 8, "optional: model re-checks top 3 (one adapter, output validated)", fontName="Helvetica-Oblique", fontSize=6, textAnchor="middle"))
    return d


def tbl(data, widths, header=True, fs=7.2):
    rows = [[Paragraph(str(c), CB if (header and i == 0) else C) for c in r] for i, r in enumerate(data)]
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#bbb")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0e3e6")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
                           ("LEFTPADDING", (0, 0), (-1, -1), 2.5), ("RIGHTPADDING", (0, 0), (-1, -1), 2.5)]))
    return t


def build():
    W = A4[0] - 2.4 * cm
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=1.2 * cm, rightMargin=1.2 * cm, topMargin=1.0 * cm, bottomMargin=0.9 * cm,
                            title="StoryDNA - Kuku AI Generalist Assignment (Problem 3)", author="Uday Rahul Ingle")
    f = []
    f += [p("StoryDNA — catch “the same story under a new name” before a microdrama is produced", T),
          p("Kuku AI Generalist Assignment · <b>Problem 3 (own problem)</b> · Uday Rahul Ingle · Roll 230102100 · IIT Guwahati", S)]

    f.append(p("1. Problem, who has it, how I know", H))
    f.append(p("<b>User &amp; step:</b> a creative-development editor doing the <i>first review of a new pitch, before any episode is written or generated</i>. "
               "<b>Bottleneck:</b> Kuku reportedly releases 150–250 original shows a month (Indian Television; Hollywood Reporter India). Nobody can remember every earlier plot, and with AI generation, "
               "plots drift toward the same few chains (hidden billionaire → humiliation → public reveal). The editor needs one question answered fast: "
               "<b>“Is this pitch the same <i>story</i> as something we already made, or just the same <i>genre</i>?”</b> and the evidence to check it."))
    f.append(p("<b>Evidence it is real (secondary only):</b> Redseer’s Dec-2025 India consumer research names repetitive storylines and slow refresh among the main churn drivers (via Exchange4media, Storyboard18); "
               "Meta–Ormax 2026 flags creative fatigue from repeated tropes (Exchange4media); China’s regulator told micro-drama makers to drop stock tropes (Sixth Tone, 2024). "
               "<b>What I did not do:</b> I did not interview viewers or Kuku editors, and I cannot measure Kuku’s actual redundancy rate. The claim “this matters more than Problems 1 and 2” is therefore a <b>hypothesis</b>: "
               "Problem 1 optimises marketing of a finished show, whereas a redundant premise wastes spend across every episode, but I have no Kuku numbers to prove it."))
    f.append(p("<b>Kuku already has related tech.</b> It publicly describes an “AI Storytelling Stack” (Business Standard, Sep 2026), so I assume retrieval over stories exists internally. "
               "I did not try to out-build it. I tested the narrower, checkable question: can a cheap, explainable pipeline <b>separate same-plot from same-trope and show its evidence</b>?"))

    f.append(p("2. Assumptions (the brief was silent)", H))
    for t in ["<b>A1</b> Input is a pitch/synopsis of 4–12 beats, not a full screenplay. Long scripts would first be condensed to beats (optional model step, built, tested on mocks only).",
              "<b>A2</b> The Kuku input pack is one show, so it cannot test cross-show matching, and it is confidential. <b>None of it is used or in the repo.</b>",
              "<b>A3</b> Catalogue = <b>30 original story cards written by an AI assistant for this assignment</b> (typical microdrama patterns, not real shows, no scraped text). Results say nothing about Kuku’s catalogue.",
              "<b>A4</b> Output is an <i>editorial review priority</i>, never a plagiarism or legal verdict; ideas and tropes are not protectable. A human always decides; nothing is auto-rejected. The matcher reads English; Hindi/Hinglish go through an offline glossary, other languages need a model (see failures)."]:
        f.append(bl(t))

    f.append(p("3. How it works — what is code, what is a model, where the human sits", H))
    f.append(arch())
    f.append(p("<b>Code (default, free, offline):</b> splitting into beats; masking character names so renamed copies still match; stemming and synonym folding; TF-IDF retrieval; six per-pair features "
               "(lexical cosine, rare-detail overlap, ordered beat alignment, ordered/rarity-weighted event overlap from a 31-event rule lexicon, plain TF-IDF); a small logistic combination fitted on 54 dev pitches; "
               "tiers; schema/evidence validation. <b>Model (optional, one adapter):</b> re-checks the top 3 and condenses long text. Provider and model are env-vars "
               "(Anthropic or any OpenAI-compatible endpoint), prompts are plain files, and <b>every model answer is validated</b>: cited beats must exist, claims need a reason, “same plot” with no valid evidence is downgraded to “unverified”, "
               "and a model/heuristic disagreement is flagged to the human, never silently resolved. "
               "<b>Human:</b> sees the matched beats side by side, the generic-trope events separated from distinctive ones, and the beats that differ, then marks <i>needs review / false alarm / safe</i>. High/Medium matches also get ideas for making the pitch more original (a what-if re-score, beat-level prompts); rewriting the two flagged sample beats took it from High to below High."))

    f.append(p("4. Prototype output (real run on an unseen pitch I wrote; not in the catalogue)", H))
    img = Image(str(ROOT / "docs/img/app_results_new.png"), width=9.2 * cm, height=9.2 * cm * 692 / 840)
    right = [p("The pitch is a hotel-heiress story that shares its skeleton with catalogue card <i>The Intern Who Owns the Floor</i> and a framing beat with <i>Night Shift Owner</i>. "
               "The tool returns S05 as <b>High</b> and S02 as <b>Medium</b>, labels PUBLIC_REVEAL and COMEUPPANCE as <i>trope-only</i>, and lists the beats that differ. "
               "Honest miss: the tagger did not recognise “hides her family name” as concealed identity, so one distinctive event is missing from the evidence.", B),
             p("<b>Run it again:</b> paste any new pitch, upload a .txt, or swap the catalogue for your own CSV/JSON (<font face='Courier'>story_id,title,synopsis</font>). "
               "CLI: <font face='Courier'>python -m storydna compare --pitch new.txt</font>. Exports JSON/CSV with the reviewer’s decision. About 35 ms per pitch including the what-if preview, no API key needed.", B)]
    t = Table([[img, right]], colWidths=[9.4 * cm, W - 9.4 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 0)]))
    f.append(t)
    f.append(p("<font color='#5b5b66'>Prototype, raw outputs, tests and README are in the repo submitted with this form. Page 2: how I know it works, and where it fails.</font>", SM))
    from reportlab.platypus import PageBreak
    f.append(PageBreak())

    f.append(p("5. Quality checking — what I ran, in order (raw files: <font face='Courier'>raw_outputs/</font>)", H))
    f.append(p("I wrote each test set <b>before</b> running the version it tests, hash-froze it, and kept every raw report including bad ones. Positives = a pitch whose plot matches one catalogue story "
               "(exact copy, renamed paraphrase, partial). Negatives = same genre/trope but different plot, or unrelated. “False High” = a negative rated High."))
    rows = [["Round (what changed)", "Pitches", "Positives: right story ranked #1", "Positives rated High", "Negatives rated High / Medium+", "Reading"],
            ["1 — a-priori rules", "40", "23/23 (plain TF-IDF 23/23)", "16/23 (exact 5/8, paraphrase 8/10, partial 3/5)", "0/17 / <b>15/17</b>", "Medium far too loose; punctuation-free text collapsed to one beat (bug, 3 exact copies missed)."],
            ["2 — bug fix + tighter rules, tuned on the same 40", "40", "23/23", "22/23", "0/17 / 2/17", "<b>In-sample, so proves nothing.</b>"],
            ["3 — 14 fresh pitches, new vocabulary, run once on round-2 tool", "14", "<b>6/7</b> (plain TF-IDF 7/7)", "2/5 paraphrases", "<b>2/7 false High</b> / 2/7", "<b>Overfit.</b> My hand-built event lexicon failed to generalise; plain cosine beat it (AUC .91 vs .69)."],
            ["Fix: name-detection bug (it deleted “Billionaire”, “Widow”), lexicon-free beat alignment, weights fitted with leave-one-out CV on rounds 1+3", "54 (CV)", "30/30 (hit@1 100%)", "—", "AUC overlap vs trope-only <b>1.00</b> (plain TF-IDF 0.96; fixed weights 0.94)", "Thin margin: worst non-overlap 0.64 vs weakest true overlap 0.68, so High set conservatively at 0.80."],
            ["<b>4 — final test:</b> 16 new pitches, scorer hash-frozen, run once", "16", "<b>7/7</b> (plain TF-IDF 7/7)", "<b>7/7</b>", "<b>0/9 / 2/9</b>", "Good, but n is tiny and plain TF-IDF is equally perfect here."]]
    f.append(tbl(rows, [4.2 * cm, 1.1 * cm, 3.0 * cm, 2.6 * cm, 3.1 * cm, W - 14.0 * cm]))
    f.append(p("<b>Honest reading.</b> On this small, easy corpus plain TF-IDF already finds the right story; StoryDNA’s measured gain is in <i>separating overlap from trope-only</i> (cross-validated AUC 1.00 vs 0.96) and in the evidence it prints, not in retrieval. "
               "Test sets and catalogue come from the same author (an AI assistant), so all numbers are optimistic. A real test needs Kuku’s catalogue and editor-labelled pairs.", B))

    f.append(p("Where it fails (all in the raw outputs)", H))
    for t in ["<b>Near-miss false positive:</b> an unrelated chess-championship pitch scored 0.64 (cross-validated) against the maths-olympiad card (shared “competition → final” events). Round 3 also rated a blackmail/twins trope pitch High.",
              "<b>Language:</b> at first Hinglish returned a silent Low. I then added a language layer (detection, offline Hindi/Hinglish glossary, optional model translation). On 22 frozen Hindi/Hinglish runs (16 true overlaps, 6 not) it ranked the right story first as High 16/16 (layer off: 8/16) with 0/6 false Highs, but the glossary and pitches share one AI author, so this is optimistic, and glossed text is crude. Other languages: reported “not assessed” unless a model is configured; model translation is mock-tested only.",
              "<b>Heavy paraphrase</b> (“becomes the cleaner on the late shift” for “night janitor”) relies on lexical overlap; the model step is meant for this and is <b>untested against a live API</b> (mock-tested only, incl. a mock that invents evidence).",
              "Short pitches (&lt;4 beats) and synopsis-only cards carry little structure; the tool says so in a warning. 16 malformed-input cases: 0 crashes, readable errors."]:
        f.append(bl(t))

    f.append(p("AI tools used, and where they got it wrong", H))
    f.append(p("<b>Tools:</b> Claude (Anthropic) for code, test design, research checks and drafting; scikit-learn, Streamlit. "
               "<b>Mistakes I caught:</b> (1) the first scorer the AI wrote scored 100% on the set it was tuned on and then fell apart on 14 fresh pitches (round 3), so I rebuilt it and froze a new test; "
               "(2) its name-masking silently removed real words and zeroed one story’s lexical score; (3) the research brief cited a “54 of 690 complaints” statistic I could not verify, so I left it out."))

    f.append(p("6. Scale, cost, and how a real team would know it worked", H))
    rows2 = [["Catalogue size", "30", "300", "3,000", "10,000"],
             ["Index build / median query / memory", "0.05 s / 4 ms / 171 MB", "0.3 s / 6 ms / 175 MB", "3.1 s / 8 ms / 212 MB", "10.3 s / 11 ms / 327 MB"]]
    f.append(tbl(rows2, [4.7 * cm] + [(W - 4.7 * cm) / 4] * 4))
    f.append(p("<font color='#5b5b66'>Measured on a 2-core sandbox with synthetic recombined cards: cost only, not accuracy. Retrieval stays O(N) with a 50-candidate shortlist; beyond ~100k stories, swap in a vector index. "
               "Baseline API cost is <b>zero</b>. Optional model step: top-3 × about 550 input + 200 output tokens (estimated) ≈ 2.3k tokens per pitch, i.e. tokens × the chosen provider’s rate; I did not invent a rupee figure.</font>", SM))
    f.append(p("<b>Pilot (10–20 real pitches, two weeks):</b> an editor reviews half with the old process and half with StoryDNA (order randomised). Track <b>review minutes per pitch</b>, <b>false alerts per pitch</b> (target ≤ 1), "
               "precision of High flags as judged by two editors, editor agreement with the tiers, and whether editors find the original card faster. Success = fewer minutes without missing a redundancy the editors later confirm. "
               "<b>Not claimed:</b> retention, revenue or legal-risk improvement."))
    doc.build(f)


if __name__ == "__main__":
    build()
    print("wrote", OUT)
