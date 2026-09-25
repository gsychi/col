#!/usr/bin/env python3
"""Conservative symbolic bound ledger and independent exact-order regressions."""
from fractions import Fraction as F
from pathlib import Path
import json
from dx_verify_interface_contracts import game, add, leq, number, ZERO, STAR


def classify(terms, cap=F(0), star=0, target=F(0)):
    """Each term is (dyadic bound, weak/strict/paired). Unknown is inconclusive."""
    slack=cap+sum(q for q,kind in terms)-target
    assert star in (0,1)
    assert all(kind in ('weak','strict','paired') for q,kind in terms)
    if slack < 0:return 'paired'
    if slack > 0:return 'unknown'
    if any(kind=='paired' for q,kind in terms):return 'paired'
    if star:return 'unknown'
    return 'strict' if any(kind=='strict' for q,kind in terms) else 'weak'


def holds(g,q,kind):
    target=number(q)
    weak=leq(g,target)
    if kind=='weak':return weak
    if kind=='strict':return weak and not leq(target,g)
    return weak and leq(add(g,STAR),target)


def exact_checks():
    up=game([ZERO],[STAR]);down=game([STAR],[ZERO])
    assert holds(down,F(0),'strict') and not holds(down,F(0),'paired')
    values=[ZERO,STAR,up,down,add(up,STAR),add(down,STAR),
            add(up,up),add(down,down)]
    values += [add(number(F(q,2)),s) for q in (-2,-1,1,2) for s in (ZERO,STAR)]
    bounds=[F(-1),F(-1,2),F(0),F(1,2),F(1)]
    assumptions=[(g,q,kind) for g in values for q in bounds
                 for kind in ('weak','strict','paired') if holds(g,q,kind)]
    total=0
    for g,q,kind in assumptions:
        if kind=='paired':
            assert holds(g,q,'strict') and holds(add(g,STAR),q,'strict')
            assert holds(add(g,STAR),q,'paired')
        for h,r,other in assumptions:
            # Two target levels test both equality and a numerical margin.
            for target in (q+r,q+r+F(1,2)):
                for star in (0,1):
                    conclusion=classify([(q,kind),(r,other)],star=star,target=target)
                    if conclusion!='unknown':
                        result=add(add(g,h),STAR) if star else add(g,h)
                        assert holds(result,target,conclusion)
                        total+=1
    return total


def ledger():
    rows=[]
    for parent,target,ordinary,ordinary_bound in (
        ('RX',F(1),'DR',-F(1,4)),('VX',F(2),'DV',F(1,2)),('XX',F(1),'DX',F(0)),
    ):
        for column,minimum,delta,family,bound,kind,cap,local_star in (
            (1,5,2,parent,target,'paired',F(0),0),
            (2,5,3,ordinary,ordinary_bound,'weak',F(-1),0),
            (3,7,4,parent,target,'paired',F(0),1),
        ):
            assert minimum-delta>0 and delta>0
            for external in (0,1):
                conclusion=classify([(bound,kind)],cap,external^local_star,target)
                assert conclusion in ('strict','paired')
                rows.append(dict(parent=parent,target=str(target),distance_from_X=column,min_width=minimum,
                                 width_parity='odd',external_star=external,
                                 child=family,child_width_delta=-delta,
                                 assumed_bound=str(bound),assumed_kind=kind,
                                 cap_number=str(cap),cap_star=local_star,
                                 next_player='White',conclusion=conclusion,
                                 status='conditional_on_child_bound'))
    unsafe=classify([(F(1),'strict')],F(-1),1,F(0))
    assert unsafe=='unknown'
    return dict(clauses=rows,
                unsafe_RX_star_extension=unsafe,
                same_width_star_move=dict(next_player='White',
                    status='requires_independent_unstarred_White_first_witness',
                    permitted_rank='(width,stage1) -> already proved (width,stage0)'),
                scope='Algebraic conditional checks only; no auxiliary induction is closed.')


if __name__=='__main__':
    count=exact_checks()
    result=ledger();result['finite_order_checks']=count
    path=Path(__file__).with_name('round4_star_bound_ledger.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(f'VERIFIED {count} finite exact-order applications and eighteen conditional endpoint clauses.')
    print('REJECTED unsafe strict-plus-star inference; White-first witness remains explicit.')
