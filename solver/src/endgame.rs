use dashmap::DashMap;
use rustc_hash::FxBuildHasher;
use rustc_hash::FxHashMap;
use std::cmp::Ordering;
use std::sync::Arc;

const BLOCK_P1: u8 = 1;
const BLOCK_P2: u8 = 2;
const DEAD: u8 = BLOCK_P1 | BLOCK_P2;
const MAX_LOCAL_CELLS: usize = 12;
const ZERO_DYADIC: Dyadic = Dyadic { num: 0, shift: 0 };
const ZERO_VALUE: Value = Value {
    number: ZERO_DYADIC,
    star: false,
};

#[derive(Clone, Copy, Default)]
pub struct EndgameStats {
    pub raw_cache_hits: u64,
    pub canonical_cache_hits: u64,
    pub cgt_misses: u64,
    pub component_evaluations: u64,
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
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

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
struct Value {
    number: Dyadic,
    star: bool,
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
    raw_values: FxHashMap<u128, Value>,
    values: FxHashMap<u128, Value>,
    shared: Option<Arc<SharedEndgameCache>>,
    cgt: CgtEngine,
    stats: EndgameStats,
}

pub struct SharedEndgameCache {
    raw_values: DashMap<u128, Value, FxBuildHasher>,
    values: DashMap<u128, Value, FxBuildHasher>,
}

impl SharedEndgameCache {
    pub fn new() -> SharedEndgameCache {
        SharedEndgameCache {
            raw_values: DashMap::with_hasher(FxBuildHasher),
            values: DashMap::with_hasher(FxBuildHasher),
        }
    }
}

impl EndgameEvaluator {
    pub fn new(
        max_component_size: u32,
        shared: Option<Arc<SharedEndgameCache>>,
    ) -> EndgameEvaluator {
        assert!(
            max_component_size <= 12,
            "packed endgame keys support components up to 12 cells"
        );
        EndgameEvaluator {
            max_component_size,
            raw_values: FxHashMap::default(),
            values: FxHashMap::default(),
            shared,
            cgt: CgtEngine::new(),
            stats: EndgameStats::default(),
        }
    }

    pub fn stats(&self) -> EndgameStats {
        self.stats
    }

