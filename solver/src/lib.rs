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
use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicU8, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;

const P1: u8 = 0;
const P2: u8 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum MoveOrdering {
    Legacy,
    Heuristic,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum MoveOrderSpec {
    Auto,
    Legacy,
    Heuristic,
}

impl MoveOrderSpec {
    fn parse(s: &str) -> MoveOrderSpec {
        match s {
            "auto" => MoveOrderSpec::Auto,
            "legacy" => MoveOrderSpec::Legacy,
            "heuristic" => MoveOrderSpec::Heuristic,
            other => panic!("--move-order must be auto, legacy, or heuristic, got {other}"),
        }
    }

    fn default_for_board(_m: usize, _n: usize) -> MoveOrderSpec {
        MoveOrderSpec::Auto
    }
}

/// Runtime move order; may change mid-solve when `--move-order auto`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ActiveOrder {
    Legacy,
    Heuristic { p2_mirror: bool },
}

const ORDER_LEGACY: u8 = 0;
const ORDER_HEURISTIC: u8 = 1;
const ORDER_HEURISTIC_NO_MIRROR: u8 = 2;

fn active_order_from_code(code: u8) -> ActiveOrder {
    match code {
        ORDER_LEGACY => ActiveOrder::Legacy,
        ORDER_HEURISTIC_NO_MIRROR => ActiveOrder::Heuristic { p2_mirror: false },
        _ => ActiveOrder::Heuristic { p2_mirror: true },
    }
}

fn order_mode_label(code: u8) -> &'static str {
    match code {
        ORDER_LEGACY => "legacy",
        ORDER_HEURISTIC_NO_MIRROR => "heuristic (no P2 mirror)",
        _ => "heuristic",
    }
}

impl MoveOrdering {
    fn parse(s: &str) -> MoveOrdering {
        match s {
            "legacy" => MoveOrdering::Legacy,
            "heuristic" => MoveOrdering::Heuristic,
            other => panic!("--move-order must be auto, legacy, or heuristic, got {other}"),
        }
    }
}

impl ActiveOrder {
    fn from_fixed(ordering: MoveOrdering) -> ActiveOrder {
        match ordering {
            MoveOrdering::Legacy => ActiveOrder::Legacy,
            MoveOrdering::Heuristic => ActiveOrder::Heuristic { p2_mirror: true },
        }
    }
}

/// Per-byte lookup tables for a single symmetry transform.
struct ByteTransformTables {
    /// tables[byte_index][byte_value] -> contribution to transformed u64 mask
    tables: [[u64; 256]; 8],
}

struct Board {
    m: usize,
    n: usize,
    num_cells: usize,
    all_cells_mask: u64,
    adjacency: Vec<u64>,
    move_order: Vec<(usize, u64)>,
    p1_order: Vec<(usize, u64)>,
    p2_order: Vec<(usize, u64)>,
    reflected_cell: Vec<usize>,
    corners: Vec<usize>,
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

        let reflected_cell: Vec<usize> = (0..num_cells)
            .map(|cell| {
                let row = cell / n;
                let col = cell % n;
                (m - 1 - row) * n + (n - 1 - col)
            })
            .collect();

        let is_corner = |cell: usize| -> bool {
            let row = cell / n;
            let col = cell % n;
            (row == 0 || row + 1 == m) && (col == 0 || col + 1 == n)
        };
        let is_edge = |cell: usize| -> bool {
            let row = cell / n;
            let col = cell % n;
            row == 0 || row + 1 == m || col == 0 || col + 1 == n
        };
        let middle_row = if m % 2 == 1 { Some(m / 2) } else { None };

        let mut corners: Vec<usize> = (0..num_cells).filter(|&cell| is_corner(cell)).collect();
        corners.sort_unstable();

        let mut p1_ranked: Vec<(i64, usize)> = (0..num_cells)
            .map(|cell| {
                let row = cell / n;
                let degree = adjacency[cell].count_ones() as i64;
                let mut score = degree * 100;
                score -= center_distance(cell);
                if middle_row == Some(row) {
                    score += 50;
                }
                if is_corner(cell) {
                    score -= 500;
                } else if is_edge(cell) {
                    score -= 100;
                }
                (score, cell)
            })
            .collect();
        p1_ranked.sort_by(|a, b| b.cmp(a).then_with(|| a.1.cmp(&b.1)));
        let p1_order = p1_ranked
            .iter()
            .map(|&(_, cell)| (cell, 1u64 << cell))
            .collect();

