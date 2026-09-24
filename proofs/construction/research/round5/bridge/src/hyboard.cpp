// hyboard: adaptive whole-board prover for Blue openings on an H x W board
// (discovery tool; its output is rechecked by proofs/5x9/verify.py).
//
// A Blue-to-move whole-board position is closed by (1) exact local values when
// every component is small, (2) a vertical column-cut comparison (dynamic
// program over seams with minimal White retirements, exact block values), or
// (3) expansion: every Blue move gets a White reply leading to a position
// closed recursively, with a depth limit.
//
// usage: hyboard H W OPENING REPLY|-1 MAXW DEPTH out.json [maxlog2] [localmax] [K] [maxfirst] [seconds]
//   The certificate root "pos" is the position after OPENING and the reply.
#include <array>
#include <chrono>
#include <climits>
#include <set>

#include "hybrid.hpp"
using namespace hy;

static int H, W, MAXW, LOCALMAX = 22, KTRY = 6, CAP = 25, CURW = 4;
static double SKIPWIDE = std::getenv("HYSKIP") ? std::atof(std::getenv("HYSKIP")) : 1.0;
static bool VERBOSE = std::getenv("HYVERBOSE") != nullptr;
static Store* ST;
static const i64 INF = LLONG_MAX / 4;
static double now() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
static double T0;

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

