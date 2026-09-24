// Discovery-only outcome solver for five-row Col permission positions plus a
// canonical dyadic number and an optional star.  Small interaction components
// (<= K live cells) are replaced by their exact values (number-or-number+star
// evaluation, as in xval.cpp); larger components are searched by minimax with
// a transposition table.  Results are EVIDENCE only; proofs use certificates.
//
// Build: c++ -O2 -std=c++17 xout.cpp -o xout
// Protocol (stdin lines):
//   O W A B NUM LOGDEN STAR MOVER   -> prints 1 if MOVER (0=Blue,1=White) wins G+NUM/2^LOGDEN+STAR*
//   V W A B                         -> prints value "num den star" by bisection
// Masks are column-major (bit 5*c+r).
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <vector>
using namespace std;
typedef uint64_t u64;
typedef int64_t i64;

static const int SHIFT = 30;
static const i64 ONE = (i64)1 << SHIFT;
static u64 ROW0, ROW4, ALLB;
static int VFLIP[32];
static int KSMALL = 12;
static u64 NODES = 0, BUDGET = ~0ULL;
static bool ABORTED = false;

static inline u64 mix(u64 x) {
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL; x ^= x >> 27; x *= 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}
static inline u64 nbrs(u64 s) {
    return (((s & ~ROW4) << 1) | ((s & ~ROW0) >> 1) | (s << 5) | (s >> 5)) & ALLB;
}
static inline u64 closedN(int v) { u64 s = (u64)1 << v; return s | nbrs(s); }
static u64 component(u64 a, u64 b, u64 seed) {
    u64 comp = seed, frontier = seed;
    while (frontier) {
        u64 grow = (nbrs(frontier & a) & a) | (nbrs(frontier & b) & b);
        grow &= ~comp; comp |= grow; frontier = grow;
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

// ---------------- exact values of small components ----------------
struct Val { i64 num; int star; };
struct VEntry { u64 a, b; i64 num; int32_t star, used; };
static VEntry* vt = nullptr; static u64 vmask = 0, vcount = 0;
static bool vlookup(u64 a, u64 b, Val& v) {
    u64 h = mix(a * 0x9E3779B97F4A7C15ULL ^ mix(b)) & vmask;
    while (vt[h].used) {
        if (vt[h].a == a && vt[h].b == b) { v.num = vt[h].num; v.star = vt[h].star; return true; }
        h = (h + 1) & vmask;
    }
    return false;
}
static void vstore(u64 a, u64 b, Val v) {
    if (vcount * 10 > vmask * 7) return;  // table saturated: just do not cache
    u64 h = mix(a * 0x9E3779B97F4A7C15ULL ^ mix(b)) & vmask;
    while (vt[h].used) { if (vt[h].a == a && vt[h].b == b) return; h = (h + 1) & vmask; }
    vt[h] = VEntry{a, b, v.num, v.star, 1}; ++vcount;
}
static int canon(u64& a, u64& b) {
    u64 s = a | b;
    int lo = __builtin_ctzll(s) / 5;
    a >>= 5 * lo; b >>= 5 * lo; s >>= 5 * lo;
    int w = (63 - __builtin_clzll(s)) / 5 + 1;
    u64 va[4], vb[4];
    va[0] = a; vb[0] = b;
    va[1] = vflip(a, w); vb[1] = vflip(b, w);
    va[2] = hflip(a, w); vb[2] = hflip(b, w);
    va[3] = hflip(va[1], w); vb[3] = hflip(vb[1], w);
    u64 ba = a, bb = b; int sign = 1;
    for (int i = 0; i < 4; ++i) {
        if (va[i] < ba || (va[i] == ba && vb[i] < bb)) { ba = va[i]; bb = vb[i]; sign = 1; }
        if (vb[i] < ba || (vb[i] == ba && va[i] < bb)) { ba = vb[i]; bb = va[i]; sign = -1; }
    }
    a = ba; b = bb; return sign;
}
static bool VERR = false;
static i64 simplest(bool haslo, i64 lo, bool loc, bool hashi, i64 hi, bool hic) {
    auto inside = [&](i64 z) {
        if (haslo && (loc ? z < lo : z <= lo)) return false;
        if (hashi && (hic ? z > hi : z >= hi)) return false;
        return true;
    };
    if (inside(0)) return 0;
    bool positive = haslo && (loc ? lo > 0 : lo >= 0);
    if (!positive) return -simplest(hashi, -hi, hic, haslo, -lo, loc);
    for (i64 z = (lo / ONE) * ONE, t = 0; t < 3; ++t, z += ONE) if (inside(z)) return z;
    for (int d = 1; d <= SHIFT; ++d) {
        i64 step = ONE >> d, m = (lo / step) * step;
        for (int t = 0; t < 3; ++t, m += step) if (inside(m)) return m;
    }
    fprintf(stderr, "precision\n"); exit(4);
}
static Val value_pos(u64 a, u64 b);
static Val value_comp(u64 a, u64 b) {
    bool haslo = false, hashi = false, loc = false, hic = false; i64 lo = 0, hi = 0, maxL = 0, minR = 0;
    bool anyL = false, anyR = false;
    for (u64 z = a; z; z &= z - 1) {
        int v = __builtin_ctzll(z);
        Val o = value_pos(a & ~closedN(v), b & ~((u64)1 << v));
        bool cl = o.star;
        if (!haslo || o.num > lo) { lo = o.num; loc = cl; haslo = true; }
        else if (o.num == lo && !cl) loc = false;
        if (!anyL || o.num > maxL) maxL = o.num; anyL = true;
    }
    for (u64 z = b; z; z &= z - 1) {
        int v = __builtin_ctzll(z);
        Val o = value_pos(a & ~((u64)1 << v), b & ~closedN(v));
        bool cl = o.star;
        if (!hashi || o.num < hi) { hi = o.num; hic = cl; hashi = true; }
        else if (o.num == hi && !cl) hic = false;
        if (!anyR || o.num < minR) minR = o.num; anyR = true;
    }
    bool nonempty = !(haslo && hashi && (lo > hi || (lo == hi && !(loc && hic))));
    if (nonempty) return Val{simplest(haslo, lo, loc, hashi, hi, hic), 0};
    if (anyL && anyR && maxL == minR) return Val{maxL, 1};
    VERR = true; return Val{maxL, 1};
}
static Val value_pos(u64 a, u64 b) {
    Val t{0, 0};
    u64 live = a | b;
    while (live) {
        u64 seed = live & (~live + 1);
        u64 comp = component(a, b, seed);
        live &= ~comp;
        u64 ca = a & comp, cb = b & comp;
        int sign = canon(ca, cb);
        Val v;
        if (!vlookup(ca, cb, v)) { v = value_comp(ca, cb); vstore(ca, cb, v); }
        t.num += sign * v.num; t.star ^= v.star;
    }
    return t;
}

// ---------------- outcome search ----------------
struct OEntry { u64 a, b; i64 q; uint32_t s; uint32_t res; };  // res: 1 lose, 2 win
static OEntry* ot = nullptr; static u64 omask = 0, ocount = 0;
static int olookup(u64 a, u64 b, i64 q, int s) {
    u64 h = mix(a ^ mix(b ^ mix((u64)q * 2 + s))) & omask;
    for (int probe = 0; probe < 64 && ot[h].res; ++probe) {
        if (ot[h].a == a && ot[h].b == b && ot[h].q == q && (int)ot[h].s == s) return ot[h].res;
        h = (h + 1) & omask;
    }
    return 0;
}
static void ostore(u64 a, u64 b, i64 q, int s, int res) {
    u64 h = mix(a ^ mix(b ^ mix((u64)q * 2 + s))) & omask;
    for (int probe = 0; probe < 64; ++probe) {
        if (!ot[h].res) { ot[h] = OEntry{a, b, q, (uint32_t)s, (uint32_t)res}; ++ocount; return; }
        if (ot[h].a == a && ot[h].b == b && ot[h].q == q && (int)ot[h].s == s) return;
        h = (h + 1) & omask;
    }
    // replace first slot
    h = mix(a ^ mix(b ^ mix((u64)q * 2 + s))) & omask;
    ot[h] = OEntry{a, b, q, (uint32_t)s, (uint32_t)res};
}
static inline bool has_left_number_move(i64 q) { return q > 0 || (q % ONE) != 0; }
static inline i64 left_number_option(i64 q) {
    if (q % ONE == 0) return q - ONE;          // positive integer
    i64 low = q & -q;                            // lowest set bit = 1/den
    return q - low;
}
static inline bool final_win(i64 q, int s) { return q > 0 || (q == 0 && s); }

// mover = holder of `cur`.  q, s from mover's perspective.
static bool win(u64 cur, u64 oth, i64 q, int s) {
    if (ABORTED) return false;
    if (++NODES > BUDGET) { ABORTED = true; return false; }
    // fold small components
    u64 live = cur | oth;
    u64 big = 0;
    while (live) {
        u64 seed = live & (~live + 1);
        u64 comp = component(cur, oth, seed);
        live &= ~comp;
        if (__builtin_popcountll(comp) <= KSMALL) {
            Val v = value_pos(cur & comp, oth & comp);
            q += v.num; s ^= v.star;
        } else big |= comp;
    }
    cur &= big; oth &= big;
    if (!(cur | oth)) return final_win(q, s);
    if (!cur) {
        // Only number/star moves for mover; opponent has board moves. Mover moves in number or star, or loses.
        // (fall through to generic handling below)
    }
    // normalize for TT: shift to column 0 (translation only)
    {
        u64 lv = cur | oth; int lo = __builtin_ctzll(lv) / 5;
        cur >>= 5 * lo; oth >>= 5 * lo;
    }
    int r = olookup(cur, oth, q, s);
    if (r) return r == 2;
    bool result = false;
    // move ordering: board moves first, prefer cells with many opponent-legal neighbours
    int mv[64]; int sc[64]; int nm = 0;
    for (u64 z = cur; z; z &= z - 1) {
        int v = __builtin_ctzll(z);
        u64 nb = closedN(v);
        mv[nm] = v; sc[nm] = __builtin_popcountll(nb & oth & ~cur) * 4 - __builtin_popcountll(nb & cur); ++nm;
    }
    for (int i = 1; i < nm; ++i) { int j = i; while (j > 0 && sc[j] > sc[j - 1]) { swap(sc[j], sc[j - 1]); swap(mv[j], mv[j - 1]); --j; } }
    for (int i = 0; i < nm && !result; ++i) {
        int v = mv[i];
        if (!win(oth & ~((u64)1 << v), cur & ~closedN(v), -q, s)) result = true;
    }
    if (!result && s) { if (!win(oth, cur, -q, 0)) result = true; }
    if (!result && has_left_number_move(q)) { if (!win(oth, cur, -left_number_option(q), s)) result = true; }
    if (ABORTED) return false;
    ostore(cur, oth, q, s, result ? 2 : 1);
    return result;
}

static int outcome(u64 a, u64 b, i64 q, int s, int mover) {
    ABORTED = false; NODES = 0;
    bool w = mover == 0 ? win(a, b, q, s) : win(b, a, -q, s);
    if (ABORTED) return -1;
    return w ? 1 : 0;
}

// value by bisection: G - q classification
// returns 0 ok
static int classify(u64 a, u64 b, i64 q, char& cls) {
    int bf = outcome(a, b, -q, 0, 0); if (bf < 0) return -1;
    int wf = outcome(a, b, -q, 0, 1); if (wf < 0) return -1;
    if (bf && !wf) cls = 'L'; else if (!bf && wf) cls = 'R'; else if (!bf && !wf) cls = 'P'; else cls = 'N';
    return 0;
}

int main(int argc, char** argv) {
    int vlog = argc > 1 ? atoi(argv[1]) : 22;
    int olog = argc > 2 ? atoi(argv[2]) : 24;
    if (argc > 3) KSMALL = atoi(argv[3]);
    if (argc > 4) BUDGET = strtoull(argv[4], 0, 10);
    vmask = ((u64)1 << vlog) - 1; omask = ((u64)1 << olog) - 1;
    vt = (VEntry*)calloc(vmask + 1, sizeof(VEntry));
    ot = (OEntry*)calloc(omask + 1, sizeof(OEntry));
    if (!vt || !ot) { fprintf(stderr, "alloc\n"); return 1; }
    for (int x = 0; x < 32; ++x) { int y = 0; for (int r = 0; r < 5; ++r) if (x >> r & 1) y |= 1 << (4 - r); VFLIP[x] = y; }
    for (int c = 0; c < 12; ++c) { ROW0 |= (u64)1 << (5 * c); ROW4 |= (u64)1 << (5 * c + 4); }
    ALLB = ((u64)1 << 60) - 1;
    char cmd[4];
    while (scanf("%3s", cmd) == 1) {
        if (cmd[0] == 'O') {
            int W, logden, star, mover; unsigned long long A, B; long long num;
            if (scanf("%d %llu %llu %lld %d %d %d", &W, &A, &B, &num, &logden, &star, &mover) != 7) break;
            i64 q = (i64)num << (SHIFT - logden);
            int r = outcome(A, B, q, star, mover);
            printf("%d %llu\n", r, (unsigned long long)NODES); fflush(stdout);
        } else if (cmd[0] == 'V') {
            int W; unsigned long long A, B;
            if (scanf("%d %llu %llu", &W, &A, &B) != 3) break;
            // integer bracket
            i64 lo = -64 * ONE, hi = 64 * ONE; char cls = 0; bool fail = false; u64 tot = 0;
            // find integer k with classification
            i64 q = 0; int steps = 0;
            // bisection on dyadics: maintain lo < x < hi, test mid
            while (true) {
                if (classify(A, B, q, cls) < 0) { fail = true; break; }
                tot += NODES;
                if (cls == 'P' || cls == 'N') break;
                if (cls == 'L') lo = q; else hi = q;
                // next test: simplest number strictly between lo and hi
                i64 m = simplest(true, lo, false, true, hi, false);
                q = m;
                if (++steps > 80) { fail = true; break; }
            }
            if (fail) { printf("UNKNOWN %llu\n", (unsigned long long)NODES); fflush(stdout); continue; }
            i64 num = q, den = ONE;
            while (den > 1 && num % 2 == 0) { num /= 2; den /= 2; }
            printf("%lld %lld %d%s\n", (long long)num, (long long)den, cls == 'N' ? 1 : 0, VERR ? " VERR" : "");
            fflush(stdout);
        }
    }
    fprintf(stderr, "vcount=%llu ocount=%llu\n", (unsigned long long)vcount, (unsigned long long)ocount);
    return 0;
}
