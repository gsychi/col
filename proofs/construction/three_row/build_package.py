#!/usr/bin/env python3
"""Rebuild the derived reflections, certificates/SHA256SUMS and manifest.json.

This is packaging, not verification: verify.py re-derives every reflection,
re-hashes every file and replays every certificate without trusting anything
written here. Deterministic (gzip mtime 0, sorted output).

    python3 proofs/construction/three_row/build_package.py
"""
import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CERTS = HERE / "certificates"

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("three_row_verify", HERE / "verify.py")
verify = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = verify
_spec.loader.exec_module(verify)

ORIGINAL = "proofs/construction/original_proof/certificates/"
RESEARCH = "proofs/construction/research/new_certificates/"

# (id, kind, file under certificates/, repository source it was copied from)
SOURCES = [
    ("tile_e4d37d528005", "ordinary", "ordinary/tile_e4d37d528005.json.gz", ORIGINAL + "tile_e4d37d528005.json.gz"),
    ("tile_675ea04f7dff", "ordinary", "ordinary/tile_675ea04f7dff.json.gz", ORIGINAL + "tile_675ea04f7dff.json.gz"),
    ("tile_e06eb7fc2dd6", "ordinary", "ordinary/tile_e06eb7fc2dd6.json.gz", ORIGINAL + "tile_e06eb7fc2dd6.json.gz"),
    ("tile_8532d5d099db", "ordinary", "ordinary/tile_8532d5d099db.json.gz", ORIGINAL + "tile_8532d5d099db.json.gz"),
    ("tile_09197aa9813a", "ordinary", "ordinary/tile_09197aa9813a.json.gz", ORIGINAL + "tile_09197aa9813a.json.gz"),
    ("tmiddle1", "ordinary", "ordinary/tmiddle1.json.gz", "proofs/construction/three_row/incoming/tmiddle1.json.gz"),
    ("atlas_3x5_W21845", "ordinary", "ordinary/atlas_3x5_W21845.json.gz", "proofs/atlas/certificates/3x5/W21845.json.gz"),
    ("z7", "ordinary", "ordinary/z7.json.gz", "proofs/construction/three_row/incoming/z7.json.gz"),
    ("tile_76ba798e4bc4", "ordinary", "ordinary/tile_76ba798e4bc4.json.gz",
     ORIGINAL + "tile_76ba798e4bc4.json.gz (identical JSON to three_row/incoming/z7old.json.gz)"),
    ("tile_4d9d5d12cc0f", "ordinary", "ordinary/tile_4d9d5d12cc0f.json.gz", ORIGINAL + "tile_4d9d5d12cc0f.json.gz"),
    ("tile_da4864d83b99", "ordinary", "ordinary/tile_da4864d83b99.json.gz", ORIGINAL + "tile_da4864d83b99.json.gz"),
    ("tile_501c8151efe6", "ordinary", "ordinary/tile_501c8151efe6.json.gz", ORIGINAL + "tile_501c8151efe6.json.gz"),
    ("tile_2398ea84ec04", "ordinary", "ordinary/tile_2398ea84ec04.json.gz", ORIGINAL + "tile_2398ea84ec04.json.gz"),
    ("tile_468c39840ab4", "ordinary", "ordinary/tile_468c39840ab4.json.gz", ORIGINAL + "tile_468c39840ab4.json.gz"),
    ("tile_7de2134cc103", "ordinary", "ordinary/tile_7de2134cc103.json.gz", ORIGINAL + "tile_7de2134cc103.json.gz"),
    ("tile_09fb65f2292a", "ordinary", "ordinary/tile_09fb65f2292a.json.gz", ORIGINAL + "tile_09fb65f2292a.json.gz"),
    ("tile_8b16696647a7", "ordinary", "ordinary/tile_8b16696647a7.json.gz", ORIGINAL + "tile_8b16696647a7.json.gz"),
    ("tile_55c55441362e", "ordinary", "ordinary/tile_55c55441362e.json.gz", ORIGINAL + "tile_55c55441362e.json.gz"),
] + [
    (stem, "numeric", f"numerical/{stem}.json.gz", RESEARCH + f"{stem}.json.gz")
    for base in ("cap_minus_quarter", "opened_bulk_plus_one", "opened_bulk_c3_plus_one",
                 "opened_bulk_middle0_plus_one", "opened_bulk_middle2_plus_one")
    for stem in (f"{base}_blue", f"{base}_white")
]

