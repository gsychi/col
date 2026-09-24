#!/usr/bin/env python3
"""Replay the recovered three-row base witnesses and a usable J5 root.

Search-free: uses stored response DAGs and stored assemblies only.  Does not
import the assembly searcher or any generator.  This finite check does not
replace the all-width induction or resolve its missing T_middle1/Z7 mappings.
"""
from pathlib import Path
import importlib.util
import json
import re


ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT.parent / "original_proof"
ATLAS = ROOT.parent.parent / "atlas"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ordinary = load_module("provenance_ordinary_verifier", ORIGINAL / "verify.py")
atlas = load_module("provenance_atlas_verifier", ATLAS / "verify.py")
require = ordinary.require


def checked_tiles():
    manifest = json.loads((ORIGINAL / "manifest.json").read_text())
    require(manifest["format"] == "col-one-sided-tiles-v1", "wrong manifest format")
    tiles = {}
    for entry in manifest["certificates"]:
        name = entry["file"]
        require(name not in tiles, "duplicate certificate filename")
        path = (ORIGINAL / name).resolve()
        require(path.is_relative_to(ORIGINAL.resolve()), "certificate path escapes package")
        tiles[name] = ordinary.check_tile(path, entry)
    # The original verifier pins these four family roots independently of the
    # manifest.  Other root claims below are pinned by geometry/assembly checks.
    ordinary.check_family_roots(manifest, tiles)
    print(f"VERIFIED source DAGs: {len(tiles)} certificates, "
          f"{sum(t['nodes'] for t in tiles.values())} checkpoints, "
          f"{sum(t['edges'] for t in tiles.values())} edges")
    return tiles


def transform_reference(reference, tiles, board_width, start):
    parts = reference.split(":")
    require(len(parts) in (1, 2), "malformed reflection reference")
    require(parts[0] in tiles, "unknown certificate reference")
    horizontal = vertical = False
    if len(parts) == 2:
        match = re.fullmatch(r"H([01])V([01])", parts[1])
        require(match is not None, "malformed reflection suffix")
        horizontal, vertical = (x == "1" for x in match.groups())
    tile = tiles[parts[0]]
    width = tile["width"]
    require(type(start) is int and 0 <= start <= board_width - width,
            "block outside board")

    def transform(vertex):
        row, column = divmod(vertex, width)
        if horizontal:
            column = width - 1 - column
        if vertical:
            row = 2 - row
        return row * board_width + start + column

    return tile, transform


def check_base(record, tiles):
    n = record["n"]
    require(n in (3, 7, 11), "unexpected base width")
    neighbors = ordinary.neighborhood(3, n)
    all_cells = set(range(3 * n))
    representatives, covered = set(), set()
    for answer in record["answers"]:
        br, bc = answer["open"]
        wr, wc = answer["reply"]
        require(all(type(x) is int for x in (br, bc, wr, wc)), "noninteger move")
        require(br in (0, 1) and 0 <= bc <= n // 2, "unnormalized opening")
        require((br, bc) not in representatives, "duplicate opening")
        representatives.add((br, bc))
        require(0 <= wr < 3 and 0 <= wc < n, "reply outside board")
        blue, white = br * n + bc, wr * n + wc
        actual_a = all_cells - {blue} - neighbors[blue]
        actual_b = all_cells - {blue}
        require(white in actual_b, "illegal first White reply")
        actual_a -= {white}
        actual_b = actual_b - {white} - neighbors[white]

        virtual_a, virtual_b, owner = set(), set(), {}
        for region, block in enumerate(answer["plan"]):
            tile, transform = transform_reference(
                block["certificate"], tiles, n, block["start_column"])
            require(tile["width"] == block["width"], "block width mismatch")
            for vertex in range(3 * tile["width"]):
                cell = transform(vertex)
                require(cell not in owner, "overlapping blocks")
                owner[cell] = region
            virtual_a.update(transform(v) for v in tile["a"])
            virtual_b.update(transform(v) for v in tile["b"])

        require(actual_a <= virtual_a, "comparison deletes an actual Blue move")
        require(virtual_b <= actual_b, "comparison invents a White move")
        for cell in all_cells:
            for other in neighbors[cell]:
                if owner.get(cell, -1) != owner.get(other, -1):
                    require(not (cell in virtual_b and other in virtual_b),
                            "White interaction crosses a region seam")
        covered.update((r, c) for r in (br, 2 - br) for c in (bc, n - 1 - bc))

    expected = {(r, c) for r in (0, 1) for c in range(n // 2 + 1)}
    require(representatives == expected, "incomplete normalized opening set")
    require(covered == {(r, c) for r in range(3) for c in range(n)},
            "reflections fail to cover all opening cells")
    require(record["solved"] == len(expected) == record["total"] and not record["failed"],
            "stored coverage metadata disagrees")
    print(f"VERIFIED stored 3x{n} base: {len(representatives)} representatives, "
          f"{len(covered)} openings; geometry, reflections, and seams checked")


def check_j5():
    # Bind the claimed role to an explicit root, independently of atlas labels.
    a, b = 32767, 21845
    diagram = ["obobo", "bobob", "obobo"]
    expected_b = sum(1 << (r * 5 + c) for r in range(3) for c in range(5)
                     if diagram[r][c] == "o")
    require(a == (1 << 15) - 1 and b == expected_b, "J5 pattern mismatch")
    ports = tuple(sum(((b >> (r * 5 + c)) & 1) << r for r in range(3))
                  for c in (0, 4))
    require(ports == (5, 5), "J5 has the wrong White ports")
    nodes, edges = atlas.verify_strategy(
        ATLAS / "certificates/3x5/W21845.json.gz", 3, 5, (a, b))
    print(f"VERIFIED usable J5 <= 0: root ({a},{b}), White ports 101/101, "
          f"{nodes} checkpoints, {edges} edges")


def main():
    tiles = checked_tiles()
    records = json.loads((ROOT / "existing_library_scan.json").read_text())
    for n in (3, 7, 11):
        matches = [record for record in records if record["n"] == n]
        require(len(matches) == 1, "missing or duplicate base record")
        check_base(matches[0], tiles)
    check_j5()
    print("Finite provenance checks passed; missing later gadget mappings remain separate.")


if __name__ == "__main__":
    main()