        let mut p2_ranked: Vec<(i64, usize)> = (0..num_cells)
            .map(|cell| {
                let degree = adjacency[cell].count_ones() as i64;
                let mut score = 0i64;
                if is_corner(cell) {
                    score += 300;
                } else if is_edge(cell) {
                    score += 150;
                }
                score += center_distance(cell);
                score -= degree * 10;
                (score, cell)
            })
            .collect();
        p2_ranked.sort_by(|a, b| b.cmp(a).then_with(|| a.1.cmp(&b.1)));
        let p2_order = p2_ranked
            .iter()
            .map(|&(_, cell)| (cell, 1u64 << cell))
            .collect();

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
            m,
            n,
            num_cells,
            all_cells_mask,
            adjacency,
            move_order,
            p1_order,
            p2_order,
            reflected_cell,
            corners,
            center_cell,
            transform_byte_tables,
            has_even_dimension: m % 2 == 0 || n % 2 == 0,
        }
    }

    fn p2_preferred(
        &self,
        legal: u64,
        last_p1_move: Option<usize>,
        mirror: bool,
    ) -> Option<usize> {
        if !mirror {
            return None;
        }
        if let (Some(center), Some(last)) = (self.center_cell, last_p1_move) {
            if last == center {
                for &cell in &self.corners {
                    if legal & (1u64 << cell) != 0 {
                        return Some(cell);
                    }
                }
                return None;
            }
        }
        if let Some(last) = last_p1_move {
            let mirror_cell = self.reflected_cell[last];
            if legal & (1u64 << mirror_cell) != 0 {
                return Some(mirror_cell);
            }
        }
        None
    }

    fn ordered_move_bits(
        &self,
        turn: u8,
        legal: u64,
        last_p1_move: Option<usize>,
        ordering: ActiveOrder,
    ) -> Vec<u64> {
        match ordering {
            ActiveOrder::Legacy => {
                let preferred = match (turn, self.center_cell) {
                    (P1, Some(center)) if legal & (1u64 << center) != 0 => Some(center),
                    _ => None,
                };
                legacy_move_bits(self, legal, preferred)
            }
            ActiveOrder::Heuristic { p2_mirror: false } if turn == P1 => {
                heuristic_move_bits(self, legal, None, &self.p1_order)
            }
            ActiveOrder::Heuristic { p2_mirror: false } => {
                heuristic_move_bits(self, legal, None, &self.p2_order)
            }
            ActiveOrder::Heuristic { p2_mirror: true } if turn == P1 => {
                heuristic_move_bits(self, legal, None, &self.p1_order)
            }
            ActiveOrder::Heuristic { p2_mirror: true } => {
                let preferred = self.p2_preferred(legal, last_p1_move, true);
                heuristic_move_bits(self, legal, preferred, &self.p2_order)
            }
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

const FLUSH_INTERVAL: u64 = 32768;
const ORDER_RANK_BUCKETS: usize = 32;
const GAME_PHASE_COUNT: usize = 3;

/// Game phase from share of cells still playable for at least one player.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum GamePhase {
    Opening,
    Midgame,
    Endgame,
}

impl GamePhase {
    fn from_open_cells(open_cells: u32, num_cells: usize) -> GamePhase {
        let pct = open_cells as f64 / num_cells as f64 * 100.0;
        if pct > 66.0 {
            GamePhase::Opening
        } else if pct > 33.0 {
            GamePhase::Midgame
        } else {
            GamePhase::Endgame
        }
    }

    fn index(self) -> usize {
        match self {
            GamePhase::Opening => 0,
            GamePhase::Midgame => 1,
            GamePhase::Endgame => 2,
        }
    }

    fn label(self) -> &'static str {
        match self {
            GamePhase::Opening => "opening (>66% open)",
            GamePhase::Midgame => "midgame (33-66% open)",
            GamePhase::Endgame => "endgame (<=33% open)",
        }
    }
}

#[derive(Default, Clone, Copy)]
struct PhaseOrderStats {
    win_decisions: u64,
    win_rank_sum: u64,
    rank0: u64,
    legal_at_win_sum: u64,
}

impl PhaseOrderStats {
    fn record_win(&mut self, rank: usize, legal_count: usize) {
        self.win_decisions += 1;
        self.win_rank_sum += rank as u64;
        if rank == 0 {
            self.rank0 += 1;
        }
        self.legal_at_win_sum += legal_count as u64;
    }

    fn merge(&mut self, other: &PhaseOrderStats) {
        self.win_decisions += other.win_decisions;
        self.win_rank_sum += other.win_rank_sum;
        self.rank0 += other.rank0;
        self.legal_at_win_sum += other.legal_at_win_sum;
    }
}

/// Move-ordering quality: rank of the first winning move tried at OR nodes.
#[derive(Default, Clone, Copy)]
struct OrderStats {
    win_decisions: u64,
    win_rank_sum: u64,
    legal_at_win_sum: u64,
    win_rank_hist: [u64; ORDER_RANK_BUCKETS],
    by_phase: [PhaseOrderStats; GAME_PHASE_COUNT],
}

impl OrderStats {
    fn record_win(&mut self, rank: usize, legal_count: usize, phase: GamePhase) {
        self.win_decisions += 1;
        self.win_rank_sum += rank as u64;
        self.legal_at_win_sum += legal_count as u64;
        self.win_rank_hist[rank.min(ORDER_RANK_BUCKETS - 1)] += 1;
        self.by_phase[phase.index()].record_win(rank, legal_count);
    }

    fn merge(&mut self, other: &OrderStats) {
        self.win_decisions += other.win_decisions;
        self.win_rank_sum += other.win_rank_sum;
        self.legal_at_win_sum += other.legal_at_win_sum;
        for i in 0..ORDER_RANK_BUCKETS {
            self.win_rank_hist[i] += other.win_rank_hist[i];
        }
        for i in 0..GAME_PHASE_COUNT {
            self.by_phase[i].merge(&other.by_phase[i]);
        }
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
    order: OrderStats,
}

impl Stats {
    fn merge(&mut self, other: &Stats) {
        self.states_searched += other.states_searched;
        self.memo_hits += other.memo_hits;
        self.endgame_hits += other.endgame_hits;
        self.endgame_raw_cache_hits += other.endgame_raw_cache_hits;
        self.endgame_canonical_cache_hits += other.endgame_canonical_cache_hits;
        self.endgame_cgt_misses += other.endgame_cgt_misses;
        self.endgame_component_evaluations += other.endgame_component_evaluations;
        self.order.merge(&other.order);
    }

