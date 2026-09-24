// hy2: hybrid expansion + comparison prover for one Blue-to-move position on
// an H x W board (discovery tool; every certificate it writes is rechecked by
// proofs/5x9/verify.py, which trusts nothing here).
//
// Differences from hyboard: the position is given as masks, one Blue move can
// be proved on its own (so a driver can run the Blue moves of one checkpoint
// as separate jobs and merge the results), vertical blocks up to width 6, and
// iterative deepening over White replies (all replies at depth d before any at
// depth d + 1).
//
// usage:
//   hy2 scan   H W A B DEPTH              one status line per Blue move
//   hy2 answer H W A B V DEPTH out.json   prove P^{Blue V, White u} <= 0 for some u
//   hy2 prove  H W A B DEPTH out.json     prove P <= 0
// environment: HYW max block width (5), HYCAP5 (25), HYCAP6 (28), HYLOG memo
// log2 (25), HYK replies tried at each deeper level (6), HYT seconds (1e9),
// HYS5 / HYS6 closure-score thresholds for trying width 5 / 6 (1.0 / 0.5),
// HYLOCAL largest component valued exactly (22), HYVERBOSE.
#include <array>
#include <chrono>
#include <climits>
#include <set>

#include "hybrid.hpp"
using namespace hy;

static int H, W, MAXW = 5, LOCALMAX = 22, KTRY = 6, CAP5 = 25, CAP6 = 28, CURW = 4;
static double S5 = 1.0, S6 = 0.5;
static bool VERBOSE = false;
static Store* ST;
static const i64 INF = LLONG_MAX / 4;
static double now() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
static double T0, DEADLINE = 1e18;
static bool timed_out() { return now() > DEADLINE; }

struct Block {
    int k, wd;
    u64 A, B;
    Val v;
};
struct Closure {
    bool ok = false, have = false;
    Val total;
    u64 retired = 0;
    std::vector<Block> blocks;
};

static inline u64 colbit(int r, int c) { return u64(1) << (r * W + c); }
static inline int capOf(int wd) { return wd <= 4 ? 64 : wd == 5 ? CAP5 : CAP6; }

