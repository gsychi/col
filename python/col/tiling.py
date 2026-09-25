"""Independent set-based certificate checking, replay, and bounded discovery.

No production DFS, CGT evaluator, or trusted outcome cache is used here.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import time
from collections import deque
from functools import lru_cache
from pathlib import Path


class InvalidCertificate(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidCertificate(message)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


@lru_cache(maxsize=128)
def neighbors(h, w):
    return tuple(frozenset(rr*w+cc for rr, cc in
                          ((r-1,c),(r+1,c),(r,c-1),(r,c+1))
                          if 0 <= rr < h and 0 <= cc < w)
                 for r in range(h) for c in range(w))


def vertices(mask, size):
    require(integer(mask) and mask < 1 << size, 'invalid mask')
    return frozenset(i for i in range(size) if mask >> i & 1)


def mask(cells):
    return sum(1 << v for v in cells)


def move(a, b, v, nb):
    require(v in a, 'illegal move')
    return a - {v} - nb[v], b - {v}


def check_tile(doc):
    h, w = doc['height'], doc['width']
    require(integer(h, 1) and h <= 7 and integer(w, 1) and h*w <= 63,
            'invalid tile dimensions')
    nb = neighbors(h, w)
    require(isinstance(doc['root'], list) and len(doc['root']) == 2, 'invalid root')
    nodes = {}
    for record in doc['nodes']:
        require(isinstance(record, (list, tuple)) and len(record) == 3, 'invalid checkpoint')
        am, bm, replies = record
        a, b = vertices(am, h*w), vertices(bm, h*w)
        require((am, bm) not in nodes and isinstance(replies, list), 'duplicate/malformed checkpoint')
        require(len(replies) == len(a), 'missing Blue response')
        nodes[am, bm] = (a, b, replies)
    root = tuple(doc['root'])
    require(root in nodes, 'missing root')
    edges, adjacency = 0, {}
    for key, (a, b, replies) in nodes.items():
        children = []
        for v, response in zip(sorted(a), replies):
            a1, b1 = move(a, b, v, nb)
            require(integer(response) and response in b1, 'illegal White reply')
            b2, a2 = move(b1, a1, response, nb)
            child = mask(a2), mask(b2)
            require(child in nodes, 'missing successor')
            require(len(a2 | b2) + 2 <= len(a | b), 'nondecreasing edge')
            children.append(child)
            edges += 1
        adjacency[key] = children
    seen, stack = set(), [root]
    while stack:
        key = stack.pop()
        if key not in seen:
            seen.add(key)
            stack.extend(adjacency[key])
    require(len(seen) == len(nodes), 'unreachable checkpoints')
    return edges


def column_sets(h, columns):
    require(integer(h, 1) and h <= 7 and isinstance(columns, list) and columns,
            'invalid board')
    n = len(columns)
    result = [set(), set()]
    for c, pair in enumerate(columns):
        require(isinstance(pair, list) and len(pair) == 2, 'invalid column')
        for actor in (0, 1):
            require(integer(pair[actor]) and pair[actor] < 1 << h, 'invalid column mask')
            result[actor].update(r*n+c for r in range(h) if pair[actor] >> r & 1)
    return tuple(frozenset(s) for s in result)


def to_columns(h, n, a, b):
    return [[sum(1 << r for r in range(h) if r*n+c in s) for s in (a,b)]
            for c in range(n)]


def flip_cell(v, h, w, rf, cf):
    r, c = divmod(v, w)
    return (h-1-r if rf else r)*w + (w-1-c if cf else c)


def check_witness(h, columns, actor, witness, tiles):
    require(integer(actor) and actor <= 1, 'invalid actor')
    actual = column_sets(h, columns)
    n = len(columns)
    va, vb, owner = set(), set(), {}
    require(isinstance(witness, dict) and isinstance(witness['blocks'], list), 'invalid witness')
    for i, block in enumerate(witness['blocks']):
        require(block['tile'] in tiles, 'unknown tile')
        d = tiles[block['tile']]['doc']
        start, w = block['start_column'], d['width']
        rf, cf = block['row_flip'], block['column_flip']
        require(type(rf) is bool and type(cf) is bool, 'invalid transform')
        require(d['height'] == h and integer(start) and start+w <= n, 'tile outside board')
        for v in range(h*w):
            r, c = divmod(flip_cell(v, h, w, rf, cf), w)
            g = r*n+start+c
            require(g not in owner, 'overlapping tiles')
            owner[g] = i
            if d['root'][0] >> v & 1: va.add(g)
            if d['root'][1] >> v & 1: vb.add(g)
    require(actual[actor] <= va, 'uncovered Blue move')
    require(vb <= actual[1-actor], 'invented White move')
    for u, adjacent in enumerate(neighbors(h, n)):
        for v in adjacent:
            if owner.get(u) != owner.get(v):
                require(not (u in vb and v in vb), 'White interaction across blocks')


def check_report(report):
    require(report['format'] == 'col-tiling-proof-v1', 'unknown proof format')
    h, n, actor = report['height'], report['width'], report['turn']
    require(integer(n,1) and n == len(report['columns']), 'width mismatch')
    require(integer(actor) and actor <= 1, 'invalid actor')
    actual = column_sets(h, report['columns'])
    tiles = {}
    for tile in report['library']:
        require(tile['id'] not in tiles, 'duplicate tile ID')
        check_tile(tile['doc'])
        tiles[tile['id']] = tile
    nb = neighbors(h, n)
    def child(cols, turn, cell):
        require(integer(turn) and turn <= 1 and integer(cell), 'invalid move')
        a, b = column_sets(h, cols)
        if turn == 0: a,b = move(a,b,cell,nb)
        else: b,a = move(b,a,cell,nb)
        return to_columns(h,n,a,b)
    for leaf in report.get('cutoffs', []):
        require(len(leaf['columns']) == n, 'cutoff width mismatch')
        cols, turn = leaf['columns'], leaf['turn']
        if leaf['response'] is not None:
            cols, turn = child(cols,turn,leaf['response']), 1-turn
        check_witness(h,cols,turn,leaf['witness'],tiles)
    outcome = report['outcome']
    witness, response = report['witness'], report['response']
    if witness is not None:
        require(not report['openings'] and not report['uncovered'], 'mixed proof forms')
        if outcome == 'loss':
            require(response is None, 'response in direct loss proof')
            cols, turn = report['columns'], actor
        else:
            require(outcome == 'win' and response is not None, 'invalid direct proof')
            cols, turn = child(report['columns'],actor,response), 1-actor
        check_witness(h,cols,turn,witness,tiles)
    else:
        require(outcome in ('loss','unknown') and response is None, 'invalid outcome')
        seen = set()
        for opening in report['openings']:
            v = opening['opening']
            require(integer(v) and v not in seen, 'duplicate opening')
            cols = child(child(report['columns'],actor,v),1-actor,opening['response'])
            check_witness(h,cols,actor,opening['witness'],tiles)
            seen.add(v)
        for v in report['uncovered']:
            require(integer(v) and v in actual[actor] and v not in seen, 'invalid uncovered opening')
            seen.add(v)
        if outcome == 'loss':
            require(not report['uncovered'] and seen == actual[actor], 'incomplete opening proof')
    return tiles


class Strategy:
    """Play the proven winner against arbitrary legal opponent moves."""
    def __init__(self, report):
        self.tiles = check_report(report)
        require(report['outcome'] in ('win','loss'), 'cannot play an unknown result')
        self.h, self.n = report['height'], report['width']
        actor = report['turn']
        self.winner = actor if report['outcome'] == 'win' else 1-actor
        self.loser = 1-self.winner
        self.actual = list(column_sets(self.h, report['columns']))
        self.nb = neighbors(self.h, self.n)
        self.history = []
        self.openings = {o['opening']: o for o in report['openings']}
        self.blocks = None
        self.initial_response = report['response']
        if self.initial_response is not None:
            self._actual_move(self.winner, self.initial_response)
        if report['witness'] is not None:
            self._attach(report['witness'])

    def _attach(self, witness):
        self.blocks = witness['blocks']
        self.states = [tuple(self.tiles[p['tile']]['doc']['root']) for p in self.blocks]
        self.tables = [{(a,b): replies for a,b,replies in self.tiles[p['tile']]['doc']['nodes']}
                       for p in self.blocks]

    def _actual_move(self, actor, v):
        self.actual[actor], self.actual[1-actor] = move(self.actual[actor],self.actual[1-actor],v,self.nb)
        self.history.append((actor,v))

    @property
    def legal_opponent_moves(self):
        return sorted(self.actual[self.loser])

    def reply(self, v):
        self._actual_move(self.loser,v)
        if self.blocks is None:
            require(v in self.openings, 'opening has no certified response')
            o = self.openings[v]
            response = o['response']
            self._attach(o['witness'])
        else:
            r,c = divmod(v,self.n)
            found = False
            for i,p in enumerate(self.blocks):
                d = self.tiles[p['tile']]['doc']; w=d['width']; start=p['start_column']
                if not start <= c < start+w: continue
                local = flip_cell(r*w+c-start,self.h,w,p['row_flip'],p['column_flip'])
                am,bm = self.states[i]
                a,b = vertices(am,self.h*w),vertices(bm,self.h*w)
                require(local in a, 'actual Blue move absent from virtual tile')
                response_local = self.tables[i][am,bm][sorted(a).index(local)]
                a,b = move(a,b,local,neighbors(self.h,w))
                b,a = move(b,a,response_local,neighbors(self.h,w))
                self.states[i] = mask(a),mask(b)
                wr,wc = divmod(flip_cell(response_local,self.h,w,p['row_flip'],p['column_flip']),w)
                response = wr*self.n+start+wc
                found = True
                break
            require(found, 'move outside partition')
        self._actual_move(self.winner,response)
        return response


class Library:
    """Discovery-side DP. Every admitted tile is independently checked."""
    def __init__(self, tiles):
        self.tiles = {t['id']:t for t in tiles}
        require(len(self.tiles) == len(tiles), 'duplicate tile ID')
        for t in tiles: check_tile(t['doc'])
        self.rebuild()

    @classmethod
    def load(cls, directory):
        directory = Path(directory).resolve()
        manifest = json.loads((directory/'manifest.json').read_text())
        require(manifest['format'] == 'col-one-sided-tiles-v1', 'unknown tile format')
        tiles = []
        for entry in manifest['certificates']:
            path = (directory/entry['file']).resolve()
            require(path.is_relative_to(directory), 'certificate outside library')
            raw = path.read_bytes()
            require(hashlib.sha256(raw).hexdigest() == entry['sha256'], 'checksum mismatch')
            doc = json.loads(gzip.decompress(raw))
            require(all(doc[k] == entry[k] for k in ('height','width','root')), 'root metadata mismatch')
            require(len(doc['nodes']) == entry['nodes'] and check_tile(doc) == entry['edges'], 'count mismatch')
            tiles.append({'id':entry['file'],'source_sha256':entry['sha256'],'doc':doc})
        return cls(tiles)

    def rebuild(self):
        self.variants = []
        seen = set()
        for t in self.tiles.values():
            d = t['doc']; h,w=d['height'],d['width']
            for rf,cf in ((False,False),(True,False),(False,True),(True,True)):
                a,b = (mask(flip_cell(v,h,w,rf,cf) for v in vertices(m,h*w)) for m in d['root'])
                if (h,w,a,b) in seen: continue
                seen.add((h,w,a,b))
                left = sum(1<<r for r in range(h) if b>>(r*w)&1)
                right = sum(1<<r for r in range(h) if b>>(r*w+w-1)&1)
                self.variants.append((h,w,a,b,left,right,t['id'],rf,cf))

    @staticmethod
    def extract(h,n,start,w,a,b):
        row = (1<<w)-1
        return tuple(sum(((m>>(r*n+start))&row)<<(r*w) for r in range(h)) for m in (a,b))

    def matches(self,h,n,a,b):
        result = [[] for _ in range(n)]
        for c in range(n):
            for v in self.variants:
                hh,w,ta,tb,*_ = v
                if hh != h or c+w > n: continue
                aa,bb=self.extract(h,n,c,w,a,b)
                if aa&~ta == 0 and tb&~bb == 0: result[c].append(v)
        return result

    def boundaries(self,h,n,a,b):
        matches=self.matches(h,n,a,b)
        dp=[{} for _ in range(n+1)]; dp[0][0]=None
        for c in range(n):
            for p in list(dp[c]):
                if self.extract(h,n,c,1,a,b)[0] == 0:
                    dp[c+1].setdefault(0,(c,p,None))
                for v in matches[c]:
                    if p & v[4] == 0: dp[c+v[1]].setdefault(v[5],(c,p,v))
        suffix=[set() for _ in range(n+1)];suffix[n].add(0)
        for c in reversed(range(n)):
            if self.extract(h,n,c,1,a,b)[0] == 0 and suffix[c+1]: suffix[c].add(0)
            for v in matches[c]:
                if any(v[5]&p == 0 for p in suffix[c+v[1]]): suffix[c].add(v[4])
        return dp,suffix

    def plan(self,h,n,a,b):
        dp,_=self.boundaries(h,n,a,b)
        if not dp[n]: return None
        c,p=n,next(iter(dp[n]));blocks=[]
        while c:
            prev,q,v=dp[c][p]
            if v is not None:
                blocks.append(dict(start_column=prev,tile=v[6],row_flip=v[7],column_flip=v[8]))
            c,p=prev,q
        return {'blocks':list(reversed(blocks))}

    def add(self,doc):
        edges=check_tile(doc)
        raw=gzip.compress(json.dumps(doc,separators=(',',':')).encode(),mtime=0)
        sha=hashlib.sha256(raw).hexdigest();name=f'certificates/mined_{sha[:20]}.json.gz'
        self.tiles[name]={'id':name,'source_sha256':sha,'doc':doc}
        self.rebuild()
        return name,raw,edges

    def save(self,directory):
        directory=Path(directory);(directory/'certificates').mkdir(parents=True,exist_ok=True)
        entries=[]
        for i,t in enumerate(self.tiles.values()):
            d=t['doc'];raw=gzip.compress(json.dumps(d,separators=(',',':')).encode(),mtime=0)
            # Keep each stable tile ID, updating the checksum for this serialization.
            name=t['id'];path=(directory/name).resolve()
            require(path.is_relative_to(directory.resolve()),'tile path outside output')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            entries.append(dict(file=name,sha256=hashlib.sha256(raw).hexdigest(),height=d['height'],width=d['width'],root=d['root'],nodes=len(d['nodes']),edges=check_tile(d)))
        (directory/'manifest.json').write_text(json.dumps(dict(format='col-one-sided-tiles-v1',certificates=entries),indent=2)+'\n')


class BudgetExhausted(Exception):
    pass


def generate_tile(h,w,a,b,state_limit=100000,seconds=1.0):
    """Exact actor-relative minimax. Unknown work never becomes a certificate."""
    require(1 <= h <= 7 and 1 <= h*w <= 63,'invalid tile dimensions')
    require(integer(state_limit,1) and seconds>0,'invalid budget')
    vertices(a,h*w);vertices(b,h*w)
    nb=[mask(s) for s in neighbors(h,w)];memo={};calls=0;deadline=time.monotonic()+seconds
    def tick():
        nonlocal calls
        calls+=1
        if calls>state_limit or time.monotonic()>deadline: raise BudgetExhausted
    def win(current,other):
        tick()
        if not current: return -1
        key=current,other
        if key in memo: return memo[key]
        z=current
        while z:
            bit=z&-z;z-=bit;v=bit.bit_length()-1
            if win(other&~bit,current&~(bit|nb[v]))<0:
                memo[key]=v;return v
        memo[key]=-1;return -1
    started=time.monotonic()
    try:
        if win(a,b)>=0: return None,dict(status='winning',states=calls,seconds=time.monotonic()-started)
        queue=deque([(a,b)]);seen={(a,b)};nodes=[]
        while queue:
            tick()
            aa,bb=queue.popleft();replies=[];z=aa
            while z:
                bit=z&-z;z-=bit;v=bit.bit_length()-1
                a1,b1=aa&~(bit|nb[v]),bb&~bit
                reply=win(b1,a1)
                require(reply>=0,'generator failed to find reply')
                replies.append(reply);rb=1<<reply
                child=a1&~rb,b1&~(rb|nb[reply])
                if child not in seen:seen.add(child);queue.append(child)
            nodes.append([aa,bb,replies])
        doc=dict(height=h,width=w,root=[a,b],nodes=nodes)
        check_tile(doc)
        return doc,dict(status='certified',states=calls,seconds=time.monotonic()-started)
    except BudgetExhausted:
        return None,dict(status='unknown',states=calls,seconds=time.monotonic()-started)
