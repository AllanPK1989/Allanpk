"""Safety rules enforced in code. No setting, prompt or role can switch these off.

1. check_request(): refuse requests to bypass/defeat safety devices, force PLC outputs, edit the
   PLC program or open a pressure vessel under pressure, before any AI call.
2. enforce_procedure(): reject AI output that contains such instructions, make sure the first
   step is energy isolation / LOTO (plus stored-air release for pneumatics and a pressure step
   for autoclaves), badge live electrical measurements as "Authorised electrician only",
   drop invented source references and label steps without evidence as general suggestions.
"""
import re
from dataclasses import dataclass

from .ai.schemas import Step, TroubleshootOut

# Words for safety devices (English, as said on the floor, plus common Tamil-script spellings).
DEVICE = (
    r"(?:\b(?:inter\s*-?\s*locks?|guards?|light\s*curtains?|e\s*-?\s*stops?|emergency\s*stops?|"
    r"safety\s*(?:relay|switch|sensor|door|circuit|plc|mat|scanner|interlock|devices?)|door\s*switch|"
    r"two\s*-?\s*hand(?:\s*control)?|area\s*sensor|safety)\b|இன்டர்லாக்|இண்டர்லாக்|கார்டு|எமர்ஜென்சி)"
)
# Clear "defeat" verbs, matched before or after the device ("bypass the interlock",
# "interlock bypass pannu").
STRONG = (
    r"(?:\b(?:by\s*-?\s*pass\w*|jumper\w*|override\w*|overrid(?:e|ing)|defeat\w*|cheat\w*|"
    r"(?:mute|disable)\s*(?:pannu|panna|pannalaam|pannalam|panrathu|karo))\b|பைபாஸ்|ஜம்பர்)"
)
# Weaker verbs, only matched before the device ("disable the light curtain"). Deliberately
# excludes "remove", "open" and "switch off": removing a guard after LOTO is normal work.
WEAK = (
    r"(?:\b(?:jump(?:ing)?|short(?:ing|en)?\s+(?:out|the|it|across)|disabl(?:e|ing)|mute|"
    r"tape\s*(?:down|over|up)|tie\s*(?:down|up)|wedg(?:e|ing)|hold\s*down|keep\s*(?:it\s*)?pressed|"
    r"trick|fool)\b|ஷார்ட்)"
)
GAP = r"[^.!?\n]{0,40}?"
DEFEAT_DEVICE = re.compile(rf"(?:{STRONG}|{WEAK}){GAP}{DEVICE}|{DEVICE}{GAP}{STRONG}", re.I)
# "Light curtain keeps stopping. How do I bypass it?": the device is in another sentence.
DEFEAT_PRONOUN = re.compile(
    rf"(?:{STRONG}|{WEAK})\s*(?:across\s+|over\s+)?(?:it|this|that|them|one\s+button|the\s+button|"
    r"both\s+buttons|the\s+switch|the\s+sensor)\b",
    re.I,
)
DEVICE_ANYWHERE = re.compile(DEVICE, re.I)
PLC_FORCE = re.compile(r"\bforc\w*\b[^.!?\n]{0,30}\b(?:outputs?|inputs?|bits?|coils?|[xym]\d+)\b", re.I)
PLC_EDIT = re.compile(
    r"\b(?:edit|chang|modif|alter|download|upload|writ|rewrit|online\s*edit)\w*\b[^.!?\n]{0,30}"
    r"\b(?:program|ladder|logic|code)\b",
    re.I,
)
PLC_WORDS = re.compile(r"\b(plc|ladder|gx\s*works\w*|fx5u)\b", re.I)
PRESSURE_OPEN = re.compile(
    r"\b(?:open|unlock|unbolt|loosen)\w*\b[^.!?\n]{0,40}\b(?:autoclave|pressure\s*vessel|vessel|"
    r"steam\s*(?:line|valve|door)|door|lid)\b[^.!?\n]{0,50}(?:\bunder\s*pressure|\bpressuri[sz]ed|"
    r"\bwhile\s*(?:it\s*is\s*|still\s*)?(?:hot|running|pressur\w*)|\bwith\s*pressure|\bstill\s*pressur\w*)",
    re.I,
)
NEGATION = re.compile(r"\b(never|not|don'?t|do\s+not|no|without|avoid|must\s+not)\b", re.I)
NEGATION_AFTER_TA = re.compile(r"^[^.!?\n]{0,30}(கூடாது|வேண்டாம்|பண்ணாதீங்க|செய்யாதீங்க)")
SENTENCE = re.compile(r"[^.!?\n]+")

