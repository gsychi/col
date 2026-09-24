import copy
from pathlib import Path
import random
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from col.adaptive_tiling import *
from col.tiling import InvalidCertificate,generate_tile
from col.weighted_tiling import plain_outcome


class AdaptiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library=Library.load(ROOT/'reports/weighted-tiling/checkpoint-library')
        cls.index=IndexedLibrary(cls.library)

    def test_bitsets_equal_linear_matching(self):
        rng=random.Random(1923)
        for w,tiles in self.index.groups.items():
            for _ in range(30):
                a,b=rng.randrange(1<<(3*w)),rng.randrange(1<<(3*w))
                expected=sum(1<<i for i,t in enumerate(tiles) if not a&~t.a and not t.b&~b)
                self.assertEqual(self.index.matching(w,a,b),expected)

    def test_indexed_frontiers_agree_with_reference(self):
        original=IndexedLibrary(self.library,checkpoints=False)
        rng=random.Random(933)
        for n in (3,7,13,19,23):
            for _ in range(5):
                a=b=(1<<(3*n))-1;nb=[mask(s) for s in neighbors(3,n)]
                for t in range(6):
                    legal=[v for v in range(3*n) if (a if t%2==0 else b)>>v&1]
                    if not legal:break
                    v=rng.choice(legal)
                    if t%2==0:a&=~((1<<v)|nb[v]);b&=~(1<<v)
                    else:b&=~((1<<v)|nb[v]);a&=~(1<<v)
                dp,suffix=original.frontiers(n,a,b,reverse=True);refdp,refsuffix=self.library.boundaries(3,n,a,b)
                self.assertEqual([set(d) for d in dp],[set(d) for d in refdp])
                self.assertEqual(suffix,refsuffix)

    def test_known_19_and_replay(self):
        n=19;full=(1<<57)-1;v=26
        a=full&~((1<<v)|mask(neighbors(3,n)[v]));b=full&~(1<<v)
        search=AdaptiveSearch(self.index,n,seconds=5,focus=v)
        self.assertEqual(search.run(a,b,max_white_turns=1)['status'],'certified')
        report=search.artifact(a,b);check_adaptive(report)
        game=AdaptivePlayer(report);game.response();rng=random.Random(23)
        while game.legal_moves:game.opponent(rng.choice(game.legal_moves))
        self.assertEqual(game.turn,0)
        bad=copy.deepcopy(report);bad['nodes'][0]['moves']=[v]
        with self.assertRaises(InvalidCertificate):check_adaptive(bad)

    def test_prefix_coverage_and_exact_small_outcomes(self):
        # No tiles: successful proofs must reach actual terminal positions.
        ix=IndexedLibrary(Library([]));rng=random.Random(952)
        found=None
        for _ in range(40):
            a,b=rng.randrange(64),rng.randrange(64)
            search=AdaptiveSearch(ix,2,seconds=2,max_states=10000)
            result=search.run(a,b,max_white_turns=6)
            self.assertEqual(result['status']=='certified',plain_outcome(3,2,a,b,1))
            if result['status']=='certified':
                report=search.artifact(a,b);check_adaptive(report)
                if any(node['kind']=='all' and node['moves'] for node in report['nodes']):found=report
        self.assertIsNotNone(found)
        bad=copy.deepcopy(found);next(r for r in bad['nodes'] if r['kind']=='all' and r['moves'])['moves'].pop()
        with self.assertRaisesRegex(InvalidCertificate,'uncovered opponent'):check_adaptive(bad)
        # Both color orientations of the complete proof must validate.
        swapped=copy.deepcopy(found);swapped['winner']=0
        swapped['root']=[found['root'][1],found['root'][0],1-found['root'][2]]
        for r in swapped['nodes']:r['a'],r['b'],r['turn']=r['b'],r['a'],1-r['turn']
        check_adaptive(swapped)

    def test_budget_exhaustion_is_unknown(self):
        ix=IndexedLibrary(Library([]))
        search=AdaptiveSearch(ix,3,seconds=1,max_states=1)
        result=search.run(511,511,max_white_turns=3)
        self.assertEqual(result['status'],'unknown');self.assertEqual(result['budget'],'time_or_states')


if __name__=='__main__':unittest.main()
