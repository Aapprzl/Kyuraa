from src.tools.pdf_processor import extract_text_from_pdf
file_path = "workspace/tempat_baca/uploaded_pdfs/11759e9d3e6c4d2ba07a65a48f89248b_HASIL ANALISIS DATA KUALITATIF.pdf"

print(f"Menguji file: {file_path}")
print("Loading PDF and running extraction (with OCR fallback if needed)...")
analysis = extract_text_from_pdf(file_path, page_start=1, page_end=1) # test 1st page only to be quick

print(f"Extracted Text Length: {len(analysis['text'])}")
print(f"Warnings: {analysis['warnings']}")

text_preview = analysis['text'][:1000] if analysis['text'] else ''
print(f"Preview Teks (Max 1000 huruf):\n{text_preview}")