    fn add_endgame_stats(&mut self, endgame: EndgameStats) {
        self.endgame_raw_cache_hits += endgame.raw_cache_hits;
        self.endgame_canonical_cache_hits += endgame.canonical_cache_hits;
        self.endgame_cgt_misses += endgame.cgt_misses;
        self.endgame_component_evaluations += endgame.component_evaluations;
    }
}

/// Cross-thread coordination: aggregated progress counter, throttle for
/// progress lines, cancel flag, and optional adaptive move ordering.
struct Coordination {
    searched: AtomicU64,
    last_report_ms: AtomicU64,
    cancel: AtomicBool,
    started: Instant,
    adapt: bool,
    board_m: usize,
    board_n: usize,
    order_mode: AtomicU8,
    win_decisions: AtomicU64,
    win_rank_sum: AtomicU64,
    win_rank0: AtomicU64,
    p2_preferred_wins: AtomicU64,
    p2_preferred_miss: AtomicU64,
    last_adapt_states: AtomicU64,
    order_switches: AtomicUsize,
}

const ADAPT_MIN_STATES: u64 = 1_000_000;
const ADAPT_CHECK_INTERVAL: u64 = 2_000_000;
/// Win-decision density below this on 3×N strips suggests a bad heuristic tree.
const ADAPT_WD_RATIO_THRESHOLD: f64 = 0.365;

impl Coordination {
    fn new(adapt: bool, board_m: usize, board_n: usize, initial_mode: u8) -> Coordination {
        Coordination {
            searched: AtomicU64::new(0),
            last_report_ms: AtomicU64::new(0),
            cancel: AtomicBool::new(false),
            started: Instant::now(),
            adapt,
            board_m,
            board_n,
            order_mode: AtomicU8::new(initial_mode),
            win_decisions: AtomicU64::new(0),
            win_rank_sum: AtomicU64::new(0),
            win_rank0: AtomicU64::new(0),
            p2_preferred_wins: AtomicU64::new(0),
            p2_preferred_miss: AtomicU64::new(0),
            last_adapt_states: AtomicU64::new(0),
            order_switches: AtomicUsize::new(0),
        }
    }

    fn active_order(&self) -> ActiveOrder {
        active_order_from_code(self.order_mode.load(Ordering::Relaxed))
    }

    fn record_order_win(&self, rank: usize, had_p2_preferred: bool) {
        self.win_decisions.fetch_add(1, Ordering::Relaxed);
        self.win_rank_sum.fetch_add(rank as u64, Ordering::Relaxed);
        if rank == 0 {
            self.win_rank0.fetch_add(1, Ordering::Relaxed);
        }
        if had_p2_preferred {
            self.p2_preferred_wins.fetch_add(1, Ordering::Relaxed);
            if rank > 0 {
                self.p2_preferred_miss.fetch_add(1, Ordering::Relaxed);
            }
        }
    }