LIVE_MEASURE = re.compile(
    r"\b(?:measur|check|test|read|prob)\w*\b[^.!?\n]{0,40}(?:\bvoltage|\bvolts?\b|\b\d+\s*v\b|\bv\s*(?:ac|dc)\b|"
    r"\bcurrent\s*(?:draw|reading)|\bamps?\b|\bampere|\blive\b)|\b(?:multi\s*-?meter|clamp\s*meter|line\s*tester|"
    r"voltage\s*tester)\b",
    re.I,
)
PNEUMATIC = re.compile(r"\b(pneumatic|air|cylinders?|solenoid\s*valves?|frl|festo|valve\s*terminal)\b", re.I)
PRESSURE_MACHINE = re.compile(r"\b(autoclaves?|curing|steam|pressure\s*vessels?|boiler)\b", re.I)
LOTO_TEXT = re.compile(r"\b(loto|lock\s*-?\s*out|isolat\w*)\b", re.I)
AIR_RELEASE = re.compile(
    r"\b(?:release|exhaust|dump|vent)\w*\b[^.!?\n]{0,30}\b(?:air|pressure)\b|\b0\s*bar\b", re.I
)

REFUSAL = {
    "en": (
        "Thunai will not help with this. Bypassing or disabling safety devices, forcing PLC "
        "outputs, editing the PLC program or opening a vessel under pressure can kill or injure "
        "someone. Stop and call your supervisor or an authorised engineer."
    ),
    "ta": (
        "இதுக்கு Thunai உதவாது. Safety device-ஐ bypass அல்லது disable பண்றது, PLC output force "
        "பண்றது, PLC program மாத்துறது, pressure இருக்கும்போது vessel திறக்கிறது — இதெல்லாம் "
        "உயிருக்கு ஆபத்து. நிறுத்திட்டு supervisor அல்லது authorised engineer-ஐ கூப்பிடுங்க."
    ),
}

SAFETY_STEPS = {
    "loto": {
        "kind": "safety",
        "action_en": "Switch off main power and apply LOTO before you start.",
        "action_ta": "வேலை ஆரம்பிக்கும் முன் main power-ஐ off பண்ணி LOTO போடுங்க.",
        "check_en": "Check your lock and tag are on. Press START once.",
        "check_ta": "உங்க lock, tag போட்டாச்சான்னு பாருங்க. START ஒரு தடவை அழுத்துங்க.",
        "expected_result_en": "Machine does not start.",
        "expected_result_ta": "Machine start ஆகக்கூடாது.",
        "tools": ["LOTO lock", "Tag"],
        "safety_note_en": "If you cannot isolate the machine, stop and call the supervisor.",
        "safety_note_ta": "Machine-ஐ isolate பண்ண முடியலைன்னா நிறுத்திட்டு supervisor-ஐ கூப்பிடுங்க.",
    },
    "air": {
        "kind": "safety",
        "action_en": "Close the main air valve. Release stored air from the system.",
        "action_ta": "Main air valve-ஐ close பண்ணுங்க. System-ல இருக்கிற air-ஐ release பண்ணுங்க.",
        "check_en": "Check the pressure gauge.",
        "check_ta": "Pressure gauge-ஐ பாருங்க.",
        "expected_result_en": "Gauge reads 0 bar. Cylinders do not move.",
        "expected_result_ta": "Gauge 0 bar காட்டணும். Cylinder அசையக்கூடாது.",
        "tools": [],
        "safety_note_en": "Cylinders can move when air comes back. Keep hands clear.",
        "safety_note_ta": "Air திரும்ப வந்தா cylinder அசையும். கை வைக்காதீங்க.",
    },
    "pressure": {
        "kind": "safety",
        "action_en": "Never open the autoclave under pressure. Check the pressure gauge first.",
        "action_ta": "Pressure இருக்கும்போது autoclave-ஐ திறக்கவே கூடாது. முதல்ல pressure gauge பாருங்க.",
        "check_en": "Check the gauge and the vessel temperature.",
        "check_ta": "Gauge-ஐயும் vessel சூட்டையும் பாருங்க.",
        "expected_result_en": "Gauge reads 0 bar and the vessel is cool.",
        "expected_result_ta": "Gauge 0 bar காட்டணும், vessel சூடு இல்லாம இருக்கணும்.",
        "tools": [],
        "safety_note_en": "If there is any pressure, stop and call the supervisor.",
        "safety_note_ta": "கொஞ்சம் pressure இருந்தாலும் நிறுத்திட்டு supervisor-ஐ கூப்பிடுங்க.",
    },
}

MAX_STEPS = 14


@dataclass
class Verdict:
    refused: bool
    reason: str = ""


def _negated(sentence: str, start: int, end: int) -> bool:
    """True for "never bypass the interlock" or "the light curtain is not muted"."""
    before = sentence[max(0, start - 40) : start]
    return bool(
        NEGATION.search(before)
        or NEGATION.search(sentence[start:end])
        or NEGATION_AFTER_TA.search(sentence[end : end + 40])
    )


