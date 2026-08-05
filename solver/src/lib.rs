//! DFS solver for the 2D m x n Col placement game.
//!
//! Shadow keying (memo on legal-move masks), geometric symmetry
//! canonicalization, center-first move ordering, the even-dimension
//! pairing theorem shortcut, parallel root opening split with a
//! shared concurrent memo, and a compact open-addressing memo table.

mod endgame;
mod tablebase;

use dashmap::DashMap;
use endgame::{
    ComponentBagKey, ComponentBagProbe, EndgameEvaluation, EndgameEvaluator, EndgameStats,
    SharedEndgameCache,
};
use rustc_hash::{FxBuildHasher, FxHashMap, FxHashSet};
use std::cell::RefCell;
use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicU8, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;

const P1: u8 = 0;
const P2: u8 = 1;
const RESERVE_CARDINALITY_GATE_SHARED: u32 = 8;

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

    fn default_for_board(m: usize, n: usize) -> MoveOrderSpec {
        if m == 3 && n >= 13 {
            MoveOrderSpec::Auto
        } else {
            MoveOrderSpec::Heuristic
        }
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
    checkerboard_mask: u64,
    left_column_mask: u64,
    right_column_mask: u64,
    fixed_matching_masks: [u64; 4],
    adjacency: Vec<u64>,
    move_order: Vec<(usize, u64)>,
    p1_order: Vec<(usize, u64)>,
    p2_order: Vec<(usize, u64)>,
    reflected_cell: Vec<usize>,
    vertical_reflection_byte_tables: ByteTransformTables,
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

        let mut checkerboard_mask = 0u64;
        let mut left_column_mask = 0u64;
        let mut right_column_mask = 0u64;
        let mut fixed_matching_masks = [0u64; 4];
        let mut adjacency = vec![0u64; num_cells];
        for row in 0..m {
            for col in 0..n {
                let cell = row * n + col;
                if (row + col) % 2 == 0 {
                    checkerboard_mask |= 1u64 << cell;
                }
                if col == 0 {
                    left_column_mask |= 1u64 << cell;
                }
                if col + 1 == n {
                    right_column_mask |= 1u64 << cell;
                }
                if col + 1 < n {
                    fixed_matching_masks[col % 2] |= 1u64 << cell;
                }
                if row + 1 < m {
                    fixed_matching_masks[2 + row % 2] |= 1u64 << cell;
                }
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
        let vertical_reflected_cell: Vec<usize> = (0..num_cells)
            .map(|cell| {
                let row = cell / n;
                let col = cell % n;
                row * n + (n - 1 - col)
            })
            .collect();
        let vertical_reflection_byte_tables =
            Self::build_byte_tables(&vertical_reflected_cell, num_cells);

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
            checkerboard_mask,
            left_column_mask,
            right_column_mask,
            fixed_matching_masks,
            adjacency,
            move_order,
            p1_order,
            p2_order,
            reflected_cell,
            vertical_reflection_byte_tables,
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
    ) -> OrderedMoveBits<'_> {
        let (preferred, order) = match ordering {
            ActiveOrder::Legacy => {
                let preferred = match (turn, self.center_cell) {
                    (P1, Some(center)) if legal & (1u64 << center) != 0 => Some(center),
                    _ => None,
                };
                (preferred, self.move_order.as_slice())
            }
            ActiveOrder::Heuristic { p2_mirror: false } if turn == P1 => {
                (None, self.p1_order.as_slice())
            }
            ActiveOrder::Heuristic { p2_mirror: false } => {
                (None, self.p2_order.as_slice())
            }
            ActiveOrder::Heuristic { p2_mirror: true } if turn == P1 => {
                (None, self.p1_order.as_slice())
            }
            ActiveOrder::Heuristic { p2_mirror: true } => {
                let preferred = self.p2_preferred(legal, last_p1_move, true);
                (preferred, self.p2_order.as_slice())
            }
        };
        OrderedMoveBits {
            legal,
            preferred: preferred.map(|cell| 1u64 << cell),
            preferred_emitted: false,
            order: order.iter(),
        }
    }

    /// Exact actor-relative child dominance. A private move `x` is dominated
    /// by `y` when `y` removes a subset of the actor's legal cells; `y` also
    /// leaves the opponent no better off (and a shared `y` removes one of the
    /// opponent's options). Equal private children keep the earlier move.
    fn dominated_move_bits(
        &self,
        turn: u8,
        legal: u64,
        opponent_legal: u64,
        last_p1_move: Option<usize>,
        ordering: ActiveOrder,
    ) -> u64 {
        let private = legal & !opponent_legal;
        if private == 0 || legal.count_ones() < 2 {
            return 0;
        }
        let mut earlier = 0u64;
        let mut dominated = 0u64;
        for bit in self.ordered_move_bits(turn, legal, last_p1_move, ordering) {
            if bit & private != 0 {
                let cell = bit.trailing_zeros() as usize;
                let removed = (bit | self.adjacency[cell]) & legal;

                // Any dominator y must itself be in `removed`: y belongs to
                // its own removal set, which must be a subset of this one.
                // A grid cell therefore has at most four candidates here.
                let mut candidates = removed & !bit;
                while candidates != 0 {
                    let candidate = candidates & candidates.wrapping_neg();
                    candidates ^= candidate;
                    let candidate_cell = candidate.trailing_zeros() as usize;
                    let candidate_removed =
                        (candidate | self.adjacency[candidate_cell]) & legal;
                    if candidate_removed & !removed != 0 {
                        continue;
                    }
                    let strictly_smaller = candidate_removed != removed;
                    let shared_dominator = candidate & opponent_legal != 0;
                    let earlier_equivalent_private =
                        !shared_dominator && candidate & earlier != 0;
                    if strictly_smaller || shared_dominator || earlier_equivalent_private {
                        dominated |= bit;
                        break;
                    }
                }
            }
            earlier |= bit;
        }
        dominated
    }

    fn independent_set_lower_bound(&self, mask: u64) -> u32 {
        let first = (mask & self.checkerboard_mask).count_ones();
        first.max(mask.count_ones() - first)
    }

    fn private_independent_set_lower_bound(&self, mask: u64) -> u32 {
        let vertical_neighbors = (mask << self.n) | (mask >> self.n);
        let horizontal_neighbors = ((mask & !self.left_column_mask) >> 1)
            | ((mask & !self.right_column_mask) << 1);
        let isolated = mask & !(vertical_neighbors | horizontal_neighbors);
        isolated.count_ones() + self.independent_set_lower_bound(mask & !isolated)
    }

    fn independent_set_upper_bound_fixed(&self, mask: u64) -> u32 {
        let horizontal = (mask & (mask >> 1) & self.fixed_matching_masks[0])
            .count_ones()
            .max((mask & (mask >> 1) & self.fixed_matching_masks[1]).count_ones());
        let vertical = (mask & (mask >> self.n) & self.fixed_matching_masks[2])
            .count_ones()
            .max((mask & (mask >> self.n) & self.fixed_matching_masks[3]).count_ones());
        let matching = horizontal.max(vertical);
        mask.count_ones() - matching
    }

    fn independent_set_upper_bound_greedy(&self, mask: u64) -> u32 {
        let mut left = mask & self.checkerboard_mask;
        let mut available_right = mask & !self.checkerboard_mask;
        let mut matching = 0u32;
        while left != 0 && available_right != 0 {
            let bit = left & left.wrapping_neg();
            left ^= bit;
            let cell = bit.trailing_zeros() as usize;
            let neighbors = self.adjacency[cell] & available_right;
            if neighbors != 0 {
                available_right ^= neighbors & neighbors.wrapping_neg();
                matching += 1;
            }
        }
        mask.count_ones() - matching
    }

    /// A necessary cardinality condition for either private-reserve proof.
    /// The caller supplies `shared = |current & opponent|` so the hot path can
    /// reuse the popcount that gates this test.
    #[inline]
    fn private_reserve_cardinality_can_prove(
        current: u64,
        opponent: u64,
        shared: u32,
    ) -> bool {
        let current_count = current.count_ones();
        let opponent_count = opponent.count_ones();
        debug_assert!(shared <= current_count && shared <= opponent_count);
        let current_private = current_count - shared;
        let opponent_private = opponent_count - shared;
        current_private > opponent_count.div_ceil(2)
            || opponent_private >= current_count.div_ceil(2)
    }

    /// Exact sufficient outcome bounds from untouchable private moves.
    /// Returns the outcome for the actor to move, the number of fixed-bound
    /// gates, and the number that needed the stronger greedy matching bound.
    fn private_reserve_outcome(
        &self,
        current: u64,
        opponent: u64,
    ) -> (Option<bool>, u8, u8) {
        let current_private_lb =
            self.private_independent_set_lower_bound(current & !opponent);
        let opponent_private_lb =
            self.private_independent_set_lower_bound(opponent & !current);
        let opponent_total_lb = self
            .independent_set_lower_bound(opponent)
            .max(opponent_private_lb);
        let mut matching_checks = 0;
        let mut greedy_checks = 0;
        if current_private_lb > opponent_total_lb {
            if current_private_lb > opponent.count_ones() {
                return (Some(true), matching_checks, greedy_checks);
            }
            matching_checks += 1;
            if current_private_lb > self.independent_set_upper_bound_fixed(opponent) {
                return (Some(true), matching_checks, greedy_checks);
            }
            greedy_checks += 1;
            if current_private_lb > self.independent_set_upper_bound_greedy(opponent) {
                return (Some(true), matching_checks, greedy_checks);
            }
            return (None, matching_checks, greedy_checks);
        }

        let current_total_lb = self
            .independent_set_lower_bound(current)
            .max(current_private_lb);
        if opponent_private_lb >= current_total_lb {
            if opponent_private_lb >= current.count_ones() {
                return (Some(false), matching_checks, greedy_checks);
            }
            matching_checks += 1;
            if opponent_private_lb >= self.independent_set_upper_bound_fixed(current) {
                return (Some(false), matching_checks, greedy_checks);
            }
            greedy_checks += 1;
            if opponent_private_lb >= self.independent_set_upper_bound_greedy(current) {
                return (Some(false), matching_checks, greedy_checks);
            }
        }
        (None, matching_checks, greedy_checks)
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

    #[inline]
    fn reflect_mask(&self, mask: u64) -> u64 {
        // Row-major half-turn maps bit i to num_cells - 1 - i: a bit
        // reversal followed by alignment to the low live bits.
        mask.reverse_bits() >> (64 - self.num_cells)
    }

    #[inline]
    fn flip_three_rows(&self, mask: u64) -> u64 {
        debug_assert_eq!(self.m, 3);
        let row_mask = (1u64 << self.n) - 1;
        ((mask & row_mask) << (2 * self.n))
            | (mask & (row_mask << self.n))
            | ((mask >> (2 * self.n)) & row_mask)
    }

    #[inline]
    fn vertical_reflect_mask(&self, mask: u64) -> u64 {
        self.transform_mask(mask, &self.vertical_reflection_byte_tables)
    }

    fn middle_column_mask(&self) -> u64 {
        let col = self.n / 2;
        (0..self.m)
            .map(|row| 1u64 << (row * self.n + col))
            .fold(0, |mask, bit| mask | bit)
    }

    fn unpack_shadow_key(&self, key: u128) -> (u64, u64, u8) {
        let turn = (key & 1) as u8;
        let p2 = ((key >> 1) as u64) & self.all_cells_mask;
        let p1 = ((key >> (self.num_cells + 1)) as u64) & self.all_cells_mask;
        (p1, p2, turn)
    }

    /// A color-swapping half-turn involution pairs every move with a legal
    /// response and restores the same relation after the pair.
    #[inline]
    fn has_reflection_pairing_certificate(
        &self,
        legal_p1: u64,
        legal_p2: u64,
        turn: u8,
    ) -> bool {
        // Reflection preserves cardinality, so most non-pairing states can be
        // rejected before the eight-byte mask transform.
        if legal_p1.count_ones() != legal_p2.count_ones() {
            return false;
        }
        let actor_legal = if turn == P1 { legal_p1 } else { legal_p2 };
        if let Some(center) = self.center_cell {
            if actor_legal & (1u64 << center) != 0 {
                return false;
            }
        }
        self.reflect_mask(legal_p1) == legal_p2
    }

    #[inline]
    fn shadow_key(&self, legal_p1: u64, legal_p2: u64, turn: u8) -> u128 {
        let pack = |p1: u64, p2: u64, side: u8| {
            ((p1 as u128) << (self.num_cells + 1)) | ((p2 as u128) << 1) | side as u128
        };
        let mut best = pack(legal_p1, legal_p2, turn).min(pack(
            legal_p2,
            legal_p1,
            turn ^ 1,
        ));
        // A non-square 3xn rectangle has only three non-identity geometric
        // symmetries. Express them with bit operations so canonicalization
        // avoids six eight-byte table transforms (P1 and P2 for each).
        if self.m == 3 && self.n != 3 {
            let r1 = self.reflect_mask(legal_p1);
            let r2 = self.reflect_mask(legal_p2);
            best = best.min(pack(r1, r2, turn));
            best = best.min(pack(r2, r1, turn ^ 1));

            let v1 = self.flip_three_rows(legal_p1);
            let v2 = self.flip_three_rows(legal_p2);
            best = best.min(pack(v1, v2, turn));
            best = best.min(pack(v2, v1, turn ^ 1));

            let h1 = self.flip_three_rows(r1);
            let h2 = self.flip_three_rows(r2);
            best = best.min(pack(h1, h2, turn));
            best = best.min(pack(h2, h1, turn ^ 1));
            return best;
        }
        for transform in &self.transform_byte_tables {
            let t1 = self.transform_mask(legal_p1, transform);
            let t2 = self.transform_mask(legal_p2, transform);
            best = best.min(pack(t1, t2, turn));
            best = best.min(pack(t2, t1, turn ^ 1));
        }
        best
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

    fn neighbor_union(&self, mut mask: u64) -> u64 {
        let mut out = 0u64;
        while mask != 0 {
            let bit = mask & mask.wrapping_neg();
            let cell = bit.trailing_zeros() as usize;
            out |= self.adjacency[cell];
            mask ^= bit;
        }
        out
    }

    fn legal_masks_from_stones(&self, p1: u64, p2: u64) -> (u64, u64) {
        assert!(p1 & p2 == 0, "P1 and P2 stones overlap");
        let occupied = p1 | p2;
        (
            self.all_cells_mask & !(occupied | self.neighbor_union(p1)),
            self.all_cells_mask & !(occupied | self.neighbor_union(p2)),
        )
    }
}

/// Allocation-free traversal of legal moves in the active order.
struct OrderedMoveBits<'a> {
    legal: u64,
    preferred: Option<u64>,
    preferred_emitted: bool,
    order: std::slice::Iter<'a, (usize, u64)>,
}

impl Iterator for OrderedMoveBits<'_> {
    type Item = u64;

    #[inline]
    fn next(&mut self) -> Option<Self::Item> {
        if !self.preferred_emitted {
            self.preferred_emitted = true;
            if let Some(bit) = self.preferred {
                debug_assert!(self.legal & bit != 0);
                return Some(bit);
            }
        }
        for &(_, bit) in self.order.by_ref() {
            if Some(bit) != self.preferred && self.legal & bit != 0 {
                return Some(bit);
            }
        }
        None
    }
}

