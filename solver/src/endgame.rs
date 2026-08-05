use dashmap::mapref::entry::Entry;
use dashmap::DashMap;
use rustc_hash::FxBuildHasher;
use rustc_hash::FxHashMap;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU32, Ordering as AtomicOrdering};
use std::sync::Arc;

const BLOCK_P1: u8 = 1;
const BLOCK_P2: u8 = 2;
const DEAD: u8 = BLOCK_P1 | BLOCK_P2;
const MAX_LOCAL_CELLS: usize = 14;
const CACHE_VERSION: i64 = 1;
const CACHE_FILENAME: &str = "cgt_components_rs.pkl";
const COMPONENT_BAG_MIN_BOARD_CELLS: usize = 33;
const COMPONENT_BAG_MIN_COMPONENTS: usize = 4;
const COMPONENT_BAG_LARGE_BOARD_CELLS: usize = 39;
const COMPONENT_BAG_LARGE_BOARD_MIN_COMPONENTS: usize = 3;
const COMPONENT_BAG_INLINE_IDS: usize = 4;
const ZERO_DYADIC: Dyadic = Dyadic { num: 0, shift: 0 };
const ZERO_VALUE: Value = Value {
    number: ZERO_DYADIC,
    star: false,
};

fn component_bag_min_components(board_cells: usize) -> usize {
    if board_cells >= COMPONENT_BAG_LARGE_BOARD_CELLS {
        COMPONENT_BAG_LARGE_BOARD_MIN_COMPONENTS
    } else {
        COMPONENT_BAG_MIN_COMPONENTS
    }
}

fn component_bag_enabled(board_cells: usize, board_columns: usize) -> bool {
    if board_cells < COMPONENT_BAG_MIN_BOARD_CELLS {
        return false;
    }
    let board_rows = board_cells / board_columns;
    board_cells >= COMPONENT_BAG_LARGE_BOARD_CELLS || board_rows == 3 || board_columns == 3
}

#[derive(Clone, Copy, Default)]
pub struct EndgameStats {
    pub raw_cache_hits: u64,
    pub canonical_cache_hits: u64,
    pub cgt_misses: u64,
    pub component_evaluations: u64,
    pub reduction_calls: u64,
    pub reduction_component_evaluations: u64,
    pub reduction_column_all_small_exits: u64,
    pub reduction_single_component_exits: u64,
    pub reduction_all_small_exits: u64,
    pub reduction_multi_oversized: u64,
    pub reduction_changes: u64,
    pub conjugate_pairs_removed: u64,
    pub zero_components_removed: u64,
    pub zero_sum_cells_removed: u64,
    pub reductions_to_empty: u64,
    pub component_bag_queries: u64,
    pub component_bag_hits: u64,
    pub component_bag_local_hits: u64,
    pub component_bag_inserts: u64,
    pub component_bag_local_duplicate_inserts: u64,
    pub component_bag_shared_queries: u64,
    pub component_bag_shared_hits: u64,
    pub component_bag_shared_inserts: u64,
    pub component_bag_shared_duplicate_inserts: u64,
    pub component_bag_raw_id_hits: u64,
    pub component_bag_signature_hits: u64,
    pub component_signature_shared_queries: u64,
    pub component_signature_shared_hits: u64,
    pub component_signature_shared_inserts: u64,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Hash, PartialEq, Serialize)]
struct Dyadic {
    num: i64,
    shift: u8,
}

impl Dyadic {
    fn new(mut num: i64, mut shift: u8) -> Dyadic {
        if num == 0 {
            return Dyadic { num: 0, shift: 0 };
        }
        while shift > 0 && num % 2 == 0 {
            num /= 2;
            shift -= 1;
        }
        Dyadic { num, shift }
    }

    fn zero() -> Dyadic {
        Dyadic { num: 0, shift: 0 }
    }

    fn from_int(value: i64) -> Dyadic {
        Dyadic {
            num: value,
            shift: 0,
        }
    }

    fn add(self, other: Dyadic) -> Dyadic {
        let shift = self.shift.max(other.shift);
        let left = (self.num as i128) << (shift - self.shift);
        let right = (other.num as i128) << (shift - other.shift);
        Dyadic::new((left + right).try_into().expect("dyadic overflow"), shift)
    }

    fn sub(self, other: Dyadic) -> Dyadic {
        self.add(other.neg())
    }

    fn neg(self) -> Dyadic {
        Dyadic {
            num: -self.num,
            shift: self.shift,
        }
    }

    fn floor_int(self) -> i64 {
        if self.shift == 0 {
            return self.num;
        }
        div_floor(self.num, 1i64 << self.shift)
    }

    fn ceil_int(self) -> i64 {
        -self.neg().floor_int()
    }

    fn floor_after_mul_pow2(self, pow: u8) -> i64 {
        if pow >= self.shift {
            self.num << (pow - self.shift)
        } else {
            div_floor(self.num, 1i64 << (self.shift - pow))
        }
    }
}

impl Ord for Dyadic {
    fn cmp(&self, other: &Self) -> Ordering {
        let shift = self.shift.max(other.shift);
        let left = (self.num as i128) << (shift - self.shift);
        let right = (other.num as i128) << (shift - other.shift);
        left.cmp(&right)
    }
}

impl PartialOrd for Dyadic {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

fn div_floor(num: i64, den: i64) -> i64 {
    let q = num / den;
    let r = num % den;
    if r != 0 && ((r > 0) != (den > 0)) {
        q - 1
    } else {
        q
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Hash, PartialEq, Serialize)]
struct Value {
    number: Dyadic,
    star: bool,
}

#[derive(Clone, Copy, Debug, Default, Deserialize, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize)]
struct LocalKey {
    len: u8,
    codes: [u16; MAX_LOCAL_CELLS],
}

#[derive(Deserialize, Serialize)]
struct CacheEntry {
    key: LocalKey,
    value: Value,
}

#[derive(Deserialize, Serialize)]
struct CachePayload {
    version: i64,
    max_local_cells: i64,
    entries: Vec<CacheEntry>,
}

impl Value {
    fn zero() -> Value {
        Value {
            number: Dyadic::zero(),
            star: false,
        }
    }

    fn add(self, other: Value) -> Value {
        Value {
            number: self.number.add(other.number),
            star: self.star ^ other.star,
        }
    }

    fn neg(self) -> Value {
        Value {
            number: self.number.neg(),
            star: self.star,
        }
    }
}

impl Ord for Value {
    fn cmp(&self, other: &Self) -> Ordering {
        self.number
            .cmp(&other.number)
            .then_with(|| self.star.cmp(&other.star))
    }
}

impl PartialOrd for Value {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

#[derive(Clone)]
struct Game {
    lefts: Vec<usize>,
    rights: Vec<usize>,
}

struct CgtEngine {
    games: Vec<Game>,
    intern: FxHashMap<(Vec<usize>, Vec<usize>), usize>,
    le_memo: FxHashMap<(usize, usize), bool>,
    add_memo: FxHashMap<(usize, usize), usize>,
    canon_memo: FxHashMap<usize, usize>,
    number_games: FxHashMap<Dyadic, usize>,
    number_values: FxHashMap<usize, Option<Dyadic>>,
    options_memo: FxHashMap<OptionsKey, Value>,
    zero: usize,
    star: usize,
}

#[derive(Clone, Copy, Eq, Hash, PartialEq)]
struct OptionsKey {
    left_len: u8,
    right_len: u8,
    lefts: [Value; MAX_LOCAL_CELLS],
    rights: [Value; MAX_LOCAL_CELLS],
}

impl CgtEngine {
    fn new() -> CgtEngine {
        let mut engine = CgtEngine {
            games: Vec::new(),
            intern: FxHashMap::default(),
            le_memo: FxHashMap::default(),
            add_memo: FxHashMap::default(),
            canon_memo: FxHashMap::default(),
            number_games: FxHashMap::default(),
            number_values: FxHashMap::default(),
            options_memo: FxHashMap::default(),
            zero: 0,
            star: 0,
        };
        let zero = engine.make(Vec::new(), Vec::new());
        let star = engine.make(vec![zero], vec![zero]);
        engine.zero = zero;
        engine.star = star;
        engine.number_games.insert(Dyadic::zero(), zero);
        engine.canon_memo.insert(zero, zero);
        engine
    }

    fn make(&mut self, mut lefts: Vec<usize>, mut rights: Vec<usize>) -> usize {
        lefts.sort_unstable();
        lefts.dedup();
        rights.sort_unstable();
        rights.dedup();
        let key = (lefts, rights);
        if let Some(&uid) = self.intern.get(&key) {
            return uid;
        }
        let uid = self.games.len();
        self.games.push(Game {
            lefts: key.0.clone(),
            rights: key.1.clone(),
        });
        self.intern.insert(key, uid);
        uid
    }

    fn le(&mut self, g: usize, h: usize) -> bool {
        if g == h {
            return true;
        }
        if let Some(&cached) = self.le_memo.get(&(g, h)) {
            return cached;
        }

        let mut result = true;
        let g_left_len = self.games[g].lefts.len();
        for index in 0..g_left_len {
            let gl = self.games[g].lefts[index];
            if self.le(h, gl) {
                result = false;
                break;
            }
        }
        if result {
            let h_right_len = self.games[h].rights.len();
            for index in 0..h_right_len {
                let hr = self.games[h].rights[index];
                if self.le(hr, g) {
                    result = false;
                    break;
                }
            }
        }
        self.le_memo.insert((g, h), result);
        result
    }

    fn add(&mut self, g: usize, h: usize) -> usize {
        if g == self.zero {
            return h;
        }
        if h == self.zero {
            return g;
        }
        let key = if g <= h { (g, h) } else { (h, g) };
        if let Some(&cached) = self.add_memo.get(&key) {
            return cached;
        }

        let g_left_len = self.games[g].lefts.len();
        let h_left_len = self.games[h].lefts.len();
        let mut lefts = Vec::with_capacity(g_left_len + h_left_len);
        for index in 0..g_left_len {
            let gl = self.games[g].lefts[index];
            lefts.push(self.add(gl, h));
        }
        for index in 0..h_left_len {
            let hl = self.games[h].lefts[index];
            lefts.push(self.add(g, hl));
        }

        let g_right_len = self.games[g].rights.len();
        let h_right_len = self.games[h].rights.len();
        let mut rights = Vec::with_capacity(g_right_len + h_right_len);
        for index in 0..g_right_len {
            let gr = self.games[g].rights[index];
            rights.push(self.add(gr, h));
        }
        for index in 0..h_right_len {
            let hr = self.games[h].rights[index];
            rights.push(self.add(g, hr));
        }

        let result = self.make(lefts, rights);
        self.add_memo.insert(key, result);
        result
    }