    fn maybe_adapt(&self) {
        if !self.adapt {
            return;
        }
        let searched = self.searched.load(Ordering::Relaxed);
        if searched < ADAPT_MIN_STATES {
            return;
        }
        let last = self.last_adapt_states.load(Ordering::Relaxed);
        if searched.saturating_sub(last) < ADAPT_CHECK_INTERVAL {
            return;
        }
        if self
            .last_adapt_states
            .compare_exchange(last, searched, Ordering::Relaxed, Ordering::Relaxed)
            .is_err()
        {
            return;
        }

        let wins = self.win_decisions.load(Ordering::Relaxed);
        if wins == 0 {
            return;
        }
        let wd_ratio = wins as f64 / searched as f64;
        let mode = self.order_mode.load(Ordering::Relaxed);
        let strip = self.board_m == 3 && self.board_n >= 11;

        let pref_wins = self.p2_preferred_wins.load(Ordering::Relaxed);
        let pref_miss = self.p2_preferred_miss.load(Ordering::Relaxed);
        let mirror_misfire = pref_wins > 50_000
            && pref_miss as f64 / pref_wins as f64 > 0.45;

        match mode {
            ORDER_HEURISTIC
                if strip
                    && self.board_n >= 13
                    && wd_ratio < ADAPT_WD_RATIO_THRESHOLD =>
            {
                self.order_mode.store(ORDER_LEGACY, Ordering::Relaxed);
                self.order_switches.fetch_add(1, Ordering::Relaxed);
                eprintln!(
                    "\norder: switched to legacy at {searched} states (wd/s={wd_ratio:.3})",
                );
            }
            ORDER_HEURISTIC if mirror_misfire || (strip && wd_ratio < ADAPT_WD_RATIO_THRESHOLD) => {
                self.order_mode
                    .store(ORDER_HEURISTIC_NO_MIRROR, Ordering::Relaxed);
                self.order_switches.fetch_add(1, Ordering::Relaxed);
                eprintln!(
                    "\norder: disabled P2 mirror at {searched} states (wd/s={wd_ratio:.3}, mirror_miss={:.0}%)",
                    100.0 * pref_miss as f64 / pref_wins.max(1) as f64,
                );
            }
            ORDER_HEURISTIC_NO_MIRROR
                if strip && wd_ratio < ADAPT_WD_RATIO_THRESHOLD && searched >= 8_000_000 =>
            {
                self.order_mode.store(ORDER_LEGACY, Ordering::Relaxed);
                self.order_switches.fetch_add(1, Ordering::Relaxed);
                eprintln!(
                    "\norder: switched to legacy at {searched} states (wd/s={wd_ratio:.3})",
                );
            }
            _ => {}
        }
    }
}

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
    order_stats: bool,
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
        order_stats: bool,
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
            order_stats,
        }
    }

    #[inline]
    fn record_win_decision(
        &mut self,
        turn: u8,
        rank: usize,
        legal_count: usize,
        p1_legal: u64,
        p2_legal: u64,
        legal_mask: u64,
        last_p1_move: Option<usize>,
        ordering: ActiveOrder,
    ) {
        if !(self.order_stats || self.coord.adapt) {
            return;
        }
        let had_p2_preferred = turn == P2
            && matches!(
                ordering,
                ActiveOrder::Heuristic { p2_mirror: true }
            )
            && self
                .board
                .p2_preferred(legal_mask, last_p1_move, true)
                .is_some();
        let open_cells = (p1_legal | p2_legal).count_ones();
        let phase = GamePhase::from_open_cells(open_cells, self.board.num_cells);
        self.stats.order.record_win(rank, legal_count, phase);
        self.coord.record_order_win(rank, had_p2_preferred);
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
    fn is_winning(
        &mut self,
        turn: u8,
        key: u128,
        p1_legal: u64,
        p2_legal: u64,
        last_p1_move: Option<usize>,
    ) -> Option<bool> {
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
            self.coord.maybe_adapt();
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
        let ordering = self.coord.active_order();

        let moves = self
            .board
            .ordered_move_bits(turn, legal_mask, last_p1_move, ordering);
        let legal_count = moves.len();
        for (rank, bit) in moves.into_iter().enumerate() {
            let cell = bit.trailing_zeros() as usize;
            let (child_p1_legal, child_p2_legal) =
                self.board.child_legals(p1_legal, p2_legal, turn, bit);
            let child_legal = if next_turn == P1 {
                child_p1_legal
            } else {
                child_p2_legal
            };
            if child_legal == 0 {
                self.record_win_decision(
                    turn,
                    rank,
                    legal_count,
                    p1_legal,
                    p2_legal,
                    legal_mask,
                    last_p1_move,
                    ordering,
                );
                self.remember(key, p1_legal, p2_legal, true);
                return Some(true);
            }

            let child_key = self
                .board
                .shadow_key(child_p1_legal, child_p2_legal, next_turn);

            if let Some(cached_child) = self.memo.get(child_key) {
                self.stats.memo_hits += 1;
                if !cached_child {
                    self.record_win_decision(
                        turn,
                        rank,
                        legal_count,
                        p1_legal,
                        p2_legal,
                        legal_mask,
                        last_p1_move,
                        ordering,
                    );
                    self.remember(key, p1_legal, p2_legal, true);
                    return Some(true);
                }
                continue;
            }

            let child_last_p1 = if turn == P1 {
                Some(cell)
            } else {
                last_p1_move
            };
            let opponent_wins = self.is_winning(
                next_turn,
                child_key,
                child_p1_legal,
                child_p2_legal,
                child_last_p1,
            )?;
            if !opponent_wins {
                self.record_win_decision(
                    turn,
                    rank,
                    legal_count,
                    p1_legal,
                    p2_legal,
                    legal_mask,
                    last_p1_move,
                    ordering,
                );
                self.remember(key, p1_legal, p2_legal, true);
                return Some(true);
            }
        }

        self.remember(key, p1_legal, p2_legal, false);
        Some(false)
    }
}

fn legacy_move_bits(board: &Board, legal: u64, preferred: Option<usize>) -> Vec<u64> {
    let mut bits = Vec::new();
    if let Some(cell) = preferred {
        bits.push(1u64 << cell);
    }
    for &(cell, bit) in &board.move_order {
        if Some(cell) == preferred || legal & bit == 0 {
            continue;
        }
        bits.push(bit);
    }
    bits
}

fn heuristic_move_bits(
    board: &Board,
    legal: u64,
    preferred: Option<usize>,
    order: &[(usize, u64)],
) -> Vec<u64> {
    let mut bits = Vec::new();
    if let Some(cell) = preferred {
        bits.push(1u64 << cell);
    }
    for &(cell, bit) in order {
        if Some(cell) == preferred || legal & bit == 0 {
            continue;
        }
        bits.push(bit);
    }
    bits
}

impl<'a, M: Memo> Solver<'a, M> {
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
        let rate = searched as f64 / elapsed.max(1e-9);
        let mut line = format!(
            "states searched: {searched} | memo: {} | {rate:.0}/s | {elapsed:.1}s",
            self.memo.len(),
        );
        if self.order_stats || self.coord.adapt {
            let wins = self.coord.win_decisions.load(Ordering::Relaxed);
            if wins > 0 {
                let rank_sum = self.coord.win_rank_sum.load(Ordering::Relaxed);
                let rank0 = self.coord.win_rank0.load(Ordering::Relaxed);
                let mean_rank = rank_sum as f64 / wins as f64;
                let rank0_pct = 100.0 * rank0 as f64 / wins as f64;
                let spr = searched as f64 / wins as f64;
                let mode = order_mode_label(self.coord.order_mode.load(Ordering::Relaxed));
                line.push_str(&format!(
                    " | rank={mean_rank:.2} r0={rank0_pct:.0}% spr={spr:.2} [{mode}]",
                ));
            }
        }
        eprint!("\r{line:<120}");
    }
}

