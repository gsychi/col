#!/usr/bin/env python3
"""Negative controls: the verifier must reject corrupted packages.

Each control copies the decoded manifest and certificate, applies one kind of
corruption, and runs verify.verify_documents (the checksum test runs on a
temporary copy of the package directory).  The unmodified package must pass.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import copy
import gzip
import json
import shutil
import sys
import tempfile
from pathlib import Path

import verify

HERE = Path(__file__).resolve().parent


def load():
    manifest = json.loads((HERE / "manifest.json").read_text())
    doc = verify.load_records(HERE / manifest["certificate"]["path"])
    return manifest, doc


def first(doc, kind, pred=lambda i, rec: True):
    for i, rec in enumerate(doc["nodes"]):
        if rec[7] == kind and pred(i, rec):
            return i
    raise SystemExit(f"no node of kind {kind} for this control")


def c_illegal_reply(m, d):
    """An expansion answers a Blue move with a White move on an occupied cell."""
    i = first(d, "E", lambda i, r: i > 0 and len(r[8]) > 0 and r[8][0][0] >= 0)
    e = d["nodes"][i][8][0]
    e[1] = e[0]  # the cell Blue just took


def c_missing_blue_move(m, d):
    """An expansion omits one Blue option."""
    i = first(d, "E", lambda i, r: i > 0 and len(r[8]) > 1)
    d["nodes"][i][8].pop()


def c_wrong_child(m, d):
    """An expansion edge points at a node that is not the resulting position."""
    i = first(d, "E", lambda i, r: i > 0 and len(r[8]) > 1)
    edges = d["nodes"][i][8]
    for e in edges:
        if e[2] != edges[0][2]:
            e[2], edges[0][2] = edges[0][2], e[2]
            return
    edges[0][2] = 0


def c_bad_transform(m, d):
    """A child transform is altered (sym flipped)."""
    i = first(d, "E", lambda i, r: i > 0 and len(r[8]) > 0)
    e = d["nodes"][i][8][0]
    e[3] ^= 6


def c_uncovered_blue(m, d):
    """A comparison drops a child containing a Blue-legal cell."""
    def pred(i, r):
        return len(r[9]) >= 2 and any(d["nodes"][ch[0]][2] for ch in r[9])
    i = first(d, "C", pred)
    kids = d["nodes"][i][9]
    for k, ch in enumerate(kids):
        if d["nodes"][ch[0]][2]:
            kids.pop(k)
            return


def c_overlap(m, d):
    """A comparison lists the same child twice (overlapping regions)."""
    i = first(d, "C", lambda i, r: len(r[9]) >= 1)
    d["nodes"][i][9].append(list(d["nodes"][i][9][0]))


def c_seam(m, d):
    """A comparison forgets its White retirements (seam edge with two White cells)."""
    i = first(d, "C", lambda i, r: r[8] != 0)
    d["nodes"][i][8] = 0


def c_retire_non_white(m, d):
    """A comparison retires a cell that is not White-legal."""
    def pred(i, r):
        h, w, a, b = r[:4]
        return (1 << (h * w)) - 1 & ~b != 0
    i = first(d, "C", pred)
    h, w, a, b = d["nodes"][i][:4]
    free = ((1 << (h * w)) - 1) & ~b
    d["nodes"][i][8] |= free & -free


def c_sum_sign(m, d):
    """A comparison's bound is made too weak (parent claims more than the sum gives)."""
    i = first(d, "C", lambda i, r: len(r[9]) >= 1)
    rec = d["nodes"][i]
    # replace its first child by an otherwise identical claim with a larger number:
    # add a fresh arithmetic-looking node is impossible, so shift the parent instead
    from fractions import Fraction
    q = Fraction(rec[4], rec[5]) + 4
    rec[4], rec[5] = q.numerator, q.denominator


def c_arith(m, d):
    """An arithmetic leaf claims a positive number is <= 0."""
    i = first(d, "A")
    d["nodes"][i][4], d["nodes"][i][5] = 1, 1


def c_cycle(m, d):
    """A comparison node is justified by itself (acyclicity check)."""
    i = first(d, "C", lambda i, r: i > 0)
    d["nodes"][i][8] = 0
    d["nodes"][i][9] = [[i, 0, 0, 0]]


def c_opening_table(m, d):
    """The manifest's White reply for a representative is changed."""
    op = m["openings"][0]
    op["white"] = [op["white"][0], (op["white"][1] + 1) % 9]


def c_missing_representative(m, d):
    """One representative opening is removed."""
    m["openings"].pop()


def c_root_claim(m, d):
    """The root is not the empty board with bound 0."""
    d["nodes"][0][4], d["nodes"][0][5] = 1, 1


def c_star_flag(m, d):
    """A star bit is flipped on a comparison child claim."""
    i = first(d, "C", lambda i, r: len(r[9]) >= 1)
    ch = d["nodes"][i][9][0][0]
    d["nodes"][ch][6] ^= 1


CONTROLS = [
    c_illegal_reply, c_missing_blue_move, c_wrong_child, c_bad_transform,
    c_uncovered_blue, c_overlap, c_seam, c_retire_non_white, c_sum_sign,
    c_arith, c_cycle, c_opening_table, c_missing_representative, c_root_claim,
    c_star_flag,
]


def checksum_control() -> str | None:
    """Corrupt one byte of a checksummed file in a temporary copy."""
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / "pkg"
        shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns("__pycache__", "generate"))
        p = dst / "PROOF.md"
        data = bytearray(p.read_bytes())
        data[len(data) // 2] ^= 1
        p.write_bytes(bytes(data))
        try:
            verify.check_sha256sums(dst)
        except verify.InvalidCertificate as exc:
            return str(exc)
    return None


def main() -> int:
    manifest, doc = load()
    base = verify.verify_documents(copy.deepcopy(manifest), copy.deepcopy(doc))
    print(f"positive control: {base['result']} ({base['nodes']} nodes)")
    failures = 0
    for ctl in CONTROLS:
        m, d = copy.deepcopy(manifest), copy.deepcopy(doc)
        ctl(m, d)
        try:
            verify.verify_documents(m, d)
            print(f"NOT REJECTED  {ctl.__name__}: {ctl.__doc__.strip()}")
            failures += 1
        except (verify.InvalidCertificate, KeyError, IndexError, TypeError, ValueError) as exc:
            print(f"rejected      {ctl.__name__}: {ctl.__doc__.strip()}\n                -> {exc}")
    msg = checksum_control()
    if msg is None:
        print("NOT REJECTED  checksum: a flipped byte in PROOF.md")
        failures += 1
    else:
        print(f"rejected      checksum: a flipped byte in PROOF.md\n                -> {msg}")
    total = len(CONTROLS) + 1
    print(f"{total - failures}/{total} corruptions rejected")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