def unsafe_instruction(text: str, allow_negated: bool = True) -> str:
    """Return the first unsafe phrase in the text, or "" when it is safe."""
    for sentence in SENTENCE.findall(text or ""):
        checks = [DEFEAT_DEVICE, PLC_FORCE, PRESSURE_OPEN]
        if PLC_WORDS.search(sentence):
            checks.append(PLC_EDIT)
        for pattern in checks:
            for m in pattern.finditer(sentence):
                if allow_negated and _negated(sentence, m.start(), m.end()):
                    continue
                return m.group(0).strip()
    return ""


def check_request(problem: str) -> Verdict:
    """Refuse clearly unsafe requests before calling the AI."""
    phrase = unsafe_instruction(problem)
    if phrase:
        return Verdict(True, phrase)
    if DEVICE_ANYWHERE.search(problem or ""):
        for sentence in SENTENCE.findall(problem or ""):
            for m in DEFEAT_PRONOUN.finditer(sentence):
                if not _negated(sentence, m.start(), m.end()):
                    return Verdict(True, m.group(0).strip())
    return Verdict(False)


def is_pneumatic(*texts: str) -> bool:
    return any(PNEUMATIC.search(t or "") for t in texts)


def is_pressure_machine(*texts: str) -> bool:
    return any(PRESSURE_MACHINE.search(t or "") for t in texts)


def _step_text(step: Step) -> str:
    return " ".join(
        [
            step.action_en,
            step.action_ta,
            step.check_en,
            step.check_ta,
            step.expected_result_en,
            step.expected_result_ta,
            step.safety_note_en,
            step.safety_note_ta,
        ]
    )


def find_unsafe_output(proc: TroubleshootOut) -> str:
    for step in proc.steps:
        phrase = unsafe_instruction(_step_text(step))
        if phrase:
            return f"step {step.step_no}: '{phrase}'"
    return ""


def _template_step(name: str) -> dict:
    data = dict(SAFETY_STEPS[name])
    data["tools"] = list(data["tools"])
    return data


def enforce_procedure(
    proc: TroubleshootOut, *, known_refs: set[str], pneumatic: bool, pressure_machine: bool
) -> list[dict]:
    """Return the final list of step dicts shown to the technician.

    Raises ValueError when the output contains an unsafe instruction (caller retries, then shows
    "Call supervisor").
    """
    unsafe = find_unsafe_output(proc)
    if unsafe:
        raise ValueError(f"Unsafe instruction in {unsafe}. Never suggest bypassing safety devices.")

    ai_steps = sorted(proc.steps, key=lambda s: s.step_no)[: MAX_STEPS - 3]
    all_text = " ".join(_step_text(s) for s in ai_steps)

    # Safety steps in a fixed order: LOTO, stored-air release, pressure check. The AI's own
    # first step counts as the LOTO step when it is a safety step that mentions isolation.
    first = ai_steps[0] if ai_steps else None
    ai_loto = bool(first and first.kind == "safety" and LOTO_TEXT.search(_step_text(first)))
    extra: list[dict] = []
    if pneumatic and not AIR_RELEASE.search(all_text):
        extra.append(_template_step("air"))
    if pressure_machine:
        extra.append(_template_step("pressure"))
    ordered: list[dict | Step] = []
    if ai_loto:
        ordered.append(first)
        rest = ai_steps[1:]
    else:
        ordered.append(_template_step("loto"))
        rest = ai_steps
    ordered += extra + rest

    mapping = {s.step_no: i for i, s in enumerate(ordered, start=1) if isinstance(s, Step)}
    total = len(ordered)

    def remap(target: int, default: int) -> int:
        if target in (0, -1):
            return target
        return mapping.get(target, default)

    steps: list[dict] = []
    for no, item in enumerate(ordered, start=1):
        sequential = no + 1 if no < total else 0
        if isinstance(item, dict):  # injected safety step
            item.update(
                step_no=no,
                authorised_only=False,
                if_ok_next=sequential,
                if_not_ok_next=-1,  # cannot make it safe → stop and call the supervisor
                source_refs=[],
                confidence=1.0,
                general=False,
                injected=True,
            )
            steps.append(item)
            continue
        s = item
        data = s.model_dump()
        data["step_no"] = no
        data["if_ok_next"] = remap(s.if_ok_next, sequential)
        data["if_not_ok_next"] = remap(s.if_not_ok_next, -1)
        if s is first and ai_loto:
            data["if_ok_next"] = sequential  # never skip the injected safety steps
        if data["if_ok_next"] == no:  # never loop on the same step
            data["if_ok_next"] = sequential
        data["source_refs"] = [r for r in s.source_refs if r in known_refs]
        data["general"] = not data["source_refs"] and s.kind != "safety"
        if LIVE_MEASURE.search(_step_text(s)):
            data["authorised_only"] = True  # can only be raised, never lowered
        data["confidence"] = min(max(float(s.confidence), 0.0), 1.0)
        data["injected"] = False
        steps.append(data)
    return steps
