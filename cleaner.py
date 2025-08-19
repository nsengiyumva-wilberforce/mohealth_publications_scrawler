import csv
import unicodedata

input_csv = "original_corpus.csv"
output_csv = "clean_corpus_with_luganda_fixed.csv"

def clean_text(text):
    if not text:
        return ""
    # Normalize to composed Unicode
    text = unicodedata.normalize("NFC", text)
    # Fix common mojibake
    text = text.replace("â€™", "’").replace("â€œ", "“").replace("â€�", "”")
    text = text.replace("â€“", "–").replace("â€”", "—").replace("â€¢", "•")
    text = text.replace("Â", "")  # stray "Â" before spaces/characters
    return text

rows = []
# Use cp1252 (Windows-1252) to read
with open(input_csv, "r", encoding="cp1252", errors="replace") as infile:
    reader = csv.reader(infile)
    header = next(reader)
    rows.append(header)

    for row in reader:
        cleaned_row = [clean_text(cell) for cell in row]
        rows.append(cleaned_row)

# Save as UTF-8 with BOM for Excel
with open(output_csv, "w", newline="", encoding="utf-8-sig") as outfile:
    writer = csv.writer(outfile)
    writer.writerows(rows)

print(f"✅ Cleaning complete! Saved fixed file as {output_csv}")
