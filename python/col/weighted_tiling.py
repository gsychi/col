"""Experimental numerical upper-bound tilings; never an exact CGT-value cache.

The independent supplied checker validates grid-plus-dyadic response DAGs.
Every checked checkpoint (A,B,q) proves G(A,B) <= -q. Geometric assembly and
exact addition are checked separately. Production DFS and gameplay are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import time

from col.tiling import Library, InvalidCertificate, require, integer, neighbors, mask, flip_cell, check_tile

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / 'proofs/construction/research/number_certificates.py'
_spec = importlib.util.spec_from_file_location('col_supplied_number_checker', CHECKER)
_checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_checker)


def fraction(pair):
    require(isinstance(pair, (list, tuple)) and len(pair) == 2, 'invalid fraction')
    num, den = pair
    require(type(num) is int, 'invalid numerator')
    require(integer(den, 1) and not den & (den-1), 'denominator is not dyadic')
    return Fraction(num, den)


def encoded(q):
    return [q.numerator, q.denominator]


def check_document(doc):
    require(integer(doc['height'],1) and doc['height'] <= 7 and integer(doc['width'],1), 'invalid dimensions')
    require(doc['height'] * doc['width'] <= 30, 'experimental certificate exceeds 30 cells')
    fraction(doc['root'][2:])
    for row in doc['nodes']:
        fraction(row[2:4])
        require(all(type(v) is int and type(r) is int for v,r in row[4]), 'invalid move ID')
    return _checker.verify(doc)


class Sources:
    def __init__(self, documents):
        self.documents = documents
        self.nodes = {}
        for identifier, entry in documents.items():
            doc = entry['doc']
            check_document(doc)
            self.nodes[identifier] = {(a,b,Fraction(q,d)) for a,b,q,d,_ in doc['nodes']}

    @classmethod
    def load(cls):
        library = Library.load(ROOT / 'proofs/3x15')
        docs = {}
        for tile in library.tiles.values():
            d = tile['doc']
            rows = []
            for a,b,replies in d['nodes']:
                moves = [v for v in range(d['height']*d['width']) if a >> v & 1]
                rows.append([a,b,0,1,list(map(list,zip(moves,replies)))])
            doc = dict(height=d['height'],width=d['width'],root=[*d['root'],0,1],
                       nodes=rows,edges=sum(len(row[4]) for row in rows))
            docs['original/'+tile['id']] = dict(doc=doc,source_sha256=tile['source_sha256'],origin='original')
        base = ROOT / 'proofs/construction/research/new_certificates'
        for path in sorted(base.glob('*.json.gz')):
            raw = path.read_bytes()
            docs['signed/'+path.name] = dict(doc=json.loads(gzip.decompress(raw)),
                source_sha256=hashlib.sha256(raw).hexdigest(),origin='signed')
        return cls(docs)

    def add(self, doc):
        check_document(doc)
        raw = json.dumps(doc,separators=(',',':')).encode()
        digest = hashlib.sha256(raw).hexdigest()
        identifier = 'generated/'+digest
        self.documents[identifier] = dict(doc=doc,source_sha256=digest,origin='generated')
        self.nodes[identifier] = {(a,b,Fraction(q,d)) for a,b,q,d,_ in doc['nodes']}
        return identifier


@dataclass(frozen=True)
class Variant:
    height: int
    width: int
    a: int
    b: int
    cost: int
    left: int
    right: int
    source: str
    checkpoint: tuple
    row_flip: bool
    column_flip: bool


class WeightedSearch:
    def __init__(self, sources, mode='weighted', checkpoints=False, original_checkpoints=False):
        require(mode in ('original','nonpositive','weighted'), 'unknown mode')
        self.sources, self.mode = sources, mode
        roots = []
        for identifier, entry in sources.documents.items():
            if mode == 'original' and entry['origin'] != 'original': continue
            d = entry['doc']
            candidates = [d['root']]
            # Separate opt-ins preserve the root-only benchmark controls while
            # allowing research probes to reuse the original DAGs as well.
            if (checkpoints and entry['origin'] != 'original') or (original_checkpoints and entry['origin'] == 'original'):
                candidates = [row[:4] for row in d['nodes']]
            for a,b,qn,qd in candidates:
                cost = -Fraction(qn,qd)
                if mode == 'nonpositive' and cost > 0: continue
                roots.append((identifier,d['height'],d['width'],a,b,cost,(a,b,qn,qd)))
        self.scale = max((r[5].denominator for r in roots),default=1)
        variants = {}
        for identifier,h,w,a,b,cost,checkpoint in roots:
            cost = int(cost * self.scale)
            for rf,cf in ((False,False),(True,False),(False,True),(True,True)):
                aa,bb = (sum(1 << flip_cell(v,h,w,rf,cf) for v in range(h*w) if m >> v & 1) for m in (a,b))
                key = h,w,aa,bb
                if key in variants and variants[key].cost <= cost: continue
                edge = lambda c: sum(1 << r for r in range(h) if bb >> (r*w+c) & 1)
                variants[key] = Variant(h,w,aa,bb,cost,edge(0),edge(w-1),identifier,checkpoint,rf,cf)
        self.variants = tuple(variants.values())
        self.by_height = {}
        for variant in self.variants:
            self.by_height.setdefault(variant.height,[]).append(variant)
        self.reset_metrics()

    def reset_metrics(self):
        self.metrics = dict(queries=0,matching_tiles=0,covers=0,query_seconds=0.0)

    def matches(self,h,n,a,b):
        result = [[] for _ in range(n)]
        widths = {v.width for v in self.by_height.get(h,())}
        for c in range(n):
            extracts = {w:Library.extract(h,n,c,w,a,b) for w in widths if c+w <= n}
            for v in self.by_height.get(h,()):
                actual = extracts.get(v.width)
                if actual is not None and not actual[0] & ~v.a and not v.b & ~actual[1]:
                    result[c].append(v)
        return result

    def frontiers(self,h,n,a,b,reverse=False):
        matches = self.matches(h,n,a,b)
        dp = [{} for _ in range(n+1)]
        dp[0][0] = (0,None)
        for c in range(n):
            if not dp[c]: continue
            if Library.extract(h,n,c,1,a,b)[0] == 0:
                p,(value,_) = min(dp[c].items(),key=lambda item:item[1][0])
                if 0 not in dp[c+1] or value < dp[c+1][0][0]: dp[c+1][0] = value,(c,p,None)
            for v in matches[c]:
                self.metrics['matching_tiles'] += 1
                for p,(value,_) in dp[c].items():
                    total = value+v.cost
                    if not p & v.left and (v.right not in dp[c+v.width] or total < dp[c+v.width][v.right][0]):
                        dp[c+v.width][v.right] = total,(c,p,v)
        suffix = None
        if reverse:
            suffix = [{} for _ in range(n+1)]; suffix[n][0] = 0
            for c in reversed(range(n)):
                if Library.extract(h,n,c,1,a,b)[0] == 0 and suffix[c+1]: suffix[c][0] = min(suffix[c+1].values())
                for v in matches[c]:
                    for p,value in suffix[c+v.width].items():
                        total = v.cost+value
                        if not v.right & p and (v.left not in suffix[c] or total < suffix[c][v.left]): suffix[c][v.left] = total
        return dp,suffix

    def bound(self,h,n,a,b):
        require(integer(h,1) and h <= 7 and integer(n,1), 'invalid board dimensions')
        require(integer(a) and integer(b) and (a|b) < 1 << (h*n), 'invalid board masks')
        started = time.perf_counter(); self.metrics['queries'] += 1
        dp,_ = self.frontiers(h,n,a,b)
        self.metrics['query_seconds'] += time.perf_counter()-started
        if not dp[n]: return None
        p,(total,_) = min(dp[n].items(),key=lambda item:item[1][0])
        c = n; placements = []
        while c:
            _,(prev,q,v) = dp[c][p]
            if v is not None:
                placements.append(dict(start_column=prev,source=v.source,checkpoint=list(v.checkpoint),
                                       row_flip=v.row_flip,column_flip=v.column_flip))
            c,p = prev,q
        self.metrics['covers'] += 1
        return dict(upper=encoded(Fraction(total,self.scale)),blocks=list(reversed(placements)))

    def query(self,h,n,a,b,turn,reply_scan=True):
        current,other = (a,b) if turn == 0 else (b,a)
        cover = self.bound(h,n,current,other)
        if cover is not None and fraction(cover['upper']) <= 0:
            return dict(outcome='loss',kind='own_upper',cover=cover)
        if self.mode != 'original':
            cover = self.bound(h,n,other,current)
            # Opponent <= 0 is insufficient for a current-player win: strictness matters.
            if cover is not None and fraction(cover['upper']) < 0:
                return dict(outcome='win',kind='opponent_negative',cover=cover)
        if reply_scan:
            nb = [mask(s) for s in neighbors(h,n)]
            for v in range(h*n):
                if current >> v & 1:
                    aa,bb = current & ~((1<<v)|nb[v]), other & ~(1<<v)
                    cover = self.bound(h,n,bb,aa)
                    if cover is not None and fraction(cover['upper']) <= 0:
                        return dict(outcome='win',kind='reply',move=v,cover=cover)
        return dict(outcome='unknown')


def check_cover(sources,h,n,a,b,cover):
    require(integer(h,1) and h <= 7 and integer(n,1), 'invalid dimensions')
    require(integer(a) and integer(b) and (a|b) < 1 << (h*n), 'invalid actual masks')
    actual_a = {v for v in range(h*n) if a >> v & 1}
    actual_b = {v for v in range(h*n) if b >> v & 1}
    va,vb,owner = set(),set(),{}
    total = Fraction(0)
    for i,placement in enumerate(cover['blocks']):
        identifier = placement['source']; d = sources.documents[identifier]['doc']
        aa,bb,qn,qd = placement['checkpoint']; q = fraction([qn,qd])
        require((aa,bb,q) in sources.nodes[identifier], 'uncertified checkpoint')
        h2,w = d['height'],d['width']; c = placement['start_column']
        rf,cf = placement['row_flip'],placement['column_flip']
        require(type(rf) is bool and type(cf) is bool, 'invalid transform')
        require(h2 == h and integer(c) and c+w <= n, 'out-of-bounds block')
        for v in range(h*w):
            rr,cc = divmod(flip_cell(v,h,w,rf,cf),w); actual = rr*n+c+cc
            require(actual not in owner, 'overlapping blocks'); owner[actual] = i
            if aa >> v & 1: va.add(actual)
            if bb >> v & 1: vb.add(actual)
        total -= q
    require(actual_a <= va, 'uncovered actual Blue move')
    require(vb <= actual_b, 'invented actual White move')
    for u,adjacent in enumerate(neighbors(h,n)):
        for v in adjacent:
            if owner.get(u) != owner.get(v): require(not(u in vb and v in vb), 'White interaction across blocks')
    require(total == fraction(cover['upper']), 'incorrect numerical sum')
    return total


def check_result(sources,h,n,a,b,turn,result):
    require(type(turn) is int and turn in (0,1), 'invalid actor')
    outcome = result['outcome']
    if outcome == 'unknown': return
    current,other = (a,b) if turn == 0 else (b,a)
    kind = result['kind']
    if kind == 'own_upper':
        require(outcome == 'loss', 'wrong bound direction')
        require(check_cover(sources,h,n,current,other,result['cover']) <= 0, 'positive loss bound')
    elif kind == 'opponent_negative':
        require(outcome == 'win', 'wrong bound direction')
        require(check_cover(sources,h,n,other,current,result['cover']) < 0, 'zero is insufficient for a win')
    elif kind == 'reply':
        v = result['move']; require(integer(v) and v < h*n and current >> v & 1, 'illegal reply')
        blocked = (1<<v)|mask(neighbors(h,n)[v])
        require(outcome == 'win' and check_cover(sources,h,n,other & ~(1<<v),current & ~blocked,result['cover']) <= 0, 'reply not certified')
    else:
        raise InvalidCertificate('unknown proof form')


def plain_outcome(h,n,a,b,turn):
    nb = [mask(s) for s in neighbors(h,n)]
    @lru_cache(None)
    def win(current,other):
        for v in range(h*n):
            if current >> v & 1 and not win(other & ~(1<<v),current & ~((1<<v)|nb[v])): return True
        return False
    return win(a,b) if turn == 0 else win(b,a)


def generate_bound(h,w,a,b,upper,state_limit=100000,seconds=0.5):
    """Bounded minimax on G-upper, with an independently checkable response DAG."""
    require(integer(h,1) and h <= 7 and integer(w,1) and h*w <= 21, 'discovery tile exceeds 21 cells')
    require(integer(a) and integer(b) and (a|b) < 1 << (h*w), 'invalid masks')
    require(integer(state_limit,1) and math.isfinite(seconds) and seconds > 0, 'invalid budget')
    upper = fraction(encoded(Fraction(upper)))
    nb = [mask(s) for s in neighbors(h,w)]; calls = 0
    deadline = time.monotonic()+seconds
    memo = {}
    class Exhausted(Exception): pass
    def tick():
        nonlocal calls
        calls += 1
        if calls > state_limit or time.monotonic() >= deadline: raise Exhausted
    def options(current,other,q):
        for v in range(h*w):
            if current >> v & 1: yield v,other & ~(1<<v),current & ~((1<<v)|nb[v]),-q
        if q.denominator != 1: left = q-Fraction(1,q.denominator)
        elif q > 0: left = q-1
        else: return
        yield -1,other,current,-left
    def win(current,other,q):
        tick(); key = current,other,q
        if key not in memo: memo[key] = any(not win(aa,bb,qq) for _,aa,bb,qq in options(current,other,q))
        return memo[key]
    started = time.monotonic(); q = -upper
    try:
        if win(a,b,q): return None,dict(status='bound_rejected',calls=calls,seconds=time.monotonic()-started)
        root = (a,b,q); states = [root]; seen = {root}; nodes = []; edges = 0
        for aa,bb,qq in states:
            tick(); replies = []
            for mv,ab,ba,qb in options(aa,bb,qq):
                reply = next((r,a2,b2,q2) for r,a2,b2,q2 in options(ab,ba,qb) if not win(a2,b2,q2))
                r,a2,b2,q2 = reply; replies.append([mv,r]); edges += 1
                child = a2,b2,q2
                if child not in seen: seen.add(child); states.append(child)
            nodes.append([aa,bb,qq.numerator,qq.denominator,replies])
        doc = dict(height=h,width=w,root=[a,b,q.numerator,q.denominator],nodes=nodes,edges=edges)
        check_document(doc)
        return doc,dict(status='certified',calls=calls,seconds=time.monotonic()-started)
    except Exhausted:
        return None,dict(status='unknown',calls=calls,seconds=time.monotonic()-started)


def extract_safe_checkpoint(sources, identifier, checkpoint):
    """Extract a grid-only response DAG rooted at a checked zero-offset state.

    Reject numeric moves instead of pretending a compensated strategy can be
    executed using the production same-tile reply player.
    """
    doc = sources.documents[identifier]['doc']
    a,b,qn,qd = checkpoint
    require(fraction([qn,qd]) == 0 and (a,b,Fraction(0)) in sources.nodes[identifier],
            'checkpoint is not a certified zero-offset grid state')
    table = {(aa,bb,Fraction(q,d)):replies for aa,bb,q,d,replies in doc['nodes']}
    h,w = doc['height'],doc['width']; nb = [mask(s) for s in neighbors(h,w)]
    states = [(a,b)]; seen = set(states); nodes = []
    for aa,bb in states:
        replies = table[aa,bb,Fraction(0)]
        require(all(v >= 0 and r >= 0 for v,r in replies), 'numeric move in grid-only strategy')
        ordered = sorted(replies)
        nodes.append([aa,bb,[r for _,r in ordered]])
        for v,r in ordered:
            child = aa & ~((1<<v)|nb[v]|(1<<r)), bb & ~((1<<v)|(1<<r)|nb[r])
            require((*child,Fraction(0)) in table, 'nonzero or missing descendant')
            if child not in seen: seen.add(child); states.append(child)
    extracted = dict(height=h,width=w,root=[a,b],nodes=nodes)
    check_tile(extracted)
    return extracted
