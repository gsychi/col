#!/usr/bin/env python3
"""Replay fourth-continuation evidence without its discovery searches."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CHECKERS = [
    'round4_dx_check.py',
    'round4_wf_check.py',
    'round4_pair_bases_check.py',
    'round4_bridge_check.py',
    'round4_star_bounds_check.py',
    'round4_graph_shortcuts_check.py',
]
PACKAGES = (
    'round4_dx_certificates', 'round4_wf_certificates',
    'round4_pair_base_certificates', 'round4_bridge_certificates',
)


def local_dependencies(paths):
    """Hash local Python imports as well as entry points, without importing."""
    seen = set(paths)
    pending = list(paths)
    while pending:
        path = pending.pop()
        if path.suffix != '.py':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                names = [node.module] if node.module else []
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            for name in names:
                dependency = HERE / (name.split('.')[0] + '.py')
                if dependency.is_file() and dependency not in seen:
                    seen.add(dependency)
                    pending.append(dependency)
    return seen


def certificate_totals():
    rows = []
    for package in PACKAGES:
        manifest = json.loads((HERE / package / 'manifest.json').read_text())
        if package == 'round4_bridge_certificates':
            entries = manifest['artifacts']
        else:
            entries = manifest
        for entry in entries:
            if 'path' in entry:
                path = HERE / entry['path']
            else:
                name = entry.get('file') or (entry['name'] + '.json.gz')
                path = HERE / package / name
            assert path.is_file()
            rows.append(dict(
                path=path.relative_to(ROOT).as_posix(),
                checkpoints=entry.get('checkpoints', entry.get('nodes')),
                edges=entry.get('edges', entry.get('response_edges')),
                reused=entry.get('reused', False),
            ))
    assert len({r['path'] for r in rows}) == len(rows)
    return rows


def main():
    checks = []
    for name in CHECKERS:
        relative = (HERE / name).relative_to(ROOT).as_posix()
        result = subprocess.run([sys.executable, relative], cwd=ROOT,
                                capture_output=True, text=True, check=False)
        checks.append(dict(command=['python3', relative], returncode=result.returncode,
                           stdout=result.stdout, stderr=result.stderr))
        print(f'{name}: {"PASS" if result.returncode == 0 else "FAIL"}', flush=True)
    rows = certificate_totals()
    counts = dict(
        replayed_dags=len(rows), new_dags=sum(not r['reused'] for r in rows),
        reused_dags=sum(r['reused'] for r in rows),
        checkpoints=sum(r['checkpoints'] for r in rows),
        response_edges=sum(r['edges'] for r in rows),
    )
    files = {p for p in HERE.glob('round4*') if p.is_file()}
    for package in PACKAGES:
        files.update(p for p in (HERE / package).rglob('*') if p.is_file())
    files.update(ROOT / r['path'] for r in rows)
    files.update((HERE / 'col_research_handoff.md', HERE.parent / 'README.md',
                  HERE / 'five_row_certificate_provenance.md'))
    files = local_dependencies(files)
    output = HERE / 'round4_verification.json'
    files.discard(output)
    record = dict(
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        status='passed' if all(c['returncode'] == 0 for c in checks) else 'failed',
        scope='Finite certificates and exact game-order checks. Unbounded claims '
              'additionally require the written symbolic arguments. Discovery '
              'outputs are hashed for provenance, not independently certified.',
        counts=counts, certificates=rows, checks=checks,
        sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(files)},
        inherited_mapping_status='No previously missing mapping is claimed recovered; '
                                 'see five_row_certificate_provenance.md.',
    )
    output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))
    print(output.relative_to(ROOT))
    return 0 if record['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
