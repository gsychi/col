// colcgt.hpp -- exact values of Col permission positions on grids of <= 64 cells.
//
// DISCOVERY ONLY. Proof claims are checked by the independent Python verifier
// against explicit response DAGs; nothing in this header is trusted by it.
//
// A position is (A,B): A = Blue-legal cells, B = White-legal cells (row-major
// bit r*w+c). Blue at v: (A\N[v], B\{v}); White at v: (A\{v}, B\N[v]).
// Values are dyadic numbers or numbers plus star (the classical Col theorem
// applies because any permission pattern is realised by pendant stones).
// The recurrence aborts on any option set outside that universe.
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

namespace cc {
using u64 = std::uint64_t;
using i64 = std::int64_t;
constexpr int SHIFT = 40;
constexpr i64 ONE = i64(1) << SHIFT;

struct Val {
    i64 num = 0;
    bool star = false;
};
inline Val vadd(Val a, Val b) { return Val{a.num + b.num, bool(a.star ^ b.star)}; }
inline Val vneg(Val a) { return Val{-a.num, a.star}; }
inline bool vle0(Val v) { return v.num < 0 || (v.num == 0 && !v.star); }  // v <= 0
inline bool vlt0(Val v) { return v.num < 0; }                              // v < 0
inline bool veq(Val a, Val b) { return a.num == b.num && a.star == b.star; }

[[noreturn]] inline void die(const std::string& msg) {
    std::fprintf(stderr, "FATAL: %s\n", msg.c_str());
    std::fflush(stderr);
    std::exit(3);
}

inline std::string numstr(i64 num) {
    if (num == 0) return "0";
    bool neg = num < 0;
    unsigned long long u = neg ? (unsigned long long)(-num) : (unsigned long long)num;
    int sh = SHIFT;
    while (sh > 0 && (u & 1ULL) == 0) {
        u >>= 1;
        --sh;
    }
    std::ostringstream os;
    if (neg) os << "-";
    os << u;
    if (sh > 0) os << "/" << (1ULL << sh);
    return os.str();
}
inline std::string valstr(Val v) {
    if (v.num == 0) return v.star ? "*" : "0";
    return numstr(v.num) + (v.star ? "+*" : "");
}
// numerator/denominator of a fixed-point number, denominator a power of two.
inline void numfrac(i64 num, i64& p, i64& q) {
    q = ONE;
    p = num;
    while (q > 1 && (p % 2) == 0) {
        p /= 2;
        q /= 2;
    }
}
inline i64 parse_num(const std::string& s) {
    auto slash = s.find('/');
    if (slash == std::string::npos) return i64(std::stoll(s)) * ONE;
    i64 p = std::stoll(s.substr(0, slash)), q = std::stoll(s.substr(slash + 1));
    if (q <= 0 || (q & (q - 1)) || q > ONE) die("bad dyadic " + s);
    return p * (ONE / q);
}

// Simplest dyadic x with lo <(=) x <(=) hi; "open" means strict.
inline i64 simplest(bool hasLo, i64 lo, bool loOpen, bool hasHi, i64 hi, bool hiOpen) {
    auto ok = [&](i64 x) {
        if (hasLo && (loOpen ? !(x > lo) : !(x >= lo))) return false;
        if (hasHi && (hiOpen ? !(x < hi) : !(x <= hi))) return false;
        return true;
    };
    if (ok(0)) return 0;
    if (!(hasLo && lo >= 0)) {
        if (!(hasHi && hi <= 0)) die("simplest: empty interval");
        return -simplest(true, -hi, hiOpen, hasLo, hasLo ? -lo : 0, loOpen);
    }
    i64 k = lo / ONE;
    for (i64 kk = k; kk <= k + 2; ++kk)
        if (ok(kk * ONE)) return kk * ONE;
    for (int d = 1; d <= SHIFT; ++d) {
        i64 step = ONE >> d;
        i64 m = lo / step;
        for (i64 mm = m; mm <= m + 2; ++mm)
            if (ok(mm * step)) return mm * step;
    }
    die("simplest: precision exceeded");
}

struct Board {
    int h = 0, w = 0, n = 0;
    u64 full = 0, notCol0 = 0, notColLast = 0;
    u64 nb[64] = {}, closed[64] = {};
    Board() {}
    Board(int h_, int w_) : h(h_), w(w_), n(h_ * w_) {
        if (h < 1 || w < 1 || h > 12 || w > 12 || n > 64) die("board too large");
        full = n == 64 ? ~u64(0) : ((u64(1) << n) - 1);
        for (int v = 0; v < n; ++v) {
            int r = v / w, c = v % w;
            if (c != 0) notCol0 |= u64(1) << v;
            if (c != w - 1) notColLast |= u64(1) << v;
            if (r > 0) nb[v] |= u64(1) << (v - w);
            if (r + 1 < h) nb[v] |= u64(1) << (v + w);
            if (c > 0) nb[v] |= u64(1) << (v - 1);
            if (c + 1 < w) nb[v] |= u64(1) << (v + 1);
            closed[v] = nb[v] | (u64(1) << v);
        }
    }
    inline u64 spread(u64 m) const {
        return (((m << 1) & notCol0) | ((m >> 1) & notColLast) | (m << w) | (m >> w)) & full;
    }
    // Component of seed under relevant edges (both endpoints Blue-legal or both White-legal).
    inline u64 flood(u64 seed, u64 A, u64 B) const {
        u64 comp = seed;
        for (;;) {
            u64 g = comp | (spread(comp & A) & A) | (spread(comp & B) & B);
            if (g == comp) return comp;
            comp = g;
        }
    }
    inline u64 blue_move_A(u64 A, int v) const { return A & ~closed[v]; }
};

struct Entry {
    u64 k1, k2;
    i64 v;
};

// Growable open-addressing table; maxLog2 bounds memory (24 bytes per slot).
struct Table {
    std::vector<Entry> t;
    u64 mask;
    std::size_t used = 0;
    int log2, maxLog2;
    bool clear_when_full = false;
    std::size_t clears = 0;
    explicit Table(int maxLog2_) : log2(16), maxLog2(maxLog2_) {
        if (maxLog2 < log2) log2 = maxLog2;
        t.assign(std::size_t(1) << log2, Entry{0, 0, 0});
        mask = (u64(1) << log2) - 1;
    }
    void grow() {
        std::vector<Entry> old;
        old.swap(t);
        ++log2;
        t.assign(std::size_t(1) << log2, Entry{0, 0, 0});
        mask = (u64(1) << log2) - 1;
        used = 0;
        for (const Entry& e : old)
            if (e.k1 || e.k2) insert(e.k1, e.k2, e.v);
    }
    void clear() {
        used = 0;
        log2 = 16 < maxLog2 ? 16 : maxLog2;
        std::vector<Entry>().swap(t);
        t.assign(std::size_t(1) << log2, Entry{0, 0, 0});
        mask = (u64(1) << log2) - 1;
    }
    static inline u64 hash(u64 a, u64 b) {
        u64 x = a * 0x9E3779B97F4A7C15ULL ^ (b + 0x632BE59BD9B4E019ULL) * 0xC2B2AE3D27D4EB4FULL;
        x ^= x >> 31;
        x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 29;
        return x;
    }
    inline bool find(u64 k1, u64 k2, i64& v) const {
        u64 i = hash(k1, k2) & mask;
        for (;;) {
            const Entry& e = t[i];
            if (e.k1 == 0 && e.k2 == 0) return false;
            if (e.k1 == k1 && e.k2 == k2) {
                v = e.v;
                return true;
            }
            i = (i + 1) & mask;
        }
    }
    inline void insert(u64 k1, u64 k2, i64 v) {
        if (used * 10 >= t.size() * 7) {
            if (log2 < maxLog2)
                grow();
            else if (used * 10 >= t.size() * 9) {
                if (!clear_when_full) die("memo table full; increase table size");
                ++clears;
                clear();
            }
        }
        u64 i = hash(k1, k2) & mask;
        for (;;) {
            Entry& e = t[i];
            if (e.k1 == 0 && e.k2 == 0) {
                e.k1 = k1;
                e.k2 = k2;
                e.v = v;
                ++used;
                return;
            }
            if (e.k1 == k1 && e.k2 == k2) return;
            i = (i + 1) & mask;
        }
    }
};

// Canonical component key under the rectangle symmetries (including transpose)
// and colour swap. Keys are independent of the ambient board.
struct Canon {
    unsigned revtab[13][4096];
    Canon() {
        for (int wd = 1; wd <= 12; ++wd)
            for (unsigned x = 0; x < (1u << wd); ++x) {
                unsigned r = 0;
                for (int i = 0; i < wd; ++i) r |= ((x >> i) & 1u) << (wd - 1 - i);
                revtab[wd][x] = r;
            }
    }
    // Returns +1 or -1 (colour swapped).
    inline int key(const Board& bd, u64 A, u64 B, u64& k1, u64& k2) const {
        const int W = bd.w;
        u64 live = A | B;
        int rmin = 99, rmax = -1;
        unsigned cols = 0;
        const unsigned wm = (W >= 32) ? ~0u : ((1u << W) - 1);
        for (int r = 0; r < bd.h; ++r) {
            unsigned lr = unsigned(live >> (r * W)) & wm;
            if (lr) {
                if (rmin == 99) rmin = r;
                rmax = r;
                cols |= lr;
            }
        }
        int cmin = __builtin_ctz(cols), cmax = 31 - __builtin_clz(cols);
        int hc = rmax - rmin + 1, wc = cmax - cmin + 1;
        if (hc > 12 || wc > 12 || hc * wc > 56) die("component bounding box too large");
        unsigned cm = (1u << wc) - 1;
        unsigned ra[12], rb[12], ta[12] = {0}, tb[12] = {0};
        for (int r = 0; r < hc; ++r) {
            ra[r] = unsigned(A >> ((r + rmin) * W + cmin)) & cm;
            rb[r] = unsigned(B >> ((r + rmin) * W + cmin)) & cm;
            for (int c = 0; c < wc; ++c) {
                ta[c] |= ((ra[r] >> c) & 1u) << r;
                tb[c] |= ((rb[r] >> c) & 1u) << r;
            }
        }
        u64 best1 = ~u64(0), best2 = ~u64(0);
        int sign = 1;
        auto consider = [&](const unsigned* xa, const unsigned* xb, int hh, int ww) {
            for (int vflip = 0; vflip < 2; ++vflip)
                for (int hflip = 0; hflip < 2; ++hflip) {
                    u64 pa = 0, pb = 0;
                    for (int r = 0; r < hh; ++r) {
                        int rr = vflip ? (hh - 1 - r) : r;
                        unsigned a = xa[rr], b = xb[rr];
                        if (hflip) {
                            a = revtab[ww][a];
                            b = revtab[ww][b];
                        }
                        pa |= u64(a) << (r * ww);
                        pb |= u64(b) << (r * ww);
                    }
                    u64 tag = (u64(hh) << 60) | (u64(ww) << 56);
                    u64 c1 = pa | tag, c2 = pb;
                    if (c1 < best1 || (c1 == best1 && c2 < best2)) {
                        best1 = c1;
                        best2 = c2;
                        sign = 1;
                    }
                    c1 = pb | tag;
                    c2 = pa;
                    if (c1 < best1 || (c1 == best1 && c2 < best2)) {
                        best1 = c1;
                        best2 = c2;
                        sign = -1;
                    }
                }
        };
        consider(ra, rb, hc, wc);
        consider(ta, tb, wc, hc);
        k1 = best1;
        k2 = best2;
        return sign;
    }
};

struct Engine {
    const Board& bd;
    Table& memo;
    const Canon& canon;
    std::uint64_t misses = 0, calls = 0;
    Table* big = nullptr;  // optional never-cleared cache for large components
    int bigMin = 14;
    Engine(const Board& b, Table& m, const Canon& c) : bd(b), memo(m), canon(c) {}