# (id, source id, reflection): stored under certificates/derived/, re-derived by verify.py
DERIVED = [
    ("K_outer4_H_of_tile_09197aa9813a", "tile_09197aa9813a", "H"),
    ("opened_bulk_2_1_plus_one_blue_V_of_opened_bulk_plus_one_blue", "opened_bulk_plus_one_blue", "V"),
    ("opened_bulk_2_3_plus_one_blue_V_of_opened_bulk_c3_plus_one_blue", "opened_bulk_c3_plus_one_blue", "V"),
    ("tile_501c8151efe6_H", "tile_501c8151efe6", "H"),
    ("tile_09fb65f2292a_H", "tile_09fb65f2292a", "H"),
]

# Theorem roles: (role, certificate id, extra fields, where the theorem uses it)
ROLES = [
    ("E4", "tile_e4d37d528005", {}, ["4k+1", "case 1", "case 3", "case 4", "case 5"]),
    ("E4bar", "tile_675ea04f7dff", {}, ["case 2", "case 3", "case 4", "case 6"]),
    ("F1", "tile_e06eb7fc2dd6", {}, ["4k+1"]),
    ("K_corner", "tile_8532d5d099db", {"local_moves": {"blue": [0, 0], "white": [2, 2]}}, ["case 2"]),
    ("K_outer2", "tile_09197aa9813a", {"local_moves": {"blue": [0, 2], "white": [2, 0]}}, ["case 3"]),
    ("K_outer4", "K_outer4_H_of_tile_09197aa9813a", {"local_moves": {"blue": [0, 4], "white": [2, 6]}},
     ["case 4"]),
    ("T_middle1", "tmiddle1", {"local_moves": {"blue": [1, 1], "white": [0, 0]}}, ["case 5"]),
    ("J5", "atlas_3x5_W21845", {}, ["case 5"]),
    ("Z7", "z7", {"local_moves": {"blue": [1, -1], "white": [0, 0]},
                  "note": "repeatable right seam (port 101); used whenever E4bar follows"}, ["case 6, s >= 11"]),
    ("Z7_end", "tile_76ba798e4bc4", {"local_moves": {"blue": [1, -1], "white": [0, 0]},
                                     "note": "right port 111: valid only at the physical right edge"},
     ["case 6, s = 7", "base 3x7", "base 3x11"]),
    ("C3", "cap_minus_quarter_blue", {"number_offset": "-1/4"}, ["case 1"]),
    ("E4_open_0_1", "opened_bulk_plus_one_blue", {"number_offset": "1", "opening": [0, 1]}, ["case 1"]),
    ("E4_open_0_3", "opened_bulk_c3_plus_one_blue", {"number_offset": "1", "opening": [0, 3]}, ["case 1"]),
    ("E4_open_1_0", "opened_bulk_middle0_plus_one_blue", {"number_offset": "1", "opening": [1, 0]}, ["case 1"]),
    ("E4_open_1_2", "opened_bulk_middle2_plus_one_blue", {"number_offset": "1", "opening": [1, 2]}, ["case 1"]),
    ("E4_open_2_1", "opened_bulk_2_1_plus_one_blue_V_of_opened_bulk_plus_one_blue",
     {"number_offset": "1", "opening": [2, 1]}, ["case 1"]),
    ("E4_open_2_3", "opened_bulk_2_3_plus_one_blue_V_of_opened_bulk_c3_plus_one_blue",
     {"number_offset": "1", "opening": [2, 3]}, ["case 1"]),
]

SUPPLEMENTARY = {
    "cap_minus_quarter_white": "C3 >= 1/4 (with the Blue file: C3 = 1/4); not needed by the theorem",
    "opened_bulk_plus_one_white": "E4 after Blue (0,1) >= -1; not needed",
    "opened_bulk_c3_plus_one_white": "E4 after Blue (0,3) >= -1; not needed",
    "opened_bulk_middle0_plus_one_white": "E4 after Blue (1,0) >= -1; not needed",
    "opened_bulk_middle2_plus_one_white": "E4 after Blue (1,2) >= -1; not needed",
}
NOTES = {
    "tile_8b16696647a7": "K_outer4 near-match with left port 111; valid only at a physical left edge "
                         "(base 3x11, opening (0,4)); NOT the K_outer4 role",
    "tile_76ba798e4bc4": "Z7 with right port 111; valid only at a physical right edge",
}

