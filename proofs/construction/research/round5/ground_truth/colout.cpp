// colout: outcome search for  G + q (+*)  on Col permission positions, with
// exact folding of small components, plus a bisection driver for exact values.
//
// Discovery tool (EVIDENCE level). A node is (A, B, q, s) in the MOVER's frame:
// A = cells legal for the player to move, B = cells legal for the opponent,
// q = dyadic number from the mover's point of view, s = star present.
// At every node the board is split into interaction components; every
// component with at most S live cells is replaced by its exact value (from
// the colcore value engine), which is folded into (q, s). This is exact:
// equal games may be substituted in a disjoint sum. Remaining ("hard")
// components are searched; moves in the folded number/star are included:
//   mover takes the star:            (B, A, -q, 0)
//   mover moves in the number q:     (B, A, -q_L, s)   (q_L = canonical Left option)
// Cutoffs: H <= alpha(A_H) and H >= -alpha(B_H) (alpha = independence number,
// bounded above by |S| - greedy matching since grid graphs are bipartite).
//
// Value driver: exact value of G by comparisons with dyadic t:
//   Blue-first outcome of G - t and White-first outcome of G - t.
//   P => G = t;  L => G > t;  R => G < t;  N => G is confused with t, and then
//   G - t + * is tested directly: if it is P, then G = t + * (no Col theorem).
//
// Usage:
//   colout [-t LOG2] [-T LOG2] [-S smax] [-j threads] < queries
// Query lines:
//   value h w A B label [guess]          exact value by bisection
//   le h w A B q star label              is G + star <= q ?  (Blue-first loss of G + star - q)
//   outcome h w A B q star label         both outcomes of G + star - q
// q is written like -5/8, star is 0 or 1.
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

// Canonical Left option of the number q (fixed point); returns false if none.
static inline bool left_option(i64 q, i64& ql) {
    if (q & (ONE - 1)) {
        i64 low = q & -q;  // lowest set bit = 2^-k in fixed point
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

// Transposition table keyed by (hard position, star). Outcomes are monotone
// in the mover's number q: a win at q implies a win at every q' > q, and a
// loss at q implies a loss at every q' < q (adding a positive number can only
// help the mover). Each entry keeps the smallest known winning q and the
// largest known losing q.
static const i64 QINF = i64(1) << 62;
struct TTEntry {
    Mask k1, k2;
    i64 winAt, loseAt;
    std::uint64_t info;  // bit1 star, bit2 valid, bits 8.. weight
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
    // returns 1 win, 0 loss, -1 unknown
    int find(Mask k1, Mask k2, i64 q, bool s) {
        TTBucket& bk = b[hash(k1, k2, s) & mask];
        spin_lock(bk.lock);
        int res = -1;
        for (int i = 0; i < 4; ++i) {
            TTEntry& e = bk.e[i];
            if ((e.info & 4) && e.k1 == k1 && e.k2 == k2 && bool(e.info & 2) == s) {
                if (q >= e.winAt) res = 1;
                else if (q <= e.loseAt) res = 0;
                break;
            }
        }
        spin_unlock(bk.lock);
        return res;
    }
    void insert(Mask k1, Mask k2, i64 q, bool s, bool res, std::uint64_t weight) {
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
                if ((e.info >> 8) < minw) { minw = e.info >> 8; slot = i; }
            }
            TTEntry& e = bk.e[slot];
            if (!(e.info & 4)) used.fetch_add(1, std::memory_order_relaxed);
            e.k1 = k1; e.k2 = k2; e.winAt = QINF; e.loseAt = -QINF;
            e.info = (s ? 2 : 0) | 4;
        }
        TTEntry& e = bk.e[slot];
        if (res) { if (q < e.winAt) e.winAt = q; }
        else { if (q > e.loseAt) e.loseAt = q; }
        std::uint64_t wt = std::min<std::uint64_t>((e.info >> 8) + weight, (1ULL << 55));
        e.info = (e.info & 0xff) | (wt << 8);
        spin_unlock(bk.lock);
    }
};

struct Search {
    const Board& bd;
    Solver vs;  // exact value engine (shared value cache)
    TT& tt;
    int smax;
    std::atomic<bool>* abort = nullptr;
    std::uint64_t nodes = 0, valued = 0;
    int killer[64][2];

    Search(const Board& b, Cache& vc, TT& t, int s) : bd(b), vs(b, vc), tt(t), smax(s) {
        for (auto& k : killer) k[0] = k[1] = -1;
    }

    // Upper bound on the independence number of the grid subgraph on S.
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

