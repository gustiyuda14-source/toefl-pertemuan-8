# Sistem Generate CAT TOEFL

Pipeline untuk mengubah file Word (.docx) materi & evaluasi TOEFL menjadi
halaman HTML CAT (Computer Adaptive Test) interaktif, via
`scripts/generate_cat.py`. Prosesnya **tidak otomatis penuh** — setiap ada
file Word baru, ikuti langkah manual di bawah, karena kunci jawaban harus
diverifikasi manusia (parser hanya mengekstrak teks verbatim, tidak tahu
mana jawaban yang benar).

## Struktur Direktori

```
/                                   file docx sumber + HTML hasil generate
├── TOEFL SKILL <N>.docx            materi (opsional, sesuai kebutuhan)
├── EVALUATION FOR SKILL <N>.docx   evaluasi/CAT
├── materi-<N>.html                 hasil build-materi
├── index-<N>.html                  hasil build-evaluation (halaman CAT)
├── vercel.json                     rewrite "/" -> index-<N>.html aktif
├── assets/                         gambar (mis. banner)
└── scripts/
    ├── generate_cat.py             CLI: parse | build-materi | build-evaluation
    ├── cat_lib/
    │   ├── docx_parser.py          ekstraksi verbatim docx -> JSON
    │   ├── renderer.py             gabungkan JSON + answers + config -> HTML
    │   ├── verify.py               cocokkan HTML hasil generate vs hasil parse
    │   └── _template/              template HTML dasar (index_base, materi_base)
    └── data/
        ├── toefl_<N>.parsed.json    hasil parse materi (auto)
        ├── toefl_<N>.answers.json   kunci jawaban materi (manual)
        ├── eval_<N>.parsed.json     hasil parse evaluasi (auto)
        ├── eval_<N>.answers.json    kunci jawaban evaluasi (manual)
        └── page_config_<N>.json     judul/copy/label halaman (manual)
```

`<N>` = penanda skill, mis. `678` untuk Skill 6,7,8 atau `910` untuk Skill 9,10.

## Alur Kerja Setiap Ada File Word Baru

### 1. Taruh file .docx di root project
Ikuti pola nama yang sudah dipakai: `TOEFL SKILL <N>.docx` (materi) dan
`EVALUATION FOR SKILL <N>.docx` (evaluasi). Materi harus punya heading
`SKILL <angka>: <judul>` per skill; evaluasi punya heading
`EVALUATION FOR SKILL ...`.

### 2. Parse docx -> JSON verbatim
```bash
python3 scripts/generate_cat.py parse \
  --docx "TOEFL SKILL <N>.docx" \
  --out scripts/data/toefl_<N>.parsed.json

python3 scripts/generate_cat.py parse \
  --docx "EVALUATION FOR SKILL <N>.docx" \
  --out scripts/data/eval_<N>.parsed.json
```
Cek output terminal: jumlah skill & soal harus sesuai ekspektasi.

### 3. Buat kunci jawaban (manual, wajib)
Buat `scripts/data/toefl_<N>.answers.json` dan `scripts/data/eval_<N>.answers.json`,
array sejajar urutan soal di file `*.parsed.json` (satu entri per soal, dalam
urutan skill lalu urutan exercise). Format tiap entri:
```json
{
  "ref": "20 karakter awal teks soal (untuk validasi urutan)",
  "answer": 0,
  "expl": "Penjelasan kenapa jawaban ini benar/salah",
  "flagged": false
}
```
- `answer`: index opsi yang benar (0-based).
- `ref`: potongan awal `text` soal — dipakai `renderer.py` untuk memastikan
  urutan answer key tidak geser dari urutan hasil parse. Kalau tidak cocok,
  build akan gagal dengan error `Answer key tidak sejajar`.
- `flagged`: `true` kalau soal perlu verifikasi ulang manual sebelum dipakai.

### 4. Buat page config (manual)
Buat `scripts/data/page_config_<N>.json` berisi judul, copy landing, dan
label section. Contoh lengkap: lihat `page_config_678.json` / `page_config_910.json`
di riwayat git (`git show <commit>:scripts/data/page_config_910.json`).

### 5. Build HTML materi & evaluasi
```bash
python3 scripts/generate_cat.py build-materi \
  --data scripts/data/toefl_<N>.parsed.json \
  --answers scripts/data/toefl_<N>.answers.json \
  --config scripts/data/page_config_<N>.json \
  --out materi-<N>.html --verify

python3 scripts/generate_cat.py build-evaluation \
  --data scripts/data/eval_<N>.parsed.json \
  --answers scripts/data/eval_<N>.answers.json \
  --config scripts/data/page_config_<N>.json \
  --out index-<N>.html --verify
```
Flag `--verify` mencocokkan ulang teks soal di HTML hasil generate terhadap
hasil parse docx asli — build gagal (exit code 1) kalau ada ketidakcocokan.

### 6. Arahkan halaman utama (opsional)
Kalau CAT baru ini yang mau ditampilkan di root domain, update `vercel.json`:
```json
{ "rewrites": [{ "source": "/", "destination": "/index-<N>.html" }] }
```

### 7. Cek manual & commit
Buka `index-<N>.html` dan `materi-<N>.html` di browser, jalankan tes sampai
selesai untuk memastikan tampilan & skoring benar, baru commit.

## Kenapa Tidak Full-Otomatis

`docx_parser.py` hanya mengekstrak teks soal apa adanya dari Word — ia tidak
tahu mana jawaban yang benar. Kunci jawaban (`*.answers.json`) dan salinan
teks (`page_config_*.json`) tetap harus dibuat/diverifikasi manusia agar CAT
yang dihasilkan akurat.
