"""OpenAPI 2.0 file for the Copilot custom connector (SPEC 13.2).

Copilot Studio tools and Power Platform custom connectors take OpenAPI 2.0 (Swagger); FastAPI writes
OpenAPI 3.1. This converts the /api/copilot routes, and only the JSON Schema features they use. It
fails loudly on anything else, so a new route cannot quietly produce a file the connector rejects.

    python -m app.cli copilot-spec > ../copilot/thunai-tools.swagger.json
    python -m app.cli copilot-spec --host thunai.plant.example --tenant <tenant-id> --scope api://<client-id>/Thunai.Use

tests/test_copilot_spec.py fails when the committed file is out of date.
"""
import copy
import json

from fastapi import FastAPI

PREFIX = "/api/copilot"
HOST = "thunai.example.com"
TENANT = "{tenant-id}"
SCOPE = "api://{thunai-api-client-id}/Thunai.Use"
SECURITY = "entra_id"
# Kept from JSON Schema; everything else on a schema node is either converted below or an error.
KEEP = {
    "type", "format", "description", "title", "enum", "default", "items", "properties", "required",
    "additionalProperties", "maxLength", "minLength", "maximum", "minimum", "maxItems", "minItems", "pattern",
}
PARAM_KEEP = {"type", "format", "enum", "default", "maxLength", "minLength", "maximum", "minimum", "pattern"}


class SpecError(ValueError):
    pass


def _ref(ref: str) -> str:
    if not ref.startswith("#/components/schemas/"):
        raise SpecError(f"unexpected $ref {ref}")
    return "#/definitions/" + ref.rsplit("/", 1)[1]


def _schema(node: dict, where: str) -> dict:
    """One JSON Schema node, 3.1 → 2.0. Optional values (X or null) become X: Thunai leaves them out."""
    node = dict(node)
    if "$ref" in node:
        extra = set(node) - {"$ref", "description", "title", "default"}
        if extra:
            raise SpecError(f"{where}: $ref with {sorted(extra)}")
        return {"$ref": _ref(node["$ref"])}  # 2.0 ignores siblings of $ref
    if "anyOf" in node:
        options = [o for o in node.pop("anyOf") if o.get("type") != "null"]
        if len(options) != 1:
            raise SpecError(f"{where}: anyOf with {len(options)} non-null options")
        node.pop("default", None)  # the null default
        inner = _schema(options[0], where)
        if "$ref" in inner:
            return inner
        merged = {**inner, **{k: v for k, v in node.items() if k in ("description", "title")}}
        return merged
    if "const" in node:
        node["enum"] = [node.pop("const")]
    node.pop("examples", None)
    if node.get("default", 0) is None:
        node.pop("default")
    unknown = set(node) - KEEP
    if unknown:
        raise SpecError(f"{where}: unsupported {sorted(unknown)}")
    out = {}
    for key, value in node.items():
        if key == "items":
            out[key] = _schema(value, f"{where}[]")
        elif key == "properties":  # field titles are only Pydantic's "Machine No" noise
            out[key] = {name: _without_title(_schema(sub, f"{where}.{name}")) for name, sub in value.items()}
        elif key == "additionalProperties" and isinstance(value, dict):
            out[key] = _schema(value, f"{where}{{}}")
        else:
            out[key] = value
    return out


def _without_title(node: dict) -> dict:
    node.pop("title", None)
    return node


def _parameter(p: dict, where: str) -> dict:
    schema = _schema(p.get("schema", {}), f"{where}.{p['name']}")
    if "$ref" in schema or schema.get("type") in ("object", "array"):
        raise SpecError(f"{where}: parameter {p['name']} must be a plain value")
    out = {"name": p["name"], "in": p["in"], "required": bool(p.get("required") or p["in"] == "path")}
    description = p.get("description") or schema.get("description", "")
    if description:
        out["description"] = description
    out.update({k: v for k, v in schema.items() if k in PARAM_KEEP})
    return out


def _operation(op: dict, where: str) -> dict:
    if not op.get("operationId") or not op.get("summary") or not op.get("description"):
        raise SpecError(f"{where}: needs operation_id, summary and a docstring")
    out = {
        "operationId": op["operationId"],
        "summary": op["summary"],
        "description": " ".join(op["description"].split()),
        "parameters": [_parameter(p, where) for p in op.get("parameters", [])],
    }
    body = op.get("requestBody", {}).get("content", {}).get("application/json")
    if body:
        out["parameters"].append({"name": "body", "in": "body", "required": True, "schema": _schema(body["schema"], f"{where} body")})
    ok = op["responses"].get("200", {}).get("content", {}).get("application/json")
    if not ok:
        raise SpecError(f"{where}: needs a JSON 200 response (set response_model)")
    out["responses"] = {
        "200": {"description": "OK", "schema": _schema(ok["schema"], f"{where} response")},
        "default": {"description": "Error: show 'detail' to the technician in plain words."},
    }
    if not out["parameters"]:
        del out["parameters"]
    return out


def _used(paths: dict, schemas: dict) -> list[str]:
    """Names of the schemas the converted operations reach, directly or through other schemas.
    (Error responses are not converted, so FastAPI's validation-error schemas are left out.)"""
    seen: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if ref:
                name = ref.rsplit("/", 1)[1]
                if name not in seen:
                    seen.append(name)
                    walk(schemas[name])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(paths)
    return sorted(seen)


def build(app: FastAPI, *, host: str = HOST, tenant: str = TENANT, scope: str = SCOPE) -> dict:
    source = copy.deepcopy(app.openapi())
    schemas = source.get("components", {}).get("schemas", {})
    paths: dict = {}
    for path, ops in source["paths"].items():
        if not path.startswith(PREFIX + "/"):
            continue
        for method, op in ops.items():
            paths.setdefault(path[len(PREFIX):], {})[method] = op
    converted = {
        path: {method: _operation(op, f"{method.upper()} {path}") for method, op in ops.items()} for path, ops in paths.items()
    }
    definitions = {name: _schema(schemas[name], name) for name in _used(converted, schemas)}
    login = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"
    return {
        "swagger": "2.0",
        "info": {
            "title": "Thunai",
            "description": "Breakdown help and logging for EPQPL maintenance technicians. Tools for the Thunai agent in "
            "Microsoft Copilot Studio. Steps come from the plant's own fault cards, logs and alarm lists, with safety rules "
            "enforced by Thunai.",
            "version": app.version,
        },
        "host": host,
        "basePath": PREFIX,
        "schemes": ["https"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "paths": converted,
        "definitions": definitions,
        "securityDefinitions": {
            SECURITY: {
                "type": "oauth2",
                "flow": "accessCode",
                "authorizationUrl": f"{login}/authorize",
                "tokenUrl": f"{login}/token",
                "scopes": {scope: "Use Thunai as the signed-in technician"},
            }
        },
        "security": [{SECURITY: [scope]}],
    }


def dumps(spec: dict) -> str:
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