/// Win/loss memo shared by reference; interior mutability so the
/// sequential and concurrent implementations share one solver body.
trait Memo {
    const USE_FRONT_CACHE: bool = false;

    fn get(&self, key: u128) -> Option<bool>;
    #[inline]
    fn get_prehashed(&self, key: u128, _hash: u64) -> Option<bool> {
        self.get(key)
    }
    fn insert(&self, key: u128, value: bool);
    #[inline]
    fn insert_prehashed(&self, key: u128, value: bool, _hash: u64) {
        self.insert(key, value);
    }
    fn len(&self) -> usize;
    fn evictions(&self) -> u64 {
        0
    }
    fn into_entries(self) -> Vec<(u128, bool)>;
}

const FRONT_CACHE_BITS: u32 = 12;

/// Tiny worker-local exact cache in front of the locked shared fixed table.
/// Direct replacement is safe because entries are immutable proven values.
struct FrontCache {
    slots: Box<[u128]>,
    shift: u32,
}

impl FrontCache {
    fn new(bits: u32) -> FrontCache {
        FrontCache {
            slots: vec![EMPTY_SLOT; 1usize << bits].into_boxed_slice(),
            shift: 64 - bits,
        }
    }

    #[inline]
    fn get_prehashed(&self, key: u128, hash: u64) -> Option<bool> {
        let slot = self.slots[(hash >> self.shift) as usize];
        (slot != EMPTY_SLOT && slot >> 1 == key).then_some(slot & 1 == 1)
    }

    #[inline]
    fn insert_prehashed(&mut self, key: u128, value: bool, hash: u64) {
        let packed = (key << 1) | value as u128;
        if packed != EMPTY_SLOT {
            self.slots[(hash >> self.shift) as usize] = packed;
        }
    }
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
    evictions: u64,
    num_cells: usize,
}

const PROBE_WINDOW: usize = 8;

impl FixedTable {
    fn with_slots_log2(bits: u32, num_cells: usize) -> FixedTable {
        let cap = 1usize << bits;
        FixedTable {
            slots: vec![EMPTY_SLOT; cap],
            shift: 64 - bits,
            mask: cap - 1,
            len: 0,
            evictions: 0,
            num_cells,
        }
    }

    #[cfg(test)]
    #[inline]
    fn slot_index(&self, key: u128) -> usize {
        self.slot_index_from_hash(hash_key(key))
    }

