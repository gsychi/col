import copy
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'python'))
from col.atlas import Atlas, LocalBound, transpose_doc
from col.certificate_types import Actor, ActualProof, BoundKind, ConstructionRejected, Unknown
from col.adaptive_tiling import AdaptiveSearch, AdaptivePlayer, IndexedLibrary, check_adaptive, resolve_contract
from col.tiling import Library, InvalidCertificate, check_tile, check_witness, mask, neighbors, to_columns, flip_cell
from col.weighted_tiling import plain_outcome


class AtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas=Atlas(ROOT/'proofs/atlas',ROOT/'proofs/atlas-review')
        entries=[dict(id=rel,doc=s.doc) for rel,s in cls.atlas.sources.items()
                 if s.doc['height']==2 and s.doc['width']<=3]
        entries.extend(dict(id=rel+'.transpose',doc=transpose_doc(s.doc)) for rel,s in cls.atlas.sources.items()
                       if s.doc['width']==2 and s.doc['height']==1)
        cls.index=IndexedLibrary(Library(entries),height=2)

    def test_all_sources_roles_and_zero_imports(self):
        v=self.atlas.verification
        self.assertEqual((v['certificates'],v['response_edges'],v['partial_checkpoints'],v['exact_zero_upgrades']),
                         (467,1861429,152473,772))
        self.assertEqual({s.classification_first for s in self.atlas.sources.values()},{Actor.BLUE,Actor.WHITE})
        self.assertTrue(all(not x.responder&~x.first for x in self.atlas.zero_upgrades))
        cp=next(x for x in self.atlas.checkpoints if x.responder&~x.first)
        self.assertEqual(cp.kind,BoundKind.UPPER_ZERO)
        # Transposition changes geometry and reply order, never player roles.
        for source in self.atlas.sources.values():
            if source.doc['height']*source.doc['width']<=6:
                doc=transpose_doc(source.doc);check_tile(doc)
                self.assertEqual(transpose_doc(doc),source.doc if set(source.doc)=={'height','width','root','nodes'} else
                                 {k:source.doc[k] for k in ('height','width','root','nodes')})

    def test_complete_lookup_lazy_counterproofs_and_damaged_masks(self):
        rng=random.Random(734)
        for h,w in ((1,3),(2,2),(2,3),(3,2)):
            full=(1<<(h*w))-1
            for b in range(full+1):
                before=self.atlas.metrics['unsafe_witness_scans'];r=self.atlas.classify(h,w,full,b)
                self.assertEqual(self.atlas.metrics['unsafe_witness_scans'],before)
                first_wins=plain_outcome(h,w,full,b,0)
                if isinstance(r,LocalBound):
                    self.assertFalse(first_wins);self.assertEqual(r.kind,BoundKind.EXACT_ZERO)
                    self.assertFalse(plain_outcome(h,w,full,b,1))
                else:
                    self.assertIsInstance(r,ConstructionRejected);self.assertTrue(first_wins)
                    witness=self.atlas.unsafe_witness(r);v=witness.first_move
                    source=self.atlas.sources[witness.source].doc
                    doc=transpose_doc(source) if witness.transpose else source
                    a1=full&~((1<<v)|mask(neighbors(h,w)[v]));b1=b&~(1<<v)
                    cols=to_columns(h,w,*({v for v in range(h*w) if m>>v&1} for m in (a1,b1)))
                    check_witness(h,cols,1,dict(blocks=[dict(start_column=0,tile='t',row_flip=False,column_flip=False)]),
                                  {'t':dict(doc=doc)})
            for _ in range(50):
                a,b=rng.randrange(full+1),rng.randrange(full+1);r=self.atlas.classify(h,w,a,b)
                if a!=full:self.assertNotIsInstance(r,ConstructionRejected)
                if isinstance(r,LocalBound):
                    self.assertFalse(plain_outcome(h,w,a,b,0))
                    if r.kind==BoundKind.EXACT_ZERO:self.assertFalse(plain_outcome(h,w,a,b,1))
        # The full-first game is unsafe, but damaged first has no moves.
        self.assertIsInstance(self.atlas.classify(2,2,15,0),ConstructionRejected)
        self.assertIsInstance(self.atlas.classify(2,2,0,0),Unknown)
        with self.assertRaises(InvalidCertificate):self.atlas.bound_doc(self.atlas.classify(2,2,15,0))

    def test_missing_classification_or_corrupt_dag_rejected(self):
        data=json.loads((ROOT/'proofs/atlas/data/full2x2_frontier.json').read_text())
        safe,unsafe=self.atlas.shapes[2,2]
        missing=dict(unsafe);missing.pop(next(iter(missing)))
        altered=copy.deepcopy(data);altered['maximal_unsafe_white_masks']=list(missing)
        with self.assertRaisesRegex(InvalidCertificate,'incomplete'):Atlas._check_lattice(15,safe,missing,altered)
        doc=copy.deepcopy(next(s.doc for s in self.atlas.sources.values() if s.doc['root'][0]))
        next(row for row in doc['nodes'] if row[2])[2][0]=999
        with self.assertRaises(InvalidCertificate):check_tile(doc)

    def test_both_actors_exact_cutoffs_color_swaps_and_reflections(self):
        rng=random.Random(1928);counts=[0,0];zeros=0
        for w in (2,3):
            full=(1<<(2*w))-1
            positions=[(a,b) for a in range(16) for b in range(16)] if w==2 else [(rng.randrange(full+1),rng.randrange(full+1)) for _ in range(150)]
            for a,b in positions:
                for rf,cf in ((False,False),(True,True)):
                    aa,bb=(sum(1<<flip_cell(v,2,w,rf,cf) for v in range(2*w) if m>>v&1) for m in (a,b))
                    for turn in (0,1):
                        search=AdaptiveSearch(self.index,w,seconds=2,max_states=5000,two_direction=True,zero_promotion=True)
                        result=search.run(aa,bb,turn,max_white_turns=1)
                        zeros+=search.metrics['exact_zero_promotions']
                        if result['status']=='unknown':
                            self.assertIsInstance(search.result(aa,bb,turn),Unknown);continue
                        typed=search.result(aa,bb,turn);self.assertIsInstance(typed,ActualProof)
                        self.assertEqual(typed.winner==turn,plain_outcome(2,w,aa,bb,turn))
                        proof=typed.artifact;check_adaptive(proof);counts[typed.winner]+=1
                        game=AdaptivePlayer(proof,checked=True)
                        if game.turn==game.winner:game.response()
                        while game.legal_moves:game.opponent(rng.choice(game.legal_moves))
                        self.assertNotEqual(game.turn,game.winner)
        self.assertTrue(all(counts));self.assertGreater(zeros,0)

    def test_actual_zero_with_holes_and_invalid_swapped_seam(self):
        # Actual live cells 0 and 2 retain their induced vertical edge. The
        # other column stays dead; promotion must not fill its holes.
        search=AdaptiveSearch(self.index,2,two_direction=True,zero_promotion=True)
        self.assertTrue(search.leaf(5,5))
        self.assertIn((5,5,1),search.refutations)
        check_adaptive(search.artifact(5,5,0));check_adaptive(search.artifact(5,5,1))
        # Each local first-empty tile is safe, but its protected responders
        # touch across the join. Actor swapping must still reject this seam.
        tile=dict(height=1,width=1,root=[0,1],nodes=[[0,1,[]]])
        witness=dict(blocks=[dict(start_column=i,tile='t',row_flip=False,column_flip=False) for i in range(2)])
        with self.assertRaisesRegex(InvalidCertificate,'interaction'):
            check_witness(1,[[1,0],[1,0]],1,witness,{'t':dict(doc=tile)})

    def test_classification_replaces_only_justified_local_minimax(self):
        with patch('col.tiling.generate_tile',side_effect=AssertionError('minimax should be avoided')):
            doc,stats=resolve_contract(2,2,15,0,atlas=self.atlas)
            self.assertIsNone(doc);self.assertEqual(stats['status'],'construction_rejected')
            doc,stats=resolve_contract(2,2,15,15,atlas=self.atlas)
            check_tile(doc);self.assertTrue(stats['minimax_avoided'])
        with patch('col.tiling.generate_tile',return_value=(None,dict(status='unknown'))) as minimax:
            resolve_contract(2,2,0,0,atlas=self.atlas);minimax.assert_called_once()


if __name__=='__main__':unittest.main()
