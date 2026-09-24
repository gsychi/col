"""Checked atlas import and complete local classifications (no minimax).

The fields called blue/white in the source index mean source first/responder.
Numeric certificates are deliberately outside this grid-only importer.
"""
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import time

from col.certificate_types import (Actor, BoundKind, ConstructionRejected,
                                   Unknown, matched_bound)
from col.tiling import Library, check_tile, integer, mask, neighbors, require


def read_json(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def checked_path(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), 'atlas path escapes fixture')
    return path


def check_hashes(root):
    count = 0
    for line in (root / 'SHA256SUMS').read_text().splitlines():
        digest, relative = line.split(maxsplit=1)
        path = checked_path(root, relative)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                'atlas hash mismatch: ' + relative)
        count += 1
    return count


def ports(h, w, b):
    return dict(west=sum(((b >> (r*w)) & 1) << r for r in range(h)),
                east=sum(((b >> (r*w+w-1)) & 1) << r for r in range(h)),
                north=b & ((1 << w)-1), south=(b >> (w*(h-1))) & ((1 << w)-1))


@dataclass(frozen=True)
class Source:
    relative: str
    sha256: str
    classification_first: Actor
    doc: dict


@dataclass(frozen=True)
class Checkpoint:
    height: int
    width: int
    first: int
    responder: int
    source: str
    node_index: int
    kind: BoundKind


@dataclass(frozen=True)
class LocalBound:
    height: int
    width: int
    first: int
    responder: int
    kind: BoundKind
    source: str
    # Geometry only; this never swaps source first/responder roles.
    transpose: bool = False


@dataclass(frozen=True)
class UnsafeWitness:
    """First has a winning move in THIS local full-first game only.

    The referenced DAG has the opposite role orientation after that move.
    Inclusion embeds it into the actual local child; it does not refute a
    larger board obtained by relaxing that board's first-player permissions.
    """
    rejection: ConstructionRejected
    containing_responder: int
    first_move: int
    source: str
    transpose: bool = False


