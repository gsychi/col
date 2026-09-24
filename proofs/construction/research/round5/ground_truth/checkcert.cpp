// checkcert: independent, search-free checker for COLCERT5 certificates
// (written separately from the solvers; shares no code with them).
//
// Claim checked: the player to move LOSES in the root game R + q (+ s*), where
// R = (a, b) is given on the command line (mover's cells a, other player's b).
//
// What is checked, using only one-ply expansions and exact dyadic arithmetic:
//  (1) Value table. Every entry is a connected component, translated to the
//      top-left corner, with a claimed value x + e*. For each entry, every
//      option of either player is split into components; each must be an
//      entry (the empty position is 0). The entry's value must equal the value
//      of {Left option values | Right option values} given by:
//        - lo = max Left number part, hi = min Right number part;
//        - if a number z exists with z > a (pure Left option a), z >= a
//          (starred Left option a+*), z < b (pure Right b), z <= b (starred
//          Right b+*) for all options, the value is the simplest such z
//          (simplicity theorem; a+* <| z iff a <= z, a <| z iff a < z);
//        - else, if lo == hi and every Left and Right option at lo is the pure
//          number lo, the value is lo+* ({a|a} = a+*, lower options dominated);
//        - otherwise the entry is rejected.
//      By induction on the number of live cells every entry value is correct.
//  (2) Checkpoints: reduced states (every component has > K cells) at which the
//      mover is claimed to lose. Components with <= K cells are replaced by
//      their table values (equal games may be substituted in a sum). An empty
//      reduced state is checked arithmetically: q < 0, or q == 0 and no star.
//      Otherwise every option of the mover (each cell of a, the canonical Left
//      move in the number q if any, taking the star if s) has exactly one
//      listed reply, which must be an option of the other player in the reduced
//      position after the option, and must lead to a listed checkpoint of
//      strictly smaller rank (hard live cells, then day(q) + s, lexicographic).
//  (3) The reduced root is a listed checkpoint.
// Then by induction on rank the mover loses at every checkpoint, hence at the
// root.
//
// Usage: checkcert CERT.bin H W A B QNUM QDEN STAR
//   (root in the mover's frame; q = QNUM/QDEN, QDEN a power of two)
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

typedef std::uint64_t u64;
typedef std::int64_t s64;

static void fail(const std::string& m) {
    std::printf("REJECTED: %s\n", m.c_str());
    std::exit(1);
}

static int H, W, K, SH;
static s64 ONE;
static std::vector<u64> NBR;  // open neighbourhoods
static u64 FULL;

static u64 closed_nbhd(int v) { return NBR[v] | (u64(1) << v); }

// Connected component of cell `seed` through edges usable by some player
// (both ends legal for Blue, or both ends legal for White).
static u64 component(int seed, u64 a, u64 b) {
    u64 comp = u64(1) << seed, frontier = comp;
    while (frontier) {
        int v = __builtin_ctzll(frontier);
        frontier &= frontier - 1;
        u64 add = 0;
        if (a >> v & 1) add |= NBR[v] & a;
        if (b >> v & 1) add |= NBR[v] & b;
        add &= ~comp;
        comp |= add;
        frontier |= add;
    }
    return comp;
}

struct Key {
    u64 a, b;
    bool operator==(const Key& o) const { return a == o.a && b == o.b; }
};
struct KeyH {
    size_t operator()(const Key& k) const {
        u64 x = k.a * 0x9E3779B97F4A7C15ULL + (k.b ^ 0xD6E8FEB86659FD93ULL) * 0xC2B2AE3D27D4EB4FULL;
        x ^= x >> 29;
        return size_t(x * 0xBF58476D1CE4E5B9ULL);
    }
};
struct V {
    s64 x;
    int e;
};

static Key normalize(u64 a, u64 b) {
    u64 live = a | b;
    int rmin = 64, cmin = 64;
    for (u64 m = live; m; m &= m - 1) {
        int v = __builtin_ctzll(m);
        if (v / W < rmin) rmin = v / W;
        if (v % W < cmin) cmin = v % W;
    }
    int sh = rmin * W + cmin;
    return Key{a >> sh, b >> sh};
}

static std::unordered_map<Key, V, KeyH> TABLE;