    Val position(u64 A, u64 B) {
        Val total;
        u64 live = A | B;
        while (live) {
            u64 seed = live & (~live + 1);
            u64 comp = bd.flood(seed, A, B);
            live &= ~comp;
            total = vadd(total, component(A & comp, B & comp));
        }
        return total;
    }

    Val component(u64 A, u64 B) {
        ++calls;
        u64 live = A | B;
        if ((live & (live - 1)) == 0) {
            if (A && B) return Val{0, true};
            return Val{A ? ONE : -ONE, false};
        }
        u64 k1, k2;
        int sign = canon.key(bd, A, B, k1, k2);
        i64 packed;
        if (memo.find(k1, k2, packed)) {
            Val v{packed >> 1, bool(packed & 1)};
            return sign > 0 ? v : vneg(v);
        }
        bool isBig = big && __builtin_popcountll(live) >= bigMin;
        if (isBig && big->find(k1, k2, packed)) {
            Val v{packed >> 1, bool(packed & 1)};
            memo.insert(k1, k2, packed);
            return sign > 0 ? v : vneg(v);
        }
        ++misses;
        Val v = compute(A, B);
        Val stored = sign > 0 ? v : vneg(v);
        memo.insert(k1, k2, stored.num * 2 + (stored.star ? 1 : 0));
        if (isBig) big->insert(k1, k2, stored.num * 2 + (stored.star ? 1 : 0));
        return v;
    }

