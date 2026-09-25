import sys
from pathlib import Path

sys.path.insert(0, "/Users/gsychi/Documents/col/proofs/atlas")
from verify import verify_strategy

H = 3
TILES = {
    "E4": (4, 4095, 2023),
    "E4bar": (4, 4095, 3710),
    "J5": (5, 32767, 21845),
    "T_middle1": (6, 253500, 130844),
    "Z7": (7, 2097022, 2088828),
    "Z7_end": (7, 2097022, 2097020),
}


def nbrs(r, c, w):
    for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if 0 <= rr < H and 0 <= cc < w:
            yield rr, cc


def actual(n, blue, white):
    A = {(r, c) for r in range(H) for c in range(n)}
    B = set(A)
    A -= {blue, white, *nbrs(*blue, n)}
    B -= {blue, white, *nbrs(*white, n)}
    return A, B


def embed(name, col0):
    w, a, b = TILES[name]
    cells = lambda m: {(v // w, col0 + v % w) for v in range(H * w) if m >> v & 1}
    return cells(a), cells(b), set((r, col0 + c) for r in range(H) for c in range(w))


def check_assembly(n, blue, white, blocks):
    A, B = actual(n, blue, white)
    As, Bs, owner = set(), set(), {}
    for i, (name, col0) in enumerate(blocks):
        if name == "EMPTY":
            w = col0[1]
            region = {(r, c) for r in range(H) for c in range(col0[0], col0[0] + w)}
            a, b = set(region), set(region)
        else:
            a, b, region = embed(name, col0)
        for cell in region:
            assert cell not in owner, ("overlap", n, blue, cell)
            owner[cell] = i
        As |= a
        Bs |= b
    assert all(0 <= c < n for _, c in owner), ("out of board", n, blue)
    assert A <= As, ("Blue move lost", n, blue, sorted(A - As))
    assert Bs <= B, ("White given extra move", n, blue, sorted(Bs - B))
    for (r, c) in Bs:
        for nb in nbrs(r, c, n):
            if nb in Bs and owner.get(nb) != owner.get((r, c)):
                raise AssertionError(("White-White seam", n, blue, (r, c), nb))


def main():
    here = Path("/tmp/colcheck")
    for name, file, w in (("T_middle1", "tmiddle1.json", 6), ("Z7", "z7.json", 7), ("Z7_end", "z7old.json", 7)):
        _, a, b = TILES[name]
        cp, edges = verify_strategy(here / file, H, w, (a, b))
        print(f"{name}: verified Blue-first loss, {cp} checkpoints, {edges} edges")

    checked5 = checked6 = 0
    for n in range(15, 200, 4):
        k = (n - 3) // 4
        for c in range(0, 2 * k + 2):
            if c % 4 == 1:
                a = (c - 1) // 4
                b = k - a - 2
                assert b >= 0, (n, c)
                blocks = [("E4", 4 * i) for i in range(a)]
                blocks.append(("T_middle1", 4 * a))
                blocks += [("E4", 4 * a + 6 + 4 * i) for i in range(b)]
                blocks.append(("J5", 4 * a + 6 + 4 * b))
                check_assembly(n, (1, c), (0, c - 1), blocks)
                checked5 += 1
            if c % 4 == 3:
                s = n - c - 1
                assert s >= 7 and s % 4 == 3, (n, c)
                blocks = [("EMPTY", (0, c))]
                blocks.append(("Z7_end" if s == 7 else "Z7", c + 1))
                blocks += [("E4bar", c + 8 + 4 * i) for i in range((s - 7) // 4)]
                check_assembly(n, (1, c), (0, c + 1), blocks)
                checked6 += 1
    print(f"case 5 assemblies OK: {checked5}; case 6 assemblies OK: {checked6} (widths 15..199)")


main()
