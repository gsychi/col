// colcore.h: shared exact-value engine for Col permission positions.
// See colval.cpp for the description of the (theorem-free) value rules.
#pragma once
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cinttypes>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

using Mask = std::uint64_t;
using i64 = std::int64_t;

static const int SHIFT = 40;  // fixed-point: value = num / 2^SHIFT
static const i64 ONE = i64(1) << SHIFT;

struct Val {
    i64 num = 0;
    bool star = false;
};
static inline Val vadd(Val a, Val b) { return Val{a.num + b.num, bool(a.star ^ b.star)}; }
static inline Val vneg(Val a) { return Val{-a.num, a.star}; }

static std::string numstr(i64 num) {
    if (num == 0) return "0";
    bool neg = num < 0;
    unsigned long long u = neg ? (unsigned long long)(-num) : (unsigned long long)num;
    int sh = SHIFT;
    while (sh > 0 && (u & 1ULL) == 0) { u >>= 1; --sh; }
    std::ostringstream os;
    if (neg) os << "-";
    os << u;
    if (sh > 0) os << "/" << (1ULL << sh);
    return os.str();
}
static std::string valstr(Val v) {
    if (v.num == 0) return v.star ? "*" : "0";
    return numstr(v.num) + (v.star ? "+*" : "");
}

[[noreturn]] static void die(const std::string& msg) {
    std::fprintf(stderr, "FATAL: %s\n", msg.c_str());
    std::fflush(stderr);
    std::exit(3);
}

