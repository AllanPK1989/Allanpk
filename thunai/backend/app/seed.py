"""SAMPLE data for demos and the pilot set-up. Not plant data.

Everything here is clearly marked: machine numbers start with DEMO-, names start with [SAMPLE],
users start with D- and are named "[Sample] ...". Sample users have PIN 1234. Before go-live,
start with an empty database (see RUNBOOK.md) or deactivate these users and machines.
The glossary entries are general technical terms and can be kept.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import machines_service
from .knowledge import group_key
from .config import get_config
from .logs_service import set_text
from .models import BreakdownLog, Component, FaultCard, Glossary, LogClassification, LogPart, User, utcnow
from .schemas import MachineIn
from .security import hash_pin
from .shifts import downtime_minutes, shift_for
from .settings_store import DEFAULTS

SAMPLE_PIN = "1234"

GLOSSARY = [
    ("solenoid valve", "சோலனாய்டு வால்வு", ["solenoid", "sol valve"], "pneumatic"),
    ("solenoid coil", "சோலனாய்டு காயில்", [], "pneumatic"),
    ("proximity sensor", "ப்ராக்ஸிமிட்டி சென்சார்", ["proxy", "prox", "proxy sensor"], "sensor"),
    ("cylinder", "சிலிண்டர்", ["cyl"], "pneumatic"),
    ("FRL unit", "FRL யூனிட்", ["air filter regulator"], "pneumatic"),
    ("MCB", "எம்சிபி", [], "electrical"),
    ("contactor", "காண்டாக்டர்", [], "electrical"),
    ("relay", "ரிலே", [], "electrical"),
    ("limit switch", "லிமிட் ஸ்விட்ச்", [], "sensor"),
    ("PLC", "பிஎல்சி", [], "plc"),
    ("HMI", "எச்எம்ஐ", [], "plc"),
    ("LOTO", "லோட்டோ", ["lock out tag out"], "safety"),
    ("print head", "பிரிண்ட் ஹெட்", [], "printer"),
    ("gasket", "காஸ்கெட்", [], "mechanical"),
    ("bearing", "பேரிங்", [], "mechanical"),
    ("thermocouple", "தெர்மோகப்பிள்", [], "sensor"),
    ("not working", "ஆகல", ["aagala", "agala", "varala", "work aagala"], "spoken"),
    ("replaced", "மாத்தினேன்", ["maathiten", "mathiten", "maathinen", "change panniten"], "spoken"),
]

TYPES = {
    "SF": "Sand filling machine",
    "NT": "Notching machine",
    "AC": "Curing autoclave",
    "RT": "Resistance test station",
    "LP": "Label printer",
}

MACHINES = [
    ("DEMO-SF-01", "[SAMPLE] Sand filling machine 1", "SF", "Bussmann Zone 1", "Line 1", "Mitsubishi FX5U", "A"),
    ("DEMO-SF-02", "[SAMPLE] Sand filling machine 2", "SF", "Bussmann Zone 1", "Line 2", "Mitsubishi FX5U", "A"),
    ("DEMO-LP-01", "[SAMPLE] Label printer 1", "LP", "Bussmann Zone 1", "Line 1", "", "B"),
    ("DEMO-NT-01", "[SAMPLE] Notching machine 1", "NT", "Notching", "Notching line", "Mitsubishi FX5U", "A"),
    ("DEMO-AC-01", "[SAMPLE] Curing autoclave 1", "AC", "Zone 2", "Curing", "Mitsubishi FX5U", "A"),
    ("DEMO-RT-01", "[SAMPLE] Resistance test station 1", "RT", "Zone 2", "Testing", "Mitsubishi FX5U", "B"),
]

# Part numbers are left empty on purpose: never invent them.
COMPONENTS = {
    "SF": [
        ("Filling cylinder", "pneumatic", "Festo", "Filling head, left side"),
        ("5/2 solenoid valve", "pneumatic", "Festo", "Valve manifold, rear panel"),
        ("Home proximity sensor", "sensor", "", "Cylinder home position"),
        ("FRL unit", "pneumatic", "Festo", "Air inlet, rear"),
        ("Vibrator motor", "electrical", "", "Under the hopper"),
    ],
    "LP": [("Print head", "mechanical", "SATO", "Printer"), ("Label sensor", "sensor", "SATO", "Label path")],
    "NT": [("Notching punch cylinder", "pneumatic", "Festo", "Punch station"), ("Light curtain", "sensor", "", "Operator side")],
    "AC": [("Door gasket", "mechanical", "", "Autoclave door"), ("Pressure gauge", "sensor", "", "Front panel"),
           ("Steam inlet valve", "mechanical", "", "Steam line")],
    "RT": [("HIOKI resistance meter", "electrical", "HIOKI", "Test station"), ("Test probe set", "electrical", "", "Fixture")],
}

USERS = [
    ("D-ADMIN", "[Sample] Admin", "admin", "", "en"),
    ("D-SUP1", "[Sample] Supervisor Zone 1", "supervisor", "Bussmann Zone 1", "en"),
    ("D-SUP2", "[Sample] Supervisor Zone 2", "supervisor", "Zone 2", "en"),
    ("D-TECH1", "[Sample] Technician 1", "technician", "Bussmann Zone 1", "ta"),
    ("D-TECH2", "[Sample] Technician 2", "technician", "Zone 2", "en"),
]

# (machine, days ago, start, minutes, status, issue(orig, en, ta), cause(...), action(...), part, symptom, failure)
LOGS = [
    ("DEMO-SF-01", 52, "09:10", 35, "verified",
     ("Cylinder return aagala", "Filling cylinder not returning", "Filling cylinder return ஆகல"),
     ("Solenoid coil burnt", "Solenoid coil burnt", "Solenoid coil burn ஆயிடுச்சு"),
     ("Coil maathiten, 10 cycle check OK", "Replaced the solenoid coil. Checked 10 cycles, OK.",
      "Solenoid coil மாத்தினேன். 10 cycle check பண்ணேன், OK."),
     "Solenoid coil", "Cylinder not returning", "coil burnt"),
    ("DEMO-SF-01", 31, "15:20", 40, "verified",
     ("Cylinder slow return, sometimes stuck", "Cylinder returns slowly and sometimes sticks",
      "Cylinder மெதுவா return ஆகுது, சில நேரம் நின்னுடுது"),
     ("Coil burnt, valve hot", "Solenoid coil burnt; valve was hot", "Coil burn ஆயிடுச்சு, valve சூடா இருந்தது"),
     ("Replaced coil, checked 24 V DC at valve connector", "Replaced the coil. Checked 24 V DC at the valve connector.",
      "Coil மாத்தினேன். Valve connector-ல 24 V DC check பண்ணேன்."),
     "Solenoid coil", "Cylinder not returning", "coil burnt"),
    ("DEMO-SF-01", 18, "23:15", 25, "verified",
     ("Cylinder not returning, home sensor LED off", "Cylinder not returning; home sensor LED off",
      "Cylinder return ஆகல, home sensor LED off"),
     ("Proximity sensor loose, misaligned", "Home proximity sensor loose and misaligned",
      "Proximity sensor loose-ஆ இருந்தது, alignment மாறிடுச்சு"),
     ("Aligned sensor to 2 mm gap and tightened", "Aligned the sensor to a 2 mm gap and tightened it.",
      "Sensor-ஐ 2 mm gap-க்கு align பண்ணி tight பண்ணேன்."),
     "", "Cylinder not returning", "sensor misaligned"),
    ("DEMO-SF-01", 5, "10:30", 30, "closed",
     ("Cylinder return aagala again", "Filling cylinder not returning again", "Filling cylinder திரும்ப return ஆகல"),
     ("Solenoid coil burnt", "Solenoid coil burnt", "Solenoid coil burn ஆயிடுச்சு"),
     ("Coil changed", "Changed the solenoid coil.", "Solenoid coil மாத்தினேன்."),
     "Solenoid coil", "Cylinder not returning", "coil burnt"),
    ("DEMO-SF-02", 40, "11:00", 45, "verified",
     ("Air leak at FRL, pressure 3 bar", "Air leak at the FRL; pressure only 3 bar", "FRL-ல air leak, pressure 3 bar தான்"),
     ("FRL bowl seal worn", "FRL bowl seal worn", "FRL bowl seal தேஞ்சு போச்சு"),
     ("Replaced bowl seal, pressure 6 bar OK", "Replaced the bowl seal. Pressure 6 bar, OK.",
      "Bowl seal மாத்தினேன். Pressure 6 bar, OK."),
     "FRL bowl seal", "Low air pressure", "seal worn"),
    ("DEMO-LP-01", 12, "07:40", 20, "verified",
     ("Label print faded", "Label print is faded", "Label print மங்கலா வருது"),
     ("Print head dirty", "Print head dirty", "Print head அழுக்கா இருந்தது"),
     ("Cleaned print head with IPA, adjusted darkness", "Cleaned the print head with IPA and adjusted print darkness.",
      "Print head-ஐ IPA வச்சு clean பண்ணி, darkness adjust பண்ணேன்."),
     "", "Label print faded", "dirty print head"),
    ("DEMO-AC-01", 9, "14:30", 90, "closed",
     ("Autoclave door seal leaking steam", "Steam leaking from the autoclave door seal",
      "Autoclave door seal-ல steam leak ஆகுது"),
     ("Door gasket worn", "Door gasket worn", "Door gasket தேஞ்சு போச்சு"),
     ("Waited for 0 bar and cool down, replaced gasket", "Waited for 0 bar and cool-down, then replaced the gasket.",
      "0 bar வந்து cool ஆன அப்புறம் gasket மாத்தினேன்."),
     "Door gasket", "Steam leak at door", "gasket worn"),
]

FAULT_CARD = {
    "machine": "DEMO-SF-01",
    "symptom": "Filling cylinder not returning",
    "symptom_ta": "Filling cylinder return ஆகல",
    "causes": [
        {"cause": "Solenoid coil burnt", "cause_ta": "Solenoid coil burn ஆயிடுச்சு", "count": 3},
        {"cause": "Home proximity sensor misaligned", "cause_ta": "Home proximity sensor alignment மாறிடுச்சு", "count": 1},
    ],
    "steps_en": [
        "Check the solenoid coil connector and cable for burn marks.",
        "Measure coil resistance with a multimeter. Compare with the coil label.",
        "If the coil is burnt or open, replace the solenoid coil.",
        "Check the home sensor is tight. Gap should be 2 mm.",
        "Remove your LOTO. Restore air and power. Keep hands clear.",
        "Run 10 cycles and watch the cylinder return.",
    ],
    "steps_ta": [
        "Solenoid coil connector, cable-ல burn mark இருக்கான்னு பாருங்க.",
        "Multimeter-ல coil resistance அளந்து, coil label-ஓட compare பண்ணுங்க.",
        "Coil burn அல்லது open-ஆ இருந்தா, solenoid coil-ஐ மாத்துங்க.",
        "Home sensor tight-ஆ இருக்கான்னு பாருங்க. Gap 2 mm இருக்கணும்.",
        "உங்க LOTO-ஐ எடுங்க. Air, power திரும்ப கொடுங்க. கை வைக்காதீங்க.",
        "10 cycle ஓட்டி cylinder return ஆகுதான்னு பாருங்க.",
    ],
    "parts": ["Solenoid coil"],
    "tools": ["Multimeter", "Screwdriver set", "Spanner set"],
    "avg_fix_min": 33,
}


def is_empty(db: Session) -> bool:
    return db.scalar(select(User.id).limit(1)) is None


def seed(db: Session) -> None:
    tz = ZoneInfo(get_config().plant_tz)
    for term_en, term_ta, spoken, category in GLOSSARY:
        db.add(Glossary(term_en=term_en, term_ta=term_ta, spoken_variants=spoken, category=category))

    users = {}
    for emp, name, role, zone, lang in USERS:
        u = User(employee_id=emp, name=name, role=role, zone=zone, preferred_language=lang, pin_hash=hash_pin(SAMPLE_PIN))
        db.add(u)
        users[emp] = u
    db.flush()

    machines = {}
    for no, name, code, zone, line, plc, crit in MACHINES:
        m = machines_service.create_machine(
            db,
            None,
            MachineIn(
                machine_no=no, name=name, machine_type=TYPES[code], zone=zone, line=line, plc_model=plc,
                criticality=crit, key_components=", ".join(c[0] for c in COMPONENTS[code]),
                notes="Sample machine for demos. Not plant data.",
            ),
        )
        for cname, cat, make, loc in COMPONENTS[code]:
            db.add(Component(machine_id=m.id, name=cname, category=cat, make=make, location=loc))
        machines[no] = m
    db.flush()

    now_local = datetime.now(tz)
    for no, days, start, minutes, status, issue, cause, action, part, symptom, failure in LOGS:
        machine = machines[no]
        tech = users["D-TECH1"] if machine.zone == "Bussmann Zone 1" else users["D-TECH2"]
        h, m = (int(x) for x in start.split(":"))
        start_at = datetime.combine((now_local - timedelta(days=days)).date(), time(h, m), tz)
        end_at = start_at + timedelta(minutes=minutes)
        shift, shift_date = shift_for(start_at, DEFAULTS["shifts"], get_config().plant_tz)
        log = BreakdownLog(
            machine=machine, technician_id=tech.id, technician_name=tech.name, zone=machine.zone,
            shift=shift, shift_date=shift_date, reported_at=start_at, start_at=start_at, end_at=end_at,
            downtime_min=downtime_minutes(start_at, end_at), status=status, source="text",
            verified_by=users["D-SUP1"].id if status == "verified" else None,
            verified_at=end_at + timedelta(hours=4) if status == "verified" else None,
            enriched_at=utcnow(),
        )
        db.add(log)
        for field, (orig, en, ta) in zip(("issue", "root_cause", "corrective_action"), (issue, cause, action)):
            set_text(db, log, field, orig, en=en, ta=ta)
            log.texts[-1].translated_at = utcnow()
        if part:
            log.parts.append(LogPart(description=part, qty=1))
        db.flush()
        log.log_no = f"BL-{start_at.year}-{log.id:06d}"
        db.add(LogClassification(log_id=log.id, symptom_category=symptom, failure_mode=failure, confidence=0.9))

    sf01 = machines[FAULT_CARD["machine"]]
    sf_logs = db.scalars(select(BreakdownLog.id).where(BreakdownLog.machine_id == sf01.id)).all()
    db.add(
        FaultCard(
            machine_id=sf01.id,
            symptom=FAULT_CARD["symptom"],
            symptom_ta=FAULT_CARD["symptom_ta"],
            causes=FAULT_CARD["causes"],
            steps_en=FAULT_CARD["steps_en"],
            steps_ta=FAULT_CARD["steps_ta"],
            parts=FAULT_CARD["parts"],
            tools=FAULT_CARD["tools"],
            avg_fix_min=FAULT_CARD["avg_fix_min"],
            source_log_ids=list(sf_logs),
            status="approved",
            version=1,
            group_key=group_key("Cylinder not returning"),  # the logs' symptom category
            approved_by=users["D-SUP1"].id,
            approved_at=utcnow() - timedelta(days=3),
        )
    )
    db.flush()
