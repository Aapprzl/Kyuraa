import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from src.utils.logger import log
from src.utils.security import SecurityManager
from src.config import MAX_UPLOAD_SIZE_BYTES, MAX_PDF_TOKENS

router = APIRouter()

UPLOAD_DIR = Path("workspace/tempat_baca/uploaded_pdfs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def verify_token(request: Request):
    cli_token = request.headers.get("X-API-Key") or request.query_params.get("token")
    srv_token = SecurityManager.get_gateway_token()
    if not cli_token or cli_token != srv_token:
        raise HTTPException(status_code=401, detail="❌ Akses dilarang: Token tidak valid.")

@router.post("/upload")
async def upload_pdf(request: Request):
    verify_token(request)
    try:
        form = await request.form()
        file = list(form.values())[0]
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Hanya file PDF yang diizinkan")
        
        safe_name = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = UPLOAD_DIR / safe_name
        
        content = await file.read()
        
        # Validasi magic bytes PDF (%PDF)
        if not content.startswith(b'%PDF'):
            raise HTTPException(400, "File bukan PDF yang valid (magic bytes tidak sesuai)")
            
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(400, "File terlalu besar (max 5MB)")
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        from src.tools.pdf_processor import extract_text_from_pdf, estimate_tokens
        import asyncio
        analysis = await asyncio.to_thread(extract_text_from_pdf, str(file_path))
        
        estimated_tokens = estimate_tokens(analysis["text"])
        
        log("upload", f"PDF uploaded: {file.filename} | tokens: {estimated_tokens}")
        
        return {
            "success": True,
            "file_id": safe_name,
            "filename": file.filename,
            "page_count": analysis["page_count"],
            "word_count": analysis["word_count"],
            "script": analysis["script"],
            "text": analysis["text"],
            "estimated_tokens": estimated_tokens,
            "exceeds_limit": estimated_tokens > MAX_PDF_TOKENS,
            "max_tokens": MAX_PDF_TOKENS,
            "warnings": analysis["warnings"]
        }
    except HTTPException:
        raise
    except Exception as e:
        log("error", f"Upload error: {e}")
        raise HTTPException(500, f"Gagal upload: {str(e)}")

@router.post("/upload/partial")
async def upload_pdf_partial(request: Request):
    verify_token(request)
    try:
        body = await request.json()
        file_id = body.get("file_id")
        page_start = body.get("page_start", 1)
        page_end = body.get("page_end")
        
        if not file_id:
            raise HTTPException(400, "file_id diperlukan")
        
        file_path = UPLOAD_DIR / file_id
        if not file_path.exists():
            raise HTTPException(404, "File tidak ditemukan")
        
        from src.tools.pdf_processor import extract_text_from_pdf, estimate_tokens
        import asyncio
        analysis = await asyncio.to_thread(extract_text_from_pdf, str(file_path), page_start, page_end)
        
        estimated_tokens = estimate_tokens(analysis["text"])
        return {
            "success": True,
            "file_id": file_id,
            "text": analysis["text"],
            "estimated_tokens": estimated_tokens,
            "warnings": analysis["warnings"]
        }
    except HTTPException:
        raise
    except Exception as e:
        log("error", f"Partial upload error: {e}")
        raise HTTPException(500, f"Gagal extract halaman: {str(e)}")

@router.get("/upload/{file_id}")
async def get_uploaded_file(request: Request, file_id: str):
    verify_token(request)
    file_path = UPLOAD_DIR / file_id
    if not file_path.exists():
        raise HTTPException(404, "File tidak ditemukan")
    return FileResponse(str(file_path), media_type="application/pdf", filename=file_path.name)

@router.delete("/upload/{file_id}")
async def delete_uploaded_file(request: Request, file_id: str):
    verify_token(request)
    file_path = UPLOAD_DIR / file_id
    if not file_path.exists():
        raise HTTPException(404, "File tidak ditemukan")
    
    file_path.unlink()
    from src.memory.session_store import SessionStore
    store = SessionStore()
    store.remove_file_metadata(file_id)
    return {"success": True, "deleted": file_id}
