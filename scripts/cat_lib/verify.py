"""Safety-net: re-extract data soal dari HTML hasil generate, lalu cocokkan
balik (karakter demi karakter) terhadap hasil parse docx asli. Lapisan
tambahan di atas jaminan arsitektur (data JS hanya pernah diserialize dari
string yang sama, tidak pernah diketik ulang manual).
"""
import json
import re
import sys


def _extract_js_array(html, var_name):
    pattern = re.compile(r"const " + re.escape(var_name) + r" = (\[.*?\n\]);", re.DOTALL)
    m = pattern.search(html)
    if not m:
        raise ValueError(f"Tidak menemukan const {var_name} di HTML hasil generate")
    return json.loads(m.group(1))


def _flatten_parsed_exercises(parsed):
    out = []
    for skill in parsed["skills"]:
        out.extend(skill["exercises"])
    return out


def _compare(expected, actual_questions, label):
    if len(expected) != len(actual_questions):
        print(f"MISMATCH [{label}]: jumlah soal beda ({len(expected)} vs {len(actual_questions)})")
        return False
    ok = True
    for i, (exp, act) in enumerate(zip(expected, actual_questions)):
        if exp["text"] != act["text"]:
            print(f"MISMATCH [{label}] soal #{i+1} text:\n  expected={exp['text']!r}\n  actual  ={act['text']!r}")
            ok = False
        if exp["options"] != act["options"]:
            print(f"MISMATCH [{label}] soal #{i+1} options:\n  expected={exp['options']!r}\n  actual  ={act['options']!r}")
            ok = False
    return ok


def verify_evaluation(data_path, html_path):
    parsed = json.loads(open(data_path, encoding="utf-8").read())
    html = open(html_path, encoding="utf-8").read()
    expected = _flatten_parsed_exercises(parsed)
    actual = _extract_js_array(html, "QUESTIONS")
    ok = _compare(expected, actual, "evaluation")
    if ok:
        print(f"VERIFY OK: {len(expected)} soal di {html_path} cocok 100% dengan hasil parse docx.")
    else:
        sys.exit(1)


def verify_materi(data_path, html_path):
    parsed = json.loads(open(data_path, encoding="utf-8").read())
    html = open(html_path, encoding="utf-8").read()
    all_ok = True
    for skill in parsed["skills"]:
        var_name = f"SKILL{skill['number']}"
        actual = _extract_js_array(html, var_name)
        ok = _compare(skill["exercises"], actual, var_name)
        all_ok = all_ok and ok
    if all_ok:
        total = sum(len(s["exercises"]) for s in parsed["skills"])
        print(f"VERIFY OK: {total} soal di {html_path} cocok 100% dengan hasil parse docx.")
    else:
        sys.exit(1)