    fn filter_dominated(&mut self, options: &[usize], keep_larger: bool) -> Vec<usize> {
        let mut kept = Vec::new();
        for &g in options {
            let mut dominated = false;
            for &h in options {
                if g == h {
                    continue;
                }
                let worse = if keep_larger {
                    self.le(g, h)
                } else {
                    self.le(h, g)
                };
                if worse {
                    let equal = if keep_larger {
                        self.le(h, g)
                    } else {
                        self.le(g, h)
                    };
                    if !equal || h < g {
                        dominated = true;
                        break;
                    }
                }
            }
            if !dominated {
                kept.push(g);
            }
        }
        kept
    }

    fn canonical(&mut self, g: usize) -> usize {
        if let Some(&cached) = self.canon_memo.get(&g) {
            return cached;
        }

        let left_len = self.games[g].lefts.len();
        let mut lefts = Vec::with_capacity(left_len);
        for index in 0..left_len {
            let option = self.games[g].lefts[index];
            lefts.push(self.canonical(option));
        }
        let right_len = self.games[g].rights.len();
        let mut rights = Vec::with_capacity(right_len);
        for index in 0..right_len {
            let option = self.games[g].rights[index];
            rights.push(self.canonical(option));
        }

        loop {
            lefts = self.filter_dominated(&lefts, true);
            rights = self.filter_dominated(&rights, false);
            let current = self.make(lefts.clone(), rights.clone());

            let mut changed = false;
            let mut new_lefts = Vec::new();
            for gl in &lefts {
                let mut reverser = None;
                let right_len = self.games[*gl].rights.len();
                for index in 0..right_len {
                    let glr = self.games[*gl].rights[index];
                    if self.le(glr, current) {
                        reverser = Some(glr);
                        break;
                    }
                }
                if let Some(reverser) = reverser {
                    new_lefts.extend_from_slice(&self.games[reverser].lefts);
                    changed = true;
                } else {
                    new_lefts.push(*gl);
                }
            }

            let mut new_rights = Vec::new();
            for gr in &rights {
                let mut reverser = None;
                let left_len = self.games[*gr].lefts.len();
                for index in 0..left_len {
                    let grl = self.games[*gr].lefts[index];
                    if self.le(current, grl) {
                        reverser = Some(grl);
                        break;
                    }
                }
                if let Some(reverser) = reverser {
                    new_rights.extend_from_slice(&self.games[reverser].rights);
                    changed = true;
                } else {
                    new_rights.push(*gr);
                }
            }

            if !changed {
                self.canon_memo.insert(g, current);
                self.canon_memo.insert(current, current);
                return current;
            }
            lefts = new_lefts;
            rights = new_rights;
        }
    }

    fn number_game(&mut self, value: Dyadic) -> usize {
        if let Some(&cached) = self.number_games.get(&value) {
            return cached;
        }

        let game = if value.shift == 0 {
            if value.num == 0 {
                self.zero
            } else if value.num > 0 {
                let left = self.number_game(Dyadic::from_int(value.num - 1));
                self.make(vec![left], Vec::new())
            } else {
                let right = self.number_game(Dyadic::from_int(value.num + 1));
                self.make(Vec::new(), vec![right])
            }
        } else {
            let step = Dyadic::new(1, value.shift);
            let left = self.number_game(value.sub(step));
            let right = self.number_game(value.add(step));
            self.make(vec![left], vec![right])
        };

        self.number_games.insert(value, game);
        self.canon_memo.insert(game, game);
        game
    }

    fn simplest_between(&mut self, low: Option<Dyadic>, high: Option<Dyadic>) -> Dyadic {
        match (low, high) {
            (None, None) => Dyadic::zero(),
            (None, Some(high)) => {
                if high > Dyadic::zero() {
                    Dyadic::zero()
                } else if high.shift == 0 {
                    Dyadic::from_int(high.ceil_int() - 1)
                } else {
                    Dyadic::from_int(high.floor_int())
                }
            }
            (Some(low), None) => {
                if low < Dyadic::zero() {
                    Dyadic::zero()
                } else {
                    Dyadic::from_int(low.floor_int() + 1)
                }
            }
            (Some(low), Some(high)) => {
                debug_assert!(low < high);
                if low < Dyadic::zero() && Dyadic::zero() < high {
                    return Dyadic::zero();
                }
                if low >= Dyadic::zero() {
                    let candidate = Dyadic::from_int(low.floor_int() + 1);
                    if candidate < high {
                        return candidate;
                    }
                } else {
                    let candidate = Dyadic::from_int(high.ceil_int() - 1);
                    if candidate > low {
                        return candidate;
                    }
                }

                let mut pow = 1u8;
                loop {
                    let numerator = low.floor_after_mul_pow2(pow) + 1;
                    let candidate = Dyadic::new(numerator, pow);
                    if candidate < high {
                        return candidate;
                    }
                    pow += 1;
                }
            }
        }
    }

    fn number_value(&mut self, g: usize) -> Option<Dyadic> {
        if self.number_values.contains_key(&g) {
            return self.number_values[&g];
        }

        let mut result = None;
        if g == self.zero {
            result = Some(Dyadic::zero());
        } else if self.games[g].lefts.len() <= 1 && self.games[g].rights.len() <= 1 {
            let left = self.games[g].lefts.first().copied();
            let right = self.games[g].rights.first().copied();
            let low = left.and_then(|left| self.number_value(left));
            let high = right.and_then(|right| self.number_value(right));
            if (left.is_none() || low.is_some()) && (right.is_none() || high.is_some()) {
                if low.is_none() || high.is_none() || low < high {
                    let candidate = self.simplest_between(low, high);
                    if self.number_game(candidate) == g {
                        result = Some(candidate);
                    }
                }
            }
        }

        self.number_values.insert(g, result);
        result
    }

    fn value_to_game(&mut self, value: Value) -> usize {
        let number = self.number_game(value.number);
        if !value.star {
            return number;
        }
        let game = self.make(vec![number], vec![number]);
        self.canonical(game)
    }

    fn extract_value(&mut self, g: usize) -> Value {
        if let Some(number) = self.number_value(g) {
            return Value {
                number,
                star: false,
            };
        }
        let plus_star = self.add(g, self.star);
        let canonical = self.canonical(plus_star);
        if let Some(number) = self.number_value(canonical) {
            return Value { number, star: true };
        }
        panic!("Col component value was not a number or number plus star");
    }

    fn value_of_options(&mut self, left_values: &[Value], right_values: &[Value]) -> Value {
        let key = options_key(left_values, right_values);
        if let Some(&cached) = self.options_memo.get(&key) {
            return cached;
        }

        let game_lefts = key
            .lefts
            .iter()
            .take(key.left_len as usize)
            .map(|&value| self.value_to_game(value))
            .collect();
        let game_rights = key
            .rights
            .iter()
            .take(key.right_len as usize)
            .map(|&value| self.value_to_game(value))
            .collect();
        let game = self.make(game_lefts, game_rights);
        let canonical = self.canonical(game);
        let result = self.extract_value(canonical);
        self.options_memo.insert(key, result);
        result
    }
}

fn options_key(left_values: &[Value], right_values: &[Value]) -> OptionsKey {
    debug_assert!(left_values.len() <= MAX_LOCAL_CELLS);
    debug_assert!(right_values.len() <= MAX_LOCAL_CELLS);

    let mut lefts = [ZERO_VALUE; MAX_LOCAL_CELLS];
    let mut rights = [ZERO_VALUE; MAX_LOCAL_CELLS];
    lefts[..left_values.len()].copy_from_slice(left_values);
    rights[..right_values.len()].copy_from_slice(right_values);
    let left_len = sort_dedup_values(&mut lefts, left_values.len());
    let right_len = sort_dedup_values(&mut rights, right_values.len());

    OptionsKey {
        left_len: left_len as u8,
        right_len: right_len as u8,
        lefts,
        rights,
    }
}

fn sort_dedup_values(values: &mut [Value; MAX_LOCAL_CELLS], len: usize) -> usize {
    values[..len].sort_unstable();
    let mut out = 0usize;
    for index in 0..len {
        if out == 0 || values[index] != values[out - 1] {
            values[out] = values[index];
            out += 1;
        }
    }
    for value in values.iter_mut().take(MAX_LOCAL_CELLS).skip(out) {
        *value = ZERO_VALUE;
    }
    out
}

pub struct EndgameEvaluator {
    max_component_size: u32,
    shapes: FxHashMap<u64, LocalShape>,
    raw_values: FxHashMap<LocalKey, Value>,
    values: FxHashMap<LocalKey, Value>,
    shared: Option<Arc<SharedEndgameCache>>,
    cgt: CgtEngine,
    component_signature_ids: FxHashMap<Vec<u16>, u32>,
    raw_component_ids: FxHashMap<u128, u32>,
    component_bag_outcomes: FxHashMap<ComponentBagKey, bool>,
    share_component_bags: bool,
    reduction_components: [u64; 64],
    reduction_component_count: u8,
    stats: EndgameStats,
}

/// A position after safely deleting disjoint zero-valued summands.
pub struct ComponentReduction {
    pub legal_p1: u64,
    pub legal_p2: u64,
    pub changed: bool,
    pub component_bag_candidate: bool,
}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct ComponentBagKey {
    private_singleton_score: i8,
    shared_singleton_parity: bool,
    components: ComponentIds,
}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
enum ComponentIds {
    Inline {
        len: u8,
        ids: [u32; COMPONENT_BAG_INLINE_IDS],
    },
    Heap(Box<[u32]>),
}

impl ComponentIds {
    fn from_sorted(ids: &[u32]) -> ComponentIds {
        if ids.len() <= COMPONENT_BAG_INLINE_IDS {
            let mut inline = [0; COMPONENT_BAG_INLINE_IDS];
            inline[..ids.len()].copy_from_slice(ids);
            ComponentIds::Inline {
                len: ids.len() as u8,
                ids: inline,
            }
        } else {
            ComponentIds::Heap(ids.into())
        }
    }
}

pub enum ComponentBagProbe {
    Ineligible,
    Hit(bool),
    Miss(ComponentBagKey),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EndgameEvaluation {
    Solved(bool),
    SingleLocalComponent,
    OversizedMiss,
}

pub struct SharedEndgameCache {
    raw_values: DashMap<LocalKey, Value, FxBuildHasher>,
    values: DashMap<LocalKey, Value, FxBuildHasher>,
    component_signature_ids: DashMap<Vec<u16>, u32, FxBuildHasher>,
    next_component_signature_id: AtomicU32,
    component_bag_outcomes: DashMap<ComponentBagKey, bool, FxBuildHasher>,
}

impl SharedEndgameCache {
    pub fn new() -> SharedEndgameCache {
        SharedEndgameCache {
            raw_values: DashMap::with_hasher(FxBuildHasher),
            values: DashMap::with_hasher(FxBuildHasher),
            component_signature_ids: DashMap::with_hasher(FxBuildHasher),
            next_component_signature_id: AtomicU32::new(0),
            component_bag_outcomes: DashMap::with_hasher(FxBuildHasher),
        }
    }

    pub fn canonical_len(&self) -> usize {
        self.values.len()
    }

