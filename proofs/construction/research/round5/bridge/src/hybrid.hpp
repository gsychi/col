// hybrid.hpp -- node store, canonical frames and certificate emission for the
// hybrid (expansion + comparison) Col certificates (format col-hybrid-v1).
//
// DISCOVERY ONLY: the Python verifier rechecks every node without search.
//
// A node is a claim  G(A,B) + q + s*  <=  0  (Blue to move) about a Col
// position on its own h x w box (row-major local masks), plus a dyadic number
// q and a star bit s. Nodes are stored in a canonical orientation (one of the
// eight box symmetries); a reference to a node carries a transform (sym, dr,
// dc) mapping the node's local cells into the referencing frame.
//
// Justifications:
//   ARITH   : A empty and (q < 0 or (q == 0 and not s)).
//   EXPAND  : one White answer for every Blue option (cell, number, star).
//   COMPARE : White retires cells R of B; the live cells of (A, B\R) are split
//             among children whose images are disjoint, cover A, stay inside
//             B\R, and no grid edge between different children joins two
//             White-legal cells. Sum condition on the children's numbers.
#pragma once
#include <algorithm>
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <unordered_map>
#include <vector>

#include "colcgt.hpp"

namespace hy {
using namespace cc;

struct Xf {
    int sym = 0, dr = 0, dc = 0;
};

inline void symdims(int sym, int h, int w, int& ho, int& wo) {
    if (sym & 1) {
        ho = w;
        wo = h;
    } else {
        ho = h;
        wo = w;
    }
}
inline void symcell(int sym, int h, int w, int r, int c, int& ro, int& co) {
    int hh = h, ww = w;
    if (sym & 1) {
        std::swap(r, c);
        std::swap(hh, ww);
    }
    if (sym & 2) r = hh - 1 - r;
    if (sym & 4) c = ww - 1 - c;
    ro = r;
    co = c;
}
// Map a mask on an h x w box by sym, then shift by (dr, dc) into a frame of width W.
inline u64 mapmask(u64 m, int h, int w, int sym, int dr, int dc, int W) {
    u64 out = 0;
    while (m) {
        int v = __builtin_ctzll(m);
        m &= m - 1;
        int ro, co;
        symcell(sym, h, w, v / w, v % w, ro, co);
        out |= u64(1) << ((ro + dr) * W + co + dc);
    }
    return out;
}

struct Canonical {
    int h = 0, w = 0;
    u64 A = 0, B = 0;
    Xf xf;
};

// Canonical orientation of the live part of (A,B) on an H x W frame.
inline Canonical canonicalize(int H, int W, u64 A, u64 B) {
    Canonical res;
    u64 live = A | B;
    if (!live) return res;
    int r0 = 99, r1 = -1, c0 = 99, c1 = -1;
    for (u64 m = live; m; m &= m - 1) {
        int v = __builtin_ctzll(m), r = v / W, c = v % W;
        r0 = std::min(r0, r);
        r1 = std::max(r1, r);
        c0 = std::min(c0, c);
        c1 = std::max(c1, c);
    }
    int bh = r1 - r0 + 1, bw = c1 - c0 + 1;
    u64 A0 = 0, B0 = 0;
    for (u64 m = live; m; m &= m - 1) {
        int v = __builtin_ctzll(m), r = v / W - r0, c = v % W - c0;
        u64 bit = u64(1) << (r * bw + c);
        if (A >> v & 1) A0 |= bit;
        if (B >> v & 1) B0 |= bit;
    }
    int bt = -1, bhh = 0, bww = 0;
    u64 bA = 0, bB = 0;
    for (int t = 0; t < 8; ++t) {
        int ht, wt;
        symdims(t, bh, bw, ht, wt);
        if (ht > 12 || wt > 12) continue;
        u64 At = mapmask(A0, bh, bw, t, 0, 0, wt), Bt = mapmask(B0, bh, bw, t, 0, 0, wt);
        if (bt < 0 || std::tie(ht, wt, At, Bt) < std::tie(bhh, bww, bA, bB)) {
            bt = t;
            bhh = ht;
            bww = wt;
            bA = At;
            bB = Bt;
        }
    }
    res.h = bhh;
    res.w = bww;
    res.A = bA;
    res.B = bB;
    for (int u = 0; u < 8; ++u) {
        int hu, wu;
        symdims(u, bhh, bww, hu, wu);
        if (hu != bh || wu != bw) continue;
        if (mapmask(bA, bhh, bww, u, 0, 0, bw) == A0 && mapmask(bB, bhh, bww, u, 0, 0, bw) == B0) {
            res.xf = Xf{u, r0, c0};
            return res;
        }
    }
    die("canonicalize: no inverse symmetry");
}

enum Kind : std::uint8_t { PENDING = 0, ARITH = 1, EXPAND = 2, COMPARE = 3 };

struct Edge {
    int mv = 0, rep = 0, child = -1;
    Xf xf;
};
struct Node {
    std::uint8_t h = 0, w = 0;
    u64 A = 0, B = 0;
    i64 q = 0;
    bool s = false;
    Kind kind = PENDING;
    u64 retired = 0;
    std::vector<Edge> edges;
};
struct Key {
    std::uint16_t hw;
    u64 A, B;
    i64 q;
    bool s;
    bool operator==(const Key& o) const { return hw == o.hw && A == o.A && B == o.B && q == o.q && s == o.s; }
};
struct KeyHash {
    std::size_t operator()(const Key& k) const {
        u64 x = k.A * 0x9E3779B97F4A7C15ULL ^ (k.B + 0x632BE59BD9B4E019ULL) * 0xC2B2AE3D27D4EB4FULL ^
                (u64(k.q) * 0x94d049bb133111ebULL) ^ (u64(k.hw) << 1) ^ (k.s ? 0x5555 : 0);
        x ^= x >> 31;
        x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 29;
        return std::size_t(x);
    }
};
struct Ref {
    int id = -1;
    Xf xf;
};

struct Store {
    std::vector<Node> nodes;
    std::unordered_map<Key, int, KeyHash> index;
    std::vector<int> pending;
    Table memo;
    Table big{23};
    Canon canon;
    std::map<int, std::unique_ptr<Board>> boards;
    std::map<int, std::unique_ptr<Engine>> engines;
    explicit Store(int maxlog) : memo(maxlog) { big.clear_when_full = true; }

