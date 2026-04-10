import fitz
import easyocr

file_path = "workspace/tempat_baca/uploaded_pdfs/05e25402ca6e42fc9c5e5501f8b01c15_Mulakhos hlm 312-318.PDF"

print("Loading PDF...")
doc = fitz.open(file_path)
page = doc.load_page(0) # Halaman 1
pix = page.get_pixmap(dpi=150) # Resolusi cukup untuk OCR
img_path = "temp_page_0.png"
pix.save(img_path)

print("Initializing EasyOCR (this will download models if first time)...")
reader = easyocr.Reader(['ar'])
print("Reading text...")
result = reader.readtext(img_path, detail=0, paragraph=True)
print("Result:")
print("\n".join(result))