// Sum of table values of all components of (a, b).
static V table_sum(u64 a, u64 b) {
    V t{0, 0};
    u64 live = a | b;
    while (live) {
        int v = __builtin_ctzll(live);
        u64 c = component(v, a, b);
        live &= ~c;
        auto it = TABLE.find(normalize(a & c, b & c));
        if (it == TABLE.end()) fail("component missing from table");
        t.x += it->second.x;
        t.e ^= it->second.e;
    }
    return t;
}

// Simplest dyadic z with lo <(=) z <(=) hi. Returns false if none.
static bool ok_in(s64 z, bool hasLo, s64 lo, bool loStrict, bool hasHi, s64 hi, bool hiStrict) {
    if (hasLo && (loStrict ? !(z > lo) : !(z >= lo))) return false;
    if (hasHi && (hiStrict ? !(z < hi) : !(z <= hi))) return false;
    return true;
}
static bool simplest(bool hasLo, s64 lo, bool loStrict, bool hasHi, s64 hi, bool hiStrict, s64& out) {
    if (hasLo && hasHi && (lo > hi || (lo == hi && (loStrict || hiStrict)))) return false;
    if (ok_in(0, hasLo, lo, loStrict, hasHi, hi, hiStrict)) { out = 0; return true; }
    bool positive = hasLo && lo >= 0;  // otherwise the interval lies below 0
    // Integers: the one of least absolute value.
    s64 start = positive ? (lo / ONE) : (hasHi ? -((-hi) / ONE) : 0);
    for (s64 k = 0; k < 4; ++k) {
        s64 z = positive ? (start + k) * ONE : (start - k) * ONE;
        if (ok_in(z, hasLo, lo, loStrict, hasHi, hi, hiStrict)) {
            // make sure no integer of smaller absolute value works
            out = z;
            return true;
        }
    }
    // Non-integers: smallest denominator 2^d; the interval then contains
    // no integer, so it lies between two consecutive integers.
    for (int d = 1; d <= SH; ++d) {
        s64 step = ONE >> d;
        s64 base = positive ? lo : hi;
        s64 m = base / step;
        for (s64 j = -2; j <= 2; ++j) {
            s64 z = (m + j) * step;
            if (ok_in(z, hasLo, lo, loStrict, hasHi, hi, hiStrict)) { out = z; return true; }
        }
    }
    return false;
}

static void check_table_entry(const Key& k, const V& claimed) {
    u64 a = k.a, b = k.b;
    if (!(a | b)) fail("empty table entry");
    if ((a | b) & ~FULL) fail("table entry outside board");
    if (normalize(a, b).a != a || normalize(a, b).b != b) fail("table entry not normalized");
    if (component(__builtin_ctzll(a | b), a, b) != (a | b)) fail("table entry not connected");
    bool hasL = false, hasR = false, loPure = false, loStar = false, hiPure = false, hiStar = false;
    s64 lo = 0, hi = 0;
    for (u64 m = a; m; m &= m - 1) {
        int v = __builtin_ctzll(m);
        V c = table_sum(a & ~closed_nbhd(v), b & ~(u64(1) << v));
        if (!hasL || c.x > lo) { hasL = true; lo = c.x; loPure = !c.e; loStar = c.e; }
        else if (c.x == lo) { if (c.e) loStar = true; else loPure = true; }
    }
    for (u64 m = b; m; m &= m - 1) {
        int v = __builtin_ctzll(m);
        V c = table_sum(a & ~(u64(1) << v), b & ~closed_nbhd(v));
        if (!hasR || c.x < hi) { hasR = true; hi = c.x; hiPure = !c.e; hiStar = c.e; }
        else if (c.x == hi) { if (c.e) hiStar = true; else hiPure = true; }
    }
    V val;
    s64 z;
    if (simplest(hasL, lo, loPure, hasR, hi, hiPure, z)) {
        val = V{z, 0};
    } else if (hasL && hasR && lo == hi && loPure && !loStar && hiPure && !hiStar) {
        val = V{lo, 1};
    } else {
        fail("table entry whose options give no number or number+star");
    }
    if (val.x != claimed.x || val.e != claimed.e) fail("table entry value mismatch");
}