// Minimal block-value sum over partitions of the columns into blocks of width
// <= CURW, each seam retiring White cells so that no White-White edge crosses.
Closure closeDP(u64 A, u64 B, i64 threshold = INF) {
    const int S = 1 << H;
    std::vector<i64> v0((W + 1) * (CURW + 1), INF), lbsuf(W + 1, INF);
    if (threshold < INF) {
        for (int k = 0; k < W; ++k)
            for (int wd = 1; wd <= CURW && k + wd <= W; ++wd) {
                u64 block = 0;
                for (int r = 0; r < H; ++r)
                    for (int c = k; c < k + wd; ++c) block |= colbit(r, c);
                if (__builtin_popcountll((A | B) & block) > capOf(wd)) continue;
                v0[k * (CURW + 1) + wd] = ST->value(H, W, A & block, B & block).num;
            }
        lbsuf[W] = 0;
        for (int k = W - 1; k >= 0; --k)
            for (int wd = 1; wd <= CURW && k + wd <= W; ++wd) {
                i64 a = v0[k * (CURW + 1) + wd];
                if (a < INF && lbsuf[k + wd] < INF) lbsuf[k] = std::min(lbsuf[k], a + lbsuf[k + wd]);
            }
        if (lbsuf[0] > threshold) return Closure{};
    }
    std::vector<std::array<i64, 2>> best((W + 1) * S, {INF, INF});
    struct Step {
        int prevK = 0, prevS = 0, prevStar = 0, width = 0, leftRet = 0;
        Val val;
    };
    std::vector<std::array<Step, 2>> from((W + 1) * S);
    best[0][0] = 0;
    for (int k = 0; k < W; ++k)
        for (int s = 0; s < S; ++s)
            for (int st = 0; st < 2; ++st) {
                i64 cur = best[k * S + s][st];
                if (cur >= INF) continue;
                for (int wd = 1; wd <= CURW && k + wd <= W; ++wd) {
                    u64 block = 0;
                    for (int r = 0; r < H; ++r)
                        for (int c = k; c < k + wd; ++c) block |= colbit(r, c);
                    u64 Bb = B & block;
                    for (int r = 0; r < H; ++r)
                        if (s >> r & 1) Bb &= ~colbit(r, k);
                    u64 Ab = A & block;
                    if (__builtin_popcountll(Ab | Bb) > capOf(wd)) continue;
                    if (threshold < INF) {
                        i64 lb0 = v0[k * (CURW + 1) + wd];
                        if (lb0 >= INF || lbsuf[k + wd] >= INF || cur + lb0 + lbsuf[k + wd] > threshold) continue;
                    }
                    int last = k + wd - 1, choice = 0;
                    if (k + wd < W)
                        for (int r = 0; r < H; ++r)
                            if ((Bb & colbit(r, last)) && (B & colbit(r, last + 1))) choice |= 1 << r;
                    for (int L = choice;; L = (L - 1) & choice) {
                        u64 Bl = Bb;
                        for (int r = 0; r < H; ++r)
                            if (L >> r & 1) Bl &= ~colbit(r, last);
                        Val v = ST->value(H, W, Ab, Bl);
                        int ns = (k + wd < W) ? (choice & ~L) : 0;
                        if (threshold < INF && cur + v.num + lbsuf[k + wd] > threshold) {
                            if (L == 0) break;
                            continue;
                        }
                        int nst = st ^ (v.star ? 1 : 0);
                        i64 nv = cur + v.num;
                        auto& slot = best[(k + wd) * S + ns][nst];
                        if (nv < slot) {
                            slot = nv;
                            from[(k + wd) * S + ns][nst] = Step{k, s, st, wd, L, v};
                        }
                        if (L == 0) break;
                    }
                }
            }
    Closure res;
    i64 b0 = best[W * S][0], b1 = best[W * S][1];
    int pick = -1;
    if (b0 <= 0)
        pick = 0;
    else if (b1 < 0)
        pick = 1;
    res.ok = pick >= 0;
    if (pick < 0) {
        if (b0 < INF && (b1 >= INF || b0 <= b1))
            pick = 0;
        else if (b1 < INF)
            pick = 1;
        else
            return res;
    }
    res.have = true;
    res.total = Val{best[W * S][pick], pick == 1};
    int k = W, s = 0, st = pick;
    while (k > 0) {
        const Step stp = from[k * S + s][st];
        int bk = stp.prevK, wd = stp.width;
        u64 block = 0;
        for (int r = 0; r < H; ++r)
            for (int c = bk; c < bk + wd; ++c) block |= colbit(r, c);
        u64 Bb = B & block;
        for (int r = 0; r < H; ++r)
            if (stp.prevS >> r & 1) {
                Bb &= ~colbit(r, bk);
                res.retired |= colbit(r, bk) & B;
            }
        for (int r = 0; r < H; ++r)
            if (stp.leftRet >> r & 1) {
                Bb &= ~colbit(r, bk + wd - 1);
                res.retired |= colbit(r, bk + wd - 1) & B;
            }
        res.blocks.push_back(Block{bk, wd, A & block, Bb, stp.val});
        k = stp.prevK;
        s = stp.prevS;
        st = stp.prevStar;
    }
    return res;
}

static double score_of(const Closure& c) {
    if (!c.have) return 1e18;
    return double(c.total.num) / double(ONE) + (c.total.star ? 1e-6 : 0);
}

Ref make_closure_node(u64 A, u64 B, const Closure& cl) {
    std::vector<Store::FrameEdge> fes;
    for (const Block& b : cl.blocks) {
        if (!(b.A | b.B)) continue;
        Ref r = ST->intern(H, W, b.A, b.B, -b.v.num, b.v.star);
        fes.push_back(Store::FrameEdge{0, 0, r.id, b.A, b.B});
    }
    return ST->add_node_frame(H, W, A, B, 0, false, COMPARE, cl.retired, fes);
}

static inline int refl_cell(int g, int v) {
    int r = v / W, c = v % W;
    if (g & 1) r = H - 1 - r;
    if (g & 2) c = W - 1 - c;
    return r * W + c;
}
static inline u64 refl_mask(int g, u64 m) {
    u64 out = 0;
    for (; m; m &= m - 1) out |= u64(1) << refl_cell(g, __builtin_ctzll(m));
    return out;
}

