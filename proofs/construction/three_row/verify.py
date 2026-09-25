#!/usr/bin/env python3
"""Search-free verifier for the theorem that every empty 3 x n Col board is 0.

Python 3.9+, standard library only. It imports nothing outside this directory
and never runs a game-tree search or a certificate generator. Run from anywhere:

    python3 proofs/construction/three_row/verify.py [--max-width N] [--quiet]

Checks, in order (PROOF_CHECKLIST.md explains why they cover every width):

1. SHA-256 of every file under certificates/, against certificates/SHA256SUMS
   and manifest.json.
2. Every ordinary response DAG (Blue to move; exactly one legal White reply to
   every Blue move; closure; strict descent; reachability) and every dyadic
   comparison DAG (mover-as-Left, with a number component).
3. Derived certificates (reflections) rebuilt from their sources, compared with
   the stored copies, and replayed in full; each reflection is checked to be a
   grid automorphism.
4. Role binding: every gadget role of empty_3xn_theorem.md is tied to an exact
   root (width, Blue mask, White mask), declared White ports and diagram, and
   a certified bound; the roles are also pinned independently of the manifest.
5. The stored finite assemblies for the base widths 3, 7, 11.
6. Width-independent local lemmas: the seam table for every adjacent pair of
   block types, the block types allowed at the physical ends, and every local
   window around an opening and its reply.
7. A regression sweep over every width 1..N (default 203): even widths
   (half-turn), 4k+1 (E4^k F1), 4k+3 (all six cases for every normalized
   opening, reflection coverage, and the strictly decreasing recursion).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROWS = 3
FORMAT = "col-3xn-all-width-package-v1"
DEFAULT_MAX_WIDTH = 203
BASE_WIDTHS = (3, 7, 11)

# Roots fixed by the theorem, the provenance audit, and the stream brief:
# role -> (width, Blue mask, White mask). The manifest must agree with these.
PINNED_ROLES = {
    "E4": (4, 4095, 2023),
    "E4bar": (4, 4095, 3710),
    "F1": (1, 7, 5),
    "K_corner": (3, 244, 94),
    "K_outer2": (7, 2080241, 2039675),
    "K_outer4": (7, 1046471, 515951),
    "T_middle1": (6, 253500, 130844),
    "J5": (5, 32767, 21845),
    "Z7": (7, 2097022, 2088828),
    "Z7_end": (7, 2097022, 2097020),
    "C3": (3, 511, 503),
}
ODD_E4_CELLS = ((0, 1), (0, 3), (1, 0), (1, 2), (2, 1), (2, 3))

# Blocks that may sit away from the opening: they must allow Blue everywhere.
FULL_BLUE_FILLERS = ("E4", "E4bar", "C3", "J5", "F1")

# Every local window the six cases can produce for k >= 3, as block column
# ranges relative to the opening column (derived by hand in
# PROOF_CHECKLIST.md, section 4). The sweep must find exactly these. Case 1
# has five: local cells (0,1), (0,3), (1,2), and (1,0) with or without an E4
# block to its left; normalized openings never lie in row 2. The row-2 odd
# cells are exercised separately ("1-row2") without reflecting the board.
EXPECTED_WINDOWS = {
    1: {"E4_open_0_1[-1..+2]", "E4_open_0_3[-3..+0], E4[+1..+4]", "off-board[-1..-1], E4_open_1_0[+0..+3]",
        "E4[-4..-1], E4_open_1_0[+0..+3]", "E4_open_1_2[-2..+1]"},
    2: {"off-board[-1..-1], K_corner[+0..+2], E4bar[+3..+6]"},
    3: {"off-board[-3..-3], K_outer2[-2..+4]", "E4[-6..-3], K_outer2[-2..+4]"},
    4: {"K_outer4[-4..+2], E4bar[+3..+6]"},
    5: {"off-board[-2..-2], T_middle1[-1..+4]", "E4[-5..-2], T_middle1[-1..+4]"},
    6: {"H_c[-1..-1], DEAD[+0..+0], Z7[+1..+7]", "H_c[-1..-1], DEAD[+0..+0], Z7_end[+1..+7]"},
    "1-row2": {"E4_open_2_1[-1..+2]", "E4_open_2_3[-3..+0], E4[+1..+4]"},
}


class InvalidPackage(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidPackage(message)


# ---------------------------------------------------------------------------
# Grid primitives (coordinate based)
# ---------------------------------------------------------------------------

def neighbors(h, w):
    table = []
    for v in range(h * w):
        r, c = divmod(v, w)
        near = ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
        table.append(frozenset(rr * w + cc for rr, cc in near if 0 <= rr < h and 0 <= cc < w))
    return tuple(table)


def cells(mask, size):
    require(type(mask) is int and 0 <= mask < 1 << size, "invalid legality mask")
    return frozenset(v for v in range(size) if mask >> v & 1)


def mask_of(cell_set):
    return sum(1 << v for v in cell_set)


def full_mask(width):
    return (1 << (ROWS * width)) - 1


def ports(white_mask, width):
    """White legality of the left and right columns, top to bottom."""
    def column(c):
        return "".join("1" if white_mask >> (r * width + c) & 1 else "0" for r in range(ROWS))
    return column(0), column(width - 1)


def diagram(blue_mask, white_mask, width):
    symbol = {(1, 1): "o", (1, 0): "b", (0, 1): "w", (0, 0): "."}
    return ["".join(symbol[(blue_mask >> (r * width + c) & 1, white_mask >> (r * width + c) & 1)]
                    for c in range(width)) for r in range(ROWS)]


def reflection(h, w, horizontal, vertical):
    perm = []
    for v in range(h * w):
        r, c = divmod(v, w)
        perm.append((h - 1 - r if vertical else r) * w + (w - 1 - c if horizontal else c))
    return tuple(perm)


def require_automorphism(h, w, perm):
    nb = neighbors(h, w)
    require(sorted(perm) == list(range(h * w)), "reflection is not a permutation")
    for v in range(h * w):
        require(frozenset(perm[x] for x in nb[v]) == nb[perm[v]], "reflection is not a grid automorphism")


def permute_mask(mask, perm):
    return sum(1 << perm[v] for v in range(len(perm)) if mask >> v & 1)


# ---------------------------------------------------------------------------
# Certificate checkers
# ---------------------------------------------------------------------------

def replay_ordinary(doc, h, w, root):
    """Every checkpoint (A, B) has Blue to move and one legal White reply per Blue move.

    Proves by induction on |A u B| that Blue, moving first, loses from every
    checkpoint; in particular the root game is <= 0.
    """
    require(isinstance(doc, dict) and (doc.get("height"), doc.get("width")) == (h, w),
            "certificate dimensions")
    require(doc.get("root") == list(root), "certificate root")
    size = h * w
    nb = neighbors(h, w)
    nodes = {}
    for record in doc["nodes"]:
        require(isinstance(record, list) and len(record) == 3, "malformed checkpoint")
        a, b, replies = record
        blue, white = cells(a, size), cells(b, size)
        require(isinstance(replies, list), "replies must be a list")
        require((a, b) not in nodes, "duplicate checkpoint")
        nodes[(a, b)] = (blue, white, replies)
    start = tuple(root)
    require(start in nodes, "missing root checkpoint")
    children, edges = {}, 0
    for key, (blue, white, replies) in nodes.items():
        blue_moves = sorted(blue)
        require(len(replies) == len(blue_moves), "not every Blue move has exactly one White reply")
        kids = []
        for v, reply in zip(blue_moves, replies):
            require(type(reply) is int, "non-integer White reply")
            blue1, white1 = blue - {v} - nb[v], white - {v}
            require(reply in white1, "illegal White reply")
            blue2, white2 = blue1 - {reply}, white1 - {reply} - nb[reply]
            child = (mask_of(blue2), mask_of(white2))
            require(child in nodes, "missing successor checkpoint")
            require(len(blue2 | white2) <= len(blue | white) - 2, "no strict descent")
            kids.append(child)
            edges += 1
        children[key] = kids
    seen, stack = {start}, [start]
    while stack:
        for child in children[stack.pop()]:
            if child not in seen:
                seen.add(child)
                stack.append(child)
    require(len(seen) == len(nodes), "unreachable checkpoints")
    return len(nodes), edges


def dyadic(numerator, denominator):
    require(type(numerator) is int and type(denominator) is int and denominator > 0
            and denominator & (denominator - 1) == 0, "number is not dyadic")
    return Fraction(numerator, denominator)


def replay_numeric(doc, h, w, root):
    """Checkpoints (a, b, q): a = mover's legal cells, b = opponent's, and the
    mover is Left in the added dyadic number q. Every option of the mover
    (board moves and the canonical Left option of q) has one listed reply.

    Proves the mover loses from every checkpoint: with the mover's colour as
    Left, the root game G satisfies G + q <= 0, i.e. G <= -q.
    """
    require(isinstance(doc, dict) and (doc.get("height"), doc.get("width")) == (h, w),
            "certificate dimensions")
    require(doc.get("root") == list(root), "certificate root")
    size = h * w
    require(1 <= size <= 30, "board size outside this format")
    nb = neighbors(h, w)

    def options(a, b, q):
        result = {v: (b - {v}, a - {v} - nb[v], -q) for v in a}
        if q.denominator != 1:
            result[-1] = (b, a, -Fraction(q.numerator - 1, q.denominator))
        elif q.numerator > 0:
            result[-1] = (b, a, -(q - 1))
        return result

    def rank(a, b, q):
        if q.denominator == 1:
            day = abs(q.numerator)
        else:
            day = abs(q.numerator) // q.denominator + 1 + (q.denominator.bit_length() - 1)
        return len(a | b) + day

    nodes = {}
    for record in doc["nodes"]:
        require(isinstance(record, list) and len(record) == 5, "malformed checkpoint")
        a, b, num, den, replies = record
        key = (cells(a, size), cells(b, size), dyadic(num, den))
        require(key not in nodes, "duplicate checkpoint")
        require(isinstance(replies, list), "replies must be a list")
        nodes[key] = replies
    start = (cells(root[0], size), cells(root[1], size), dyadic(root[2], root[3]))
    require(start in nodes, "missing root checkpoint")
    children, edges = {}, 0
    for key, replies in nodes.items():
        first_options = options(*key)
        require(all(isinstance(p, list) and len(p) == 2 and all(type(x) is int for x in p)
                    for p in replies), "malformed reply pair")
        require(len(replies) == len(first_options) and {p[0] for p in replies} == set(first_options),
                "first player's options not all answered exactly once")
        kids = []
        for first, reply in replies:
            middle = first_options[first]
            answers = options(*middle)
            require(reply in answers, "illegal reply")
            child = answers[reply]
            require(child in nodes, "missing successor checkpoint")
            require(rank(*child) < rank(*middle) < rank(*key), "no strict descent")
            kids.append(child)
            edges += 1
        children[key] = kids
    seen, stack = {start}, [start]
    while stack:
        for child in children[stack.pop()]:
            if child not in seen:
                seen.add(child)
                stack.append(child)
    require(len(seen) == len(nodes), "unreachable checkpoints")
    require(edges == doc.get("edges"), "edge-count metadata inside the certificate")
    return len(nodes), edges


def transform_certificate(doc, kind, perm):
    """Image of a certificate under a cell permutation (used for reflections)."""
    h, w = doc["height"], doc["width"]
    size = h * w
    require(len(perm) == size, "permutation size")
    if kind == "ordinary":
        nodes = []
        for a, b, replies in doc["nodes"]:
            moves = [v for v in range(size) if a >> v & 1]
            require(len(moves) == len(replies), "malformed source checkpoint")
            pairs = sorted((perm[v], perm[r]) for v, r in zip(moves, replies))
            nodes.append([permute_mask(a, perm), permute_mask(b, perm), [r for _, r in pairs]])
        root = [permute_mask(doc["root"][0], perm), permute_mask(doc["root"][1], perm)]
        return {"height": h, "width": w, "root": root, "nodes": nodes}

    def cell(x):
        return x if x == -1 else perm[x]

    nodes = [[permute_mask(a, perm), permute_mask(b, perm), num, den,
              sorted([cell(first), cell(reply)] for first, reply in replies)]
             for a, b, num, den, replies in doc["nodes"]]
    r = doc["root"]
    root = [permute_mask(r[0], perm), permute_mask(r[1], perm), r[2], r[3]]
    return {"height": h, "width": w, "root": root, "nodes": nodes, "edges": doc["edges"]}


CORE_KEYS = {"ordinary": ("height", "width", "root", "nodes"),
             "numeric": ("height", "width", "root", "nodes", "edges")}
TRANSFORMS = {"H": (True, False), "V": (False, True)}


# ---------------------------------------------------------------------------
# Package loading: hashes, replay, derived certificates, role binding
# ---------------------------------------------------------------------------

@dataclass
class Role:
    name: str
    width: int
    blue: int
    white: int
    bound: Fraction
    certificate: str
    left_port: str
    right_port: str
    opening: tuple | None = None


@dataclass
class Package:
    directory: Path
    manifest: dict
    certificates: dict        # id -> manifest entry
    documents: dict           # id -> decoded certificate
    counts: dict              # id -> (checkpoints, edges)
    roles: dict               # role name -> Role
    base_records: dict = field(default_factory=dict)
    planner: object = None    # hook used by negative controls


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_sha256sums(path):
    sums = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*").strip()
        require(name not in sums, f"duplicate SHA256SUMS entry {name}")
        sums[name] = digest
    return sums


def package_path(directory, relative):
    path = (directory / relative).resolve()
    require(path.is_relative_to(directory / "certificates"), f"path escapes certificates/: {relative}")
    return path


def load_package(directory=HERE, manifest=None, documents_override=None):
    """Hash-check, replay and bind everything named in the manifest.

    documents_override (id -> decoded doc) lets negative controls tamper with a
    decoded certificate without touching files: the file on disk is still
    hash-checked, then its decoded content is replaced before replay.
    """
    directory = Path(directory).resolve()
    if manifest is None:
        manifest = json.loads((directory / "manifest.json").read_text())
    require(manifest.get("format") == FORMAT, "unknown manifest format")
    cert_dir = directory / "certificates"
    sums = read_sha256sums(cert_dir / "SHA256SUMS")
    on_disk = {p.relative_to(cert_dir).as_posix() for p in cert_dir.rglob("*")
               if p.is_file() and p.name != "SHA256SUMS" and not p.name.startswith(".")}
    require(on_disk == set(sums), "SHA256SUMS does not list exactly the files under certificates/")
    for name, digest in sums.items():
        require(sha256((cert_dir / name).read_bytes()) == digest, f"checksum mismatch: {name}")

    entries = {}
    for entry in manifest["certificates"]:
        require(entry["id"] not in entries, f"duplicate certificate id {entry['id']}")
        entries[entry["id"]] = entry
    documents, counts = {}, {}
    ordered = sorted(entries.values(), key=lambda e: "derived_from" in e)
    for entry in ordered:
        cid, kind = entry["id"], entry["kind"]
        require(kind in CORE_KEYS, f"unknown certificate kind for {cid}")
        path = package_path(directory, entry["file"])
        rel = path.relative_to(cert_dir).as_posix()
        raw = path.read_bytes()
        require(sha256(raw) == entry["sha256"] == sums.get(rel), f"manifest checksum mismatch: {cid}")
        doc = json.loads(gzip.decompress(raw))
        if documents_override and cid in documents_override:
            doc = documents_override[cid]
        if "derived_from" in entry:
            source = entries[entry["derived_from"]]
            require(source["kind"] == kind and "derived_from" not in source, f"bad derivation source for {cid}")
            h, w = source["height"], source["width"]
            perm = reflection(h, w, *TRANSFORMS[entry["transform"]])
            require_automorphism(h, w, perm)
            rebuilt = transform_certificate(documents[source["id"]], kind, perm)
            require(all(doc.get(key) == rebuilt[key] for key in CORE_KEYS[kind]),
                    f"stored derived certificate {cid} is not the {entry['transform']}-reflection of its source")
            expected_root = [permute_mask(source["root"][0], perm), permute_mask(source["root"][1], perm)]
            require(entry["root"][:2] == expected_root and entry["root"][2:] == source["root"][2:],
                    f"derived root of {cid} is not the reflected source root")
        require(entry["height"] == ROWS, f"{cid}: height must be 3")
        replay = replay_ordinary if kind == "ordinary" else replay_numeric
        counts[cid] = replay(doc, ROWS, entry["width"], entry["root"])
        require(counts[cid] == (entry["nodes"], entry["edges"]), f"checkpoint/edge metadata mismatch: {cid}")
        documents[cid] = doc

    roles = {}
    for item in manifest["roles"]:
        name = item["role"]
        require(name not in roles, f"duplicate role {name}")
        entry = entries[item["certificate"]]
        width, blue, white = item["width"], item["blue_mask"], item["white_mask"]
        require(entry["width"] == width, f"{name}: width differs from its certificate")
        root = entry["root"]
        require(root[0] == blue and root[1] == white, f"{name}: role masks differ from the certificate root")
        if entry["kind"] == "ordinary":
            require(len(root) == 2 and "number_offset" not in item, f"{name}: ordinary root expected")
            bound = Fraction(0)
        else:
            offset = dyadic(root[2], root[3])
            require(Fraction(item["number_offset"]) == offset, f"{name}: number offset differs from the root")
            bound = -offset
        require(Fraction(item["bound"]) == bound, f"{name}: declared bound is not the certified bound")
        left, right = ports(white, width)
        require((left, right) == (item["white_ports"]["left"], item["white_ports"]["right"]),
                f"{name}: declared White ports differ from the White mask")
        require(diagram(blue, white, width) == item["diagram"], f"{name}: declared diagram differs from the masks")
        if name in PINNED_ROLES:
            require(PINNED_ROLES[name] == (width, blue, white), f"{name}: root differs from the pinned theorem root")
        opening = tuple(item["opening"]) if "opening" in item else None
        roles[name] = Role(name, width, blue, white, bound, item["certificate"], left, right, opening)
    require(set(PINNED_ROLES) <= set(roles), "a pinned theorem role is unbound")
    package = Package(directory, manifest, entries, documents, counts, roles)
    package.planner = plan_width_4k3
    return package


def check_opened_e4_roles(package):
    """The six odd-parity openings of E4 each have a certified bound <= -1."""
    e4 = package.roles["E4"]
    nb = neighbors(ROWS, 4)
    for r, c in ODD_E4_CELLS:
        name = f"E4_open_{r}_{c}"
        require(name in package.roles, f"no certified bound for E4 opened at ({r},{c})")
        role = package.roles[name]
        v = r * 4 + c
        require(role.opening == (r, c) and role.width == 4, f"{name}: wrong opening or width")
        require(role.blue == e4.blue & ~((1 << v) | mask_of(nb[v])) and role.white == e4.white & ~(1 << v),
                f"{name}: root is not E4 after Blue's local move ({r},{c})")
        require(role.bound <= -1, f"{name}: bound is not <= -1")
    odd = {(r, c) for r in range(ROWS) for c in range(4) if (r + c) % 2}
    require(odd == set(ODD_E4_CELLS), "odd-parity cell list of E4 is incomplete")
    return len(ODD_E4_CELLS)


# ---------------------------------------------------------------------------
# Board positions and the comparison-principle checker
# ---------------------------------------------------------------------------

_BOARD_NEIGHBORS = {}


def board_neighbor_masks(n):
    if n not in _BOARD_NEIGHBORS:
        _BOARD_NEIGHBORS[n] = tuple(mask_of(s) for s in neighbors(ROWS, n))
    return _BOARD_NEIGHBORS[n]


def play(n, moves):
    """Legal play from the empty 3 x n board. moves: [(player, (r, c)), ...]."""
    nb = board_neighbor_masks(n)
    blue = white = (1 << (ROWS * n)) - 1
    for player, (r, c) in moves:
        require(0 <= r < ROWS and 0 <= c < n, f"move ({r},{c}) is off the 3x{n} board")
        v = r * n + c
        closed = (1 << v) | nb[v]
        if player == "Blue":
            require(blue >> v & 1, f"Blue move ({r},{c}) is illegal")
            blue, white = blue & ~closed, white & ~(1 << v)
        else:
            require(white >> v & 1, f"White reply ({r},{c}) is illegal")
            blue, white = blue & ~(1 << v), white & ~closed
    return blue, white


def embed(local, width, start, n):
    row = (1 << width) - 1
    return sum(((local >> (r * width)) & row) << (r * n + start) for r in range(ROWS))


@dataclass
class Block:
    label: str            # role name, or "H_c" for an empty region supplied by induction
    start: int
    width: int
    blue: int
    white: int
    bound: Fraction


def role_block(package, name, start):
    role = package.roles[name]
    return Block(name, start, role.width, role.blue, role.white, role.bound)


def empty_block(start, width):
    return Block("H_c", start, width, full_mask(width), full_mask(width), Fraction(0))


@dataclass
class Plan:
    case: object
    blue: tuple | None
    white: tuple | None
    blocks: list
    dead: list
    to_move: str
    recursive: int | None = None
    params: dict = field(default_factory=dict)

    def moves(self):
        result = []
        if self.blue is not None:
            result.append(("Blue", self.blue))
        if self.white is not None:
            result.append(("White", self.white))
        return result


def check_comparison(n, plan):
    """The comparison principle's hypotheses and the bound bookkeeping.

    Returns (A, B, owner): actual legal masks and the owner of each column.
    """
    blue, white = play(n, plan.moves())
    owner = [None] * n
    for i, block in enumerate(plan.blocks):
        require(block.width >= 1 and 0 <= block.start and block.start + block.width <= n,
                f"block {block.label} lies outside the board")
        for c in range(block.start, block.start + block.width):
            require(owner[c] is None, "overlapping blocks")
            owner[c] = i
    for c in plan.dead:
        require(0 <= c < n and owner[c] is None, "dead column overlaps a block")
        owner[c] = "dead"
    require(all(o is not None for o in owner), "a column is neither tiled nor dead")
    blue_star = white_star = 0
    for block in plan.blocks:
        blue_star |= embed(block.blue, block.width, block.start, n)
        white_star |= embed(block.white, block.width, block.start, n)
    require(blue & ~blue_star == 0, "comparison deletes an actual Blue move")
    require(white_star & ~white == 0, "comparison gives White a move she does not have")
    # Blocks are column intervals, so only horizontal edges can cross a seam.
    for c in range(n - 1):
        if owner[c] != owner[c + 1]:
            for r in range(ROWS):
                require(not (white_star >> (r * n + c) & 1 and white_star >> (r * n + c + 1) & 1),
                        f"White-legal cells on both sides of the seam between columns {c} and {c + 1}")
    total = sum((block.bound for block in plan.blocks), Fraction(0))
    if plan.to_move == "Blue":
        require(total <= 0, f"bound sum {total} is not <= 0 with Blue to move")
    elif plan.to_move == "White":
        require(total < 0, f"bound sum {total} is not < 0 with White to move")
    else:
        raise InvalidPackage("unknown player to move")
    return blue, white, owner


# ---------------------------------------------------------------------------
# The theorem's constructions, transcribed from empty_3xn_theorem.md
# ---------------------------------------------------------------------------

def plan_width_4k1(package, n):
    k, rem = divmod(n - 1, 4)
    require(rem == 0 and k >= 0, "not a 4k+1 width")
    blocks = [role_block(package, "E4", 4 * i) for i in range(k)] + [role_block(package, "F1", 4 * k)]
    return Plan("4k+1", None, None, blocks, [], "Blue", params={"k": k})


def plan_width_4k3(package, n, r, c, min_k=3):
    """The six cases for n = 4k+3 >= 15 and a normalized Blue opening (r, c).

    min_k < 3 is only used by the diagnostic that shows why widths 7 and 11
    need stored base assemblies.
    """
    k, rem = divmod(n - 3, 4)
    require(rem == 0 and k >= min_k, f"the six-case step needs n = 4k+3 >= 15, got n = {n}")
    require(r in (0, 1) and 0 <= c <= 2 * k + 1, f"opening ({r},{c}) is not normalized")
    holds = {
        1: (r + c) % 2 == 1,
        2: r == 0 and c == 0,
        3: r == 0 and c % 4 == 2,
        4: r == 0 and c % 4 == 0 and c >= 4,
        5: r == 1 and c % 4 == 1,
        6: r == 1 and c % 4 == 3,
    }
    matching = [case for case, ok in holds.items() if ok]
    require(len(matching) == 1, f"opening ({r},{c}) at n={n} matches cases {matching}, not exactly one")
    case = matching[0]
    E4 = lambda start: role_block(package, "E4", start)            # noqa: E731
    E4bar = lambda start: role_block(package, "E4bar", start)      # noqa: E731
    if case == 1:
        return plan_case1(package, n, r, c)
    if case == 2:
        blocks = [role_block(package, "K_corner", 0)] + [E4bar(3 + 4 * i) for i in range(k)]
        return Plan(2, (r, c), (2, 2), blocks, [], "Blue", params={"k": k})
    if case == 3:
        a = (c - 2) // 4
        b = k - a - 1
        require(b >= 0, f"case 3 at n={n}, c={c}: b = k-a-1 = {b} < 0")
        blocks = [E4(4 * i) for i in range(a)] + [role_block(package, "K_outer2", 4 * a)]
        blocks += [E4bar(4 * a + 7 + 4 * i) for i in range(b)]
        return Plan(3, (r, c), (2, c - 2), blocks, [], "Blue", params={"k": k, "a": a, "b": b})
    if case == 4:
        a = (c - 4) // 4
        b = k - a - 1
        require(a >= 0 and b >= 0, f"case 4 at n={n}, c={c}: a = {a}, b = {b}")
        blocks = [E4(4 * i) for i in range(a)] + [role_block(package, "K_outer4", 4 * a)]
        blocks += [E4bar(4 * a + 7 + 4 * i) for i in range(b)]
        return Plan(4, (r, c), (2, c + 2), blocks, [], "Blue", params={"k": k, "a": a, "b": b})
    if case == 5:
        a = (c - 1) // 4
        b = k - a - 2
        require(b >= 0, f"case 5 at n={n}, c={c}: b = k-a-2 = {b} < 0")
        blocks = [E4(4 * i) for i in range(a)] + [role_block(package, "T_middle1", 4 * a)]
        blocks += [E4(4 * a + 6 + 4 * i) for i in range(b)] + [role_block(package, "J5", 4 * a + 6 + 4 * b)]
        return Plan(5, (r, c), (0, c - 1), blocks, [], "Blue", params={"k": k, "a": a, "b": b})
    s = n - c - 1
    require(c % 4 == 3 and 3 <= c < n, f"case 6: separator column {c} is not 3 mod 4 inside the board")
    require(s >= 7 and s % 4 == 3, f"case 6 at n={n}, c={c}: right width s = {s} is not >= 7 and 3 mod 4")
    z7 = "Z7_end" if s == 7 else "Z7"
    blocks = [empty_block(0, c), role_block(package, z7, c + 1)]
    blocks += [E4bar(c + 8 + 4 * i) for i in range((s - 7) // 4)]
    return Plan(6, (r, c), (0, c + 1), blocks, [c], "Blue", recursive=c, params={"k": k, "s": s})


def plan_case1(package, n, r, c, case=1):
    """Case 1 (odd r+c): E4^k C3; the E4 block holding the opening is bounded by -1.

    Valid for any row, so it is also used, un-normalized, for row-2 openings.
    """
    k = (n - 3) // 4
    require(n == 4 * k + 3 and (r + c) % 2 == 1, "case 1 needs n = 4k+3 and odd r+c")
    require(c < 4 * k, "case 1: the opening is not inside an E4 block")
    j, local = divmod(c, 4)
    require((r + local) % 2 == 1, "case 1: local parity is not odd")
    blocks = [role_block(package, "E4", 4 * i) for i in range(k)]
    blocks[j] = role_block(package, f"E4_open_{r}_{local}", 4 * j)
    blocks.append(role_block(package, "C3", 4 * k))
    return Plan(case, (r, c), None, blocks, [], "White", params={"k": k, "j": j})


def check_case6_structure(n, plan):
    """Case 6: left region is exactly the empty 3 x c board, then a dead column, Z7, E4bar^m."""
    c, s = plan.recursive, plan.params["s"]
    left = plan.blocks[0]
    require(left.label == "H_c" and left.start == 0 and left.width == c
            and left.blue == left.white == full_mask(c), "case 6: left region is not the empty 3 x c board")
    require(c % 4 == 3 and 3 <= c < n, "case 6: recursive width is not 3 mod 4 and strictly smaller")
    require(plan.dead == [c], "case 6: column c is not the dead separator")
    z7 = plan.blocks[1]
    require(z7.start == c + 1 and z7.label == ("Z7_end" if s == 7 else "Z7"),
            "case 6: wrong Z7 version for its position")
    rest = plan.blocks[2:]
    require(len(rest) == (s - 7) // 4 and all(b.label == "E4bar" for b in rest),
            "case 6: right region is not Z7 followed by E4bar blocks")


def normalize(n, r, c):
    return min(r, ROWS - 1 - r), min(c, n - 1 - c)


def check_board_symmetries(n):
    for horizontal, vertical in ((True, False), (False, True), (True, True)):
        require_automorphism(ROWS, n, reflection(ROWS, n, horizontal, vertical))


def check_reflection_coverage(n, handled):
    """Every opening is mapped into the handled normalized set by a board symmetry."""
    for r in range(ROWS):
        for c in range(n):
            require(normalize(n, r, c) in handled, f"opening ({r},{c}) on 3x{n} has no handled image")


# ---------------------------------------------------------------------------
# Local (width-independent) data: windows, seams, ends
# ---------------------------------------------------------------------------

def local_window(n, plan, blue, white):
    """Everything the comparison checks can depend on near the opening.

    Records, relative to the opening column, every cell of a block whose Blue
    mask is not full, every cell within distance one of a stone, and the dead
    column, with its block label, local coordinate, actual bits and virtual
    bits. Every other block must be a full-Blue filler untouched by the stones;
    for such a block the per-cell comparison conditions hold automatically.
    """
    anchor = plan.blue[1]
    affected = set()
    for _, (r, c) in plan.moves():
        affected |= {(r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)}
    on_board = {(r, c) for r, c in affected if 0 <= r < ROWS and 0 <= c < n}
    entries = {("OFF", r, c - anchor) for r, c in affected - on_board if 0 <= r < ROWS}
    for block in plan.blocks:
        span = range(block.start, block.start + block.width)
        touched = {(r, c) for r, c in on_board if c in span}
        full = block.blue == full_mask(block.width)
        if full and not touched:
            require(block.label in FULL_BLUE_FILLERS, f"unexpected block {block.label} away from the opening")
            continue
        if block.label == "H_c":
            record, origin = touched, block.start + block.width   # local columns counted from the right end
        else:
            record, origin = {(r, c) for r in range(ROWS) for c in span}, block.start
        for r, c in record:
            v, lv = r * n + c, r * block.width + (c - block.start)
            entries.add((block.label, r, c - anchor, c - origin, blue >> v & 1, white >> v & 1,
                         block.blue >> lv & 1, block.white >> lv & 1))
    for c in plan.dead:
        for r in range(ROWS):
            v = r * n + c
            entries.add(("DEAD", r, c - anchor, 0, blue >> v & 1, white >> v & 1, 0, 0))
    return frozenset(entries)


def seam_labels(plan, n):
    """Adjacent (left, right) block-type pairs, and the block types at both physical ends."""
    owner = [None] * n
    for i, block in enumerate(plan.blocks):
        for c in range(block.start, block.start + block.width):
            owner[c] = (i, block.label)
    for c in plan.dead:
        owner[c] = (c, "DEAD")
    pairs = {(owner[c][1], owner[c + 1][1]) for c in range(n - 1) if owner[c] != owner[c + 1]}
    return pairs, owner[0][1], owner[-1][1]


def describe_window(window):
    """Human-readable summary: blocks meeting the window, as column ranges relative to the opening."""
    spans = {}
    for entry in window:
        if entry[0] == "OFF":
            spans.setdefault("off-board", set()).add(entry[2])
        else:
            spans.setdefault(entry[0], set()).add(entry[2])
    parts = [f"{label}[{min(cols):+d}..{max(cols):+d}]" for label, cols in spans.items()]
    return ", ".join(sorted(parts, key=lambda p: int(p.split("[")[1].split("..")[0])))


def label_ports(package, label):
    if label == "DEAD":
        return "000", "000"
    if label == "H_c":
        return "111", "111"
    role = package.roles[label]
    return role.left_port, role.right_port


def check_seam_table(package, seams):
    """seams: (left type, right type) -> first width where they are adjacent."""
    table = []
    for (left, right), first_width in sorted(seams.items()):
        right_port = label_ports(package, left)[1]
        left_port = label_ports(package, right)[0]
        clash = int(right_port, 2) & int(left_port, 2)
        require(clash == 0, f"seam {left}|{right}: ports {right_port} and {left_port} clash")
        table.append((left, right, right_port, left_port, first_width))
    return table


# ---------------------------------------------------------------------------
# Base widths 3, 7, 11 (stored witnesses)
# ---------------------------------------------------------------------------

def check_base_widths(package):
    spec = package.manifest["base_widths"]
    path = package_path(package.directory, spec["file"])
    raw = path.read_bytes()
    require(sha256(raw) == spec["sha256"], "base-witness file checksum mismatch")
    records = json.loads(raw)
    aliases = spec["certificate_aliases"]
    results = {}
    for n in BASE_WIDTHS:
        matching = [rec for rec in records if rec.get("n") == n]
        require(len(matching) == 1, f"missing or duplicate base record for width {n}")
        record = matching[0]
        handled = set()
        for answer in record["answers"]:
            br, bc = answer["open"]
            wr, wc = answer["reply"]
            require(all(type(x) is int for x in (br, bc, wr, wc)), "non-integer base move")
            require(br in (0, 1) and 0 <= bc <= n // 2, "base opening is not normalized")
            require((br, bc) not in handled, "duplicate base opening")
            handled.add((br, bc))
            blocks = []
            for item in answer["plan"]:
                ref = item["certificate"]
                require(ref in aliases, f"base witness uses an unbound certificate reference {ref}")
                cid = aliases[ref]
                entry = package.certificates[cid]
                require(entry["kind"] == "ordinary" and entry["width"] == item["width"],
                        f"base block {ref} has the wrong kind or width")
                if ":" in ref:
                    source_ref, suffix = ref.split(":")
                    require(suffix == "H1V0" and entry.get("derived_from") == aliases[source_ref]
                            and entry.get("transform") == "H", f"reflection suffix of {ref} not honoured")
                blocks.append(Block(cid, item["start_column"], item["width"],
                                    entry["root"][0], entry["root"][1], Fraction(0)))
            plan = Plan(f"base {n}", (br, bc), (wr, wc), blocks, [], "Blue")
            check_comparison(n, plan)
        expected = {(r, c) for r in (0, 1) for c in range(n // 2 + 1)}
        require(handled == expected, f"base width {n}: normalized openings not all answered")
        require(record["solved"] == record["total"] == len(expected) and not record["failed"],
                f"base width {n}: stored coverage metadata disagrees")
        check_reflection_coverage(n, handled)
        results[n] = len(handled)
    package.base_records = results
    return results


# ---------------------------------------------------------------------------
# The sweep: every width 1..max_width
# ---------------------------------------------------------------------------

def run_sweep(package, max_width):
    established = set()        # widths already shown to have value 0, in increasing order
    windows = {}               # (case, window) -> first (n, r, c)
    seams = {}                 # (left type, right type) -> first width where adjacent
    left_ends, right_ends = set(), set()
    stats = {"even": 0, "4k+1": 0, "base": 0, "4k+3": 0, "openings": 0, "assemblies": 0,
             "cases": {case: 0 for case in range(1, 7)}, "recursive_calls": 0,
             "z7_repeatable_at_edge": 0, "row2_case1": 0}

    def record_layout(n, plan):
        pairs, first, last = seam_labels(plan, n)
        for pair in pairs:
            seams.setdefault(pair, n)
        left_ends.add(first)
        right_ends.add(last)
        stats["assemblies"] += 1

    for n in range(1, max_width + 1):
        check_board_symmetries(n)
        if n % 2 == 0:
            rotate = reflection(ROWS, n, True, True)
            require(all(rotate[v] != v for v in range(ROWS * n)), f"half-turn of 3x{n} has a fixed cell")
            require(all(rotate[rotate[v]] == v for v in range(ROWS * n)), "half-turn is not an involution")
            stats["even"] += 1
        elif n % 4 == 1:
            plan = plan_width_4k1(package, n)
            check_comparison(n, plan)
            record_layout(n, plan)
            stats["4k+1"] += 1
        elif n in BASE_WIDTHS:
            require(package.base_records.get(n), f"base width {n} was not verified")
            stats["base"] += 1
        else:
            handled = set()
            k = (n - 3) // 4
            for r in (0, 1):
                for c in range(2 * k + 2):
                    plan = package.planner(package, n, r, c)
                    blue, white, _ = check_comparison(n, plan)
                    if plan.case == 6:
                        check_case6_structure(n, plan)
                        require(plan.recursive in established,
                                f"case 6 at n={n} recurses to width {plan.recursive}, not yet established")
                        stats["recursive_calls"] += 1
                        if plan.params["s"] == 7:
                            # The repeatable Z7 also works at the physical edge.
                            alt = Plan(6, plan.blue, plan.white,
                                       plan.blocks[:1] + [role_block(package, "Z7", plan.blocks[1].start)],
                                       plan.dead, "Blue", plan.recursive, plan.params)
                            check_comparison(n, alt)
                            stats["z7_repeatable_at_edge"] += 1
                    windows.setdefault((plan.case, local_window(n, plan, blue, white)), (n, r, c))
                    record_layout(n, plan)
                    handled.add((r, c))
                    stats["cases"][plan.case] += 1
                    stats["openings"] += 1
            require(handled == {(r, c) for r in (0, 1) for c in range(2 * k + 2)}, "normalized set mismatch")
            check_reflection_coverage(n, handled)
            # Supplementary: row-2 odd openings handled by case 1 directly, without
            # reflecting the board; this exercises the reflected (2,1), (2,3) bounds.
            for c in range(1, 2 * k + 2, 2):
                plan = plan_case1(package, n, 2, c, case="1-row2")
                blue, white, _ = check_comparison(n, plan)
                windows.setdefault((plan.case, local_window(n, plan, blue, white)), (n, 2, c))
                stats["row2_case1"] += 1
                stats["assemblies"] += 1
            stats["4k+3"] += 1
        established.add(n)
    return stats, windows, seams, left_ends, right_ends


def small_width_failures(package):
    """Where the six cases would fail if applied at n = 7 or 11 (why those bases are stored)."""
    failures = {}
    for n in (7, 11):
        k = (n - 3) // 4
        bad = []
        for r in (0, 1):
            for c in range(2 * k + 2):
                try:
                    check_comparison(n, plan_width_4k3(package, n, r, c, min_k=1))
                except InvalidPackage as error:
                    bad.append(((r, c), str(error)))
        failures[n] = bad
    return failures


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def verify(directory=HERE, max_width=DEFAULT_MAX_WIDTH, package=None, verbose=True):
    started = time.perf_counter()
    require(max_width >= 15, "the sweep must reach the first induction width 15")
    if package is None:
        package = load_package(directory)
    odd_cells = check_opened_e4_roles(package)
    base = check_base_widths(package)
    stats, windows, seams, left_ends, right_ends = run_sweep(package, max_width)
    observed = {case: {describe_window(w) for cs, w in windows if cs == case} for case in EXPECTED_WINDOWS}
    require(observed == EXPECTED_WINDOWS and len(windows) == sum(map(len, EXPECTED_WINDOWS.values())),
            f"local windows {observed} differ from the analysed set {EXPECTED_WINDOWS}")
    per_case = {case: len(descriptions) for case, descriptions in observed.items()}
    seam_table = check_seam_table(package, seams)
    require(right_ends <= {"C3", "E4bar", "J5", "Z7_end", "F1"}, f"unexpected right-end blocks {right_ends}")
    require(left_ends <= {"E4", "K_corner", "K_outer2", "K_outer4", "T_middle1", "H_c", "F1"}
            | {f"E4_open_{r}_{c}" for r, c in ODD_E4_CELLS}, f"unexpected left-end blocks {left_ends}")
    ordinary = [cid for cid, e in package.certificates.items() if e["kind"] == "ordinary"]
    numeric = [cid for cid, e in package.certificates.items() if e["kind"] == "numeric"]
    summary = {
        "result": "VERIFIED: every finite input and assembly of empty_3xn_theorem.md",
        "ordinary_certificates": len(ordinary),
        "ordinary_checkpoints": sum(package.counts[c][0] for c in ordinary),
        "ordinary_edges": sum(package.counts[c][1] for c in ordinary),
        "numeric_certificates": len(numeric),
        "numeric_checkpoints": sum(package.counts[c][0] for c in numeric),
        "numeric_edges": sum(package.counts[c][1] for c in numeric),
        "derived_by_reflection": sorted(c for c, e in package.certificates.items() if "derived_from" in e),
        "roles_bound": len(package.roles),
        "odd_E4_openings_bound_le_minus_1": odd_cells,
        "base_widths_representatives": base,
        "max_width": max_width,
        "widths": {"even": stats["even"], "4k+1": stats["4k+1"], "base": stats["base"],
                   "4k+3_induction": stats["4k+3"]},
        "normalized_openings_checked": stats["openings"],
        "openings_per_case": stats["cases"],
        "supplementary_row2_case1_assemblies": stats["row2_case1"],
        "assemblies_checked": stats["assemblies"],
        "case6_recursive_calls": stats["recursive_calls"],
        "local_windows_per_case": per_case,
        "seam_types": len(seam_table),
        "z7_repeatable_also_checked_at_physical_edge": stats["z7_repeatable_at_edge"],
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }
    if verbose:
        print_report(package, summary, windows, seam_table, left_ends, right_ends)
    return summary


def print_report(package, summary, windows, seam_table, left_ends, right_ends):
    print("Certificates replayed (search-free):")
    for cid, entry in sorted(package.certificates.items()):
        nodes, edges = package.counts[cid]
        origin = f"{entry['transform']}-reflection of {entry['derived_from']}" if "derived_from" in entry else "file"
        print(f"  {cid:36s} {entry['kind']:8s} 3x{entry['width']} root={entry['root']} "
              f"{nodes} checkpoints, {edges} edges ({origin})")
    print("Roles:")
    for name, role in package.roles.items():
        extra = f" opening={role.opening}" if role.opening else ""
        print(f"  {name:12s} 3x{role.width} A={role.blue} B={role.white} ports {role.left_port}/{role.right_port} "
              f"bound<={role.bound} via {role.certificate}{extra}")
    print("Seam table (right port of left block & left port of right block = 0; first width where adjacent):")
    for left, right, rp, lp, first_width in seam_table:
        print(f"  {left:>12s} | {right:<12s} {rp} & {lp}   n={first_width}")
    print(f"Left-end blocks: {sorted(left_ends)}; right-end blocks: {sorted(right_ends)}")
    print("Local windows (columns relative to the opening; first width/opening where seen):")
    for (case, window), where in sorted(windows.items(), key=lambda item: (str(item[0][0]), item[1])):
        print(f"  case {case}: n={where[0]} opening=({where[1]},{where[2]}): {describe_window(window)}")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-width", type=int, default=DEFAULT_MAX_WIDTH)
    parser.add_argument("--directory", type=Path, default=HERE)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--small-width-diagnostics", action="store_true",
                        help="also report where the six cases would fail at n = 7 and 11")
    args = parser.parse_args()
    try:
        summary = verify(args.directory, args.max_width, verbose=not args.quiet)
        if args.small_width_diagnostics:
            package = load_package(args.directory)
            for n, bad in small_width_failures(package).items():
                print(f"six-case scheme at n={n}: {len(bad)} normalized openings fail -> {bad}")
    except (InvalidPackage, KeyError, TypeError, ValueError, OSError) as error:
        raise SystemExit(f"INVALID PACKAGE: {error}")
    if args.quiet:
        print(summary["result"])


if __name__ == "__main__":
    main()
