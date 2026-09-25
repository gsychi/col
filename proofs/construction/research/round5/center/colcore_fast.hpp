// Evaluator core copied from ../literature/col_fastval.cpp (Theorem-5 based).
// Exact Col values on grids, computed bottom-up from option values.
//
// Correctness rests on Theorem 5 of COL_VALUES.md (every Col position is x or
// x+*) and on the simplest-number rule: for a position whose options are
// a_i + e_i* (Blue) and b_j + d_j* (White), the value is the simplest number z
// with [z > a_i or (z = a_i and e_i = 1)] for all i and
// [z < b_j or (z = b_j and d_j = 1)] for all j, if such z exists; otherwise
// (then max a_i = min b_j = c with unstarred options there) it is c + *.
// Mixed star bits at c would contradict the theorem and abort the program.
// Components (via edges usable by some player) are evaluated separately and
// summed; component values are memoised after translation to the corner.
// Implementation is cross-checked against cgt_core.py (general canonical
// forms) by fastval_crosscheck.py.
//
// Build: c++ -O2 -std=c++17 col_fastval.cpp -o col_fastval
// Modes:
//   value H W A B            value of one position
//   openings H W             values of all Blue openings on the empty board
//   mirror H W               half-turn mirror positions with live centre:
//                            value of the centre child, domination test
//   isolate H W              the three-pair isolation line (GENERAL_IDEAS §2)
//   ddreserve MAXN           DD_n and DD_n after White's private (2,0) move
//   random H W COUNT SEED    random shadow states, printed for cross-checking
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <unordered_map>
#include <vector>
using u64 = std::uint64_t;
using i64 = std::int64_t;
using i128 = __int128;

static const int FRAC = 24;            // values stored as integers times 2^24
static const i64 ONE = i64{1} << FRAC;
struct Val { i64 x; int e; };
static Val add(Val a, Val b) { return {a.x + b.x, (a.e + b.e) & 1}; }
// a <= b for values of the form x + e*
static bool leqv(Val a, Val b) { return a.e == b.e ? a.x <= b.x : a.x < b.x; }

static int H, W, N;
static std::vector<u64> NB;  // closed neighbourhoods
struct KeyHash { std::size_t operator()(const std::pair<u64,u64>& k) const {
    u64 x = k.first * 0x9E3779B97F4A7C15ULL ^ (k.second + 0x632BE59BD9B4E019ULL + (k.first << 6));
    x ^= x >> 31; x *= 0xbf58476d1ce4e5b9ULL; x ^= x >> 29; return (std::size_t)x; } };
static std::unordered_map<std::pair<u64,u64>, Val, KeyHash> memo;
static std::size_t MEMO_CAP = 18000000;

static void setup(int h, int w) {
    H = h; W = w; N = h * w;
    if (N > 64) { std::fprintf(stderr, "board too large\n"); std::exit(1); }
    NB.assign(N, 0);
    for (int v = 0; v < N; ++v) {
        int r = v / W, c = v % W; u64 m = u64{1} << v;
        if (r > 0) m |= u64{1} << (v - W);
        if (r + 1 < H) m |= u64{1} << (v + W);
        if (c > 0) m |= u64{1} << (v - 1);
        if (c + 1 < W) m |= u64{1} << (v + 1);
        NB[v] = m;
    }
    memo.clear();
}

static i64 floordiv(i128 a, i128 b) { i128 q = a / b; if ((a % b != 0) && ((a < 0) != (b < 0))) --q; return (i64)q; }

struct Interval { bool has_lo, lo_closed, has_hi, hi_closed; i64 lo, hi; };
static bool inside(const Interval& I, i64 z) {
    if (I.has_lo && (z < I.lo || (z == I.lo && !I.lo_closed))) return false;
    if (I.has_hi && (z > I.hi || (z == I.hi && !I.hi_closed))) return false;
    return true;
}
static bool simplest(Interval I, i64& out) {
    if (I.has_lo && I.has_hi && (I.lo > I.hi || (I.lo == I.hi && !(I.lo_closed && I.hi_closed)))) return false;
    if (inside(I, 0)) { out = 0; return true; }
    bool neg = I.has_hi && (I.hi < 0 || (I.hi == 0 && !I.hi_closed));
    if (neg) {  // mirror to the positive side
        Interval J{I.has_hi, I.hi_closed, I.has_lo, I.lo_closed, -I.hi, -I.lo};
        i64 z; if (!simplest(J, z)) return false; out = -z; return true;
    }
    // now every member is positive and I.has_lo holds with lo >= 0
    for (int k = 0; k <= FRAC; ++k) {
        i64 step = ONE >> k;  // grid of multiples of 2^-k
        i64 m = I.lo_closed ? -floordiv(-(i128)I.lo, step) : floordiv(I.lo, step) + 1;
        i64 z = m * step;
        if (inside(I, z)) { out = z; return true; }
    }
    std::fprintf(stderr, "denominator exceeds 2^%d\n", FRAC); std::exit(2);
}

