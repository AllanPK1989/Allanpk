from app.ai.rules_provider import RulesProvider
from app.ai.schemas import ExtractOut, FieldValue, strict_schema
from app.logs_service import _check_originals
from app.textutil import detect_lang, overlap_ratio, rank, tokens

BRIEF_EXAMPLE = "Cylinder return aagala, solenoid coil burnt, coil maathiten, 10 cycle check OK."


def test_mock_extracts_the_brief_example_into_fields():
    out = RulesProvider()._extract_log({"transcript": BRIEF_EXAMPLE})
    parsed = ExtractOut.model_validate(out)
    assert parsed.issue.original == "Cylinder return aagala"
    assert parsed.root_cause.original == "solenoid coil burnt"
    assert parsed.corrective_action.original == "coil maathiten, 10 cycle check OK"
    assert parsed.parts_replaced[0].description.lower() == "coil"
    assert parsed.missing_question_en == ""


def test_missing_corrective_action_asks_one_question():
    out = ExtractOut.model_validate(RulesProvider()._extract_log({"transcript": "Hopper jam, vibrator not running"}))
    assert out.corrective_action.original == ""
    assert out.missing_question_en and out.missing_question_ta


def _extraction(issue_original: str) -> ExtractOut:
    empty = FieldValue(original="", en="", ta="", unsure=False)
    return ExtractOut(
        language="mixed",
        issue=FieldValue(original=issue_original, en="Cylinder not returning", ta="", unsure=False),
        root_cause=empty,
        corrective_action=empty,
        parts_replaced=[],
        downtime_min=-1,
        start_time="",
        end_time="",
        alarm_code="",
        missing_question_en="",
        missing_question_ta="",
    )


def test_technicians_words_pass_the_original_check():
    out = _check_originals(BRIEF_EXAMPLE)(_extraction("Cylinder return aagala"))
    assert out.issue.original == "Cylinder return aagala"
    assert out.issue.unsure is False


def test_invented_original_is_removed_and_flagged():
    out = _check_originals(BRIEF_EXAMPLE)(_extraction("Pneumatic actuator retraction failure due to valve fault"))
    assert out.issue.original == ""  # never stored as the technician's words
    assert out.issue.unsure is True
    assert out.issue.en == "Cylinder not returning"


def test_language_detection():
    assert detect_lang("Cylinder return aagala") == "en"  # romanised Tamil is handled by the AI
    assert detect_lang("சிலிண்டர் திரும்பவில்லை") == "ta"
    assert detect_lang("Cylinder return ஆகல") == "mixed"


def test_glossary_variants_and_stemming_help_matching():
    variants = {"aagala": "not working", "proxy": "proximity sensor"}
    assert "work" in tokens("Cylinder return aagala", variants)
    scores = rank("proxy sensor loose", ["Proximity sensor misaligned", "Label print faded"], variants)
    assert scores[0] > scores[1]
    assert overlap_ratio("coil maathiten", BRIEF_EXAMPLE) == 1.0


def test_schema_sent_to_the_model_is_strict():
    schema = strict_schema(ExtractOut)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["issue"]["additionalProperties"] is False
    assert "$defs" not in schema and "$ref" not in str(schema)
