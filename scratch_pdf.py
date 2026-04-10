from src.tools.pdf_processor import extract_text_from_pdf
file_path = "workspace/tempat_baca/uploaded_pdfs/05e25402ca6e42fc9c5e5501f8b01c15_Mulakhos hlm 312-318.PDF"
analysis = extract_text_from_pdf(file_path)
print(f"Page Count: {analysis['page_count']}")
print(f"Word Count: {analysis['word_count']}")
print(f"Text len: {len(analysis['text'])}")
print(f"Warnings: {analysis['warnings']}")
if len(analysis['text']) < 100:
    print(f"Content: {analysis['text']}")
