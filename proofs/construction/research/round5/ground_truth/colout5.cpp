// colout5: outcome search for  G + q (+*)  on Col permission positions, with
// exact folding of small components, plus a bisection driver for exact values.
//
// Same search semantics as colout.cpp (discovery tool, EVIDENCE level); the
// changes are engineering only:
//   * the transposition table stores the last winning move of every entry
//     (in the entry's canonical coordinates) and it is tried first;
//   * history heuristic per side;
//   * root children identical up to the board's symmetries are searched once;
//   * idle root threads help on unfinished root children with a perturbed
//     move order (shared table), so stragglers finish sooner;
//   * progress lines on stderr, a wall-clock limit (-L seconds) after which
//     the query is reported INCONCLUSIVE, and a persistent component-value
//     file (-V load, -W save; keys are board-independent).
//
// Node (A, B, q, s) is in the MOVER's frame: A = cells legal for the player to
// move, B = cells legal for the opponent, q = number (mover's view), s = star.
// Mover wins at a leaf with no hard component iff q > 0 or (q == 0 and s).
//
// Usage:
//   colout5 [-t LOG2] [-T LOG2] [-S smax] [-j threads] [-L seconds] [-V in] [-W out] < queries
// Query lines:
//   value h w A B label [guess]
//   outcome h w A B q star label
#include "colcore.h"

#include <mutex>

static i64 parse_dyadic(const std::string& s) {
    auto slash = s.find('/');
    long long num = std::stoll(s.substr(0, slash));
    long long den = slash == std::string::npos ? 1 : std::stoll(s.substr(slash + 1));
    if (den <= 0 || (den & (den - 1))) die("not dyadic: " + s);
    int k = 0;
    while ((1LL << k) < den) ++k;
    return (i64)num << (SHIFT - k);
}

static inline bool left_option(i64 q, i64& ql) {
    if (q & (ONE - 1)) {
        i64 low = q & -q;
        ql = q - low;
        return true;
    }
    if (q > 0) { ql = q - ONE; return true; }
    return false;
}

static inline void spin_lock(std::atomic<std::uint32_t>& l) {
    std::uint32_t z = 0;
    while (!l.compare_exchange_weak(z, 1, std::memory_order_acquire)) { z = 0; }
}
static inline void spin_unlock(std::atomic<std::uint32_t>& l) { l.store(0, std::memory_order_release); }

static int g_histShift = 8;
static int g_useBest = 1;
static int g_refute = 0;
static int g_quickRefute = 0;
static int g_etc = 0;
// Certificate mode: fold exactly the components with at most smax cells (no
// cached large components, no separate valuation of extra hard components).
static int g_certMode = 0;
static int g_stats = 0;
static int g_pass = 0;
static const i64 QINF = i64(1) << 62;
static const int MV_NONE = 0xFF, MV_NUM = 0xF1, MV_STAR = 0xF2;

// info: bit1 star, bit2 valid, bits 8..15 best move code, bits 16.. weight
struct TTEntry {
    Mask k1, k2;
    i64 winAt, loseAt;
    std::uint64_t info;
};
struct TTBucket {
    std::atomic<std::uint32_t> lock{0};
    std::uint32_t pad = 0;
    TTEntry e[4];
};
struct TT {
    std::unique_ptr<TTBucket[]> b;
    Mask mask;
    std::atomic<std::uint64_t> used{0};
    explicit TT(int log2) : mask((Mask(1) << log2) - 1) {
        b.reset(new TTBucket[std::size_t(1) << log2]);
        for (std::size_t i = 0; i <= mask; ++i) std::memset((void*)b[i].e, 0, sizeof(b[i].e));
    }
    static inline Mask hash(Mask a, Mask c, bool s) {
        Mask x = Cache::hash(a, c) ^ (s ? 0x9E3779B97F4A7C15ULL : 0);
        x ^= x >> 32; x *= 0xbf58476d1ce4e5b9ULL; x ^= x >> 29;
        return x;
    }
    // returns 1 win, 0 loss, -1 unknown; best = stored move code
    int find(Mask k1, Mask k2, i64 q, bool s, int& best) {
        TTBucket& bk = b[hash(k1, k2, s) & mask];
        spin_lock(bk.lock);
        int res = -1;
        best = MV_NONE;
        for (int i = 0; i < 4; ++i) {
            TTEntry& e = bk.e[i];
            if ((e.info & 4) && e.k1 == k1 && e.k2 == k2 && bool(e.info & 2) == s) {
                if (q >= e.winAt) res = 1;
                else if (q <= e.loseAt) res = 0;
                best = int((e.info >> 8) & 0xFF);
                break;
            }
        }
        spin_unlock(bk.lock);
        return res;
    }
    void insert(Mask k1, Mask k2, i64 q, bool s, bool res, int best, std::uint64_t weight) {
        TTBucket& bk = b[hash(k1, k2, s) & mask];
        spin_lock(bk.lock);
        int slot = -1;
        std::uint64_t minw = ~0ULL;
        bool existing = false;
        for (int i = 0; i < 4; ++i) {
            TTEntry& e = bk.e[i];
            if ((e.info & 4) && e.k1 == k1 && e.k2 == k2 && bool(e.info & 2) == s) { slot = i; existing = true; break; }
        }
        if (!existing) {
            for (int i = 0; i < 4; ++i) {
                TTEntry& e = bk.e[i];
                if (!(e.info & 4)) { slot = i; break; }
                if ((e.info >> 16) < minw) { minw = e.info >> 16; slot = i; }
            }
            TTEntry& e = bk.e[slot];
            if (!(e.info & 4)) used.fetch_add(1, std::memory_order_relaxed);
            e.k1 = k1; e.k2 = k2; e.winAt = QINF; e.loseAt = -QINF;
            e.info = (s ? 2 : 0) | 4 | (std::uint64_t(MV_NONE) << 8);
        }
        TTEntry& e = bk.e[slot];
        if (res) { if (q < e.winAt) e.winAt = q; }
        else { if (q > e.loseAt) e.loseAt = q; }
        std::uint64_t mv = (e.info >> 8) & 0xFF;
        if (res && best != MV_NONE) mv = std::uint64_t(best);
        std::uint64_t wt = std::min<std::uint64_t>((e.info >> 16) + weight, (1ULL << 47));
        e.info = (e.info & 0xff) | (mv << 8) | (wt << 16);
        spin_unlock(bk.lock);
    }
};

