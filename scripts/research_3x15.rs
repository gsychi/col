//! Isolated, single-threaded, state-bounded experiments. Outputs no winner on cancellation.
use super::*;
use std::io::Write;
pub static LIMIT: AtomicU64 = AtomicU64::new(u64::MAX);
pub static ADMISSION: AtomicBool = AtomicBool::new(false);
pub static PROFILE: AtomicBool = AtomicBool::new(false);
pub static REJECTED: AtomicU64 = AtomicU64::new(0);
pub static FRAGMENT_MIN: AtomicU64 = AtomicU64::new(0);
pub static SEPARATOR: AtomicBool = AtomicBool::new(false);
pub static CUT_HITS: AtomicU64 = AtomicU64::new(0);
thread_local! {
    static TRACE: RefCell<Vec<(u64,u64,u8,u64,bool)>> = const {RefCell::new(Vec::new())};
    static CALLS: RefCell<u64> = const {RefCell::new(0)};
}
pub fn record(p1:u64,p2:u64,turn:u8,cost:u64) {
    let sampled = CALLS.with(|c| {let mut c=c.borrow_mut(); *c+=1; *c%64==0});
    if sampled || cost>=100 {
        TRACE.with(|v| v.borrow_mut().push((p1,p2,turn,cost,sampled)));
    }
}
pub fn run() {
    // N, state limit, memo bits, admission 0/1, position or empty, turn 0/1,
    // ordering legacy/heuristic, profile TSV or -, minimum memo live cells.
    let args:Vec<String>=std::env::args().collect();
    let n:usize=args[1].parse().unwrap();
    let limit:u64=args[2].parse().unwrap();
    let bits:u32=args[3].parse().unwrap();
    let admission=args[4]=="1";
    let turn:u8=args[6].parse().unwrap();
    let profile=args[8]!="-";
    let min_live:u32=args.get(9).map_or(0,|s|s.parse().unwrap());
    let mode=args.get(10).map_or("dfs",String::as_str);
    SEPARATOR.store(mode=="separator",Ordering::Relaxed);
    if let Some(min)=mode.strip_prefix("fragment-") {FRAGMENT_MIN.store(min.parse().unwrap(),Ordering::Relaxed);}
    assert!(n>0 && 3*n<=63 && (16..=28).contains(&bits) && turn<=1);
    LIMIT.store(limit,Ordering::Relaxed);
    ADMISSION.store(admission,Ordering::Relaxed);
    PROFILE.store(profile,Ordering::Relaxed);
    let board=Board::new(3,n);
    let ordering=if args[7]=="legacy" {ORDER_LEGACY} else {ORDER_HEURISTIC};
    let coord=Coordination::new(false,3,n,ordering,true,true,
        ComponentBagPolicy::default_profile(),0,false,mode=="native",mode=="charge");
    let memo=FixedMemo(RefCell::new(FixedTable::with_slots_log2(bits,board.num_cells)));
    let (p1,p2)=if args[5]=="empty" {(0,0)} else {parse_position(&args[5],&board)};
    let (l1,l2)=board.legal_masks_from_stones(p1,p2);
    let mut solver=Solver::new(&board,&memo,&coord,false,None,10,min_live,false);
    let start=Instant::now();
    let last=if p1!=0 {Some(63-p1.leading_zeros() as usize)} else {None};
    let mut pn=PnSearch {table:FxHashMap::default(),expanded:0,limit};
    let result=if mode=="dfpn" {pn.search(&mut solver,l1,l2,turn,last,INF,INF).and_then(|v| {
        if v.0==0 {Some(true)} else if v.1==0 {Some(false)} else {None}
    })} else {solver.is_winning(turn,board.shadow_key(l1,l2,turn),l1,l2,last,false)};
    let elapsed=start.elapsed().as_secs_f64();
    let stats=solver.take_stats();
    eprintln!("mode={mode} pn_expanded={} pn_entries={} native_states={} native_hits={} cut_hits={}",pn.expanded,pn.table.len(),stats.component_native_states,stats.component_native_memo_hits,CUT_HITS.load(Ordering::Relaxed));
    println!("{{\"n\":{n},\"limit\":{limit},\"memo_bits\":{bits},\"admission\":{admission},\"min_live\":{min_live},\"profile\":{profile},\"actor_wins\":{},\"states\":{},\"seconds\":{elapsed},\"memo_hits\":{},\"evictions\":{},\"rejected\":{},\"bag_queries\":{},\"bag_hits\":{}}}",
        result.map_or("null",|v|if v {"true"} else {"false"}),stats.states_searched,
        stats.memo_hits,memo.evictions(),REJECTED.load(Ordering::Relaxed),stats.component_bag_queries,stats.component_bag_hits);
    if profile {
        let file=std::fs::File::create(&args[8]).unwrap();
        let mut out=std::io::BufWriter::new(file);
        writeln!(out,"p1\tp2\tturn\tcost\tsampled\tcomponents\tlarge_size\tsmall_size\tcore\tpair\tcharge\tseparator").unwrap();
        let mut evaluator=EndgameEvaluator::new(10,None);
        TRACE.with(|v| for &(p1,p2,t,cost,sampled) in v.borrow().iter() {
            if let Some(row)=endgame::research_pair(&mut evaluator,n,p1,p2,t) {
                writeln!(out,"{p1}\t{p2}\t{t}\t{cost}\t{sampled}\t{row}").unwrap();
            }
        });
    }
}

