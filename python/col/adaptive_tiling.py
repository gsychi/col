"""Bounded adaptive strategies with verified grid-tile leaves.

Unknown means no proof was found within this depth/budget, never a game loss.
All checkpoints of checked grid-only DAGs may be reused. Production is unchanged.
"""
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
import math
import time

from col.tiling import (Library, Strategy, check_tile, check_witness, column_sets,
                        flip_cell, integer, mask, move, neighbors, require, to_columns)
from col.certificate_types import Actor, ActualProof, BoundKind, Unknown, matched_bound


@dataclass(frozen=True)
class Tile:
    width: int
    a: int
    b: int
    source: str
    checkpoint: tuple
    row_flip: bool
    column_flip: bool
    left: int
    right: int


class IndexedLibrary:
    """Bitset subset queries: A_actual <= A_tile, B_tile <= B_actual.

    Match caches depend on local masks and library revision, not global width.
    """
    def __init__(self, library, height=3, checkpoints=True, cache_size=100000):
        require(integer(height,1) and height<=7 and integer(cache_size,1),'invalid index dimensions/cache')
        self.library=library;self.height=height;self.cache_size=cache_size
        self.rebuild(checkpoints)

    def rebuild(self, checkpoints=True):
        self.checkpoints=checkpoints; h=self.height; unique={}
        @lru_cache(None)
        def transform(m,w,rf,cf):
            return sum(1<<flip_cell(v,h,w,rf,cf) for v in range(h*w) if m>>v&1)
        for name,entry in self.library.tiles.items():
            doc=entry['doc']; w=doc['width']
            if doc['height']!=h: continue
            states=(row[:2] for row in doc['nodes']) if checkpoints else [doc['root']]
            for a,b in states:
                for rf,cf in ((False,False),(True,False),(False,True),(True,True)):
                    aa,bb=transform(a,w,rf,cf),transform(b,w,rf,cf)
                    key=w,aa,bb
                    if key in unique:continue
                    left=sum(1<<r for r in range(h) if bb>>(r*w)&1)
                    right=sum(1<<r for r in range(h) if bb>>(r*w+w-1)&1)
                    unique[key]=Tile(w,aa,bb,name,(a,b),rf,cf,left,right)
        self.groups={}
        for tile in unique.values(): self.groups.setdefault(tile.width,[]).append(tile)
        self.index={}
        for w,tiles in self.groups.items():
            all_bits=(1<<len(tiles))-1; a_bits=[0]*(h*w); b_bits=[0]*(h*w)
            left=[0]*(1<<h);right=[0]*(1<<h)
            for i,tile in enumerate(tiles):
                bit=1<<i
                for v in range(h*w):
                    if tile.a>>v&1:a_bits[v]|=bit
                    if tile.b>>v&1:b_bits[v]|=bit
                left[tile.left]|=bit;right[tile.right]|=bit
            compatible=[sum(left[l] for l in range(1<<h) if not l&p) for p in range(1<<h)]
            right_compatible=[sum(right[r] for r in range(1<<h) if not r&p) for p in range(1<<h)]
            self.index[w]=(all_bits,a_bits,[all_bits^b for b in b_bits],compatible,right,left,right_compatible)
        self.matches_cache=OrderedDict();self.variant_count=len(unique)
        self.metrics=dict(queries=0,query_seconds=0.0,local_queries=0,local_cache_hits=0,covers=0)

    def matching(self,w,a,b):
        key=w,a,b;self.metrics['local_queries']+=1
        if key in self.matches_cache:
            self.metrics['local_cache_hits']+=1
            result=self.matches_cache.pop(key);self.matches_cache[key]=result;return result
        all_bits,yes_a,no_b,*_=self.index[w]; candidates=all_bits
        bits=a
        while bits and candidates:
            low=bits&-bits;bits-=low;candidates &= yes_a[low.bit_length()-1]
        bits=((1<<(self.height*w))-1)^b
        while bits and candidates:
            low=bits&-bits;bits-=low;candidates &= no_b[low.bit_length()-1]
        self.matches_cache[key]=candidates
        if len(self.matches_cache)>self.cache_size:self.matches_cache.popitem(last=False)
        return candidates

    def frontiers(self,n,a,b,reverse=False):
        h=self.height;dp=[{} for _ in range(n+1)];dp[0][0]=None;matches={}
        for c in range(n):
            if not dp[c]: continue
            if Library.extract(h,n,c,1,a,b)[0]==0: dp[c+1].setdefault(0,(c,next(iter(dp[c])),None))
            for w in self.groups:
                if c+w>n:continue
                aa,bb=Library.extract(h,n,c,w,a,b);bits=self.matching(w,aa,bb);matches[c,w]=bits
                if not bits:continue
                _,_,_,left,right,*_=self.index[w]
                for p in dp[c]:
                    allowed=bits&left[p]
                    if not allowed:continue
                    for r,rbits in enumerate(right):
                        if r in dp[c+w]:continue
                        available=allowed&rbits
                        if available:
                            tile=self.groups[w][(available&-available).bit_length()-1]
                            dp[c+w][r]=(c,p,tile)
        suffix=None
        if reverse:
            suffix=[set() for _ in range(n+1)];suffix[n].add(0)
            for c in reversed(range(n)):
                if Library.extract(h,n,c,1,a,b)[0]==0 and suffix[c+1]:suffix[c].add(0)
                for w in self.groups:
                    if c+w>n or not suffix[c+w]:continue
                    bits=matches.get((c,w))
                    if bits is None:
                        aa,bb=Library.extract(h,n,c,w,a,b);bits=self.matching(w,aa,bb)
                    if not bits:continue
                    *_,left_exact,right_compatible=self.index[w]
                    for r in suffix[c+w]:
                        available=bits&right_compatible[r]
                        for l,lbits in enumerate(left_exact):
                            if available&lbits:suffix[c].add(l)
        return dp,suffix

    def plan(self,n,a,b):
        t=time.perf_counter();self.metrics['queries']+=1
        dp,_=self.frontiers(n,a,b)
        self.metrics['query_seconds']+=time.perf_counter()-t
        if not dp[n]:return None
        c,p=n,next(iter(dp[n]));blocks=[]
        while c:
            prev,q,tile=dp[c][p]
            if tile is not None:
                blocks.append(dict(start_column=prev,source=tile.source,checkpoint=list(tile.checkpoint),
                    row_flip=tile.row_flip,column_flip=tile.column_flip))
            c,p=prev,q
        self.metrics['covers']+=1
        return dict(blocks=list(reversed(blocks)))


