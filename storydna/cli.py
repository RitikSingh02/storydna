"""Command line: python -m storydna compare --pitch my_pitch.txt [--catalogue cat.json] [--out dir]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalogue import InputError, load_catalogue
from .llm import AdapterError, adapter_from_env, llm_extract_beats
from .matcher import StoryIndex
from .report import report_to_csv, report_to_markdown, review_pitch
from .translate import prepare_catalogue

DEFAULT_CATALOGUE = Path(__file__).resolve().parent.parent / "data" / "catalogue.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="storydna", description="Compare a new microdrama pitch with a story catalogue.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare", help="review one pitch")
    c.add_argument("--pitch", required=True, help="path to a .txt pitch / synopsis ('-' for stdin)")
    c.add_argument("--catalogue", default=str(DEFAULT_CATALOGUE), help="catalogue .json or .csv")
    c.add_argument("--title", default="")
    c.add_argument("--top", type=int, default=5)
    c.add_argument("--out", default="", help="folder for report.json / report.csv / report.md")
    c.add_argument("--llm", action="store_true", help="use the model from STORYDNA_PROVIDER/MODEL/API_KEY for the top candidates")
    c.add_argument("--llm-extract", action="store_true", help="also condense a long pitch into beats with the model first")
    c.add_argument("--llm-translate", action="store_true", help="let the model translate non-English pitch/catalogue text (any language). Without it, only Hindi/Hinglish is handled (offline glossary)")
    c.add_argument("--translate", choices=["auto", "off"], default="auto", help="off = old English-only behaviour")
    c.add_argument("--no-suggest", action="store_true", help="skip the 'how to make it more original' suggestions")
    c.add_argument("--llm-ideas", action="store_true", help="also ask the model for fresh angles on High/Medium candidates")
    c.add_argument("--redact-input", action="store_true", help="store only a hash of the pitch in the report")
    a = ap.parse_args(argv)

    try:
        text = sys.stdin.read() if a.pitch == "-" else Path(a.pitch).read_text(encoding="utf-8", errors="replace")
        adapter = adapter_from_env() if (a.llm or a.llm_extract or a.llm_translate or a.llm_ideas) else None
        cards, cat_notes = prepare_catalogue(load_catalogue(a.catalogue), adapter if a.llm_translate else None, mode=a.translate)
        for n in cat_notes:
            print("catalogue note: " + n, file=sys.stderr)
        index = StoryIndex(cards)
        if a.llm_extract:
            beats = llm_extract_beats(text, adapter)
            text = " ".join(beats)
        rep = review_pitch(index, text, query_id=Path(a.pitch).stem if a.pitch != "-" else "stdin",
                           title=a.title, top_k=a.top, adapter=adapter, redact_input=a.redact_input,
                           translate=a.translate, translate_with_model=a.llm_translate,
                           suggest=not a.no_suggest, suggest_with_model=a.llm_ideas)
    except (InputError, AdapterError, FileNotFoundError, ValueError) as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps(rep, indent=2))
        (out / "report.csv").write_text(report_to_csv(rep))
        (out / "report.md").write_text(report_to_markdown(rep))
        print("wrote %s" % out)
    print(report_to_markdown(rep))
    return 0 if rep["validation"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