struct Xf {
    int rmin = 0, cmin = 0, hc = 0, wc = 0, vflip = 0, hflip = 0;
};

struct Search {
    const Board& bd;
    Solver vs;
    TT& tt;
    int smax;
    std::atomic<bool>* abortG = nullptr;
    std::atomic<bool>* abortL = nullptr;
    std::uint64_t nodes = 0, valued = 0, refuted = 0, etcHits = 0, passed = 0;
    std::uint64_t wonFirst = 0, wonLater = 0, wasteNodes = 0, wonNodes = 0, lostNodes = 0, lostCount = 0;
    unsigned jitter = 0;
    int killer[64][2];
    std::uint32_t hist[2][64];

    Search(const Board& b, Cache& vc, TT& t, int s) : bd(b), vs(b, vc), tt(t), smax(s) {
        for (auto& k : killer) k[0] = k[1] = -1;
        std::memset(hist, 0, sizeof(hist));
    }
    inline bool aborted() const {
        return (abortG && abortG->load(std::memory_order_relaxed)) || (abortL && abortL->load(std::memory_order_relaxed));
    }

    inline int alpha_upper(Mask S) const {
        Mask rem = S;
        int matched = 0;
        while (rem) {
            int v = __builtin_ctzll(rem);
            Mask bit = Mask(1) << v;
            rem &= ~bit;
            Mask nbr = bd.nb[v] & rem;
            if (nbr) {
                Mask u = nbr & (~nbr + 1);
                rem &= ~u;
                ++matched;
            }
        }
        return __builtin_popcountll(S) - matched;
    }

    inline void canon_geo(Mask A, Mask B, Mask& k1, Mask& k2, Xf& xf) const {
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
        int bv = 0, bh = 0;
        for (int vflip = 0; vflip < 2; ++vflip)
            for (int hflip = 0; hflip < 2; ++hflip) {
                Mask pa = 0, pb = 0;
                for (int r = 0; r < hc; ++r) {
                    int rr = vflip ? (hc - 1 - r) : r;
                    unsigned xa = ra[rr], xb = rb[rr];
                    if (hflip) { xa = vs.revtab[wc][xa]; xb = vs.revtab[wc][xb]; }
                    pa |= Mask(xa) << (r * wc);
                    pb |= Mask(xb) << (r * wc);
                }
                if (pa < best1 || (pa == best1 && pb < best2)) { best1 = pa; best2 = pb; bv = vflip; bh = hflip; }
            }
        k1 = best1 | (Mask(hc) << 60);
        k2 = best2 | (Mask(wc) << 60);
        xf = Xf{rmin, cmin, hc, wc, bv, bh};
    }
    inline int to_code(int v, const Xf& x) const {
        int r = v / bd.w - x.rmin, c = v % bd.w - x.cmin;
        if (x.vflip) r = x.hc - 1 - r;
        if (x.hflip) c = x.wc - 1 - c;
        return r * 16 + c;
    }
    inline int from_code(int code, const Xf& x) const {
        int r = code >> 4, c = code & 15;
        if (x.vflip) r = x.hc - 1 - r;
        if (x.hflip) c = x.wc - 1 - c;
        return (r + x.rmin) * bd.w + (c + x.cmin);
    }