    fn intern_component_signature(&self, signature: &[u16]) -> (u32, bool) {
        if let Some(id) = self.component_signature_ids.get(signature) {
            return (*id, true);
        }
        match self.component_signature_ids.entry(signature.to_vec()) {
            Entry::Occupied(entry) => (*entry.get(), true),
            Entry::Vacant(entry) => {
                let id = self
                    .next_component_signature_id
                    .fetch_update(
                        AtomicOrdering::Relaxed,
                        AtomicOrdering::Relaxed,
                        |next| next.checked_add(1),
                    )
                    .expect("component signature ID space exhausted");
                entry.insert(id);
                (id, false)
            }
        }
    }

    fn component_bag_outcome(&self, key: &ComponentBagKey) -> Option<bool> {
        self.component_bag_outcomes.get(key).map(|entry| *entry)
    }

    fn insert_component_bag(&self, key: ComponentBagKey, wins: bool) -> Option<bool> {
        match self.component_bag_outcomes.entry(key) {
            Entry::Occupied(entry) => Some(*entry.get()),
            Entry::Vacant(entry) => {
                entry.insert(wins);
                None
            }
        }
    }

    fn insert_loaded(&self, key: LocalKey, value: Value) {
        self.values.insert(key, value);
    }

    fn canonical_entries(&self) -> Vec<CacheEntry> {
        let mut entries: Vec<CacheEntry> = self
            .values
            .iter()
            .map(|entry| CacheEntry {
                key: *entry.key(),
                value: *entry.value(),
            })
            .collect();
        entries.sort_unstable_by_key(|entry| entry.key);
        entries
    }
}

pub fn cache_path(root: &Path) -> PathBuf {
    root.join(CACHE_FILENAME)
}

pub fn load_shared_cache(root: &Path) -> Result<(Arc<SharedEndgameCache>, usize), String> {
    let cache = Arc::new(SharedEndgameCache::new());
    let path = cache_path(root);
    if !path.is_file() {
        return Ok((cache, 0));
    }

    let bytes = fs::read(&path).map_err(|err| err.to_string())?;
    let payload: CachePayload =
        serde_pickle::from_slice(&bytes, Default::default()).map_err(|err| err.to_string())?;
    if payload.version != CACHE_VERSION {
        return Err(format!(
            "unsupported CGT cache version {} in {}",
            payload.version,
            path.display()
        ));
    }
    if payload.max_local_cells != MAX_LOCAL_CELLS as i64 {
        return Err(format!(
            "CGT cache {} was built for max-local-cells {}, expected {}",
            path.display(),
            payload.max_local_cells,
            MAX_LOCAL_CELLS
        ));
    }

    let mut loaded = 0usize;
    for entry in payload.entries {
        cache.insert_loaded(entry.key, entry.value);
        loaded += 1;
    }
    Ok((cache, loaded))
}

pub fn save_shared_cache(
    root: &Path,
    cache: &SharedEndgameCache,
    loaded_count: usize,
) -> Result<Option<(PathBuf, usize)>, String> {
    let entries = cache.canonical_entries();
    if entries.len() <= loaded_count {
        return Ok(None);
    }

    fs::create_dir_all(root).map_err(|err| err.to_string())?;
    let path = cache_path(root);
    let payload = CachePayload {
        version: CACHE_VERSION,
        max_local_cells: MAX_LOCAL_CELLS as i64,
        entries,
    };
    let saved_count = payload.entries.len();
    let bytes =
        serde_pickle::to_vec(&payload, Default::default()).map_err(|err| err.to_string())?;
    let tmp = path.with_extension("pkl.tmp");
    fs::write(&tmp, bytes).map_err(|err| err.to_string())?;
    fs::rename(&tmp, &path).map_err(|err| err.to_string())?;
    Ok(Some((path, saved_count)))
}

fn effective_component_limit(configured: u32, open_cells: u32) -> u32 {
    if configured > 12 && open_cells > configured {
        12
    } else {
        configured
    }
}

impl EndgameEvaluator {
    pub fn new(
        max_component_size: u32,
        shared: Option<Arc<SharedEndgameCache>>,
    ) -> EndgameEvaluator {
        assert!(
            max_component_size <= MAX_LOCAL_CELLS as u32,
            "packed endgame keys support components up to MAX_LOCAL_CELLS"
        );
        EndgameEvaluator {
            max_component_size,
            shapes: FxHashMap::default(),
            raw_values: FxHashMap::default(),
            values: FxHashMap::default(),
            shared,
            cgt: CgtEngine::new(),
            component_signature_ids: FxHashMap::default(),
            raw_component_ids: FxHashMap::default(),
            component_bag_outcomes: FxHashMap::default(),
            share_component_bags: false,
            reduction_components: [0; 64],
            reduction_component_count: 0,
            stats: EndgameStats::default(),
        }
    }

    pub fn stats(&self) -> EndgameStats {
        self.stats
    }

    /// Enable exact cross-worker component interning and solved-bag reuse.
    /// This must happen before the evaluator assigns any worker-local IDs.
    pub fn enable_shared_component_bags(&mut self) {
        assert!(
            self.component_signature_ids.is_empty()
                && self.raw_component_ids.is_empty()
                && self.component_bag_outcomes.is_empty(),
            "shared component bags must be enabled before the first bag query"
        );
        self.share_component_bags = self.shared.is_some();
    }

    /// Query an exact actor-relative multiset key for a fragmented position.
    /// Components are canonicalized geometrically but never color-swapped
    /// independently. Duplicate component IDs remain in the sorted bag.
    pub fn probe_component_bag(
        &mut self,
        n: usize,
        legal_p1: u64,
        legal_p2: u64,
        turn: u8,
    ) -> ComponentBagProbe {
        let component_count = self.reduction_component_count as usize;
        if component_count < COMPONENT_BAG_LARGE_BOARD_MIN_COMPONENTS {
            return ComponentBagProbe::Ineligible;
        }

        self.stats.component_bag_queries += 1;
        let (actor, opponent) = if turn == 0 {
            (legal_p1, legal_p2)
        } else {
            (legal_p2, legal_p1)
        };
        let mut ids = [0u32; 64];
        let mut id_count = 0usize;
        let mut private_singleton_score = 0i8;
        let mut shared_singleton_parity = false;
        for index in 0..component_count {
            let component = self.reduction_components[index];
            if component.is_power_of_two() {
                let actor_can_play = actor & component != 0;
                let opponent_can_play = opponent & component != 0;
                match (actor_can_play, opponent_can_play) {
                    (true, true) => shared_singleton_parity ^= true,
                    (true, false) => private_singleton_score += 1,
                    (false, true) => private_singleton_score -= 1,
                    (false, false) => unreachable!("component must contain a legal move"),
                }
                continue;
            }
            let raw_key = (((actor & component) as u128) << 63)
                | (opponent & component) as u128;
            let id = if let Some(&id) = self.raw_component_ids.get(&raw_key) {
                self.stats.component_bag_raw_id_hits += 1;
                id
            } else {
                let (signature, signature_len) =
                    component_signature_fixed(n, component, actor, opponent);
                let signature = &signature[..signature_len];
                let id = if let Some(&id) = self.component_signature_ids.get(signature) {
                    self.stats.component_bag_signature_hits += 1;
                    id
                } else if self.share_component_bags {
                    self.stats.component_signature_shared_queries += 1;
                    let (id, hit) = self
                        .shared
                        .as_ref()
                        .expect("shared component bags require a shared cache")
                        .intern_component_signature(signature);
                    if hit {
                        self.stats.component_signature_shared_hits += 1;
                    } else {
                        self.stats.component_signature_shared_inserts += 1;
                    }
                    self.component_signature_ids
                        .insert(signature.to_vec(), id);
                    id
                } else {
                    let id = self.component_signature_ids.len() as u32;
                    self.component_signature_ids.insert(signature.to_vec(), id);
                    id
                };
                self.raw_component_ids.insert(raw_key, id);
                id
            };
            ids[id_count] = id;
            id_count += 1;
        }
        ids[..id_count].sort_unstable();
        let key = ComponentBagKey {
            private_singleton_score,
            shared_singleton_parity,
            components: ComponentIds::from_sorted(&ids[..id_count]),
        };
        if let Some(&wins) = self.component_bag_outcomes.get(&key) {
            self.stats.component_bag_hits += 1;
            self.stats.component_bag_local_hits += 1;
            ComponentBagProbe::Hit(wins)
        } else if self.share_component_bags {
            self.stats.component_bag_shared_queries += 1;
            if let Some(wins) = self
                .shared
                .as_ref()
                .expect("shared component bags require a shared cache")
                .component_bag_outcome(&key)
            {
                self.stats.component_bag_hits += 1;
                self.stats.component_bag_shared_hits += 1;
                self.component_bag_outcomes.insert(key, wins);
                self.stats.component_bag_inserts += 1;
                ComponentBagProbe::Hit(wins)
            } else {
                ComponentBagProbe::Miss(key)
            }
        } else {
            ComponentBagProbe::Miss(key)
        }
    }

    pub fn insert_component_bag(&mut self, key: ComponentBagKey, wins: bool) {
        let shared_key = self.share_component_bags.then(|| key.clone());
        let local_was_new = if let Some(previous) = self.component_bag_outcomes.insert(key, wins) {
            debug_assert_eq!(previous, wins, "component-bag outcome conflict");
            self.stats.component_bag_local_duplicate_inserts += 1;
            false
        } else {
            self.stats.component_bag_inserts += 1;
            true
        };
        if let Some(key) = shared_key {
            let previous = self
                .shared
                .as_ref()
                .expect("shared component bags require a shared cache")
                .insert_component_bag(key, wins);
            if let Some(previous) = previous {
                assert_eq!(previous, wins, "shared component-bag outcome conflict");
                if local_was_new {
                    self.stats.component_bag_shared_duplicate_inserts += 1;
                }
            } else {
                self.stats.component_bag_shared_inserts += 1;
            }
        }
    }

    fn retain_reduction_components(&mut self, components: &[u64], remove: u64) -> usize {
        let mut count = 0usize;
        for &component in components {
            if component & remove != 0 {
                debug_assert_eq!(component & !remove, 0);
                continue;
            }
            self.reduction_components[count] = component;
            count += 1;
        }
        self.reduction_component_count = count as u8;
        count
    }

