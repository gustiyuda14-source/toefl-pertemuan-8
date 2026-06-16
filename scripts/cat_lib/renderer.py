"""Gabungkan hasil parse docx + answer key + page-config jadi HTML akhir.

Strategi: index.html & materi.html yang sudah ada dipakai LANGSUNG sebagai
template sumber (CSS & JS scaffold disalin verbatim via baca-file, bukan
ditulis ulang manual) -- hanya bagian yang memang spesifik-konten (judul,
landing copy, data soal JS, blok materi per skill) yang disubstitusi via
regex pada anchor yang stabil (id elemen / nama variabel JS), bukan pada
teks skill-4/5 yang akan berubah-ubah.
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = Path(__file__).resolve().parent / "_template"
INDEX_TEMPLATE_PATH = TEMPLATE_DIR / "index_base.html"
MATERI_TEMPLATE_PATH = TEMPLATE_DIR / "materi_base.html"

TYPE_TO_SECTION = {"ci": "A", "err": "B", "mcq": "C"}


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _normalize(s):
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("\xa0", " ")
    s = re.sub(r"\([A-D]\)", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.lower().strip()


def _merge_exercises(parsed_skills, answers):
    """Gabungkan exercises (teks verbatim dari parser) dengan answers (sejajar index)."""
    merged = []
    ai = 0
    for skill in parsed_skills:
        for ex in skill["exercises"]:
            if ai >= len(answers):
                raise ValueError(f"Answer key kurang: butuh entri ke-{ai} untuk soal {ex['text']!r}")
            ans = answers[ai]
            ref = ans.get("ref", "")
            if ref:
                norm_ref_prefix = _normalize(ref)[:20]
                if norm_ref_prefix not in _normalize(ex["text"]):
                    raise ValueError(
                        f"Answer key tidak sejajar di index {ai}:\n  ref   = {ref!r}\n  soal  = {ex['text']!r}"
                    )
            merged.append({
                "section": TYPE_TO_SECTION[ex["type"]],
                "type": ex["type"],
                "text": ex["text"],
                "options": ex["options"],
                "answer": ans["answer"],
                "expl": ans["expl"],
                "flagged": bool(ans.get("flagged", False)),
            })
            ai += 1
    if ai != len(answers):
        raise ValueError(f"Jumlah soal hasil parse ({ai}) != jumlah entri answer key ({len(answers)})")
    return merged


def _replace_once(pattern, repl_text, text, flags=0):
    new_text, n = re.subn(pattern, lambda m: repl_text, text, count=1, flags=flags)
    if n == 0:
        raise ValueError(f"Anchor tidak ditemukan di template: {pattern!r}")
    return new_text


# ------------------------------------------------------------------ EVALUATION

def _build_landing_section(config, total_soal):
    return f'''<section id="screen-landing">
    <div class="hero">
      <img src="assets/ipdn-banner.jpg" alt="Kampus IPDN">
      <div class="hero-cap">
        <span class="tag">D Ajiks Akademi</span>
        <h1>{config["eval_hero_title"]}</h1>
      </div>
    </div>
    <div class="card">
      <h1>{config["eval_h1"]}</h1>
      <p class="sub">{config["eval_sub"]}</p>
      <div class="stats">
        <div class="stat"><b>{total_soal}</b><span>Total Soal</span></div>
        <div class="stat"><b>{config["stat_skills"]}</b><span>Skill Diuji</span></div>
        <div class="stat"><b>{config["duration_minutes"]}'</b><span>Durasi</span></div>
      </div>
      <p style="color:var(--muted)">{config["eval_intro"]}</p>
      <label for="nama">Nama Peserta</label>
      <input type="text" id="nama" placeholder="Tulis nama kamu di sini..." autocomplete="off">
      <div class="err" id="nameErr"></div>
      <div class="btn-row">
        <button class="btn btn-primary" onclick="startTest()">Mulai Tes</button>
        <a class="btn btn-ghost" href="{config["materi_href"]}">Pelajari Materi Dulu</a>
      </div>
    </div>
    <footer>{config["footer_eval"]}</footer>
  </section>'''


def build_evaluation_html(data_path, answers_path, config_path):
    parsed = _load_json(data_path)
    answers = _load_json(answers_path)
    config = _load_json(config_path)
    questions = _merge_exercises(parsed["skills"], answers)

    html = INDEX_TEMPLATE_PATH.read_text(encoding="utf-8")

    html = _replace_once(r"<title>.*?</title>", f'<title>{config["eval_title"]}</title>', html)
    html = _replace_once(
        r'<section id="screen-landing">.*?</section>',
        _build_landing_section(config, len(questions)),
        html, flags=re.DOTALL,
    )
    questions_js = "const QUESTIONS = " + json.dumps(questions, ensure_ascii=False, indent=2) + ";"
    html = _replace_once(r"const QUESTIONS = \[.*?\n\];", questions_js, html, flags=re.DOTALL)

    section_names_js = "const SECTION_NAMES = " + json.dumps(config["section_names"], ensure_ascii=False) + ";"
    html = _replace_once(r"const SECTION_NAMES = \{.*?\};", section_names_js, html)

    groups_literal = "{ " + ", ".join(f"{k}:{{c:0,t:0}}" for k in config["section_names"]) + " }"
    html = _replace_once(r"const groups = \{.*?\};", f"const groups = {groups_literal};", html)

    duration_seconds = config["duration_minutes"] * 60
    html = re.sub(r"\b20\*60\b", str(duration_seconds), html)

    badge_old = '<div class="qn">SOAL ${i+1} • ${SECTION_NAMES[q.section]} ${statusPill}</div>'
    badge_new = (
        '<div class="qn">SOAL ${i+1} • ${SECTION_NAMES[q.section]} ${statusPill}'
        '${q.flagged ? \' <span class="badge">perlu verifikasi</span>\' : \'\'}</div>'
    )
    if badge_old in html:
        html = html.replace(badge_old, badge_new)

    return html


# ----------------------------------------------------------------------- MATERI

def _theory_html(theory_items):
    """Render daftar paragraf teori verbatim jadi HTML, mode formula/contoh dideteksi dari tag label."""
    mode = "intro"
    parts = []
    for item in theory_items:
        text = item["text"]
        if item["tag"] == "label":
            if re.match(r"^Contoh\b", text, re.IGNORECASE):
                mode = "examples"
                parts.append('<p style="color:var(--accent);font-weight:600;margin-top:14px">Contoh:</p>')
                continue
            if re.match(r"^(Rumus|Pola)\b", text, re.IGNORECASE):
                mode = "formula"
                parts.append(f'<div class="formula">{text}</div>')
                continue
            mode = "intro"
            parts.append(f"<p>{text}</p>")
            continue
        if mode == "examples":
            parts.append(f'<div class="ex">{text}</div>')
        elif mode == "formula":
            parts.append(f'<div class="formula">{text}</div>')
        else:
            parts.append(f"<p>{text}</p>")
    return "\n    ".join(parts)


def _skill_block_html(skill, config):
    title_case = skill["title"].title()
    return f'''  <!-- ===================== SKILL {skill["number"]} ===================== -->
  <div class="skill-head"><span class="k">SKILL {skill["number"]}</span> — {title_case}</div>

  <div class="card">
    <h3>{title_case}</h3>
    {_theory_html(skill["theory"])}
  </div>

  <h3 style="margin:24px 0 14px;color:var(--accent)">\U0001F4DD Latihan Interaktif — Skill {skill["number"]}</h3>
  <div id="ex-skill{skill["number"]}"></div>
'''


def _build_materi_body(parsed, config):
    skills = parsed["skills"]
    blocks = "\n".join(_skill_block_html(s, config) for s in skills)
    return f'''
  <div class="navbar">
    <a class="btn btn-ghost" href="{config["index_href"]}">← Kembali ke Tes</a>
    <a class="btn btn-primary" href="{config["index_href"]}">Mulai Tes →</a>
  </div>

  <div class="hero">
    <img src="assets/ipdn-banner.jpg" alt="Kampus IPDN">
    <div class="hero-cap">
      <span class="tag">Materi Belajar</span>
      <h1>{config["materi_hero_title"]}</h1>
    </div>
  </div>

  <h1>{config["materi_h1"]}</h1>
  <p class="sub">{config["materi_sub"]}</p>

{blocks}
  <div class="navbar" style="margin-top:30px">
    <a class="btn btn-ghost" href="{config["index_href"]}">← Kembali ke Tes</a>
    <a class="btn btn-primary" href="{config["index_href"]}">Siap! Mulai Tes →</a>
  </div>

  <footer>{config["footer_materi"]}</footer>
'''


def _build_materi_script_data(parsed, answers):
    """Bangun blok `const SKILLn = [...]` + panggilan renderExercises, sejajar dengan urutan exercises."""
    ai = 0
    decls = []
    calls = []
    for skill in parsed["skills"]:
        items = []
        for ex in skill["exercises"]:
            ans = answers[ai]
            ref = ans.get("ref", "")
            if ref and _normalize(ref)[:20] not in _normalize(ex["text"]):
                raise ValueError(
                    f"Answer key tidak sejajar di index {ai}:\n  ref  = {ref!r}\n  soal = {ex['text']!r}"
                )
            entry = {"text": ex["text"], "options": ex["options"], "answer": ans["answer"], "expl": ans["expl"]}
            if ans.get("flagged"):
                entry["flagged"] = True
            items.append(entry)
            ai += 1
        var_name = f"SKILL{skill['number']}"
        decls.append(f"const {var_name} = " + json.dumps(items, ensure_ascii=False, indent=2) + ";")
        calls.append(f'renderExercises("ex-skill{skill["number"]}", {var_name}, "s{skill["number"]}");')
    if ai != len(answers):
        raise ValueError(f"Jumlah soal hasil parse ({ai}) != jumlah entri answer key ({len(answers)})")
    return "\n\n".join(decls), "\n".join(calls)


def build_materi_html(data_path, answers_path, config_path):
    parsed = _load_json(data_path)
    answers = _load_json(answers_path)
    config = _load_json(config_path)

    html = MATERI_TEMPLATE_PATH.read_text(encoding="utf-8")

    html = _replace_once(r"<title>.*?</title>", f'<title>{config["materi_title"]}</title>', html)
    html = html.replace('href="index.html"', f'href="{config["index_href"]}"')

    body = _build_materi_body(parsed, config)
    html, n = re.subn(
        r'(<div class="wrap">\n).*?(\n<script>)',
        lambda m: m.group(1) + body + m.group(2),
        html, count=1, flags=re.DOTALL,
    )
    if n == 0:
        raise ValueError('Anchor <div class="wrap">...<script> tidak ditemukan di materi template')

    decls, calls = _build_materi_script_data(parsed, answers)
    # Anchor pada deklarasi data SKILL4/SKILL5 SAJA (berhenti sebelum `const LETTERS`
    # dan definisi function renderExercises -- keduanya generik & harus tetap dipertahankan).
    html = _replace_once(
        r'const SKILL4 = \[.*?\n\];\n\nconst SKILL5 = \[.*?\n\];',
        decls, html, flags=re.DOTALL,
    )
    # Anchor pada 2 baris pemanggilan renderExercises() di paling bawah script.
    html = _replace_once(
        r'renderExercises\("ex-skill4", SKILL4, "s4"\);\nrenderExercises\("ex-skill5", SKILL5, "s5"\);',
        calls, html,
    )

    return html
