"""Spare parts: a read-only mirror of the stores system (SPEC 12.2).

Stock comes from a file import or the parts API; Thunai never changes it. The catalogue lets the
AI cite real part numbers and lets technicians see stock and store location next to a step.
"""
import re
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from . import audit
from .models import Machine, MachineType, PartFit, SparePart, User, utcnow

# Part numbers look like "SY5120-5DZ-01", "DSNU-25-100-PPV-A" or "1234567". A token is a run of
# letters, digits and - / . that starts and ends with a letter or digit.
PART_TOKEN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9\-/.]*[A-Za-z0-9])?")
FIELDS = ("description", "unit", "stock_qty", "min_qty", "location", "stock_at")


def _key(part_no: str) -> str:
    return (part_no or "").strip().upper()


def _match_keys(part: SparePart) -> str:
    keys = [_key(part.part_no), *(_key(a) for a in part.alt_part_nos or [])]
    return (" " + " ".join(k for k in keys if k) + " ")[:600]


def info(part: SparePart) -> dict:
    return {
        "part_no": part.part_no,
        "description": part.description,
        "unit": part.unit,
        "stock_qty": part.stock_qty,
        "min_qty": part.min_qty,
        "location": part.location,
        "stock_at": part.stock_at.isoformat() if part.stock_at else None,
        "low": part.low,
        "alt_part_nos": part.alt_part_nos or [],
    }


def serialize(part: SparePart) -> dict:
    out = info(part)
    out.update(id=part.id, active=part.active, source=part.source, fits=len(part.fits))
    return out


def for_machine(db: Session, machine: Machine) -> list[SparePart]:
    """Active parts that fit the machine or its type, or match one of its components' part numbers."""
    fit_filter = [PartFit.machine_id == machine.id]
    if machine.machine_type_id:
        fit_filter.append(PartFit.machine_type_id == machine.machine_type_id)
    conditions = [SparePart.fits.any(or_(*fit_filter))]
    for c in machine.components:
        if c.active and c.part_no.strip():
            conditions.append(SparePart.match_keys.contains(f" {_key(c.part_no)} ", autoescape=True))
    return list(
        db.scalars(
            select(SparePart)
            .where(SparePart.active.is_(True), or_(*conditions))
            .options(selectinload(SparePart.fits))
            .order_by(SparePart.part_no)
            .limit(200)
        )
    )


def index(parts: list[SparePart]) -> dict[str, SparePart]:
    """Upper-case part number (and manufacturer numbers) → part, for matching text."""
    out: dict[str, SparePart] = {}
    for p in parts:
        for key in (_key(p.part_no), *(_key(a) for a in p.alt_part_nos or [])):
            if key and key not in out:
                out[key] = p
    return out


def find_in_text(text: str, idx: dict[str, SparePart]) -> list[SparePart]:
    """Catalogue parts whose number appears in the text as a whole word (any case). No fuzzy matching."""
    found: list[SparePart] = []
    for token in PART_TOKEN.findall(text or ""):
        part = idx.get(token.upper())
        if part is not None and part not in found:
            found.append(part)
    return found


def search(db: Session, q: str, machine: Machine | None = None, limit: int = 20) -> list[SparePart]:
    """Parts picker in the log form: this machine's parts first, then the whole catalogue."""
    q = (q or "").strip()
    query = select(SparePart).where(SparePart.active.is_(True))
    if q:
        query = query.where(
            or_(
                SparePart.match_keys.contains(_key(q), autoescape=True),
                SparePart.description.icontains(q, autoescape=True),
            )
        )
    rows = list(db.scalars(query.options(selectinload(SparePart.fits)).order_by(SparePart.part_no).limit(200)))
    if machine is not None:
        mine = {p.id for p in for_machine(db, machine)}
        rows.sort(key=lambda p: (p.id not in mine, p.part_no))
    return rows[:limit]


def _number(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError:
        raise ValueError(f"not a number: {value}")


def upsert(db: Session, user: User | None, rows: list[tuple[int, dict]], source: str) -> dict:
    """Create or update parts by part number. Rows are (row number, values) from a file or the API.

    values: part_no, description, unit, stock_qty, min_qty, location, stock_at (datetime or None),
    alt_part_nos (list), machine_nos (list), machine_types (list). A part's fits are replaced by the
    fits listed for it in this batch, when any are listed; otherwise they stay as they are.
    """
    machines = {m.machine_no.upper(): m.id for m in db.scalars(select(Machine))}
    types = {t.name.lower(): t.id for t in db.scalars(select(MachineType))}
    created = updated = 0
    errors: list[dict] = []
    fits: dict[str, set[tuple[str, int]]] = {}
    seen: dict[str, SparePart] = {}
    now = utcnow()
    for row_no, v in rows:
        part_no = (v.get("part_no") or "").strip()
        if not part_no:
            errors.append({"row": row_no, "error": "Missing part number"})
            continue
        if str(v.get("description", "")).startswith("[SAMPLE] Delete"):
            continue
        try:
            stock = _number(v.get("stock_qty"))
            minimum = _number(v.get("min_qty"))
        except ValueError as e:
            errors.append({"row": row_no, "error": str(e)})
            continue
        unknown = [m for m in v.get("machine_nos") or [] if m.strip().upper() not in machines]
        unknown += [t for t in v.get("machine_types") or [] if t.strip().lower() not in types]
        if unknown:
            errors.append({"row": row_no, "error": f"Unknown machine or machine type: {', '.join(unknown)}"})
            continue
        key = _key(part_no)
        part = seen.get(key) or db.scalar(select(SparePart).where(func.upper(SparePart.part_no) == key))
        before = audit.snapshot(part) if part else None
        if part is None:
            part = SparePart(part_no=part_no[:80], active=True)
            db.add(part)
            created += 1
        elif key not in seen:
            updated += 1
        seen[key] = part
        if v.get("description"):
            part.description = str(v["description"])[:300]
        if v.get("unit"):
            part.unit = str(v["unit"])[:20]
        if v.get("location"):
            part.location = str(v["location"])[:120]
        if stock is not None:
            part.stock_qty = stock
            stamp = v.get("stock_at")
            part.stock_at = stamp if isinstance(stamp, datetime) else now
        if minimum is not None:
            part.min_qty = minimum
        alts = [a.strip() for a in v.get("alt_part_nos") or [] if a and a.strip()]
        if alts:
            part.alt_part_nos = sorted({*(part.alt_part_nos or []), *alts})
        part.match_keys = _match_keys(part)
        part.source = source[:40]
        listed = fits.setdefault(key, set())
        listed.update(("m", machines[m.strip().upper()]) for m in v.get("machine_nos") or [])
        listed.update(("t", types[t.strip().lower()]) for t in v.get("machine_types") or [])
        db.flush()
        if before is not None:
            audit.record(db, user, "spare_part", part.part_no, "update", before, audit.snapshot(part))
    for key, listed in fits.items():
        if not listed:
            continue
        part = seen[key]
        part.fits.clear()
        for kind, ref in sorted(listed):
            part.fits.append(PartFit(machine_id=ref if kind == "m" else None, machine_type_id=ref if kind == "t" else None))
    db.flush()
    audit.record(db, user, "import", "spare_parts", "import", None, {"created": created, "updated": updated, "errors": len(errors), "source": source})
    return {"created": created, "updated": updated, "errors": errors}


def set_active(db: Session, user: User, part: SparePart, active: bool) -> SparePart:
    before = audit.snapshot(part)
    part.active = active
    audit.record(db, user, "spare_part", part.part_no, "update", before, audit.snapshot(part))
    return part
