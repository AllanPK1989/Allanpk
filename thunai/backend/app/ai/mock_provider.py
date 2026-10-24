"""Rule-based stand-in for the AI, used for demos without an API key and in tests.

It builds answers from the retrieved plant data only (fault cards, logs). It does not translate:
missing language versions stay empty and the UI shows the original text. The UI shows a
"Demo AI" badge whenever this provider is active.
"""
import re

from ..textutil import detect_lang
from .base import AIResult

CAUSE_WORDS = re.compile(
    r"\b(burnt|burn|burned|broken|damaged|loose|worn|leak\w*|jam\w*|stuck|failed|faulty|short\w*|"
    r"cut|misalign\w*|dirty|block\w*|low|weak|bent|cracked|tripped|blown|dust|wear)\b",
    re.I,
)
ACTION_WORDS = re.compile(
    r"\b(replac\w*|chang\w*|maathi\w*|clean\w*|tighten\w*|adjust\w*|reset\w*|fix\w*|repair\w*|"
    r"refill\w*|align\w*|rewir\w*|check\w* ok|ok)\b",
    re.I,
)
PART_AFTER = re.compile(r"\b(?:replaced|changed|replace|change)\s+(?:the\s+)?([\w\s-]{2,40})", re.I)
PART_BEFORE = re.compile(r"([\w-]+(?:\s[\w-]+)?)\s+maathi\w*", re.I)

LOTO = {
    "kind": "safety",
    "action_en": "Switch off main power and apply LOTO before you start.",
    "action_ta": "வேலை ஆரம்பிக்கும் முன் main power-ஐ off பண்ணி LOTO போடுங்க.",
    "check_en": "Check the lock and tag are on. Press START once.",
    "check_ta": "Lock, tag போட்டாச்சான்னு பாருங்க. START ஒரு தடவை அழுத்துங்க.",
    "expected_result_en": "Machine does not start.",
    "expected_result_ta": "Machine start ஆகக்கூடாது.",
    "tools": ["LOTO lock", "Tag"],
    "safety_note_en": "",
    "safety_note_ta": "",
    "authorised_only": False,
}

GENERIC = [
    (
        "Read the alarm message on the HMI. Note the alarm code.",
        "HMI-ல alarm message படிங்க. Alarm code-ஐ note பண்ணுங்க.",
        "Alarm code is shown.",
        "Alarm code தெரியணும்.",
    ),
    (
        "Check cables and connectors on the faulty unit are tight.",
        "Fault இருக்கிற unit-ல cable, connector எல்லாம் tight-ஆ இருக்கான்னு பாருங்க.",
        "No loose or damaged cable.",
        "Loose அல்லது damage ஆன cable இருக்கக்கூடாது.",
    ),
    (
        "Check the sensor LED changes when the part is in place.",
        "Part வச்சதும் sensor LED மாறுதான்னு பாருங்க.",
        "LED turns on with the part in place.",
        "Part இருக்கும்போது LED on ஆகணும்.",
    ),
]


def _step(no: int, total: int, **fields) -> dict:
    base = {
        "step_no": no,
        "kind": "check",
        "action_en": "",
        "action_ta": "",
        "check_en": "",
        "check_ta": "",
        "expected_result_en": "",
        "expected_result_ta": "",
        "tools": [],
        "safety_note_en": "",
        "safety_note_ta": "",
        "authorised_only": False,
        "if_ok_next": no + 1 if no < total else 0,
        "if_not_ok_next": no + 1 if no < total else -1,
        "source_refs": [],
        "confidence": 0.5,
    }
    base.update(fields)
    return base


