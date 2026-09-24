#!/usr/bin/env python3
"""Create an isolated, budgeted raw-permission research copy of the Rust solver.

Production sources are read-only. Results are discovery unless independently
certified; cancellation is emitted as null, never as a losing root.
"""
from pathlib import Path
import hashlib,json,shutil,sys
root=Path(__file__).resolve().parents[3]
dest=Path(sys.argv[1]).resolve()
dest.mkdir(parents=True,exist_ok=True)
shutil.copytree(root/'solver/src',dest/'src',dirs_exist_ok=True)
for name in ('Cargo.toml','Cargo.lock'):shutil.copy2(root/'solver'/name,dest/name)
p=dest/'src/lib.rs';source=p.read_text();original=hashlib.sha256(source.encode()).hexdigest()
source=source.replace('mod endgame;','mod endgame;\npub mod raw_research;',1)
needle='        self.stats.states_searched += 1;'
assert source.count(needle)==1
source=source.replace(needle,'''        if self.stats.states_searched >= raw_research::LIMIT.load(Ordering::Relaxed) {
            self.coord.cancel.store(true, Ordering::Relaxed);
            return false;
        }
'''+needle,1)
p.write_text(source)
(dest/'src/raw_research.rs').write_text('''use super::*;
pub static LIMIT: AtomicU64 = AtomicU64::new(u64::MAX);
pub fn run() {
 let args:Vec<String>=std::env::args().collect();
 assert!(args.len()==7 || args.len()==8);
 let m:usize=args[1].parse().unwrap(); let n:usize=args[2].parse().unwrap();
 let a:u64=args[3].parse().unwrap();let b:u64=args[4].parse().unwrap();
 let turn:u8=args[5].parse().unwrap();let budget:u64=args[6].parse().unwrap();
 let cutoff:u32=args.get(7).map_or(10,|s|s.parse().unwrap());
 let board=Board::new(m,n);assert!(turn<=1 && (a|b)&!board.all_cells_mask==0);
 LIMIT.store(budget,Ordering::Relaxed);
 let coord=Coordination::new(false,m,n,ORDER_HEURISTIC,true,true,ComponentBagPolicy::default_profile(),0,false,false,false);
 let memo=FixedMemo(RefCell::new(FixedTable::with_slots_log2(22,board.num_cells)));
 let mut solver=Solver::new(&board,&memo,&coord,false,None,cutoff,0,false);
 let start=Instant::now();
 let result=solver.is_winning(turn,board.shadow_key(a,b,turn),a,b,None,false);
 let stats=solver.take_stats();
 println!("{}",serde_json::json!({"height":m,"width":n,"blue":a,"white":b,"turn":turn,"budget":budget,"actor_wins":result,"states":stats.states_searched,"memo_hits":stats.memo_hits,"seconds":start.elapsed().as_secs_f64()}));
}
''')
(dest/'src/bin/raw_research.rs').write_text('fn main() { col_rs::raw_research::run(); }\n')
(dest/'raw_provenance.json').write_text(json.dumps({'production_source':str(root/'solver/src/lib.rs'),'original_sha256':original,'scope':'Isolated raw-permission discovery, no theorem from sampled widths'},indent=2)+'\n')
print(dest)
