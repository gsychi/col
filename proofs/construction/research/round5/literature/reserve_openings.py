"""Private-reserve reduction on empty-board openings (GENERAL_IDEAS.md).

After Blue opens at v, every neighbour u of v is White-only, so Lemma 4(4)
gives K <= K^{R,u} - 1.  For each opening v (up to symmetry) this prints
K and every K^{R,u}, and whether the bound is tight for some u.
Run:  python3 reserve_openings.py H W [/path/to/col_fastval]
"""

import subprocess
import sys

H, W = int(sys.argv[1]), int(sys.argv[2])
BIN = sys.argv[3] if len(sys.argv) > 3 else "/tmp/literature/col_fastval"
N = H * W


def nbrs(v):
    r, c = divmod(v, W)
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < H and 0 <= cc < W:
            yield rr * W + cc


def perms(blue, white):
    a = b = 0
    for v in range(N):
        if v in blue or v in white:
            continue
        ns = set(nbrs(v))
        if not ns & blue:
            a |= 1 << v
        if not ns & white:
            b |= 1 << v
    return a, b


def value(blue, white):
    a, b = perms(set(blue), set(white))
    out = subprocess.run([BIN, "value", str(H), str(W), str(a), str(b)],
                         capture_output=True, text=True, check=True, timeout=1500).stdout
    return out.strip().split(" = ")[-1]


def main():
    for r in range((H + 1) // 2):
        for c in range((W + 1) // 2):
            v = r * W + c
            k = value([v], [])
            kids = {f"({u // W},{u % W})": value([v], [u]) for u in nbrs(v)}
            print(f"opening ({r},{c}) = {k}; after White at neighbour: {kids}", flush=True)


if __name__ == "__main__":
    main()