    const Board& board(int h, int w) {
        auto& b = boards[h * 16 + w];
        if (!b) b.reset(new Board(h, w));
        return *b;
    }
    Engine& engine(int h, int w) {
        auto& e = engines[h * 16 + w];
        if (!e) {
            e.reset(new Engine(board(h, w), memo, canon));
            e->big = &big;
        }
        return *e;
    }
    Val value(int h, int w, u64 A, u64 B) {
        if (!(A | B)) return Val{};
        return engine(h, w).position(A, B);
    }
    bool claim_true(int h, int w, u64 A, u64 B, i64 q, bool s) { return vle0(vadd(value(h, w, A, B), Val{q, s})); }

    int find(int H, int W, u64 A, u64 B, i64 q, bool s, Xf* xf = nullptr) {
        Canonical c = canonicalize(H, W, A, B);
        auto it = index.find(Key{std::uint16_t(c.h * 16 + c.w), c.A, c.B, q, s});
        if (xf) *xf = c.xf;
        return it == index.end() ? -1 : it->second;
    }
    // Intern a claim given in an H x W frame; new nodes are queued as pending.
    Ref intern(int H, int W, u64 A, u64 B, i64 q, bool s) {
        Canonical c = canonicalize(H, W, A, B);
        Key k{std::uint16_t(c.h * 16 + c.w), c.A, c.B, q, s};
        auto it = index.find(k);
        if (it != index.end()) return Ref{it->second, c.xf};
        int id = int(nodes.size());
        Node n;
        n.h = std::uint8_t(c.h);
        n.w = std::uint8_t(c.w);
        n.A = c.A;
        n.B = c.B;
        n.q = q;
        n.s = s;
        nodes.push_back(std::move(n));
        index.emplace(k, id);
        pending.push_back(id);
        return Ref{id, c.xf};
    }

    std::vector<u64> components(int h, int w, u64 A, u64 B) {
        std::vector<u64> out;
        if (!(A | B)) return out;
        const Board& bd = board(h, w);
        u64 live = A | B;
        while (live) {
            u64 seed = live & (~live + 1);
            u64 comp = bd.flood(seed, A, B);
            live &= ~comp;
            out.push_back(comp);
        }
        return out;
    }

    // Justify a pending node whose claim is true, using exact values.
    void justify_local(int id) {
        Node nd = nodes[id];
        int h = nd.h, w = nd.w;
        if (!nd.A && (nd.q < 0 || (nd.q == 0 && !nd.s))) {
            nodes[id].kind = ARITH;
            return;
        }
        auto comps = components(h, w, nd.A, nd.B);
        if (comps.size() >= 2) {
            std::vector<Edge> es;
            for (u64 cm : comps) {
                Val v = value(h, w, nd.A & cm, nd.B & cm);
                Ref r = intern(h, w, nd.A & cm, nd.B & cm, -v.num, v.star);
                es.push_back(Edge{0, 0, r.id, r.xf});
            }
            nodes[id].kind = COMPARE;
            nodes[id].retired = 0;
            nodes[id].edges = std::move(es);
            return;
        }
        expand_local(id);
    }