    // Geometric canonical key (4 rectangle symmetries, no colour swap).
    inline void canon_geo(Mask A, Mask B, Mask& k1, Mask& k2) const {
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
                if (pa < best1 || (pa == best1 && pb < best2)) { best1 = pa; best2 = pb; }
            }
        k1 = best1 | (Mask(hc) << 60);
        k2 = best2 | (Mask(wc) << 60);
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
                // A large component whose exact value is already cached is folded too.
                Mask k1, k2;
                int sign = vs.canon(ca, cb, k1, k2);
                i64 packed;
                if (vs.memo.find(k1, k2, packed)) {
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

    // Exact value (mover as Left) of a single hard component, by bisection
    // with outcome searches; cached in the value cache. Returns false if aborted.
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

    // 1 = mover wins, 0 = mover loses, -1 = aborted.
    int win(Mask A, Mask B, i64 q, bool s, int depth) {
        if (abort && abort->load(std::memory_order_relaxed)) return -1;
        ++nodes;
        Folded f = fold(A, B, q, s);
        q = f.q; s = f.s;
        Mask HA = f.HA, HB = f.HB;
        if (!(HA | HB)) return (q > 0 || (q == 0 && s)) ? 1 : 0;
        int ubA = alpha_upper(HA), ubB = alpha_upper(HB);
        if (q - i64(ubB) * ONE > 0) return 1;
        if (q + i64(ubA) * ONE < 0) return 0;
        Mask k1, k2;
        if (f.nhard == 1) canon_geo(HA, HB, k1, k2);
        else { k1 = HA | (Mask(15) << 60); k2 = HB | (Mask(15) << 60); }
        int cached = tt.find(k1, k2, q, s);
        if (cached >= 0) return cached;
        std::uint64_t n0 = nodes;
        if (f.nhard >= 2) {
            // Value every hard component except the largest separately and fold.
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
            int r = win(bigA, bigB, q2, s2, depth + 1);
            if (r < 0) return -1;
            tt.insert(k1, k2, q, s, r == 1, nodes - n0);
            return r;
        }

        // Candidate moves in hard components with a simple ordering.
        int mv[64], sc[64], nm = 0;
        for (Mask m = HA; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            Mask bit = Mask(1) << v;
            if (!(HB & bit) && vs.blue_dominated(v, HA, HB)) continue;
            int score = ((HB & bit) ? 2 : 0) - __builtin_popcountll(bd.nb[v] & HA);
            int d = depth < 64 ? depth : 63;
            if (v == killer[d][0]) score += 100;
            else if (v == killer[d][1]) score += 50;
            mv[nm] = v; sc[nm] = score; ++nm;
        }
        for (int i = 1; i < nm; ++i) {  // insertion sort, descending score
            int v = mv[i], s2 = sc[i], j = i - 1;
            while (j >= 0 && sc[j] < s2) { mv[j + 1] = mv[j]; sc[j + 1] = sc[j]; --j; }
            mv[j + 1] = v; sc[j + 1] = s2;
        }
        bool won = false;
        for (int i = 0; i < nm && !won; ++i) {
            int v = mv[i];
            Mask bit = Mask(1) << v;
            int r = win(HB & ~bit, HA & ~bd.closed[v], -q, s, depth + 1);
            if (r < 0) return -1;
            if (r == 0) {
                won = true;
                int d = depth < 64 ? depth : 63;
                if (killer[d][0] != v) { killer[d][1] = killer[d][0]; killer[d][0] = v; }
            }
        }
        if (!won && s) {
            int r = win(HB, HA, -q, false, depth + 1);
            if (r < 0) return -1;
            if (r == 0) won = true;
        }
        i64 ql;
        if (!won && left_option(q, ql)) {
            int r = win(HB, HA, -ql, s, depth + 1);
            if (r < 0) return -1;
            if (r == 0) won = true;
        }
        tt.insert(k1, k2, q, s, won, nodes - n0);
        return won ? 1 : 0;
    }
};

// Root search with parallel evaluation of the root moves.
struct RootResult {
    bool win;
    std::uint64_t nodes;
};

static RootResult root_win(const Board& bd, Cache& vc, TT& tt, int smax, int threads, Mask A, Mask B, i64 q,
                           bool s) {
    std::vector<std::unique_ptr<Search>> ss;
    for (int t = 0; t < threads; ++t) ss.emplace_back(new Search(bd, vc, tt, smax));
    Search& s0 = *ss[0];
    Search::Folded f = s0.fold(A, B, q, s);
    if (!(f.HA | f.HB)) return {(f.q > 0 || (f.q == 0 && f.s)), 1};
    // children of the root: (childA, childB, childq, childs)
    struct Child { Mask a, b; i64 q; bool s; };
    std::vector<Child> kids;
    for (Mask m = f.HA; m; m &= m - 1) {
        int v = __builtin_ctzll(m);
        Mask bit = Mask(1) << v;
        if (!(f.HB & bit) && s0.vs.blue_dominated(v, f.HA, f.HB)) continue;
        kids.push_back({f.HB & ~bit, f.HA & ~bd.closed[v], -f.q, f.s});
    }
    if (f.s) kids.push_back({f.HB, f.HA, -f.q, false});
    i64 ql;
    if (left_option(f.q, ql)) kids.push_back({f.HB, f.HA, -ql, f.s});
    std::atomic<bool> abort{false};
    std::atomic<std::size_t> next{0};
    std::atomic<bool> found{false};
    std::vector<std::thread> pool;
    for (int t = 0; t < threads; ++t) {
        ss[t]->abort = &abort;
        pool.emplace_back([&, t] {
            for (;;) {
                std::size_t i = next.fetch_add(1);
                if (i >= kids.size() || abort.load()) break;
                int r = ss[t]->win(kids[i].a, kids[i].b, kids[i].q, kids[i].s, 1);
                if (r == 0) { found = true; abort = true; break; }
            }
        });
    }
    for (auto& th : pool) th.join();
    std::uint64_t nodes = 0;
    for (auto& x : ss) nodes += x->nodes;
    return {found.load(), nodes};
}

static std::string dstr(i64 q) { return numstr(q); }

int main(int argc, char** argv) {
    int vlog = 22, tlog = 22, smax = 16, threads = 1;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-t" && i + 1 < argc) vlog = std::atoi(argv[++i]);
        else if (a == "-T" && i + 1 < argc) tlog = std::atoi(argv[++i]);
        else if (a == "-S" && i + 1 < argc) smax = std::atoi(argv[++i]);
        else if (a == "-j" && i + 1 < argc) threads = std::atoi(argv[++i]);
        else die("unknown argument " + a);
    }
    Cache vc(vlog);
    TT tt(tlog);
    std::string line;
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
        if (cmd == "le" || cmd == "outcome") {
            std::string qs, label;
            int st;
            is >> qs >> st;
            std::getline(is, label);
            i64 q = parse_dyadic(qs);
            // G + st* - q : Blue first  -> mover Blue: (A, B, -q, st)
            RootResult b = root_win(bd, vc, tt, smax, threads, A, B, -q, st);
            std::printf("%s\t%s: G%s-(%s) Blue-first %s\tnodes=%" PRIu64 "\t%.2fs\n", cmd.c_str(), label.c_str(),
                        st ? "+*" : "", qs.c_str(), b.win ? "WINS" : "LOSES", b.nodes, elapsed());
            if (cmd == "outcome") {
                RootResult wr = root_win(bd, vc, tt, smax, threads, B, A, q, st);
                std::printf("outcome\t%s: G%s-(%s) White-first %s\tnodes=%" PRIu64 "\t%.2fs\t=> %s\n",
                            label.c_str(), st ? "+*" : "", qs.c_str(), wr.win ? "WINS" : "LOSES", wr.nodes,
                            elapsed(), b.win ? (wr.win ? "N" : "L") : (wr.win ? "R" : "P"));
            }
            std::fflush(stdout);
            continue;
        }
        if (cmd != "value") die("unknown command " + cmd);
        std::string label, guess;
        is >> label;
        bool haveGuess = bool(is >> guess);
        Search probe(bd, vc, tt, smax);
        // x lies in [-alpha(B), alpha(A)].
        i64 lo = -i64(probe.alpha_upper(B)) * ONE - ONE, hi = i64(probe.alpha_upper(A)) * ONE + ONE;
        i64 t = haveGuess ? parse_dyadic(guess) : simplest(true, lo, true, true, hi, true);
        std::string trail;
        for (int step = 0; step < 64; ++step) {
            RootResult b = root_win(bd, vc, tt, smax, threads, A, B, -t, false);
            RootResult wr = root_win(bd, vc, tt, smax, threads, B, A, t, false);
            char cls = b.win ? (wr.win ? 'N' : 'L') : (wr.win ? 'R' : 'P');
            trail += " " + dstr(t) + ":" + cls;
            std::fprintf(stderr, "  %s t=%s %c nodes=%" PRIu64 "+%" PRIu64 " %.1fs\n", label.c_str(), dstr(t).c_str(),
                         cls, b.nodes, wr.nodes, elapsed());
            if (cls == 'P') {
                Mask k1, k2;
                int sign = probe.vs.canon(A, B, k1, k2);
                i64 sv = sign > 0 ? t : -t;
                vc.insert(k1, k2, sv * 2, __builtin_popcountll(A | B));
                std::printf("value\t%s\t%s\t%.2fs\t[%s ]\n", label.c_str(), dstr(t).c_str(), elapsed(), trail.c_str());
                break;
            }
            if (cls == 'N') {
                RootResult b2 = root_win(bd, vc, tt, smax, threads, A, B, -t, true);
                RootResult w2 = root_win(bd, vc, tt, smax, threads, B, A, t, true);
                bool conf = !b2.win && !w2.win;
                if (conf) {
                    Mask k1, k2;
                    int sign = probe.vs.canon(A, B, k1, k2);
                    i64 sv = sign > 0 ? t : -t;
                    vc.insert(k1, k2, sv * 2 + 1, __builtin_popcountll(A | B));
                }
                trail += std::string(" ") + dstr(t) + "+*:" + (conf ? "P" : "?");
                std::printf("value\t%s\t%s\t%.2fs\t[%s ]\n", label.c_str(),
                            conf ? (dstr(t) + "+*").c_str() : ("CONFUSED-WITH-" + dstr(t) + "-NOT-STAR").c_str(),
                            elapsed(), trail.c_str());
                break;
            }
            if (cls == 'L') lo = t; else hi = t;
            if (lo >= hi) die("bisection interval collapsed");
            t = simplest(true, lo, true, true, hi, true);
        }
        std::fflush(stdout);
    }
    return 0;
}
