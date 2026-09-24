#!/usr/bin/env python3
"""Negative controls: verify.py must reject each deliberately broken input.

Standard library only. Tampering happens in memory or in a scratch copy under
/tmp/three_row/; nothing in this directory is modified.

    python3 proofs/construction/three_row/negative_controls.py
"""
import copy
import gzip
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/tmp/three_row")
SWEEP = 23   # smallest sweep containing case 4 with a >= 1 (first at n = 19)
SCRATCH_COPIES = []


def load_verifier():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("three_row_verify_controls", HERE / "verify.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V = load_verifier()
MANIFEST = json.loads((HERE / "manifest.json").read_text())


def role_item(manifest, name):
    return next(item for item in manifest["roles"] if item["role"] == name)


def run(package=None, manifest=None, directory=HERE, max_width=SWEEP, documents_override=None):
    if package is None:
        package = V.load_package(directory, manifest, documents_override)
    V.verify(directory, max_width, package=package, verbose=False)


def scratch_copy():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix="negctl_", dir=SCRATCH))
    SCRATCH_COPIES.append(target)
    shutil.copy2(HERE / "manifest.json", target / "manifest.json")
    shutil.copytree(HERE / "certificates", target / "certificates")
    return target


def rehash(directory, relative, manifest):
    """Refresh SHA256SUMS and manifest hashes after editing a scratch file."""
    certs = directory / "certificates"
    lines = []
    for line in (certs / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if name == relative:
            digest = hashlib.sha256((certs / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (certs / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    new = hashlib.sha256((certs / relative).read_bytes()).hexdigest()
    for entry in manifest["certificates"]:
        if entry["file"] == f"certificates/{relative}":
            entry["sha256"] = new
    if manifest["base_widths"]["file"] == f"certificates/{relative}":
        manifest["base_widths"]["sha256"] = new
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


# --- the controls -----------------------------------------------------------

def old_z7_in_repeated_position():
    """Case 6 with the physical-edge Z7 (right port 111) followed by E4bar."""
    package = V.load_package(HERE)
    original = V.plan_width_4k3

    def planner(pkg, n, r, c):
        plan = original(pkg, n, r, c)
        if plan.case == 6 and plan.params["s"] > 7:
            plan.blocks[1] = V.role_block(pkg, "Z7_end", plan.blocks[1].start)
        return plan

    package.planner = planner
    run(package)


def wrong_reply_case3():
    """Case 3 with White at (2, c-1) instead of (2, c-2)."""
    package = V.load_package(HERE)
    original = V.plan_width_4k3

    def planner(pkg, n, r, c):
        plan = original(pkg, n, r, c)
        if plan.case == 3:
            plan.white = (2, c - 1)
        return plan

    package.planner = planner
    run(package)


def wrong_reply_case6():
    """Case 6 with White at (2, c+1) instead of (0, c+1)."""
    package = V.load_package(HERE)
    original = V.plan_width_4k3

    def planner(pkg, n, r, c):
        plan = original(pkg, n, r, c)
        if plan.case == 6:
            plan.white = (2, c + 1)
        return plan

    package.planner = planner
    run(package)


def flipped_declared_port():
    """T_middle1's declared left port flipped from 001 to 101."""
    manifest = copy.deepcopy(MANIFEST)
    role_item(manifest, "T_middle1")["white_ports"]["left"] = "101"
    run(manifest=manifest)


def flipped_mask_bit():
    """T_middle1's White mask with the seam exclusion at local (0,5) removed."""
    manifest = copy.deepcopy(MANIFEST)
    role_item(manifest, "T_middle1")["white_mask"] ^= 1 << 5
    run(manifest=manifest)


def left_port_111_after_e4():
    """K_outer4 bound to tile_8b16696647a7 (left port 111), pins adjusted to match.

    Binding succeeds; the assembly must fail where E4 precedes K_outer4 (a >= 1).
    """
    manifest = copy.deepcopy(MANIFEST)
    item = role_item(manifest, "K_outer4")
    cert = next(e for e in manifest["certificates"] if e["id"] == "tile_8b16696647a7")
    blue, white = cert["root"]
    left, right = V.ports(white, 7)
    item.update(certificate=cert["id"], blue_mask=blue, white_mask=white,
                white_ports={"left": left, "right": right}, diagram=V.diagram(blue, white, 7))
    saved = V.PINNED_ROLES["K_outer4"]
    V.PINNED_ROLES["K_outer4"] = (7, blue, white)
    try:
        run(manifest=manifest)
    finally:
        V.PINNED_ROLES["K_outer4"] = saved


def corrupted_certificate_reply():
    """One White reply in the T_middle1 DAG changed."""
    doc = json.loads(gzip.decompress((HERE / "certificates/ordinary/tmiddle1.json.gz").read_bytes()))
    record = doc["nodes"][0]
    record[2][0] = (record[2][0] + 1) % 18
    run(documents_override={"tmiddle1": doc})


def byte_corruption():
    """One byte of the repeatable Z7 file flipped on disk (scratch copy)."""
    directory = scratch_copy()
    path = directory / "certificates/ordinary/z7.json.gz"
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))
    run(directory=directory)


def tampered_derived_certificate():
    """Stored K_outer4 reflection edited, with hashes refreshed so only the re-derivation can catch it."""
    directory = scratch_copy()
    relative = "derived/K_outer4_H_of_tile_09197aa9813a.json.gz"
    path = directory / "certificates" / relative
    doc = json.loads(gzip.decompress(path.read_bytes()))
    doc["nodes"][0][2][0] = (doc["nodes"][0][2][0] + 1) % 21
    path.write_bytes(gzip.compress(json.dumps(doc, separators=(",", ":")).encode(), mtime=0))
    manifest = rehash(directory, relative, copy.deepcopy(MANIFEST))
    run(directory=directory, manifest=manifest)


def missing_odd_cell():
    """The E4 opened-at-(1,2) bound removed from the manifest."""
    manifest = copy.deepcopy(MANIFEST)
    manifest["roles"] = [item for item in manifest["roles"] if item["role"] != "E4_open_1_2"]
    run(manifest=manifest)


def wrong_direction_numeric():
    """Opened-E4 (0,1) role bound to the White-mover (>= -1) certificate."""
    manifest = copy.deepcopy(MANIFEST)
    role_item(manifest, "E4_open_0_1")["certificate"] = "opened_bulk_plus_one_white"
    run(manifest=manifest)


def weak_cap_bound():
    """C3 treated as <= 1 instead of <= 1/4: case 1 no longer strictly negative."""
    package = V.load_package(HERE)
    package.roles["C3"].bound = Fraction(1)
    run(package)


def case5_below_threshold():
    """Case 5 applied at n = 11 (k = 2), where b = k-a-2 < 0."""
    package = V.load_package(HERE)
    V.check_comparison(11, V.plan_width_4k3(package, 11, 1, 5, min_k=1))


def base_width_11_removed():
    """Without the stored 3 x 11 base the six cases cannot establish width 11."""
    saved = V.BASE_WIDTHS
    V.BASE_WIDTHS = (3, 7)
    try:
        run()
    finally:
        V.BASE_WIDTHS = saved


def base_witness_dropped():
    """The 3 x 7 answer to Blue (1,3) removed from the stored base assemblies."""
    directory = scratch_copy()
    relative = "base/existing_library_scan.json"
    path = directory / "certificates" / relative
    records = json.loads(path.read_text())
    for record in records:
        if record["n"] == 7:
            record["answers"] = [a for a in record["answers"] if a["open"] != [1, 3]]
    path.write_text(json.dumps(records))
    manifest = rehash(directory, relative, copy.deepcopy(MANIFEST))
    run(directory=directory, manifest=manifest)


CONTROLS = [
    (old_z7_in_repeated_position, "White-legal cells on both sides of the seam"),
    (wrong_reply_case3, "comparison deletes an actual Blue move"),
    (wrong_reply_case6, "comparison deletes an actual Blue move"),
    (flipped_declared_port, "declared White ports differ"),
    (flipped_mask_bit, "role masks differ from the certificate root"),
    (left_port_111_after_e4, "White-legal cells on both sides of the seam"),
    (corrupted_certificate_reply, "T"),   # any replay failure; message checked below
    (byte_corruption, "checksum mismatch"),
    (tampered_derived_certificate, "is not the H-reflection of its source"),
    (missing_odd_cell, "no certified bound for E4 opened at (1,2)"),
    (wrong_direction_numeric, "role masks differ from the certificate root"),
    (weak_cap_bound, "is not < 0 with White to move"),
    (case5_below_threshold, "b = k-a-2 = -1 < 0"),
    (base_width_11_removed, "the six-case step needs n = 4k+3 >= 15, got n = 11"),
    (base_witness_dropped, "normalized openings not all answered"),
]
REPLAY_FAILURES = ("illegal White reply", "missing successor checkpoint", "no strict descent")


def main():
    run()   # the unmodified package must pass the same shortened sweep
    print(f"baseline: unmodified package passes (sweep to width {SWEEP})")
    failures = 0
    try:
        for control, expected in CONTROLS:
            try:
                control()
            except V.InvalidPackage as error:
                message = str(error)
                ok = any(x in message for x in REPLAY_FAILURES) if control is corrupted_certificate_reply \
                    else expected in message
                status = "REJECTED as expected" if ok else "REJECTED for an unexpected reason"
                failures += not ok
                print(f"{status:34s} {control.__name__}: {message}")
            else:
                failures += 1
                print(f"{'NOT REJECTED':34s} {control.__name__}")
    finally:
        for directory in SCRATCH_COPIES:
            shutil.rmtree(directory, ignore_errors=True)
    print(f"{len(CONTROLS) - failures}/{len(CONTROLS)} negative controls behaved as expected")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