    struct Opt {
        int mv;
        u64 A, B;
        i64 q;
        bool s;
    };
    std::vector<Opt> blue_options(int h, int w, u64 A, u64 B, i64 q, bool s) {
        std::vector<Opt> out;
        if (A) {
            const Board& bd = board(h, w);
            for (u64 m = A; m; m &= m - 1) {
                int v = __builtin_ctzll(m);
                out.push_back(Opt{v, A & ~bd.closed[v], B & ~(u64(1) << v), q, s});
            }
        }
        i64 ql;
        if (left_of_number(q, ql)) out.push_back(Opt{-1, A, B, ql, s});
        if (s) out.push_back(Opt{-2, A, B, q, false});
        return out;
    }
    std::vector<Opt> white_options(int h, int w, u64 A, u64 B, i64 q, bool s) {
        std::vector<Opt> out;
        if (B) {
            const Board& bd = board(h, w);
            for (u64 m = B; m; m &= m - 1) {
                int v = __builtin_ctzll(m);
                out.push_back(Opt{v, A & ~(u64(1) << v), B & ~bd.closed[v], q, s});
            }
        }
        i64 qr;
        if (right_of_number(q, qr)) out.push_back(Opt{-1, A, B, qr, s});
        if (s) out.push_back(Opt{-2, A, B, q, false});
        return out;
    }

    int largest_component(int h, int w, u64 A, u64 B) {
        int best = 0;
        for (u64 c : components(h, w, A, B)) best = std::max(best, __builtin_popcountll(c));
        return best;
    }

    void expand_local(int id) {
        Node nd = nodes[id];
        int h = nd.h, w = nd.w;
        std::vector<Edge> es;
        for (const Opt& b : blue_options(h, w, nd.A, nd.B, nd.q, nd.s)) {
            int bestScore = 1 << 30;
            Opt best{};
            bool found = false;
            for (const Opt& r : white_options(h, w, b.A, b.B, b.q, b.s)) {
                if (!claim_true(h, w, r.A, r.B, r.q, r.s)) continue;
                int score;
                if (find(h, w, r.A, r.B, r.q, r.s) >= 0)
                    score = 0;
                else
                    score = 1 + 64 * largest_component(h, w, r.A, r.B) + __builtin_popcountll(r.A | r.B);
                if (!found || score < bestScore) {
                    found = true;
                    bestScore = score;
                    best = r;
                    if (score == 0) break;
                }
            }
            if (!found) die("expand_local: no White answer at a claimed losing node");
            Ref ref = intern(h, w, best.A, best.B, best.q, best.s);
            es.push_back(Edge{b.mv, best.mv, ref.id, ref.xf});
        }
        nodes[id].kind = EXPAND;
        nodes[id].edges = std::move(es);
    }

    // Process all pending nodes with exact local values.
    void drain(std::size_t report_every = 100000) {
        std::size_t done = 0;
        while (!pending.empty()) {
            int id = pending.back();
            pending.pop_back();
            if (nodes[id].kind != PENDING) continue;
            justify_local(id);
            if (++done % report_every == 0)
                std::fprintf(stderr, "  drained %zu, nodes=%zu, pending=%zu, memo=%zu\n", done, nodes.size(),
                             pending.size(), memo.used);
        }
    }

    // Transform placing node `id` onto the masks (At, Bt) of an Hn x Wn frame.
    Xf find_xf(int id, int Wn, u64 At, u64 Bt) {
        const Node& c = nodes[id];
        if (!(At | Bt)) return Xf{};
        int r0 = 99, c0 = 99;
        for (u64 m = At | Bt; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            r0 = std::min(r0, v / Wn);
            c0 = std::min(c0, v % Wn);
        }
        for (int t = 0; t < 8; ++t) {
            int ht, wt;
            symdims(t, c.h, c.w, ht, wt);
            if (c0 + wt > Wn) continue;
            if (mapmask(c.A, c.h, c.w, t, r0, c0, Wn) == At && mapmask(c.B, c.h, c.w, t, r0, c0, Wn) == Bt)
                return Xf{t, r0, c0};
        }
        die("find_xf: child does not match");
    }

