"""Knowledge-source management.

Admin and Super User may upload, preview, and approve/reject documents.
Document deletion remains Admin-only. Regional and Normal users cannot call these endpoints.
"""

from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.auth.rbac import CurrentUser, require_roles
from app.config.settings import get_settings
from app.database.connection import (
    document_chunks_collection,
    documents_collection,
    knowledge_sources_collection,
)
from app.models.audit import AuditAction
from app.models.document import ALLOWED_EXTENSIONS, DocumentStatus, KnowledgeCategory, new_document_record
from app.models.user import Region, Role
from app.schemas.document import ChunkOut, DocumentOut, DocumentUpdateRequest
from app.services.hitl.approvals import record_knowledge_decision
from app.services.ingestion.errors import IngestionError
from app.services.ingestion.pipeline import extract_chunks
from app.utils.audit import write_audit_log

router = APIRouter(prefix="/admin/knowledge", tags=["admin-knowledge"])
require_knowledge_steward = require_roles(Role.ADMIN, Role.SUPER)


def _to_out(document: dict) -> DocumentOut:
    return DocumentOut(
        id=str(document["_id"]),
        filename=document["filename"],
        file_type=document["file_type"],
        category=document["category"],
        region=document.get("region"),
        description=document.get("description") or "",
        status=document["status"],
        uploaded_by=document["uploaded_by"],
        page_count=document.get("page_count"),
        chunk_count=document.get("chunk_count") or 0,
        error_message=document.get("error_message"),
        created_at=document.get("created_at"),
    )


def _normalize_region(category: KnowledgeCategory, region_raw: str | None) -> str | None:
    region_value = (region_raw or "").strip().upper() or None
    if category == KnowledgeCategory.REGIONAL:
        if region_value is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Regional knowledge must include a region.",
            )
        try:
            return Region(region_value).value
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown region. Use a value from the sample region list until SLT provides the official list.",
            ) from exc
    if category == KnowledgeCategory.GENERAL and region_value is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GENERAL knowledge must not have a region.",
        )
    if region_value is None:
        return None
    try:
        return Region(region_value).value
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown region.") from exc


def _detect_file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix == "jpeg":
        suffix = "jpg"
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload PDF, Word (.docx), CSV, or Excel (.xlsx).",
        )
    return suffix


def _safe_filename(original: str) -> str:
    name = Path(original or "upload.bin").name
    name = name.replace("..", "")
    return name or "upload.bin"


