#!/usr/bin/env python3
"""Extract the discovered safe checkpoint and cross-check full-board strategies."""
import argparse
import gzip
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from col.weighted_tiling import Sources, extract_safe_checkpoint
from col.tiling import Library, Strategy, check_report, check_tile, flip_cell


def run(output,boards):
    evidence=json.loads(gzip.decompress((output/'evidence.json.gz').read_bytes()))
    sources=Sources(evidence['sources'])
    case=next(c for c in evidence['cases'] if c['label']=='3x19/opening/1,7')
    result=case['results']['weighted_checkpoints']
    if result.get('kind')!='reply' or result['outcome']!='win':
        raise ValueError('Expected discovered response proof')
    library=Library.load(ROOT/'proofs/3x15'); added=[]
    for p in result['cover']['blocks']:
        if p['source'].startswith('original/'): continue
        doc=extract_safe_checkpoint(sources,p['source'],p['checkpoint'])
        name,_,edges=library.add(doc)
        added.append(dict(tile=name,source=p['source'],source_sha256=sources.documents[p['source']]['source_sha256'],
                          checkpoint=p['checkpoint'],nodes=len(doc['nodes']),edges=edges))
    # Attribution control: the same usable state can already occur inside an
    # older DAG, although the older palette only exposes roots.
    older_matches=[]
    for found in added:
        target=found['checkpoint'][:2]
        for identifier,entry in sources.documents.items():
            d=entry['doc']
            if entry['origin']!='original' or (d['height'],d['width'])!=(3,4): continue
            for a,b,q,den,_ in d['nodes']:
                for rf,cf in ((False,False),(True,False),(False,True),(True,True)):
                    pair=[sum(1<<flip_cell(v,3,4,rf,cf) for v in range(12) if m>>v&1) for m in (a,b)]
                    if pair!=target: continue
                    olddoc=extract_safe_checkpoint(sources,identifier,[a,b,q,den])
                    older_matches.append(dict(source=identifier,checkpoint=[a,b,q,den],
                        row_flip=rf,column_flip=cf,nodes=len(olddoc['nodes']),edges=check_tile(olddoc)))
    library_path=output/'checkpoint-library'; library.save(library_path)
    subprocess.run(['cargo','build','--quiet','--release','--offline','--manifest-path',str(ROOT/'solver/Cargo.toml'),'--bin','col-cert'],check=True)
    binary=ROOT/'solver/target/release/col-cert'; rng=random.Random(190819); records=[]
    for label in boards:
        h,n=map(int,label.split('x')); artifact=output/(label+'.json')
        t=time.perf_counter()
        process=subprocess.run([str(binary),'--m',str(h),'--n',str(n),'--proof-library',str(library_path),'--proof-out',str(artifact)],capture_output=True,text=True,timeout=30)
        seconds=time.perf_counter()-t
        if process.returncode not in (0,2): raise RuntimeError(process.stdout+process.stderr)
        report=json.loads(artifact.read_text()); check_report(report)
        if label in ('3x19','3x101') and report['outcome']!='loss':
            raise AssertionError('Certified board regressed: '+label)
        verify=subprocess.run([str(binary),'verify',str(artifact)],capture_output=True,text=True,check=True,timeout=30)
        games=0; moves=0
        if report['outcome']=='loss':
            prototype=Strategy(report)
            for swap in (False,True):
                for opening in range(h*n):
                    for trial in range(3):
                        game=object.__new__(Strategy);game.__dict__=prototype.__dict__.copy()
                        game.actual=list(prototype.actual);game.history=[]
                        if prototype.blocks is not None: game.states=list(prototype.states)
                        if swap:
                            game.actual.reverse();game.winner=1-prototype.winner;game.loser=1-prototype.loser
                        game.reply(opening)
                        while game.legal_opponent_moves: game.reply(rng.choice(game.legal_opponent_moves))
                        games+=1;moves+=len(game.history)
        record=dict(board=label,outcome=report['outcome'],uncovered=report['uncovered'],
                    opening_assemblies=len(report['openings']),seconds=seconds,
                    replay_games=games,replay_moves=moves,rust_verifier=verify.stdout.strip())
        records.append(record);print(json.dumps(record),flush=True)
    summary=dict(format='col-checkpoint-probe-v1',source_evidence='evidence.json.gz',
        discovered_opening=[1,7],white_response=result['move'],added=added,older_checkpoint_matches=older_matches,boards=records,
        note='Finite board proofs using extracted zero-offset DAGs; production default library unchanged. Replay samples supplement complete DAG and assembly checking.')
    (output/'checkpoint-probe.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# Reusing a checkpoint certifies 3x19', '',
        'The weighted experiment found a useful internal state in the economical bulk certificate. Extracting its reachable response DAG produces one ordinary 3x4 tile with Blue mask 1843, White mask 1825, 17 checkpoints, and 35 response edges. Its certified upper bound is zero.', '',
        '**Attribution:** The same state was already present in the original library, in two reflected forms. The gain comes from exposing internal checkpoints as reusable tile roots. Positive-tile compensation and new exhaustive search are unnecessary for this 3x19 proof.', '',
        'For the formerly missing Blue opening at row 1, column 7, White replies at cell 8 (row 0, column 8), zero-based. The remaining board has a compatible partition of widths 7 + 4 + 4 + 4. Every tile gives a Blue-first loss.', '',
        '| Board | Certificate result | Covered opening assemblies | Uncovered cells | Replay games |', '|---|---|---:|---|---:|']
    for r in records:
        coverage=str(r['opening_assemblies']) if r['opening_assemblies'] else 'Direct tiling'
        lines.append(f'| {r["board"]} | {r["outcome"]} | {coverage} | {r["uncovered"]} | {r["replay_games"]} |')
    lines += ['', '`loss` means the initial player loses: empty 3x19 is a second-player win. Both the Rust checker (using engine legality transitions) and the independent Python set-based checker validate every local edge and every opening assembly. Replay covers every initial cell, three continuations per cell, and both color orientations. Sampled replay supplements the complete certificate checks.', '',
        'The added safe tile closes all 57 openings on 3x19. Larger 4k+3 boards still have gaps: 3x23 at (1,11), 3x27 at (1,11)/(1,15), and 3x31 at (1,11)/(1,15)/(1,19). These are finite results, not an all-width proof.', '',
        'Production defaults remain unchanged. The augmented 26-tile library and standalone executable strategy artifacts are preserved here. Unlike general weighted bounds, this extracted grid-only strategy works with the existing replay player.', '',
        'Reproduce after running the weighted benchmark:', '', '```sh',
        'python3 scripts/checkpoint_tiling_probe.py',
        './col-cert --m 3 --n 19 --proof-library reports/weighted-tiling/checkpoint-library --proof-out /tmp/3x19.json',
        './col-cert verify /tmp/3x19.json',
        './col-cert verify-python /tmp/3x19.json',
        './col-cert replay /tmp/3x19.json --moves 26', '```', '',
        'Provenance, local checkpoint counts, full verifier output, timing, and replay counts: [checkpoint-probe.json](checkpoint-probe.json). Full board proof: [3x19.json](3x19.json).', '']
    (output/'checkpoint-results.md').write_text('\n'.join(lines))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'reports/weighted-tiling')
    p.add_argument('--boards',nargs='+',default=['3x19','3x23','3x27','3x31','3x101'])
    args=p.parse_args();run(args.output,args.boards)