    /// Delete disconnected summands that are provably zero without requiring
    /// every component to fit the local CGT cutoff.
    pub fn reduce_zero_summands(
        &mut self,
        n: usize,
        adjacency: &[u64],
        legal_p1: u64,
        legal_p2: u64,
    ) -> ComponentReduction {
        self.stats.reduction_calls += 1;
        self.reduction_component_count = 0;
        let combined = legal_p1 | legal_p2;
        let open_cells = combined.count_ones();
        let effective_max_component_size =
            effective_component_limit(self.max_component_size, open_cells);
        // With no more live cells than the local cutoff, every component is
        // necessarily small. `try_evaluate` handles such positions exactly,
        // so avoid discovering components only to take the all-small exit.
        if open_cells <= effective_max_component_size {
            self.stats.reduction_all_small_exits += 1;
            return ComponentReduction {
                legal_p1,
                legal_p2,
                changed: false,
                component_bag_candidate: false,
            };
        }
        // Dead columns partition a 3xn strip. If every resulting interval has
        // at most the cutoff's live cells, every component is necessarily
        // small and `try_evaluate` will handle the position exactly.
        if adjacency.len() == 3 * n {
            let row_mask = (1u64 << n) - 1;
            let mut live_columns =
                (combined | (combined >> n) | (combined >> (2 * n))) & row_mask;
            let mut all_intervals_small = true;
            while live_columns != 0 {
                let start = live_columns.trailing_zeros();
                let width = (live_columns >> start).trailing_ones();
                let columns = ((1u64 << width) - 1) << start;
                let interval = columns | (columns << n) | (columns << (2 * n));
                if (combined & interval).count_ones() > effective_max_component_size {
                    all_intervals_small = false;
                    break;
                }
                live_columns &= !columns;
            }
            if all_intervals_small {
                self.stats.reduction_column_all_small_exits += 1;
                self.stats.reduction_all_small_exits += 1;
                return ComponentReduction {
                    legal_p1,
                    legal_p2,
                    changed: false,
                    component_bag_candidate: false,
                };
            }
        }
        let mut remaining = combined;
        let mut components = [0u64; 64];
        let mut component_count = 0usize;
        let mut oversized_count = 0usize;
        while remaining != 0 {
            let component = if adjacency.len() == 3 * n {
                take_component_3xn(n, legal_p1, legal_p2, &mut remaining)
            } else {
                take_component(adjacency, legal_p1, legal_p2, &mut remaining)
            };
            components[component_count] = component;
            component_count += 1;
            oversized_count +=
                usize::from(component.count_ones() > effective_max_component_size);
        }
        let components = &components[..component_count];
        if component_count < 2 {
            self.stats.reduction_single_component_exits += 1;
            return ComponentReduction {
                legal_p1,
                legal_p2,
                changed: false,
                component_bag_candidate: false,
            };
        }
        // Fully small positions are already handled exactly by `try_evaluate`;
        // stripping them here only duplicates its work. This pass is for the
        // important case where an oversized component would otherwise make
        // the whole evaluator return `None`.
        if oversized_count == 0 {
            self.stats.reduction_all_small_exits += 1;
            return ComponentReduction {
                legal_p1,
                legal_p2,
                changed: false,
                component_bag_candidate: false,
            };
        }

        let mut remove = 0u64;
        if oversized_count > 1 {
            self.stats.reduction_multi_oversized += 1;
            let mut pending: FxHashMap<Vec<u16>, Vec<u64>> = FxHashMap::default();
            for &component in components {
                if component.count_ones() <= effective_max_component_size {
                    continue;
                }
                let signature = component_signature(n, component, legal_p1, legal_p2, false);
                let conjugate = component_signature(n, component, legal_p1, legal_p2, true);
                if signature == conjugate {
                    continue;
                }
                if let Some(mut matches) = pending.remove(&conjugate) {
                    let mate = matches.pop().expect("nonempty component signature bucket");
                    if !matches.is_empty() {
                        pending.insert(conjugate, matches);
                    }
                    remove |= component | mate;
                    self.stats.conjugate_pairs_removed += 1;
                } else {
                    pending.entry(signature).or_default().push(component);
                }
            }
        }

        let mut evaluated = [0u64; 64];
        let mut evaluated_count = 0usize;
        let mut total = Value::zero();
        for &component in components {
            if component.count_ones() > effective_max_component_size {
                continue;
            }
            let (shape, p1, p2) =
                self.local_shape_and_masks(n, legal_p1 & component, legal_p2 & component);
            self.stats.reduction_component_evaluations += 1;
            let value = self.component_value_local(&shape, p1, p2);
            if value == Value::zero() {
                remove |= component;
                self.stats.zero_components_removed += 1;
            }
            total = total.add(value);
            evaluated[evaluated_count] = component;
            evaluated_count += 1;
        }
        if evaluated_count > 1 && total == Value::zero() {
            for &component in &evaluated[..evaluated_count] {
                remove |= component;
            }
        }

        if remove == 0 {
            let component_bag_candidate = component_bag_enabled(adjacency.len(), n)
                && self.retain_reduction_components(components, remove)
                    >= component_bag_min_components(adjacency.len());
            return ComponentReduction {
                legal_p1,
                legal_p2,
                changed: false,
                component_bag_candidate,
            };
        }
        self.stats.zero_sum_cells_removed += remove.count_ones() as u64;
        let legal_p1 = legal_p1 & !remove;
        let legal_p2 = legal_p2 & !remove;
        if legal_p1 | legal_p2 == 0 {
            self.stats.reductions_to_empty += 1;
        }
        self.stats.reduction_changes += 1;
        let component_bag_candidate = component_bag_enabled(adjacency.len(), n)
            && self.retain_reduction_components(components, remove)
                >= component_bag_min_components(adjacency.len());
        ComponentReduction {
            legal_p1,
            legal_p2,
            changed: true,
            component_bag_candidate,
        }
    }

    pub fn try_evaluate(
        &mut self,
        n: usize,
        adjacency: &[u64],
        legal_p1: u64,
        legal_p2: u64,
        turn: u8,
    ) -> Option<bool> {
        match self.classify_position(n, adjacency, legal_p1, legal_p2, turn) {
            EndgameEvaluation::Solved(wins) => Some(wins),
            EndgameEvaluation::SingleLocalComponent
            | EndgameEvaluation::OversizedMiss => None,
        }
    }

    pub fn classify_position(
        &mut self,
        n: usize,
        adjacency: &[u64],
        legal_p1: u64,
        legal_p2: u64,
        turn: u8,
    ) -> EndgameEvaluation {
        let combined = legal_p1 | legal_p2;
        if combined == 0 {
            return EndgameEvaluation::Solved(false);
        }
        let effective_max_component_size =
            effective_component_limit(self.max_component_size, combined.count_ones());

        let mut remaining = combined;
        let mut component_count = 0usize;
        let mut first_local_component: Option<(u64, u64)> = None;
        let mut total = Value::zero();
        let mut used_known_value = false;
        while remaining != 0 {
            component_count += 1;
            let component_eval = match take_component_eval(
                n,
                adjacency,
                &mut remaining,
                legal_p1,
                legal_p2,
                effective_max_component_size,
            ) {
                Some(component_eval) => component_eval,
                None => return EndgameEvaluation::OversizedMiss,
            };
            match component_eval {
                ComponentEval::KnownValue(value) => {
                    if let Some((comp_p1, comp_p2)) = first_local_component.take() {
                        let (shape, p1, p2) = self.local_shape_and_masks(n, comp_p1, comp_p2);
                        total = total.add(self.component_value_local(&shape, p1, p2));
                    }
                    total = total.add(value);
                    used_known_value = true;
                }
                ComponentEval::Local(component) => {
                    let component_masks = (legal_p1 & component, legal_p2 & component);
                    if component_count == 1 && !used_known_value {
                        first_local_component = Some(component_masks);
                        continue;
                    }
                    if let Some((comp_p1, comp_p2)) = first_local_component.take() {
                        let (shape, p1, p2) = self.local_shape_and_masks(n, comp_p1, comp_p2);
                        total = total.add(self.component_value_local(&shape, p1, p2));
                    }
                    let (shape, p1, p2) =
                        self.local_shape_and_masks(n, component_masks.0, component_masks.1);
                    total = total.add(self.component_value_local(&shape, p1, p2));
                }
            }
        }

        if component_count < 2 && !used_known_value {
            return EndgameEvaluation::SingleLocalComponent;
        }

        let value = if turn == 0 { total } else { total.neg() };
        EndgameEvaluation::Solved(first_player_wins(value))
    }

    fn component_value_local(&mut self, shape: &LocalShape, p1_legal: u16, p2_legal: u16) -> Value {
        self.stats.component_evaluations += 1;
        let live = p1_legal | p2_legal;
        if live == 0 {
            return Value::zero();
        }
        if live.count_ones() == 1 {
            let bit = live & live.wrapping_neg();
            let tint = local_tint(bit, p1_legal, p2_legal);
            return single_cell_value(tint);
        }
        if let Some(value) = linear_chain_value_local(shape, p1_legal, p2_legal) {
            return value;
        }

        let raw_key = raw_shape_key_local(shape, p1_legal, p2_legal);
        if let Some(&cached) = self.raw_values.get(&raw_key) {
            self.stats.raw_cache_hits += 1;
            return cached;
        }
        if let Some(shared) = &self.shared {
            if let Some(cached) = shared.raw_values.get(&raw_key) {
                let value = *cached;
                self.stats.raw_cache_hits += 1;
                self.raw_values.insert(raw_key, value);
                return value;
            }
        }

        let (key, swapped) = canonical_key_local(shape, p1_legal, p2_legal);
        if let Some(&cached) = self.values.get(&key) {
            let value = if swapped { cached.neg() } else { cached };
            self.stats.canonical_cache_hits += 1;
            self.raw_values.insert(raw_key, value);
            return value;
        }
        if let Some(shared) = &self.shared {
            if let Some(cached) = shared.values.get(&key) {
                let cached = *cached;
                let value = if swapped { cached.neg() } else { cached };
                self.stats.canonical_cache_hits += 1;
                self.values.insert(key, cached);
                self.raw_values.insert(raw_key, value);
                return value;
            }
        }

        let mut left_values = [ZERO_VALUE; MAX_LOCAL_CELLS];
        let mut right_values = [ZERO_VALUE; MAX_LOCAL_CELLS];
        let mut left_len = 0usize;
        let mut right_len = 0usize;
        let mut left_moves = p1_legal;
        while left_moves != 0 {
            let bit = left_moves & left_moves.wrapping_neg();
            left_moves ^= bit;
            let cell = bit.trailing_zeros() as usize;
            let next_p1 = p1_legal & !(bit | shape.adj[cell]);
            let next_p2 = p2_legal & !bit;
            left_values[left_len] = self.position_value_local(shape, next_p1, next_p2);
            left_len += 1;
        }
        let mut right_moves = p2_legal;
        while right_moves != 0 {
            let bit = right_moves & right_moves.wrapping_neg();
            right_moves ^= bit;
            let cell = bit.trailing_zeros() as usize;
            let next_p1 = p1_legal & !bit;
            let next_p2 = p2_legal & !(bit | shape.adj[cell]);
            right_values[right_len] = self.position_value_local(shape, next_p1, next_p2);
            right_len += 1;
        }

        self.stats.cgt_misses += 1;
        let value = self
            .cgt
            .value_of_options(&left_values[..left_len], &right_values[..right_len]);
        self.values
            .insert(key, if swapped { value.neg() } else { value });
        self.raw_values.insert(raw_key, value);
        if let Some(shared) = &self.shared {
            shared
                .values
                .insert(key, if swapped { value.neg() } else { value });
            shared.raw_values.insert(raw_key, value);
        }
        value
    }

