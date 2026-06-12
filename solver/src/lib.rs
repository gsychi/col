//! DFS solver for the 2D m x n Col placement game.
//!
//! Shadow keying (memo on legal-move masks), geometric symmetry
//! canonicalization, center-first move ordering, the even-dimension
//! pairing theorem shortcut, parallel root opening split with a
//! shared concurrent memo, and a compact open-addressing memo table.

mod endgame;
mod tablebase;

use dashmap::DashMap;
use endgame::{EndgameEvaluator, EndgameStats, SharedEndgameCache};
use rustc_hash::{FxBuildHasher, FxHashMap, FxHashSet};
use std::cell::RefCell;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;

const P1: u8 = 0;
const P2: u8 = 1;

/// Per-byte lookup tables for a single symmetry transform.
struct ByteTransformTables {
    /// tables[byte_index][byte_value] -> contribution to transformed u64 mask
    tables: [[u64; 256]; 8],
}

struct Board {
    n: usize,
    num_cells: usize,
    all_cells_mask: u64,
    adjacency: Vec<u64>,
    move_order: Vec<(usize, u64)>,
    center_cell: Option<usize>,
    transform_byte_tables: Vec<ByteTransformTables>,
    has_even_dimension: bool,
}

impl Board {
    fn new(m: usize, n: usize) -> Board {
        assert!(m * n <= 63, "board too large for u64 masks");
        let num_cells = m * n;
        let all_cells_mask = (1u64 << num_cells) - 1;

        let mut adjacency = vec![0u64; num_cells];
        for row in 0..m {
            for col in 0..n {
                let cell = row * n + col;
                let mut mask = 0u64;
                if row > 0 {
                    mask |= 1 << (cell - n);
                }
                if row + 1 < m {
                    mask |= 1 << (cell + n);
                }
                if col > 0 {
                    mask |= 1 << (cell - 1);
                }
                if col + 1 < n {
                    mask |= 1 << (cell + 1);
                }
                adjacency[cell] = mask;
            }
        }

        let center_distance = |cell: usize| -> i64 {
            let row = (cell / n) as i64;
            let col = (cell % n) as i64;
            (2 * row - (m as i64 - 1)).abs() + (2 * col - (n as i64 - 1)).abs()
        };
        let mut order: Vec<usize> = (0..num_cells).collect();
        order.sort_by_key(|&cell| (-center_distance(cell), cell));
        let move_order = order.iter().map(|&cell| (cell, 1u64 << cell)).collect();

        let center_cell = if m % 2 == 1 && n % 2 == 1 {
            Some((m / 2) * n + n / 2)
        } else {
            None
        };
        let mut cell_maps: Vec<Vec<usize>> = Vec::new();
        {
            let mut push = |f: &dyn Fn(usize, usize) -> (usize, usize)| {
                let map: Vec<usize> = (0..num_cells)
                    .map(|cell| {
                        let (r, c) = f(cell / n, cell % n);
                        r * n + c
                    })
                    .collect();
                let identity: Vec<usize> = (0..num_cells).collect();
                if map != identity && !cell_maps.contains(&map) {
                    cell_maps.push(map);
                }
            };
            push(&|r, c| (m - 1 - r, c));
            push(&|r, c| (r, n - 1 - c));
            push(&|r, c| (m - 1 - r, n - 1 - c));
            if m == n {
                push(&|r, c| (c, n - 1 - r));
                push(&|r, c| (m - 1 - c, r));
                push(&|r, c| (c, r));
                push(&|r, c| (m - 1 - c, n - 1 - r));
            }
        }

        let transform_byte_tables = cell_maps
            .iter()
            .map(|cell_map| Self::build_byte_tables(cell_map, num_cells))
            .collect();

        Board {
            n,
            num_cells,
            all_cells_mask,
            adjacency,
            move_order,
            center_cell,
            transform_byte_tables,
            has_even_dimension: m % 2 == 0 || n % 2 == 0,
        }
    }

