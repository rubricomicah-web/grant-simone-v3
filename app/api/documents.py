
from pathlib import Path
import os, re, uuid, io
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_paid_user
from app.models.tables import Document, Organization
from app.services.plans import check_and_record_usage, require_feature
from app.services.serialize import model_to_dict
from app.services.storage import save_upload, signed_url
from app.services.document_parser import extract_text_from_upload
from app.core.config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])
STORAGE_DIR = Path("storage/uploads")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".csv", ".png", ".jpg", ".jpeg"}

def safe_name(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "document"
    return stem[:180]

@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    organization_id: int | None = Form(None),
    document_type: str = Form("supporting_document"),
    db: Session = Depends(get_db),
    user = Depends(require_paid_user),
):
    require_feature(db, user, "documents")
    if organization_id:
        org = db.query(Organization).filter(Organization.id == organization_id, Organization.tenant_id == user.tenant_id).first()
        if not org:
            raise HTTPException(404, "Funding profile not found")
    ext = Path(file.filename or "upload").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported file type. Upload PDF, DOC, DOCX, TXT, CSV, PNG, JPG, or JPEG.")
    content = await file.read()
    max_bytes = int(settings.max_upload_mb) * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File too large. Maximum size is {settings.max_upload_mb}MB.")
    check_and_record_usage(db, user, "document_upload", {"filename": file.filename})
    stored = f"{uuid.uuid4().hex}_{safe_name(file.filename or 'document')}"
    storage_info = save_upload(io.BytesIO(content), stored, user.tenant_id, user.id)
    path = Path(storage_info["path"]) if storage_info["backend"] == "local" else Path(stored)
    extracted = extract_text_from_upload(file.filename or stored, content)
    row = Document(
        tenant_id=user.tenant_id,
        user_id=user.id,
        organization_id=organization_id,
        filename=stored,
        original_filename=file.filename or stored,
        content_type=file.content_type,
        size_bytes=len(content),
        storage_path=storage_info["path"],
        document_type=document_type,
        extracted_text=extracted,
    )
    db.add(row); db.commit(); db.refresh(row)
    return model_to_dict(row)

@router.get("")
def list_documents(organization_id: int | None = None, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "documents")
    q = db.query(Document).filter(Document.tenant_id == user.tenant_id)
    if organization_id:
        q = q.filter(Document.organization_id == organization_id)
    rows = q.order_by(Document.created_at.desc()).limit(200).all()
    return [model_to_dict(r) for r in rows]

@router.get("/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db), user = Depends(require_paid_user)):
    require_feature(db, user, "documents")
    row = db.query(Document).filter(Document.id == document_id, Document.tenant_id == user.tenant_id).first()
    if not row:
        raise HTTPException(404, "Document not found")
    if row.storage_path.startswith("s3://"):
        return {"download_url": signed_url(row.storage_path), "filename": row.original_filename}
    path = Path(row.storage_path)
    if not path.exists():
        raise HTTPException(404, "Stored file is missing")
    return FileResponse(str(path), filename=row.original_filename, media_type=row.content_type or "application/octet-stream")