    struct Folded {
        Mask HA = 0, HB = 0;
        int nhard = 0;
        i64 q;
        bool s;
    };

    inline Folded fold(Mask A, Mask B, i64 q, bool s) {
        Folded f;
        Mask live = A | B;
        while (live) {
            Mask seed = live & (~live + 1);
            Mask comp = bd.flood(seed, A, B);
            live &= ~comp;
            Mask ca = A & comp, cb = B & comp;
            if (__builtin_popcountll(comp) <= smax) {
                Val v = vs.component(ca, cb);
                q += v.num;
                s ^= v.star;
            } else {
                Mask k1, k2;
                int sign = g_certMode ? 0 : vs.canon(ca, cb, k1, k2);
                i64 packed;
                if (!g_certMode && vs.memo.find(k1, k2, packed)) {
                    Val v{packed >> 1, bool(packed & 1)};
                    if (sign < 0) v = vneg(v);
                    q += v.num;
                    s ^= v.star;
                } else {
                    f.HA |= ca; f.HB |= cb; ++f.nhard;
                }
            }
        }
        f.q = q;
        f.s = s;
        return f;
    }

    bool value_of(Mask ca, Mask cb, int depth, Val& out) {
        i64 lo = -i64(alpha_upper(cb) + 1) * ONE, hi = i64(alpha_upper(ca) + 1) * ONE;
        i64 t = simplest(true, lo, true, true, hi, true);
        for (;;) {
            int w1 = win(ca, cb, -t, false, depth + 1);
            if (w1 < 0) return false;
            int w2 = win(cb, ca, t, false, depth + 1);
            if (w2 < 0) return false;
            if (!w1 && !w2) { out = Val{t, false}; break; }
            if (w1 && w2) {
                int w3 = win(ca, cb, -t, true, depth + 1);
                if (w3 < 0) return false;
                int w4 = win(cb, ca, t, true, depth + 1);
                if (w4 < 0) return false;
                if (w3 || w4) die("component confused with a number but not number+star");
                out = Val{t, true};
                break;
            }
            if (w1) lo = t; else hi = t;
            if (lo >= hi) die("value_of: interval collapsed");
            t = simplest(true, lo, true, true, hi, true);
        }
        Mask k1, k2;
        int sign = vs.canon(ca, cb, k1, k2);
        Val st = sign > 0 ? out : vneg(out);
        vs.memo.insert(k1, k2, st.num * 2 + (st.star ? 1 : 0), __builtin_popcountll(ca | cb));
        ++valued;
        return true;
    }

    // Static evaluation without search: 1 win, 0 loss, -1 unknown.
    inline int quick(Mask A, Mask B, i64 q, bool s) {
        Folded f = fold(A, B, q, s);
        if (!(f.HA | f.HB)) return (f.q > 0 || (f.q == 0 && f.s)) ? 1 : 0;
        if (f.q - i64(alpha_upper(f.HB)) * ONE > 0) return 1;
        if (f.q + i64(alpha_upper(f.HA)) * ONE < 0) return 0;
        Mask k1, k2;
        Xf xf;
        if (f.nhard == 1) canon_geo(f.HA, f.HB, k1, k2, xf);
        else { k1 = f.HA | (Mask(15) << 60); k2 = f.HB | (Mask(15) << 60); }
        int bc;
        return tt.find(k1, k2, f.q, f.s, bc);
    }