    fn build_byte_tables(cell_map: &[usize], num_cells: usize) -> ByteTransformTables {
        let mut tables = [[0u64; 256]; 8];
        for byte_idx in 0..8 {
            for byte_val in 0..256u16 {
                let mut out = 0u64;
                for bit in 0..8 {
                    if byte_val & (1 << bit) == 0 {
                        continue;
                    }
                    let cell = byte_idx * 8 + bit;
                    if cell >= num_cells {
                        continue;
                    }
                    out |= 1u64 << cell_map[cell];
                }
                tables[byte_idx][byte_val as usize] = out;
            }
        }
        ByteTransformTables { tables }
    }

    #[inline]
    fn transform_mask(&self, mask: u64, transform: &ByteTransformTables) -> u64 {
        let mut out = 0u64;
        for byte_idx in 0..8 {
            let byte_val = ((mask >> (byte_idx * 8)) & 0xFF) as usize;
            out |= transform.tables[byte_idx][byte_val];
        }
        out
    }

    fn canonical_legal_pair(&self, legal_p1: u64, legal_p2: u64) -> (u64, u64) {
        let mut best = (legal_p1, legal_p2);
        for transform in &self.transform_byte_tables {
            let t1 = self.transform_mask(legal_p1, transform);
            if t1 > best.0 {
                continue;
            }
            let t2 = self.transform_mask(legal_p2, transform);
            if t1 < best.0 || t2 < best.1 {
                best = (t1, t2);
            }
        }
        best
    }

    #[inline]
    fn shadow_key(&self, legal_p1: u64, legal_p2: u64, turn: u8) -> u128 {
        let (c1, c2) = self.canonical_legal_pair(legal_p1, legal_p2);
        ((c1 as u128) << (self.num_cells + 1)) | ((c2 as u128) << 1) | turn as u128
    }

    /// O(1) child legal masks after the current player plays `bit`.
    #[inline]
    fn child_legals(&self, p1_legal: u64, p2_legal: u64, turn: u8, bit: u64) -> (u64, u64) {
        let cell = bit.trailing_zeros() as usize;
        let blocked = bit | self.adjacency[cell];
        if turn == P1 {
            (p1_legal & !blocked, p2_legal & !bit)
        } else {
            (p1_legal & !bit, p2_legal & !blocked)
        }
    }
}

/// Win/loss memo shared by reference; interior mutability so the
/// sequential and concurrent implementations share one solver body.
trait Memo {
    fn get(&self, key: u128) -> Option<bool>;
    fn insert(&self, key: u128, value: bool);
    fn len(&self) -> usize;
    fn into_entries(self) -> Vec<(u128, bool)>;
}

/// Single-threaded memo: plain FxHashMap.
struct SeqMemo(RefCell<FxHashMap<u128, bool>>);

impl Memo for SeqMemo {
    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        self.0.borrow().get(&key).copied()
    }
    #[inline]
    fn insert(&self, key: u128, value: bool) {
        self.0.borrow_mut().insert(key, value);
    }
    fn len(&self) -> usize {
        self.0.borrow().len()
    }
    fn into_entries(self) -> Vec<(u128, bool)> {
        self.0.into_inner().into_iter().collect()
    }
}

/// Sentinel for an unused open-addressing slot. A real entry would need
/// shadow key 2^127-1 (all cells legal for both players with P2 to move),
/// which never occurs: P1 always moves first from the full board.
const EMPTY_SLOT: u128 = u128::MAX;

#[inline]
fn hash_key(key: u128) -> u64 {
    ((key as u64) ^ ((key >> 64) as u64)).wrapping_mul(0x9E37_79B9_7F4A_7C15)
}

/// Flat open-addressing table: one u128 per slot, key shifted left with
/// the win/loss bit stored in bit 0. ~16 bytes/slot vs hashbrown's wider
/// (key, value) buckets plus control bytes.
struct OpenTable {
    slots: Vec<u128>,
    shift: u32,
    len: usize,
    grow_at: usize,
}

impl OpenTable {
    fn with_capacity(min_entries: usize) -> OpenTable {
        let cap = (min_entries.max(1) * 2).next_power_of_two().max(1 << 16);
        OpenTable {
            slots: vec![EMPTY_SLOT; cap],
            shift: 64 - cap.trailing_zeros(),
            len: 0,
            grow_at: cap / 10 * 6,
        }
    }

