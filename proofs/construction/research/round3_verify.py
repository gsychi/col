#!/usr/bin/env python3
"""Check third-continuation artifacts without running their discovery searches."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CHECKERS=[
    'round3_dx_check.py',
    'round3_wf_check.py',
    'round3_corner_check.py',
    'round3_central_check.py',
    'round3_independent_support_check.py',
]


def main():
    checks=[]
    for name in CHECKERS:
        relative=(HERE/name).relative_to(ROOT).as_posix()
        result=subprocess.run([sys.executable,relative],cwd=ROOT,
                              capture_output=True,text=True,check=False)
        checks.append(dict(command=['python3',relative],returncode=result.returncode,
                           stdout=result.stdout,stderr=result.stderr))
        print(f'{name}: {"PASS" if result.returncode == 0 else "FAIL"}',flush=True)
    files={p for p in HERE.rglob('round3*') if p.is_file()}
    numeric=[]
    for name in ('round3_dx_certificates','round3_wf_certificates','round3_corner_certificates'):
        files.update(p for p in (HERE/name).rglob('*') if p.is_file())
        numeric.extend((HERE/name).glob('*.json.gz'))
    files.update(HERE/name for name in (
        'number_certificates.py','dx_verify_interface_contracts.py',
        'round2_height_twin_check.py','round2_dx_check.py',
        'round2_height_applications_check.py','round2_wf_check.py',
        'wf_white_first_check.py',
        'five_row_certificate_provenance.md',
    ))
    output=HERE/'round3_verification.json'
    files.discard(output)
    files={p for p in files if '__pycache__' not in p.parts}
    record=dict(
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        status='passed' if all(c['returncode']==0 for c in checks) else 'failed',
        scope='Independent finite certificate and game-order verification; '
              'unbounded claims additionally require the symbolic proofs. '
              'Discovery outputs are hashed for provenance, not certified.',
        numerical_dag_files=len(numeric),
        central_policy_dag_files=len(list(HERE.glob('round3_central_counter*.json.gz'))),
        checks=checks,
        sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(files)},
        inherited_mapping_status='No previously missing mapping is claimed recovered; '
                                 'see five_row_certificate_provenance.md.',
    )
    output.write_text(json.dumps(record,indent=2)+'\n')
    print(f'{len(numeric)} numerical DAGs; {record["central_policy_dag_files"]} central-policy DAGs.')
    print(output.relative_to(ROOT))
    return 0 if record['status']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
