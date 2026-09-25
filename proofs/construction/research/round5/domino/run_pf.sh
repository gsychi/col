#!/bin/bash
cd /tmp/domino
for f in pf5x7 pf5x9 pf7x7; do
  L=60; [ $f != pf5x7 ] && L=150
  while read -r line; do
    [ -e /workspace/proofs/construction/research/round5/STOP ] && exit 0
    echo "$line" | ./colout5 -j 1 -t 22 -T 22 -L $L >> $f.out 2>> $f.err
  done < $f.txt
done
echo DONE >> pf7x7.out