    #[inline]
    fn slot_index(&self, key: u128) -> usize {
        (hash_key(key) >> self.shift) as usize
    }

    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        let mask = self.slots.len() - 1;
        let mut i = self.slot_index(key);
        loop {
            let slot = self.slots[i];
            if slot == EMPTY_SLOT {
                return None;
            }
            if slot >> 1 == key {
                return Some(slot & 1 == 1);
            }
            i = (i + 1) & mask;
        }
    }

    fn insert(&mut self, key: u128, value: bool) {
        debug_assert!(key >> 127 == 0, "shadow key must fit in 127 bits");
        if self.len >= self.grow_at {
            self.grow();
        }
        let mask = self.slots.len() - 1;
        let mut i = self.slot_index(key);
        loop {
            let slot = self.slots[i];
            if slot == EMPTY_SLOT {
                self.slots[i] = (key << 1) | value as u128;
                self.len += 1;
                return;
            }
            if slot >> 1 == key {
                self.slots[i] = (key << 1) | value as u128;
                return;
            }
            i = (i + 1) & mask;
        }
    }

    fn grow(&mut self) {
        let new_cap = self.slots.len() * 2;
        let old = std::mem::replace(&mut self.slots, vec![EMPTY_SLOT; new_cap]);
        self.shift = 64 - new_cap.trailing_zeros();
        self.grow_at = new_cap / 10 * 6;
        let mask = new_cap - 1;
        for slot in old {
            if slot == EMPTY_SLOT {
                continue;
            }
            let mut i = self.slot_index(slot >> 1);
            while self.slots[i] != EMPTY_SLOT {
                i = (i + 1) & mask;
            }
            self.slots[i] = slot;
        }
    }
}

/// Bounded transposition table: fixed slot count, bounded probe window,
/// replace-on-collision. RAM never grows; evicted entries are recomputed.
struct FixedTable {
    slots: Vec<u128>,
    shift: u32,
    mask: usize,
    len: usize,
}

const PROBE_WINDOW: usize = 8;

impl FixedTable {
    fn with_slots_log2(bits: u32) -> FixedTable {
        let cap = 1usize << bits;
        FixedTable {
            slots: vec![EMPTY_SLOT; cap],
            shift: 64 - bits,
            mask: cap - 1,
            len: 0,
        }
    }

    #[inline]
    fn slot_index(&self, key: u128) -> usize {
        (hash_key(key) >> self.shift) as usize
    }

    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        let base = self.slot_index(key);
        for offset in 0..PROBE_WINDOW {
            let slot = self.slots[(base + offset) & self.mask];
            if slot != EMPTY_SLOT && slot >> 1 == key {
                return Some(slot & 1 == 1);
            }
        }
        None
    }

    fn insert(&mut self, key: u128, value: bool) {
        let base = self.slot_index(key);
        let entry = (key << 1) | value as u128;
        for offset in 0..PROBE_WINDOW {
            let i = (base + offset) & self.mask;
            let slot = self.slots[i];
            if slot == EMPTY_SLOT {
                self.slots[i] = entry;
                self.len += 1;
                return;
            }
            if slot >> 1 == key {
                self.slots[i] = entry;
                return;
            }
        }
        // Window full of other keys: evict the base slot.
        self.slots[base] = entry;
    }
}

/// Single-threaded memo backed by the bounded replacement table.
struct FixedMemo(RefCell<FixedTable>);

impl Memo for FixedMemo {
    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        self.0.borrow().get(key)
    }
    #[inline]
    fn insert(&self, key: u128, value: bool) {
        self.0.borrow_mut().insert(key, value);
    }
    fn len(&self) -> usize {
        self.0.borrow().len
    }
    fn into_entries(self) -> Vec<(u128, bool)> {
        self.0
            .into_inner()
            .slots
            .into_iter()
            .filter(|&slot| slot != EMPTY_SLOT)
            .map(|slot| (slot >> 1, slot & 1 == 1))
            .collect()
    }
}

/// Single-threaded memo backed by the compact open-addressing table.
struct OpenMemo(RefCell<OpenTable>);

impl Memo for OpenMemo {
    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        self.0.borrow().get(key)
    }
    #[inline]
    fn insert(&self, key: u128, value: bool) {
        self.0.borrow_mut().insert(key, value);
    }
    fn len(&self) -> usize {
        self.0.borrow().len
    }
    fn into_entries(self) -> Vec<(u128, bool)> {
        self.0
            .into_inner()
            .slots
            .into_iter()
            .filter(|&slot| slot != EMPTY_SLOT)
            .map(|slot| (slot >> 1, slot & 1 == 1))
            .collect()
    }
}