static Val value(u64 a, u64 b);

static Val component_value(u64 a, u64 b) {
    // translate to the top-left corner for memo reuse
    u64 live = a | b;
    int minr = H, minc = W;
    for (u64 z = live; z; z &= z - 1) { int v = __builtin_ctzll(z); minr = std::min(minr, v / W); minc = std::min(minc, v % W); }
    int s = minr * W + minc;
    std::pair<u64,u64> key{a >> s, b >> s};
    auto it = memo.find(key);
    if (it != memo.end()) return it->second;
    bool anyL = false, anyR = false;
    i64 m = 0, M = 0; bool mStarOnly = true, MStarOnly = true;
    std::vector<Val> Ls, Rs;
    for (u64 z = a; z; z &= z - 1) {
        int v = __builtin_ctzll(z); u64 bit = u64{1} << v;
        Val o = value(a & ~NB[v], b & ~bit); Ls.push_back(o);
        if (!anyL || o.x > m) { m = o.x; mStarOnly = o.e == 1; anyL = true; }
        else if (o.x == m && o.e == 0) mStarOnly = false;
    }
    for (u64 z = b; z; z &= z - 1) {
        int v = __builtin_ctzll(z); u64 bit = u64{1} << v;
        Val o = value(a & ~bit, b & ~NB[v]); Rs.push_back(o);
        if (!anyR || o.x < M) { M = o.x; MStarOnly = o.e == 1; anyR = true; }
        else if (o.x == M && o.e == 0) MStarOnly = false;
    }
    Val res;
    if (anyL && anyR && m == M) {
        // theorem: all options at c carry one star bit
        bool lmixed = false, rmixed = false; int lb = -1, rb = -1;
        for (auto& o : Ls) if (o.x == m) { if (lb < 0) lb = o.e; else if (lb != o.e) lmixed = true; }
        for (auto& o : Rs) if (o.x == M) { if (rb < 0) rb = o.e; else if (rb != o.e) rmixed = true; }
        if (lmixed || rmixed || lb != rb) { std::fprintf(stderr, "THEOREM VIOLATION (mixed star bits)\n"); std::exit(3); }
        res = lb == 0 ? Val{m, 1} : Val{m, 0};
    } else {
        if (anyL && anyR && m > M) { std::fprintf(stderr, "THEOREM VIOLATION (m > M)\n"); std::exit(3); }
        Interval I{anyL, anyL && mStarOnly, anyR, anyR && MStarOnly, m, M};
        i64 z; if (!simplest(I, z)) { std::fprintf(stderr, "empty interval\n"); std::exit(3); }
        res = {z, 0};
    }
    if (memo.size() > MEMO_CAP) memo.clear();
    memo.emplace(key, res);
    return res;
}

static Val value(u64 a, u64 b) {
    u64 live = a | b;
    Val total{0, 0};
    while (live) {
        int v0 = __builtin_ctzll(live);
        u64 comp = u64{1} << v0, frontier = comp;
        while (frontier) {
            int v = __builtin_ctzll(frontier); frontier &= frontier - 1;
            u64 usable = 0;
            if ((a >> v) & 1) usable |= a;
            if ((b >> v) & 1) usable |= b;
            u64 nb = NB[v] & usable & live & ~comp;
            comp |= nb; frontier |= nb;
        }
        total = add(total, component_value(a & comp, b & comp));
        live &= ~comp;
    }
    return total;
}

static std::string fmt(Val v) {
    i64 num = v.x, den = ONE;
    while (den > 1 && num % 2 == 0) { num /= 2; den /= 2; }
    if (num == 0) return v.e ? "*" : "0";
    std::string s = std::to_string(num);
    if (den > 1) s += "/" + std::to_string(den);
    if (v.e) s += "+*";
    return s;
}
static void show(u64 a, u64 b) {
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int v = r * W + c; bool x = (a >> v) & 1, y = (b >> v) & 1;
            std::putchar(x && y ? 'o' : x ? 'b' : y ? 'w' : '.');
        }
        if (r + 1 < H) std::putchar('/');
    }
}
static int rho(int v) { return N - 1 - v; }
static u64 fullmask() { return N == 64 ? ~u64{0} : ((u64{1} << N) - 1); }
static void perms_from_stones(u64 blue, u64 white, u64& a, u64& b) {
    a = b = 0; u64 occ = blue | white;
    for (int v = 0; v < N; ++v) {
        if ((occ >> v) & 1) continue;
        if (!(NB[v] & blue)) a |= u64{1} << v;
        if (!(NB[v] & white)) b |= u64{1} << v;
    }
}

