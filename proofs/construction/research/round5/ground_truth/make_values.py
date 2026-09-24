#!/usr/bin/env python3
"""Collect computed values and write values.json plus the tables of VALUES.md.

Sources (all discovery output unless a certificate is listed):
  runs/colval_w1to5.txt, runs/colval_small_extra.txt  exact enumeration (colval)
  runs/values.jsonl                                    bisection by outcome search (colout)
  certificates/manifest.json                           replayed certificates
Prints the markdown tables to stdout; VALUES.md embeds them.
"""
from fractions import Fraction as F
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
FAMS = ["DD", "DU", "DV", "DR", "DX", "DJ", "RX", "VX", "XX", "XU", "XJ", "D", "U", "V", "X", "R", "J", "DT", "M"]


def parse_val(s):
    s = s.strip()
    star = s.endswith("*")
    if s == "*":
        return F(0), True
    if star:
        s = s[: -2] if s.endswith("+*") else s[:-1]
    return F(s), star


def fmt(v):
    x, star = v
    if x == 0 and star:
        return "*"
    return f"{x}{'+*' if star else ''}"


def collect():
    vals = {}  # (fam, n) -> dict(value=(x,star), sources=set)

    def add(fam, n, v, src):
        key = (fam, n)
        if key in vals and vals[key]["value"] != v:
            raise SystemExit(f"CONFLICT {fam}_{n}: {vals[key]['value']} vs {v} ({src})")
        vals.setdefault(key, dict(value=v, sources=set()))["sources"].add(src)

    for name in ("colval_w1to5.txt", "colval_small_extra.txt", "colval_w6.txt"):
        p = HERE / "runs" / name
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z]+)_(\d+)\t(\S+)\t", line)
            if m and not (m.group(1) == "M" and m.group(2) == "1"):
                add(m.group(1), int(m.group(2)), parse_val(m.group(3)), "colval")
    p = HERE / "runs" / "values.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == "Completed" and not r["value"].startswith("CONFUSED"):
                add(r["family"], r["width"], parse_val(r["value"]), "colout")
    p = HERE / "runs" / "rust_values.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == "Completed":
                add(r["family"], r["width"], parse_val(r["value"]), "rust")
    certs = {}
    p = HERE / "certificates" / "manifest.json"
    if p.exists():
        for c in json.loads(p.read_text())["certificates"]:
            certs.setdefault((c["family"], c["width"]), []).append(c)
    return vals, certs


def status(vals, certs, fam, n):
    """CERTIFIED-FINITE if both directions of the exact value are replayed."""
    v = vals[(fam, n)]["value"]
    cs = certs.get((fam, n), [])
    need = {("blue", str(v[0]), int(v[1])), ("white", str(v[0]), int(v[1]))}
    have = {(c["player"], c["q"], int(c["star"])) for c in cs if c.get("verified")}
    return "C" if need <= have else "E"


def table(vals, certs, fams, widths):
    head = "| family | " + " | ".join(str(n) for n in widths) + " |"
    sep = "| --- |" + " --- |" * len(widths)
    rows = [head, sep]
    for f in fams:
        cells = []
        for n in widths:
            if (f, n) in vals:
                st = status(vals, certs, f, n)
                cells.append(fmt(vals[(f, n)]["value"]) + ("ᶜ" if st == "C" else ""))
            else:
                cells.append("")
        rows.append(f"| {f} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


TARGETS = [
    # name, family, parity (1 odd / 0 even), test(x,star)->bool, margin(x)->F, min width
    ("DU_k < 0 (odd k)", "DU", 1, lambda x, s: x < 0, lambda x: -x, 1),
    ("DV_k <= 1/2 (even k)", "DV", 0, lambda x, s: x < F(1, 2) or (x == F(1, 2) and not s), lambda x: F(1, 2) - x, 2),
    ("DR_k <= -1/4 (even k)", "DR", 0, lambda x, s: x < F(-1, 4) or (x == F(-1, 4) and not s), lambda x: F(-1, 4) - x, 2),
    ("DR_k < 0 (even k)", "DR", 0, lambda x, s: x < 0, lambda x: -x, 2),
    ("DX_k <= 0, DX_k+* <= 0, DX_k < 0 (even k)", "DX", 0, lambda x, s: x < 0, lambda x: -x, 2),
    ("DJ_k < -1/4 (odd k)", "DJ", 1, lambda x, s: x < F(-1, 4), lambda x: F(-1, 4) - x, 1),
    ("DD_n < 0 (odd n >= 3)", "DD", 1, lambda x, s: x < 0, lambda x: -x, 3),
    ("T_1(RX_k) (odd k >= 3)", "RX", 1, lambda x, s: x < 1, lambda x: 1 - x, 3),
    ("T_2(VX_k) (odd k >= 3)", "VX", 1, lambda x, s: x < 2, lambda x: 2 - x, 3),
    ("T_1(XX_k) (odd k >= 3)", "XX", 1, lambda x, s: x < 1, lambda x: 1 - x, 3),
    ("M_n <= 0 (odd n >= 3)", "M", 1, lambda x, s: x < 0 or (x == 0 and not s), lambda x: -x, 3),
]


def margins(vals, certs):
    out = ["| target | width: value, margin, holds? |", "| --- | --- |"]
    fails = []
    for name, fam, par, test, margin, wmin in TARGETS:
        cells = []
        for n in range(wmin, 13):
            if n % 2 != par or (fam, n) not in vals:
                continue
            x, s = vals[(fam, n)]["value"]
            ok = test(x, s)
            st = status(vals, certs, fam, n)
            cells.append(f"{n}: {fmt((x, s))}, {margin(x)}, {'yes' if ok else '**NO**'}{'ᶜ' if st == 'C' else ''}")
            if not ok:
                fails.append(f"{name} fails at width {n}: value {fmt((x, s))}")
        out.append(f"| {name} | " + "; ".join(cells) + " |")
    return "\n".join(out), fails


if __name__ == "__main__":
    vals, certs = collect()
    data = {f"{f}_{n}": dict(family=f, width=n, value=fmt(v["value"]), sources=sorted(v["sources"]),
                             status="CERTIFIED-FINITE" if status(vals, certs, f, n) == "C" else "EVIDENCE")
            for (f, n), v in sorted(vals.items(), key=lambda kv: (FAMS.index(kv[0][0]), kv[0][1]))}
    (HERE / "values.json").write_text(json.dumps(data, indent=1) + "\n")
    widths = sorted({n for _, n in vals})
    print(table(vals, certs, FAMS, widths))
    print()
    m, fails = margins(vals, certs)
    print(m)
    print()
    print("FAILURES:" if fails else "No target failure among computed widths.")
    for f in fails:
        print(" -", f)
