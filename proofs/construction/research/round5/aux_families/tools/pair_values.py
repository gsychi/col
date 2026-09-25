#!/usr/bin/env python3
"""DISCOVERY: exact values of two-ended five-row strips (P,Q)_n for all
ordered letter pairs, via the colval evaluator.  Output JSON is data for
choosing targets and constructions; it proves nothing."""
import json
import sys
import time

from strips import Evaluator, fmt_value, strip

letters = sys.argv[1] if len(sys.argv) > 1 else 'ODUVXRJuvrjT'
wmax = int(sys.argv[2]) if len(sys.argv) > 2 else 6
out = sys.argv[3] if len(sys.argv) > 3 else '/tmp/aux_families/pair_values.json'

ev = Evaluator(24)
res = {}
try:
    res = json.load(open(out))
except Exception:
    pass
for n in range(1, wmax + 1):
    t = time.time()
    for P in letters:
        for Q in letters:
            key = f'{P}{Q}_{n}'
            if key in res:
                continue
            res[key] = fmt_value(ev.value(strip(P, Q, n)))
    json.dump(res, open(out, 'w'), indent=0, sort_keys=True)
    print('width', n, 'done', round(time.time() - t, 1), 's', flush=True)
ev.close()
