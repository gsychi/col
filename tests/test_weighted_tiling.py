"""Signed bounds must survive independent play, geometry, and corruption checks."""
import copy
from fractions import Fraction
from pathlib import Path
import random
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from col.weighted_tiling import (Sources, WeightedSearch, check_document, check_cover,
    check_result, plain_outcome, generate_bound, fraction, neighbors, mask, extract_safe_checkpoint)
from col.tiling import InvalidCertificate, flip_cell


class WeightedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=Sources.load()
        cls.engine=WeightedSearch(cls.sources)

    def test_source_counts_and_cap(self):
        self.assertEqual(len(self.sources.documents),44)
        cap=self.engine.bound(3,3,511,503)
        self.assertEqual(fraction(cap['upper']),Fraction(1,4))
        self.assertEqual(check_cover(self.sources,3,3,511,503,cap),Fraction(1,4))
        self.assertEqual(self.engine.query(3,3,511,503,0,reply_scan=False)['outcome'],'win')

    def test_strict_compensation_and_colors(self):
        h,n=3,7; full=(1<<(h*n))-1; v=1
        a=full & ~((1<<v)|mask(neighbors(h,n)[v])); b=full & ~(1<<v)
        result=self.engine.query(h,n,a,b,1,reply_scan=False)
        self.assertEqual(result['kind'],'opponent_negative')
        self.assertLess(fraction(result['cover']['upper']),0)
        self.assertTrue(any(p['checkpoint'][2]<0 for p in result['cover']['blocks']))
        check_result(self.sources,h,n,a,b,1,result)
        check_result(self.sources,h,n,b,a,0,result)
        control=WeightedSearch(self.sources,'nonpositive')
        self.assertEqual(control.query(h,n,a,b,1,reply_scan=False)['outcome'],'unknown')

    def test_zero_is_not_strict(self):
        cover=self.engine.bound(3,1,7,5)
        check_cover(self.sources,3,1,7,5,cover)
        with self.assertRaises(InvalidCertificate):
            check_result(self.sources,3,1,7,5,1,dict(outcome='win',kind='opponent_negative',cover=cover))

    def test_corrupt_numeric_dag(self):
        entry=next(d for d in self.sources.documents.values() if d['origin']=='signed' and d['doc']['edges'])
        doc=copy.deepcopy(entry['doc'])
        next(row for row in doc['nodes'] if row[4])[4].pop()
        with self.assertRaises(ValueError): check_document(doc)
        doc=copy.deepcopy(entry['doc'])
        next(row for row in doc['nodes'] if row[4])[4][0][1]=999
        with self.assertRaises(ValueError): check_document(doc)
        for q in ([0,3],[True,1],[0,0]):
            with self.assertRaises(InvalidCertificate): fraction(q)

    def test_corrupt_assembly(self):
        cover=self.engine.bound(3,5,(1<<15)-1,(1<<15)-1)
        for mutate in (
            lambda c:c.update(upper=[-1,1]),
            lambda c:c['blocks'].pop(),
            lambda c:c['blocks'][0].update(checkpoint=[0,0,99,1]),
            lambda c:c['blocks'][1].update(start_column=c['blocks'][0]['start_column']),
        ):
            bad=copy.deepcopy(cover); mutate(bad)
            with self.assertRaises(InvalidCertificate): check_cover(self.sources,3,5,32767,32767,bad)
        # Two individually valid F1 blocks touch on White-legal outer cells.
        one=self.engine.bound(3,1,7,5)['blocks'][0]
        two=copy.deepcopy(one);two['start_column']=1
        with self.assertRaisesRegex(InvalidCertificate,'interaction'):
            check_cover(self.sources,3,2,63,63,dict(upper=[0,1],blocks=[one,two]))

    def test_small_exact_search_reflections_and_actors(self):
        rng=random.Random(9917); accepted=0
        for width in (2,3):
            for _ in range(36):
                a=rng.randrange(1<<(3*width));b=rng.randrange(1<<(3*width))
                expected=[plain_outcome(3,width,a,b,t) for t in (0,1)]
                for rf,cf in ((False,False),(True,False),(False,True)):
                    aa,bb=(sum(1<<flip_cell(v,3,width,rf,cf) for v in range(3*width) if m>>v&1) for m in (a,b))
                    for turn in (0,1):
                        result=self.engine.query(3,width,aa,bb,turn)
                        check_result(self.sources,3,width,aa,bb,turn,result)
                        if result['outcome']!='unknown':
                            accepted+=1
                            self.assertEqual(result['outcome']=='win',expected[turn])
        self.assertGreater(accepted,50)

    def test_checkpoint_extraction(self):
        doc=extract_safe_checkpoint(self.sources,'signed/economical_bulk_blue.json.gz',[1843,1825,0,1])
        self.assertEqual(doc['root'],[1843,1825])
        self.assertFalse(plain_outcome(3,4,1843,1825,0))
        self.assertGreater(len(doc['nodes']),1)
        with self.assertRaises(InvalidCertificate):
            extract_safe_checkpoint(self.sources,'signed/cap_minus_quarter_blue.json.gz',[511,503,-1,4])

    def test_bounded_discovery(self):
        doc,status=generate_bound(3,1,7,5,Fraction(0),seconds=2)
        self.assertEqual(status['status'],'certified');check_document(doc)
        doc,status=generate_bound(3,3,511,503,Fraction(0),seconds=2)
        self.assertIsNone(doc);self.assertEqual(status['status'],'bound_rejected')
        doc,status=generate_bound(3,3,511,503,Fraction(1,4),seconds=2)
        self.assertEqual(status['status'],'certified');check_document(doc)
        doc,status=generate_bound(3,3,511,503,Fraction(1,4),state_limit=1)
        self.assertIsNone(doc);self.assertEqual(status['status'],'unknown')


if __name__=='__main__':unittest.main()
