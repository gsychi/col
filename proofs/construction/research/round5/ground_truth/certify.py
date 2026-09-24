#!/usr/bin/env python3
"""Generate and check a pair of COLCERT5 certificates for an exact value G = x
(or G = x + * with --star): Blue moving first loses in G - x (+*), and White
moving first loses in G - x (+*). Together: G - x (+*) = 0.

Root masks are built by verify_cert.family_masks (letter patterns, written
independently of families.py). Generation uses colcert5 (search-based);
checking uses checkcert (search-free). Results are appended to
certificates/manifest.json.

Usage: certify.py FAMILY WIDTH X [--star] [-K 12] [--only blue|white] [-T 22]
"""
import argparse
import json
import subprocess
import time
from fractions import Fraction as F
from pathlib import Path

import verify_cert

HERE = Path(__file__).resolve().parent
CERTS = HERE / "certificates"
GEN = "/tmp/ground_truth/colcert5"
CHK = "/tmp/ground_truth/checkcert"

ap = argparse.ArgumentParser()
ap.add_argument("family")
ap.add_argument("width", type=int)
ap.add_argument("x")
ap.add_argument("--star", action="store_true")
ap.add_argument("-K", type=int, default=12)
ap.add_argument("-T", type=int, default=22)
ap.add_argument("--only", default="")
ap.add_argument("--outdir", default="/tmp/ground_truth/certs")
a = ap.parse_args()

x = F(a.x)
A, B = verify_cert.family_masks(a.family, a.width)
Path(a.outdir).mkdir(parents=True, exist_ok=True)
CERTS.mkdir(exist_ok=True)
man_path = CERTS / "manifest.json"
manifest = json.loads(man_path.read_text()) if man_path.exists() else {"certificates": []}
s = 1 if a.star else 0
ok_all = True
for player in ("blue", "white"):
    if a.only and player != a.only:
        continue
    # mover's frame: Blue first in G - x: (A, B, -x); White first: (B, A, +x)
    mover, other, q = (A, B, -x) if player == "blue" else (B, A, x)
    out = Path(a.outdir) / f"{a.family}_{a.width}_{player}_{str(x).replace('/', 'o')}{'s' if s else ''}.bin"
    t0 = time.time()
    g = subprocess.run([GEN, "5", str(a.width), str(mover), str(other), str(q), str(s), str(out), "-S", str(a.K),
                        "-t", "21", "-T", str(a.T)], capture_output=True, text=True)
    tg = time.time() - t0
    if g.returncode != 0:
        print(player, "GENERATION FAILED", g.stderr[-500:])
        ok_all = False
        continue
    t0 = time.time()
    c = subprocess.run([CHK, str(out), "5", str(a.width), str(mover), str(other), str(q.numerator),
                        str(q.denominator), str(s)], capture_output=True, text=True)
    tc = time.time() - t0
    verified = c.returncode == 0 and c.stdout.startswith("VERIFIED")
    ok_all &= verified
    rec = dict(family=a.family, width=a.width, player=player, q=str(x), star=s, K=a.K, file=str(out),
               bytes=out.stat().st_size, generator=g.stdout.strip(), checker=c.stdout.strip(),
               verified=verified, gen_seconds=round(tg, 1), check_seconds=round(tc, 1),
               statement=f"{player.capitalize()} moving first loses in {a.family}_{a.width} - ({x})" + (" + *" if s else ""))
    manifest["certificates"] = [m for m in manifest["certificates"]
                                if not (m["family"] == a.family and m["width"] == a.width and m["player"] == player
                                        and m["q"] == str(x) and m["star"] == s)] + [rec]
    man_path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(player, "VERIFIED" if verified else "NOT VERIFIED", g.stdout.strip(), "|", c.stdout.strip(),
          f"gen {tg:.1f}s check {tc:.1f}s")
print("PAIR VERIFIED" if ok_all else "PAIR NOT VERIFIED")
