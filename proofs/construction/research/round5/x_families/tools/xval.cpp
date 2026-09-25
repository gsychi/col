// Discovery-only exact value evaluator for five-row Col permission positions.
//
// A position is (A,B): A = Blue-legal cells, B = White-legal cells, on a
// 5 x W grid, W <= 12.  Bits are COLUMN-major internally: bit = 5*c + r.
// Values are computed by component decomposition plus the simplicity rule,
// ASSUMING the classical theorem that every Col position is a number or a
// number plus star.  A component whose options violate the stop condition of
// that form is reported as an error.  Output is discovery evidence only; all
// proved claims in this directory are backed by response-DAG certificates.
//
// Build: c++ -O2 -std=c++17 xval.cpp -o xval
// Input lines:  W A B      (A,B column-major decimal masks)
// Output lines: num den star   (value = num/den + star*'*')
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <algorithm>
#include <string>
#include <iostream>
using namespace std;
typedef uint64_t u64;
typedef int64_t i64;

static const int SHIFT = 30;           // numbers are stored as k / 2^SHIFT
static const i64 ONE = (i64)1 << SHIFT;
static u64 ROW0, ROW4, ALLB;
static int VFLIP[32];

struct Val { i64 num; int star; };

// ---------------- hash table -----------------
struct Entry { u64 a, b; i64 num; int32_t star; int32_t used; };
static Entry* table_ = nullptr;
static u64 tmask = 0, tcount = 0;
static inline u64 mix(u64 x) {
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL; x ^= x >> 27; x *= 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}
static bool lookup(u64 a, u64 b, Val& v) {
    u64 h = mix(a * 0x9E3779B97F4A7C15ULL ^ mix(b)) & tmask;
    while (table_[h].used) {
        if (table_[h].a == a && table_[h].b == b) { v.num = table_[h].num; v.star = table_[h].star; return true; }
        h = (h + 1) & tmask;
    }
    return false;
}
static void store(u64 a, u64 b, Val v) {
    if (tcount * 10 > tmask * 8) { fprintf(stderr, "table full\n"); exit(3); }
    u64 h = mix(a * 0x9E3779B97F4A7C15ULL ^ mix(b)) & tmask;
    while (table_[h].used) {
        if (table_[h].a == a && table_[h].b == b) return;
        h = (h + 1) & tmask;
    }
    table_[h].a = a; table_[h].b = b; table_[h].num = v.num; table_[h].star = v.star; table_[h].used = 1;
    ++tcount;
}

// ---------------- grid helpers -----------------
static inline u64 nbrs(u64 s) {
    return (((s & ~ROW4) << 1) | ((s & ~ROW0) >> 1) | (s << 5) | (s >> 5)) & ALLB;
}
static inline u64 closedN(int v) { u64 s = (u64)1 << v; return s | nbrs(s); }

// Component of cell set containing seed, edges only where both endpoints share a color permission.
static u64 component(u64 a, u64 b, u64 seed) {
    u64 comp = seed, frontier = seed;
    while (frontier) {
        u64 grow = (nbrs(frontier & a) & a) | (nbrs(frontier & b) & b);
        grow &= ~comp;
        comp |= grow; frontier = grow;
    }
    return comp;
}

static inline u64 vflip(u64 s, int w) {
    u64 r = 0;
    for (int c = 0; c < w; ++c) r |= (u64)VFLIP[(s >> (5 * c)) & 31] << (5 * c);
    return r;
}
static inline u64 hflip(u64 s, int w) {
    u64 r = 0;
    for (int c = 0; c < w; ++c) r |= ((s >> (5 * c)) & 31) << (5 * (w - 1 - c));
    return r;
}

static Val value_comp(u64 a, u64 b);

// canonical key: returns sign (+1 or -1 if colors swapped)
static int canon(u64& a, u64& b) {
    u64 s = a | b;
    int lo = __builtin_ctzll(s) / 5;
    a >>= 5 * lo; b >>= 5 * lo; s >>= 5 * lo;
    int hi = (63 - __builtin_clzll(s)) / 5;
    int w = hi + 1;
    u64 best_a = a, best_b = b; int sign = 1;
    u64 va[4], vb[4];
    va[0] = a; vb[0] = b;
    va[1] = vflip(a, w); vb[1] = vflip(b, w);
    va[2] = hflip(a, w); vb[2] = hflip(b, w);
    va[3] = hflip(va[1], w); vb[3] = hflip(vb[1], w);
    for (int i = 0; i < 4; ++i) {
        if (va[i] < best_a || (va[i] == best_a && vb[i] < best_b)) { best_a = va[i]; best_b = vb[i]; sign = 1; }
        if (vb[i] < best_a || (vb[i] == best_a && va[i] < best_b)) { best_a = vb[i]; best_b = va[i]; sign = -1; }
    }
    a = best_a; b = best_b;
    return sign;
}

static Val add(Val x, Val y) { return Val{x.num + y.num, x.star ^ y.star}; }