async def _get_document_or_404(document_id: str) -> dict:
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document id")
    document = await documents_collection().find_one({"_id": ObjectId(document_id)})
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_knowledge(
    file: UploadFile = File(...),
    category: KnowledgeCategory = Form(...),
    description: str = Form(""),
    region: str | None = Form(None),
    actor: CurrentUser = Depends(require_knowledge_steward),
):
    settings = get_settings()
    original_name = _safe_filename(file.filename or "")
    file_type = _detect_file_type(original_name)
    region_value = _normalize_region(category, region)

    payload = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(payload) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(payload) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is larger than {settings.max_upload_mb} MB.",
        )
    if file_type == "pdf" and not payload.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is not a valid PDF.")
    if file_type in {"xlsx", "docx"} and not payload.startswith(b"PK"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is not a valid .{file_type} package.",
        )
    if file_type == "xls":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Legacy .xls is not supported. Save the file as .xlsx and upload again.",
        )

    record = new_document_record(
        filename=original_name,
        stored_path="",
        file_type=file_type,
        category=category.value,
        region=region_value,
        description=(description or "").strip(),
        uploaded_by=actor.id,
        status=DocumentStatus.PROCESSING,
    )
    insert = await documents_collection().insert_one(record)
    document_id = insert.inserted_id

    upload_root = Path(settings.upload_dir)
    target_dir = upload_root / str(document_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_path = target_dir / original_name
    stored_path.write_bytes(payload)

    await documents_collection().update_one(
        {"_id": document_id},
        {"$set": {"stored_path": str(stored_path), "updated_at": datetime.now(timezone.utc)}},
    )
    await knowledge_sources_collection().insert_one(
        {
            "document_id": str(document_id),
            "filename": original_name,
            "file_type": file_type,
            "category": category.value,
            "region": region_value,
            "uploaded_by": actor.id,
            "created_at": datetime.now(timezone.utc),
        }
    )
    await write_audit_log(
        user_id=actor.id,
        action=AuditAction.DOCUMENT_UPLOADED.value,
        resource=f"documents/{document_id}",
        status_="PROCESSING",
    )

    try:
        page_count, chunks = await run_in_threadpool(
            extract_chunks,
            path=stored_path,
            file_type=file_type,
            filename=original_name,
            category=category.value,
            region=region_value,
        )
    except IngestionError as exc:
        await documents_collection().update_one(
            {"_id": document_id},
            {
                "$set": {
                    "status": DocumentStatus.FAILED.value,
                    "error_message": exc.message,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        document = await documents_collection().find_one({"_id": document_id})
        return _to_out(document)
    except Exception:
        await documents_collection().update_one(
            {"_id": document_id},
            {
                "$set": {
                    "status": DocumentStatus.FAILED.value,
                    "error_message": "Ingestion failed unexpectedly.",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        raise

    now = datetime.now(timezone.utc)
    chunk_docs = [
        {
            **chunk,
            "document_id": str(document_id),
            "status": DocumentStatus.PENDING.value,
            "created_at": now,
        }
        for chunk in chunks
    ]
    if chunk_docs:
        await document_chunks_collection().insert_many(chunk_docs)

    await documents_collection().update_one(
        {"_id": document_id},
        {
            "$set": {
                "status": DocumentStatus.PENDING.value,
                "page_count": page_count,
                "chunk_count": len(chunk_docs),
                "error_message": None,
                "updated_at": now,
            }
        },
    )
    document = await documents_collection().find_one({"_id": document_id})
    return _to_out(document)


@router.get("", response_model=list[DocumentOut])
async def list_knowledge(_steward: CurrentUser = Depends(require_knowledge_steward)):
    cursor = documents_collection().find({}).sort("created_at", -1)
    return [_to_out(document) async for document in cursor]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_knowledge(document_id: str, _steward: CurrentUser = Depends(require_knowledge_steward)):
    return _to_out(await _get_document_or_404(document_id))


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
async def list_chunks(document_id: str, _steward: CurrentUser = Depends(require_knowledge_steward)):
    await _get_document_or_404(document_id)
    cursor = document_chunks_collection().find({"document_id": document_id}).sort("chunk_index", 1)
    chunks = []
    async for document in cursor:
        chunks.append(
            ChunkOut(
                id=str(document["_id"]),
                document_id=document["document_id"],
                content=document["content"],
                category=document["category"],
                region=document.get("region"),
                filename=document.get("filename") or "",
                source_page=document.get("source_page"),
                source_row=document.get("source_row"),
                sheet_name=document.get("sheet_name"),
                chunk_index=document.get("chunk_index") or 0,
                status=document["status"],
            )
        )
    return chunks


@router.put("/{document_id}", response_model=DocumentOut)
async def update_knowledge(
    document_id: str,
    payload: DocumentUpdateRequest,
    actor: CurrentUser = Depends(require_knowledge_steward),
):
    document = await _get_document_or_404(document_id)
    updates: dict = {}
    if payload.description is not None:
        updates["description"] = payload.description.strip()
    if payload.category is not None:
        region_for_check = payload.region.value if payload.region else document.get("region")
        region_value = _normalize_region(payload.category, region_for_check)
        updates["category"] = payload.category.value
        updates["region"] = region_value
    elif payload.region is not None:
        category = KnowledgeCategory(document["category"])
        updates["region"] = _normalize_region(category, payload.region.value)

    if not updates:
        return _to_out(document)

    updates["updated_at"] = datetime.now(timezone.utc)
    await documents_collection().update_one({"_id": ObjectId(document_id)}, {"$set": updates})
    chunk_updates = {key: value for key, value in updates.items() if key in {"category", "region"}}
    if chunk_updates:
        await document_chunks_collection().update_many({"document_id": document_id}, {"$set": chunk_updates})
    await write_audit_log(
        user_id=actor.id,
        action=AuditAction.DOCUMENT_UPDATED.value,
        resource=f"documents/{document_id}",
        status_="SUCCESS",
    )
    return _to_out(await _get_document_or_404(document_id))


@router.post("/{document_id}/approve", response_model=DocumentOut)
async def approve_knowledge(document_id: str, actor: CurrentUser = Depends(require_knowledge_steward)):
    document = await _get_document_or_404(document_id)
    if document["status"] not in {DocumentStatus.PENDING.value, DocumentStatus.REJECTED.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PENDING (or previously REJECTED) documents can be approved.",
        )
    if document.get("chunk_count", 0) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document has no extracted text chunks, so it cannot be approved for retrieval.",
        )
    now = datetime.now(timezone.utc)
    await documents_collection().update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"status": DocumentStatus.APPROVED.value, "updated_at": now, "error_message": None}},
    )
    await document_chunks_collection().update_many(
        {"document_id": document_id},
        {"$set": {"status": DocumentStatus.APPROVED.value}},
    )
    await record_knowledge_decision(document_id=document_id, admin_id=actor.id, decision="APPROVED")
    await write_audit_log(
        user_id=actor.id,
        action=AuditAction.DOCUMENT_APPROVED.value,
        resource=f"documents/{document_id}",
        status_="SUCCESS",
    )
    return _to_out(await _get_document_or_404(document_id))


@router.post("/{document_id}/reject", response_model=DocumentOut)
async def reject_knowledge(document_id: str, actor: CurrentUser = Depends(require_knowledge_steward)):
    document = await _get_document_or_404(document_id)
    if document["status"] not in {DocumentStatus.PENDING.value, DocumentStatus.APPROVED.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PENDING or APPROVED documents can be rejected.",
        )
    now = datetime.now(timezone.utc)
    await documents_collection().update_one(
        {"_id": ObjectId(document_id)},
        {"$set": {"status": DocumentStatus.REJECTED.value, "updated_at": now}},
    )
    await document_chunks_collection().update_many(
        {"document_id": document_id},
        {"$set": {"status": DocumentStatus.REJECTED.value}},
    )
    await record_knowledge_decision(document_id=document_id, admin_id=actor.id, decision="REJECTED")
    await write_audit_log(
        user_id=actor.id,
        action=AuditAction.DOCUMENT_REJECTED.value,
        resource=f"documents/{document_id}",
        status_="SUCCESS",
    )
    return _to_out(await _get_document_or_404(document_id))


@router.delete("/{document_id}")
async def delete_knowledge(document_id: str, admin: CurrentUser = Depends(require_roles(Role.ADMIN))):
    document = await _get_document_or_404(document_id)
    stored = document.get("stored_path")
    if stored:
        path = Path(stored)
        if path.exists():
            path.unlink()
        parent = path.parent
        if parent.exists() and parent.name == document_id:
            try:
                parent.rmdir()
            except OSError:
                pass
    await document_chunks_collection().delete_many({"document_id": document_id})
    await documents_collection().delete_one({"_id": ObjectId(document_id)})
    await write_audit_log(
        user_id=admin.id,
        action=AuditAction.DOCUMENT_DELETED.value,
        resource=f"documents/{document_id}",
        status_="SUCCESS",
    )
    return {"message": "Document deleted"}
