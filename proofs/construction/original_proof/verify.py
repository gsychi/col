#!/usr/bin/env python3
"""Independent, search-free verifier for the supplied Col strategy certificates.

Python 3.10+, standard library only. Run: python3 verify.py
The verifier does not import or execute the certificate generator.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

class InvalidCertificate(ValueError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidCertificate(message)

def vertices(mask: int, size: int) -> frozenset[int]:
    require(type(mask) is int and 0 <= mask < (1 << size), "Invalid legality mask")
    return frozenset(v for v in range(size) if mask & (1 << v))

def neighborhood(h: int, w: int) -> tuple[frozenset[int], ...]:
    # Deliberately coordinate/set based, independently of the generator's bit operations.
    result = []
    for v in range(h * w):
        row, col = divmod(v, w)
        candidates = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
        result.append(frozenset(r * w + c for r, c in candidates if 0 <= r < h and 0 <= c < w))
    return tuple(result)

def masks(a: frozenset[int], b: frozenset[int]) -> tuple[int, int]:
    return sum(1 << v for v in a), sum(1 << v for v in b)

def check_tile(path: Path, expected: dict) -> dict:
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected['sha256'], f"Checksum mismatch: {path.name}")
    doc = json.loads(gzip.decompress(raw))
    h, w = doc['height'], doc['width']
    require(h == 3 and type(w) is int and 1 <= w <= 7, "Invalid tile dimensions")
    require((h, w) == (expected['height'], expected['width']), "Tile dimension mismatch")
    require(doc['root'] == expected['root'], "Tile root mismatch")
    nb = neighborhood(h, w)
    nodes = {}
    for record in doc['nodes']:
        require(isinstance(record, list) and len(record) == 3, 'Malformed checkpoint')
        a, b, replies = record
        vertices(a, h * w); vertices(b, h * w)
        require(isinstance(replies, list), 'Replies must be a list')
        key = (a, b)
        require(key not in nodes, 'Duplicate checkpoint')
        nodes[key] = replies
    require(tuple(doc['root']) in nodes, 'Missing root checkpoint')
    edges = 0
    adjacency = {}
    for (am, bm), replies in nodes.items():
        a, b = vertices(am, h * w), vertices(bm, h * w)
        blue_moves = sorted(a)
        require(len(replies) == len(blue_moves), 'Not every Blue move has one White response')
        next_states = []
        for v, response in zip(blue_moves, replies):
            require(type(response) is int, 'Non-integer response')
            # Blue plays v, then White plays the prescribed response.
            a1 = a - {v} - nb[v]
            b1 = b - {v}
            require(response in b1, f'Illegal White response {response} after Blue {v}')
            a2 = a1 - {response}
            b2 = b1 - {response} - nb[response]
            child = masks(a2, b2)
            require(child in nodes, 'Missing successor checkpoint')
            require(len(a2 | b2) <= len(a | b) - 2, 'Non-decreasing strategy edge')
            next_states.append(child)
            edges += 1
        adjacency[(am, bm)] = next_states
    seen = {tuple(doc['root'])}
    stack = list(seen)
    while stack:
        for nxt in adjacency[stack.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    require(len(seen) == len(nodes), 'Unreachable checkpoints in certificate')
    require(len(nodes) == expected['nodes'] and edges == expected['edges'], 'Metadata count mismatch')
    return {'height': h, 'width': w, 'a': vertices(doc['root'][0], h*w),
            'b': vertices(doc['root'][1], h*w), 'nodes': len(nodes), 'edges': edges}

def actual_after_opening(blue: int, white: int) -> tuple[frozenset[int], frozenset[int]]:
    require(0 <= blue < 45 and 0 <= white < 45 and blue != white, 'Invalid opening/response')
    nb = neighborhood(3, 15)
    empty = frozenset(range(45))
    a1 = empty - {blue} - nb[blue]
    b1 = empty - {blue}
    require(white in b1, 'Illegal first White response')
    return a1 - {white}, b1 - {white} - nb[white]

def check_assembly(opening: dict, tiles: dict[str, dict], actual_override=None) -> None:
    if actual_override is None:
        blue, white = opening['blue_opening'], opening['white_response']
        actual_a, actual_b = actual_after_opening(blue, white)
    else:
        actual_a, actual_b = actual_override
    virtual_a, virtual_b = set(), set()
    owner = {}
    for i, block in enumerate(opening['blocks']):
        tile = tiles[block['certificate']]
        start, w = block['start_column'], block['width']
        require(type(start) is int and 0 <= start and start+w <= 15, 'Tile outside board')
        require(tile['width'] == w, 'Inconsistent block width')
        for local in range(3*w):
            row, col = divmod(local, w)
            v = row*15 + start + col
            require(v not in owner, 'Overlapping blocks')
            owner[v] = i
            if local in tile['a']: virtual_a.add(v)
            if local in tile['b']: virtual_b.add(v)
    require(actual_a <= virtual_a, 'Relaxation deletes an actual Blue move')
    require(virtual_b <= actual_b, 'Relaxation invents an actual White move')
    # Cross-tile edges may be deleted only if they cannot constrain White.
    nb = neighborhood(3, 15)
    for u in range(45):
        for v in nb[u]:
            if owner.get(u, -1) != owner.get(v, -1):
                require(not (u in virtual_b and v in virtual_b), 'Unremoved White interaction across blocks')
    require(list(masks(frozenset(virtual_a), frozenset(virtual_b))) == opening['relaxed_masks'],
            'Incorrect reported virtual masks')

def check_demon(manifest: dict, tiles: dict) -> None:
    case=manifest['demon_case']
    require(case['blue_stones']==[0,14] and case['white_stones']==[44]
            and case['white_response']==12, 'Unexpected demon-state claim')
    nb=neighborhood(3,15)
    occupied=frozenset({0,14,44})
    a=frozenset(range(45))-occupied-nb[0]-nb[14]
    b=frozenset(range(45))-occupied-nb[44]
    response=case['white_response']
    require(response in b, 'Demon-state White response is illegal')
    check_assembly(case,tiles,(a-{response}, b-{response}-nb[response]))

def check_family_roots(manifest: dict, tiles: dict) -> None:
    """Check the finite base lemmas used in the written parametric proofs."""
    expected = {
        'A4': (4, 4076, 2038), 'E4': (4, 4095, 2023),
        'B2': (2, 60, 24), 'F1': (1, 7, 5),
    }
    for name, (w, a, b) in expected.items():
        info = tiles[manifest['family_tiles'][name]]
        require(info['width'] == w and masks(info['a'], info['b']) == (a, b),
                f'Wrong base tile for family: {name}')

def verify(directory: Path, verbose: bool = True) -> dict:
    started = time.perf_counter()
    manifest = json.loads((directory/'manifest.json').read_text())
    require(manifest['format'] == 'col-one-sided-tiles-v1', 'Unknown certificate format')
    require(manifest['board'] == {'height':3, 'width':15}, 'This checker targets 3x15')
    tiles = {}
    for item in manifest['certificates']:
        filename = item['file']
        require(filename not in tiles, 'Duplicate tile file')
        path = (directory/filename).resolve()
        require(path.is_relative_to(directory.resolve()), 'Path outside certificate directory')
        tiles[filename] = check_tile(path, item)
    reps = {row*15+col for row in (0,1) for col in range(8)}
    observed = [entry['blue_opening'] for entry in manifest['openings']]
    require(len(observed) == 16 and set(observed) == reps, 'Incomplete 16-case opening coverage')
    covered = set()
    for entry in manifest['openings']:
        check_assembly(entry, tiles)
        row, col = divmod(entry['blue_opening'], 15)
        covered |= {rr*15+cc for rr in (row,2-row) for cc in (col,14-col)}
    require(covered == set(range(45)), 'Reflections do not cover all 45 opening cells')
    check_family_roots(manifest, tiles)
    check_demon(manifest, tiles)
    result = {'result': 'VERIFIED: empty 3x15 Col is a second-player win',
              'demon_state': 'VERIFIED: White wins by playing cell 12',
              'opening_representatives': len(observed), 'opening_cells_covered': len(covered),
              'tile_certificates': len(tiles), 'largest_tile_cells': max(3*t['width'] for t in tiles.values()),
              'checkpoints':sum(t['nodes'] for t in tiles.values()),
              'blue_move_white_reply_edges':sum(t['edges'] for t in tiles.values()),
              'elapsed_seconds':time.perf_counter()-started}
    if verbose:
        print(json.dumps(result, indent=2))
    return result

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    try:
        verify(args.directory)
    except (InvalidCertificate, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f'INVALID CERTIFICATE: {error}')
