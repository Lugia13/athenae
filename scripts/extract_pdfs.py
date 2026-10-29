import sys
from config import BASE_DIR
import fitz  # pymupdf
import os
from pathlib import Path
from tqdm import tqdm

BOOKS_DIR = sys.argv[1] if len(sys.argv) > 1 else str(BASE_DIR / "docs")
OUTPUT_DIR = str(BASE_DIR / "extracted_text")

def extract_pdf(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    full_text = []
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            full_text.append(f"\n\n--- Page {page_num + 1} ---\n\n{text}")
    doc.close()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("".join(full_text))
    return len("".join(full_text))

def main():
    pdf_files = list(Path(BOOKS_DIR).glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")
    
    results = []
    for pdf_path in tqdm(pdf_files, desc="Extracting"):
        out_name = pdf_path.stem.replace(" ", "_") + ".txt"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        try:
            char_count = extract_pdf(str(pdf_path), out_path)
            results.append((pdf_path.name, char_count, "OK"))
        except Exception as e:
            results.append((pdf_path.name, 0, f"ERROR: {e}"))
    
    print("\n--- Summary ---")
    for name, chars, status in results:
        print(f"{status:10s} | {chars:>10,} chars | {name}")

if __name__ == "__main__":
    main()
