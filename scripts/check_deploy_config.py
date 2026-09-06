#!/usr/bin/env python3
"""Validate the deployment configs without needing a Docker daemon or a host.

Catches the failures that only show up when someone clicks Deploy:
  * render.yaml somewhere other than the repo root, where Render never looks
  * a service pinned to a branch that does not carry the code
  * dockerfilePath / dockerContext pointing at nothing
  * a Dockerfile COPY whose source is outside the declared build context
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALID_REGIONS = {"oregon", "ohio", "virginia", "frankfurt", "singapore"}
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def check_render() -> None:
    cfg = ROOT / "render.yaml"
    if not cfg.exists():
        err("render.yaml is not at the repository root; Render only looks there")
        return
    spec = yaml.safe_load(cfg.read_text())
    for svc in spec.get("services", []):
        name = svc.get("name", "<unnamed>")
        if svc.get("region") and svc["region"] not in VALID_REGIONS:
            err(f"{name}: region {svc['region']!r} is not a Render region")

        branch = svc.get("branch")
        if not branch:
            err(f"{name}: no branch set, so Render will use main")
        else:
            listed = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", branch],
                cwd=ROOT, capture_output=True, text=True)
            if listed.returncode != 0:
                err(f"{name}: branch {branch!r} does not exist locally")
            else:
                ctx = svc.get("dockerContext", ".").lstrip("./")
                if ctx and ctx not in listed.stdout:
                    err(f"{name}: branch {branch!r} does not contain {ctx}/")

        for key in ("dockerfilePath", "dockerContext"):
            if key in svc:
                p = ROOT / svc[key].lstrip("./")
                if not p.exists():
                    err(f"{name}: {key} {svc[key]!r} does not exist")

        if svc.get("runtime") == "docker":
            check_dockerfile(name, svc)


def check_dockerfile(name: str, svc: dict) -> None:
    """Every COPY source must resolve inside the declared build context."""
    df = ROOT / svc.get("dockerfilePath", "./Dockerfile").lstrip("./")
    ctx = ROOT / svc.get("dockerContext", ".").lstrip("./")
    if not df.exists():
        return
    for line in df.read_text().splitlines():
        m = re.match(r"\s*COPY\s+(?!--from)(.+)", line, re.I)
        if not m:
            continue
        parts = m.group(1).split()
        if len(parts) < 2:
            continue
        for src in parts[:-1]:
            if src.startswith("--"):
                continue
            target = ctx / src.rstrip("/")
            if not target.exists():
                err(f"{name}: Dockerfile COPY {src!r} resolves to {target.relative_to(ROOT)}, "
                    f"which does not exist in the build context")


def check_fly() -> None:
    fly = ROOT / "us-portfolio" / "fly.toml"
    if not fly.exists():
        return
    import tomllib
    cfg = tomllib.loads(fly.read_text())
    df = fly.parent / cfg.get("build", {}).get("dockerfile", "Dockerfile")
    if not df.exists():
        err(f"fly.toml: dockerfile {df.relative_to(ROOT)} does not exist")
    port = cfg.get("http_service", {}).get("internal_port")
    if port != 8000:
        err(f"fly.toml: internal_port {port} does not match the Dockerfile's EXPOSE 8000")


check_render()
check_fly()

if errors:
    print("Deployment config problems:\n")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
print("Deployment configs are consistent: render.yaml at root, branch carries the "
      "code, Docker paths resolve inside the build context.")
