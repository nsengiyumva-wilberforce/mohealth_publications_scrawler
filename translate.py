import csv
import asyncio
from googletrans import Translator
import unicodedata

input_csv = "clean_corpus.csv"
output_csv = "clean_corpus_with_luganda.csv"

BATCH_SIZE = 20

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def clean_text(text):
    """
    Normalize text and fix encoding issues like â€™ turning into ’
    """
    if not text:
        return ""
    # Normalize to NFC (proper composed Unicode)
    text = unicodedata.normalize("NFC", text)
    # Replace common mojibake artifacts
    text = text.replace("â€™", "’").replace("â€œ", "“").replace("â€�", "”")
    text = text.replace("â€“", "–").replace("â€”", "—").replace("â€¢", "•")
    return text

async def translate_batches(sentences):
    translations = []
    async with Translator() as translator:
        for i, batch in enumerate(chunks(sentences, BATCH_SIZE), start=1):
            try:
                print(f"🔄 Translating batch {i} ({len(batch)} sentences)...")
                results = await translator.translate(batch, src="en", dest="lg")
                batch_translations = [clean_text(res.text) for res in results]
                translations.extend(batch_translations)
                print(f"✅ Finished batch {i}")
            except Exception as e:
                print(f"⚠️ Batch {i} failed: {e}")
                translations.extend([""] * len(batch))
    return translations

# Load sentences
sentences = []
with open(input_csv, "r", encoding="utf-8-sig") as infile:  # use utf-8-sig to strip BOM
    reader = csv.DictReader(infile)
    for row in reader:
        if row["Sentence"].strip():
            sentences.append(row["Sentence"].strip())

print(f"📄 Loaded {len(sentences)} sentences from {input_csv}")

# Run async translation
translations = asyncio.run(translate_batches(sentences))

# Save results with UTF-8 BOM so Excel/Windows reads correctly
with open(output_csv, "w", newline="", encoding="utf-8-sig") as outfile:
    writer = csv.writer(outfile)
    writer.writerow(["English", "Luganda"])
    for en, lg in zip(sentences, translations):
        writer.writerow([clean_text(en), clean_text(lg)])

print(f"✅ Done! Translations saved to {output_csv}")
