from pathlib import Path
from typing import TypedDict

import os
import uuid

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

_OCR_READER = None

def get_ocr_reader():
    global _OCR_READER
    if _OCR_READER is None:
        try:
            import easyocr
            from src.utils.logger import log
            log("info", "Loading EasyOCR model for Arabic/English...")
            _OCR_READER = easyocr.Reader(['ar', 'en'], gpu=False)
        except ImportError:
            pass
    return _OCR_READER


class PDFAnalysis(TypedDict):
    text: str
    page_count: int
    word_count: int
    script: str
    warnings: list[str]


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


def detect_script(text: str) -> str:
    if not text.strip():
        return "unknown"
    
    arabic_chars = sum(
        1 for c in text 
        if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F'
    )
    latin_chars = sum(
        1 for c in text 
        if ('\u0041' <= c <= '\u007A') or 
           ('\u00C0' <= c <= '\u024F') or
           ('\u0040' <= c <= '\u005A')
    )
    
    total = len(text)
    if total == 0:
        return "unknown"
    
    arabic_ratio = arabic_chars / total
    latin_ratio = latin_chars / total
    
    if arabic_ratio > 0.3:
        return "arabic"
    elif latin_ratio > 0.5:
        return "latin"
    elif arabic_ratio > 0.1:
        return "mixed"
    return "latin"


def extract_text_from_pdf(file_path: str, page_start: int = None, page_end: int = None) -> PDFAnalysis:
    warnings = []
    full_text = []
    page_count = 0
    
    if not PDFPLUMBER_AVAILABLE and not PYMUPDF_AVAILABLE:
        return PDFAnalysis(
            text="",
            page_count=0,
            word_count=0,
            script="unknown",
            warnings=["pdfplumber or PyMuPDF not installed"]
        )
    
    try:
        if PYMUPDF_AVAILABLE:
            doc = fitz.open(file_path)
            total_pages = len(doc)
        else:
            doc = pdfplumber.open(file_path)
            total_pages = len(doc.pages)
            
        if page_start is not None and page_end is not None:
            pages_to_extract = range(page_start - 1, min(page_end, total_pages))
        elif page_start is not None:
            pages_to_extract = range(page_start - 1, total_pages)
        elif page_end is not None:
            pages_to_extract = range(0, min(page_end, total_pages))
        else:
            pages_to_extract = range(0, total_pages)
        
        page_count = len(list(pages_to_extract))
        reader = None
        
        for i in pages_to_extract:
            text = ""
            if PYMUPDF_AVAILABLE:
                page = doc.load_page(i)
                text = page.get_text()
            else:
                page = doc.pages[i]
                text = page.extract_text()
                
            if text and text.strip():
                full_text.append(text)
            else:
                # Fallback to OCR if empty
                if not PYMUPDF_AVAILABLE:
                    warnings.append(f"Halaman {i+1}: Tidak ada teks (PDF scan). Install PyMuPDF + easyocr untuk OCR.")
                    continue
                    
                reader = get_ocr_reader()
                if not reader:
                    warnings.append(f"Halaman {i+1}: Tidak ada teks. Install easyocr untuk membaca PDF scan.")
                    continue
                
                # Gunakan PyMuPDF untuk render gambar ke memory
                page_fitz = doc.load_page(i)
                pix = page_fitz.get_pixmap(dpi=150)
                
                # Konversi ke numpy array untuk EasyOCR
                try:
                    import numpy as np
                    import cv2
                    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    if pix.n == 4: # RGBA
                        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
                    elif pix.n == 1: # Grayscale
                        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
                        
                    ocr_res = reader.readtext(img_array, detail=0, paragraph=True)
                    if ocr_res:
                        full_text.append("\n".join(ocr_res))
                    else:
                        warnings.append(f"Halaman {i+1}: Teks kosong bahkan setelah proses OCR.")
                except Exception as ex:
                    warnings.append(f"Halaman {i+1}: Gagal OCR ({str(ex)})")

        if not PYMUPDF_AVAILABLE:
            doc.close()
            
        combined = "\n\n".join(full_text)
        word_count = len(combined.split())
        script = detect_script(combined)
        
        return PDFAnalysis(
            text=combined,
            page_count=page_count,
            word_count=word_count,
            script=script,
            warnings=warnings
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return PDFAnalysis(
            text="",
            page_count=0,
            word_count=0,
            script="unknown",
            warnings=[f"Error: {str(e)}"]
        )


def get_pdf_info(file_path: str) -> dict:
    if not PDFPLUMBER_AVAILABLE:
        return {"pages": 0, "error": "pdfplumber not installed"}
    
    try:
        with pdfplumber.open(file_path) as pdf:
            return {"pages": len(pdf.pages)}
    except Exception as e:
        return {"pages": 0, "error": str(e)}
