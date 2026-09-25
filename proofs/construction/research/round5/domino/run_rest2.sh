#!/bin/bash
cd /tmp/domino
while read -r line; do
  [ -e /workspace/proofs/construction/research/round5/STOP ] && exit 0
  echo "$line" | ./colout5 -j 1 -t 22 -T 22 -L 400 >> d5x9_rest2.out 2>> d5x9_rest2.err
done < q5x9_rest2.txt
echo DONE >> d5x9_rest2.out