struct PKey {
    u64 A, B;
    bool operator<(const PKey& o) const { return A < o.A || (A == o.A && B < o.B); }
};
static std::map<PKey, int> failed;          // position -> largest depth that failed
static std::map<PKey, Ref> proved;          // position -> node
static std::map<PKey, double> scoreMemo;    // position -> best closure score seen
static long long nodes_tried = 0, closures = 0;
static std::vector<int> hardBlue;

// Close a Blue-to-move position without expansion.  score = best sum found.
bool closeOnly(u64 A, u64 B, Ref& out, double* score) {
    PKey pk{A, B};
    auto pit = proved.find(pk);
    if (pit != proved.end()) {
        out = pit->second;
        if (score) *score = -1;
        return true;
    }
    auto sit = scoreMemo.find(pk);
    if (sit != scoreMemo.end() && failed.count(pk)) {
        if (score) *score = sit->second;
        return false;
    }
    ++closures;
    auto comps = ST->components(H, W, A, B);
    int maxc = 0;
    for (u64 c : comps) maxc = std::max(maxc, __builtin_popcountll(c));
    double sc;
    bool ok = false;
    if (maxc <= LOCALMAX) {
        Val v = ST->value(H, W, A, B);
        sc = double(v.num) / double(ONE) + (v.star ? 1e-6 : 0);
        if (vle0(v)) {
            out = ST->intern(H, W, A, B, 0, false);
            ok = true;
        }
    } else {
        CURW = std::min(4, MAXW);
        Closure cl = closeDP(A, B);
        sc = score_of(cl);
        if (!cl.ok && MAXW >= 5 && sc <= S5) {
            CURW = 5;
            Closure c5 = closeDP(A, B, 0);
            if (c5.have && score_of(c5) < sc) sc = score_of(c5);
            if (c5.ok) cl = c5;
        }
        if (!cl.ok && MAXW >= 6 && sc <= S6) {
            CURW = 6;
            Closure c6 = closeDP(A, B, 0);
            if (c6.have && score_of(c6) < sc) sc = score_of(c6);
            if (c6.ok) cl = c6;
        }
        if (cl.ok) {
            out = make_closure_node(A, B, cl);
            ok = true;
        }
    }
    if (score) *score = ok ? -1 : sc;
    if (ok)
        proved[pk] = out;
    else {
        scoreMemo[pk] = sc;
        failed.emplace(pk, 0);
    }
    return ok;
}

std::vector<std::pair<double, int>> rank_replies(u64 A1, u64 B1, int& closedBy, Ref& closedRef,
                                                const std::vector<int>& first);
bool proveBoard(u64 A, u64 B, int depth, Ref& out);

// Find a White answer to Blue's move (A1, B1 = position after it, White to move)
// with a proof of depth <= depth.  Returns the reply or -1.
int answerMove(u64 A1, u64 B1, int depth, const std::vector<int>& first, Ref& out, double* bestScore) {
    const Board& bd = ST->board(H, W);
    int closedBy = -1;
    Ref cref;
    auto ranked = rank_replies(A1, B1, closedBy, cref, first);
    if (bestScore) *bestScore = ranked.empty() ? 1e18 : ranked[0].first;
    if (closedBy >= 0) {
        out = cref;
        return closedBy;
    }
    for (int d = 1; d <= depth; ++d) {
        int tried = 0;
        for (auto& sc : ranked) {
            if (tried++ >= KTRY) break;
            if (timed_out()) return -1;
            int u = sc.second;
            u64 A2 = A1 & ~(u64(1) << u), B2 = B1 & ~bd.closed[u];
            if (proveBoard(A2, B2, d, out)) return u;
        }
    }
    return -1;
}

// Closure-only pass over every White reply: returns replies sorted by score;
// if one closes, closedBy is set.
std::vector<std::pair<double, int>> rank_replies(u64 A1, u64 B1, int& closedBy, Ref& closedRef,
                                                const std::vector<int>& first) {
    const Board& bd = ST->board(H, W);
    std::vector<int> order = first;
    for (u64 m = B1; m; m &= m - 1) {
        int u = __builtin_ctzll(m);
        if (std::find(order.begin(), order.end(), u) == order.end()) order.push_back(u);
    }
    std::vector<std::pair<double, int>> scored;
    closedBy = -1;
    for (int u : order) {
        if (!(B1 >> u & 1)) continue;
        u64 A2 = A1 & ~(u64(1) << u), B2 = B1 & ~bd.closed[u];
        double s;
        Ref r;
        if (closeOnly(A2, B2, r, &s)) {
            closedBy = u;
            closedRef = r;
            return scored;
        }
        scored.push_back({s, u});
    }
    std::stable_sort(scored.begin(), scored.end());
    return scored;
}

