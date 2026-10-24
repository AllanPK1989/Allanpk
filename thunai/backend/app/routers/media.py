from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import media as media_service
from .. import serialize
from ..db import get_db
from ..models import LogMedia, User
from ..security import current_user

router = APIRouter(prefix="/api/media", tags=["media"])


@router.post("/audio")
def upload_audio(
    file: UploadFile = File(...),
    language: str = "en",
    transcribe: bool = True,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    md = media_service.save_upload(db, user, file, "audio")
    text = media_service.transcribe(db, md, language) if transcribe else None
    db.commit()
    return {"media_id": md.id, "transcript": text or "", "status": md.status, "provider": md.stt_provider}


@router.post("/photo")
def upload_photo(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    md = media_service.save_upload(db, user, file, "photo")
    db.commit()
    return {"media_id": md.id}


@router.get("/{media_id}")
def get_media(media_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    md = db.get(LogMedia, media_id)
    if md is None:
        raise HTTPException(404, "Not found")
    if md.purged_at is not None:
        raise HTTPException(410, "File removed after the retention period")
    if user.role == "technician" and md.created_by != user.id and md.log_id is None:
        raise HTTPException(403, "Not allowed")
    return FileResponse(media_service.path_of(md), media_type=md.mime)


@router.get("/{media_id}/info")
def media_info(media_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    md = db.get(LogMedia, media_id)
    if md is None:
        raise HTTPException(404, "Not found")
    return serialize.media(md)