/// Multi-threaded memo: sharded concurrent map. An entry inserted by
/// one worker is immediately visible to all others.
struct SharedMemo(DashMap<u128, bool, FxBuildHasher>);

impl Memo for SharedMemo {
    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        self.0.get(&key).map(|entry| *entry)
    }
    #[inline]
    fn insert(&self, key: u128, value: bool) {
        self.0.insert(key, value);
    }
    fn len(&self) -> usize {
        self.0.len()
    }
    fn into_entries(self) -> Vec<(u128, bool)> {
        self.0.into_iter().collect()
    }
}

/// Parallel bounded replacement memo. Exact keys, fixed RAM, shard-level locks.
/// Collisions evict entries, so missed entries are recomputed but results stay exact.
struct SharedFixedMemo {
    shards: Vec<Mutex<FixedTable>>,
    shard_mask: usize,
}

impl SharedFixedMemo {
    fn with_total_slots_log2(bits: u32) -> SharedFixedMemo {
        let shard_bits = (bits.saturating_sub(10)).min(6);
        let shard_count = 1usize << shard_bits;
        let table_bits = bits - shard_bits;
        let shards = (0..shard_count)
            .map(|_| Mutex::new(FixedTable::with_slots_log2(table_bits)))
            .collect();
        SharedFixedMemo {
            shards,
            shard_mask: shard_count - 1,
        }
    }

    #[inline]
    fn shard_index(&self, key: u128) -> usize {
        hash_key(key) as usize & self.shard_mask
    }
}

impl Memo for SharedFixedMemo {
    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        self.shards[self.shard_index(key)].lock().unwrap().get(key)
    }

    #[inline]
    fn insert(&self, key: u128, value: bool) {
        self.shards[self.shard_index(key)]
            .lock()
            .unwrap()
            .insert(key, value);
    }

    fn len(&self) -> usize {
        self.shards
            .iter()
            .map(|shard| shard.lock().unwrap().len)
            .sum()
    }

    fn into_entries(self) -> Vec<(u128, bool)> {
        let mut entries = Vec::new();
        for shard in self.shards {
            entries.extend(
                shard
                    .into_inner()
                    .unwrap()
                    .slots
                    .into_iter()
                    .filter(|&slot| slot != EMPTY_SLOT)
                    .map(|slot| (slot >> 1, slot & 1 == 1)),
            );
        }
        entries
    }
}

#[derive(Default)]
struct Stats {
    states_searched: u64,
    memo_hits: u64,
    endgame_hits: u64,
    endgame_raw_cache_hits: u64,
    endgame_canonical_cache_hits: u64,
    endgame_cgt_misses: u64,
    endgame_component_evaluations: u64,
}

impl Stats {
    fn add_endgame_stats(&mut self, endgame: EndgameStats) {
        self.endgame_raw_cache_hits += endgame.raw_cache_hits;
        self.endgame_canonical_cache_hits += endgame.canonical_cache_hits;
        self.endgame_cgt_misses += endgame.cgt_misses;
        self.endgame_component_evaluations += endgame.component_evaluations;
    }
}

/// Cross-thread coordination: aggregated progress counter, throttle for
/// progress lines, and a cancel flag set once the overall result is known.
struct Coordination {
    searched: AtomicU64,
    last_report_ms: AtomicU64,
    cancel: AtomicBool,
    started: Instant,
}

impl Coordination {
    fn new() -> Coordination {
        Coordination {
            searched: AtomicU64::new(0),
            last_report_ms: AtomicU64::new(0),
            cancel: AtomicBool::new(false),
            started: Instant::now(),
        }
    }
}

const FLUSH_INTERVAL: u64 = 32768;

struct Solver<'a, M: Memo> {
    board: &'a Board,
    memo: &'a M,
    coord: &'a Coordination,
    stats: Stats,
    progress: bool,
    endgame: Option<EndgameEvaluator>,
    /// Positions with fewer combined legal cells than this are not
    /// memoized (cheap to recompute; they dominate entry counts).
    memo_min_legal: u32,
}