def extract_checkpoint(library, identifier, checkpoint):
    doc=library.tiles[identifier]['doc'];h,w=doc['height'],doc['width']
    table={(a,b):r for a,b,r in doc['nodes']};nb=[mask(s) for s in neighbors(h,w)]
    root=tuple(checkpoint);require(root in table,'missing checkpoint')
    states=[root];seen={root};nodes=[]
    for a,b in states:
        replies=table[a,b];nodes.append([a,b,list(replies)])
        legal=[v for v in range(h*w) if a>>v&1]
        for v,r in zip(legal,replies):
            child=a&~((1<<v)|nb[v]|(1<<r)),b&~((1<<v)|(1<<r)|nb[r])
            if child not in seen:seen.add(child);states.append(child)
    result=dict(height=h,width=w,root=list(root),nodes=nodes)
    check_tile(result);return result


class Exhausted(Exception):pass


class AdaptiveSearch:
    """Iterative bounded AND/OR search, with all response cutoffs preflighted.

    At White nodes one move suffices; at Blue nodes every move is required.
    Failed branches guide subsequent move ordering. A failure only concerns
    this bounded proof language and is never stored as an exact game outcome.
    """
    def __init__(self,index,n,seconds=30,max_states=100000,focus=None,two_direction=False,zero_promotion=False):
        require(math.isfinite(seconds) and seconds>0 and integer(max_states,1),'invalid budget')
        require(integer(n,1),'invalid board width')
        self.index=index;self.h=index.height;self.n=n;self.size=self.h*n
        self.nb=[mask(s) for s in neighbors(self.h,n)]
        self.deadline=time.monotonic()+seconds;self.max_states=max_states;self.focus=focus
        self.nodes={};self.failed=set();self.cover_cache={};self.failures=[];self.hard_moves={}
        self.refutations={};self.two_direction=two_direction;self.zero_promotion=zero_promotion
        self.metrics=dict(states=0,memo_hits=0,white_preflights=0,failed_branches=0,depths_completed=[],
                          blue_loss_queries=0,white_loss_queries=0,blue_loss_leaves=0,white_loss_leaves=0,
                          actual_refutation_cutoffs=0,exact_zero_promotions=0)
        self.budget='not_run'

    def tick(self):
        if time.monotonic()>=self.deadline or self.metrics['states']>=self.max_states:raise Exhausted

    def child(self,a,b,turn,v):
        bit=1<<v
        return (a&~(bit|self.nb[v]),b&~bit,1) if turn==0 else (a&~bit,b&~(bit|self.nb[v]),0)

    def legal(self,a,b,turn):
        bits=a if turn==0 else b
        result=[]
        while bits:
            low=bits&-bits;bits-=low;result.append(low.bit_length()-1)
        def priority(v):
            distance=abs(v//self.n-self.focus//self.n)+abs(v%self.n-self.focus%self.n) if self.focus is not None else 0
            return -self.hard_moves.get(v,0) if turn==0 else 0,distance,v
        return sorted(result,key=priority)

    def representative_white_moves(self,a,b):
        moves=self.legal(a,b,1);transforms=[]
        for rf,cf in ((True,False),(False,True),(True,True)):
            flipped=tuple(sum(1<<flip_cell(v,self.h,self.n,rf,cf) for v in range(self.size) if m>>v&1) for m in (a,b))
            if flipped==(a,b):transforms.append((rf,cf))
        seen=set();result=[]
        for v in moves:
            if v in seen:continue
            result.append(v);seen.add(v)
            for rf,cf in transforms:seen.add(flip_cell(v,self.h,self.n,rf,cf))
        return result

    def loss_leaf(self,a,b,actor):
        # The entire construction is oriented to its first player, including
        # the responder's seam masks. Never negate an untransformed result.
        first,responder=(a,b) if actor==0 else (b,a)
        key=first,responder
        if key not in self.cover_cache:
            self.tick()
            self.metrics['blue_loss_queries' if actor==0 else 'white_loss_queries']+=1
            self.cover_cache[key]=self.index.plan(self.n,first,responder)
        cover=self.cover_cache[key]
        if cover is not None:
            target=self.nodes if actor==0 else self.refutations
            target[a,b,actor]=dict(kind='tiling',cover=cover)
            self.metrics['blue_loss_leaves' if actor==0 else 'white_loss_leaves']+=1
            if self.zero_promotion and matched_bound(first,responder)==BoundKind.EXACT_ZERO:
                # The SAME witness embeds with the opposite actor: its first
                # mask still contains actual responder, and its responder mask
                # is still contained in actual first. Its seams are unchanged.
                # Export an ordinary actor-oriented witness, checked normally.
                other=self.refutations if actor==0 else self.nodes
                other[a,b,1-actor]=dict(kind='tiling',cover=cover)
                self.metrics['exact_zero_promotions']+=1
            return True
        return False

    def leaf(self,a,b):
        return self.loss_leaf(a,b,0)

    def prove(self,a,b,turn,white_turns,path=()):
        self.tick();self.metrics['states']+=1;key=a,b,turn
        if key in self.nodes:self.metrics['memo_hits']+=1;return True
        if key in self.refutations:
            self.metrics['actual_refutation_cutoffs']+=1;return False
        if (key,white_turns) in self.failed:self.metrics['memo_hits']+=1;return False
        if turn==0 and self.leaf(a,b):return True
        if turn==1 and self.two_direction and self.loss_leaf(a,b,1):
            self.metrics['actual_refutation_cutoffs']+=1;return False
        if not white_turns or turn==1 and not b:
            self.failed.add((key,white_turns));return False
        if turn==1:
            moves=self.representative_white_moves(a,b);children=[]
            # Check every immediate certified child before expanding descendants.
            for v in moves:
                self.tick();child=self.child(a,b,1,v);children.append((v,child))
                self.metrics['white_preflights']+=1
                if self.leaf(*child[:2]):
                    self.nodes[key]=dict(kind='choice',move=v,child=child);return True
            if white_turns>1:
                for v,child in children:
                    if self.prove(*child,white_turns-1,path+(v,)):
                        self.nodes[key]=dict(kind='choice',move=v,child=child);return True
            # Symmetry representatives suffice to search for a White win, but
            # a White loss needs every legal White move in an executable DAG.
            # Do not silently treat omitted symmetric moves as covered.
            if len(children)==b.bit_count() and all(child in self.refutations for _,child in children):
                self.refutations[key]=dict(kind='all',branches=children)
        else:
            branches=[]
            for v in self.legal(a,b,0):
                child=self.child(a,b,0,v)
                if not self.prove(*child,white_turns,path+(v,)):
                    if child in self.refutations:
                        self.refutations[key]=dict(kind='choice',move=v,child=child)
                    self.hard_moves[v]=self.hard_moves.get(v,0)+1
                    self.metrics['failed_branches']+=1
                    if len(self.failures)<200:
                        self.failures.append(dict(a=hex(child[0]),b=hex(child[1]),turn=1,path=list(path+(v,)),white_turns=white_turns))
                    self.failed.add((key,white_turns));return False
                branches.append((v,child))
            self.nodes[key]=dict(kind='all',branches=branches);return True
        self.failed.add((key,white_turns));return False

    def run(self,a,b,turn=1,max_white_turns=2):
        require(integer(a) and integer(b) and (a|b)<1<<self.size and type(turn)is int and turn in (0,1),'invalid root')
        require(integer(max_white_turns,1),'invalid depth')
        started=time.monotonic();status='unknown';budget='depth'
        try:
            for depth in range(1,max_white_turns+1):
                if self.prove(a,b,turn,depth):status='certified';budget=None;break
                if (a,b,turn) in self.refutations:status='refuted';budget=None;break
                self.metrics['depths_completed'].append(depth)
        except Exhausted:budget='time_or_states'
        self.budget=budget
        return dict(status=status,budget=budget,winner=1 if status=='certified' else 0 if status=='refuted' else None,
                    seconds=time.monotonic()-started,
                    metrics=dict(self.metrics),oracle=dict(self.index.metrics),failures=self.failures)

    def result(self,a,b,turn=1):
        if (a,b,turn) not in self.nodes and (a,b,turn) not in self.refutations:
            return Unknown(self.budget)
        artifact=self.artifact(a,b,turn)
        return ActualProof(Actor(artifact['winner']),(a,b,turn),artifact)

    def artifact(self,a,b,turn=1):
        root=a,b,turn
        winner=1 if root in self.nodes else 0
        proved=self.nodes if winner==1 else self.refutations
        require(root in proved,'root is not proved')
        used_library=Library([]);converted={};output=[];seen={root};queue=[root]
        for key in queue:
            node=proved[key];record=dict(a=hex(key[0]),b=hex(key[1]),turn=key[2],kind=node['kind'])
            if node['kind']=='tiling':
                blocks=[]
                for p in node['cover']['blocks']:
                    local=p['source'],tuple(p['checkpoint'])
                    if local not in converted:
                        doc=extract_checkpoint(self.index.library,*local);name,_,_=used_library.add(doc);converted[local]=name
                        source=self.index.library.tiles[local[0]]
                        used_library.tiles[name]['derived_from']=dict(source_id=local[0],checkpoint=list(local[1]),
                            source_sha256=source.get('source_sha256'),provenance=source.get('provenance'))
                    blocks.append(dict(start_column=p['start_column'],tile=converted[local],
                                       row_flip=p['row_flip'],column_flip=p['column_flip']))
                record['witness']=dict(blocks=blocks)
            else:
                branches=[(node['move'],node['child'])] if node['kind']=='choice' else node['branches']
                record['moves']=[v for v,_ in branches]
                for _,child in branches:
                    if child not in seen:seen.add(child);queue.append(child)
            output.append(record)
        return dict(format='col-adaptive-tiling-proof-v1',height=self.h,width=self.n,
            root=[hex(a),hex(b),turn],winner=winner,nodes=output,library=list(used_library.tiles.values()))


def check_adaptive(report):
    """Independent set-based checker; never calls the search or its bitset oracle."""
    require(report['format']=='col-adaptive-tiling-proof-v1','invalid adaptive format')
    h,n=report['height'],report['width'];require(integer(h,1) and h<=7 and integer(n,1),'invalid dimensions')
    winner=report['winner'];require(type(winner)is int and winner in (0,1),'invalid winner')
    library=Library(report['library']);nb=neighbors(h,n);nodes={}
    def state(a,b,t):
        require(type(t)is int and t in (0,1),'invalid turn')
        aa,bb=int(a,16),int(b,16)
        require(0<=aa<1<<(h*n) and 0<=bb<1<<(h*n),'invalid masks')
        return aa,bb,t
    for row in report['nodes']:
        key=state(row['a'],row['b'],row['turn']);require(key not in nodes,'duplicate node');nodes[key]=row
    root=state(*report['root']);require(root in nodes,'missing root');seen=set();stack=[root];edges=0
    while stack:
        key=stack.pop()
        if key in seen:continue
        seen.add(key);row=nodes[key];a,b,t=key
        sets=[{v for v in range(h*n) if m>>v&1} for m in (a,b)]
        if row['kind']=='tiling':
            require(t!=winner,'tile leaf has wrong actor')
            check_witness(h,to_columns(h,n,*sets),t,row['witness'],library.tiles);continue
        choices=row['moves']
        require(all(integer(v) for v in choices) and len(set(choices))==len(choices),'invalid move list')
        if row['kind']=='choice':require(t==winner and len(choices)==1,'invalid choice node')
        else:require(row['kind']=='all' and t!=winner and set(choices)==sets[t],'uncovered opponent move')
        for v in choices:
            aa,bb=move(sets[t],sets[1-t],v,nb);pair=[None,None];pair[t]=aa;pair[1-t]=bb
            child=mask(pair[0]),mask(pair[1]),1-t
            require(child in nodes,'missing child')
            require(len(aa|bb)<len(sets[0]|sets[1]),'nondecreasing edge')
            stack.append(child);edges+=1
    require(len(seen)==len(nodes),'unreachable nodes')
    return dict(nodes=len(nodes),edges=edges,tiles=len(library.tiles))


class AdaptivePlayer:
    def __init__(self,report,checked=False):
        if not checked:check_adaptive(report)
        self.report=report;self.h=report['height'];self.n=report['width'];self.winner=report['winner']
        a,b,self.turn=report['root'];self.actual=[int(a,16),int(b,16)]
        self.nodes={(int(r['a'],16),int(r['b'],16),r['turn']):r for r in report['nodes']}
        self.nb=[mask(s) for s in neighbors(self.h,self.n)];self.tail=None;self.history=[]

    @property
    def legal_moves(self):return [v for v in range(self.h*self.n) if self.actual[self.turn]>>v&1]

    def play(self,v):
        require(v in self.legal_moves,'illegal actual move')
        actor=self.turn;bit=1<<v
        self.actual[actor]&=~(bit|self.nb[v]);self.actual[1-actor]&=~bit
        self.turn=1-actor;self.history.append((actor,v))

    def response(self):
        require(self.turn==self.winner,'not winner turn')
        node=self.nodes[(*self.actual,self.turn)];require(node['kind']=='choice','missing winner choice')
        v=node['moves'][0];self.play(v);return v

    def opponent(self,v):
        require(self.turn!=self.winner,'not opponent turn')
        if self.tail is None:
            node=self.nodes[(*self.actual,self.turn)]
            if node['kind']=='tiling':
                sets=[{v for v in range(self.h*self.n) if m>>v&1} for m in self.actual]
                r=dict(format='col-tiling-proof-v1',height=self.h,width=self.n,turn=self.turn,
                    columns=to_columns(self.h,self.n,*sets),library=self.report['library'],
                    outcome='loss',witness=node['witness'],response=None,openings=[],uncovered=[])
                self.tail=Strategy(r)
        if self.tail is not None:
            response=self.tail.reply(v);self.play(v);self.play(response);return response
        self.play(v);return self.response()


def discover_contracts(index,n,positions,seconds=30,max_candidates=64,tile_seconds=0.5,max_states=100000,focus=None,excluded=None,atlas=None):
    """Search an exact local game only where checked prefixes/suffixes meet it."""
    started=time.monotonic();deadline=started+seconds;h=index.height
    require(integer(max_candidates,1) and integer(max_states,1) and seconds>0 and tile_seconds>0,'invalid discovery budget')
    nb=[mask(s) for s in neighbors(h,n)];candidates={};records=[];added=[]
    # Collect concrete missing contracts first; repeated obligations get priority.
    for position in positions:
        a,b=position['a'],position['b'];position_candidates={}
        legal=[v for v in range(h*n) if b>>v&1]
        if focus is not None:legal.sort(key=lambda v:abs(v//n-focus//n)+abs(v%n-focus%n))
        for response in legal:
            if time.monotonic()>=deadline:break
            aa,bb=a&~(1<<response),b&~((1<<response)|nb[response])
            dp,suffix=index.frontiers(n,aa,bb,reverse=True)
            if dp[n]:continue
            for w in range(min(n,21//h),0,-1):
                for c in range(n-w+1):
                    if not dp[c] or not suffix[c+w]:continue
                    if focus is not None and not c<=focus%n<c+w:continue
                    la,lb=Library.extract(h,n,c,w,aa,bb)
                    for left in dp[c]:
                        for right in suffix[c+w]:
                            forbidden=sum((1<<(r*w) if left>>r&1 else 0)|(1<<(r*w+w-1) if right>>r&1 else 0) for r in range(h))
                            key=h,w,la,lb&~forbidden
                            context=dict(path=position.get('path',[]),response=response,start_column=c,left=left,right=right)
                            if key not in position_candidates:position_candidates[key]=dict(context=context,hits=0)
                            position_candidates[key]['hits']+=1
        for key,context in position_candidates.items():
            if key not in candidates:candidates[key]=context
            else:candidates[key]['hits']+=context['hits']
        if time.monotonic()>=deadline:break
    collect_seconds=time.monotonic()-started
    ordered=sorted(candidates.items(),key=lambda item:((item[0][2]==(1<<(item[0][0]*item[0][1]))-1),-item[1]['hits'],(item[0][2]|item[0][3]).bit_count(),item[0]))
    skipped=0;avoided=0;classification_rejections=0
    for (hh,w,a,b),context in ordered:
        if excluded is not None and (hh,w,a,b) in excluded:
            skipped+=1;continue
        if time.monotonic()>=deadline or len(records)>=max_candidates:break
        doc,metrics=resolve_contract(hh,w,a,b,atlas=atlas,state_limit=max_states,
            seconds=min(tile_seconds,max(.001,deadline-time.monotonic())))
        avoided+=int(metrics.get('minimax_avoided',False))
        classification_rejections+=int(metrics['status']=='construction_rejected')
        row=dict(height=hh,width=w,a=hex(a),b=hex(b),**context,**metrics);records.append(row)
        if doc is not None:
            old=set(index.library.tiles);name,_,edges=index.library.add(doc)
            row.update(tile=name,nodes=len(doc['nodes']),edges=edges)
            if name not in old:added.append(name)
    if added:index.rebuild(index.checkpoints)
    return dict(seconds=time.monotonic()-started,collect_seconds=collect_seconds,
        unique_contracts=len(candidates),previously_resolved=skipped,attempts=records,added=added,
        minimax_calls_avoided=avoided,construction_rejections=classification_rejections,
        limits=dict(seconds=seconds,max_candidates=max_candidates,max_tile_cells=21,tile_seconds=tile_seconds,max_states=max_states))


def resolve_contract(h,w,a,b,atlas=None,state_limit=100000,seconds=.5):
    """Local classification may avoid minimax; rejection never resolves a board."""
    from col.atlas import LocalBound
    from col.certificate_types import ConstructionRejected
    from col.tiling import generate_tile
    if atlas is not None:
        started=time.perf_counter();result=atlas.classify(h,w,a,b)
        if isinstance(result,ConstructionRejected):
            return None,dict(status='construction_rejected',states=0,seconds=time.perf_counter()-started,
                minimax_avoided=True,reason=result.reason)
        if isinstance(result,LocalBound):
            return atlas.bound_doc(result),dict(status='certified',states=0,seconds=time.perf_counter()-started,
                minimax_avoided=True,bound_kind=result.kind.value)
    return generate_tile(h,w,a,b,state_limit=state_limit,seconds=seconds)