    // A Blue-only cell w is a dominated Blue option if some Blue-legal
    // neighbour u satisfies N[u]&A subset of N[w]&A: the u-child then has a
    // Blue superset and White subset of the w-child on the same graph.
    inline bool blue_dominated(int wv, u64 A, u64 B) const {
        u64 nw = bd.closed[wv] & A;
        u64 cand = bd.nb[wv] & A;
        while (cand) {
            int u = __builtin_ctzll(cand);
            cand &= cand - 1;
            u64 nu = bd.closed[u] & A;
            if ((nu & ~nw) != 0) continue;
            bool uPrivate = !((B >> u) & 1);
            if (!uPrivate) return true;
            if (nu != nw) return true;
            if (u < wv) return true;
        }
        return false;
    }
    inline bool white_dominated(int wv, u64 A, u64 B) const {
        u64 nw = bd.closed[wv] & B;
        u64 cand = bd.nb[wv] & B;
        while (cand) {
            int u = __builtin_ctzll(cand);
            cand &= cand - 1;
            u64 nu = bd.closed[u] & B;
            if ((nu & ~nw) != 0) continue;
            bool uPrivate = !((A >> u) & 1);
            if (!uPrivate) return true;
            if (nu != nw) return true;
            if (u < wv) return true;
        }
        return false;
    }

