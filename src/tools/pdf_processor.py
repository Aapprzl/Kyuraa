from pathlib import Path
from typing import TypedDict

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


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
    
    if not PDFPLUMBER_AVAILABLE:
        return PDFAnalysis(
            text="",
            page_count=0,
            word_count=0,
            script="unknown",
            warnings=["pdfplumber not installed. Run: pip install pdfplumber"]
        )
    
    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            if page_start is not None and page_end is not None:
                pages_to_extract = range(page_start - 1, min(page_end, total_pages))
            elif page_start is not None:
                pages_to_extract = range(page_start - 1, total_pages)
            elif page_end is not None:
                pages_to_extract = range(0, min(page_end, total_pages))
            else:
                pages_to_extract = range(0, total_pages)
            
            page_count = len(list(pages_to_extract))
            
            for i in pages_to_extract:
                page = pdf.pages[i]
                text = page.extract_text()
                if text:
                    full_text.append(text)
                else:
                    warnings.append(f"Halaman {i+1}: Tidak ada teks (mungkin PDF scan)")
            
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