impl<'a, M: Memo> Solver<'a, M> {
    fn new(
        board: &'a Board,
        memo: &'a M,
        coord: &'a Coordination,
        progress: bool,
        shared_endgame: Option<Arc<SharedEndgameCache>>,
        endgame_size: u32,
        memo_min_legal: u32,
    ) -> Self {
        let endgame =
            (endgame_size > 0).then(|| EndgameEvaluator::new(endgame_size, shared_endgame));
        Solver {
            board,
            memo,
            coord,
            stats: Stats::default(),
            progress,
            endgame,
            memo_min_legal,
        }
    }

    #[inline]
    fn remember(&self, key: u128, p1_legal: u64, p2_legal: u64, value: bool) {
        if (p1_legal | p2_legal).count_ones() >= self.memo_min_legal {
            self.memo.insert(key, value);
        }
    }

    fn take_stats(&mut self) -> Stats {
        let mut stats = std::mem::take(&mut self.stats);
        if let Some(endgame) = &self.endgame {
            stats.add_endgame_stats(endgame.stats());
        }
        stats
    }

    /// Returns None if the search was cancelled by another worker.
    fn is_winning(&mut self, turn: u8, key: u128, p1_legal: u64, p2_legal: u64) -> Option<bool> {
        if let Some(cached) = self.memo.get(key) {
            self.stats.memo_hits += 1;
            return Some(cached);
        }

        self.stats.states_searched += 1;
        if self.stats.states_searched % FLUSH_INTERVAL == 0 {
            if self.coord.cancel.load(Ordering::Relaxed) {
                return None;
            }
            self.coord
                .searched
                .fetch_add(FLUSH_INTERVAL, Ordering::Relaxed);
            if self.progress {
                self.maybe_report();
            }
        }

        let legal_mask = if turn == P1 { p1_legal } else { p2_legal };
        if legal_mask == 0 {
            self.remember(key, p1_legal, p2_legal, false);
            return Some(false);
        }
        if let Some(endgame) = self.endgame.as_mut() {
            if let Some(wins) = endgame.try_evaluate(
                self.board.n,
                &self.board.adjacency,
                p1_legal,
                p2_legal,
                turn,
            ) {
                self.stats.endgame_hits += 1;
                self.remember(key, p1_legal, p2_legal, wins);
                return Some(wins);
            }
        }

        let next_turn = 1 - turn;

        let preferred = match (turn, self.board.center_cell) {
            (P1, Some(center)) if legal_mask & (1u64 << center) != 0 => Some(center),
            _ => None,
        };

        let moves = self.ordered_moves(legal_mask, preferred);
        for (_cell, bit) in moves {
            let (child_p1_legal, child_p2_legal) =
                self.board.child_legals(p1_legal, p2_legal, turn, bit);
            let child_legal = if next_turn == P1 {
                child_p1_legal
            } else {
                child_p2_legal
            };
            if child_legal == 0 {
                self.remember(key, p1_legal, p2_legal, true);
                return Some(true);
            }

            let child_key = self
                .board
                .shadow_key(child_p1_legal, child_p2_legal, next_turn);

            if let Some(cached_child) = self.memo.get(child_key) {
                self.stats.memo_hits += 1;
                if !cached_child {
                    self.remember(key, p1_legal, p2_legal, true);
                    return Some(true);
                }
                continue;
            }

            let opponent_wins =
                self.is_winning(next_turn, child_key, child_p1_legal, child_p2_legal)?;
            if !opponent_wins {
                self.remember(key, p1_legal, p2_legal, true);
                return Some(true);
            }
        }

        self.remember(key, p1_legal, p2_legal, false);
        Some(false)
    }

    fn ordered_moves(
        &self,
        legal_mask: u64,
        preferred: Option<usize>,
    ) -> Vec<(usize, u64)> {
        let mut moves = Vec::new();
        if let Some(preferred_cell) = preferred {
            moves.push((preferred_cell, 1u64 << preferred_cell));
        }
        for &(cell, bit) in &self.board.move_order {
            if Some(cell) == preferred || legal_mask & bit == 0 {
                continue;
            }
            moves.push((cell, bit));
        }
        moves
    }

