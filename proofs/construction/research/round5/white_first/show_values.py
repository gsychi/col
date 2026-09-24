#!/usr/bin/env python3
"""Print the table of runs/values.jsonl (family x width)."""
import json
import sys
d = {}
for l in open('runs/values.jsonl'):
    r = json.loads(l)
    d[(r['family'], r['width'])] = r['value']
fams = sys.argv[1].split(',') if len(sys.argv) > 1 else sorted({f for f, w in d})
maxw = max(w for f, w in d)
print('fam  ' + ' '.join(str(w).ljust(7) for w in range(1, maxw + 1)))
for f in fams:
    print(f.ljust(5), ' '.join(d.get((f, w), '-').ljust(7) for w in range(1, maxw + 1)))