bool proveBoard(u64 A, u64 B, int depth, Ref& out) {
    PKey fk{A, B};
    auto pit = proved.find(fk);
    if (pit != proved.end()) {
        out = pit->second;
        return true;
    }
    auto fit = failed.find(fk);
    if (fit != failed.end() && fit->second >= depth) return false;
    ++nodes_tried;
    if (closeOnly(A, B, out, nullptr)) return true;
    if (depth == 0 || timed_out()) return false;
    const Board& bd = ST->board(H, W);
    std::vector<int> syms;
    for (int g = 1; g < 4; ++g)
        if (refl_mask(g, A) == A && refl_mask(g, B) == B) syms.push_back(g);
    std::map<int, int> replyOf;
    std::vector<Store::FrameEdge> fes;
    std::vector<int> killers, order;
    for (int hv : hardBlue)
        if (A >> hv & 1) order.push_back(hv);
    for (u64 m = A; m; m &= m - 1)
        if (std::find(order.begin(), order.end(), __builtin_ctzll(m)) == order.end())
            order.push_back(__builtin_ctzll(m));
    for (int v : order) {
        u64 A1 = A & ~bd.closed[v], B1 = B & ~(u64(1) << v);
        std::vector<int> first;
        for (int g : syms) {
            auto it = replyOf.find(refl_cell(g, v));
            if (it != replyOf.end()) first.push_back(refl_cell(g, it->second));
        }
        for (int k : killers) first.push_back(k);
        Ref child;
        double bs;
        int u = answerMove(A1, B1, depth - 1, first, child, &bs);
        if (u < 0) {
            if (VERBOSE)
                std::fprintf(stderr, "    depth %d: Blue (%d,%d) unanswered (best closure %.4f) [%.0fs]\n", depth,
                             v / W, v % W, bs, now() - T0);
            failed[fk] = std::max(failed[fk], depth);
            hardBlue.erase(std::remove(hardBlue.begin(), hardBlue.end(), v), hardBlue.end());
            hardBlue.insert(hardBlue.begin(), v);
            if (hardBlue.size() > 12) hardBlue.pop_back();
            return false;
        }
        u64 A2 = A1 & ~(u64(1) << u), B2 = B1 & ~bd.closed[u];
        fes.push_back(Store::FrameEdge{v, u, child.id, A2, B2});
        replyOf[v] = u;
        killers.erase(std::remove(killers.begin(), killers.end(), u), killers.end());
        killers.insert(killers.begin(), u);
        if (killers.size() > 8) killers.pop_back();
    }
    out = ST->add_node_frame(H, W, A, B, 0, false, EXPAND, 0, fes);
    proved[fk] = out;
    return true;
}

static void emit(Ref r, const std::string& path, const std::string& extra) {
    ST->drain_from(r.id);
    char buf[128];
    std::snprintf(buf, sizeof buf, ",\"board\":[%d,%d],\"root_xf\":[%d,%d,%d]", H, W, r.xf.sym, r.xf.dr, r.xf.dc);
    ST->emit(path, {{"pos", r.id}}, extra + buf);
}

static double envd(const char* k, double d) { return std::getenv(k) ? std::atof(std::getenv(k)) : d; }