    fn local_shape_and_masks(
        &mut self,
        n: usize,
        legal_p1: u64,
        legal_p2: u64,
    ) -> (LocalShape, u16, u16) {
        let live = legal_p1 | legal_p2;
        let shape = if let Some(shape) = self.shapes.get(&live) {
            *shape
        } else {
            let shape = local_shape_from_live(n, live);
            self.shapes.insert(live, shape);
            shape
        };
        let (p1, p2) = local_masks_from_live(live, legal_p1, legal_p2);
        (shape, p1, p2)
    }

    fn position_value_local(&mut self, shape: &LocalShape, p1_legal: u16, p2_legal: u16) -> Value {
        let live = p1_legal | p2_legal;
        if live == 0 {
            return Value::zero();
        }
        let mut total = Value::zero();
        let mut remaining = live;
        while remaining != 0 {
            let component =
                take_local_component(shape, p1_legal, p2_legal, &mut remaining);
            total = total.add(self.component_value_local(
                shape,
                p1_legal & component,
                p2_legal & component,
            ));
        }
        total
    }
}

pub fn component_value_text(n: usize, legal_p1: u64, legal_p2: u64) -> Option<String> {
    let live = legal_p1 | legal_p2;
    if live.count_ones() as usize > MAX_LOCAL_CELLS {
        return None;
    }
    let (shape, p1, p2) = local_shape_from_masks(n, legal_p1, legal_p2);
    let mut evaluator = EndgameEvaluator::new(MAX_LOCAL_CELLS as u32, None);
    let value = evaluator.position_value_local(&shape, p1, p2);
    Some(format_value(value))
}

fn format_value(value: Value) -> String {
    let number = format_dyadic(value.number);
    if value.star {
        if value.number == Dyadic::zero() {
            "*".to_string()
        } else {
            format!("{number}+*")
        }
    } else {
        number
    }
}

fn format_dyadic(value: Dyadic) -> String {
    if value.shift == 0 {
        return value.num.to_string();
    }
    format!("{}/{}", value.num, 1i64 << value.shift)
}

#[derive(Clone, Copy)]
struct LocalShape {
    rows: [i16; MAX_LOCAL_CELLS],
    cols: [i16; MAX_LOCAL_CELLS],
    adj: [u16; MAX_LOCAL_CELLS],
}

fn local_shape_from_masks(n: usize, legal_p1: u64, legal_p2: u64) -> (LocalShape, u16, u16) {
    let live = legal_p1 | legal_p2;
    let shape = local_shape_from_live(n, live);
    let (p1, p2) = local_masks_from_live(live, legal_p1, legal_p2);
    (shape, p1, p2)
}

fn local_masks_from_live(live: u64, legal_p1: u64, legal_p2: u64) -> (u16, u16) {
    let mut p1 = 0u16;
    let mut p2 = 0u16;
    let mut len = 0usize;
    let mut combined = live;

    while combined != 0 {
        let bit = combined & combined.wrapping_neg();
        combined ^= bit;
        let local_bit = 1u16 << len;
        if legal_p1 & bit != 0 {
            p1 |= local_bit;
        }
        if legal_p2 & bit != 0 {
            p2 |= local_bit;
        }
        len += 1;
    }

    (p1, p2)
}

fn local_shape_from_live(n: usize, live: u64) -> LocalShape {
    let mut rows = [0i16; MAX_LOCAL_CELLS];
    let mut cols = [0i16; MAX_LOCAL_CELLS];
    let mut global_bits = [0u64; MAX_LOCAL_CELLS];
    let mut len = 0usize;
    let mut combined = live;

    while combined != 0 {
        let bit = combined & combined.wrapping_neg();
        combined ^= bit;
        let cell = bit.trailing_zeros() as usize;
        rows[len] = (cell / n) as i16;
        cols[len] = (cell % n) as i16;
        global_bits[len] = bit;
        len += 1;
    }
    debug_assert!(len <= MAX_LOCAL_CELLS);

    let mut adj = [0u16; MAX_LOCAL_CELLS];
    for i in 0..len {
        for j in (i + 1)..len {
            if (rows[i] - rows[j]).abs() + (cols[i] - cols[j]).abs() == 1 {
                adj[i] |= 1u16 << j;
                adj[j] |= 1u16 << i;
            }
        }
    }
    let _ = global_bits;

    LocalShape { rows, cols, adj }
}

fn local_tint(bit: u16, p1_legal: u16, p2_legal: u16) -> u8 {
    let mut tint = 0;
    if p1_legal & bit == 0 {
        tint |= BLOCK_P1;
    }
    if p2_legal & bit == 0 {
        tint |= BLOCK_P2;
    }
    tint
}

#[inline]
fn local_interaction_neighbors(
    shape: &LocalShape,
    cell: usize,
    bit: u16,
    p1_legal: u16,
    p2_legal: u16,
) -> u16 {
    let mut neighbors = 0;
    if p1_legal & bit != 0 {
        neighbors |= shape.adj[cell] & p1_legal;
    }
    if p2_legal & bit != 0 {
        neighbors |= shape.adj[cell] & p2_legal;
    }
    neighbors
}

fn take_local_component(
    shape: &LocalShape,
    p1_legal: u16,
    p2_legal: u16,
    remaining: &mut u16,
) -> u16 {
    let seed = *remaining & remaining.wrapping_neg();
    let mut stack = [0u16; MAX_LOCAL_CELLS];
    let mut stack_len = 1usize;
    stack[0] = seed;
    let mut component = seed;
    *remaining ^= seed;

    while stack_len > 0 {
        stack_len -= 1;
        let bit = stack[stack_len];
        let cell = bit.trailing_zeros() as usize;
        let mut neighbors =
            local_interaction_neighbors(shape, cell, bit, p1_legal, p2_legal) & !component;
        while neighbors != 0 {
            let neighbor = neighbors & neighbors.wrapping_neg();
            neighbors ^= neighbor;
            component |= neighbor;
            *remaining &= !neighbor;
            stack[stack_len] = neighbor;
            stack_len += 1;
        }
    }
    component
}

fn raw_shape_key_local(shape: &LocalShape, p1_legal: u16, p2_legal: u16) -> LocalKey {
    let live = p1_legal | p2_legal;
    debug_assert!(live != 0);

    let mut min_row = i16::MAX;
    let mut min_col = i16::MAX;
    let mut bits = live;
    while bits != 0 {
        let bit = bits & bits.wrapping_neg();
        bits ^= bit;
        let cell = bit.trailing_zeros() as usize;
        min_row = min_row.min(shape.rows[cell]);
        min_col = min_col.min(shape.cols[cell]);
    }

    let mut key = [0u16; MAX_LOCAL_CELLS];
    let mut len = 0usize;
    let mut bits = live;
    while bits != 0 {
        let bit = bits & bits.wrapping_neg();
        bits ^= bit;
        let cell = bit.trailing_zeros() as usize;
        let row = (shape.rows[cell] - min_row) as u16;
        let col = (shape.cols[cell] - min_col) as u16;
        debug_assert!(row < 16 && col < 16);
        key[len] = (row << 6) | (col << 2) | local_tint(bit, p1_legal, p2_legal) as u16;
        len += 1;
    }
    debug_assert!(key[..len].windows(2).all(|pair| pair[0] < pair[1]));
    LocalKey {
        len: len as u8,
        codes: key,
    }
}

fn canonical_key_local(shape: &LocalShape, p1_legal: u16, p2_legal: u16) -> (LocalKey, bool) {
    let live = p1_legal | p2_legal;
    debug_assert!(live != 0);

    let mut best_key: Option<LocalKey> = None;
    let mut best_swapped = false;
    for transform in 0..8 {
        let mut rows = [0i16; MAX_LOCAL_CELLS];
        let mut cols = [0i16; MAX_LOCAL_CELLS];
        let mut tints = [0u8; MAX_LOCAL_CELLS];
        let mut min_row = i16::MAX;
        let mut min_col = i16::MAX;
        let mut len = 0usize;
        let mut bits = live;
        while bits != 0 {
            let bit = bits & bits.wrapping_neg();
            bits ^= bit;
            let cell = bit.trailing_zeros() as usize;
            let (row, col) = transform_point(transform, shape.rows[cell], shape.cols[cell]);
            rows[len] = row;
            cols[len] = col;
            tints[len] = local_tint(bit, p1_legal, p2_legal);
            min_row = min_row.min(row);
            min_col = min_col.min(col);
            len += 1;
        }

        let mut key = [0u16; MAX_LOCAL_CELLS];
        for index in 0..len {
            let row = (rows[index] - min_row) as u16;
            let col = (cols[index] - min_col) as u16;
            debug_assert!(row < 16 && col < 16);
            key[index] = (row << 6) | (col << 2) | tints[index] as u16;
        }
        key[..len].sort_unstable();
        let normal = pack_key(&key[..len]);
        if best_key.map_or(true, |best| normal < best) {
            best_key = Some(normal);
            best_swapped = false;
        }

        for code in &mut key[..len] {
            *code = (*code & !3) | swap_tint((*code & 3) as u8) as u16;
        }
        debug_assert!(key[..len].windows(2).all(|pair| pair[0] < pair[1]));
        let swapped = pack_key(&key[..len]);
        if best_key.map_or(true, |best| swapped < best) {
            best_key = Some(swapped);
            best_swapped = true;
        }
    }

    (best_key.expect("local canonical key missing"), best_swapped)
}

fn first_player_wins(value: Value) -> bool {
    value.number > Dyadic::zero() || (value.number == Dyadic::zero() && value.star)
}

fn endpoint_chain_score(tint: u8) -> Option<i64> {
    match tint {
        0 => Some(0),
        BLOCK_P2 => Some(1),
        BLOCK_P1 => Some(-1),
        DEAD => None,
        _ => unreachable!(),
    }
}

fn single_cell_value(tint: u8) -> Value {
    match tint {
        0 => Value {
            number: Dyadic::zero(),
            star: true,
        },
        BLOCK_P1 => Value {
            number: Dyadic::from_int(-1),
            star: false,
        },
        BLOCK_P2 => Value {
            number: Dyadic::from_int(1),
            star: false,
        },
        DEAD => Value::zero(),
        _ => unreachable!(),
    }
}

#[inline]
fn interaction_neighbors(
    adjacency: &[u64],
    cell: usize,
    bit: u64,
    legal_p1: u64,
    legal_p2: u64,
) -> u64 {
    let mut neighbors = 0;
    if legal_p1 & bit != 0 {
        neighbors |= adjacency[cell] & legal_p1;
    }
    if legal_p2 & bit != 0 {
        neighbors |= adjacency[cell] & legal_p2;
    }
    neighbors
}

fn take_component(
    adjacency: &[u64],
    legal_p1: u64,
    legal_p2: u64,
    remaining: &mut u64,
) -> u64 {
    let seed = *remaining & remaining.wrapping_neg();
    let mut stack = [0u64; 64];
    let mut stack_len = 1usize;
    stack[0] = seed;
    let mut component = seed;
    *remaining ^= seed;

    while stack_len > 0 {
        stack_len -= 1;
        let bit = stack[stack_len];
        let cell = bit.trailing_zeros() as usize;
        let mut neighbors =
            interaction_neighbors(adjacency, cell, bit, legal_p1, legal_p2) & !component;
        while neighbors != 0 {
            let neighbor = neighbors & neighbors.wrapping_neg();
            neighbors ^= neighbor;
            component |= neighbor;
            *remaining &= !neighbor;
            stack[stack_len] = neighbor;
            stack_len += 1;
        }
    }
    component
}

fn take_component_3xn(
    n: usize,
    legal_p1: u64,
    legal_p2: u64,
    remaining: &mut u64,
) -> u64 {
    debug_assert!(n > 0 && 3 * n <= 63);
    let left_edge = 1u64 | (1u64 << n) | (1u64 << (2 * n));
    let right_edge = left_edge << (n - 1);
    let seed = *remaining & remaining.wrapping_neg();
    let mut component = seed;
    let mut frontier = seed;
    while frontier != 0 {
        let p1_frontier = frontier & legal_p1;
        let p1_horizontal =
            ((p1_frontier & !right_edge) << 1) | ((p1_frontier & !left_edge) >> 1);
        let p1_vertical = (p1_frontier << n) | (p1_frontier >> n);
        let p2_frontier = frontier & legal_p2;
        let p2_horizontal =
            ((p2_frontier & !right_edge) << 1) | ((p2_frontier & !left_edge) >> 1);
        let p2_vertical = (p2_frontier << n) | (p2_frontier >> n);
        frontier = (((p1_horizontal | p1_vertical) & legal_p1)
            | ((p2_horizontal | p2_vertical) & legal_p2))
            & !component;
        component |= frontier;
    }
    *remaining &= !component;
    component
}

fn component_signature(
    n: usize,
    component: u64,
    legal_p1: u64,
    legal_p2: u64,
    swapped: bool,
) -> Vec<u16> {
    let mut best: Option<Vec<u16>> = None;
    for transform in 0..8 {
        let mut points = Vec::with_capacity(component.count_ones() as usize);
        let mut min_row = i16::MAX;
        let mut min_col = i16::MAX;
        let mut bits = component;
        while bits != 0 {
            let bit = bits & bits.wrapping_neg();
            bits ^= bit;
            let cell = bit.trailing_zeros() as usize;
            let (row, col) = transform_point(transform, (cell / n) as i16, (cell % n) as i16);
            min_row = min_row.min(row);
            min_col = min_col.min(col);
            let tint = global_tint(bit, legal_p1, legal_p2);
            points.push((row, col, if swapped { swap_tint(tint) } else { tint }));
        }
        let mut key = Vec::with_capacity(points.len());
        for (row, col, tint) in points {
            let row = (row - min_row) as u16;
            let col = (col - min_col) as u16;
            debug_assert!(row < 64 && col < 64);
            key.push((row << 8) | (col << 2) | tint as u16);
        }
        key.sort_unstable();
        if best.as_ref().map_or(true, |current| key < *current) {
            best = Some(key);
        }
    }
    best.expect("component signature needs a live cell")
}

/// Allocation-free color-preserving component canonicalization for bag IDs.
/// Only the winning signature is allocated, and only when it is first interned.
fn component_signature_fixed(
    n: usize,
    component: u64,
    actor: u64,
    opponent: u64,
) -> ([u16; 64], usize) {
    let len = component.count_ones() as usize;
    let mut best = [0u16; 64];
    let mut candidate = [0u16; 64];
    let mut have_best = false;
    for transform in 0..8 {
        let mut min_row = i16::MAX;
        let mut min_col = i16::MAX;
        let mut bits = component;
        while bits != 0 {
            let bit = bits & bits.wrapping_neg();
            bits ^= bit;
            let cell = bit.trailing_zeros() as usize;
            let (row, col) =
                transform_point(transform, (cell / n) as i16, (cell % n) as i16);
            min_row = min_row.min(row);
            min_col = min_col.min(col);
        }

        let mut out = 0usize;
        let mut bits = component;
        while bits != 0 {
            let bit = bits & bits.wrapping_neg();
            bits ^= bit;
            let cell = bit.trailing_zeros() as usize;
            let (row, col) =
                transform_point(transform, (cell / n) as i16, (cell % n) as i16);
            let row = (row - min_row) as u16;
            let col = (col - min_col) as u16;
            debug_assert!(row < 64 && col < 64);
            candidate[out] =
                (row << 8) | (col << 2) | global_tint(bit, actor, opponent) as u16;
            out += 1;
        }
        debug_assert_eq!(out, len);
        candidate[..len].sort_unstable();
        if !have_best || candidate[..len] < best[..len] {
            best[..len].copy_from_slice(&candidate[..len]);
            have_best = true;
        }
    }
    (best, len)
}

enum ComponentEval {
    Local(u64),
    KnownValue(Value),
}

fn take_component_eval(
    n: usize,
    adjacency: &[u64],
    remaining: &mut u64,
    legal_p1: u64,
    legal_p2: u64,
    max_component_size: u32,
) -> Option<ComponentEval> {
    let seed = *remaining & remaining.wrapping_neg();
    let mut stack = [0u64; 64];
    let mut stack_len = 1usize;
    stack[0] = seed;
    let mut component = seed;
    let mut count = 1u32;
    let mut linear_possible = true;
    let mut endpoint_count = 0u32;
    let mut endpoint_score_sum = 0i64;
    let mut all_open = true;
    let mut min_row = usize::MAX;
    let mut max_row = 0usize;
    let mut min_col = usize::MAX;
    let mut max_col = 0usize;
    *remaining ^= seed;

    while stack_len > 0 {
        stack_len -= 1;
        let bit = stack[stack_len];
        let cell = bit.trailing_zeros() as usize;
        let row = cell / n;
        let col = cell % n;
        min_row = min_row.min(row);
        max_row = max_row.max(row);
        min_col = min_col.min(col);
        max_col = max_col.max(col);
        let interaction = interaction_neighbors(adjacency, cell, bit, legal_p1, legal_p2);
        let degree = interaction.count_ones();
        let tint = global_tint(bit, legal_p1, legal_p2);
        if tint != 0 {
            all_open = false;
            if count > max_component_size && !linear_possible {
                return None;
            }
        }
        if degree > 2 {
            linear_possible = false;
        } else if degree <= 1 {
            endpoint_count += 1;
            endpoint_score_sum += endpoint_chain_score(tint)
                .expect("a cell in the live union cannot have dead tint");
        } else if tint != 0 {
            linear_possible = false;
        }

        let mut neighbors = interaction & !component;
        while neighbors != 0 {
            let neighbor = neighbors & neighbors.wrapping_neg();
            neighbors ^= neighbor;
            component |= neighbor;
            *remaining &= !neighbor;
            count += 1;
            if count > max_component_size && !linear_possible && !all_open {
                return None;
            }
            stack[stack_len] = neighbor;
            stack_len += 1;
        }
    }

    if all_open {
        let rows = max_row - min_row + 1;
        let cols = max_col - min_col + 1;
        if rows * cols == count as usize && (rows % 2 == 0 || cols % 2 == 0) {
            return Some(ComponentEval::KnownValue(Value::zero()));
        }
    }

    if linear_possible {
        let value = if count == 1 {
            single_cell_value(global_tint(seed, legal_p1, legal_p2))
        } else if endpoint_count == 2 {
            Value {
                number: Dyadic::new(endpoint_score_sum, 1),
                star: false,
            }
        } else if count <= max_component_size {
            return Some(ComponentEval::Local(component));
        } else {
            return None;
        };
        return Some(ComponentEval::KnownValue(value));
    }

    if count <= max_component_size {
        Some(ComponentEval::Local(component))
    } else {
        None
    }
}

fn pack_key(codes: &[u16]) -> LocalKey {
    debug_assert!(codes.len() <= MAX_LOCAL_CELLS);
    let mut key = LocalKey {
        len: codes.len() as u8,
        codes: [0u16; MAX_LOCAL_CELLS],
    };
    for (index, &code) in codes.iter().enumerate() {
        debug_assert!(code < 1024);
        key.codes[index] = code;
    }
    key
}

fn transform_point(transform: u8, row: i16, col: i16) -> (i16, i16) {
    match transform {
        0 => (row, col),
        1 => (-row, col),
        2 => (row, -col),
        3 => (-row, -col),
        4 => (col, row),
        5 => (-col, row),
        6 => (col, -row),
        7 => (-col, -row),
        _ => unreachable!(),
    }
}

fn swap_tint(tint: u8) -> u8 {
    ((tint & BLOCK_P1) << 1) | ((tint & BLOCK_P2) >> 1)
}

fn global_tint(bit: u64, p1_legal: u64, p2_legal: u64) -> u8 {
    let mut tint = 0;
    if p1_legal & bit == 0 {
        tint |= BLOCK_P1;
    }
    if p2_legal & bit == 0 {
        tint |= BLOCK_P2;
    }
    tint
}

fn linear_chain_value_local(shape: &LocalShape, p1_legal: u16, p2_legal: u16) -> Option<Value> {
    let live = p1_legal | p2_legal;
    debug_assert!(live.count_ones() > 1);

    let mut endpoint_count = 0u32;
    let mut endpoint_score_sum = 0i64;
    let mut bits = live;
    while bits != 0 {
        let bit = bits & bits.wrapping_neg();
        bits ^= bit;
        let cell = bit.trailing_zeros() as usize;
        let degree =
            local_interaction_neighbors(shape, cell, bit, p1_legal, p2_legal).count_ones();
        let tint = local_tint(bit, p1_legal, p2_legal);
        if degree > 2 {
            return None;
        }
        if degree <= 1 {
            endpoint_count += 1;
            endpoint_score_sum += endpoint_chain_score(tint)?;
        } else if tint != 0 {
            return None;
        }
    }

    if endpoint_count == 2 {
        Some(Value {
            number: Dyadic::new(endpoint_score_sum, 1),
            star: false,
        })
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn line_adjacency(len: usize) -> Vec<u64> {
        let mut adjacency = vec![0u64; len];
        for cell in 0..len {
            if cell > 0 {
                adjacency[cell] |= 1u64 << (cell - 1);
            }
            if cell + 1 < len {
                adjacency[cell] |= 1u64 << (cell + 1);
            }
        }
        adjacency
    }

    fn grid_adjacency(m: usize, n: usize) -> Vec<u64> {
        let mut adjacency = vec![0u64; m * n];
        for row in 0..m {
            for col in 0..n {
                let cell = row * n + col;
                if row > 0 {
                    adjacency[cell] |= 1u64 << ((row - 1) * n + col);
                }
                if row + 1 < m {
                    adjacency[cell] |= 1u64 << ((row + 1) * n + col);
                }
                if col > 0 {
                    adjacency[cell] |= 1u64 << (row * n + col - 1);
                }
                if col + 1 < n {
                    adjacency[cell] |= 1u64 << (row * n + col + 1);
                }
            }
        }
        adjacency
    }

    fn temp_cache_dir() -> PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("col-rs-cgt-cache-{unique}"))
    }

