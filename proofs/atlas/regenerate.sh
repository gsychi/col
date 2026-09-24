#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
c++ -O3 -std=c++17 src/frontier_certificates.cpp -o frontier_certificates
c++ -O3 -std=c++17 src/number_scan.cpp -o number_scan
python3 - <<'PY'
import json,subprocess
from pathlib import Path
root=Path.cwd()
for p in sorted((root/'data').glob('full*x*_frontier.json')):
 d=json.loads(p.read_text());h,w=d['height'],d['width'];masks=d['minimal_safe_white_masks']+d['maximal_unsafe_white_masks']
 text=''.join(str(b)+'\n' for b in masks)
 subprocess.run([str(root/'frontier_certificates'),str(h),str(w),str(root/'certificates'/f'{h}x{w}')],input=text,text=True,check=True)
PY
REGENERATE=1 python3 build_numeric.py
python3 verify.py
python3 verify_numeric.py
python3 test_corruption.py
python3 build_atlas.py
python3 test_constructions.py
python3 verify_index.py