class MockProvider:
    name = "mock"

    def generate_json(self, *, tier, purpose, system, user, schema, max_tokens, hints) -> AIResult:
        handler = getattr(self, f"_{purpose}", None)
        if handler is None:
            return AIResult(None, "mock", error=f"mock has no handler for {purpose}")
        return AIResult(handler(hints), "mock")

    # ---- troubleshooting -----------------------------------------------------------------------
    def _clarify(self, h: dict) -> dict:
        problem = h.get("problem", "")
        questions = []
        if not h.get("alarm_code"):
            questions.append(
                {
                    "id": "hmi_alarm",
                    "text_en": "Is there an alarm on the HMI screen?",
                    "text_ta": "HMI screen-ல alarm ஏதாவது வருதா?",
                    "options": [
                        {"value": "yes", "label_en": "Yes", "label_ta": "ஆமா"},
                        {"value": "no", "label_en": "No", "label_ta": "இல்லை"},
                    ],
                }
            )
        if h.get("pneumatic"):
            questions.append(
                {
                    "id": "air_ok",
                    "text_en": "Does the FRL gauge show 5 to 6 bar?",
                    "text_ta": "FRL gauge 5 முதல் 6 bar காட்டுதா?",
                    "options": [
                        {"value": "yes", "label_en": "Yes", "label_ta": "ஆமா"},
                        {"value": "no", "label_en": "No", "label_ta": "இல்லை"},
                        {"value": "unknown", "label_en": "Not sure", "label_ta": "தெரியல"},
                    ],
                }
            )
        questions.append(
            {
                "id": "when",
                "text_en": "When did it start?",
                "text_ta": "எப்போ ஆரம்பிச்சது?",
                "options": [
                    {"value": "just_now", "label_en": "Just now", "label_ta": "இப்போதான்"},
                    {"value": "after_work", "label_en": "After maintenance", "label_ta": "Maintenance-க்கு அப்புறம்"},
                    {"value": "often", "label_en": "Happens often", "label_ta": "அடிக்கடி வருது"},
                ],
            }
        )
        return {"understood_problem_en": problem[:200], "questions": questions[:3]}

    def _troubleshoot(self, h: dict) -> dict:
        items = h.get("items", [])
        cards = [i for i in items if i["kind"] == "fault_card"]
        logs = [i for i in items if i["kind"] == "log"]
        plan: list[dict] = []
        causes: list[dict] = []
        if cards:
            card = cards[0]
            steps_en = card["data"].get("steps_en", [])
            steps_ta = card["data"].get("steps_ta", [])
            for i, text in enumerate(steps_en):
                plan.append(
                    {
                        "kind": "check" if text.lower().startswith("check") else "action",
                        "action_en": text,
                        "action_ta": steps_ta[i] if i < len(steps_ta) else "",
                        "source_refs": [card["ref"]],
                        "confidence": 0.8,
                    }
                )
            for c in card["data"].get("causes", [])[:3]:
                causes.append(
                    {
                        "cause_en": c.get("cause", ""),
                        "cause_ta": c.get("cause_ta", ""),
                        "likelihood": 0.6,
                        "source_refs": [card["ref"]],
                    }
                )
        for log in [] if cards else logs[:3]:
            d = log["data"]
            if d.get("root_cause_en"):
                plan.append(
                    {
                        "kind": "check",
                        "action_en": f"Check: {d['root_cause_en']}"[:160],
                        "action_ta": f"இதை பாருங்க: {d.get('root_cause_ta') or d['root_cause_en']}"[:160],
                        "source_refs": [log["ref"]],
                        "confidence": 0.6,
                    }
                )
                causes.append(
                    {
                        "cause_en": d["root_cause_en"],
                        "cause_ta": d.get("root_cause_ta", ""),
                        "likelihood": 0.4,
                        "source_refs": [log["ref"]],
                    }
                )
            if d.get("corrective_action_en"):
                plan.append(
                    {
                        "kind": "action",
                        "action_en": d["corrective_action_en"][:160],
                        "action_ta": (d.get("corrective_action_ta") or "")[:160],
                        "source_refs": [log["ref"]],
                        "confidence": 0.6,
                    }
                )
        confidence = 0.75 if cards else 0.55 if logs else 0.3
        if not plan:
            for en, ta, exp_en, exp_ta in GENERIC:
                plan.append(
                    {
                        "kind": "check",
                        "action_en": en,
                        "action_ta": ta,
                        "expected_result_en": exp_en,
                        "expected_result_ta": exp_ta,
                        "confidence": 0.3,
                    }
                )
        plan = plan[:8]
        total = len(plan) + 1
        steps = [_step(1, total, **LOTO, source_refs=[], confidence=1.0)]
        steps[0]["if_not_ok_next"] = -1
        for i, fields in enumerate(plan, start=2):
            steps.append(_step(i, total, **fields))
        seen, unique_causes = set(), []
        for c in causes:
            if c["cause_en"].lower() not in seen:
                seen.add(c["cause_en"].lower())
                unique_causes.append(c)
        history = "Based on this machine's history." if (cards or logs) else "No matching history found."
        return {
            "summary_en": f"Demo AI. {history}",
            "summary_ta": "Demo AI. " + (
                "இந்த machine-ன் history-ல இருந்து." if (cards or logs) else "இதுக்கு முன்னாடி history இல்லை."
            ),
            "likely_causes": unique_causes[:3],
            "steps": steps,
            "confidence": confidence,
            "refuse": False,
            "refuse_reason_en": "",
            "refuse_reason_ta": "",
        }

    def _explain(self, h: dict) -> dict:
        step = h.get("step", {})
        check = step.get("check_en") or step.get("action_en", "")
        check_ta = step.get("check_ta") or step.get("action_ta", "")
        return {
            "text_en": f"Demo AI. This step checks: {check} If the result is not as expected, "
            "the fault is likely here. Fix it before you move on.",
            "text_ta": f"Demo AI. இந்த step-ல பார்க்கிறது: {check_ta} Expected மாதிரி இல்லைன்னா fault "
            "இங்கதான் இருக்கலாம். அதை சரி பண்ணிட்டு அடுத்த step போங்க.",
        }

    # ---- logs ----------------------------------------------------------------------------------
    def _extract_log(self, h: dict) -> dict:
        transcript = (h.get("transcript") or "").strip()
        lang = detect_lang(transcript)
        clauses = [c.strip() for c in re.split(r"[,.;\n]+", transcript) if c.strip()]
        issue, cause, actions = "", "", []
        for clause in clauses:
            if ACTION_WORDS.search(clause):
                actions.append(clause)
            elif not issue:
                issue = clause
            elif CAUSE_WORDS.search(clause) and not cause:
                cause = clause
            elif not cause:
                cause = clause
        corrective = ", ".join(actions)
        parts = []
        for clause in actions:
            m = PART_AFTER.search(clause) or PART_BEFORE.search(clause)
            if m:
                parts.append({"description": m.group(1).strip(), "part_no": "", "qty": 1})
        downtime = re.search(r"(\d+)\s*(?:min|mins|minutes|nimisham)", transcript, re.I)
        times = re.findall(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", transcript)

        def field(text: str) -> dict:
            text_lang = detect_lang(text)
            return {
                "original": text,
                "en": text if text_lang == "en" else "",
                "ta": text if text_lang == "ta" else "",
                "unsure": False,
            }

        q_en = q_ta = ""
        if not issue:
            q_en, q_ta = "What was the problem?", "என்ன problem வந்தது?"
        elif not corrective:
            q_en, q_ta = "What did you do to fix it?", "சரி பண்ண என்ன பண்ணீங்க?"
        return {
            "language": "mixed" if lang == "mixed" else lang,
            "issue": field(issue),
            "root_cause": field(cause),
            "corrective_action": field(corrective),
            "parts_replaced": parts,
            "downtime_min": int(downtime.group(1)) if downtime else -1,
            "start_time": f"{int(times[0][0]):02d}:{times[0][1]}" if len(times) >= 1 else "",
            "end_time": f"{int(times[1][0]):02d}:{times[1][1]}" if len(times) >= 2 else "",
            "alarm_code": "",
            "missing_question_en": q_en,
            "missing_question_ta": q_ta,
        }

    def _session_to_log(self, h: dict) -> dict:
        done = [s for s in h.get("steps_done", []) if s.get("kind") == "action"]
        corrective_en = " ".join(s.get("action_en", "") for s in done)[:400]
        corrective_ta = " ".join(s.get("action_ta", "") for s in done)[:400]
        causes = h.get("likely_causes", [])
        cause = causes[0] if causes else {}
        problem = h.get("problem", "")
        return {
            "language": h.get("language", "en") if h.get("language") in ("en", "ta") else "en",
            "issue": {"original": problem, "en": problem if detect_lang(problem) == "en" else "", "ta": "", "unsure": False},
            "root_cause": {
                "original": "",
                "en": cause.get("cause_en", ""),
                "ta": cause.get("cause_ta", ""),
                "unsure": True,
            },
            "corrective_action": {
                "original": "",
                "en": corrective_en,
                "ta": corrective_ta,
                "unsure": not corrective_en,
            },
            "parts_replaced": [],
            "downtime_min": -1,
            "start_time": "",
            "end_time": "",
            "alarm_code": h.get("alarm_code", ""),
            "missing_question_en": "",
            "missing_question_ta": "",
        }

    def _enrich_log(self, h: dict) -> dict:
        fields = h.get("fields", {})
        out = []
        for name, original in fields.items():
            lang = detect_lang(original)
            out.append(
                {
                    "field": name,
                    "en": original if lang == "en" else "",
                    "ta": original if lang == "ta" else "",
                }
            )
        text = " ".join(fields.values()).lower()
        component = ""
        for comp in h.get("components", []):
            if comp["name"].lower() in text or any(
                w in text for w in comp["name"].lower().split() if len(w) > 4
            ):
                component = comp["name"]
                break
        failure = ""
        m = CAUSE_WORDS.search(fields.get("root_cause", "") or text)
        if m:
            failure = m.group(1).lower()
        issue = fields.get("issue", "")
        symptom = " ".join(re.split(r"[,.;]", issue)[0].split()[:6]).capitalize()
        return {
            "fields": out,
            "symptom_category": symptom,
            "component_name": component,
            "failure_mode": failure,
            "confidence": 0.4,
        }