    fn masks(pattern: &str) -> (u64, u64) {
        let mut p1 = 0u64;
        let mut p2 = 0u64;
        for (index, ch) in pattern.chars().enumerate() {
            let bit = 1u64 << index;
            match ch {
                'o' => {
                    p1 |= bit;
                    p2 |= bit;
                }
                'b' => p1 |= bit,
                'w' => p2 |= bit,
                'x' => {}
                _ => panic!("bad chain pattern"),
            }
        }
        (p1, p2)
    }

    #[test]
    fn bit_parallel_three_row_components_match_generic_bfs() {
        let n = 5;
        let adjacency = grid_adjacency(3, n);
        for live in 1u64..(1u64 << (3 * n)) {
            let mut generic_remaining = live;
            let mut parallel_remaining = live;
            while generic_remaining != 0 {
                let generic =
                    take_component(&adjacency, live, live, &mut generic_remaining);
                let parallel = take_component_3xn(n, live, live, &mut parallel_remaining);
                assert_eq!(parallel, generic);
            }
            assert_eq!(parallel_remaining, 0);
        }
    }

    #[test]
    fn bit_parallel_three_row_interaction_components_match_generic_bfs() {
        let n = 3;
        let adjacency = grid_adjacency(3, n);
        let limit = 1u64 << (3 * n);
        for legal_p1 in 0..limit {
            for legal_p2 in 0..limit {
                let mut generic_remaining = legal_p1 | legal_p2;
                let mut parallel_remaining = generic_remaining;
                while generic_remaining != 0 {
                    let generic = take_component(
                        &adjacency,
                        legal_p1,
                        legal_p2,
                        &mut generic_remaining,
                    );
                    let parallel = take_component_3xn(
                        n,
                        legal_p1,
                        legal_p2,
                        &mut parallel_remaining,
                    );
                    assert_eq!(parallel, generic);
                }
                assert_eq!(parallel_remaining, 0);
            }
        }
    }