const INF:u64=1u64<<60;
struct PnSearch {table:FxHashMap<u128,(u64,u64)>,expanded:u64,limit:u64}
impl PnSearch {
    fn search<M:Memo>(&mut self,s:&mut Solver<M>,a:u64,b:u64,t:u8,last:Option<usize>,phi:u64,delta:u64)->Option<(u64,u64)> {
        if s.stats.states_searched+self.expanded>=self.limit {return None;}
        let key=s.board.shadow_key(a,b,t);
        if let Some(v)=s.memo_get(key) {return Some(if v {(0,INF)} else {(INF,0)});}
        if let Some(&v)=self.table.get(&key) {if v.0==0||v.1==0 {return Some(v);}}
        if !self.table.contains_key(&key) {
            // Exact DFS is a leaf evaluator. Budget exhaustion is unknown, never a loss.
            LIMIT.store((s.stats.states_searched+128).min(self.limit-self.expanded),Ordering::Relaxed);
            let exact=s.is_winning(t,key,a,b,last,false);
            s.coord.cancel.store(false,Ordering::Relaxed);
            LIMIT.store(self.limit,Ordering::Relaxed);
            if let Some(v)=exact {
                let pair=if v {(0,INF)} else {(INF,0)};
                self.table.insert(key,pair);return Some(pair);
            }
            self.table.insert(key,(1,1));
        }
        self.expanded+=1;
        let legal=if t==0 {a} else {b};
        let mut seen=FxHashSet::default();
        let mut children=Vec::new();
        for bit in s.board.ordered_move_bits(t,legal,last,s.coord.active_order()) {
            let (ca,cb)=s.board.child_legals(a,b,t,bit);
            let ck=s.board.shadow_key(ca,cb,1-t);
            if seen.insert(ck) {children.push((ca,cb,ck,if t==0 {Some(bit.trailing_zeros() as usize)} else {last}));}
        }
        loop {
            if s.stats.states_searched+self.expanded>=self.limit {return None;}
            let mut values=Vec::new();
            for &(_,_,ck,_) in &children {
                let v=if let Some(w)=s.memo_get(ck) {if w {(0,INF)} else {(INF,0)}}
                    else {*self.table.get(&ck).unwrap_or(&(1,1))};
                values.push(v);
            }
            let proof=values.iter().map(|v|v.1).min().unwrap_or(INF);
            let disproof=values.iter().fold(0u64,|sum,v|(sum+v.0).min(INF));
            self.table.insert(key,(proof,disproof));
            if proof==0||disproof==0 {
                s.remember(key,a,b,proof==0);
                return Some((proof,disproof));
            }
            if proof>=phi||disproof>=delta {return Some((proof,disproof));}
            let chosen=values.iter().enumerate().min_by_key(|(_,v)|v.1).unwrap().0;
            let second=values.iter().enumerate().filter(|(i,_)|*i!=chosen).map(|(_,v)|v.1).min().unwrap_or(INF);
            let child_phi=if delta==INF {INF} else {delta-disproof+values[chosen].0};
            let child_delta=phi.min(second.saturating_add(1).min(INF));
            let (ca,cb,_,clast)=children[chosen];
            self.search(s,ca,cb,1-t,clast,child_phi,child_delta)?;
        }
    }
}