// value of an arbitrary (possibly disconnected) position
static Val value_pos(u64 a, u64 b) {
    Val total{0, 0};
    u64 live = a | b;
    while (live) {
        u64 seed = live & (~live + 1);
        u64 comp = component(a, b, seed);
        live &= ~comp;
        u64 ca = a & comp, cb = b & comp;
        // tiny shortcuts
        if (!(ca & cb) && true) {
            // no shared cells: A-cells and B-cells.  If no edges inside color classes, value = |A|-|B|
            // (generic path handles it too; keep generic)
        }
        int sign = canon(ca, cb);
        Val v;
        if (!lookup(ca, cb, v)) { v = value_comp(ca, cb); store(ca, cb, v); }
        if (sign < 0) v.num = -v.num;
        total = add(total, v);
    }
    return total;
}

static bool has_err = false;

static i64 simplest(bool haslo, i64 lo, bool loclosed, bool hashi, i64 hi, bool hiclosed) {
    auto inside = [&](i64 z) {
        if (haslo) { if (loclosed ? z < lo : z <= lo) return false; }
        if (hashi) { if (hiclosed ? z > hi : z >= hi) return false; }
        return true;
    };
    if (inside(0)) return 0;
    bool positive = haslo && (loclosed ? lo > 0 : lo >= 0);
    if (!positive) {
        // all negative: negate
        return -simplest(hashi, -hi, hiclosed, haslo, -lo, loclosed);
    }
    // smallest positive integer in interval
    i64 k = lo / ONE; // lo >= 0
    for (i64 z = k * ONE; ; z += ONE) {
        if (hashi && (hiclosed ? z > hi : z >= hi)) break;
        if (inside(z)) return z;
        if (z > lo + 2 * ONE) break;
    }
    for (int d = 1; d <= SHIFT; ++d) {
        i64 step = ONE >> d;
        i64 m = (lo / step) * step;
        for (int t = 0; t < 3; ++t, m += step) if (inside(m)) return m;
    }
    fprintf(stderr, "precision overflow\n"); exit(4);
}

static Val value_comp(u64 a, u64 b) {
    // Options
    bool haslo = false, hashi = false; i64 lo = 0, hi = 0; bool loclosed = false, hiclosed = false;
    i64 maxL = 0, minR = 0; bool anyL = false, anyR = false;
    for (u64 z = a; z; z &= z - 1) {
        int v = __builtin_ctzll(z);
        Val o = value_pos(a & ~closedN(v), b & ~((u64)1 << v));
        // constraint: z > o.num (star 0) or z >= o.num (star 1)
        bool cl = o.star;
        if (!haslo || o.num > lo || (o.num == lo && !cl && loclosed)) { lo = o.num; loclosed = cl; haslo = true; }
        else if (o.num == lo && !cl) loclosed = false;
        if (!anyL || o.num > maxL) maxL = o.num;
        anyL = true;
    }
    for (u64 z = b; z; z &= z - 1) {
        int v = __builtin_ctzll(z);
        Val o = value_pos(a & ~((u64)1 << v), b & ~closedN(v));
        bool cl = o.star;
        if (!hashi || o.num < hi || (o.num == hi && !cl && hiclosed)) { hi = o.num; hiclosed = cl; hashi = true; }
        else if (o.num == hi && !cl) hiclosed = false;
        if (!anyR || o.num < minR) minR = o.num;
        anyR = true;
    }
    // is interval nonempty?
    bool nonempty = true;
    if (haslo && hashi) {
        if (lo > hi) nonempty = false;
        else if (lo == hi && !(loclosed && hiclosed)) nonempty = false;
    }
    if (nonempty) return Val{simplest(haslo, lo, loclosed, hashi, hi, hiclosed), 0};
    if (anyL && anyR && maxL == minR) return Val{maxL, 1};
    has_err = true;
    fprintf(stderr, "NOT number/number+star: maxL=%lld minR=%lld\n", (long long)maxL, (long long)minR);
    return Val{maxL, 1};
}

int main(int argc, char** argv) {
    int logsize = argc > 1 ? atoi(argv[1]) : 24;
    tmask = ((u64)1 << logsize) - 1;
    table_ = (Entry*)calloc(tmask + 1, sizeof(Entry));
    if (!table_) { fprintf(stderr, "alloc\n"); return 1; }
    for (int x = 0; x < 32; ++x) { int y = 0; for (int r = 0; r < 5; ++r) if (x >> r & 1) y |= 1 << (4 - r); VFLIP[x] = y; }
    ROW0 = ROW4 = 0;
    for (int c = 0; c < 12; ++c) { ROW0 |= (u64)1 << (5 * c); ROW4 |= (u64)1 << (5 * c + 4); }
    ALLB = ((u64)1 << 60) - 1;
    int W; unsigned long long A, B;
    while (scanf("%d %llu %llu", &W, &A, &B) == 3) {
        if (W < 1 || W > 12) { printf("ERR width\n"); fflush(stdout); continue; }
        u64 full = ((u64)1 << (5 * W)) - 1;
        if ((A | B) & ~full) { printf("ERR mask\n"); fflush(stdout); continue; }
        has_err = false;
        Val v = value_pos(A, B);
        // reduce fraction
        i64 num = v.num, den = ONE;
        while (den > 1 && (num % 2 == 0)) { num /= 2; den /= 2; }
        printf("%lld %lld %d%s\n", (long long)num, (long long)den, v.star, has_err ? " ERR" : "");
        fflush(stdout);
    }
    fprintf(stderr, "entries=%llu\n", (unsigned long long)tcount);
    return 0;
}
