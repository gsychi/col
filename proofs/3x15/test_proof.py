#!/usr/bin/env python3
"""Corruption checks and legal-play integration tests, standard library only."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest
from verify import check_tile, check_assembly, verify, InvalidCertificate
from strategy import CertifiedWhite
ROOT=Path(__file__).resolve().parent

class ProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'manifest.json').read_text())
        cls.tiles={e['file']:check_tile(ROOT/e['file'],e) for e in cls.manifest['certificates']}

    def test_full_proof(self):
        result=verify(ROOT,False)
        self.assertEqual(result['opening_cells_covered'],45)

    def test_illegal_first_white_move_rejected(self):
        e=copy.deepcopy(self.manifest['openings'][0])
        e['white_response']=e['blue_opening']
        with self.assertRaises(InvalidCertificate):check_assembly(e,self.tiles)

    def test_missing_block_rejected(self):
        e=copy.deepcopy(self.manifest['openings'][0])
        e['blocks'].pop()
        with self.assertRaises(InvalidCertificate):check_assembly(e,self.tiles)

    def test_overlapping_blocks_rejected(self):
        e=copy.deepcopy(self.manifest['openings'][0])
        e['blocks'][1]['start_column']=0
        with self.assertRaises(InvalidCertificate):check_assembly(e,self.tiles)

    def test_white_bridge_rejected(self):
        # Give White the top-left cell of the first neutral tile. This cell
        # is actually legal, but reinstates a White interaction across the cut.
        e=copy.deepcopy(self.manifest['openings'][0])
        tiles=copy.deepcopy(self.tiles)
        name=e['blocks'][1]['certificate']
        self.assertNotIn(0,tiles[name]['b'])
        tiles[name]['b']=tiles[name]['b']|{0}
        with self.assertRaisesRegex(InvalidCertificate,'White interaction across blocks'):
            check_assembly(e,tiles)

    def test_bad_local_reply_rejected_even_with_updated_checksum(self):
        original=next(e for e in self.manifest['certificates'] if e['edges']>0)
        doc=json.loads(gzip.decompress((ROOT/original['file']).read_bytes()))
        node=next(n for n in doc['nodes'] if n[2])
        # White may not occupy the cell Blue just selected.
        node[2][0]=min(i for i in range(3*doc['width']) if node[0]>>i&1)
        raw=gzip.compress(json.dumps(doc).encode(),mtime=0)
        expected=copy.deepcopy(original);expected['sha256']=hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'bad.json.gz';path.write_bytes(raw)
            with self.assertRaises(InvalidCertificate):check_tile(path,expected)

    def test_all_openings_and_random_legal_play(self):
        rng=random.Random(150315)
        # Reuse immutable certificate data; make 450 independent actual-board games.
        prototype=CertifiedWhite()
        for opening in range(45):
            for repetition in range(10):
                game=object.__new__(CertifiedWhite)
                game.__dict__=prototype.__dict__.copy()
                game.local_states=[];game.history=[]
                game.reply(opening)
                while game.a:
                    game.reply(rng.choice(sorted(game.a)))
                    self.assertLessEqual(len(game.history),22)
                self.assertFalse(game.a)

if __name__=='__main__':unittest.main(verbosity=2)