/// Symmetry-distinct P1 openings, each a self-contained subtree:
/// (child shadow key, child P1 legal, child P2 legal, P1 opening cell).
fn distinct_openings(board: &Board, ordering: ActiveOrder) -> Vec<(u128, u64, u64, usize)> {
    let legal = board.all_cells_mask;
    let mut seen: FxHashSet<u128> = FxHashSet::default();
    let mut openings = Vec::new();
    let mut emit = |cell: usize, bit: u64| {
        let (c1, c2) = board.child_legals(legal, legal, P1, bit);
        let key = board.shadow_key(c1, c2, P2);
        if seen.insert(key) {
            openings.push((key, c1, c2, cell));
        }
    };
    let bits = board.ordered_move_bits(P1, legal, None, ordering);
    for bit in bits {
        emit(bit.trailing_zeros() as usize, bit);
    }
    openings
}

struct SolveOutput {
    p1_wins: bool,
    stats: Stats,
    entries: Vec<(u128, bool)>,
}

fn print_order_stats(order: &OrderStats) {
    if order.win_decisions == 0 {
        println!("order stats: no win decisions recorded");
        return;
    }
    let mean_rank = order.win_rank_sum as f64 / order.win_decisions as f64;
    let mean_legal = order.legal_at_win_sum as f64 / order.win_decisions as f64;
    let rank0_pct = 100.0 * order.win_rank_hist[0] as f64 / order.win_decisions as f64;
    println!(
        "order stats: {} win decisions, mean rank {:.2}, rank-0 {:.1}%, mean legal moves {:.1}",
        order.win_decisions, mean_rank, rank0_pct, mean_legal,
    );
    let mut hist_parts = Vec::new();
    for rank in 0..ORDER_RANK_BUCKETS {
        if order.win_rank_hist[rank] == 0 {
            continue;
        }
        let label = if rank == ORDER_RANK_BUCKETS - 1 {
            format!("{rank}+")
        } else {
            rank.to_string()
        };
        hist_parts.push(format!("{}={}", label, order.win_rank_hist[rank]));
        if hist_parts.len() >= 12 {
            break;
        }
    }
    if !hist_parts.is_empty() {
        println!("order rank histogram: {}", hist_parts.join(" "));
    }
    println!("order stats by phase (% of board cells still playable):");
    for phase in [GamePhase::Opening, GamePhase::Midgame, GamePhase::Endgame] {
        let p = &order.by_phase[phase.index()];
        if p.win_decisions == 0 {
            println!("  {}: no win decisions", phase.label());
            continue;
        }
        let phase_mean = p.win_rank_sum as f64 / p.win_decisions as f64;
        let phase_rank0 = 100.0 * p.rank0 as f64 / p.win_decisions as f64;
        let phase_legal = p.legal_at_win_sum as f64 / p.win_decisions as f64;
        let share = 100.0 * p.win_decisions as f64 / order.win_decisions as f64;
        println!(
            "  {}: {} decisions ({:.1}% of wins), mean rank {:.2}, rank-0 {:.1}%, mean legal {:.1}",
            phase.label(),
            p.win_decisions,
            share,
            phase_mean,
            phase_rank0,
            phase_legal,
        );
    }
}

