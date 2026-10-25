"""The connector's OpenAPI 2.0 file (copilot/thunai-tools.swagger.json) matches the code and is valid."""
import json
from pathlib import Path

import pytest
from openapi_spec_validator import validate
from openapi_spec_validator.validation import OpenAPIV2SpecValidator

from app import copilot_spec
from app.main import app

FILE = Path(__file__).resolve().parents[2] / "copilot" / "thunai-tools.swagger.json"
INSTRUCTIONS = FILE.parent / "agent-instructions.md"


def test_committed_file_is_up_to_date():
    assert FILE.read_text() == copilot_spec.dumps(copilot_spec.build(app)), (
        "Regenerate: cd backend && python -m app.cli copilot-spec > ../copilot/thunai-tools.swagger.json"
    )


def test_file_is_valid_openapi_2_for_the_connector():
    spec = json.loads(FILE.read_text())
    validate(spec, cls=OpenAPIV2SpecValidator)
    ops = [op for ops in spec["paths"].values() for op in ops.values()]
    assert len(ops) == 15 <= 25  # Microsoft suggests at most 25 to 30 tools per agent
    assert len({op["operationId"] for op in ops}) == len(ops)
    for op in ops:
        assert 0 < len(op["summary"]) <= 80 and 40 < len(op["description"]) <= 1000, op["operationId"]
    text = FILE.read_text()
    for leftover in ('"anyOf"', '"oneOf"', '"allOf"', '"const"', '"null"', "components/schemas", "HTTPValidationError"):
        assert leftover not in text
    assert spec["securityDefinitions"]["entra_id"]["flow"] == "accessCode"  # the user's own sign-in, not app-only
    assert spec["basePath"] == "/api/copilot" and spec["schemes"] == ["https"]
    assert len(text.encode()) < 1_000_000  # Power Platform's limit for an imported definition


def test_tenant_values_are_filled_in():
    spec = copilot_spec.build(app, host="thunai.plant.test", tenant="t-1", scope="api://abc/Thunai.Use")
    sec = spec["securityDefinitions"]["entra_id"]
    assert spec["host"] == "thunai.plant.test" and sec["tokenUrl"] == "https://login.microsoftonline.com/t-1/oauth2/v2.0/token"
    assert spec["security"] == [{"entra_id": ["api://abc/Thunai.Use"]}]


def test_unsupported_schema_features_fail_loudly():
    with pytest.raises(copilot_spec.SpecError):
        copilot_spec._schema({"oneOf": [{"type": "string"}, {"type": "integer"}]}, "x")
    with pytest.raises(copilot_spec.SpecError):
        copilot_spec._schema({"anyOf": [{"type": "string"}, {"type": "integer"}]}, "x")
    assert copilot_spec._schema({"anyOf": [{"type": "number"}, {"type": "null"}], "default": None, "description": "d"}, "x") == {
        "type": "number", "description": "d"}


def test_agent_instructions_fit_copilot_studio():
    text = INSTRUCTIONS.read_text()
    assert len(text) <= 8000  # Copilot Studio's instruction limit
    ops = {op["operationId"] for ops in json.loads(FILE.read_text())["paths"].values() for op in ops.values()}
    named = {op for op in ops if op in text}
    assert {"startTroubleshooting", "reportStep", "closeSession", "checkSafety", "callSupervisor", "createLog"} <= named
