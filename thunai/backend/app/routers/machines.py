from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import audit, logs_service, machines_service, serialize
from ..db import get_db
from ..models import AISession, BreakdownLog, Component, Machine, User
from ..schemas import ComponentIn, MachineIn, MachineUpdate
from ..security import admin_only, current_user

router = APIRouter(prefix="/api/machines", tags=["machines"])


@router.get("")
def list_machines(
    q: str = "",
    zone: str = "",
    include_inactive: bool = False,
    limit: int = Query(100, le=1000),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = select(Machine).options(selectinload(Machine.machine_type)).order_by(Machine.machine_no)
    if not (include_inactive and user.role == "admin"):
        query = query.where(Machine.active.is_(True))
    if zone:
        query = query.where(Machine.zone == zone)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.where(or_(func.lower(Machine.machine_no).like(like), func.lower(Machine.name).like(like)))
    return [serialize.machine(m) for m in db.scalars(query.limit(limit))]


@router.get("/recent")
def recent_machines(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Machines this user worked on most recently, then machines in their zone."""
    ids: list[int] = []
    for (mid,) in db.execute(
        select(BreakdownLog.machine_id).where(BreakdownLog.technician_id == user.id)
        .order_by(BreakdownLog.reported_at.desc()).limit(30)
    ).all() + db.execute(
        select(AISession.machine_id).where(AISession.technician_id == user.id)
        .order_by(AISession.created_at.desc()).limit(30)
    ).all():
        if mid not in ids:
            ids.append(mid)
    machines = {m.id: m for m in db.scalars(select(Machine).where(Machine.id.in_(ids), Machine.active.is_(True)))}
    recent = [machines[i] for i in ids if i in machines][:8]
    return [serialize.machine(m) for m in recent]


@router.get("/zones")
def zones(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return sorted(z for (z,) in db.execute(select(distinct(Machine.zone)).where(Machine.active.is_(True))) if z)


@router.get("/{machine_no}")
def machine_page(machine_no: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return machines_service.machine_page(db, machines_service.get_machine(db, machine_no))


@router.get("/{machine_no}/open-log")
def open_log(machine_no: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    machine = machines_service.get_machine(db, machine_no)
    log = logs_service.find_open_log(db, machine)
    return {"log": serialize.log(logs_service.load_log(db, log.id), full=False) if log else None}


@router.get("/{machine_no}/active-alarm")
def active_alarm(machine_no: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The alarm that pre-fills Ask Thunai and New log (PLC/SCADA feed), or null."""
    machine = machines_service.get_machine(db, machine_no)
    return {"alarm": machines_service.active_alarm(db, machine)}


@router.get("/{machine_no}/qr.{fmt}")
def qr(machine_no: str, fmt: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    machine = machines_service.get_machine(db, machine_no)
    if fmt not in ("svg", "png"):
        fmt = "png"
    media = "image/svg+xml" if fmt == "svg" else "image/png"
    return Response(machines_service.qr_image(machine.machine_no, fmt), media_type=media)


@router.post("", dependencies=[Depends(admin_only)])
def create_machine(body: MachineIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    machine = machines_service.create_machine(db, user, body)
    db.commit()
    return serialize.machine(machines_service.get_machine(db, machine.machine_no), with_components=True)


@router.patch("/{machine_no}", dependencies=[Depends(admin_only)])
def update_machine(machine_no: str, body: MachineUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    machine = machines_service.update_machine(db, user, machines_service.get_machine(db, machine_no), body)
    db.commit()
    return serialize.machine(machine, with_components=True)


@router.post("/{machine_no}/components", dependencies=[Depends(admin_only)])
def add_component(machine_no: str, body: ComponentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    comp = machines_service.add_component(db, user, machines_service.get_machine(db, machine_no), body)
    db.commit()
    return serialize.component(comp)


@router.patch("/{machine_no}/components/{component_id}", dependencies=[Depends(admin_only)])
def update_component(
    machine_no: str, component_id: int, body: ComponentIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    machine = machines_service.get_machine(db, machine_no)
    comp = db.get(Component, component_id)
    if comp is None or comp.machine_id != machine.id:
        raise HTTPException(404, "Component not found")
    before = audit.snapshot(comp)
    for key, value in body.model_dump().items():
        setattr(comp, key, value)
    audit.record(db, user, "component", comp.id, "update", before, audit.snapshot(comp))
    db.commit()
    return serialize.component(comp)