fn run_sequential<M: Memo>(
    board: &Board,
    memo: M,
    coord: &Coordination,
    progress: bool,
    endgame_size: u32,
    memo_min_legal: u32,
    order_stats: bool,
) -> SolveOutput {
    let legal = board.all_cells_mask;
    let key = board.shadow_key(legal, legal, P1);
    let shared_endgame = (endgame_size > 0).then(|| Arc::new(SharedEndgameCache::new()));
    let mut solver = Solver::new(
        board,
        &memo,
        coord,
        progress,
        shared_endgame,
        endgame_size,
        memo_min_legal,
        order_stats,
    );
    let p1_wins = solver
        .is_winning(P1, key, legal, legal, None)
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
    coord: &Coordination,
    progress: bool,
    endgame_size: u32,
    memo: M,
    memo_min_legal: u32,
    order_stats: bool,
) -> SolveOutput {
    let openings = distinct_openings(board, coord.active_order());
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
                    coord,
                    progress,
                    shared_endgame.clone(),
                    endgame_size,
                    memo_min_legal,
                    order_stats,
                );
                loop {
                    if coord.cancel.load(Ordering::Relaxed) {
                        break;
                    }
                    let i = next_opening.fetch_add(1, Ordering::Relaxed);
                    if i >= openings.len() {
                        break;
                    }
                    let (key, c1, c2, opening_cell) = openings[i];
                    match solver.is_winning(P2, key, c1, c2, Some(opening_cell)) {
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
                total.lock().unwrap().merge(&stats);
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

#[derive(Clone, Copy)]
struct SubTask {
    key: u128,
    p1: u64,
    p2: u64,
    last_p1_move: Option<usize>,
}

enum JobState {
    Unexpanded,
    Running {
        generation: u32,
        q_key: u128,
        subtasks: Vec<SubTask>,
        next: usize,
        pending: usize,
    },
    Done,
}

struct OpeningJob {
    key: u128,
    p1: u64,
    p2: u64,
    opening_cell: usize,
    /// P2 reply bits already tried for this opening.
    tried_replies: u64,
    state: JobState,
}

struct SchedState {
    jobs: Vec<OpeningJob>,
    ready: VecDeque<Claim>,
    active: usize,
    result: Option<bool>,
}

struct Claim {
    job: usize,
    generation: u32,
    task: SubTask,
}

enum Poll {
    Work(Claim),
    NoWorkYet,
    Finished,
}

enum Advance {
    /// Opening refuted (P2-to-move wins it); job done.
    JobDone,
    /// Every P2 reply fails: this opening is a P1 win, so P1 wins the game.
    P1Wins,
    /// Subtasks installed; workers can claim them.
    Working,
}

enum ReplyOutcome {
    Refuted,
    NextReply,
    Installed(u128, Vec<SubTask>),
}

/// AND-split scheduler. Tasks mirror exactly what sequential search must do:
/// every symmetry-distinct opening must be searched (AND at the root), and for
/// the speculated best P2 reply, every P1 continuation must be searched (AND
/// one ply deeper). Speculation only wastes work when move ordering picks a
/// losing P2 reply, which is rare and detected as soon as one subtask fails.
struct AndSplit<'a, M: Memo> {
    board: &'a Board,
    memo: &'a M,
    coord: &'a Coordination,
    state: Mutex<SchedState>,
}

impl<'a, M: Memo> AndSplit<'a, M> {
    fn new(board: &'a Board, memo: &'a M, coord: &'a Coordination) -> Self {
        let jobs: Vec<OpeningJob> = distinct_openings(board, coord.active_order())
            .into_iter()
            .map(|(key, p1, p2, opening_cell)| OpeningJob {
                key,
                p1,
                p2,
                opening_cell,
                tried_replies: 0,
                state: JobState::Unexpanded,
            })
            .collect();
        let active = jobs.len();
        AndSplit {
            board,
            memo,
            coord,
            state: Mutex::new(SchedState {
                jobs,
                ready: VecDeque::new(),
                active,
                result: None,
            }),
        }
    }

    fn next_untried_p2_reply(&self, job: &OpeningJob) -> Option<u64> {
        let remaining = job.p2 & !job.tried_replies;
        if remaining == 0 {
            return None;
        }
        let bits = self.board.ordered_move_bits(
            P2,
            remaining,
            Some(job.opening_cell),
            self.coord.active_order(),
        );
        bits.into_iter().next()
    }

    /// Expand one P2 reply of an opening into its P1-continuation subtasks.
    /// Memo hits resolve children (or the whole reply) without queueing work.
    fn expand_reply(&self, o_p1: u64, o_p2: u64, reply: u64) -> ReplyOutcome {
        let board = self.board;
        let (q1, q2) = board.child_legals(o_p1, o_p2, P2, reply);
        if q1 == 0 {
            // P1 has no continuation: this reply refutes the opening.
            return ReplyOutcome::Refuted;
        }
        let q_key = board.shadow_key(q1, q2, P1);
        match self.memo.get(q_key) {
            Some(true) => return ReplyOutcome::NextReply,
            Some(false) => return ReplyOutcome::Refuted,
            None => {}
        }
        let preferred = match board.center_cell {
            Some(center) if q1 & (1u64 << center) != 0 => Some(center),
            _ => None,
        };
        let mut subtasks = Vec::new();
        let mut seen: FxHashSet<u128> = FxHashSet::default();
        for bit in board.ordered_move_bits(P1, q1, preferred, self.coord.active_order()) {
            let cell = bit.trailing_zeros() as usize;
            let (c1, c2) = board.child_legals(q1, q2, P1, bit);
            if c2 == 0 {
                // P1 move leaves P2 with nothing: P1 wins Q, reply fails.
                self.memo.insert(q_key, true);
                return ReplyOutcome::NextReply;
            }
            let ckey = board.shadow_key(c1, c2, P2);
            if !seen.insert(ckey) {
                continue;
            }
            match self.memo.get(ckey) {
                Some(true) => continue,
                Some(false) => {
                    self.memo.insert(q_key, true);
                    return ReplyOutcome::NextReply;
                }
                None => subtasks.push(SubTask {
                    key: ckey,
                    p1: c1,
                    p2: c2,
                    last_p1_move: Some(cell),
                }),
            }
        }
        if subtasks.is_empty() {
            self.memo.insert(q_key, false);
            return ReplyOutcome::Refuted;
        }
        ReplyOutcome::Installed(q_key, subtasks)
    }

    /// Try untried P2 replies until one installs subtasks or the job resolves.
    fn advance_job(&self, job: &mut OpeningJob, generation: u32) -> Advance {
        while let Some(reply) = self.next_untried_p2_reply(job) {
            job.tried_replies |= reply;
            match self.expand_reply(job.p1, job.p2, reply) {
                ReplyOutcome::Refuted => {
                    self.memo.insert(job.key, true);
                    job.state = JobState::Done;
                    return Advance::JobDone;
                }
                ReplyOutcome::NextReply => {}
                ReplyOutcome::Installed(q_key, subtasks) => {
                    let pending = subtasks.len();
                    job.state = JobState::Running {
                        generation,
                        q_key,
                        subtasks,
                        next: 0,
                        pending,
                    };
                    return Advance::Working;
                }
            }
        }
        self.memo.insert(job.key, false);
        job.state = JobState::Done;
        Advance::P1Wins
    }

    fn set_result(&self, state: &mut SchedState, p1_wins: bool) {
        if state.result.is_none() {
            state.result = Some(p1_wins);
            self.coord.cancel.store(true, Ordering::Relaxed);
        }
    }

    fn is_current_claim(state: &SchedState, claim: &Claim) -> bool {
        matches!(
            state.jobs.get(claim.job).map(|job| &job.state),
            Some(JobState::Running { generation, .. }) if *generation == claim.generation
        )
    }

    fn enqueue_ready(state: &mut SchedState, job_idx: usize) {
        let (generation, tasks) = match &mut state.jobs[job_idx].state {
            JobState::Running {
                generation,
                subtasks,
                next,
                ..
            } => {
                let generation = *generation;
                let start = *next;
                *next = subtasks.len();
                (generation, subtasks[start..].to_vec())
            }
            _ => return,
        };
        state
            .ready
            .extend(tasks.into_iter().map(|task| Claim {
                job: job_idx,
                generation,
                task,
            }));
    }

    fn take_work(&self) -> Poll {
        let mut state = self.state.lock().unwrap();
        if state.result.is_some() {
            return Poll::Finished;
        }
        // Claim an already-expanded subtask first. Stale tasks can remain
        // after a speculated P2 reply fails; skip them before doing work.
        while let Some(claim) = state.ready.pop_front() {
            if Self::is_current_claim(&state, &claim) {
                return Poll::Work(claim);
            }
        }
        // Expand the next opening.
        for job_idx in 0..state.jobs.len() {
            if !matches!(state.jobs[job_idx].state, JobState::Unexpanded) {
                continue;
            }
            match self.memo.get(state.jobs[job_idx].key) {
                Some(true) => {
                    state.jobs[job_idx].state = JobState::Done;
                    state.active -= 1;
                    if state.active == 0 {
                        self.set_result(&mut state, false);
                        return Poll::Finished;
                    }
                    continue;
                }
                Some(false) => {
                    state.jobs[job_idx].state = JobState::Done;
                    self.set_result(&mut state, true);
                    return Poll::Finished;
                }
                None => {}
            }
            if state.jobs[job_idx].p2 == 0 {
                // P2 has no reply: P1's opening wins outright.
                self.memo.insert(state.jobs[job_idx].key, false);
                state.jobs[job_idx].state = JobState::Done;
                self.set_result(&mut state, true);
                return Poll::Finished;
            }
            let mut job = std::mem::replace(
                &mut state.jobs[job_idx],
                OpeningJob {
                    key: 0,
                    p1: 0,
                    p2: 0,
                    opening_cell: 0,
                    tried_replies: 0,
                    state: JobState::Done,
                },
            );
            let advance = self.advance_job(&mut job, 0);
            state.jobs[job_idx] = job;
            match advance {
                Advance::JobDone => {
                    state.active -= 1;
                    if state.active == 0 {
                        self.set_result(&mut state, false);
                        return Poll::Finished;
                    }
                }
                Advance::P1Wins => {
                    self.set_result(&mut state, true);
                    return Poll::Finished;
                }
                Advance::Working => {
                    Self::enqueue_ready(&mut state, job_idx);
                    if let Some(claim) = state.ready.pop_front() {
                        return Poll::Work(claim);
                    }
                }
            }
        }
        if state.active == 0 {
            self.set_result(&mut state, false);
            return Poll::Finished;
        }
        Poll::NoWorkYet
    }

    fn report(&self, claim: &Claim, p2_wins_child: bool) {
        let mut state = self.state.lock().unwrap();
        if state.result.is_some() {
            return;
        }
        let job_idx = claim.job;
        let (matches_gen, q_key) = match state.jobs[job_idx].state {
            JobState::Running {
                generation,
                q_key,
                ..
            } => (generation == claim.generation, q_key),
            _ => (false, 0),
        };
        if !matches_gen {
            return; // stale result from an abandoned speculation
        }
        if p2_wins_child {
            if let JobState::Running {
                ref mut pending, ..
            } = state.jobs[job_idx].state
            {
                *pending -= 1;
                if *pending > 0 {
                    return;
                }
            }
            // Every P1 continuation refuted: the reply wins, opening refuted.
            self.memo.insert(q_key, false);
            self.memo.insert(state.jobs[job_idx].key, true);
            state.jobs[job_idx].state = JobState::Done;
            state.active -= 1;
            if state.active == 0 {
                self.set_result(&mut state, false);
            }
        } else {
            // P1 has a winning continuation: speculated reply fails.
            self.memo.insert(q_key, true);
            let mut job = std::mem::replace(
                &mut state.jobs[job_idx],
                OpeningJob {
                    key: 0,
                    p1: 0,
                    p2: 0,
                    opening_cell: 0,
                    tried_replies: 0,
                    state: JobState::Done,
                },
            );
            let advance = self.advance_job(&mut job, claim.generation + 1);
            state.jobs[job_idx] = job;
            match advance {
                Advance::JobDone => {
                    state.active -= 1;
                    if state.active == 0 {
                        self.set_result(&mut state, false);
                    }
                }
                Advance::P1Wins => self.set_result(&mut state, true),
                Advance::Working => Self::enqueue_ready(&mut state, job_idx),
            }
        }
    }
}

/// Parallel AND-split: openings (all required) are subdivided one ply deeper
/// into the P1 continuations of the best-ordered P2 reply (all required when
/// the reply is correct). Yields hundreds of tasks instead of ~20 without
/// enlarging the search.
fn solve_parallel_and_split<M: Memo + Sync>(
    board: &Board,
    threads: usize,
    coord: &Coordination,
    progress: bool,
    endgame_size: u32,
    memo: M,
    memo_min_legal: u32,
    order_stats: bool,
) -> SolveOutput {
    let legal = board.all_cells_mask;
    let root_key = board.shadow_key(legal, legal, P1);
    let shared_endgame = (endgame_size > 0).then(|| Arc::new(SharedEndgameCache::new()));
    let sched = AndSplit::new(board, &memo, coord);
    let total = std::sync::Mutex::new(Stats::default());

    std::thread::scope(|scope| {
        for _ in 0..threads {
            scope.spawn(|| {
                let mut solver = Solver::new(
                    board,
                    &memo,
                    coord,
                    progress,
                    shared_endgame.clone(),
                    endgame_size,
                    memo_min_legal,
                    order_stats,
                );
                loop {
                    if coord.cancel.load(Ordering::Relaxed) {
                        break;
                    }
                    match sched.take_work() {
                        Poll::Work(claim) => {
                            match solver.is_winning(
                                P2,
                                claim.task.key,
                                claim.task.p1,
                                claim.task.p2,
                                claim.task.last_p1_move,
                            ) {
                                Some(p2_wins) => sched.report(&claim, p2_wins),
                                None => break,
                            }
                        }
                        Poll::NoWorkYet => {
                            std::thread::sleep(std::time::Duration::from_millis(1))
                        }
                        Poll::Finished => break,
                    }
                }
                let stats = solver.take_stats();
                total.lock().unwrap().merge(&stats);
            });
        }
    });

    let mut stats = total.into_inner().unwrap();
    stats.states_searched += 1;
    let p1_wins = sched
        .state
        .into_inner()
        .unwrap()
        .result
        .expect("and-split must resolve the root");
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
    let mut root_split = false;
    let mut move_order_spec: Option<MoveOrderSpec> = None;
    let mut order_stats = false;
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
            "--root-split" => {
                root_split = true;
                i += 1;
            }
            "--move-order" => {
                move_order_spec = Some(MoveOrderSpec::parse(&args[i + 1]));
                i += 2;
            }
            "--order-stats" => {
                order_stats = true;
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
        "usage: col-rs --m M --n N [--threads T] [--memo open|hash|fixed] [--memo-min-legal K] [--memo-bits K] [--endgame-size K] [--move-order auto|legacy|heuristic] [--order-stats] [--tablebase-dir DIR] [--no-tablebase] [--root-split] [--progress]"
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
    let move_order_spec = move_order_spec.unwrap_or_else(|| MoveOrderSpec::default_for_board(m, n));
    let (adapt_order, initial_order_mode) = match move_order_spec {
        MoveOrderSpec::Auto => (true, ORDER_HEURISTIC),
        MoveOrderSpec::Legacy => (false, ORDER_LEGACY),
        MoveOrderSpec::Heuristic => (false, ORDER_HEURISTIC),
    };
    let coord = Coordination::new(adapt_order, m, n, initial_order_mode);
    let track_order = order_stats || adapt_order;
    let board = Board::new(m, n);
    let legal = board.all_cells_mask;
    let root_key = board.shadow_key(legal, legal, P1);
    let effective_root_split = root_split || m == 1;

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
                    &coord,
                    progress,
                    endgame_size,
                    memo_min_legal,
                    track_order,
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
                    &coord,
                    progress,
                    endgame_size,
                    memo_min_legal,
                    track_order,
                )
            }
            _ => run_sequential(
                &board,
                SeqMemo(RefCell::new(loaded)),
                &coord,
                progress,
                endgame_size,
                memo_min_legal,
                track_order,
            ),
        };
        (output, true)
    } else {
        let output = if memo_kind == "fixed" {
            let memo = SharedFixedMemo::with_total_slots_log2(memo_bits);
            for (key, value) in loaded {
                memo.insert(key, value);
            }
            if effective_root_split {
                solve_parallel_root(
                    &board,
                    threads,
                    &coord,
                    progress,
                    endgame_size,
                    memo,
                    memo_min_legal,
                    track_order,
                )
            } else {
                solve_parallel_and_split(
                    &board,
                    threads,
                    &coord,
                    progress,
                    endgame_size,
                    memo,
                    memo_min_legal,
                    track_order,
                )
            }
        } else {
            let memo = SharedMemo(DashMap::with_hasher(FxBuildHasher));
            for (key, value) in loaded {
                memo.insert(key, value);
            }
            if effective_root_split {
                solve_parallel_root(
                    &board,
                    threads,
                    &coord,
                    progress,
                    endgame_size,
                    memo,
                    memo_min_legal,
                    track_order,
                )
            } else {
                solve_parallel_and_split(
                    &board,
                    threads,
                    &coord,
                    progress,
                    endgame_size,
                    memo,
                    memo_min_legal,
                    track_order,
                )
            }
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
    let move_order_label = match move_order_spec {
        MoveOrderSpec::Auto => {
            let final_mode = order_mode_label(coord.order_mode.load(Ordering::Relaxed));
            let switches = coord.order_switches.load(Ordering::Relaxed);
            if switches > 0 {
                format!("auto→{final_mode} ({switches} switch(es))")
            } else {
                format!("auto ({final_mode})")
            }
        }
        MoveOrderSpec::Legacy => "legacy".to_string(),
        MoveOrderSpec::Heuristic => "heuristic".to_string(),
    };
    let ordering_suffix = format!(", move-order {move_order_label}");
    println!(
        "solver: rust DFS (shadow keys, {} thread{}{}, {} memo{}{})",
        threads,
        if threads == 1 { "" } else { "s" },
        if threads == 1 {
            ""
        } else if effective_root_split {
            " root-split"
        } else {
            " and-split"
        },
        if threads == 1 {
            memo_kind.as_str()
        } else if memo_kind == "fixed" {
            "fixed"
        } else {
            "dashmap"
        },
        ordering_suffix,
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
    if track_order {
        print_order_stats(&output.stats.order);
    }
}
