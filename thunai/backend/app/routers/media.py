from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import machines_service, photos, serialize
from .. import media as media_service
from ..config import get_config
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


class PhotoReadIn(BaseModel):
    machine_no: str
    note: str = Field(default="", max_length=500)


@router.post("/{media_id}/read")
def read_photo(media_id: int, body: PhotoReadIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Photo-based diagnosis: what the AI reads from the photo (SPEC 12.4). Shown to the technician."""
    md = db.get(LogMedia, media_id)
    if md is None or md.kind != "photo":
        raise HTTPException(404, "Photo not found")
    if md.created_by != user.id and user.role == "technician":
        raise HTTPException(403, "Not your photo")
    machine = machines_service.get_machine(db, body.machine_no)
    observation = photos.read(db, md, machine, body.note)
    db.commit()
    return {
        "media_id": md.id,
        "enabled": get_config().photos_to_ai,
        "observation": observation,
        "alarm": photos.suggestion(db, machine, observation),
    }


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
