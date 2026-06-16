#!/usr/bin/env python3
"""CLI generator sistem CAT TOEFL dari file .docx materi/evaluasi.

Subcommands:
  parse            ekstraksi verbatim dari .docx -> JSON
  build-materi      gabungkan parsed JSON + answers + page-config -> materi HTML
  build-evaluation  gabungkan parsed JSON + answers + page-config -> evaluasi HTML (CAT)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cat_lib import docx_parser, renderer, verify


def cmd_parse(args):
    data = docx_parser.parse_docx(args.docx)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    n_exercises = sum(len(s["exercises"]) for s in data["skills"])
    print(f"OK: {len(data['skills'])} skill block(s), {n_exercises} soal -> {out_path}")


def cmd_build_materi(args):
    html = renderer.build_materi_html(args.data, args.answers, args.config)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"OK: materi HTML ditulis ke {args.out}")
    if args.verify:
        verify.verify_materi(args.data, args.out)


def cmd_build_evaluation(args):
    html = renderer.build_evaluation_html(args.data, args.answers, args.config)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"OK: evaluation HTML ditulis ke {args.out}")
    if args.verify:
        verify.verify_evaluation(args.data, args.out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="ekstraksi verbatim dari .docx -> JSON")
    p_parse.add_argument("--docx", required=True)
    p_parse.add_argument("--out", required=True)
    p_parse.set_defaults(func=cmd_parse)

    p_materi = sub.add_parser("build-materi", help="generate halaman materi & latihan")
    p_materi.add_argument("--data", required=True, help="path *.parsed.json")
    p_materi.add_argument("--answers", required=True, help="path *.answers.json")
    p_materi.add_argument("--config", required=True, help="path page_config*.json")
    p_materi.add_argument("--out", required=True)
    p_materi.add_argument("--verify", action="store_true")
    p_materi.set_defaults(func=cmd_build_materi)

    p_eval = sub.add_parser("build-evaluation", help="generate halaman evaluasi (CAT)")
    p_eval.add_argument("--data", required=True, help="path *.parsed.json")
    p_eval.add_argument("--answers", required=True, help="path *.answers.json")
    p_eval.add_argument("--config", required=True, help="path page_config*.json")
    p_eval.add_argument("--out", required=True)
    p_eval.add_argument("--verify", action="store_true")
    p_eval.set_defaults(func=cmd_build_evaluation)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