struct St {
    u64 a, b;
    s64 q;
    int s;
    bool operator==(const St& o) const { return a == o.a && b == o.b && q == o.q && s == o.s; }
};
struct StH {
    size_t operator()(const St& k) const {
        return KeyH()(Key{k.a ^ (u64(k.s) << 63), k.b}) ^ size_t(u64(k.q) * 0x9E3779B97F4A7C15ULL);
    }
};

static St reduce(u64 a, u64 b, s64 q, int s) {
    u64 live = a | b, ha = 0, hb = 0;
    while (live) {
        int v = __builtin_ctzll(live);
        u64 c = component(v, a, b);
        live &= ~c;
        if (__builtin_popcountll(c) <= K) {
            auto it = TABLE.find(normalize(a & c, b & c));
            if (it == TABLE.end()) fail("small component missing from table");
            q += it->second.x;
            s ^= it->second.e;
        } else {
            ha |= a & c;
            hb |= b & c;
        }
    }
    return St{ha, hb, q, s};
}

// Canonical Left option of the number q (fixed point).
static bool left_option(s64 q, s64& ql) {
    if (q & (ONE - 1)) { ql = q - (q & -q); return true; }
    if (q > 0) { ql = q - ONE; return true; }
    return false;
}
// Option `code` of the player to move in reduced state k, as a full state in
// the other player's frame. Returns false if the option does not exist.
static bool apply(const St& k, int code, St& out) {
    if (code >= 0) {
        if (code >= H * W || !(k.a >> code & 1)) return false;
        out = St{k.b & ~(u64(1) << code), k.a & ~closed_nbhd(code), -k.q, k.s};
        return true;
    }
    if (code == -1) {
        s64 ql;
        if (!left_option(k.q, ql)) return false;
        out = St{k.b, k.a, -ql, k.s};
        return true;
    }
    if (code == -2) {
        if (!k.s) return false;
        out = St{k.b, k.a, -k.q, 0};
        return true;
    }
    return false;
}
static int day(s64 q) {
    // birthday of the dyadic q = ip + m/2^k in lowest terms: ip if k = 0, else ip + 1 + k
    s64 aq = q < 0 ? -q : q;
    s64 ip = aq / ONE, fr = aq % ONE;
    if (!fr) return int(ip);
    return int(ip) + 1 + (SH - __builtin_ctzll(u64(fr)));
}
static bool rank_less(const St& x, const St& y) {
    int hx = __builtin_popcountll(x.a | x.b), hy = __builtin_popcountll(y.a | y.b);
    if (hx != hy) return hx < hy;
    return day(x.q) + x.s < day(y.q) + y.s;
}

template <class T> static void rd(FILE* f, T& x) {
    if (std::fread(&x, sizeof(T), 1, f) != 1) fail("truncated certificate");
}