    #[test]
    fn component_bag_key_is_actor_relative_and_component_order_independent() {
        let n = 7;
        let mut evaluator = EndgameEvaluator::new(0, None);

        // Four isolated components: two shared, P1-only, and P2-only.
        let p1 = (1u64 << 0) | (1u64 << 6) | (1u64 << 9);
        let p2 = (1u64 << 0) | (1u64 << 6) | (1u64 << 18);
        evaluator.retain_reduction_components(
            &[1u64 << 0, 1u64 << 6, 1u64 << 9, 1u64 << 18],
            0,
        );
        let key = match evaluator.probe_component_bag(n, p1, p2, 0) {
            ComponentBagProbe::Miss(key) => key,
            _ => panic!("first component bag must miss"),
        };
        evaluator.insert_component_bag(key, true);

        // Move and permute the same three component games geometrically.
        let moved_p1 = (1u64 << 0) | (1u64 << 6) | (1u64 << 11);
        let moved_p2 = (1u64 << 0) | (1u64 << 6) | (1u64 << 16);
        evaluator.retain_reduction_components(
            &[1u64 << 0, 1u64 << 6, 1u64 << 11, 1u64 << 16],
            0,
        );
        assert!(matches!(
            evaluator.probe_component_bag(n, moved_p1, moved_p2, 0),
            ComponentBagProbe::Hit(true)
        ));

        // Global color swap plus side-to-move swap retains the actor-relative bag.
        evaluator.retain_reduction_components(
            &[1u64 << 0, 1u64 << 6, 1u64 << 9, 1u64 << 18],
            0,
        );
        assert!(matches!(
            evaluator.probe_component_bag(n, p2, p1, 1),
            ComponentBagProbe::Hit(true)
        ));

        // Independently recoloring one component is a different game bag.
        evaluator.retain_reduction_components(
            &[1u64 << 0, 1u64 << 6, 1u64 << 9, 1u64 << 18],
            0,
        );
        assert!(matches!(
            evaluator.probe_component_bag(n, p1 | (1u64 << 18), p2, 0),
            ComponentBagProbe::Miss(_)
        ));
    }

    #[test]
    fn completed_component_bags_are_shared_across_evaluators_exactly() {
        let n = 8;
        let shared = Arc::new(SharedEndgameCache::new());
        let mut first = EndgameEvaluator::new(0, Some(shared.clone()));
        let mut second = EndgameEvaluator::new(0, Some(shared.clone()));
        first.enable_shared_component_bags();
        second.enable_shared_component_bags();

        let shared_domino = (1u64 << 0) | (1u64 << 1);
        let actor_domino = (1u64 << 10) | (1u64 << 11);
        let opponent_domino = (1u64 << 20) | (1u64 << 21);
        let star = 1u64 << 31;
        let p1 = shared_domino | actor_domino | star;
        let p2 = shared_domino | opponent_domino | star;
        first.retain_reduction_components(
            &[shared_domino, actor_domino, opponent_domino, star],
            0,
        );
        let key = match first.probe_component_bag(n, p1, p2, 0) {
            ComponentBagProbe::Miss(key) => key,
            _ => panic!("first evaluator must miss the shared bag"),
        };
        first.insert_component_bag(key, true);

        // Translate every component, permute their order, then globally swap
        // colors and the side to move. The actor-relative game bag is exact.
        let moved_shared = (1u64 << 4) | (1u64 << 5);
        let moved_actor = (1u64 << 14) | (1u64 << 15);
        let moved_opponent = (1u64 << 24) | (1u64 << 25);
        let moved_star = 1u64 << 8;
        let moved_p1 = moved_shared | moved_actor | moved_star;
        let moved_p2 = moved_shared | moved_opponent | moved_star;
        second.retain_reduction_components(
            &[moved_star, moved_opponent, moved_shared, moved_actor],
            0,
        );
        assert!(matches!(
            second.probe_component_bag(n, moved_p2, moved_p1, 1),
            ComponentBagProbe::Hit(true)
        ));
        assert_eq!(second.stats.component_bag_local_hits, 0);
        assert_eq!(second.stats.component_bag_shared_hits, 1);
        assert_eq!(second.stats.component_signature_shared_hits, 3);

        // Recoloring only the opponent domino changes the component multiset.
        second.retain_reduction_components(
            &[moved_star, moved_opponent, moved_shared, moved_actor],
            0,
        );
        assert!(matches!(
            second.probe_component_bag(n, moved_p1 | moved_opponent, moved_p2, 0),
            ComponentBagProbe::Miss(_)
        ));
    }

    #[test]
    fn shared_component_interning_and_outcomes_are_race_safe() {
        let shared = Arc::new(SharedEndgameCache::new());
        let signature = vec![0x101u16, 0x202, 0x303];
        std::thread::scope(|scope| {
            let handles: Vec<_> = (0..8)
                .map(|_| {
                    let shared = shared.clone();
                    let signature = signature.clone();
                    scope.spawn(move || shared.intern_component_signature(&signature).0)
                })
                .collect();
            for handle in handles {
                assert_eq!(handle.join().unwrap(), 0);
            }
        });
        assert_eq!(shared.component_signature_ids.len(), 1);

        let key = ComponentBagKey {
            private_singleton_score: 1,
            shared_singleton_parity: true,
            components: ComponentIds::from_sorted(&[0, 0, 0]),
        };
        let unique_inserts: usize = std::thread::scope(|scope| {
            let handles: Vec<_> = (0..8)
                .map(|_| {
                    let shared = shared.clone();
                    let key = key.clone();
                    scope.spawn(move || shared.insert_component_bag(key, true).is_none())
                })
                .collect();
            handles
                .into_iter()
                .map(|handle| usize::from(handle.join().unwrap()))
                .sum()
        });
        assert_eq!(unique_inserts, 1);
        assert_eq!(shared.component_bag_outcomes.len(), 1);
        assert_eq!(shared.component_bag_outcome(&key), Some(true));
    }

    #[test]
    fn component_bag_gate_targets_large_boards_and_mid_size_strips() {
        assert!(!component_bag_enabled(27, 9));
        assert!(!component_bag_enabled(35, 7));
        assert!(component_bag_enabled(33, 11));
        assert!(component_bag_enabled(33, 3));
        assert!(component_bag_enabled(39, 13));
        assert_eq!(component_bag_min_components(33), 4);
        assert_eq!(component_bag_min_components(39), 3);
    }

    #[test]
    fn component_id_bag_has_a_unique_inline_boundary() {
        assert!(matches!(
            ComponentIds::from_sorted(&[1, 2, 3, 4]),
            ComponentIds::Inline {
                len: 4,
                ids: [1, 2, 3, 4]
            }
        ));
        assert!(matches!(
            ComponentIds::from_sorted(&[1, 2, 3, 4, 5]),
            ComponentIds::Heap(ids) if ids.as_ref() == [1, 2, 3, 4, 5]
        ));
    }

    #[test]
    fn fixed_component_signature_matches_allocating_reference() {
        let n = 3;
        let limit = 1u64 << 9;
        for actor in 0..limit {
            for opponent in 0..limit {
                let component = actor | opponent;
                if component == 0 {
                    continue;
                }
                let expected = component_signature(n, component, actor, opponent, false);
                let (actual, len) =
                    component_signature_fixed(n, component, actor, opponent);
                assert_eq!(&actual[..len], expected.as_slice());
            }
        }
    }