    #[inline]
    fn slot_index_from_hash(&self, hash: u64) -> usize {
        (hash >> self.shift) as usize
    }

    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        self.get_hashed(key, hash_key(key))
    }

    #[inline]
    fn get_hashed(&self, key: u128, hash: u64) -> Option<bool> {
        let base = self.slot_index_from_hash(hash);
        for offset in 0..PROBE_WINDOW {
            let slot = self.slots[(base + offset) & self.mask];
            if slot == EMPTY_SLOT {
                return None;
            }
            if slot >> 1 == key {
                return Some(slot & 1 == 1);
            }
        }
        None
    }

    fn insert(&mut self, key: u128, value: bool) {
        self.insert_hashed(key, value, hash_key(key));
    }

    fn insert_hashed(&mut self, key: u128, value: bool, hash: u64) {
        let base = self.slot_index_from_hash(hash);
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
        // Window full: retain the positions with the most remaining legal
        // moves, which are usually the most expensive to recompute.
        let mut victim = base;
        let mut victim_priority = self.priority(self.slots[base] >> 1);
        for offset in 1..PROBE_WINDOW {
            let i = (base + offset) & self.mask;
            let priority = self.priority(self.slots[i] >> 1);
            if priority < victim_priority {
                victim = i;
                victim_priority = priority;
            }
        }
        self.evictions += 1;
        self.slots[victim] = entry;
    }

    #[inline]
    fn priority(&self, key: u128) -> u32 {
        let legal_mask = (1u128 << self.num_cells) - 1;
        let p2 = (key >> 1) & legal_mask;
        let p1 = (key >> (self.num_cells + 1)) & legal_mask;
        (p1 | p2).count_ones()
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
    fn evictions(&self) -> u64 {
        self.0.borrow().evictions
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
    shard_shift: u32,
}

impl SharedFixedMemo {
    fn with_total_slots_log2(bits: u32, num_cells: usize) -> SharedFixedMemo {
        let shard_bits = (bits.saturating_sub(10)).min(6);
        let shard_count = 1usize << shard_bits;
        let table_bits = bits - shard_bits;
        let shard_shift = 64 - table_bits - shard_bits;
        let shards = (0..shard_count)
            .map(|_| Mutex::new(FixedTable::with_slots_log2(table_bits, num_cells)))
            .collect();
        SharedFixedMemo {
            shards,
            shard_mask: shard_count - 1,
            shard_shift,
        }
    }

    #[cfg(test)]
    #[inline]
    fn shard_index(&self, key: u128) -> usize {
        self.shard_index_from_hash(hash_key(key))
    }

    #[inline]
    fn shard_index_from_hash(&self, hash: u64) -> usize {
        (hash >> self.shard_shift) as usize & self.shard_mask
    }
}

impl Memo for SharedFixedMemo {
    const USE_FRONT_CACHE: bool = true;

    #[inline]
    fn get(&self, key: u128) -> Option<bool> {
        let hash = hash_key(key);
        self.get_prehashed(key, hash)
    }

    #[inline]
    fn get_prehashed(&self, key: u128, hash: u64) -> Option<bool> {
        self.shards[self.shard_index_from_hash(hash)]
            .lock()
            .unwrap()
            .get_hashed(key, hash)
    }

    #[inline]
    fn insert(&self, key: u128, value: bool) {
        let hash = hash_key(key);
        self.insert_prehashed(key, value, hash);
    }

    #[inline]
    fn insert_prehashed(&self, key: u128, value: bool, hash: u64) {
        self.shards[self.shard_index_from_hash(hash)]
            .lock()
            .unwrap()
            .insert_hashed(key, value, hash);
    }

    fn len(&self) -> usize {
        self.shards
            .iter()
            .map(|shard| shard.lock().unwrap().len)
            .sum()
    }

    fn evictions(&self) -> u64 {
        self.shards
            .iter()
            .map(|shard| shard.lock().unwrap().evictions)
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
    front_cache_queries: u64,
    front_cache_hits: u64,
    dominance_nodes: u64,
    dominance_pruned_moves: u64,
    reserve_cardinality_skips: u64,
    reserve_matching_checks: u64,
    reserve_greedy_checks: u64,
    reserve_win_hits: u64,
    reserve_loss_hits: u64,
    pairing_certificate_checks: u64,
    pairing_certificate_hits: u64,
    endgame_hits: u64,
    endgame_raw_cache_hits: u64,
    endgame_canonical_cache_hits: u64,
    endgame_cgt_misses: u64,
    endgame_component_evaluations: u64,
    reduction_calls: u64,
    reduction_component_evaluations: u64,
    reduction_column_all_small_exits: u64,
    reduction_single_component_exits: u64,
    reduction_all_small_exits: u64,
    reduction_multi_oversized: u64,
    reduction_changes: u64,
    conjugate_pairs_removed: u64,
    zero_components_removed: u64,
    zero_sum_cells_removed: u64,
    reductions_to_empty: u64,
    component_bag_queries: u64,
    component_bag_hits: u64,
    component_bag_local_hits: u64,
    component_bag_inserts: u64,
    component_bag_local_duplicate_inserts: u64,
    component_bag_shared_queries: u64,
    component_bag_shared_hits: u64,
    component_bag_shared_inserts: u64,
    component_bag_shared_duplicate_inserts: u64,
    component_bag_raw_id_hits: u64,
    component_bag_signature_hits: u64,
    component_signature_shared_queries: u64,
    component_signature_shared_hits: u64,
    component_signature_shared_inserts: u64,
    order: OrderStats,
}

impl Stats {
    fn merge(&mut self, other: &Stats) {
        self.states_searched += other.states_searched;
        self.memo_hits += other.memo_hits;
        self.front_cache_queries += other.front_cache_queries;
        self.front_cache_hits += other.front_cache_hits;
        self.dominance_nodes += other.dominance_nodes;
        self.dominance_pruned_moves += other.dominance_pruned_moves;
        self.reserve_cardinality_skips += other.reserve_cardinality_skips;
        self.reserve_matching_checks += other.reserve_matching_checks;
        self.reserve_greedy_checks += other.reserve_greedy_checks;
        self.reserve_win_hits += other.reserve_win_hits;
        self.reserve_loss_hits += other.reserve_loss_hits;
        self.pairing_certificate_checks += other.pairing_certificate_checks;
        self.pairing_certificate_hits += other.pairing_certificate_hits;
        self.endgame_hits += other.endgame_hits;
        self.endgame_raw_cache_hits += other.endgame_raw_cache_hits;
        self.endgame_canonical_cache_hits += other.endgame_canonical_cache_hits;
        self.endgame_cgt_misses += other.endgame_cgt_misses;
        self.endgame_component_evaluations += other.endgame_component_evaluations;
        self.reduction_calls += other.reduction_calls;
        self.reduction_component_evaluations += other.reduction_component_evaluations;
        self.reduction_column_all_small_exits += other.reduction_column_all_small_exits;
        self.reduction_single_component_exits += other.reduction_single_component_exits;
        self.reduction_all_small_exits += other.reduction_all_small_exits;
        self.reduction_multi_oversized += other.reduction_multi_oversized;
        self.reduction_changes += other.reduction_changes;
        self.conjugate_pairs_removed += other.conjugate_pairs_removed;
        self.zero_components_removed += other.zero_components_removed;
        self.zero_sum_cells_removed += other.zero_sum_cells_removed;
        self.reductions_to_empty += other.reductions_to_empty;
        self.component_bag_queries += other.component_bag_queries;
        self.component_bag_hits += other.component_bag_hits;
        self.component_bag_local_hits += other.component_bag_local_hits;
        self.component_bag_inserts += other.component_bag_inserts;
        self.component_bag_local_duplicate_inserts +=
            other.component_bag_local_duplicate_inserts;
        self.component_bag_shared_queries += other.component_bag_shared_queries;
        self.component_bag_shared_hits += other.component_bag_shared_hits;
        self.component_bag_shared_inserts += other.component_bag_shared_inserts;
        self.component_bag_shared_duplicate_inserts +=
            other.component_bag_shared_duplicate_inserts;
        self.component_bag_raw_id_hits += other.component_bag_raw_id_hits;
        self.component_bag_signature_hits += other.component_bag_signature_hits;
        self.component_signature_shared_queries += other.component_signature_shared_queries;
        self.component_signature_shared_hits += other.component_signature_shared_hits;
        self.component_signature_shared_inserts += other.component_signature_shared_inserts;
        self.order.merge(&other.order);
    }

    fn add_endgame_stats(&mut self, endgame: EndgameStats) {
        self.endgame_raw_cache_hits += endgame.raw_cache_hits;
        self.endgame_canonical_cache_hits += endgame.canonical_cache_hits;
        self.endgame_cgt_misses += endgame.cgt_misses;
        self.endgame_component_evaluations += endgame.component_evaluations;
        self.reduction_calls += endgame.reduction_calls;
        self.reduction_component_evaluations += endgame.reduction_component_evaluations;
        self.reduction_column_all_small_exits += endgame.reduction_column_all_small_exits;
        self.reduction_single_component_exits += endgame.reduction_single_component_exits;
        self.reduction_all_small_exits += endgame.reduction_all_small_exits;
        self.reduction_multi_oversized += endgame.reduction_multi_oversized;
        self.reduction_changes += endgame.reduction_changes;
        self.conjugate_pairs_removed += endgame.conjugate_pairs_removed;
        self.zero_components_removed += endgame.zero_components_removed;
        self.zero_sum_cells_removed += endgame.zero_sum_cells_removed;
        self.reductions_to_empty += endgame.reductions_to_empty;
        self.component_bag_queries += endgame.component_bag_queries;
        self.component_bag_hits += endgame.component_bag_hits;
        self.component_bag_local_hits += endgame.component_bag_local_hits;
        self.component_bag_inserts += endgame.component_bag_inserts;
        self.component_bag_local_duplicate_inserts +=
            endgame.component_bag_local_duplicate_inserts;
        self.component_bag_shared_queries += endgame.component_bag_shared_queries;
        self.component_bag_shared_hits += endgame.component_bag_shared_hits;
        self.component_bag_shared_inserts += endgame.component_bag_shared_inserts;
        self.component_bag_shared_duplicate_inserts +=
            endgame.component_bag_shared_duplicate_inserts;
        self.component_bag_raw_id_hits += endgame.component_bag_raw_id_hits;
        self.component_bag_signature_hits += endgame.component_bag_signature_hits;
        self.component_signature_shared_queries += endgame.component_signature_shared_queries;
        self.component_signature_shared_hits += endgame.component_signature_shared_hits;
        self.component_signature_shared_inserts += endgame.component_signature_shared_inserts;
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
    pairing_certificate: bool,
    component_reduction: bool,
}

const ADAPT_MIN_STATES: u64 = 1_000_000;
const ADAPT_CHECK_INTERVAL: u64 = 2_000_000;
/// Win-decision density below this on 3×N strips suggests a bad heuristic tree.
const ADAPT_WD_RATIO_THRESHOLD: f64 = 0.365;

impl Coordination {
    fn new(
        adapt: bool,
        board_m: usize,
        board_n: usize,
        initial_mode: u8,
        pairing_certificate: bool,
        component_reduction: bool,
    ) -> Coordination {
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
            pairing_certificate,
            component_reduction,
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
    front_cache: Option<FrontCache>,
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
            front_cache: M::USE_FRONT_CACHE.then(|| FrontCache::new(FRONT_CACHE_BITS)),
            memo_min_legal,
            order_stats,
        }
    }

    fn enable_shared_component_bags(&mut self) {
        if let Some(endgame) = self.endgame.as_mut() {
            endgame.enable_shared_component_bags();
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
    fn memo_get(&mut self, key: u128) -> Option<bool> {
        let Some(front) = self.front_cache.as_mut() else {
            return self.memo.get(key);
        };
        let hash = hash_key(key);
        self.stats.front_cache_queries += 1;
        if let Some(value) = front.get_prehashed(key, hash) {
            self.stats.front_cache_hits += 1;
            return Some(value);
        }
        let value = self.memo.get_prehashed(key, hash);
        if let Some(value) = value {
            front.insert_prehashed(key, value, hash);
        }
        value
    }

    #[inline]
    fn remember(&mut self, key: u128, p1_legal: u64, p2_legal: u64, value: bool) {
        if (p1_legal | p2_legal).count_ones() >= self.memo_min_legal {
            if let Some(front) = self.front_cache.as_mut() {
                let hash = hash_key(key);
                front.insert_prehashed(key, value, hash);
                self.memo.insert_prehashed(key, value, hash);
            } else {
                self.memo.insert(key, value);
            }
        }
    }

    #[inline]
    fn remember_component_bag(&mut self, key: &mut Option<ComponentBagKey>, value: bool) {
        if let Some(key) = key.take() {
            self.endgame
                .as_mut()
                .expect("component-bag key requires endgame evaluator")
                .insert_component_bag(key, value);
        }
    }

    fn take_stats(&mut self) -> Stats {
        let mut stats = std::mem::take(&mut self.stats);
        if let Some(endgame) = &self.endgame {
            stats.add_endgame_stats(endgame.stats());
        }
        stats
    }

    #[inline]
    fn begin_state(&mut self) -> bool {
        self.stats.states_searched += 1;
        if self.stats.states_searched % FLUSH_INTERVAL == 0 {
            if self.coord.cancel.load(Ordering::Relaxed) {
                return false;
            }
            self.coord
                .searched
                .fetch_add(FLUSH_INTERVAL, Ordering::Relaxed);
            if self.progress {
                self.maybe_report();
            }
            self.coord.maybe_adapt();
        }
        true
    }

    /// Returns None if the search was cancelled by another worker.
    fn is_winning(
        &mut self,
        turn: u8,
        mut key: u128,
        mut p1_legal: u64,
        mut p2_legal: u64,
        last_p1_move: Option<usize>,
        known_unreduced_miss: bool,
    ) -> Option<bool> {
        let mut skip_reduction = false;
        let mut raw_endgame_miss = false;
        if known_unreduced_miss && self.coord.component_reduction {
            let endgame = self
                .endgame
                .as_mut()
                .expect("component reduction requires endgame evaluation");
            match endgame.classify_position(
                self.board.n,
                &self.board.adjacency,
                p1_legal,
                p2_legal,
                turn,
            ) {
                EndgameEvaluation::Solved(wins) => {
                    if !self.begin_state() {
                        return None;
                    }
                    self.stats.endgame_hits += 1;
                    self.remember(key, p1_legal, p2_legal, wins);
                    return Some(wins);
                }
                EndgameEvaluation::SingleLocalComponent => {
                    // A connected position has no disjoint zero summand for
                    // the component reducer to remove.
                    skip_reduction = true;
                    raw_endgame_miss = true;
                }
                EndgameEvaluation::OversizedMiss => {
                    raw_endgame_miss = true;
                }
            }
        }
        let mut key_changed = false;
        let mut component_bag_candidate = false;
        if self.coord.component_reduction && !skip_reduction {
            let endgame = self
                .endgame
                .as_mut()
                .expect("component reduction requires endgame evaluation");
            let reduction = endgame.reduce_zero_summands(
                self.board.n,
                &self.board.adjacency,
                p1_legal,
                p2_legal,
            );
            component_bag_candidate = reduction.component_bag_candidate;
            if reduction.changed {
                p1_legal = reduction.legal_p1;
                p2_legal = reduction.legal_p2;
                key = self.board.shadow_key(p1_legal, p2_legal, turn);
                key_changed = true;
            }
        }
        if !known_unreduced_miss || key_changed {
            if let Some(cached) = self.memo_get(key) {
                self.stats.memo_hits += 1;
                return Some(cached);
            }
        }
        if !self.begin_state() {
            return None;
        }

        let legal_mask = if turn == P1 { p1_legal } else { p2_legal };
        if legal_mask == 0 {
            self.remember(key, p1_legal, p2_legal, false);
            return Some(false);
        }
        if self.coord.pairing_certificate {
            self.stats.pairing_certificate_checks += 1;
            if self
                .board
                .has_reflection_pairing_certificate(p1_legal, p2_legal, turn)
            {
                self.stats.pairing_certificate_hits += 1;
                self.remember(key, p1_legal, p2_legal, false);
                return Some(false);
            }
        }
        if (!raw_endgame_miss || key_changed) && self.endgame.is_some() {
            let endgame = self.endgame.as_mut().unwrap();
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

        let opponent_legal = if turn == P1 { p2_legal } else { p1_legal };
        let shared_count = (legal_mask & opponent_legal).count_ones();
        let reserve_can_prove = shared_count < RESERVE_CARDINALITY_GATE_SHARED
            || Board::private_reserve_cardinality_can_prove(
                legal_mask,
                opponent_legal,
                shared_count,
            );
        let (reserve_outcome, reserve_matching_checks, reserve_greedy_checks) = if reserve_can_prove
        {
            self.board
                .private_reserve_outcome(legal_mask, opponent_legal)
        } else {
            self.stats.reserve_cardinality_skips += 1;
            (None, 0, 0)
        };
        self.stats.reserve_matching_checks += reserve_matching_checks as u64;
        self.stats.reserve_greedy_checks += reserve_greedy_checks as u64;
        if let Some(wins) = reserve_outcome {
            if wins {
                self.stats.reserve_win_hits += 1;
            } else {
                self.stats.reserve_loss_hits += 1;
            }
            self.remember(key, p1_legal, p2_legal, wins);
            return Some(wins);
        }

        let component_bag_probe = if component_bag_candidate {
            self.endgame
                .as_mut()
                .expect("component-bag candidate requires endgame evaluator")
                .probe_component_bag(self.board.n, p1_legal, p2_legal, turn)
        } else {
            ComponentBagProbe::Ineligible
        };
        let mut component_bag_key = match component_bag_probe {
            ComponentBagProbe::Ineligible => None,
            ComponentBagProbe::Hit(wins) => {
                self.remember(key, p1_legal, p2_legal, wins);
                return Some(wins);
            }
            ComponentBagProbe::Miss(key) => Some(key),
        };

        let next_turn = 1 - turn;
        let ordering = self.coord.active_order();

        let board = self.board;
        let dominated = board.dominated_move_bits(
            turn,
            legal_mask,
            opponent_legal,
            last_p1_move,
            ordering,
        );
        if dominated != 0 {
            self.stats.dominance_nodes += 1;
            self.stats.dominance_pruned_moves += dominated.count_ones() as u64;
        }
        let moves = board
            .ordered_move_bits(turn, legal_mask, last_p1_move, ordering)
            .filter(|bit| dominated & bit == 0);
        let legal_count = (legal_mask & !dominated).count_ones() as usize;
        for (rank, bit) in moves.enumerate() {
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
                self.remember_component_bag(&mut component_bag_key, true);
                self.remember(key, p1_legal, p2_legal, true);
                return Some(true);
            }

            let child_key = self
                .board
                .shadow_key(child_p1_legal, child_p2_legal, next_turn);

            if let Some(cached_child) = self.memo_get(child_key) {
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
                    self.remember_component_bag(&mut component_bag_key, true);
                    self.remember(key, p1_legal, p2_legal, true);
                    return Some(true);
                }
                continue;
            }

            let child_last_p1 = if turn == P1 {
                Some(bit.trailing_zeros() as usize)
            } else {
                last_p1_move
            };
            let opponent_wins = self.is_winning(
                next_turn,
                child_key,
                child_p1_legal,
                child_p2_legal,
                child_last_p1,
                true,
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
                self.remember_component_bag(&mut component_bag_key, true);
                self.remember(key, p1_legal, p2_legal, true);
                return Some(true);
            }
        }

        self.remember_component_bag(&mut component_bag_key, false);
        self.remember(key, p1_legal, p2_legal, false);
        Some(false)
    }
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
    let moves = board.ordered_move_bits(P1, legal, None, ordering);
    for bit in moves {
        emit(bit.trailing_zeros() as usize, bit);
    }
    openings
}

struct SolveOutput {
    p1_wins: bool,
    stats: Stats,
    memo_entries: usize,
    memo_evictions: u64,
    entries: Vec<(u128, bool)>,
}

fn finish_memo<M: Memo>(memo: M, collect_entries: bool) -> (usize, u64, Vec<(u128, bool)>) {
    let memo_entries = memo.len();
    let memo_evictions = memo.evictions();
    let entries = if collect_entries {
        memo.into_entries()
    } else {
        Vec::new()
    };
    (memo_entries, memo_evictions, entries)
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
    shared_endgame: Option<Arc<SharedEndgameCache>>,
    endgame_size: u32,
    memo_min_legal: u32,
    order_stats: bool,
    collect_entries: bool,
) -> SolveOutput {
    let legal = board.all_cells_mask;
    let key = board.shadow_key(legal, legal, P1);
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
        .is_winning(P1, key, legal, legal, None, false)
        .expect("sequential search cannot be cancelled");
    let stats = solver.take_stats();
    drop(solver);
    // Root must always be present so re-runs answer instantly.
    memo.insert(key, p1_wins);
    let (memo_entries, memo_evictions, entries) = finish_memo(memo, collect_entries);
    SolveOutput {
        p1_wins,
        stats,
        memo_entries,
        memo_evictions,
        entries,
    }
}

fn run_position_query(
    board: &Board,
    loaded: FxHashMap<u128, bool>,
    coord: &Coordination,
    progress: bool,
    shared_endgame: Option<Arc<SharedEndgameCache>>,
    endgame_size: u32,
    memo_min_legal: u32,
    order_stats: bool,
    p1_stones: u64,
    p2_stones: u64,
    turn: u8,
) -> SolveOutput {
    let (p1_legal, p2_legal) = board.legal_masks_from_stones(p1_stones, p2_stones);
    let key = board.shadow_key(p1_legal, p2_legal, turn);
    let memo = SeqMemo(RefCell::new(loaded));
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
        .is_winning(turn, key, p1_legal, p2_legal, None, false)
        .expect("position query should not be cancelled");
    let stats = solver.take_stats();
    let memo_entries = memo.len();
    let memo_evictions = memo.evictions();
    SolveOutput {
        p1_wins,
        stats,
        memo_entries,
        memo_evictions,
        entries: Vec::new(),
    }
}

fn parse_position(position: &str, board: &Board) -> (u64, u64) {
    let rows: Vec<&str> = position.split('/').collect();
    assert!(
        rows.len() == board.m,
        "--position row count must match --m (use / between rows)"
    );
    let mut p1 = 0u64;
    let mut p2 = 0u64;
    for (row, text) in rows.iter().enumerate() {
        assert!(
            text.chars().count() == board.n,
            "--position column count must match --n"
        );
        for (col, ch) in text.chars().enumerate() {
            let bit = 1u64 << (row * board.n + col);
            match ch {
                'B' | 'b' | '1' => p1 |= bit,
                'W' | 'w' | '2' => p2 |= bit,
                '.' | '_' | '-' => {}
                other => panic!("bad --position character {other:?}; use B, W, or ."),
            }
        }
    }
    assert!(p1 & p2 == 0, "--position has overlapping stones");
    (p1, p2)
}

fn parse_turn(turn: &str) -> u8 {
    match turn {
        "P1" | "p1" | "1" | "B" | "b" => P1,
        "P2" | "p2" | "2" | "W" | "w" => P2,
        other => panic!("bad --turn {other}; expected P1 or P2"),
    }
}

fn write_opening_certificate(
    path: &PathBuf,
    board: &Board,
    entries: &[(u128, bool)],
) -> Result<(), String> {
    let lookup = |key: u128| -> Option<bool> {
        entries
            .binary_search_by_key(&key, |entry| entry.0)
            .ok()
            .map(|index| entries[index].1)
    };
    let mut openings = Vec::new();
    let p1_legal = board.all_cells_mask;
    let p2_legal = board.all_cells_mask;
    let mut p1_moves = p1_legal;
    while p1_moves != 0 {
        let p1_bit = p1_moves & p1_moves.wrapping_neg();
        p1_moves ^= p1_bit;
        let p1_cell = p1_bit.trailing_zeros() as usize;
        let (child_p1, child_p2) = board.child_legals(p1_legal, p2_legal, P1, p1_bit);
        let child_key = board.shadow_key(child_p1, child_p2, P2);
        if lookup(child_key) != Some(true) {
            return Err(format!("opening {p1_cell} has no certified winning P2 state"));
        }

        let mut response = None;
        let mut p2_moves = child_p2;
        while p2_moves != 0 {
            let p2_bit = p2_moves & p2_moves.wrapping_neg();
            p2_moves ^= p2_bit;
            let (target_p1, target_p2) =
                board.child_legals(child_p1, child_p2, P2, p2_bit);
            let target_key = board.shadow_key(target_p1, target_p2, P1);
            if lookup(target_key) == Some(false) {
                response = Some((p2_bit.trailing_zeros() as usize, target_key));
                break;
            }
        }
        let (p2_cell, target_key) =
            response.ok_or_else(|| format!("opening {p1_cell} has no certified P2 reply"))?;
        openings.push((p1_cell, p2_cell, child_key, target_key));
    }

    let mut json = format!(
        "{{\n  \"schema_version\": 1,\n  \"board\": \"{}x{}\",\n  \"openings\": [\n",
        board.m, board.n
    );
    for (index, (p1_cell, p2_cell, child_key, target_key)) in openings.iter().enumerate() {
        json.push_str(&format!(
            "    {{\"p1_move\": {p1_cell}, \"p2_response\": {p2_cell}, \
             \"child_key\": \"0x{child_key:x}\", \"target_key\": \"0x{target_key:x}\"}}{}",
            if index + 1 == openings.len() { "\n" } else { ",\n" }
        ));
    }
    json.push_str("  ]\n}\n");
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    std::fs::write(path, json).map_err(|err| err.to_string())
}

fn write_invariant_report(
    path: &PathBuf,
    board: &Board,
    entries: &[(u128, bool)],
) -> Result<(), String> {
    let middle = board.middle_column_mask();
    let wings = board.all_cells_mask & !middle;
    let mut candidates = 0u64;
    let mut counterexample_count = 0u64;
    let mut counterexamples = Vec::new();
    for &(key, side_to_move_wins) in entries {
        let (p1_legal, p2_legal, turn) = board.unpack_shadow_key(key);
        if board.vertical_reflect_mask(p1_legal & wings) != p2_legal & wings {
            continue;
        }
        let middle_value = endgame::component_value_text(
            board.n,
            p1_legal & middle,
            p2_legal & middle,
        );
        if middle_value.as_deref() != Some("0") {
            continue;
        }
        candidates += 1;
        if side_to_move_wins {
            counterexample_count += 1;
            if counterexamples.len() < 100 {
                counterexamples.push((key, turn, p1_legal, p2_legal));
            }
        }
    }

    let mut json = format!(
        "{{\n  \"schema_version\": 1,\n  \"board\": \"{}x{}\",\n  \
         \"entries\": {},\n  \"naive_candidates\": {},\n  \
         \"naive_counterexamples\": {},\n  \"examples\": [\n",
        board.m,
        board.n,
        entries.len(),
        candidates,
        counterexample_count,
    );
    for (index, (key, turn, p1_legal, p2_legal)) in counterexamples.iter().enumerate() {
        json.push_str(&format!(
            "    {{\"key\": \"0x{key:x}\", \"turn\": \"P{}\", \
             \"p1_legal\": \"0x{p1_legal:x}\", \"p2_legal\": \"0x{p2_legal:x}\"}}{}",
            turn + 1,
            if index + 1 == counterexamples.len() {
                "\n"
            } else {
                ",\n"
            }
        ));
    }
    json.push_str("  ]\n}\n");
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    std::fs::write(path, json).map_err(|err| err.to_string())
}

/// Parallel root split: one task per symmetry-distinct P1 opening.
/// Preserves sequential early-exit semantics within each opening subtree.
fn solve_parallel_root<M: Memo + Sync>(
    board: &Board,
    threads: usize,
    coord: &Coordination,
    progress: bool,
    shared_endgame: Option<Arc<SharedEndgameCache>>,
    endgame_size: u32,
    memo: M,
    memo_min_legal: u32,
    order_stats: bool,
    collect_entries: bool,
) -> SolveOutput {
    let openings = distinct_openings(board, coord.active_order());
    let legal = board.all_cells_mask;
    let root_key = board.shadow_key(legal, legal, P1);
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
                solver.enable_shared_component_bags();
                loop {
                    if coord.cancel.load(Ordering::Relaxed) {
                        break;
                    }
                    let i = next_opening.fetch_add(1, Ordering::Relaxed);
                    if i >= openings.len() {
                        break;
                    }
                    let (key, c1, c2, opening_cell) = openings[i];
                    match solver.is_winning(P2, key, c1, c2, Some(opening_cell), false) {
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
    let (memo_entries, memo_evictions, entries) = finish_memo(memo, collect_entries);
    SolveOutput {
        p1_wins,
        stats,
        memo_entries,
        memo_evictions,
        entries,
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
                    last_p1_move: Some(bit.trailing_zeros() as usize),
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
    shared_endgame: Option<Arc<SharedEndgameCache>>,
    endgame_size: u32,
    memo: M,
    memo_min_legal: u32,
    order_stats: bool,
    collect_entries: bool,
) -> SolveOutput {
    let legal = board.all_cells_mask;
    let root_key = board.shadow_key(legal, legal, P1);
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
                solver.enable_shared_component_bags();
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
                                false,
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
    let (memo_entries, memo_evictions, entries) = finish_memo(memo, collect_entries);
    SolveOutput {
        p1_wins,
        stats,
        memo_entries,
        memo_evictions,
        entries,
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
    let mut endgame_cache_enabled = true;
    let mut root_split = false;
    let mut pairing_certificate = true;
    let mut component_reduction = true;
    let mut move_order_spec: Option<MoveOrderSpec> = None;
    let mut order_stats = false;
    let mut opening_certificate_path: Option<PathBuf> = None;
    let mut invariant_report_path: Option<PathBuf> = None;
    let mut position_arg: Option<String> = None;
    let mut query_turn = P1;
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
            "--no-endgame-cache" => {
                endgame_cache_enabled = false;
                i += 1;
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
            "--no-pairing-certificate" => {
                pairing_certificate = false;
                i += 1;
            }
            "--component-reduction" => {
                component_reduction = true;
                i += 1;
            }
            "--no-component-reduction" => {
                component_reduction = false;
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
            "--opening-certificate" => {
                opening_certificate_path = Some(PathBuf::from(&args[i + 1]));
                i += 2;
            }
            "--invariant-report" => {
                invariant_report_path = Some(PathBuf::from(&args[i + 1]));
                i += 2;
            }
            "--position" => {
                position_arg = Some(args[i + 1].clone());
                i += 2;
            }
            "--turn" => {
                query_turn = parse_turn(&args[i + 1]);
                i += 2;
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
        "usage: col-rs --m M --n N [--threads T] [--memo open|hash|fixed] [--memo-min-legal K] [--memo-bits K] [--endgame-size K] [--no-endgame-cache] [--component-reduction|--no-component-reduction] [--move-order auto|legacy|heuristic] [--order-stats] [--opening-certificate PATH] [--invariant-report PATH] [--position ROWS] [--turn P1|P2] [--tablebase-dir DIR] [--no-tablebase] [--root-split] [--no-pairing-certificate] [--progress]"
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
    let coord = Coordination::new(
        adapt_order,
        m,
        n,
        initial_order_mode,
        pairing_certificate,
        component_reduction,
    );
    let track_order = order_stats || adapt_order;
    let board = Board::new(m, n);
    let legal = board.all_cells_mask;
    let root_key = board.shadow_key(legal, legal, P1);
    let position_query = position_arg
        .as_deref()
        .map(|position| parse_position(position, &board));
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
    let cache_load_start = Instant::now();
    let (shared_endgame, endgame_cache_loaded) = if endgame_size > 0 {
        if endgame_cache_enabled {
            endgame::load_shared_cache(&tablebase_dir).unwrap_or_else(|err| {
                eprintln!("warning: could not load CGT component cache: {err}");
                (Arc::new(SharedEndgameCache::new()), 0)
            })
        } else {
            (Arc::new(SharedEndgameCache::new()), 0)
        }
    } else {
        (Arc::new(SharedEndgameCache::new()), 0)
    };
    let endgame_cache_load_secs = cache_load_start.elapsed().as_secs_f64();
    let shared_endgame = (endgame_size > 0).then_some(shared_endgame);
    let collect_entries = tablebase_enabled
        || opening_certificate_path.is_some()
        || invariant_report_path.is_some();

    let start = Instant::now();
    let empty_linear_second_player_win = m == 1 && n > 1;

    let (mut output, searched_fresh) = if let Some((p1_stones, p2_stones)) = position_query {
        (
            run_position_query(
                &board,
                loaded,
                &coord,
                progress,
                shared_endgame.clone(),
                endgame_size,
                memo_min_legal,
                track_order,
                p1_stones,
                p2_stones,
                query_turn,
            ),
            false,
        )
    } else if board.has_even_dimension || empty_linear_second_player_win {
        (
            SolveOutput {
                p1_wins: false,
                stats: Stats::default(),
                memo_entries: loaded_count,
                memo_evictions: 0,
                entries: Vec::new(),
            },
            false,
        )
    } else if let Some(p1_wins) = cached_root {
        (
            SolveOutput {
                p1_wins,
                stats: Stats::default(),
                memo_entries: loaded_count,
                memo_evictions: 0,
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
                    shared_endgame.clone(),
                    endgame_size,
                    memo_min_legal,
                    track_order,
                    collect_entries,
                )
            }
            "fixed" => {
                let mut table = FixedTable::with_slots_log2(memo_bits, board.num_cells);
                for (key, value) in loaded {
                    table.insert(key, value);
                }
                run_sequential(
                    &board,
                    FixedMemo(RefCell::new(table)),
                    &coord,
                    progress,
                    shared_endgame.clone(),
                    endgame_size,
                    memo_min_legal,
                    track_order,
                    collect_entries,
                )
            }
            _ => run_sequential(
                &board,
                SeqMemo(RefCell::new(loaded)),
                &coord,
                progress,
                shared_endgame.clone(),
                endgame_size,
                memo_min_legal,
                track_order,
                collect_entries,
            ),
        };
        (output, true)
    } else {
        let output = if memo_kind == "fixed" {
            let memo = SharedFixedMemo::with_total_slots_log2(memo_bits, board.num_cells);
            for (key, value) in loaded {
                memo.insert(key, value);
            }
            if effective_root_split {
                solve_parallel_root(
                    &board,
                    threads,
                    &coord,
                    progress,
                    shared_endgame.clone(),
                    endgame_size,
                    memo,
                    memo_min_legal,
                    track_order,
                    collect_entries,
                )
            } else {
                solve_parallel_and_split(
                    &board,
                    threads,
                    &coord,
                    progress,
                    shared_endgame.clone(),
                    endgame_size,
                    memo,
                    memo_min_legal,
                    track_order,
                    collect_entries,
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
                    shared_endgame.clone(),
                    endgame_size,
                    memo,
                    memo_min_legal,
                    track_order,
                    collect_entries,
                )
            } else {
                solve_parallel_and_split(
                    &board,
                    threads,
                    &coord,
                    progress,
                    shared_endgame.clone(),
                    endgame_size,
                    memo,
                    memo_min_legal,
                    track_order,
                    collect_entries,
                )
            }
        };
        (output, true)
    };
    let elapsed = start.elapsed().as_secs_f64();
    if progress {
        eprintln!();
    }

    if let Some(path) = &opening_certificate_path {
        output.entries.sort_unstable_by_key(|entry| entry.0);
        if let Err(err) = write_opening_certificate(path, &board, &output.entries) {
            panic!("could not write opening certificate: {err}");
        }
        println!("opening certificate saved: {}", path.display());
    }
    if let Some(path) = &invariant_report_path {
        if let Err(err) = write_invariant_report(path, &board, &output.entries) {
            panic!("could not write invariant report: {err}");
        }
        println!("invariant report saved: {}", path.display());
    }

    let memo_entries = output.memo_entries;
    let memo_evictions = output.memo_evictions;
    let collected_entries = output.entries.len();
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
    let (endgame_cache_saved, endgame_cache_save_secs) = if endgame_size > 0 && endgame_cache_enabled {
        if let Some(cache) = &shared_endgame {
            let save_start = Instant::now();
            let saved = match endgame::save_shared_cache(&tablebase_dir, cache, endgame_cache_loaded) {
                Ok(saved) => saved,
                Err(err) => {
                    eprintln!("warning: could not save CGT component cache: {err}");
                    None
                }
            };
            (saved, save_start.elapsed().as_secs_f64())
        } else {
            (None, 0.0)
        }
    } else {
        (None, 0.0)
    };
    let endgame_cache_entries = shared_endgame
        .as_ref()
        .map(|cache| cache.canonical_len())
        .unwrap_or(0);

    let winner = if position_query.is_some() {
        match (query_turn, output.p1_wins) {
            (P1, true) | (P2, false) => "P1",
            _ => "P2",
        }
    } else if output.p1_wins {
        "P1"
    } else {
        "P2"
    };
    println!("{} x {}: {} wins", m, n, winner);
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
    if output.stats.front_cache_queries > 0 {
        println!("front cache queries: {}", output.stats.front_cache_queries);
        println!("front cache hits: {}", output.stats.front_cache_hits);
    }
    println!("dominance nodes: {}", output.stats.dominance_nodes);
    println!(
        "dominance pruned moves: {}",
        output.stats.dominance_pruned_moves
    );
    println!(
        "reserve cardinality skips: {}",
        output.stats.reserve_cardinality_skips
    );
    println!(
        "reserve matching checks: {}",
        output.stats.reserve_matching_checks
    );
    println!(
        "reserve greedy checks: {}",
        output.stats.reserve_greedy_checks
    );
    println!("reserve win hits: {}", output.stats.reserve_win_hits);
    println!("reserve loss hits: {}", output.stats.reserve_loss_hits);
    println!(
        "pairing certificate checks: {}",
        output.stats.pairing_certificate_checks
    );
    println!(
        "pairing certificate hits: {}",
        output.stats.pairing_certificate_hits
    );
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
        println!("component reduction calls: {}", output.stats.reduction_calls);
        println!(
            "component reduction component evals: {}",
            output.stats.reduction_component_evaluations
        );
        println!(
            "component reduction column all-small exits: {}",
            output.stats.reduction_column_all_small_exits
        );
        println!(
            "component reduction single-component exits: {}",
            output.stats.reduction_single_component_exits
        );
        println!(
            "component reduction all-small exits: {}",
            output.stats.reduction_all_small_exits
        );
        println!(
            "component reduction multi-oversized: {}",
            output.stats.reduction_multi_oversized
        );
        println!(
            "component reduction changes: {}",
            output.stats.reduction_changes
        );
        println!(
            "conjugate pairs removed: {}",
            output.stats.conjugate_pairs_removed
        );
        println!(
            "zero components removed: {}",
            output.stats.zero_components_removed
        );
        println!(
            "zero-sum cells removed: {}",
            output.stats.zero_sum_cells_removed
        );
        println!(
            "reductions to empty: {}",
            output.stats.reductions_to_empty
        );
        if output.stats.component_bag_queries > 0 {
            println!(
                "component bag queries: {}",
                output.stats.component_bag_queries
            );
            println!("component bag hits: {}", output.stats.component_bag_hits);
            println!(
                "component bag local hits: {}",
                output.stats.component_bag_local_hits
            );
            println!(
                "component bag inserts: {}",
                output.stats.component_bag_inserts
            );
            println!(
                "component bag local duplicate inserts: {}",
                output.stats.component_bag_local_duplicate_inserts
            );
            if output.stats.component_bag_shared_queries > 0 {
                println!(
                    "component bag shared queries: {}",
                    output.stats.component_bag_shared_queries
                );
                println!(
                    "component bag shared hits: {}",
                    output.stats.component_bag_shared_hits
                );
                println!(
                    "component bag shared inserts: {}",
                    output.stats.component_bag_shared_inserts
                );
                println!(
                    "component bag shared duplicate inserts: {}",
                    output.stats.component_bag_shared_duplicate_inserts
                );
                println!(
                    "component signature shared queries: {}",
                    output.stats.component_signature_shared_queries
                );
                println!(
                    "component signature shared hits: {}",
                    output.stats.component_signature_shared_hits
                );
                println!(
                    "component signature shared inserts: {}",
                    output.stats.component_signature_shared_inserts
                );
            }
            println!(
                "component bag raw id hits: {}",
                output.stats.component_bag_raw_id_hits
            );
            println!(
                "component bag signature hits: {}",
                output.stats.component_bag_signature_hits
            );
        }
        if endgame_cache_enabled {
            println!("endgame cache loaded: {endgame_cache_loaded} entries");
            if endgame_cache_loaded > 0 {
                println!("endgame cache load: {endgame_cache_load_secs:.6}s");
            }
            println!("endgame cache entries: {endgame_cache_entries}");
        } else {
            println!("endgame cache: disabled");
        }
    }
    if tablebase_enabled && loaded_count > 0 {
        println!("tablebase loaded: {loaded_count} entries");
    }
    println!("memo entries: {memo_entries}");
    println!("memo evictions: {memo_evictions}");
    println!("memo entries collected: {collected_entries}");
    if let Some(path) = saved_path {
        let file_size = std::fs::metadata(&path).map(|meta| meta.len()).unwrap_or(0);
        println!(
            "tablebase saved: {} ({:.2} MB)",
            path.display(),
            file_size as f64 / 1_048_576.0
        );
    }
    if let Some((path, saved_count)) = endgame_cache_saved {
        let file_size = std::fs::metadata(&path).map(|meta| meta.len()).unwrap_or(0);
        println!(
            "endgame cache saved: {} ({} entries, {:.2} MB)",
            path.display(),
            saved_count,
            file_size as f64 / 1_048_576.0
        );
        println!("endgame cache save: {endgame_cache_save_secs:.6}s");
    }
    let rate = output.stats.states_searched as f64 / elapsed.max(1e-9);
    println!("states per second: {:.0}", rate);
    println!("time elapsed (solve): {elapsed:.6}s");
    if track_order {
        print_order_stats(&output.stats.order);
    }
}

#[cfg(test)]
mod tests {
    use super::{
        finish_memo, hash_key, ActiveOrder, Board, FixedTable, FrontCache, SeqMemo,
        SharedFixedMemo, EMPTY_SLOT, P1, P2,
    };
    use rustc_hash::FxHashMap;
    use std::cell::RefCell;

    fn two_entry_memo() -> SeqMemo {
        let mut entries = FxHashMap::default();
        entries.insert(1, true);
        entries.insert(2, false);
        SeqMemo(RefCell::new(entries))
    }

    fn exact_independent_set_size(board: &Board, mask: u64) -> u32 {
        let mut best = 0;
        let mut subset = mask;
        loop {
            if subset.count_ones() > best {
                let mut cells = subset;
                let mut independent = true;
                while cells != 0 {
                    let bit = cells & cells.wrapping_neg();
                    cells ^= bit;
                    if board.adjacency[bit.trailing_zeros() as usize] & cells != 0 {
                        independent = false;
                        break;
                    }
                }
                if independent {
                    best = subset.count_ones();
                }
            }
            if subset == 0 {
                return best;
            }
            subset = (subset - 1) & mask;
        }
    }

    #[test]
    fn private_reserve_bounds_are_sound_exhaustively_on_three_by_three() {
        let board = Board::new(3, 3);
        let exact: Vec<u32> = (0..=board.all_cells_mask)
            .map(|mask| exact_independent_set_size(&board, mask))
            .collect();
        for mask in 0..=board.all_cells_mask {
            assert!(board.independent_set_lower_bound(mask) <= exact[mask as usize]);
            assert!(
                board.private_independent_set_lower_bound(mask) <= exact[mask as usize]
            );
            assert!(board.independent_set_upper_bound_fixed(mask) >= exact[mask as usize]);
            assert!(board.independent_set_upper_bound_greedy(mask) >= exact[mask as usize]);
        }
        for current in 0..=board.all_cells_mask {
            for opponent in 0..=board.all_cells_mask {
                let shared = (current & opponent).count_ones();
                let reserve_result = board.private_reserve_outcome(current, opponent);
                if !Board::private_reserve_cardinality_can_prove(
                    current,
                    opponent,
                    shared,
                ) {
                    assert_eq!(reserve_result, (None, 0, 0));
                }
                match reserve_result.0 {
                    Some(true) => assert!(
                        exact[(current & !opponent) as usize] > exact[opponent as usize]
                    ),
                    Some(false) => assert!(
                        exact[(opponent & !current) as usize] >= exact[current as usize]
                    ),
                    None => {}
                }
            }
        }
    }

    #[test]
    fn private_reserve_cardinality_gate_respects_strict_boundaries() {
        // Win equality is insufficient: 2 private cells cannot beat ceil(4/2).
        let current: u64 = 0b01_1111;
        let opponent: u64 = 0b10_0111;
        let shared = (current & opponent).count_ones();
        assert!(!Board::private_reserve_cardinality_can_prove(
            current, opponent, shared
        ));

        // Loss equality is sufficient: 2 opponent-private cells can tie ceil(4/2).
        let current: u64 = 0b00_1111;
        let opponent: u64 = 0b11_0011;
        let shared = (current & opponent).count_ones();
        assert!(Board::private_reserve_cardinality_can_prove(
            current, opponent, shared
        ));
    }

    #[test]
    fn front_cache_is_exact_under_replacement_and_sentinel_collision() {
        let mut cache = FrontCache::new(2);
        let key = 42u128;
        let hash = hash_key(key);
        assert_eq!(cache.get_prehashed(key, hash), None);
        cache.insert_prehashed(key, true, hash);
        assert_eq!(cache.get_prehashed(key, hash), Some(true));
        cache.insert_prehashed(key, false, hash);
        assert_eq!(cache.get_prehashed(key, hash), Some(false));

        cache.insert_prehashed(7, true, 0);
        cache.insert_prehashed(9, false, 0);
        assert_eq!(cache.get_prehashed(7, 0), None);
        assert_eq!(cache.get_prehashed(9, 0), Some(false));

        let sentinel_key = EMPTY_SLOT >> 1;
        cache.insert_prehashed(sentinel_key, true, 0);
        assert_eq!(cache.get_prehashed(sentinel_key, 0), None);
    }

    fn reference_shadow_key(board: &Board, p1: u64, p2: u64, turn: u8) -> u128 {
        let canonical_pair = |left: u64, right: u64| {
            let mut best = (left, right);
            for transform in &board.transform_byte_tables {
                let transformed_left = board.transform_mask(left, transform);
                if transformed_left > best.0 {
                    continue;
                }
                let transformed_right = board.transform_mask(right, transform);
                if transformed_left < best.0 || transformed_right < best.1 {
                    best = (transformed_left, transformed_right);
                }
            }
            best
        };
        let pack = |left: u64, right: u64, side: u8| {
            ((left as u128) << (board.num_cells + 1))
                | ((right as u128) << 1)
                | side as u128
        };
        let normal = canonical_pair(p1, p2);
        let swapped = canonical_pair(p2, p1);
        pack(normal.0, normal.1, turn).min(pack(swapped.0, swapped.1, turn ^ 1))
    }

    #[test]
    fn memo_collection_is_skipped_without_losing_the_count() {
        let (count, evictions, entries) = finish_memo(two_entry_memo(), false);
        assert_eq!(count, 2);
        assert_eq!(evictions, 0);
        assert!(entries.is_empty());

        let (count, evictions, entries) = finish_memo(two_entry_memo(), true);
        assert_eq!(count, 2);
        assert_eq!(evictions, 0);
        assert_eq!(entries.len(), 2);
    }

    #[test]
    fn fixed_table_counts_full_window_evictions() {
        let mut table = FixedTable::with_slots_log2(4, 4);
        let mut colliding = Vec::new();
        for key in 0..10_000u128 {
            if table.slot_index(key) == 0 {
                colliding.push(key);
                if colliding.len() == 9 {
                    break;
                }
            }
        }
        assert_eq!(colliding.len(), 9);
        for &key in &colliding[..8] {
            table.insert(key, true);
        }
        assert_eq!(table.evictions, 0);
        table.insert(colliding[8], false);
        assert_eq!(table.evictions, 1);
        table.insert(colliding[8], true);
        assert_eq!(table.evictions, 1);
    }

    #[test]
    fn shared_fixed_memo_uses_mixed_hash_bits_for_shards() {
        let memo = SharedFixedMemo::with_total_slots_log2(20, 33);
        let mut seen = 0u64;
        for index in 0..1024u128 {
            seen |= 1u64 << memo.shard_index(index << 6);
        }
        assert_eq!(seen.count_ones(), 64);
    }

    #[test]
    fn ordered_move_iterator_yields_each_legal_move_once() {
        let board = Board::new(3, 3);
        let orderings = [
            ActiveOrder::Legacy,
            ActiveOrder::Heuristic { p2_mirror: false },
            ActiveOrder::Heuristic { p2_mirror: true },
        ];
        for legal in 0..=board.all_cells_mask {
            for &turn in &[P1, P2] {
                for &ordering in &orderings {
                    let moves: Vec<u64> = board
                        .ordered_move_bits(turn, legal, Some(4), ordering)
                        .collect();
                    assert_eq!(moves.len(), legal.count_ones() as usize);
                    assert_eq!(moves.iter().fold(0, |mask, bit| mask | bit), legal);
                }
            }
        }
    }

    #[test]
    fn every_pruned_move_has_a_dominating_child() {
        let board = Board::new(2, 3);
        let ordering = ActiveOrder::Heuristic { p2_mirror: false };
        for p1_legal in 0..=board.all_cells_mask {
            for p2_legal in 0..=board.all_cells_mask {
                for turn in [P1, P2] {
                    let own = if turn == P1 { p1_legal } else { p2_legal };
                    let opponent = if turn == P1 { p2_legal } else { p1_legal };
                    let dominated =
                        board.dominated_move_bits(turn, own, opponent, None, ordering);
                    if own != 0 {
                        assert_ne!(own & !dominated, 0);
                    }
                    let mut pruned = dominated;
                    while pruned != 0 {
                        let x = pruned & pruned.wrapping_neg();
                        pruned ^= x;
                        let (x1, x2) = board.child_legals(p1_legal, p2_legal, turn, x);
                        let (x_own, x_opponent) = if turn == P1 { (x1, x2) } else { (x2, x1) };
                        let mut alternatives = own & !x;
                        let mut witnessed = false;
                        while alternatives != 0 {
                            let y = alternatives & alternatives.wrapping_neg();
                            alternatives ^= y;
                            let (y1, y2) = board.child_legals(p1_legal, p2_legal, turn, y);
                            let (y_own, y_opponent) =
                                if turn == P1 { (y1, y2) } else { (y2, y1) };
                            if x_own & !y_own == 0 && y_opponent & !x_opponent == 0 {
                                witnessed = true;
                                break;
                            }
                        }
                        assert!(witnessed, "turn={turn}, p1={p1_legal:#x}, p2={p2_legal:#x}");
                    }
                }
            }
        }
    }

    #[test]
    fn shadow_key_identifies_global_color_swap() {
        let board = Board::new(3, 3);
        let p1_legal = (1u64 << 0) | (1u64 << 4) | (1u64 << 7);
        let p2_legal = (1u64 << 1) | (1u64 << 3) | (1u64 << 8);

        assert_eq!(
            board.shadow_key(p1_legal, p2_legal, P1),
            board.shadow_key(p2_legal, p1_legal, P2),
        );
    }

    #[test]
    fn combined_shadow_key_matches_two_pass_reference() {
        let board = Board::new(3, 3);
        for p1 in 0..=board.all_cells_mask {
            for p2 in 0..=board.all_cells_mask {
                for turn in [P1, P2] {
                    assert_eq!(
                        board.shadow_key(p1, p2, turn),
                        reference_shadow_key(&board, p1, p2, turn)
                    );
                }
            }
        }
    }

    #[test]
    fn three_row_bit_symmetries_match_generic_canonicalization() {
        let board = Board::new(3, 5);
        for mask in 0..=board.all_cells_mask {
            let mut generic: Vec<u64> = board
                .transform_byte_tables
                .iter()
                .map(|transform| board.transform_mask(mask, transform))
                .collect();
            generic.sort_unstable();
            let rotated = board.reflect_mask(mask);
            let mut fast = vec![
                board.flip_three_rows(mask),
                rotated,
                board.flip_three_rows(rotated),
            ];
            fast.sort_unstable();
            assert_eq!(fast, generic);
        }

        for p1 in (0..=board.all_cells_mask).step_by(31) {
            let p2 = p1.wrapping_mul(0x5a5b) & board.all_cells_mask;
            for turn in [P1, P2] {
                assert_eq!(
                    board.shadow_key(p1, p2, turn),
                    reference_shadow_key(&board, p1, p2, turn)
                );
            }
        }
    }

    #[test]
    fn reflection_pairing_certificate_requires_color_swapped_legals() {
        let board = Board::new(3, 3);
        let p1_legal = (1u64 << 0) | (1u64 << 1);
        let p2_legal = (1u64 << 8) | (1u64 << 7);

        assert!(board.has_reflection_pairing_certificate(p1_legal, p2_legal, P1));
        assert!(board.has_reflection_pairing_certificate(p1_legal, p2_legal, P2));
        assert!(!board.has_reflection_pairing_certificate(
            p1_legal | (1u64 << 4),
            p2_legal | (1u64 << 4),
            P1,
        ));
        assert!(!board.has_reflection_pairing_certificate(
            p1_legal,
            p2_legal ^ (1u64 << 7),
            P1,
        ));
    }

    #[test]
    fn bit_reversal_half_turn_matches_cell_mapping() {
        for (m, n) in [(3, 3), (3, 5), (5, 7)] {
            let board = Board::new(m, n);
            for cell in 0..board.num_cells {
                assert_eq!(
                    board.reflect_mask(1u64 << cell),
                    1u64 << board.reflected_cell[cell]
                );
            }
        }
    }

    #[test]
    fn paired_moves_preserve_reflected_legal_masks() {
        let board = Board::new(3, 3);
        let p1_legal = (1u64 << 0) | (1u64 << 1);
        let p2_legal = (1u64 << 8) | (1u64 << 7);
        let (after_p1, after_p2) = board.child_legals(p1_legal, p2_legal, P1, 1u64 << 0);
        assert_ne!(after_p2 & (1u64 << 8), 0);

        let (paired_p1, paired_p2) =
            board.child_legals(after_p1, after_p2, P2, 1u64 << 8);
        assert_eq!(board.reflect_mask(paired_p1), paired_p2);
    }
}
