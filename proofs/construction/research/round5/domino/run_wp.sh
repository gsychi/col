#!/bin/sh
# Replays every finite check of W_PRIME.md.  Builds into /tmp/wp, writes runs/wp_*.txt.
# Total time about 20 minutes on one core.
set -e
cd "$(dirname "$0")"
mkdir -p /tmp/wp runs
for p in wp_rule wp_cert wp_certB wp_bnd offhist; do
    g++ -O3 -march=native -std=c++17 $p.cpp -o /tmp/wp/$p
done

# Section 2: the answer rule R*, every PF-class position of 3x3 ... 3x9.
for k in 3 5 7 9; do /tmp/wp/wp_rule $k 99 99 30; done > runs/wp_rule.txt

# Section 3: cut certificates (EW via Lemma 4(2) at y').
for k in 3 5 7 9; do EWLEMMA=1 /tmp/wp/wp_cert $k 2; done > runs/wp_cert.txt

# Section 4: strip lemmas.
{
  # T: even strips, right end column Y X Y with top White-illegal, bottom Blue-illegal
  #    (bottom may hold a White stone: class W*).
  for k in 2 4 6 8; do /tmp/wp/wp_bnd 3 $k nnn wnB; done
  # K: odd strips with the middle cell of the left end column White-illegal.
  for k in 1 3 5 7; do /tmp/wp/wp_bnd 3 $k nwn nnn; done
  QZERO=1 /tmp/wp/wp_bnd 3 9 nwn nnn
  # P: odd strips with a Blue stone at the top-left corner and the bottom-left cell
  #    White-illegal (the far piece of branch EW).
  for k in 1 3 5 7; do FORCEB=0,0 /tmp/wp/wp_bnd 3 $k nnW nnn; done
  FORCEB=0,0 QZERO=1 /tmp/wp/wp_bnd 3 9 nnW nnn
  # plain strips (PF itself), for reference
  for k in 1 2 3 4 5 6 7; do /tmp/wp/wp_bnd 3 $k nnn nnn; done
} > runs/wp_lemmas.txt

# Section 5: margin histogram of value(G^{R,y}) - F.
for k in 5 7 9; do /tmp/wp/offhist 3 $k 99 99; done > runs/wp_margin.txt

# Section 6: upper half (dual certificates and upper traces).
for k in 3 5 7 9; do /tmp/wp/wp_certB $k 2; done > runs/wp_certB.txt
{
  for k in 1 3 5 7; do /tmp/wp/wp_bnd 3 $k bnW nnn; done
  QZERO=1 /tmp/wp/wp_bnd 3 9 bnW nnn
} > runs/wp_upper.txt