BASE_ALIASES = {
    f"certificates/{cid}.json.gz": cid
    for cid in ("tile_8532d5d099db", "tile_4d9d5d12cc0f", "tile_e06eb7fc2dd6", "tile_da4864d83b99",
                "tile_501c8151efe6", "tile_675ea04f7dff", "tile_2398ea84ec04", "tile_468c39840ab4",
                "tile_76ba798e4bc4", "tile_7de2134cc103", "tile_09fb65f2292a", "tile_e4d37d528005",
                "tile_8b16696647a7", "tile_55c55441362e")
}
BASE_ALIASES["certificates/tile_501c8151efe6.json.gz:H1V0"] = "tile_501c8151efe6_H"
BASE_ALIASES["certificates/tile_09fb65f2292a.json.gz:H1V0"] = "tile_09fb65f2292a_H"


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def write_gzip_json(path, doc):
    path.write_bytes(gzip.compress(json.dumps(doc, separators=(",", ":")).encode(), mtime=0))


def main():
    entries, docs = {}, {}
    for cid, kind, rel, source in SOURCES:
        doc = load(CERTS / rel)
        docs[cid] = doc
        entries[cid] = {"id": cid, "kind": kind, "file": f"certificates/{rel}", "height": doc["height"],
                        "width": doc["width"], "root": doc["root"], "source": source}
    (CERTS / "derived").mkdir(exist_ok=True)
    for cid, source_id, transform in DERIVED:
        source = entries[source_id]
        perm = verify.reflection(3, source["width"], *verify.TRANSFORMS[transform])
        doc = verify.transform_certificate(docs[source_id], source["kind"], perm)
        rel = f"derived/{cid}.json.gz"
        write_gzip_json(CERTS / rel, doc)
        docs[cid] = doc
        entries[cid] = {"id": cid, "kind": source["kind"], "file": f"certificates/{rel}", "height": 3,
                        "width": source["width"], "root": doc["root"], "derived_from": source_id,
                        "transform": transform,
                        "source": f"{transform}-reflection of {source_id}, rebuilt by verify.py"}
    for cid, entry in entries.items():
        replay = verify.replay_ordinary if entry["kind"] == "ordinary" else verify.replay_numeric
        entry["nodes"], entry["edges"] = replay(docs[cid], 3, entry["width"], entry["root"])
        entry["sha256"] = hashlib.sha256((HERE / entry["file"]).read_bytes()).hexdigest()
        if cid in SUPPLEMENTARY:
            entry["supplementary"] = SUPPLEMENTARY[cid]
        if cid in NOTES:
            entry["note"] = NOTES[cid]

    files = sorted(p for p in CERTS.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (CERTS / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(CERTS).as_posix()}\n" for p in files))

    roles = []
    for name, cid, extra, used_in in ROLES:
        entry = entries[cid]
        width, blue, white = entry["width"], entry["root"][0], entry["root"][1]
        left, right = verify.ports(white, width)
        item = {"role": name, "certificate": cid, "width": width, "blue_mask": blue, "white_mask": white,
                "white_ports": {"left": left, "right": right}, "diagram": verify.diagram(blue, white, width)}
        item.update(extra)
        offset = extra.get("number_offset")
        item["bound"] = str(-verify.Fraction(offset)) if offset else "0"
        item["claim"] = f"{name} <= {item['bound']}"
        item["used_in"] = used_in
        roles.append(item)

    base_file = CERTS / "base" / "existing_library_scan.json"
    manifest = {
        "format": verify.FORMAT,
        "theorem": "For every n >= 1 the empty 3 x n Col board has value 0 (proofs/construction/empty_3xn_theorem.md).",
        "conventions": {
            "rows": 3,
            "mask_bits": "row-major within the block: bit r*width + c, bit 0 = top-left",
            "ordinary_root": "[Blue-legal mask, White-legal mask], Blue to move; certificate proves Blue-first loss (<= 0)",
            "numeric_root": "[mover mask, opponent mask, q numerator, q denominator]; mover is Left in q; proves G + q <= 0",
            "white_ports": "White legality of the left / right column, read top to bottom",
            "diagram": "o both, b Blue only, w White only, . neither (permissions, not stones)",
        },
        "certificates": [entries[cid] for cid in [s[0] for s in SOURCES] + [d[0] for d in DERIVED]],
        "roles": roles,
        "base_widths": {
            "file": "certificates/base/existing_library_scan.json",
            "source": "proofs/construction/research/existing_library_scan.json (byte-identical copy)",
            "sha256": hashlib.sha256(base_file.read_bytes()).hexdigest(),
            "widths": list(verify.BASE_WIDTHS),
            "certificate_aliases": dict(sorted(BASE_ALIASES.items())),
        },
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote manifest.json: {len(entries)} certificates, {len(roles)} roles; SHA256SUMS: {len(files)} files")


if __name__ == "__main__":
    main()
