from src.tools.pdf_processor import extract_text_from_pdf
import fitz

# Bikin PDF dummy yang isinya cuma gambar (supaya OCR trigger)
doc = fitz.open()
page = doc.new_page()

# Tambahkan gambar (kita pakai sembarang background merah)
page.draw_rect(page.rect, color=(1,0,0), fill=(1,0,0))
# Letakkan teks tulisan ke image, tapi PyMuPDF draw_text masih bikin text layer,
# kita harapkan untuk text asli, tidak usah. Kita save rect kosong saja lalu kita simulasikan 
# image kosong atau kita ambil satu page dari file PDF text, jadikan pixmap, dan insert sbg image
src_doc = fitz.open("workspace/tempat_baca/uploaded_pdfs/11759e9d3e6c4d2ba07a65a48f89248b_HASIL ANALISIS DATA KUALITATIF.pdf")
src_page = src_doc.load_page(0)
pix = src_page.get_pixmap()

# doc.insert_page punya insert_image
page.insert_image(page.rect, pixmap=pix)
scanned_path = "workspace/tempat_baca/uploaded_pdfs/dummy_scan.pdf"
doc.save(scanned_path)
doc.close()

print(f"Menguji file OCR Scan PDF: {scanned_path}")
analysis = extract_text_from_pdf(scanned_path, page_start=1, page_end=1)

print(f"Extracted OCR Text Length: {len(analysis['text'])}")
print(f"Warnings: {analysis['warnings']}")

text_preview = analysis['text'][:500] if analysis['text'] else ''
print(f"Preview Teks (Max 500 huruf):\n{text_preview}")
