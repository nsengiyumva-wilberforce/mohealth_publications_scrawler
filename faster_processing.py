import os
import re
import csv
import fitz  # PyMuPDF
import nltk

# ✅ Optional: use spaCy instead of NLTK for faster sentence splitting
USE_SPACY = False
if USE_SPACY:
    import spacy
    nlp = spacy.load("en_core_web_sm", disable=["ner", "parser", "tagger"])
else:
    nltk.download("punkt", quiet=True)

pdf_dir = "downloaded_pdfs"
output_csv = "clean_corpus.csv"
removed_fragments_file = "removed_fragments.txt"


# ------------------------
# Precompiled regexes
# ------------------------
REPLACEMENTS = [
    (re.compile(r"-\s*\n\s*"), ""),                  # fix hyphenated line breaks
    (re.compile(r"\.{5,}\s*\w*"), ""),               # dot leaders
    (re.compile(r"doi:\s*\S+", re.I), ""),           # DOIs
    (re.compile(r"https?://\S+|www\.\S+"), ""),      # URLs
    (re.compile(r"\S+@\S+"), ""),                    # emails
    (re.compile(r"\+?\d[\d\s-]{7,}"), ""),           # phone numbers
    (re.compile(r"P\.?\s?O\.?\s?Box\s*\d+", re.I), ""),
    (re.compile(r"Plot\s*\d+[\w\s,]*", re.I), ""),
    (re.compile(r"(Department|Faculty|University|Hospital|Clinic|Ministry of|Headquarters).*", re.I), ""),
    (re.compile(r"^\s*[\-•●\d]+\s+", re.M), ""),     # list markers
    (re.compile(r"\b(\d{1,3}(,\d{1,3})+)\b"), ""),   # inline numeric citations
    (re.compile(r"\([A-Z][A-Za-z]+ et al\., \d{4}\)"), ""),
    (re.compile(r"\([A-Z][A-Za-z]+, \d{4}\)"), ""),
    (re.compile(r"\[\d+\]|\(\d+\)"), ""),            # ref markers
    (re.compile(r"(Figure|Table)\s*\d+.*", re.I), ""), # captions
    (re.compile(r"\b([B-Z])\s+([A-Za-z]{2,})\b"), r"\1\2"),  # W hat -> What
    (re.compile(r"\b(?:[A-Za-z]\s){2,}[A-Za-z]\b"), lambda m: m.group(0).replace(" ", "")), # W h a t
    (re.compile(r"(\d)\s+(\d)"), r"\1\2"),           # split numbers
    (re.compile(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[A-Za-z\-\s]*\d{2,4}"), ""),
    (re.compile(r"([a-z])([A-Z])"), r"\1. \2"),      # glued sentences
]

DROP_PATTERNS = [
    re.compile(p, re.I | re.S) for p in [
        r"\bTABLE OF CONTENTS\b",
        r"\bFOREWORD\b",
        r"\bPREFACE\b",
        r"\bEXECUTIVE SUMMARY\b",
        r"\bREFERENCES\b",
        r"\bBIBLIOGRAPHY\b",
        r"\bABBREVIATIONS\b",
        r"Creative Commons.*?licen[cs]e",
        r"This work is available under.*?licen[cs]e",
        r"World Health Organization.*?rights reserved",
        r"All rights reserved",
        r"WHO 20\d{2}",
    ]
]


def fix_encoding(text: str) -> str:
    """Fix common UTF-8/Windows-1252 mojibake issues."""
    return (
        text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        .replace("â€“", "-").replace("â€”", "-")
        .replace("â€¢", "-").replace("â—", "-")
        .replace("Â©", "©").replace("â€˜", "'")
        .replace("â€™", "'").replace("â€œ", '"').replace("â€�", '"')
    )


def clean_text(text: str, removed_writer) -> str:
    """Clean up a page of text."""
    text = fix_encoding(text)

    # Drop whole sections
    for pat in DROP_PATTERNS:
        text = pat.sub("", text)

    # Run substitutions
    for pat, repl in REPLACEMENTS:
        text = pat.sub(repl, text)

    # Line filtering
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) < 25 or len(line) > 500:
            removed_writer.writerow([line]); continue
        if re.match(r"^[\d\s,.-]+$", line):
            removed_writer.writerow([line]); continue
        if line.isupper() or (sum(c.isupper() for c in line) / max(1, len(line)) > 0.6):
            removed_writer.writerow([line]); continue
        if len(re.findall(r"[\d.,%]", line)) / max(1, len(line)) > 0.4:
            removed_writer.writerow([line]); continue
        cleaned_lines.append(line)

    return " ".join(cleaned_lines)


def extract_sentences(text: str, removed_writer):
    """Split into sentences and filter."""
    if USE_SPACY:
        sentences = [s.text.strip() for s in nlp(text).sents]
    else:
        sentences = nltk.sent_tokenize(text)

    result = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15 or len(s) > 999:
            removed_writer.writerow([s]); continue
        if re.search(r"(Figure|Table|Workshop|Likert)", s, re.I):
            removed_writer.writerow([s]); continue
        if re.search(r"(Ministry|Plot|P\.O\. Box|Street|Road|Uganda|Creative Commons|World Health Organization|rights reserved|All rights reserved)", s, re.I):
            removed_writer.writerow([s]); continue
        if re.search(r"\bet al\.\b", s):
            removed_writer.writerow([s]); continue
        if len(re.findall(r"\d", s)) / max(1, len(s)) > 0.15:
            removed_writer.writerow([s]); continue
        if not re.match(r"^[A-Z]", s):
            removed_writer.writerow([s]); continue
        if not re.search(r"\b(is|are|was|were|has|have|can|may|should|provide|develop|improve)\b", s):
            removed_writer.writerow([s]); continue
        result.append(s)
    return result


# ------------------------
# Main loop with fitz
# ------------------------
with open(output_csv, "w", newline="", encoding="utf-8") as out_csv, \
     open(removed_fragments_file, "w", newline="", encoding="utf-8") as out_removed:

    writer = csv.writer(out_csv)
    removed_writer = csv.writer(out_removed)

    writer.writerow(["Sentence"])
    removed_writer.writerow(["Removed"])  # header

    for file in os.listdir(pdf_dir):
        if not file.lower().endswith(".pdf"):
            continue
        print(f"Processing {file}...")
        try:
            pdf_path = os.path.join(pdf_dir, file)
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    raw = page.get_text("text") or ""
                    if not raw.strip():
                        continue
                    cleaned = clean_text(raw, removed_writer)
                    for sent in extract_sentences(cleaned, removed_writer):
                        writer.writerow([sent])
        except Exception as e:
            print(f"❌ Error {file}: {e}")

print(f"✅ Done. Clean corpus saved to {output_csv}")
print(f"🗑️ Removed fragments saved to {removed_fragments_file}")