def transpose_mask(value, h, w):
    return sum(1 << ((v % w)*h + v//w) for v in range(h*w) if value >> v & 1)


def transpose_doc(doc):
    h, w = doc['height'], doc['width']
    nodes = []
    for a, b, replies in doc['nodes']:
        moves = [v for v in range(h*w) if a >> v & 1]
        pairs = sorted(((v % w)*h + v//w, (r % w)*h + r//w)
                       for v, r in zip(moves, replies))
        nodes.append([transpose_mask(a, h, w), transpose_mask(b, h, w),
                      [r for _, r in pairs]])
    result = dict(height=w, width=h, root=[transpose_mask(x, h, w) for x in doc['root']], nodes=nodes)
    check_tile(result)
    return result


class Atlas:
    """Construction data becomes usable only after DAG and lattice checks."""
    def __init__(self, root, review=None):
        started = time.perf_counter()
        self.root = Path(root).resolve()
        hashes = check_hashes(self.root)
        meta = read_json(self.root / 'atlas.json')
        require(meta['version'] == 1, 'unsupported atlas version')
        self.sources = {}; self.shapes = {}; self.checkpoints = []; self.zero_upgrades = []
        states = edges = masks = 0
        for path in sorted((self.root / 'data').glob('full*x*_frontier.json')):
            data = read_json(path); h, w = data['height'], data['width']
            require(integer(h, 1) and integer(w, 1) and h*w <= 21, 'atlas shape exceeds tile limit')
            full = (1 << (h*w))-1
            require(data['blue'] == full, 'classification requires full first permissions')
            manifest = read_json(self.root / 'certificates' / f'{h}x{w}' / 'manifest.json')
            require((manifest['height'], manifest['width']) == (h, w), 'manifest shape mismatch')
            safe = {}; unsafe = {}; nb = [mask(s) for s in neighbors(h, w)]
            for row in manifest['records']:
                b, v = row['white'], row['blue_winning_move']
                require(integer(b) and b <= full and type(row['blue_first_loses']) is bool, 'invalid classification')
                loses = row['blue_first_loses']
                if loses:
                    require(v == -1, 'safe root has a winning move')
                    expected = [full, b]; target = safe; actor = Actor.BLUE
                else:
                    require(integer(v) and v < h*w, 'invalid unsafe opening')
                    expected = [b & ~(1 << v), full & ~((1 << v) | nb[v])]
                    target = unsafe; actor = Actor.WHITE
                require(b not in target, 'duplicate frontier root')
                rel = f'certificates/{h}x{w}/' + row['file']
                source_path = checked_path(self.root, rel)
                if not source_path.exists():
                    source_path = source_path.with_suffix('.json.gz')
                    rel = str(source_path.relative_to(self.root))
                doc = read_json(source_path)
                require((doc['height'], doc['width'], doc['root']) == (h, w, expected), 'source root/role mismatch')
                edges += check_tile(doc); states += len(doc['nodes'])
                require(rel not in self.sources, 'duplicate source')
                self.sources[rel] = Source(rel, hashlib.sha256(source_path.read_bytes()).hexdigest(), actor, doc)
                target[b] = (rel, v)
            self._check_lattice(full, safe, unsafe, data)
            self.shapes[h, w] = (safe, unsafe)
            masks += full+1
        require(dict(shapes=len(self.shapes), classified_masks=masks,
                     safe_masks=sum(len(read_json(p)['safe_white_masks']) for p in (self.root/'data').glob('full*x*_frontier.json')),
                     minimal_safe=sum(len(s[0]) for s in self.shapes.values()),
                     certificates=len(self.sources), checkpoints=states, response_edges=edges) == meta['summary'],
                'atlas summary mismatch')
        for tile in meta['primitive_zero_tiles']:
            source = self.sources[tile['certificate']]; doc = source.doc
            require((tile['height'], tile['width'], [tile['blue'], tile['white']]) ==
                    (doc['height'], doc['width'], doc['root']), 'primitive reference mismatch')
            require(tile['value_kind'] == 'exact_number' and tile['value'] == [0, 1] and
                    tile['blue'] == (1 << (doc['height']*doc['width']))-1, 'invalid exact-zero primitive')
            require(tile['white_ports'] == ports(doc['height'], doc['width'], tile['white']), 'primitive ports mismatch')
        seen = set()
        with gzip.open(checked_path(self.root, meta['partial_tile_file']), 'rt') as stream:
            for line in stream:
                x = json.loads(line); source = self.sources[x['certificate']]; doc = source.doc
                i = x['node_index']; require(integer(i) and i < len(doc['nodes']), 'invalid checkpoint index')
                a, b, _ = doc['nodes'][i]; key = (x['height'], x['width'], x['blue'], x['white'])
                require(key == (doc['height'], doc['width'], a, b) and key not in seen, 'checkpoint reference/duplicate')
                require(x['value_kind'] == 'upper_bound' and x['bound'] == [0, 1], 'checkpoint is not an upper bound')
                require(x['white_ports'] == ports(*key[:2], b), 'checkpoint ports mismatch')
                seen.add(key)
                self.checkpoints.append(Checkpoint(*key, source.relative, i, matched_bound(a, b)))
        require(len(seen) == meta['partial_tile_upper_bound_count'], 'checkpoint count mismatch')
        zeros = {(x.source, x.node_index): x for x in self.checkpoints if x.kind == BoundKind.EXACT_ZERO}
        if review is not None:
            review = Path(review).resolve(); check_hashes(review); exported = set()
            with gzip.open(review/'zero_upgrades.jsonl.gz', 'rt') as stream:
                for line in stream:
                    x = json.loads(line); key = (x['certificate'], x['node_index'])
                    require(key in zeros and key not in exported, 'invalid/duplicate zero upgrade')
                    cp = zeros[key]; source = self.sources[cp.source]
                    require((x['height'], x['width'], x['blue'], x['white']) ==
                            (cp.height, cp.width, cp.first, cp.responder), 'zero-upgrade masks mismatch')
                    require(x['certificate_sha256'] == source.sha256 and x['value_kind'] == 'exact_number' and x['value'] == [0, 1],
                            'zero-upgrade provenance/value mismatch')
                    require(x['roles'] == 'positive=source first actor; negative=source responder' and
                            x['rule'] == 'certified_nonpositive_plus_white_subset_blue', 'zero-upgrade role/rule mismatch')
                    exported.add(key)
            require(exported == set(zeros), 'incomplete zero upgrades')
        self.zero_upgrades = list(zeros.values())
        self.metrics = dict(queries=0, safe_hits=0, construction_rejections=0, unknown=0, unsafe_witness_scans=0)
        self.verification = dict(**meta['summary'], partial_checkpoints=len(seen),
                                 exact_zero_upgrades=len(zeros), hashed_files=hashes,
                                 seconds=time.perf_counter()-started)

    @staticmethod
    def _check_lattice(full, safe, unsafe, data):
        require(set(safe) == set(data['minimal_safe_white_masks']) and
                set(unsafe) == set(data['maximal_unsafe_white_masks']), 'frontier disagreement')
        cover = bytearray(full+1)
        for b in safe:
            rest = full ^ b; sub = rest
            while True:
                require(cover[b | sub] != 2, 'conflicting classification')
                cover[b | sub] = 1
                if not sub: break
                sub = (sub-1) & rest
        for b in unsafe:
            sub = b
            while True:
                require(cover[sub] != 1, 'conflicting classification')
                cover[sub] = 2
                if not sub: break
                sub = (sub-1) & b
        require(0 not in cover, 'incomplete classification')
        require({i for i, v in enumerate(cover) if v == 1} == set(data['safe_white_masks']), 'safe masks disagreement')
        require(all(not any(c != b and c & b == c for c in safe) for b in safe), 'nonminimal safe frontier')
        require(all(not any(c != b and c | b == c for c in unsafe) for b in unsafe), 'nonmaximal unsafe frontier')

    def _orientation(self, h, w, a, b):
        if (h, w) in self.shapes: return h, w, a, b, False
        if (w, h) in self.shapes:
            return w, h, transpose_mask(a, h, w), transpose_mask(b, h, w), True
        return None

    def classify(self, h, w, first, responder):
        require(integer(h, 1) and integer(w, 1) and integer(first) and integer(responder) and
                (first | responder) < 1 << (h*w), 'invalid local masks')
        self.metrics['queries'] += 1
        oriented = self._orientation(h, w, first, responder)
        if oriented is not None:
            hh, ww, a, b, transposed = oriented; safe, _ = self.shapes[hh, ww]
            for support, (source, _) in safe.items():
                if not support & ~b:
                    self.metrics['safe_hits'] += 1
                    return LocalBound(h, w, first, responder, matched_bound(first, responder), source, transposed)
            if a == (1 << (h*w))-1:
                self.metrics['construction_rejections'] += 1
                return ConstructionRejected(h, w, first, responder)
        self.metrics['unknown'] += 1
        return Unknown('no safe inclusion; unsafe classification requires a full first mask')

    def unsafe_witness(self, rejection):
        require(isinstance(rejection, ConstructionRejected), 'not a local rejection')
        h, w, first, responder = rejection.height, rejection.width, rejection.first, rejection.responder
        require(first == (1 << (h*w))-1, 'unsafe inference on damaged first mask')
        oriented = self._orientation(h, w, first, responder)
        require(oriented is not None, 'unclassified shape')
        hh, ww, _, b, transposed = oriented
        self.metrics['unsafe_witness_scans'] += 1
        for support, (source, v) in self.shapes[hh, ww][1].items():
            if not b & ~support:
                if transposed: v = (v % ww)*hh + v//ww
                return UnsafeWitness(rejection, transpose_mask(support, hh, ww) if transposed else support,
                                     v, source, transposed)
        raise ValueError('no containing unsafe witness')

    def bound_doc(self, bound):
        require(isinstance(bound, LocalBound), 'construction rejection is not a safe tile')
        doc = self.sources[bound.source].doc
        return transpose_doc(doc) if bound.transpose else doc

    def library(self, height, base=None):
        entries = list(base.tiles.values()) if base else []
        for rel, source in self.sources.items():
            h, w = source.doc['height'], source.doc['width']
            if h != height and w != height: continue
            transpose = h != height
            doc = transpose_doc(source.doc) if transpose else source.doc
            raw = gzip.compress(json.dumps(doc, separators=(',', ':')).encode(), mtime=0)
            entries.append(dict(id='atlas/'+rel+('.transpose' if transpose else ''),
                source_sha256=hashlib.sha256(raw).hexdigest(), doc=doc,
                provenance=dict(format='col-atlas-source-v1', certificate=rel, source_sha256=source.sha256,
                    source_first_at_classification=int(source.classification_first),
                    mask_roles=['source_first', 'source_responder'], transpose=transpose)))
        return Library(entries)
