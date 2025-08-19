import csv
import unicodedata

input_csv = "original_corpus.csv"
output_csv = "clean_corpus_with_luganda_fixed.csv"

# Replacement dictionary for common mojibake
replacements = {
    "â€™": "’", "â€˜": "‘",
    "â€œ": "“", "â€�": "”",
    "â€“": "–", "â€”": "—",
    "â€¢": "•", "â€¦": "…",
    "Å‹": "Š", "Å": "Š", "z†Ÿ": "z’",
    "Ã©": "é", "Ã¨": "è",
    "€": "€", "™": "™", "‹": "‘", "˜": "~",
    "\x03": "", "\x07": "", "\x08": "",
    "|": "", "<": "", ">": "", "[": "", "]": "", "&": "", "+": "", "=": "", "*": "", "$": "", "@": "", "/": "",
    "Â": "",
}

# Function to fix double-encoding mojibake
def fix_double_encoding(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    try:
        text = text.encode("cp1252", errors="replace").decode("utf-8", errors="replace")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return text

# Function to replace sequences and handle remaining �
def replace_text(text: str) -> str:
    text = fix_double_encoding(text)
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    # Replace remaining � with single quote
    text = text.replace("�", "'")
    return text

# Process CSV
rows = []
with open(input_csv, "r", encoding="cp1252", errors="replace") as infile:
    reader = csv.reader(infile)
    for row in reader:
        cleaned_row = [replace_text(cell) for cell in row]
        rows.append(cleaned_row)

# Save cleaned CSV with UTF-8 BOM
with open(output_csv, "w", newline="", encoding="utf-8-sig") as outfile:
    writer = csv.writer(outfile)
    writer.writerows(rows)

print(f"✅ All replacements done. Cleaned CSV saved as {output_csv}")
