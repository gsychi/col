"""Build an isolated research copy; never rewrite the production solver.

Usage: python3 scripts/prepare_3x15_research.py /private/tmp/col-3x15-research
Then: cargo build --release --offline --manifest-path DEST/Cargo.toml --bin research
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
dest = Path(sys.argv[1]).resolve()
dest.mkdir(parents=True, exist_ok=True)
shutil.copytree(root / "solver/src", dest / "src", dirs_exist_ok=True)
for name in ("Cargo.toml", "Cargo.lock"):
    shutil.copy2(root / "solver" / name, dest / name)
source = (dest / "src/lib.rs").read_text()
source_hash = hashlib.sha256(source.encode()).hexdigest()
source = source.replace("mod endgame;", "mod endgame;\npub mod research;")
source = source.replace("        self.stats.states_searched += 1;", """        if self.stats.states_searched >= research::LIMIT.load(Ordering::Relaxed) {
            self.coord.cancel.store(true, Ordering::Relaxed);
            return false;
        }
        self.stats.states_searched += 1;""", 1)
source = source.replace("    fn is_winning(\n", """    fn is_winning(&mut self, turn: u8, key: u128, p1: u64, p2: u64,
        last: Option<usize>, miss: bool) -> Option<bool> {
        let before = self.stats.states_searched;
        let result = self.is_winning_inner(turn, key, p1, p2, last, miss);
        if research::PROFILE.load(Ordering::Relaxed) && result.is_some() {
            research::record(p1, p2, turn, self.stats.states_searched - before);
        }
        result
    }

    fn is_winning_inner(
""", 1)
needle = "        self.evictions += 1;\n        self.slots[victim] = entry;"
assert source.count(needle) == 1
source = source.replace(needle, """        if research::ADMISSION.load(Ordering::Relaxed) && self.priority(key) < victim_priority {
            research::REJECTED.fetch_add(1, Ordering::Relaxed);
            return;
        }
""" + needle)
needle = "        for (rank, bit) in moves.enumerate() {"
assert source.count(needle)==1
source=source.replace(needle,"""        let mut move_list: Vec<u64> = moves.collect();
        let fragment_min=research::FRAGMENT_MIN.load(Ordering::Relaxed);
        if fragment_min>0 && (p1_legal|p2_legal).count_ones() as u64 >= fragment_min {
            move_list.sort_by_cached_key(|bit| {
                let (a,b)=board.child_legals(p1_legal,p2_legal,turn,*bit);
                endgame::research_fragment_score(board.n,a,b)
            });
        }
        for (rank, bit) in move_list.into_iter().enumerate() {""")
needle="        if self.coord.component_native_one_large {"
assert source.count(needle)==1
source=source.replace(needle,"""        if research::SEPARATOR.load(Ordering::Relaxed) && (p1_legal|p2_legal).count_ones()<=32 {
            if let Some(wins)=endgame::research_separator_bound(self.endgame.as_mut().unwrap(),
                self.board.n,p1_legal,p2_legal,turn) {
                research::CUT_HITS.fetch_add(1,Ordering::Relaxed);
                self.remember_component_bag(&mut component_bag_key,wins);
                self.remember(key,p1_legal,p2_legal,wins);
                return Some(wins);
            }
        }
"""+needle)
(dest / "src/lib.rs").write_text(source)
shutil.copy2(root / "scripts/research_3x15.rs", dest / "src/research.rs")
with (dest / "src/endgame.rs").open("a") as f:
    f.write((root / "scripts/research_3x15_endgame.rs").read_text())
(dest / "src/bin/research.rs").write_text("fn main() { col_rs::research::run(); }\n")
(dest / "provenance.json").write_text(json.dumps({"source": str(root), "lib_sha256": source_hash}, indent=2))
print(dest)
