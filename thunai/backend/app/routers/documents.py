from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import documents, excel, machines_service, retrieval
from ..db import get_db
from ..models import Document, User
from ..security import current_user, supervisor_or_admin

router = APIRouter(prefix="/api", tags=["documents"])


def _load(db: Session, doc_id: int) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/documents")
def upload(
    file: UploadFile = File(...),
    title: str = Form(""),
    kind: str = Form("manual"),
    machine_no: str = Form(""),
    machine_type: str = Form(""),
    user: User = Depends(supervisor_or_admin),
    db: Session = Depends(get_db),
):
    doc = documents.upload(db, user, file, title, kind, machine_no, machine_type)
    db.commit()
    db.refresh(doc)
    return documents.serialize(db, doc)


@router.get("/documents")
def list_documents(machine_no: str = "", include_inactive: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if machine_no:
        docs = documents.visible_for(db, machines_service.get_machine(db, machine_no))
    else:
        q = db.query(Document).order_by(Document.created_at.desc())
        if not include_inactive:
            q = q.filter(Document.active.is_(True))
        docs = q.limit(500).all()
    return [documents.serialize(db, d) for d in docs]


@router.get("/documents/{doc_id}/file")
def get_file(doc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = _load(db, doc_id)
    return FileResponse(documents.path_of(doc), media_type=doc.mime, filename=None)


@router.patch("/documents/{doc_id}")
def set_active(doc_id: int, body: dict, user: User = Depends(supervisor_or_admin), db: Session = Depends(get_db)):
    doc = documents.set_active(db, user, _load(db, doc_id), bool(body.get("active", True)))
    db.commit()
    return documents.serialize(db, doc)


@router.get("/alarms/lookup")
def lookup(machine_no: str, code: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    alarm = retrieval.lookup_alarm(db, machines_service.get_machine(db, machine_no), code)
    if alarm is None:
        return {"alarm": None}
    return {"alarm": {"code": alarm.code, "message": alarm.message, "cause": alarm.cause, "remedy": alarm.remedy}}


@router.get("/admin/templates/alarms.xlsx")
def alarm_template(user: User = Depends(supervisor_or_admin)):
    return Response(
        excel.template("alarms"),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="thunai-alarms-template.xlsx"'},
    )