    pub fn try_evaluate(
        &mut self,
        n: usize,
        adjacency: &[u64],
        legal_p1: u64,
        legal_p2: u64,
        turn: u8,
    ) -> Option<bool> {
        let combined = legal_p1 | legal_p2;
        if combined == 0 {
            return Some(false);
        }

        let mut remaining = combined;
        let mut component_count = 0usize;
        let mut first_component: Option<(u64, u64)> = None;
        let mut total = Value::zero();
        while remaining != 0 {
            let component =
                take_component(adjacency, combined, &mut remaining, self.max_component_size)?;
            let component_masks = (legal_p1 & component, legal_p2 & component);
            component_count += 1;

            if component_count == 1 {
                first_component = Some(component_masks);
                continue;
            }
            if component_count == 2 {
                let (comp_p1, comp_p2) = first_component.take().expect("first component missing");
                let (shape, p1, p2) = local_shape_from_masks(n, comp_p1, comp_p2);
                total = total.add(self.component_value_local(&shape, p1, p2));
            }
            let (shape, p1, p2) = local_shape_from_masks(n, component_masks.0, component_masks.1);
            total = total.add(self.component_value_local(&shape, p1, p2));
        }

        if component_count < 2 {
            return None;
        }

        let value = if turn == 0 { total } else { total.neg() };
        Some(first_player_wins(value))
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

    fn position_value_local(&mut self, shape: &LocalShape, p1_legal: u16, p2_legal: u16) -> Value {
        let live = p1_legal | p2_legal;
        if live == 0 {
            return Value::zero();
        }
        let mut total = Value::zero();
        let mut remaining = live;
        while remaining != 0 {
            let component = take_local_component(shape, live, &mut remaining);
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
    let value = evaluator.component_value_local(&shape, p1, p2);
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

struct LocalShape {
    rows: [i16; MAX_LOCAL_CELLS],
    cols: [i16; MAX_LOCAL_CELLS],
    adj: [u16; MAX_LOCAL_CELLS],
}

fn local_shape_from_masks(n: usize, legal_p1: u64, legal_p2: u64) -> (LocalShape, u16, u16) {
    let mut rows = [0i16; MAX_LOCAL_CELLS];
    let mut cols = [0i16; MAX_LOCAL_CELLS];
    let mut global_bits = [0u64; MAX_LOCAL_CELLS];
    let mut p1 = 0u16;
    let mut p2 = 0u16;
    let mut len = 0usize;
    let mut combined = legal_p1 | legal_p2;

    while combined != 0 {
        let bit = combined & combined.wrapping_neg();
        combined ^= bit;
        let cell = bit.trailing_zeros() as usize;
        let local_bit = 1u16 << len;
        rows[len] = (cell / n) as i16;
        cols[len] = (cell % n) as i16;
        global_bits[len] = bit;
        if legal_p1 & bit != 0 {
            p1 |= local_bit;
        }
        if legal_p2 & bit != 0 {
            p2 |= local_bit;
        }
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

    (LocalShape { rows, cols, adj }, p1, p2)
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

fn take_local_component(shape: &LocalShape, live: u16, remaining: &mut u16) -> u16 {
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
        let mut neighbors = shape.adj[cell] & live & !component;
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

fn raw_shape_key_local(shape: &LocalShape, p1_legal: u16, p2_legal: u16) -> u128 {
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
    key[..len].sort_unstable();
    pack_key(&key[..len])
}

fn canonical_key_local(shape: &LocalShape, p1_legal: u16, p2_legal: u16) -> (u128, bool) {
    let live = p1_legal | p2_legal;
    debug_assert!(live != 0);

    let mut best_key: Option<u128> = None;
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

        for swapped in [false, true] {
            let mut key = [0u16; MAX_LOCAL_CELLS];
            for index in 0..len {
                let row = (rows[index] - min_row) as u16;
                let col = (cols[index] - min_col) as u16;
                debug_assert!(row < 16 && col < 16);
                let tint = if swapped {
                    swap_tint(tints[index])
                } else {
                    tints[index]
                };
                key[index] = (row << 6) | (col << 2) | tint as u16;
            }
            key[..len].sort_unstable();
            let packed = pack_key(&key[..len]);
            if best_key.map_or(true, |best| packed < best) {
                best_key = Some(packed);
                best_swapped = swapped;
            }
        }
    }

    (best_key.unwrap_or(0), best_swapped)
}

fn first_player_wins(value: Value) -> bool {
    value.number > Dyadic::zero() || (value.number == Dyadic::zero() && value.star)
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

fn take_component(
    adjacency: &[u64],
    combined: u64,
    remaining: &mut u64,
    max_component_size: u32,
) -> Option<u64> {
    let seed = *remaining & remaining.wrapping_neg();
    let mut stack = [0u64; 64];
    let mut stack_len = 1usize;
    stack[0] = seed;
    let mut component = seed;
    let mut count = 1u32;
    *remaining ^= seed;

    while stack_len > 0 {
        stack_len -= 1;
        let bit = stack[stack_len];
        let cell = bit.trailing_zeros() as usize;
        let mut neighbors = adjacency[cell] & combined & !component;
        while neighbors != 0 {
            let neighbor = neighbors & neighbors.wrapping_neg();
            neighbors ^= neighbor;
            component |= neighbor;
            *remaining &= !neighbor;
            count += 1;
            if count > max_component_size {
                return None;
            }
            stack[stack_len] = neighbor;
            stack_len += 1;
        }
    }
    Some(component)
}

fn pack_key(codes: &[u16]) -> u128 {
    debug_assert!(codes.len() <= 12);
    let mut key = codes.len() as u128;
    for &code in codes {
        debug_assert!(code < 1024);
        key = (key << 10) | code as u128;
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