    // 1 = mover wins, 0 = mover loses, -1 = aborted.
    // et: expected node type, 1 = mover expected to lose (AND), 0 = win, -1 unknown.
    int win(Mask A, Mask B, i64 q, bool s, int depth, int et = -1) {
        if (aborted()) return -1;
        ++nodes;
        Folded f = fold(A, B, q, s);
        q = f.q; s = f.s;
        Mask HA = f.HA, HB = f.HB;
        if (!(HA | HB)) return (q > 0 || (q == 0 && s)) ? 1 : 0;
        int ubA = alpha_upper(HA), ubB = alpha_upper(HB);
        if (q - i64(ubB) * ONE > 0) return 1;
        if (q + i64(ubA) * ONE < 0) return 0;
        Mask k1, k2;
        Xf xf;
        if (f.nhard == 1) canon_geo(HA, HB, k1, k2, xf);
        else { k1 = HA | (Mask(15) << 60); k2 = HB | (Mask(15) << 60); xf = Xf{0, 0, bd.h, bd.w, 0, 0}; }
        int bestCode;
        int cached = tt.find(k1, k2, q, s, bestCode);
        if (cached >= 0) return cached;
        std::uint64_t n0 = nodes;
        if (f.nhard >= 2 && !g_certMode) {
            Mask rest = HA | HB, bigA = 0, bigB = 0;
            int bigSize = -1;
            struct C { Mask a, b; };
            C comps[32];
            int nc = 0;
            while (rest) {
                Mask seed = rest & (~rest + 1);
                Mask comp = bd.flood(seed, HA, HB);
                rest &= ~comp;
                comps[nc++] = C{HA & comp, HB & comp};
                int sz = __builtin_popcountll(comp);
                if (sz > bigSize) { bigSize = sz; bigA = HA & comp; bigB = HB & comp; }
            }
            i64 q2 = q;
            bool s2 = s;
            for (int i = 0; i < nc; ++i) {
                if (comps[i].a == bigA && comps[i].b == bigB) continue;
                Val v;
                if (!value_of(comps[i].a, comps[i].b, depth, v)) return -1;
                q2 += v.num;
                s2 ^= v.star;
            }
            int r = win(bigA, bigB, q2, s2, depth, et);
            if (r < 0) return -1;
            tt.insert(k1, k2, q, s, r == 1, MV_NONE, nodes - n0);
            return r;
        }

        if (g_pass && s && et == 1) {
            // Cor 4.4 of COL_VALUES.md (PROVED): G <| 0 iff G + * <= 0. With G = H + q in
            // the mover's frame: the mover loses moving first in H + q + * iff the
            // opponent wins moving first in H + q. At an expected loss this turns the
            // enumeration of all mover moves into a search for one opponent move.
            int r = win(HB, HA, -q, false, depth, 0);
            if (r < 0) return -1;
            ++passed;
            tt.insert(k1, k2, q, s, r == 0, MV_NONE, nodes - n0);
            return r == 0 ? 1 : 0;
        }
        const int d = depth < 64 ? depth : 63;
        const int side = depth & 1;
        if (g_refute > 0 && et == 1) {
            // Lemma 4 of COL_VALUES.md (PROVED), in the mover's frame: for an opponent
            // move v, H <= H^{R,v} + * (v shared) and H <= H^{R,v} - 1 (v opponent-only).
            // So if the mover loses moving first in H^{R,v} + q + (s+1)* (resp.
            // H^{R,v} + q - 1 + s*), the mover loses here.
            int ov[64], no = 0;
            std::int64_t osc[64];
            for (Mask m = HB; m; m &= m - 1) {
                int v = __builtin_ctzll(m);
                Mask bit = Mask(1) << v;
                if (!(HA & bit) && vs.blue_dominated(v, HB, HA)) continue;
                std::int64_t score = std::int64_t(((HA & bit) ? 2 : 0) - __builtin_popcountll(bd.nb[v] & HB)) << 20;
                score += std::int64_t(std::min<std::uint32_t>(hist[side ^ 1][v] >> g_histShift, (1u << 19) - 1));
                ov[no] = v; osc[no] = score; ++no;
            }
            for (int k = 0; k < g_refute && k < no; ++k) {
                int bi = k;
                for (int j = k + 1; j < no; ++j) if (osc[j] > osc[bi]) bi = j;
                std::swap(ov[k], ov[bi]); std::swap(osc[k], osc[bi]);
                int v = ov[k];
                Mask bit = Mask(1) << v;
                int r = (HA & bit) ? win(HA & ~bit, HB & ~bd.closed[v], q, !s, depth + 1, 1)
                                   : win(HA, HB & ~bd.closed[v], q - ONE, s, depth + 1, 1);
                if (r < 0) return -1;
                if (r == 0) {
                    ++refuted;
                    tt.insert(k1, k2, q, s, false, MV_NONE, nodes - n0);
                    return 0;
                }
            }
        }
        if (g_quickRefute > 0) {
            // Same Lemma-4 argument as above, but the child is only evaluated statically.
            int tried = 0;
            for (Mask m = HB; m && tried < g_quickRefute; m &= m - 1) {
                int v = __builtin_ctzll(m);
                Mask bit = Mask(1) << v;
                ++tried;
                int r = (HA & bit) ? quick(HA & ~bit, HB & ~bd.closed[v], q, !s)
                                   : quick(HA, HB & ~bd.closed[v], q - ONE, s);
                if (r == 0) {
                    ++refuted;
                    tt.insert(k1, k2, q, s, false, MV_NONE, nodes - n0);
                    return 0;
                }
            }
        }
        int bestCell = -1;
        if (!g_useBest) bestCode = MV_NONE;
        if (bestCode < 0xF0) bestCell = from_code(bestCode, xf);
        int mv[64], nm = 0;
        std::int64_t sc[64];
        for (Mask m = HA; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            Mask bit = Mask(1) << v;
            if (!(HB & bit) && vs.blue_dominated(v, HA, HB)) continue;
            std::int64_t score = (std::int64_t(((HB & bit) ? 2 : 0) - __builtin_popcountll(bd.nb[v] & HA)) << 20);
            score += std::int64_t(std::min<std::uint32_t>(hist[side][v] >> g_histShift, (1u << 22) - 1));
            if (jitter) score += std::int64_t(((unsigned(v) * 2654435761u) ^ jitter) >> 12 & 0x7FFFF) << 1;
            if (v == bestCell) score += std::int64_t(1) << 40;
            else if (v == killer[d][0]) score += std::int64_t(1) << 30;
            else if (v == killer[d][1]) score += std::int64_t(1) << 29;
            mv[nm] = v; sc[nm] = score; ++nm;
        }
        for (int i = 1; i < nm; ++i) {
            int v = mv[i], j = i - 1;
            std::int64_t s2 = sc[i];
            while (j >= 0 && sc[j] < s2) { mv[j + 1] = mv[j]; sc[j + 1] = sc[j]; --j; }
            mv[j + 1] = v; sc[j + 1] = s2;
        }
        bool won = false;
        int winCode = MV_NONE;
        // Moves in the number / star first if the table says so.
        auto try_star = [&]() -> int {
            int r = win(HB, HA, -q, false, depth + 1, et == 1 ? 0 : 1);
            if (r < 0) return -1;
            if (r == 0) { won = true; winCode = MV_STAR; }
            return 0;
        };
        auto try_num = [&]() -> int {
            i64 ql;
            if (!left_option(q, ql)) return 0;
            int r = win(HB, HA, -ql, s, depth + 1, et == 1 ? 0 : 1);
            if (r < 0) return -1;
            if (r == 0) { won = true; winCode = MV_NUM; }
            return 0;
        };
        if (bestCode == MV_STAR && s) { if (try_star() < 0) return -1; }
        else if (bestCode == MV_NUM) { if (try_num() < 0) return -1; }
        if (g_etc && !won) {
            for (int i = 0; i < nm; ++i) {
                int v = mv[i];
                Mask bit = Mask(1) << v;
                if (quick(HB & ~bit, HA & ~bd.closed[v], -q, s) == 0) {
                    won = true;
                    winCode = to_code(v, xf);
                    ++etcHits;
                    break;
                }
            }
        }
        std::uint64_t nBefore = nodes;
        for (int i = 0; i < nm && !won; ++i) {
            int v = mv[i];
            Mask bit = Mask(1) << v;
            std::uint64_t nChild = nodes;
            int r = win(HB & ~bit, HA & ~bd.closed[v], -q, s, depth + 1, et == 1 ? 0 : 1);
            if (r < 0) return -1;
            if (r == 0) {
                if (i == 0) ++wonFirst; else { ++wonLater; wasteNodes += nChild - nBefore; }
                wonNodes += nodes - nBefore;
                won = true;
                winCode = to_code(v, xf);
                if (killer[d][0] != v) { killer[d][1] = killer[d][0]; killer[d][0] = v; }
                hist[side][v] += 1u << std::min(12, std::max(0, 20 - d));
                if (hist[side][v] > (1u << 28))
                    for (auto& h : hist[side]) h >>= 1;
            }
        }
        if (!won) { lostNodes += nodes - nBefore; ++lostCount; }
        if (!won && s && bestCode != MV_STAR) { if (try_star() < 0) return -1; }
        if (!won && bestCode != MV_NUM) { if (try_num() < 0) return -1; }
        tt.insert(k1, k2, q, s, won, winCode, nodes - n0);
        return won ? 1 : 0;
    }
};