    /// Print at most one progress line per ~250ms across all workers.
    fn maybe_report(&self) {
        let elapsed_ms = self.coord.started.elapsed().as_millis() as u64;
        let last = self.coord.last_report_ms.load(Ordering::Relaxed);
        if elapsed_ms.saturating_sub(last) < 250 {
            return;
        }
        if self
            .coord
            .last_report_ms
            .compare_exchange(last, elapsed_ms, Ordering::Relaxed, Ordering::Relaxed)
            .is_err()
        {
            return;
        }
        let searched = self.coord.searched.load(Ordering::Relaxed);
        let elapsed = elapsed_ms as f64 / 1000.0;
        let rate = searched as f64 / (elapsed_ms as f64 / 1000.0).max(1e-9);
        let line = format!(
            "states searched: {searched} | memo: {} | {rate:.0}/s | {elapsed:.1}s",
            self.memo.len(),
        );
        eprint!("\r{line:<80}");
    }
}

/// Symmetry-distinct P1 openings, each a self-contained subtree:
/// (child shadow key, child P1 legal, child P2 legal).
fn distinct_openings(board: &Board) -> Vec<(u128, u64, u64)> {
    let legal = board.all_cells_mask;
    let mut seen: FxHashSet<u128> = FxHashSet::default();
    let mut openings = Vec::new();
    let mut emit = |bit: u64| {
        let (c1, c2) = board.child_legals(legal, legal, P1, bit);
        let key = board.shadow_key(c1, c2, P2);
        if seen.insert(key) {
            openings.push((key, c1, c2));
        }
    };
    if let Some(center) = board.center_cell {
        emit(1u64 << center);
    }
    for &(cell, bit) in &board.move_order {
        if Some(cell) == board.center_cell {
            continue;
        }
        emit(bit);
    }
    openings
}

struct SolveOutput {
    p1_wins: bool,
    stats: Stats,
    entries: Vec<(u128, bool)>,
}

fn run_sequential<M: Memo>(
    board: &Board,
    memo: M,
    progress: bool,
    endgame_size: u32,
    memo_min_legal: u32,
) -> SolveOutput {
    let coord = Coordination::new();
    let legal = board.all_cells_mask;
    let key = board.shadow_key(legal, legal, P1);
    let shared_endgame = (endgame_size > 0).then(|| Arc::new(SharedEndgameCache::new()));
    let mut solver = Solver::new(
        board,
        &memo,
        &coord,
        progress,
        shared_endgame,
        endgame_size,
        memo_min_legal,
    );
    let p1_wins = solver
        .is_winning(P1, key, legal, legal)
        .expect("sequential search cannot be cancelled");
    let stats = solver.take_stats();
    drop(solver);
    // Root must always be present so re-runs answer instantly.
    memo.insert(key, p1_wins);
    SolveOutput {
        p1_wins,
        stats,
        entries: memo.into_entries(),
    }
}

/// Parallel root split: one task per symmetry-distinct P1 opening.
/// Preserves sequential early-exit semantics within each opening subtree.
fn solve_parallel_root<M: Memo + Sync>(
    board: &Board,
    threads: usize,
    progress: bool,
    endgame_size: u32,
    memo: M,
    memo_min_legal: u32,
) -> SolveOutput {
    let coord = Coordination::new();
    let openings = distinct_openings(board);
    let legal = board.all_cells_mask;
    let root_key = board.shadow_key(legal, legal, P1);
    let shared_endgame = (endgame_size > 0).then(|| Arc::new(SharedEndgameCache::new()));
    let next_opening = AtomicUsize::new(0);
    let p1_wins = AtomicBool::new(false);
    let total = std::sync::Mutex::new(Stats::default());

    std::thread::scope(|scope| {
        for _ in 0..threads {
            scope.spawn(|| {
                let mut solver = Solver::new(
                    board,
                    &memo,
                    &coord,
                    progress,
                    shared_endgame.clone(),
                    endgame_size,
                    memo_min_legal,
                );
                loop {
                    if coord.cancel.load(Ordering::Relaxed) {
                        break;
                    }
                    let i = next_opening.fetch_add(1, Ordering::Relaxed);
                    if i >= openings.len() {
                        break;
                    }
                    let (key, c1, c2) = openings[i];
                    match solver.is_winning(P2, key, c1, c2) {
                        // P2 to move loses this opening => P1 wins the game.
                        Some(false) => {
                            p1_wins.store(true, Ordering::Relaxed);
                            coord.cancel.store(true, Ordering::Relaxed);
                            break;
                        }
                        Some(true) => {}
                        None => break,
                    }
                }
                let stats = solver.take_stats();
                let mut total = total.lock().unwrap();
                total.states_searched += stats.states_searched;
                total.memo_hits += stats.memo_hits;
                total.endgame_hits += stats.endgame_hits;
                total.endgame_raw_cache_hits += stats.endgame_raw_cache_hits;
                total.endgame_canonical_cache_hits += stats.endgame_canonical_cache_hits;
                total.endgame_cgt_misses += stats.endgame_cgt_misses;
                total.endgame_component_evaluations += stats.endgame_component_evaluations;
            });
        }
    });

    let mut stats = total.into_inner().unwrap();
    stats.states_searched += 1;
    let p1_wins = p1_wins.load(Ordering::Relaxed);
    memo.insert(root_key, p1_wins);
    SolveOutput {
        p1_wins,
        stats,
        entries: memo.into_entries(),
    }
}