    #[test]
    fn component_bag_outcomes_are_exact_exhaustively_on_two_by_four() {
        let n = 4;
        let adjacency = grid_adjacency(2, n);
        let limit = 1u64 << 8;
        let mut bag_evaluator = EndgameEvaluator::new(0, None);
        let mut value_evaluator = EndgameEvaluator::new(MAX_LOCAL_CELLS as u32, None);
        for legal_p1 in 0..limit {
            for legal_p2 in 0..limit {
                let mut components = [0u64; 8];
                let mut component_count = 0usize;
                let mut remaining = legal_p1 | legal_p2;
                while remaining != 0 {
                    components[component_count] = take_component(
                        &adjacency,
                        legal_p1,
                        legal_p2,
                        &mut remaining,
                    );
                    component_count += 1;
                }
                if component_count < COMPONENT_BAG_LARGE_BOARD_MIN_COMPONENTS {
                    continue;
                }

                let mut total = Value::zero();
                for &component in &components[..component_count] {
                    let (shape, p1, p2) = local_shape_from_masks(
                        n,
                        legal_p1 & component,
                        legal_p2 & component,
                    );
                    total = total.add(value_evaluator.component_value_local(&shape, p1, p2));
                }
                for turn in [0, 1] {
                    bag_evaluator
                        .retain_reduction_components(&components[..component_count], 0);
                    let actor_value = if turn == 0 { total } else { total.neg() };
                    let expected = first_player_wins(actor_value);
                    match bag_evaluator.probe_component_bag(n, legal_p1, legal_p2, turn) {
                        ComponentBagProbe::Hit(actual) => assert_eq!(actual, expected),
                        ComponentBagProbe::Miss(key) => {
                            bag_evaluator.insert_component_bag(key, expected)
                        }
                        ComponentBagProbe::Ineligible => {
                            panic!("three-component position must be bag eligible")
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn interaction_components_preserve_exact_value_exhaustively_on_two_by_three() {
        let n = 3;
        let adjacency = grid_adjacency(2, n);
        let limit = 1u64 << 6;
        let mut evaluator = EndgameEvaluator::new(MAX_LOCAL_CELLS as u32, None);
        for legal_p1 in 0..limit {
            for legal_p2 in 0..limit {
                let live = legal_p1 | legal_p2;
                let full = if live == 0 {
                    Value::zero()
                } else {
                    let (shape, p1, p2) = local_shape_from_masks(n, legal_p1, legal_p2);
                    evaluator.position_value_local(&shape, p1, p2)
                };

                let mut sum = Value::zero();
                let mut remaining = live;
                while remaining != 0 {
                    let component =
                        take_component(&adjacency, legal_p1, legal_p2, &mut remaining);
                    let (shape, p1, p2) = local_shape_from_masks(
                        n,
                        legal_p1 & component,
                        legal_p2 & component,
                    );
                    sum = sum.add(evaluator.component_value_local(&shape, p1, p2));
                }
                assert_eq!(sum, full, "p1={legal_p1:#x}, p2={legal_p2:#x}");
            }
        }
    }

    #[test]
    fn interaction_components_are_move_independent_exhaustively_on_two_by_three() {
        let n = 3;
        let adjacency = grid_adjacency(2, n);
        let limit = 1u64 << 6;
        for legal_p1 in 0..limit {
            for legal_p2 in 0..limit {
                let live = legal_p1 | legal_p2;
                let mut remaining = live;
                while remaining != 0 {
                    let component =
                        take_component(&adjacency, legal_p1, legal_p2, &mut remaining);
                    let outside = live & !component;

                    let mut p1_moves = legal_p1 & component;
                    while p1_moves != 0 {
                        let bit = p1_moves & p1_moves.wrapping_neg();
                        p1_moves ^= bit;
                        let cell = bit.trailing_zeros() as usize;
                        let child_p1 = legal_p1 & !(bit | adjacency[cell]);
                        let child_p2 = legal_p2 & !bit;
                        assert_eq!(child_p1 & outside, legal_p1 & outside);
                        assert_eq!(child_p2 & outside, legal_p2 & outside);
                    }

                    let mut p2_moves = legal_p2 & component;
                    while p2_moves != 0 {
                        let bit = p2_moves & p2_moves.wrapping_neg();
                        p2_moves ^= bit;
                        let cell = bit.trailing_zeros() as usize;
                        let child_p1 = legal_p1 & !bit;
                        let child_p2 = legal_p2 & !(bit | adjacency[cell]);
                        assert_eq!(child_p1 & outside, legal_p1 & outside);
                        assert_eq!(child_p2 & outside, legal_p2 & outside);
                    }
                }
            }
        }
    }

    #[test]
    fn small_linear_chain_values_match_theorem() {
        let (p1, p2) = masks("oooo");
        assert_eq!(component_value_text(4, p1, p2).as_deref(), Some("0"));

        let (p1, p2) = masks("booo");
        assert_eq!(component_value_text(4, p1, p2).as_deref(), Some("1/2"));

        let (p1, p2) = masks("wooo");
        assert_eq!(component_value_text(4, p1, p2).as_deref(), Some("-1/2"));

        let (p1, p2) = masks("boow");
        assert_eq!(component_value_text(4, p1, p2).as_deref(), Some("0"));
    }

    #[test]
    fn detailed_evaluation_distinguishes_exact_miss_reasons() {
        let adjacency_2x2 = grid_adjacency(2, 2);
        let all_2x2 = (1u64 << 4) - 1;
        let mut evaluator = EndgameEvaluator::new(4, None);
        assert_eq!(
            evaluator.classify_position(2, &adjacency_2x2, 0, 0, 0),
            EndgameEvaluation::Solved(false)
        );
        assert_eq!(
            evaluator.classify_position(
                2,
                &adjacency_2x2,
                all_2x2,
                all_2x2 ^ 1,
                0,
            ),
            EndgameEvaluation::SingleLocalComponent
        );

        let adjacency_2x3 = grid_adjacency(2, 3);
        let all_2x3 = (1u64 << 6) - 1;
        assert_eq!(
            evaluator.classify_position(
                3,
                &adjacency_2x3,
                all_2x3,
                all_2x3 ^ 1,
                0,
            ),
            EndgameEvaluation::OversizedMiss
        );
        assert_eq!(
            evaluator.classify_position(3, &adjacency_2x3, all_2x3, all_2x3, 0),
            EndgameEvaluation::Solved(false)
        );

        let adjacency_2x5 = grid_adjacency(2, 5);
        let left_block = 0b00111u64 | (0b00111u64 << 5);
        let isolated_column = (1u64 << 4) | (1u64 << 9);
        let mixed = left_block | isolated_column;
        assert_eq!(
            evaluator.classify_position(
                5,
                &adjacency_2x5,
                mixed,
                mixed ^ 1,
                0,
            ),
            EndgameEvaluation::OversizedMiss
        );
    }

    #[test]
    fn empty_even_rectangle_value_matches_pairing_theorem() {
        let adjacency = grid_adjacency(2, 3);
        let legal = (1u64 << 6) - 1;
        let mut evaluator = EndgameEvaluator::new(4, None);

        assert_eq!(evaluator.try_evaluate(3, &adjacency, legal, legal, 0), Some(false));
    }

    #[test]
    fn shared_cache_round_trips_canonical_values() {
        let root = temp_cache_dir();
        let cache = SharedEndgameCache::new();
        let key = LocalKey {
            len: 2,
            codes: [0, 68, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        };
        let value = Value {
            number: Dyadic::new(1, 1),
            star: false,
        };
        cache.insert_loaded(key, value);

        let saved = save_shared_cache(&root, &cache, 0).unwrap();
        assert!(saved.is_some());
        let (loaded, loaded_count) = load_shared_cache(&root).unwrap();
        assert_eq!(loaded_count, 1);
        assert_eq!(loaded.values.get(&key).as_deref().copied(), Some(value));

        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn long_linear_chains_bypass_local_component_limit() {
        let adjacency = line_adjacency(15);
        let mut evaluator = EndgameEvaluator::new(6, None);

        let (p1, p2) = masks("ooooooooooooooo");
        assert_eq!(
            evaluator.try_evaluate(15, &adjacency, p1, p2, 0),
            Some(false)
        );

        let (p1, p2) = masks("boooooooooooooo");
        assert_eq!(
            evaluator.try_evaluate(15, &adjacency, p1, p2, 0),
            Some(true)
        );
        assert_eq!(
            evaluator.try_evaluate(15, &adjacency, p1, p2, 1),
            Some(false)
        );
    }

    #[test]
    fn zero_components_are_removed_beside_other_components() {
        let adjacency = line_adjacency(12);
        let mut evaluator = EndgameEvaluator::new(4, None);
        let large = ((1u64 << 6) - 1) << 6;
        let p1 = (1u64 << 0) | (1u64 << 3) | large;
        let p2 = (1u64 << 1) | (1u64 << 4) | large;

        let reduced = evaluator.reduce_zero_summands(12, &adjacency, p1, p2);
        assert!(reduced.changed);
        assert_eq!(reduced.legal_p1 | reduced.legal_p2, large);
        assert_eq!(evaluator.stats().zero_components_removed, 0);
        assert_eq!(evaluator.stats().reduction_component_evaluations, 4);
    }

    #[test]
    fn fully_small_single_component_uses_fast_exit() {
        let adjacency = line_adjacency(4);
        let mut evaluator = EndgameEvaluator::new(4, None);
        let p1 = (1u64 << 4) - 1;
        let p2 = p1;

        let reduced = evaluator.reduce_zero_summands(4, &adjacency, p1, p2);

        assert!(!reduced.changed);
        assert_eq!(reduced.legal_p1, p1);
        assert_eq!(reduced.legal_p2, p2);
        assert_eq!(evaluator.stats().reduction_single_component_exits, 0);
        assert_eq!(evaluator.stats().reduction_all_small_exits, 1);
        assert_eq!(
            evaluator.try_evaluate(4, &adjacency, p1, p2, 0),
            Some(false)
        );
    }

    #[test]
    fn three_row_small_intervals_skip_component_scan() {
        let adjacency = grid_adjacency(3, 5);
        let live = (1u64 << 0)
            | (1u64 << 4)
            | (1u64 << 5)
            | (1u64 << 9)
            | (1u64 << 10)
            | (1u64 << 14);
        let mut evaluator = EndgameEvaluator::new(4, None);

        let reduced = evaluator.reduce_zero_summands(5, &adjacency, live, live);

        assert!(!reduced.changed);
        assert_eq!(evaluator.stats().reduction_column_all_small_exits, 1);
        assert_eq!(evaluator.stats().reduction_all_small_exits, 1);
        assert_eq!(evaluator.stats().reduction_single_component_exits, 0);
    }

    #[test]
    fn small_conjugate_components_cancel_beside_oversized_component() {
        let adjacency = line_adjacency(12);
        let mut evaluator = EndgameEvaluator::new(4, None);
        let large = ((1u64 << 8) - 1) << 4;
        let p1 = (1u64 << 0) | large;
        let p2 = (1u64 << 2) | large;

        let reduced = evaluator.reduce_zero_summands(12, &adjacency, p1, p2);

        assert!(reduced.changed);
        assert_eq!(reduced.legal_p1 | reduced.legal_p2, large);
        assert_eq!(evaluator.stats().reduction_multi_oversized, 0);
    }

    #[test]
    fn oversized_conjugate_components_cancel_by_signature() {
        let adjacency = line_adjacency(11);
        let mut evaluator = EndgameEvaluator::new(4, None);
        let left = (1u64 << 5) - 1;
        let right = left << 6;
        let p1 = left | (right & !(1u64 << 6));
        let p2 = (left & !1u64) | right;

        let reduced = evaluator.reduce_zero_summands(11, &adjacency, p1, p2);

        assert!(reduced.changed);
        assert_eq!(reduced.legal_p1 | reduced.legal_p2, 0);
        assert_eq!(evaluator.stats().conjugate_pairs_removed, 1);
        assert_eq!(evaluator.stats().reduction_multi_oversized, 1);
    }


    #[test]
    fn nonzero_small_component_beside_oversized_component_is_unchanged() {
        let adjacency = line_adjacency(8);
        let mut evaluator = EndgameEvaluator::new(4, None);
        let large = ((1u64 << 6) - 1) << 2;
        let p1 = 1u64 | large;
        let p2 = large;

        let reduced = evaluator.reduce_zero_summands(8, &adjacency, p1, p2);

        assert!(!reduced.changed);
        assert_eq!(reduced.legal_p1, p1);
        assert_eq!(reduced.legal_p2, p2);
    }
}