int main(int argc, char** argv) {
    if (argc < 6) die("usage: hy2 scan|answer|prove|close H W A B ...");
    std::string mode = argv[1];
    H = std::atoi(argv[2]);
    W = std::atoi(argv[3]);
    u64 A = std::strtoull(argv[4], nullptr, 10), B = std::strtoull(argv[5], nullptr, 10);
    MAXW = int(envd("HYW", 5));
    CAP5 = int(envd("HYCAP5", 25));
    CAP6 = int(envd("HYCAP6", 28));
    KTRY = int(envd("HYK", 6));
    S5 = envd("HYS5", 1.0);
    S6 = envd("HYS6", 0.5);
    LOCALMAX = int(envd("HYLOCAL", 22));
    VERBOSE = std::getenv("HYVERBOSE") != nullptr;
    Store st(int(envd("HYLOG", 25)));
    st.memo.clear_when_full = true;
    ST = &st;
    T0 = now();
    DEADLINE = T0 + envd("HYT", 1e9);
    const Board& bd = st.board(H, W);
    if (mode == "scan") {
        int depth = std::atoi(argv[6]);
        for (u64 m = A; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            u64 A1 = A & ~bd.closed[v], B1 = B & ~(u64(1) << v);
            Ref r;
            double bs;
            long long before = nodes_tried;
            int u = answerMove(A1, B1, depth, {}, r, &bs);
            std::printf("SCAN blue %d (%d,%d) reply %d best0 %.4f tried %lld t %.0f\n", v, v / W, v % W, u, bs,
                        nodes_tried - before, now() - T0);
            std::fflush(stdout);
        }
        return 0;
    }
    if (mode == "close") {
        // close H W A B [V]: best vertical-cut closures of P (or of every
        // White reply to Blue V), widths 4..MAXW, with the blocks.
        std::vector<std::pair<u64, u64>> todo;
        std::vector<int> labels;
        if (argc > 6) {
            int v = std::atoi(argv[6]);
            u64 A1 = A & ~bd.closed[v], B1 = B & ~(u64(1) << v);
            for (u64 m = B1; m; m &= m - 1) {
                int u = __builtin_ctzll(m);
                todo.push_back({A1 & ~(u64(1) << u), B1 & ~bd.closed[u]});
                labels.push_back(u);
            }
        } else {
            todo.push_back({A, B});
            labels.push_back(-1);
        }
        for (std::size_t i = 0; i < todo.size(); ++i) {
            auto [a, b] = todo[i];
            std::printf("reply %d  %s\n", labels[i], rows_str(bd, a, b).c_str());
            for (int w = 4; w <= MAXW; ++w) {
                CURW = w;
                Closure cl = closeDP(a, b);
                std::printf("  w<=%d total %s%s [%.0fs]:", w, cl.have ? valstr(cl.total).c_str() : "none",
                            cl.ok ? " OK" : "", now() - T0);
                for (auto it = cl.blocks.rbegin(); it != cl.blocks.rend(); ++it)
                    std::printf(" [c%d-%d %s]", it->k, it->k + it->wd - 1, valstr(it->v).c_str());
                std::printf(" retired %llu\n", (unsigned long long)cl.retired);
                std::fflush(stdout);
            }
        }
        return 0;
    }
    if (mode == "answer") {
        if (argc < 9) die("usage: hy2 answer H W A B V DEPTH out.json");
        int v = std::atoi(argv[6]), depth = std::atoi(argv[7]);
        if (!(A >> v & 1)) die("V is not a Blue-legal cell");
        u64 A1 = A & ~bd.closed[v], B1 = B & ~(u64(1) << v);
        Ref r;
        double bs;
        int u = answerMove(A1, B1, depth, {}, r, &bs);
        if (u < 0) {
            std::printf("RESULT blue %d FAILED best0 %.4f tried %lld closures %lld seconds %.0f%s\n", v, bs,
                        nodes_tried, closures, now() - T0, timed_out() ? " TIMEOUT" : "");
            return 1;
        }
        char extra[128];
        std::snprintf(extra, sizeof extra, ",\"move\":%d,\"reply\":%d", v, u);
        emit(r, argv[8], extra);
        std::printf("RESULT blue %d reply %d nodes %zu tried %lld seconds %.0f\n", v, u, st.nodes.size(),
                    nodes_tried, now() - T0);
        return 0;
    }
    if (mode == "prove") {
        if (argc < 8) die("usage: hy2 prove H W A B DEPTH out.json");
        int depth = std::atoi(argv[6]);
        Ref r;
        bool ok = false;
        for (int d = 0; d <= depth && !ok; ++d) ok = proveBoard(A, B, d, r);
        if (!ok) {
            std::printf("RESULT FAILED tried %lld seconds %.0f%s\n", nodes_tried, now() - T0,
                        timed_out() ? " TIMEOUT" : "");
            return 1;
        }
        emit(r, argv[7], "");
        std::printf("RESULT proved nodes %zu tried %lld seconds %.0f\n", st.nodes.size(), nodes_tried, now() - T0);
        return 0;
    }
    die("unknown mode");
}