pub fn run(args: Vec<String>) {
    let mut m = 0usize;
    let mut n = 0usize;
    let mut progress = false;
    let mut tablebase_enabled = true;
    let mut tablebase_dir = PathBuf::from("data/tablebases");
    let mut memo_kind = String::from("open");
    let mut memo_min_legal = 0u32;
    let mut memo_bits = 0u32;
    let mut endgame_size = 10u32;
    let mut threads = std::thread::available_parallelism()
        .map(|p| p.get())
        .unwrap_or(1);
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--m" => {
                m = args[i + 1].parse().expect("bad --m");
                i += 2;
            }
            "--n" => {
                n = args[i + 1].parse().expect("bad --n");
                i += 2;
            }
            "--threads" => {
                threads = args[i + 1].parse().expect("bad --threads");
                i += 2;
            }
            "--memo" => {
                memo_kind = args[i + 1].clone();
                i += 2;
            }
            "--memo-min-legal" => {
                memo_min_legal = args[i + 1].parse().expect("bad --memo-min-legal");
                i += 2;
            }
            "--memo-bits" => {
                memo_bits = args[i + 1].parse().expect("bad --memo-bits");
                i += 2;
            }
            "--endgame-size" => {
                endgame_size = args[i + 1].parse().expect("bad --endgame-size");
                i += 2;
            }
            "--tablebase-dir" => {
                tablebase_dir = PathBuf::from(&args[i + 1]);
                i += 2;
            }
            "--no-tablebase" => {
                tablebase_enabled = false;
                i += 1;
            }
            "--progress" => {
                progress = true;
                i += 1;
            }
            other => panic!("unknown arg {other}"),
        }
    }
    assert!(
        m > 0 && n > 0,
        "usage: col-rs --m M --n N [--threads T] [--memo open|hash|fixed] [--memo-min-legal K] [--memo-bits K] [--endgame-size K] [--tablebase-dir DIR] [--no-tablebase] [--progress]"
    );
    assert!(threads > 0, "--threads must be >= 1");
    assert!(
        memo_kind == "open" || memo_kind == "hash" || memo_kind == "fixed",
        "--memo must be open, hash, or fixed"
    );
    if memo_kind == "fixed" {
        assert!(
            (16..=34).contains(&memo_bits),
            "--memo fixed requires --memo-bits 16..=34 (table has 2^bits slots, 16 bytes each)"
        );
    }

    let (m, n) = if m > n { (n, m) } else { (m, n) };
    let board = Board::new(m, n);
    let legal = board.all_cells_mask;
    let root_key = board.shadow_key(legal, legal, P1);

    let loaded = if tablebase_enabled {
        tablebase::load(&tablebase_dir, m, n).unwrap_or_else(|err| {
            eprintln!("warning: could not load tablebase: {err}");
            FxHashMap::default()
        })
    } else {
        FxHashMap::default()
    };
    let loaded_count = loaded.len();
    let cached_root = loaded.get(&root_key).copied();

    let start = Instant::now();
    let (output, searched_fresh) = if board.has_even_dimension {
        (
            SolveOutput {
                p1_wins: false,
                stats: Stats::default(),
                entries: Vec::new(),
            },
            false,
        )
    } else if let Some(p1_wins) = cached_root {
        (
            SolveOutput {
                p1_wins,
                stats: Stats::default(),
                entries: Vec::new(),
            },
            false,
        )
    } else if threads == 1 {
        let output = match memo_kind.as_str() {
            "open" => {
                let mut table = OpenTable::with_capacity(loaded_count);
                for (key, value) in loaded {
                    table.insert(key, value);
                }
                run_sequential(
                    &board,
                    OpenMemo(RefCell::new(table)),
                    progress,
                    endgame_size,
                    memo_min_legal,
                )
            }
            "fixed" => {
                let mut table = FixedTable::with_slots_log2(memo_bits);
                for (key, value) in loaded {
                    table.insert(key, value);
                }
                run_sequential(
                    &board,
                    FixedMemo(RefCell::new(table)),
                    progress,
                    endgame_size,
                    memo_min_legal,
                )
            }
            _ => run_sequential(
                &board,
                SeqMemo(RefCell::new(loaded)),
                progress,
                endgame_size,
                memo_min_legal,
            ),
        };
        (output, true)
    } else {
        let output = if memo_kind == "fixed" {
            let memo = SharedFixedMemo::with_total_slots_log2(memo_bits);
            for (key, value) in loaded {
                memo.insert(key, value);
            }
            solve_parallel_root(
                &board,
                threads,
                progress,
                endgame_size,
                memo,
                memo_min_legal,
            )
        } else {
            let memo = SharedMemo(DashMap::with_hasher(FxBuildHasher));
            for (key, value) in loaded {
                memo.insert(key, value);
            }
            solve_parallel_root(
                &board,
                threads,
                progress,
                endgame_size,
                memo,
                memo_min_legal,
            )
        };
        (output, true)
    };
    let elapsed = start.elapsed().as_secs_f64();
    if progress {
        eprintln!();
    }

    let memo_entries = output.entries.len();
    let saved_path = if tablebase_enabled && searched_fresh && !output.entries.is_empty() {
        match tablebase::save(&tablebase_dir, m, n, output.entries) {
            Ok(path) => Some(path),
            Err(err) => {
                eprintln!("warning: could not save tablebase: {err}");
                None
            }
        }
    } else {
        None
    };

    println!(
        "{} x {}: {} wins",
        m,
        n,
        if output.p1_wins { "P1" } else { "P2" }
    );
    println!(
        "solver: rust DFS (shadow keys, {} thread{}, {} memo{})",
        threads,
        if threads == 1 { "" } else { "s" },
        if threads == 1 {
            memo_kind.as_str()
        } else if memo_kind == "fixed" {
            "fixed"
        } else {
            "dashmap"
        },
        if memo_min_legal > 0 {
            format!(", min-legal {memo_min_legal}")
        } else if endgame_size > 0 {
            format!(", endgame-size {endgame_size}")
        } else {
            String::new()
        },
    );
    println!("states searched: {}", output.stats.states_searched);
    println!("memo hits: {}", output.stats.memo_hits);
    if endgame_size > 0 {
        println!("endgame hits: {}", output.stats.endgame_hits);
        println!(
            "endgame raw cache hits: {}",
            output.stats.endgame_raw_cache_hits
        );
        println!(
            "endgame canonical cache hits: {}",
            output.stats.endgame_canonical_cache_hits
        );
        println!("endgame cgt misses: {}", output.stats.endgame_cgt_misses);
        println!(
            "endgame component evals: {}",
            output.stats.endgame_component_evaluations
        );
    }
    if tablebase_enabled && loaded_count > 0 {
        println!("tablebase loaded: {loaded_count} entries");
    }
    println!("memo entries: {memo_entries}");
    if let Some(path) = saved_path {
        let file_size = std::fs::metadata(&path).map(|meta| meta.len()).unwrap_or(0);
        println!(
            "tablebase saved: {} ({:.2} MB)",
            path.display(),
            file_size as f64 / 1_048_576.0
        );
    }
    let rate = output.stats.states_searched as f64 / elapsed.max(1e-9);
    println!("states per second: {:.0}", rate);
    println!("time elapsed: {:.6}s", elapsed);
}