int main(int argc, char** argv) {
    if (argc != 9) {
        std::fprintf(stderr, "usage: checkcert CERT.bin H W A B QNUM QDEN STAR\n");
        return 2;
    }
    FILE* f = std::fopen(argv[1], "rb");
    if (!f) fail("cannot open certificate");
    char magic[8];
    if (std::fread(magic, 1, 8, f) != 8 || std::memcmp(magic, "COLCERT5", 8)) fail("bad magic");
    std::uint32_t h, w, k, sh;
    rd(f, h); rd(f, w); rd(f, k); rd(f, sh);
    H = int(h); W = int(w); K = int(k); SH = int(sh);
    if (H != std::atoi(argv[2]) || W != std::atoi(argv[3])) fail("board size differs from the claim");
    if (H * W > 64 || SH < 8 || SH > 50) fail("bad header");
    ONE = s64(1) << SH;
    FULL = H * W == 64 ? ~u64(0) : (u64(1) << (H * W)) - 1;
    NBR.assign(H * W, 0);
    for (int v = 0; v < H * W; ++v) {
        int r = v / W, c = v % W;
        if (r > 0) NBR[v] |= u64(1) << (v - W);
        if (r + 1 < H) NBR[v] |= u64(1) << (v + W);
        if (c > 0) NBR[v] |= u64(1) << (v - 1);
        if (c + 1 < W) NBR[v] |= u64(1) << (v + 1);
    }
    // claimed root
    u64 ra = std::strtoull(argv[4], nullptr, 10), rb = std::strtoull(argv[5], nullptr, 10);
    long long qn = std::atoll(argv[6]), qd = std::atoll(argv[7]);
    int rs = std::atoi(argv[8]);
    if (qd <= 0 || (qd & (qd - 1))) fail("claim q not dyadic");
    int qk = 0;
    while ((1LL << qk) < qd) ++qk;
    s64 rq = s64(qn) * (ONE >> qk);
    St croot;
    rd(f, croot.a); rd(f, croot.b); rd(f, croot.q);
    std::uint8_t b8;
    rd(f, b8);
    croot.s = b8;
    u64 nt;
    rd(f, nt);
    TABLE.reserve(nt * 2);
    for (u64 i = 0; i < nt; ++i) {
        Key key;
        V v;
        rd(f, key.a); rd(f, key.b); rd(f, v.x); rd(f, b8);
        if (b8 > 1) fail("bad star flag");
        v.e = b8;
        if (!TABLE.emplace(key, v).second) fail("duplicate table entry");
    }
    std::size_t checkedT = 0;
    for (auto& [key, v] : TABLE) { check_table_entry(key, v); ++checkedT; }
    std::fprintf(stderr, "table: %zu entries verified\n", checkedT);

    u64 nc;
    rd(f, nc);
    std::vector<St> states(nc);
    std::vector<std::vector<std::pair<int, int>>> reps(nc);
    std::unordered_map<St, std::size_t, StH> index;
    index.reserve(nc * 2);
    for (u64 i = 0; i < nc; ++i) {
        rd(f, states[i].a); rd(f, states[i].b); rd(f, states[i].q); rd(f, b8);
        if (b8 > 1) fail("bad star flag");
        states[i].s = b8;
        std::uint16_t n;
        rd(f, n);
        reps[i].resize(n);
        for (auto& p : reps[i]) {
            std::int16_t x, y;
            rd(f, x); rd(f, y);
            p = {x, y};
        }
        if (!index.emplace(states[i], i).second) fail("duplicate checkpoint");
    }
    if (std::fgetc(f) != EOF) fail("trailing bytes");
    std::fclose(f);

    std::uint64_t edges = 0;
    for (u64 i = 0; i < nc; ++i) {
        const St& kst = states[i];
        if ((kst.a | kst.b) & ~FULL) fail("checkpoint outside board");
        St red = reduce(kst.a, kst.b, kst.q, kst.s);
        if (!(red == kst)) fail("checkpoint not reduced");
        if (!(kst.a | kst.b)) {
            if (!reps[i].empty()) fail("replies at an empty checkpoint");
            if (kst.q > 0 || (kst.q == 0 && kst.s)) fail("empty checkpoint is not a loss");
            continue;
        }
        // options of the mover
        std::vector<int> codes;
        for (u64 m = kst.a; m; m &= m - 1) codes.push_back(__builtin_ctzll(m));
        s64 ql;
        if (left_option(kst.q, ql)) codes.push_back(-1);
        if (kst.s) codes.push_back(-2);
        if (codes.size() != reps[i].size()) fail("incomplete coverage of the mover's options");
        for (int code : codes) {
            const std::pair<int, int>* rp = nullptr;
            for (auto& p : reps[i]) if (p.first == code) { if (rp) fail("two replies to one option"); rp = &p; }
            if (!rp) fail("option without reply");
            St full, mid, full2;
            if (!apply(kst, code, full)) fail("internal: option");
            mid = reduce(full.a, full.b, full.q, full.s);
            if (!apply(mid, rp->second, full2)) fail("illegal reply");
            St child = reduce(full2.a, full2.b, full2.q, full2.s);
            auto it = index.find(child);
            if (it == index.end()) fail("reply leads to an unlisted state");
            if (!rank_less(child, kst)) fail("no rank descent");
            ++edges;
        }
    }
    St root = reduce(ra, rb, rq, rs);
    if (!(root == croot)) fail("certificate root differs from the claimed root");
    if (!index.count(root)) fail("root is not a checkpoint");
    std::printf("VERIFIED: mover loses. table %zu entries, %llu checkpoints, %llu edges\n", checkedT,
                (unsigned long long)nc, (unsigned long long)edges);
    return 0;
}
