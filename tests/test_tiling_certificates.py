"""Independent checks of Rust-generated certificates and executable strategies."""
import copy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from functools import lru_cache

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
sys.path.insert(0,str(ROOT/'scripts'))
from col.tiling import (Library, Strategy, InvalidCertificate, check_report, check_tile,
                        generate_tile, mask, neighbors, to_columns, check_witness)
from tiling_research import coverage

BIN=ROOT/'solver/target/release/col-cert'

class TilingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BIN.exists():
            raise RuntimeError('Build cargo --release --bin col-cert before these integration tests')
        cls.temp=tempfile.TemporaryDirectory(prefix='col-tiling-tests-')
        cls.library=Library.load(ROOT/'proofs/3x15')
        cls.reports={}
        for n in (15,19,101):
            path=Path(cls.temp.name)/f'3x{n}.json'
            result=subprocess.run([str(BIN),'--m','3','--n',str(n),'--proof-out',str(path)],text=True,capture_output=True)
            if result.returncode != (2 if n==19 else 0):raise RuntimeError(result.stdout+result.stderr)
            cls.reports[n]=json.loads(path.read_text())
        cls.prototype=Strategy(cls.reports[15])

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_both_checkers_and_unknown(self):
        for n,report in self.reports.items():
            check_report(report)
            self.assertEqual(report['outcome'],'unknown' if n==19 else 'loss')
            path=Path(self.temp.name)/f'3x{n}.json'
            result=subprocess.run([str(BIN),'verify',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        bad=copy.deepcopy(self.reports[19]);bad['outcome']='loss'
        with self.assertRaises(InvalidCertificate):check_report(bad)
        self.assertEqual(self.reports[19]['uncovered'],[26,30])

    def test_all_45_openings_with_arbitrary_play(self):
        rng=random.Random(150315)
        for opening in range(45):
            for _ in range(10):
                game=object.__new__(Strategy)
                game.__dict__=self.prototype.__dict__.copy()
                game.actual=list(game.actual);game.history=[]
                game.reply(opening)
                while game.legal_opponent_moves:
                    game.reply(rng.choice(game.legal_opponent_moves))
                self.assertLessEqual(len(game.history),45)

    def test_long_board_replay_and_color_swap(self):
        rng=random.Random(101)
        for swapped in (False,True):
            report=copy.deepcopy(self.reports[101])
            if swapped:
                report['turn']=1
                report['columns']=[p[::-1] for p in report['columns']]
            game=Strategy(report)
            while game.legal_opponent_moves:game.reply(rng.choice(game.legal_opponent_moves))
            self.assertLessEqual(len(game.history),303)

    def test_corruption(self):
        original=self.reports[15]
        edits=[lambda r:r['openings'].pop(),
               lambda r:r['openings'][0].update(response=r['openings'][0]['opening']),
               lambda r:r['openings'][0]['witness']['blocks'].pop(),
               lambda r:r['openings'][0]['witness']['blocks'][1].update(start_column=0)]
        for edit in edits:
            r=copy.deepcopy(original);edit(r)
            with self.assertRaises(InvalidCertificate):check_report(r)
        doc=copy.deepcopy(next(t['doc'] for t in original['library'] if t['doc']['root'][0]))
        node=next(n for n in doc['nodes'] if n[2]);node[2][0]=(node[0]&-node[0]).bit_length()-1
        with self.assertRaises(InvalidCertificate):check_tile(doc)

    def test_demon_and_response_30(self):
        path=Path(self.temp.name)/'demon.json'
        result=subprocess.run([str(BIN),'--m','3','--n','15','--position','B.............B/.............../..............W','--turn','P2','--proof-out',str(path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(path.read_text());check_report(report)
        self.assertEqual(report['response'],12)
        game=Strategy(report);rng=random.Random(12)
        while game.legal_opponent_moves:game.reply(rng.choice(game.legal_opponent_moves))
        nb=neighbors(3,15);occupied={0,14,44,30}
        a=set(range(45))-occupied-nb[0]-nb[14]
        b=set(range(45))-occupied-nb[44]-nb[30]
        self.assertIsNone(self.library.plan(3,15,mask(a),mask(b)))

    def test_benchmark_records_tiling_metrics(self):
        from odd_board_experiments import parse_output
        parsed=parse_output('tiling metrics: {"queries":7,"matching_tiles":4,"successful_covers":2,"dfs_cutoffs":1,"query_seconds":0.125}')
        self.assertEqual(parsed['tiling_queries'],7)
        self.assertEqual(parsed['tiling_query_seconds'],0.125)
        self.assertEqual(parsed['tiling_dfs_cutoffs'],1)

    @unittest.skipUnless(os.name == "posix", "POSIX resource usage")
    def test_memory_measurement_fallback_and_timeout(self):
        from odd_board_experiments import run_one
        from col.boards import BoardSpec
        board=BoardSpec.parse('3x3')
        config=SimpleNamespace(name='memory-test')
        args=SimpleNamespace(out_dir=Path(self.temp.name),timeout=5)
        command=[sys.executable,'-c',"print('3 x 3: P2 wins'); print('states searched: 1')"]
        with patch('odd_board_experiments.darwin_extended_time_available',return_value=False), patch('odd_board_experiments.solver_command',return_value=command):
            result=run_one(args,board,config,1)
        self.assertTrue(result.ok)
        self.assertGreater(result.peak_rss_bytes,0)
        args.timeout=0.05
        with patch('odd_board_experiments.darwin_extended_time_available',return_value=False), patch('odd_board_experiments.solver_command',return_value=[sys.executable,'-c','import time; time.sleep(20)']):
            result=run_one(args,board,config,1)
        self.assertEqual(result.returncode,124)
        self.assertLess(result.wall_seconds,3)

    def test_generated_small_tiles_and_budget(self):
        doc,stats=generate_tile(3,1,7,5)
        self.assertEqual(stats['status'],'certified');self.assertEqual(check_tile(doc),3)
        doc,stats=generate_tile(3,7,(1<<21)-1,(1<<21)-1,state_limit=1)
        self.assertIsNone(doc);self.assertEqual(stats['status'],'unknown')
        doc,stats=generate_tile(3,1,1,1)
        self.assertIsNone(doc);self.assertEqual(stats['status'],'winning')

    def test_random_shadows_against_plain_recursion(self):
        rng=random.Random(307);h,n=3,3;nb=[mask(s) for s in neighbors(h,n)]
        @lru_cache(None)
        def win(a,b):
            for v in range(h*n):
                if a>>v&1 and not win(b&~(1<<v),a&~((1<<v)|nb[v])):return True
            return False
        accepted=0
        for _ in range(300):
            a,b=rng.randrange(512),rng.randrange(512)
            for aa,bb in ((a,b),(b,a)):
                witness=self.library.plan(h,n,aa,bb)
                if witness is not None:
                    self.assertFalse(win(aa,bb));accepted+=1
                    check_witness(h,to_columns(h,n,{v for v in range(9) if aa>>v&1},{v for v in range(9) if bb>>v&1}),0,witness,self.library.tiles)
        self.assertGreater(accepted,20)

    def test_partial_library_fallback_all_schedulers(self):
        directory=Path(self.temp.name)/'partial-library'
        partial=Library([t for t in self.library.tiles.values() if t['doc']['width'] <= 2])
        partial.save(directory)
        self.assertTrue(coverage(partial,3,5)['uncovered'])
        solver=ROOT/'solver/target/release/col-rs'
        for mode,threads,split in [('off',1,False),('root',1,False),('root',2,False),('root',2,True),('search',1,False)]:
            path=Path(self.temp.name)/f'fallback-{mode}-{threads}-{split}.json'
            cmd=[str(solver),'--m','3','--n','5','--proof-mode',mode,'--threads',str(threads),
                 '--no-tablebase','--no-endgame-cache','--endgame-size','0','--no-component-reduction','--no-pairing-certificate']
            if mode!='off':cmd += ['--proof-library',str(directory),'--proof-out',str(path)]
            if split:cmd += ['--root-split']
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('3 x 5: P2 wins',result.stdout)
            if mode!='off':
                report=json.loads(path.read_text());check_report(report)
                self.assertEqual(report['outcome'],'unknown')
                if mode=='search':self.assertTrue(report['cutoffs'])

    def test_height_five_and_seven_seed_certificates(self):
        for h in (5,7):
            # A pair of adjacent cells supports an elementary responder strategy.
            doc,stats=generate_tile(h,1,3,3)
            self.assertEqual(stats['status'],'certified')
            lib=Library([dict(id='pair',source_sha256='',doc=doc)])
            a=b=3
            w=lib.plan(h,1,a,b)
            self.assertIsNotNone(w)
            check_witness(h,to_columns(h,1,{0,1},{0,1}),0,w,lib.tiles)

if __name__=='__main__':unittest.main()