static double g_deadline = 1e18;
static std::chrono::steady_clock::time_point g_start;
static double since_start() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - g_start).count();
}

struct RootResult {
    int win;  // 1 win, 0 loss, -1 aborted (time limit)
    std::uint64_t nodes;
};

static RootResult root_win(const Board& bd, Cache& vc, TT& tt, int smax, int threads, Mask A, Mask B, i64 q,
                           bool s, const std::string& tag) {
    std::vector<std::unique_ptr<Search>> ss;
    for (int t = 0; t < threads; ++t) {
        ss.emplace_back(new Search(bd, vc, tt, smax));
        ss.back()->jitter = t ? 0x9E3779B9u * unsigned(t) : 0;
    }
    Search& s0 = *ss[0];
    Search::Folded f = s0.fold(A, B, q, s);
    if (!(f.HA | f.HB)) return {(f.q > 0 || (f.q == 0 && f.s)) ? 1 : 0, 1};
    struct Child { Mask a, b; i64 q; bool s; };
    std::vector<Child> kids;
    std::vector<std::pair<Mask, Mask>> seenKeys;
    for (Mask m = f.HA; m; m &= m - 1) {
        int v = __builtin_ctzll(m);
        Mask bit = Mask(1) << v;
        if (!(f.HB & bit) && s0.vs.blue_dominated(v, f.HA, f.HB)) continue;
        Child c{f.HB & ~bit, f.HA & ~bd.closed[v], -f.q, f.s};
        // Children isomorphic under translation/reflection are the same game.
        bool dup = false;
        if (c.a | c.b) {
            Mask k1, k2;
            Xf xf;
            s0.canon_geo(c.a, c.b, k1, k2, xf);
            for (auto& p : seenKeys) if (p.first == k1 && p.second == k2) { dup = true; break; }
            seenKeys.push_back({k1, k2});
        }
        if (!dup) kids.push_back(c);
    }
    if (f.s) kids.push_back({f.HB, f.HA, -f.q, false});
    i64 ql;
    if (left_option(f.q, ql)) kids.push_back({f.HB, f.HA, -ql, f.s});
    const std::size_t nk = kids.size();
    std::atomic<bool> abort{false}, timeout{false};
    std::unique_ptr<std::atomic<bool>[]> kidDone(new std::atomic<bool>[nk]);
    std::unique_ptr<std::atomic<int>[]> kidWorkers(new std::atomic<int>[nk]);
    for (std::size_t i = 0; i < nk; ++i) { kidDone[i] = false; kidWorkers[i] = 0; }
    std::atomic<std::size_t> next{0}, ndone{0};
    std::atomic<bool> found{false};
    std::mutex mu;
    std::vector<std::thread> pool;
    for (int t = 0; t < threads; ++t) {
        pool.emplace_back([&, t] {
            Search& S = *ss[t];
            S.abortG = &abort;
            for (;;) {
                if (abort.load()) break;
                std::size_t i = next.fetch_add(1);
                if (i >= nk) {
                    // help: pick the unfinished child with the fewest workers
                    int best = -1, bw = 1 << 30;
                    for (std::size_t j = 0; j < nk; ++j)
                        if (!kidDone[j].load() && kidWorkers[j].load() < bw) { bw = kidWorkers[j].load(); best = int(j); }
                    if (best < 0) break;
                    i = std::size_t(best);
                    S.jitter = 0x85EBCA6Bu * unsigned(t + 1) + unsigned(S.nodes);
                }
                if (kidDone[i].load()) continue;
                kidWorkers[i].fetch_add(1);
                S.abortL = &kidDone[i];
                int r = S.win(kids[i].a, kids[i].b, kids[i].q, kids[i].s, 1, 0);
                S.abortL = nullptr;
                kidWorkers[i].fetch_sub(1);
                if (r < 0) continue;  // aborted: child finished elsewhere, or global abort
                bool expected = false;
                if (kidDone[i].compare_exchange_strong(expected, true)) {
                    ndone.fetch_add(1);
                    if (r == 0) { found = true; abort = true; break; }
                }
            }
        });
    }
    // monitor
    double lastReport = since_start();
    for (;;) {
        bool alive = false;
        if (ndone.load() >= nk || abort.load()) {
            alive = false;
        } else alive = true;
        if (!alive) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        double now = since_start();
        if (now > g_deadline) { timeout = true; abort = true; break; }
        if (now - lastReport > 120) {
            lastReport = now;
            std::uint64_t nodes = 0;
            for (auto& x : ss) nodes += x->nodes;
            std::fprintf(stderr, "    [%s] %.0fs kids %zu/%zu nodes %" PRIu64 " tt %" PRIu64 " vc %" PRIu64 "\n",
                         tag.c_str(), now, ndone.load(), nk, nodes, tt.used.load(), vc.used.load());
            std::fflush(stderr);
        }
    }
    for (auto& th : pool) th.join();
    std::uint64_t nodes = 0;
    for (auto& x : ss) nodes += x->nodes;
    if (g_stats) {
        std::uint64_t wf = 0, wl = 0, wn = 0, wsn = 0, ln = 0, lc = 0, ps = 0;
        for (auto& x : ss) { ps += x->passed; wf += x->wonFirst; wl += x->wonLater; wn += x->wonNodes; wsn += x->wasteNodes; ln += x->lostNodes; lc += x->lostCount; }
        std::fprintf(stderr, "    passed %" PRIu64 "\n", ps);
        std::fprintf(stderr, "    stats[%s]: won-first %" PRIu64 " won-later %" PRIu64 " waste-nodes %" PRIu64 " / won-subtree %" PRIu64
                     "; lost %" PRIu64 " nodes-under-lost %" PRIu64 "\n", tag.c_str(), wf, wl, wsn, wn, lc, ln);
    }
    if (found.load()) return {1, nodes};
    if (timeout.load() || ndone.load() < nk) return {-1, nodes};
    return {0, nodes};
}