    Val compute(u64 A, u64 B) {
        bool haveL = false, haveR = false;
        i64 lo = 0, hi = 0;
        bool loPure = false, loStar = false, hiPure = false, hiStar = false;
        for (u64 m = A; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            u64 bit = u64(1) << v;
            if (!(B & bit) && blue_dominated(v, A, B)) continue;
            Val c = position(A & ~bd.closed[v], B & ~bit);
            if (!haveL || c.num > lo) {
                haveL = true;
                lo = c.num;
                loPure = !c.star;
                loStar = c.star;
            } else if (c.num == lo) {
                if (c.star)
                    loStar = true;
                else
                    loPure = true;
            }
        }
        for (u64 m = B; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            u64 bit = u64(1) << v;
            if (!(A & bit) && white_dominated(v, A, B)) continue;
            Val c = position(A & ~bit, B & ~bd.closed[v]);
            if (!haveR || c.num < hi) {
                haveR = true;
                hi = c.num;
                hiPure = !c.star;
                hiStar = c.star;
            } else if (c.num == hi) {
                if (c.star)
                    hiStar = true;
                else
                    hiPure = true;
            }
        }
        if (haveL && haveR) {
            if (lo > hi) die("hot option set: lo=" + numstr(lo) + " hi=" + numstr(hi));
            if (lo == hi) {
                if (loPure && !loStar && hiPure && !hiStar) return Val{lo, true};
                if (!loPure && loStar && !hiPure && hiStar) return Val{lo, false};
                die("mixed star boundary at " + numstr(lo));
            }
        }
        return Val{simplest(haveL, lo, loPure, haveR, hi, hiPure), false};
    }

    // Value of (A,B) plus auxiliary number p and star s.
    inline Val with_aux(u64 A, u64 B, i64 p, bool s) { return vadd(position(A, B), Val{p, s}); }
};

// Left / Right options of a canonical dyadic number (fixed point).
inline bool left_of_number(i64 p, i64& out) {
    if (p % ONE != 0) {
        i64 q, d;
        numfrac(p, q, d);
        out = p - ONE / d;
        return true;
    }
    if (p > 0) {
        out = p - ONE;
        return true;
    }
    return false;
}
inline bool right_of_number(i64 p, i64& out) {
    if (p % ONE != 0) {
        i64 q, d;
        numfrac(p, q, d);
        out = p + ONE / d;
        return true;
    }
    if (p < 0) {
        out = p + ONE;
        return true;
    }
    return false;
}

inline std::string rows_str(const Board& bd, u64 A, u64 B) {
    std::string s;
    for (int r = 0; r < bd.h; ++r) {
        if (r) s += "/";
        for (int c = 0; c < bd.w; ++c) {
            int v = r * bd.w + c;
            bool a = (A >> v) & 1, b = (B >> v) & 1;
            s += a && b ? 'o' : a ? 'b' : b ? 'w' : '.';
        }
    }
    return s;
}
inline void parse_rows(const Board& bd, const std::string& s, u64& A, u64& B) {
    A = B = 0;
    int r = 0, c = 0;
    for (char ch : s) {
        if (ch == '/') {
            if (c != bd.w) die("bad row length in " + s);
            ++r;
            c = 0;
            continue;
        }
        int v = r * bd.w + c;
        if (ch == 'o' || ch == 'b') A |= u64(1) << v;
        if (ch == 'o' || ch == 'w') B |= u64(1) << v;
        ++c;
    }
    if (r != bd.h - 1 || c != bd.w) die("bad pattern " + s);
}

}  // namespace cc