    struct FrameEdge {
        int mv, rep, child;
        u64 A, B;  // child's position in the frame
    };
    // Create (or return) the node for a frame position with an explicit
    // justification given in frame coordinates.
    Ref add_node_frame(int H, int W, u64 A, u64 B, i64 q, bool s, Kind kind, u64 retired,
                       const std::vector<FrameEdge>& fes) {
        Ref me = intern(H, W, A, B, q, s);
        if (nodes[me.id].kind != PENDING) return me;
        Node& n0 = nodes[me.id];
        int h = n0.h, w = n0.w;
        std::vector<int> inv(H * W, -1);
        for (int v = 0; v < h * w; ++v) {
            int ro, co;
            symcell(me.xf.sym, h, w, v / w, v % w, ro, co);
            int fr = ro + me.xf.dr, fc = co + me.xf.dc;
            if (fr >= 0 && fr < H && fc >= 0 && fc < W) inv[fr * W + fc] = v;
        }
        auto mapc = [&](int cell) {
            if (cell < 0) return cell;
            if (inv[cell] < 0) die("add_node_frame: cell outside node box");
            return inv[cell];
        };
        auto mapm = [&](u64 m) {
            u64 out = 0;
            for (; m; m &= m - 1) out |= u64(1) << mapc(__builtin_ctzll(m));
            return out;
        };
        std::vector<Edge> es;
        for (const FrameEdge& fe : fes) {
            u64 ca = mapm(fe.A), cb = mapm(fe.B);
            Xf x = find_xf(fe.child, w, ca, cb);
            es.push_back(Edge{mapc(fe.mv), mapc(fe.rep), fe.child, x});
        }
        Node& n = nodes[me.id];
        n.kind = kind;
        n.retired = mapm(retired);
        n.edges = std::move(es);
        return me;
    }

    // Justify every pending node reachable from root (depth-first).
    void drain_from(int root, std::size_t report_every = 100000) {
        std::vector<char> seen(nodes.size(), 0);
        std::vector<int> stack{root};
        std::size_t done = 0;
        while (!stack.empty()) {
            int x = stack.back();
            stack.pop_back();
            if (std::size_t(x) >= seen.size()) seen.resize(nodes.size(), 0);
            if (seen[x]) continue;
            seen[x] = 1;
            if (nodes[x].kind == PENDING) {
                justify_local(x);
                if (++done % report_every == 0)
                    std::fprintf(stderr, "  justified %zu, nodes=%zu, memo=%zu\n", done, nodes.size(), memo.used);
            }
            for (const Edge& e : nodes[x].edges) stack.push_back(e.child);
        }
    }

    // Emit the sub-DAG reachable from the given roots, renumbered.
    void emit(const std::string& path, const std::vector<std::pair<std::string, int>>& roots,
              const std::string& extra_json = "") {
        std::vector<int> order, newid(nodes.size(), -1);
        std::vector<int> stack;
        for (auto& [nm, r] : roots)
            if (newid[r] < 0) {
                newid[r] = int(order.size());
                order.push_back(r);
                stack.push_back(r);
            }
        while (!stack.empty()) {
            int x = stack.back();
            stack.pop_back();
            if (nodes[x].kind == PENDING) die("emit: pending node reachable");
            for (const Edge& e : nodes[x].edges)
                if (newid[e.child] < 0) {
                    newid[e.child] = int(order.size());
                    order.push_back(e.child);
                    stack.push_back(e.child);
                }
        }
        std::ofstream os(path);
        if (!os) die("cannot open " + path);
        os << "{\"format\":\"col-hybrid-v1\",\"roots\":{";
        for (std::size_t i = 0; i < roots.size(); ++i) {
            if (i) os << ",";
            os << "\"" << roots[i].first << "\":" << newid[roots[i].second];
        }
        os << "}" << extra_json << ",\"nodes\":[\n";
        for (std::size_t i = 0; i < order.size(); ++i) {
            const Node& n = nodes[order[i]];
            i64 pn, pd;
            numfrac(n.q, pn, pd);
            if (i) os << ",\n";
            os << "[" << int(n.h) << "," << int(n.w) << "," << n.A << "," << n.B << "," << pn << "," << pd << ","
               << (n.s ? 1 : 0) << ",";
            if (n.kind == ARITH)
                os << "\"A\"]";
            else if (n.kind == EXPAND) {
                os << "\"E\",[";
                for (std::size_t j = 0; j < n.edges.size(); ++j) {
                    const Edge& e = n.edges[j];
                    if (j) os << ",";
                    os << "[" << e.mv << "," << e.rep << "," << newid[e.child] << "," << e.xf.sym << ","
                       << e.xf.dr << "," << e.xf.dc << "]";
                }
                os << "]]";
            } else {
                os << "\"C\"," << n.retired << ",[";
                for (std::size_t j = 0; j < n.edges.size(); ++j) {
                    const Edge& e = n.edges[j];
                    if (j) os << ",";
                    os << "[" << newid[e.child] << "," << e.xf.sym << "," << e.xf.dr << "," << e.xf.dc << "]";
                }
                os << "]]";
            }
        }
        os << "\n]}\n";
        if (!os) die("write failed");
        std::fprintf(stderr, "emitted %zu nodes to %s\n", order.size(), path.c_str());
    }
};

}  // namespace hy
