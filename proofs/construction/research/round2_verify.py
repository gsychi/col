#!/usr/bin/env python3
"""Replay the second continuation's independent checks and record provenance.

No discovery search is run. Symbolic scope is supplied by the linked proofs,
not inferred from the finite regression counts.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHECKERS = [
    'round2_dx_check.py',
    'round2_dx_verify_mirror.py',
    'round2_wf_check.py',
    'round2_height_twin_check.py',
    'round2_height_reflection_check.py',
    'round2_height_applications_check.py',
    'round2_bridge_support_check.py',
]


def main():
    checks = []
    for name in CHECKERS:
        relative = (HERE / name).relative_to(ROOT).as_posix()
        result = subprocess.run(
            [sys.executable, relative], cwd=ROOT,
            capture_output=True, text=True, check=False,
        )
        checks.append(dict(command=['python3', relative],
                           returncode=result.returncode,
                           stdout=result.stdout, stderr=result.stderr))
        print(f'{name}: {"PASS" if result.returncode == 0 else "FAIL"}', flush=True)

    # Bind local numerical and policy artifacts, current arguments, discovery
    # records, and helper definitions. Hashing discovery does not certify it.
    files = {p for p in HERE.rglob('round2*') if p.is_file()}
    for directory in ('round2_dx_certificates', 'round2_wf_certificates'):
        files.update(p for p in (HERE / directory).rglob('*') if p.is_file())
    files.update(HERE / name for name in (
        'number_certificates.py', 'dx_verify_interface_contracts.py',
        'five_row_certificate_provenance.md',
    ))
    output = HERE / 'round2_verification.json'
    files.discard(output)
    files = {p for p in files if '__pycache__' not in p.parts}
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(files)}
    numeric = list((HERE / 'round2_dx_certificates').glob('*.json.gz'))
    numeric += list((HERE / 'round2_wf_certificates').glob('*.json.gz'))
    policies = list(HERE.glob('round2_dx_mirror_*_DX_*.json.gz'))
    record = dict(
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        status='passed' if all(c['returncode'] == 0 for c in checks) else 'failed',
        scope='Independent finite certificates and geometry regressions; '
              'unbounded conclusions require the written symbolic proofs. '
              'Discovery files are hashed for provenance, not certified.',
        numerical_dag_files=len(numeric),
        mirror_policy_dag_files=len(policies),
        checks=checks,
        sha256=hashes,
        inherited_missing_mappings='See five_row_certificate_provenance.md; '
                                  'this round does not recover its missing artifacts.',
    )
    output.write_text(json.dumps(record, indent=2) + '\n')
    print(f'{len(numeric)} numerical DAGs; {len(policies)} mirror-policy DAGs.')
    print(output.relative_to(ROOT))
    return 0 if record['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
