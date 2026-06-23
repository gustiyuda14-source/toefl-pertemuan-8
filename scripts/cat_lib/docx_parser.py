"""Ekstraksi verbatim soal & teori dari file .docx materi/evaluasi TOEFL.

Tidak ada parafrase atau penulisan ulang di sini -- setiap potongan teks yang
dikembalikan adalah substring langsung dari paragraph.text milik python-docx.
"""
import re
import docx

SKILL_HEADER_RE = re.compile(r"^(?:TOEFL\s+)?SKILL\s+(\d+)\s*:\s*(.+)$")
EVAL_HEADER_RE = re.compile(r"^(?:EVALUATION FOR SKILL|EVALUASI SKILL)\b.*$", re.IGNORECASE)

# (regex pola instruksi, type, jumlah opsi). Daftar ini bisa ditambah untuk
# batch skill berikutnya tanpa mengubah state machine di bawah.
INSTRUCTION_PATTERNS = [
    (re.compile(r"choose correct or incorrect", re.IGNORECASE), "ci", 2),
    (re.compile(r"incorrect structure", re.IGNORECASE), "err", 4),
    (re.compile(r"choose a,?\s*b,?\s*c,?\s*or d\b", re.IGNORECASE), "mcq", 4),
    (re.compile(r"^latihan\b", re.IGNORECASE), "mcq", 4),
]

THEORY_TAG_RE = re.compile(r"^(Contoh|Rumus|Pola)\b", re.IGNORECASE)


def _normalize_quotes_for_match(s):
    return s.replace("“", '"').replace("”", '"').replace("’", "'")


def _flatten_lines(doc):
    """Pecah tiap paragraph.text di karakter newline manual (<w:br/>).

    Hanya whitespace ASCII biasa (spasi/tab/CR) yang di-strip dari ujung baris.
    Non-breaking space (\xa0) TIDAK distrip karena di sebagian soal sumber
    dipakai penulis dokumen sebagai penanda visual "blank" yang harus diisi
    (mis. blank di awal kalimat) -- menghapusnya akan mengurangi soal asli.
    """
    lines = []
    for p in doc.paragraphs:
        text = p.text
        if not text:
            continue
        for raw_line in text.split("\n"):
            line = raw_line.strip(" \t\r")
            if line:
                lines.append(line)
    return lines


def _match_instruction(line):
    normalized = _normalize_quotes_for_match(line)
    for pattern, qtype, opt_count in INSTRUCTION_PATTERNS:
        if pattern.search(normalized):
            return qtype, opt_count
    return None


def parse_docx(path):
    """Kembalikan {"skills": [{"number", "title", "theory": [...], "exercises": [...]}]}.

    Untuk dokumen evaluasi (tanpa header "TOEFL SKILL N"), seluruh dokumen
    diperlakukan sebagai satu "skill" dengan number=None.
    """
    doc = docx.Document(path)
    lines = _flatten_lines(doc)

    skills = []
    current_skill = None
    current_group = None  # {"type", "opt_count", "exercises": [...]}

    def start_skill(number, title):
        nonlocal current_skill, current_group
        current_skill = {"number": number, "title": title, "theory": [], "exercises": []}
        skills.append(current_skill)
        current_group = None

    for line in lines:
        header_match = SKILL_HEADER_RE.match(line)
        if header_match:
            start_skill(int(header_match.group(1)), header_match.group(2).strip())
            continue
        if EVAL_HEADER_RE.match(line):
            start_skill(None, line)
            continue

        if current_skill is None:
            # Dokumen tanpa header skill (mis. file evaluasi) -- mulai skill default.
            start_skill(None, "")

        if line.strip().lower() == "exercise":
            # Marker struktural ("mulai bagian latihan"), bukan konten yang perlu disimpan.
            continue

        instr = _match_instruction(line)
        if instr:
            qtype, opt_count = instr
            current_group = {"type": qtype, "opt_count": opt_count, "pending": []}
            continue

        if current_group is None:
            # Masih di area teori (sebelum instruksi exercise pertama).
            tag = "label" if THEORY_TAG_RE.match(line) else "text"
            current_skill["theory"].append({"tag": tag, "text": line})
            continue

        # Di dalam grup exercise: kumpulkan baris sampai cukup utk 1 soal lengkap.
        current_group["pending"].append(line)
        needed = 1 + current_group["opt_count"]
        if len(current_group["pending"]) == needed:
            stem, *options = current_group["pending"]
            current_skill["exercises"].append({
                "type": current_group["type"],
                "text": stem,
                "options": options,
            })
            current_group["pending"] = []

    return {"skills": skills}
