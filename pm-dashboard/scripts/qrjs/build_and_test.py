#!/usr/bin/env python3
"""
build_and_test.py - injects the QR lookup tables into qr.js and verifies the
result against the python-qrcode reference implementation.

The browser QR generator has to be trusted without anyone being able to run
Python at the site that uses it, so it is checked here instead: for a few
hundred payloads, every one of the 8 mask patterns is compared module by
module, and the automatic mask choice is compared too.

Run:  python3 scripts/qrjs/build_and_test.py [--fuzz N]
Exit code 1 on any mismatch.
"""
import argparse, json, os, random, string, subprocess, sys

import qrcode
import qrcode.base as qb
import qrcode.util as qu
import qrcode.constants as qc
from qrcode.util import QRData, MODE_8BIT_BYTE

HERE = os.path.dirname(os.path.abspath(__file__))
MAXV = 40


def build() -> str:
    off = qb.RS_BLOCK_OFFSET[qc.ERROR_CORRECT_H]
    rs = [list(qb.RS_BLOCK_TABLE[(v - 1) * 4 + off]) for v in range(1, MAXV + 1)]
    align = [list(qu.PATTERN_POSITION_TABLE[v - 1]) for v in range(1, MAXV + 1)]
    src = open(os.path.join(HERE, "qr.js"), encoding="utf-8").read()
    src = src.replace("__RS_BLOCKS_H__", json.dumps(rs))
    src = src.replace("__ALIGN__", json.dumps(align))
    out = os.path.join(HERE, "qr.built.js")
    open(out, "w", encoding="utf-8").write(src)
    return out


def payloads(fuzz: int) -> list[str]:
    here = os.path.dirname(os.path.dirname(HERE))
    import csv
    p = []
    ENV = "3f2a8c11-4d5e-4a7b-9c0d-1e2f3a4b5c6d"
    APP = "b7e91d20-6f3a-48c9-8d1e-2a5b7c9d0e3f"
    TEN = "9c8b7a6d-5e4f-3210-9876-543210fedcba"
    base = f"https://apps.powerapps.com/play/e/{ENV}/a/{APP}?tenantId={TEN}&source=qr"
    for r in csv.DictReader(open(os.path.join(here, "data", "dummy", "Machine_Master.csv"))):
        p.append(f"{base}&type=machine&id={r['MachineID']}")
    for r in csv.DictReader(open(os.path.join(here, "data", "dummy", "Technician_Master.csv"))):
        p.append(f"{base}&type=tech&id={r['TechID']}")
    p += ["A", "MC-001", "x" * 10, "x" * 40, "x" * 100, "x" * 200, "x" * 400,
          "Cell-01 / CNC unicode üï ✓ test", "https://t.co/a?b=1&c=2#frag"]
    rnd = random.Random(20260828)
    alphabet = string.printable[:94]
    for _ in range(fuzz):
        n = rnd.choice([1, 2, 3, 7, 13, 17, 26, 33, 47, 65, 90, 129, 175, 257,
                        330, 420, 520, 640, 760, 900, 1050, 1180, 1268])
        p.append("".join(rnd.choice(alphabet) for _ in range(n)))
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuzz", type=int, default=250)
    args = ap.parse_args()

    built = build()
    print(f"  built {os.path.relpath(built)} ({MAXV} versions of tables injected)")

    pays = payloads(args.fuzz)
    tmp = os.path.join(HERE, ".payloads.json")
    json.dump(pays, open(tmp, "w"))
    raw = subprocess.run(["node", os.path.join(HERE, "dump_js.js"), tmp],
                         capture_output=True, text=True, check=True).stdout
    js = json.loads(raw)
    os.remove(tmp)

    total = mism = vermis = automis = 0
    vers: dict[int, int] = {}
    bad = []
    for p in pays:
        for m in range(8):
            q = qrcode.QRCode(error_correction=qc.ERROR_CORRECT_H, border=0)
            q.add_data(QRData(p.encode("utf-8"), mode=MODE_8BIT_BYTE))
            q.best_fit()
            q.makeImpl(False, m)
            ref = "|".join("".join("1" if c else "0" for c in r) for r in q.modules)
            total += 1
            vers[q.version] = vers.get(q.version, 0) + 1
            if js[p]["version"] != q.version:
                vermis += 1
                if len(bad) < 5:
                    bad.append((p[:30], m, f"v{js[p]['version']} vs v{q.version}"))
            elif js[p][str(m)] != ref:
                mism += 1
                if len(bad) < 5:
                    bad.append((p[:30], m, "matrix differs"))
        q = qrcode.QRCode(error_correction=qc.ERROR_CORRECT_H, border=0)
        q.add_data(QRData(p.encode("utf-8"), mode=MODE_8BIT_BYTE))
        q.make(fit=True)
        if q.best_mask_pattern() != js[p]["auto"]:
            automis += 1

    print(f"  payloads             {len(pays)}")
    print(f"  versions exercised   {sorted(vers)}")
    print(f"  matrices compared    {total}   (all 8 mask patterns each)")
    print(f"  version mismatches   {vermis}")
    print(f"  matrix mismatches    {mism}")
    print(f"  auto-mask mismatches {automis}")
    for b in bad:
        print("     ", b)
    ok = (mism == 0 and vermis == 0 and automis == 0)
    print("\n  " + ("PASS - identical to the python-qrcode reference, module for module"
                    if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