// Vertical-cut comparison search: minimal block-value sum over all partitions
// of the columns into blocks of width <= MAXW with seam retirements.
Closure closeDP(u64 A, u64 B, i64 threshold = INF) {
    const int S = 1 << H;
    // Lower bounds: a block's value only grows with retirements, so the
    // unretired block values bound every variant from below.
    std::vector<i64> v0((W + 1) * (CURW + 1), INF), lbsuf(W + 1, INF);
    if (threshold < INF) {
        for (int k = 0; k < W; ++k)
            for (int wd = 1; wd <= CURW && k + wd <= W; ++wd) {
                u64 block = 0;
                for (int r = 0; r < H; ++r)
                    for (int c = k; c < k + wd; ++c) block |= colbit(r, c);
                if (__builtin_popcountll((A | B) & block) > CAP) continue;
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
                    if (__builtin_popcountll(Ab | Bb) > CAP) continue;
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

// Symmetries of the H x W frame that fix rows/columns orientation classes:
// g bit0 flips rows, bit1 flips columns.
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

struct FailKey {
    u64 A, B;
    bool operator<(const FailKey& o) const { return A < o.A || (A == o.A && B < o.B); }
};
static std::map<FailKey, int> failed;  // position -> largest depth that failed
static std::map<FailKey, Ref> proved;  // frame position -> node
static long long nodes_tried = 0;
static std::vector<int> hardBlue;
static double DEADLINE = 1e18;
static int MAXFIRST = 1000;

bool proveBoard(u64 A, u64 B, int depth, Ref& out);

bool closeOnly(u64 A, u64 B, Ref& out, double* score) {
    auto comps = ST->components(H, W, A, B);
    int maxc = 0;
    for (u64 c : comps) maxc = std::max(maxc, __builtin_popcountll(c));
    if (maxc <= LOCALMAX) {
        Val v = ST->value(H, W, A, B);
        if (score) *score = double(v.num) / double(ONE) + (v.star ? 1e-6 : 0);
        if (vle0(v)) {
            out = ST->intern(H, W, A, B, 0, false);
            return true;
        }
        return false;
    }
    CURW = std::min(4, MAXW);
    Closure cl = closeDP(A, B);
    if (score) *score = score_of(cl);
    if (!cl.ok && MAXW > 4 && score_of(cl) <= SKIPWIDE) {
        CURW = MAXW;
        cl = closeDP(A, B, 0);
    }
    if (cl.ok) {
        out = make_closure_node(A, B, cl);
        return true;
    }
    return false;
}

bool proveBoard(u64 A, u64 B, int depth, Ref& out) {
    FailKey fk{A, B};
    auto pit = proved.find(fk);
    if (pit != proved.end()) {
        out = pit->second;
        return true;
    }
    auto fit = failed.find(fk);
    if (fit != failed.end() && fit->second >= depth) return false;
    ++nodes_tried;
    if (closeOnly(A, B, out, nullptr)) {
        proved[fk] = out;
        return true;
    }
    if (depth == 0) {
        failed[fk] = std::max(failed[fk], 0);
        return false;
    }
    const Board& bd = ST->board(H, W);
    // symmetries of this position
    std::vector<int> syms;
    for (int g = 1; g < 4; ++g)
        if (refl_mask(g, A) == A && refl_mask(g, B) == B) syms.push_back(g);
    std::map<int, int> replyOf;
    std::vector<Store::FrameEdge> fes;
    std::vector<int> killers;
    std::vector<int> order;
    for (int hv : hardBlue)
        if (A >> hv & 1) order.push_back(hv);
    for (u64 m = A; m; m &= m - 1)
        if (std::find(order.begin(), order.end(), __builtin_ctzll(m)) == order.end())
            order.push_back(__builtin_ctzll(m));
    for (int v : order) {
        if (now() > DEADLINE) {
            failed[fk] = std::max(failed[fk], depth);
            return false;
        }
        u64 A1 = A & ~bd.closed[v], B1 = B & ~(u64(1) << v);
        std::vector<int> cands;
        for (int g : syms) {
            int pv = refl_cell(g, v);
            auto it = replyOf.find(pv);
            if (it != replyOf.end()) cands.push_back(refl_cell(g, it->second));
        }
        for (int k : killers)
            if ((B1 >> k & 1) && std::find(cands.begin(), cands.end(), k) == cands.end()) cands.push_back(k);
        // order the remaining replies by closure score
        std::vector<std::pair<double, int>> scored;
        for (u64 mm = B1; mm; mm &= mm - 1) {
            int u = __builtin_ctzll(mm);
            if (std::find(cands.begin(), cands.end(), u) != cands.end()) continue;
            scored.push_back({0.0, u});
        }
        bool ok = false;
        Ref child;
        int chosen = -1;
        auto attempt = [&](int u, int d) {
            u64 A2 = A1 & ~(u64(1) << u), B2 = B1 & ~bd.closed[u];
            if (proveBoard(A2, B2, d, child)) {
                chosen = u;
                ok = true;
                fes.push_back(Store::FrameEdge{v, u, child.id, A2, B2});
            }
        };
        for (int u : cands) {
            attempt(u, depth - 1);
            if (ok) break;
        }
        if (!ok) {
            // cheap pass: closure only, recording scores
            for (auto& sc : scored) {
                int u = sc.second;
                u64 A2 = A1 & ~(u64(1) << u), B2 = B1 & ~bd.closed[u];
                double s;
                Ref r;
                if (closeOnly(A2, B2, r, &s)) {
                    proved[FailKey{A2, B2}] = r;
                    chosen = u;
                    ok = true;
                    fes.push_back(Store::FrameEdge{v, u, r.id, A2, B2});
                    break;
                }
                sc.first = s;
            }
        }
        if (!ok && depth >= 2) {
            std::sort(scored.begin(), scored.end());
            int tried = 0;
            for (auto& sc : scored) {
                if (tried++ >= KTRY) break;
                attempt(sc.second, depth - 1);
                if (ok) break;
            }
        }
        if (!ok) {
            if (VERBOSE) {
                double bs = 1e18;
                int bu = -1;
                for (auto& sc : scored)
                    if (sc.first < bs) bs = sc.first, bu = sc.second;
                std::fprintf(stderr, "    depth %d: Blue (%d,%d) unanswered; best reply (%d,%d) score %.4f\n", depth,
                             v / W, v % W, bu / W, bu % W, bs);
            }
            failed[fk] = std::max(failed[fk], depth);
            hardBlue.erase(std::remove(hardBlue.begin(), hardBlue.end(), v), hardBlue.end());
            hardBlue.insert(hardBlue.begin(), v);
            if (hardBlue.size() > 12) hardBlue.pop_back();
            return false;
        }
        replyOf[v] = chosen;
        killers.erase(std::remove(killers.begin(), killers.end(), chosen), killers.end());
        killers.insert(killers.begin(), chosen);
        if (killers.size() > 8) killers.pop_back();
    }
    out = ST->add_node_frame(H, W, A, B, 0, false, EXPAND, 0, fes);
    proved[fk] = out;
    return true;
}

int main(int argc, char** argv) {
    if (argc < 8) die("usage: hyboard H W OPENING REPLY|-1 MAXW DEPTH out.json [maxlog2] [localmax] [K]");
    H = std::atoi(argv[1]);
    W = std::atoi(argv[2]);
    int opening = std::atoi(argv[3]), reply = std::atoi(argv[4]);
    MAXW = std::atoi(argv[5]);
    int depth = std::atoi(argv[6]);
    std::string out = argv[7];
    int maxlog = argc > 8 ? std::atoi(argv[8]) : 25;
    if (argc > 9) LOCALMAX = std::atoi(argv[9]);
    if (argc > 10) KTRY = std::atoi(argv[10]);
    if (argc > 11) MAXFIRST = std::atoi(argv[11]);
    if (std::getenv("HYCAP")) CAP = std::atoi(std::getenv("HYCAP"));
    double budget = argc > 12 ? std::atof(argv[12]) : 1e9;
    Store st(maxlog);
    st.memo.clear_when_full = true;
    ST = &st;
    T0 = now();
    DEADLINE = T0 + budget;
    const Board& bd = st.board(H, W);
    u64 A0 = bd.full & ~bd.closed[opening], B0 = bd.full & ~(u64(1) << opening);
    std::vector<int> replies;
    if (reply >= 0)
        replies.push_back(reply);
    else {
        // order replies by closure score first
        std::vector<std::pair<double, int>> sc;
        for (u64 m = B0; m; m &= m - 1) {
            int u = __builtin_ctzll(m);
            u64 A = A0 & ~(u64(1) << u), B = B0 & ~bd.closed[u];
            double s;
            Ref r;
            bool ok = closeOnly(A, B, r, &s);
            if (ok) s = -1e9;
            sc.push_back({s, u});
            std::fprintf(stderr, "  reply (%d,%d) closure score %.4f%s [%.0fs]\n", u / W, u % W, s,
                         ok ? " CLOSED" : "", now() - T0);
        }
        std::sort(sc.begin(), sc.end());
        for (auto& p : sc)
            if (int(replies.size()) < MAXFIRST) replies.push_back(p.second);
    }
    for (int u : replies) {
        u64 A = A0 & ~(u64(1) << u), B = B0 & ~bd.closed[u];
        Ref r;
        std::fprintf(stderr, "trying reply (%d,%d) depth %d [%.0fs]\n", u / W, u % W, depth, now() - T0);
        if (proveBoard(A, B, depth, r)) {
            std::fprintf(stderr, "PROVED opening (%d,%d) reply (%d,%d); draining local claims [%.0fs]\n",
                         opening / W, opening % W, u / W, u % W, now() - T0);
            st.drain_from(r.id);
            char extra[256];
            std::snprintf(extra, sizeof extra,
                          ",\"board\":[%d,%d],\"opening\":%d,\"reply\":%d,\"root_xf\":[%d,%d,%d]", H, W, opening, u,
                          r.xf.sym, r.xf.dr, r.xf.dc);
            st.emit(out, {{"pos", r.id}}, extra);
            std::printf("RESULT opening %d reply %d nodes %zu tried %lld seconds %.0f\n", opening, u,
                        st.nodes.size(), nodes_tried, now() - T0);
            return 0;
        }
        std::fprintf(stderr, "  failed reply (%d,%d) [%.0fs, tried %lld]\n", u / W, u % W, now() - T0, nodes_tried);
    }
    std::printf("RESULT opening %d FAILED tried %lld seconds %.0f\n", opening, nodes_tried, now() - T0);
    return 1;
}