// ---------------------------------------------------------- value file I/O
static std::uint64_t save_values(Cache& vc, const std::string& path, int minw) {
    FILE* f = std::fopen(path.c_str(), "wb");
    if (!f) die("cannot write " + path);
    std::uint64_t n = 0;
    for (std::size_t i = 0; i < vc.nb; ++i)
        for (int j = 0; j < 4; ++j) {
            const Entry& e = vc.b[i].e[j];
            if ((e.k1 | e.k2) == 0) continue;
            if (int(e.v & 127) < minw) continue;
            Mask rec[3] = {e.k1, e.k2, Mask(e.v)};
            std::fwrite(rec, sizeof(rec), 1, f);
            ++n;
        }
    std::fclose(f);
    return n;
}
static std::uint64_t load_values(Cache& vc, const std::string& path) {
    FILE* f = std::fopen(path.c_str(), "rb");
    if (!f) return 0;
    std::uint64_t n = 0;
    Mask rec[3];
    while (std::fread(rec, sizeof(rec), 1, f) == 1) {
        i64 word = i64(rec[2]);
        vc.insert(rec[0], rec[1], word >> 7, int(word & 127));
        ++n;
    }
    std::fclose(f);
    return n;
}

int main(int argc, char** argv) {
    int vlog = 22, tlog = 22, smax = 14, threads = 1;
    double limit = 1e18;
    std::vector<std::string> loads;
    std::string savePath;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-t" && i + 1 < argc) vlog = std::atoi(argv[++i]);
        else if (a == "-T" && i + 1 < argc) tlog = std::atoi(argv[++i]);
        else if (a == "-S" && i + 1 < argc) smax = std::atoi(argv[++i]);
        else if (a == "-j" && i + 1 < argc) threads = std::atoi(argv[++i]);
        else if (a == "-L" && i + 1 < argc) limit = std::atof(argv[++i]);
        else if (a == "-V" && i + 1 < argc) loads.push_back(argv[++i]);
        else if (a == "-W" && i + 1 < argc) savePath = argv[++i];
        else if (a == "-H" && i + 1 < argc) g_histShift = std::atoi(argv[++i]);
        else if (a == "-B" && i + 1 < argc) g_useBest = std::atoi(argv[++i]);
        else if (a == "-R" && i + 1 < argc) g_refute = std::atoi(argv[++i]);
        else if (a == "-Q" && i + 1 < argc) g_quickRefute = std::atoi(argv[++i]);
        else if (a == "-E" && i + 1 < argc) g_etc = std::atoi(argv[++i]);
        else if (a == "-X" && i + 1 < argc) g_stats = std::atoi(argv[++i]);
        else if (a == "-P" && i + 1 < argc) g_pass = std::atoi(argv[++i]);
        else die("unknown argument " + a);
    }
    g_start = std::chrono::steady_clock::now();
    g_deadline = limit;
    Cache vc(vlog);
    TT tt(tlog);
    for (auto& p : loads) {
        std::uint64_t n = load_values(vc, p);
        std::fprintf(stderr, "loaded %" PRIu64 " component values from %s\n", n, p.c_str());
    }
    std::string line;
    int rc = 0;
    while (std::getline(std::cin, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream is(line);
        std::string cmd;
        int h, w;
        unsigned long long A, B;
        is >> cmd >> h >> w >> A >> B;
        Board bd(h, w);
        if ((A | B) & ~bd.full) die("mask outside board");
        auto t0 = std::chrono::steady_clock::now();
        auto elapsed = [&] {
            return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        };
        auto cls_of = [](int b, int w) {
            if (b < 0 || w < 0) return '?';
            return b ? (w ? 'N' : 'L') : (w ? 'R' : 'P');
        };
        if (cmd == "outcome") {
            std::string qs, label;
            int st;
            is >> qs >> st >> label;
            i64 q = parse_dyadic(qs);
            RootResult b = root_win(bd, vc, tt, smax, threads, A, B, -q, st, label + " B " + qs);
            RootResult wr = b.win < 0 ? RootResult{-1, 0}
                                      : root_win(bd, vc, tt, smax, threads, B, A, q, st, label + " W " + qs);
            char c = cls_of(b.win, wr.win);
            std::printf("outcome\t%s\tG%s-(%s)\t%c\tBlue-first %s\tWhite-first %s\tnodes=%" PRIu64 "+%" PRIu64
                        "\t%.2fs\n",
                        label.c_str(), st ? "+*" : "", qs.c_str(), c, b.win < 0 ? "?" : (b.win ? "WINS" : "LOSES"),
                        wr.win < 0 ? "?" : (wr.win ? "WINS" : "LOSES"), b.nodes, wr.nodes, elapsed());
            std::fflush(stdout);
            if (c == '?') { rc = 2; break; }
            continue;
        }
        if (cmd == "first") {
            // first h w A B q star label blue|white : outcome of G + star - q with the given player first
            std::string qs, label, who;
            int st;
            is >> qs >> st >> label >> who;
            i64 q = parse_dyadic(qs);
            bool blue = who == "blue";
            if (!blue && who != "white") die("first: player must be blue or white");
            RootResult r = blue ? root_win(bd, vc, tt, smax, threads, A, B, -q, st, label + " B " + qs)
                                : root_win(bd, vc, tt, smax, threads, B, A, q, st, label + " W " + qs);
            std::printf("first\t%s\tG%s-(%s)\t%s-first\t%s\tnodes=%" PRIu64 "\t%.2fs\n", label.c_str(),
                        st ? "+*" : "", qs.c_str(), who.c_str(), r.win < 0 ? "INCONCLUSIVE" : (r.win ? "WINS" : "LOSES"),
                        r.nodes, elapsed());
            std::fflush(stdout);
            if (r.win < 0) { rc = 2; break; }
            continue;
        }
        if (cmd != "value") die("unknown command " + cmd);
        std::string label, guess;
        is >> label;
        bool haveGuess = bool(is >> guess);
        Search probe(bd, vc, tt, smax);
        i64 lo = -i64(probe.alpha_upper(B)) * ONE - ONE, hi = i64(probe.alpha_upper(A)) * ONE + ONE;
        i64 t = haveGuess ? parse_dyadic(guess) : simplest(true, lo, true, true, hi, true);
        std::string trail;
        bool inconclusive = false;
        for (int step = 0; step < 64; ++step) {
            RootResult b = root_win(bd, vc, tt, smax, threads, A, B, -t, false, label + " B " + numstr(t));
            RootResult wr = b.win < 0 ? RootResult{-1, 0}
                                      : root_win(bd, vc, tt, smax, threads, B, A, t, false, label + " W " + numstr(t));
            char cls = cls_of(b.win, wr.win);
            trail += " " + numstr(t) + ":" + cls;
            std::fprintf(stderr, "  %s t=%s %c nodes=%" PRIu64 "+%" PRIu64 " %.1fs\n", label.c_str(),
                         numstr(t).c_str(), cls, b.nodes, wr.nodes, elapsed());
            std::fflush(stderr);
            if (cls == '?') {
                std::printf("value\t%s\tINCONCLUSIVE(in (%s,%s))\t%.2fs\t[%s ]\n", label.c_str(), numstr(lo).c_str(),
                            numstr(hi).c_str(), elapsed(), trail.c_str());
                inconclusive = true;
                break;
            }
            if (cls == 'P') {
                Mask k1, k2;
                int sign = probe.vs.canon(A, B, k1, k2);
                i64 sv = sign > 0 ? t : -t;
                vc.insert(k1, k2, sv * 2, __builtin_popcountll(A | B));
                std::printf("value\t%s\t%s\t%.2fs\t[%s ]\n", label.c_str(), numstr(t).c_str(), elapsed(), trail.c_str());
                break;
            }
            if (cls == 'N') {
                RootResult b2 = root_win(bd, vc, tt, smax, threads, A, B, -t, true, label + " B* " + numstr(t));
                RootResult w2 = b2.win < 0 ? RootResult{-1, 0}
                                           : root_win(bd, vc, tt, smax, threads, B, A, t, true, label + " W* " + numstr(t));
                if (b2.win < 0 || w2.win < 0) {
                    std::printf("value\t%s\tINCONCLUSIVE(%s or %s+*)\t%.2fs\t[%s ]\n", label.c_str(),
                                numstr(t).c_str(), numstr(t).c_str(), elapsed(), trail.c_str());
                    inconclusive = true;
                    break;
                }
                bool conf = !b2.win && !w2.win;
                if (conf) {
                    Mask k1, k2;
                    int sign = probe.vs.canon(A, B, k1, k2);
                    i64 sv = sign > 0 ? t : -t;
                    vc.insert(k1, k2, sv * 2 + 1, __builtin_popcountll(A | B));
                }
                trail += std::string(" ") + numstr(t) + "+*:" + (conf ? "P" : "?");
                std::printf("value\t%s\t%s\t%.2fs\t[%s ]\n", label.c_str(),
                            conf ? (numstr(t) + "+*").c_str() : ("CONFUSED-WITH-" + numstr(t) + "-NOT-STAR").c_str(),
                            elapsed(), trail.c_str());
                break;
            }
            if (cls == 'L') lo = t; else hi = t;
            if (lo >= hi) die("bisection interval collapsed");
            t = simplest(true, lo, true, true, hi, true);
        }
        std::fflush(stdout);
        if (inconclusive) { rc = 2; break; }
    }
    if (!savePath.empty()) {
        std::uint64_t n = save_values(vc, savePath, 12);
        std::fprintf(stderr, "saved %" PRIu64 " component values to %s\n", n, savePath.c_str());
    }
    return rc;
}