// Simplest dyadic x with lo <(=) x <(=) hi (fixed point).
static i64 simplest(bool hasLo, i64 lo, bool loOpen, bool hasHi, i64 hi, bool hiOpen) {
    auto ok = [&](i64 x) {
        if (hasLo && (loOpen ? !(x > lo) : !(x >= lo))) return false;
        if (hasHi && (hiOpen ? !(x < hi) : !(x <= hi))) return false;
        return true;
    };
    if (ok(0)) return 0;
    bool negSide = !(hasLo && lo >= 0);
    if (negSide) {
        if (!(hasHi && hi <= 0)) die("simplest: empty interval (neg)");
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
    die("simplest: precision exceeded or empty interval");
}

struct Board {
    int h, w, n;
    Mask full, notCol0, notColLast;
    std::vector<Mask> nb, closed;
    Board(int h_, int w_) : h(h_), w(w_), n(h_ * w_) {
        if (h > 16 || w > 16 || n > 60) die("board too large (max 60 cells, sides <= 16)");
        full = (Mask(1) << n) - 1;
        notCol0 = notColLast = 0;
        nb.assign(n, 0);
        closed.assign(n, 0);
        for (int v = 0; v < n; ++v) {
            int r = v / w, c = v % w;
            if (c != 0) notCol0 |= Mask(1) << v;
            if (c != w - 1) notColLast |= Mask(1) << v;
            if (r > 0) nb[v] |= Mask(1) << (v - w);
            if (r + 1 < h) nb[v] |= Mask(1) << (v + w);
            if (c > 0) nb[v] |= Mask(1) << (v - 1);
            if (c + 1 < w) nb[v] |= Mask(1) << (v + 1);
            closed[v] = nb[v] | (Mask(1) << v);
        }
    }
    inline Mask spread(Mask m) const {
        return (((m << 1) & notCol0) | ((m >> 1) & notColLast) | (m << w) | (m >> w)) & full;
    }
    inline Mask flood(Mask seed, Mask A, Mask B) const {
        Mask comp = seed;
        for (;;) {
            Mask g = comp | (spread(comp & A) & A) | (spread(comp & B) & B);
            if (g == comp) return comp;
            comp = g;
        }
    }
};

// ------------------------------------------------ lossy set-associative cache
// Each bucket has 4 entries and a spinlock. Values are exact; eviction only
// costs recomputation. Entry value word: ((num*2+star) << 7) | weight.
struct Entry {
    Mask k1, k2;
    i64 v;
};
struct Bucket {
    std::atomic<std::uint32_t> lock{0};
    std::uint32_t pad = 0;
    Entry e[4];
};

struct Cache {
    std::unique_ptr<Bucket[]> b;
    Mask mask;
    std::size_t nb;
    std::atomic<std::uint64_t> used{0}, evictions{0};
    explicit Cache(int log2) : nb(std::size_t(1) << log2), mask((Mask(1) << log2) - 1) {
        b.reset(new Bucket[nb]);
        for (std::size_t i = 0; i < nb; ++i) std::memset((void*)b[i].e, 0, sizeof(b[i].e));
    }
    static inline Mask hash(Mask a, Mask c) {
        Mask x = a * 0x9E3779B97F4A7C15ULL ^ (c + 0x632BE59BD9B4E019ULL) * 0xC2B2AE3D27D4EB4FULL;
        x ^= x >> 31; x *= 0xbf58476d1ce4e5b9ULL; x ^= x >> 29;
        return x;
    }
    static inline void acquire(Bucket& bk) {
        std::uint32_t z = 0;
        while (!bk.lock.compare_exchange_weak(z, 1, std::memory_order_acquire)) { z = 0; }
    }
    static inline void release(Bucket& bk) { bk.lock.store(0, std::memory_order_release); }
    inline bool find(Mask k1, Mask k2, i64& v) {
        Bucket& bk = b[hash(k1, k2) & mask];
        acquire(bk);
        bool ok = false;
        for (int i = 0; i < 4; ++i)
            if (bk.e[i].k1 == k1 && bk.e[i].k2 == k2) { v = bk.e[i].v >> 7; ok = true; break; }
        release(bk);
        return ok;
    }
    inline void insert(Mask k1, Mask k2, i64 v, int weight) {
        Bucket& bk = b[hash(k1, k2) & mask];
        i64 word = (v << 7) | weight;
        acquire(bk);
        int empty = -1, victim = 0, minw = 1 << 30;
        for (int i = 0; i < 4; ++i) {
            if (bk.e[i].k1 == k1 && bk.e[i].k2 == k2) { release(bk); return; }
            if (bk.e[i].k1 == 0 && bk.e[i].k2 == 0) { if (empty < 0) empty = i; continue; }
            int wgt = int(bk.e[i].v & 127);
            if (wgt < minw) { minw = wgt; victim = i; }
        }
        int slot = empty >= 0 ? empty : victim;
        if (empty >= 0) used.fetch_add(1, std::memory_order_relaxed);
        else evictions.fetch_add(1, std::memory_order_relaxed);
        bk.e[slot].k1 = k1; bk.e[slot].k2 = k2; bk.e[slot].v = word;
        release(bk);
    }
};

struct Solver {
    const Board& bd;
    Cache& memo;
    std::uint64_t misses = 0;
    unsigned revtab[17][1 << 16];
    Solver(const Board& b, Cache& m) : bd(b), memo(m) {
        for (int wd = 1; wd <= 16; ++wd)
            for (unsigned x = 0; x < (1u << wd); ++x) {
                unsigned r = 0;
                for (int i = 0; i < wd; ++i) r |= ((x >> i) & 1u) << (wd - 1 - i);
                revtab[wd][x] = r;
            }
    }

    // Canonical key under the 4 rectangle symmetries and colour swap.
    inline int canon(Mask A, Mask B, Mask& k1, Mask& k2) const {
        const int W = bd.w;
        Mask live = A | B;
        int rmin = 99, rmax = -1;
        unsigned cols = 0;
        const unsigned wm = (1u << W) - 1;
        unsigned ra[16], rb[16];
        for (int r = 0; r < bd.h; ++r) {
            unsigned lr = unsigned(live >> (r * W)) & wm;
            if (lr) { if (rmin == 99) rmin = r; rmax = r; cols |= lr; }
        }
        int cmin = __builtin_ctz(cols), cmax = 31 - __builtin_clz(cols);
        int hc = rmax - rmin + 1, wc = cmax - cmin + 1;
        unsigned cm = (1u << wc) - 1;
        for (int r = 0; r < hc; ++r) {
            ra[r] = unsigned(A >> ((r + rmin) * W + cmin)) & cm;
            rb[r] = unsigned(B >> ((r + rmin) * W + cmin)) & cm;
        }
        Mask best1 = ~Mask(0), best2 = ~Mask(0);
        int sign = 1;
        for (int vflip = 0; vflip < 2; ++vflip) {
            for (int hflip = 0; hflip < 2; ++hflip) {
                Mask pa = 0, pb = 0;
                for (int r = 0; r < hc; ++r) {
                    int rr = vflip ? (hc - 1 - r) : r;
                    unsigned xa = ra[rr], xb = rb[rr];
                    if (hflip) { xa = revtab[wc][xa]; xb = revtab[wc][xb]; }
                    pa |= Mask(xa) << (r * wc);
                    pb |= Mask(xb) << (r * wc);
                }
                if (pa < best1 || (pa == best1 && pb < best2)) { best1 = pa; best2 = pb; sign = 1; }
                if (pb < best1 || (pb == best1 && pa < best2)) { best1 = pb; best2 = pa; sign = -1; }
            }
        }
        k1 = best1 | (Mask(hc) << 60);
        k2 = best2 | (Mask(wc) << 60);
        return sign;
    }

    Val position(Mask A, Mask B) {
        Val total;
        Mask live = A | B;
        while (live) {
            Mask seed = live & (~live + 1);
            Mask comp = bd.flood(seed, A, B);
            live &= ~comp;
            total = vadd(total, component(A & comp, B & comp));
        }
        return total;
    }

    Val component(Mask A, Mask B) {
        Mask live = A | B;
        if ((live & (live - 1)) == 0) {
            if (A && B) return Val{0, true};
            return Val{A ? ONE : -ONE, false};
        }
        Mask k1, k2;
        int sign = canon(A, B, k1, k2);
        i64 packed;
        if (memo.find(k1, k2, packed)) {
            Val v{packed >> 1, bool(packed & 1)};
            return sign > 0 ? v : vneg(v);
        }
        ++misses;
        Val v = compute(A, B);
        Val stored = sign > 0 ? v : vneg(v);
        memo.insert(k1, k2, stored.num * 2 + (stored.star ? 1 : 0), __builtin_popcountll(live));
        return v;
    }

    inline bool blue_dominated(int wv, Mask A, Mask B) const {
        Mask nw = bd.closed[wv] & A;
        Mask cand = bd.nb[wv] & A;
        while (cand) {
            int u = __builtin_ctzll(cand);
            cand &= cand - 1;
            Mask nu = bd.closed[u] & A;
            if ((nu & ~nw) != 0) continue;
            if ((B >> u) & 1) return true;
            if (nu != nw) return true;
            if (u < wv) return true;
        }
        return false;
    }
    inline bool white_dominated(int wv, Mask A, Mask B) const {
        Mask nw = bd.closed[wv] & B;
        Mask cand = bd.nb[wv] & B;
        while (cand) {
            int u = __builtin_ctzll(cand);
            cand &= cand - 1;
            Mask nu = bd.closed[u] & B;
            if ((nu & ~nw) != 0) continue;
            if ((A >> u) & 1) return true;
            if (nu != nw) return true;
            if (u < wv) return true;
        }
        return false;
    }

    Val compute(Mask A, Mask B) {
        bool haveL = false, haveR = false;
        i64 lo = 0, hi = 0;
        bool loPure = false, loStar = false, hiPure = false, hiStar = false;
        for (Mask m = A; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            Mask bit = Mask(1) << v;
            if (!(B & bit) && blue_dominated(v, A, B)) continue;
            Val c = position(A & ~bd.closed[v], B & ~bit);
            if (!haveL || c.num > lo) { haveL = true; lo = c.num; loPure = !c.star; loStar = c.star; }
            else if (c.num == lo) { if (c.star) loStar = true; else loPure = true; }
        }
        for (Mask m = B; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            Mask bit = Mask(1) << v;
            if (!(A & bit) && white_dominated(v, A, B)) continue;
            Val c = position(A & ~bit, B & ~bd.closed[v]);
            if (!haveR || c.num < hi) { haveR = true; hi = c.num; hiPure = !c.star; hiStar = c.star; }
            else if (c.num == hi) { if (c.star) hiStar = true; else hiPure = true; }
        }
        if (haveL && haveR) {
            if (lo > hi) die("hot option set (not number/number+star): lo=" + numstr(lo) + " hi=" + numstr(hi));
            if (lo == hi) {
                if (loPure && !loStar && hiPure && !hiStar) return Val{lo, true};
                if (!loPure && loStar && !hiPure && hiStar) return Val{lo, false};
                die("mixed star boundary at " + numstr(lo));
            }
        }
        return Val{simplest(haveL, lo, loPure, haveR, hi, hiPure), false};
    }

    // Positions reached by one move (Blue then White) from (A,B).
    std::vector<std::pair<Mask, Mask>> children(Mask A, Mask B) const {
        std::vector<std::pair<Mask, Mask>> out;
        for (Mask m = A; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            out.push_back({A & ~bd.closed[v], B & ~(Mask(1) << v)});
        }
        for (Mask m = B; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            out.push_back({A & ~(Mask(1) << v), B & ~bd.closed[v]});
        }
        return out;
    }
};

