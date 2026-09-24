// colcert5: emit a folded response-DAG certificate that the player to move
// LOSES in  G + q (+*)  for a Col permission position G = (A, B).
//
// The colout5 search (certificate mode) is used only to FIND replies. The
// output is checked by the separate program checkcert.cpp.
//
// Certificate content (all states in the mover's frame: a = cells of the
// player to move, b = cells of the other player, q = number, s = star):
//   * a value table: components (translated to the top-left corner) with a
//     claimed exact value x + e*; the checker verifies every entry from the
//     entries of its options (one ply, simplicity rule), so the table is
//     closed under taking options;
//   * checkpoints: REDUCED states (every component of the live cells has more
//     than K cells; components with at most K cells have been replaced by
//     their table values, added into q and s) at which the mover loses, each
//     with one reply to every option of the mover. An empty reduced state is
//     checked arithmetically.
//
// Binary format (little endian):
//   "COLCERT5" u32 H u32 W u32 K u32 SHIFT
//   u64 a u64 b i64 q u8 s                      reduced root
//   u64 nTable  { u64 a u64 b i64 x u8 e }      table entries
//   u64 nCheck  { u64 a u64 b i64 q u8 s u16 n { i16 first i16 reply } }
// Move codes: cell index >= 0, -1 = the mover's canonical move in the number,
// -2 = taking the star.
//
// Usage: colcert5 h w A B q star out.bin [-S K] [-t log2] [-T log2]
//   (q in the mover's frame, e.g. Blue first in G - r: A B -r)
#include "colcore.h"

#include <unordered_map>
#include <unordered_set>

#define main colout5_main_unused
#include "colout5.cpp"
#undef main

struct St {
    Mask a, b;
    i64 q;
    bool s;
    bool operator==(const St& o) const { return a == o.a && b == o.b && q == o.q && s == o.s; }
};
struct StHash {
    std::size_t operator()(const St& k) const {
        return std::size_t(Cache::hash(k.a ^ (Mask(k.s) << 63), k.b) ^ (Mask(k.q) * 0x9E3779B97F4A7C15ULL));
    }
};
struct PairHash {
    std::size_t operator()(const std::pair<Mask, Mask>& k) const { return std::size_t(Cache::hash(k.first, k.second)); }
};

struct Gen {
    const Board& bd;
    Search& sr;
    int K;
    std::unordered_map<std::pair<Mask, Mask>, Val, PairHash> table;  // normalized component -> value
    std::vector<std::pair<Mask, Mask>> pending;                       // table entries whose options are not yet closed

    Gen(const Board& b, Search& s, int k) : bd(b), sr(s), K(k) {}

    std::pair<Mask, Mask> normalize(Mask a, Mask b) const {
        Mask live = a | b;
        int rmin = __builtin_ctzll(live) / bd.w;
        int cmin = bd.w;
        for (Mask m = live; m; m &= m - 1) cmin = std::min(cmin, __builtin_ctzll(m) % bd.w);
        int sh = rmin * bd.w + cmin;
        return {a >> sh, b >> sh};
    }
    Val value_of_comp(Mask a, Mask b) {
        auto key = normalize(a, b);
        auto it = table.find(key);
        if (it != table.end()) return it->second;
        Val v = sr.vs.component(a, b);
        table.emplace(key, v);
        pending.push_back(key);
        return v;
    }
    // Fold every component with at most K cells into (q, s).
    St reduce(Mask a, Mask b, i64 q, bool s) {
        Mask live = a | b, ha = 0, hb = 0;
        while (live) {
            Mask seed = live & (~live + 1);
            Mask comp = bd.flood(seed, a, b);
            live &= ~comp;
            if (__builtin_popcountll(comp) <= K) {
                Val v = value_of_comp(a & comp, b & comp);
                q += v.num;
                s ^= v.star;
            } else {
                ha |= a & comp;
                hb |= b & comp;
            }
        }
        return St{ha, hb, q, s};
    }
    // Options of the player to move in a reduced state: (code, full child in the other player's frame).
    std::vector<std::pair<int, St>> options(const St& k) {
        std::vector<std::pair<int, St>> o;
        for (Mask m = k.a; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            o.push_back({v, St{k.b & ~(Mask(1) << v), k.a & ~bd.closed[v], -k.q, k.s}});
        }
        i64 ql;
        if (left_option(k.q, ql)) o.push_back({-1, St{k.b, k.a, -ql, k.s}});
        if (k.s) o.push_back({-2, St{k.b, k.a, -k.q, false}});
        return o;
    }
    // Close the table under options (every option of every entry splits into entries).
    void close_table() {
        while (!pending.empty()) {
            auto key = pending.back();
            pending.pop_back();
            Mask a = key.first, b = key.second;
            for (Mask m = a; m; m &= m - 1) {
                int v = __builtin_ctzll(m);
                Mask ca = a & ~bd.closed[v], cb = b & ~(Mask(1) << v);
                split_into_table(ca, cb);
            }
            for (Mask m = b; m; m &= m - 1) {
                int v = __builtin_ctzll(m);
                Mask ca = a & ~(Mask(1) << v), cb = b & ~bd.closed[v];
                split_into_table(ca, cb);
            }
        }
    }
    void split_into_table(Mask a, Mask b) {
        Mask live = a | b;
        while (live) {
            Mask seed = live & (~live + 1);
            Mask comp = bd.flood(seed, a, b);
            live &= ~comp;
            value_of_comp(a & comp, b & comp);
        }
    }
};

int main(int argc, char** argv) {
    if (argc < 8) die("usage: colcert5 h w A B q star out.bin [-S K] [-t log2] [-T log2]");
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    Mask A = std::strtoull(argv[3], nullptr, 10), B = std::strtoull(argv[4], nullptr, 10);
    i64 q0 = parse_dyadic(argv[5]);
    bool s0 = std::atoi(argv[6]) != 0;
    std::string out = argv[7];
    int K = 12, vlog = 22, tlog = 22;
    for (int i = 8; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-S" && i + 1 < argc) K = std::atoi(argv[++i]);
        else if (a == "-t" && i + 1 < argc) vlog = std::atoi(argv[++i]);
        else if (a == "-T" && i + 1 < argc) tlog = std::atoi(argv[++i]);
        else die("unknown argument " + a);
    }
    g_certMode = 1;
    g_start = std::chrono::steady_clock::now();
    Board bd(h, w);
    Cache vc(vlog);
    TT tt(tlog);
    Search sr(bd, vc, tt, K);
    Gen g(bd, sr, K);
    auto lost = [&](const St& k) {
        int r = sr.win(k.a, k.b, k.q, k.s, 0);
        if (r < 0) die("search aborted");
        return r == 0;
    };
    St root = g.reduce(A, B, q0, s0);
    if (!lost(root)) die("root is not a loss for the player to move");

    std::unordered_map<St, std::uint32_t, StHash> index;
    std::vector<St> states{root};
    index.emplace(root, 0);
    std::vector<std::vector<std::pair<int, int>>> replies;
    std::uint64_t edges = 0;
    for (std::size_t i = 0; i < states.size(); ++i) {
        St k = states[i];
        std::vector<std::pair<int, int>> rs;
        if (k.a | k.b) {
            for (auto& [code, full] : g.options(k)) {
                St mid = g.reduce(full.a, full.b, full.q, full.s);
                bool ok = false;
                auto ro = g.options(mid);
                std::vector<St> kids;
                kids.reserve(ro.size());
                for (auto& [rc, f2] : ro) kids.push_back(g.reduce(f2.a, f2.b, f2.q, f2.s));
                for (int pass = 0; pass < 2 && !ok; ++pass) {
                    for (std::size_t j = 0; j < ro.size() && !ok; ++j) {
                        bool known = index.count(kids[j]) > 0;
                        if ((pass == 0) != known) continue;
                        if (lost(kids[j])) {
                            rs.push_back({code, ro[j].first});
                            if (!known) {
                                index.emplace(kids[j], std::uint32_t(states.size()));
                                states.push_back(kids[j]);
                            }
                            ok = true;
                        }
                    }
                }
                if (!ok) die("no winning reply found at a purported losing node");
                ++edges;
            }
        } else if (k.q > 0 || (k.q == 0 && k.s)) {
            die("empty reduced state is not a loss");
        }
        replies.push_back(std::move(rs));
        if ((i & 0x3fff) == 0)
            std::fprintf(stderr, "  checkpoints %zu / %zu, edges %" PRIu64 ", table %zu, %.0fs\n", i, states.size(),
                         edges, g.table.size(), since_start());
    }
    std::fprintf(stderr, "DAG done: %zu checkpoints, %" PRIu64 " edges, table %zu before closure, %.0fs\n",
                 states.size(), edges, g.table.size(), since_start());
    g.close_table();
    std::fprintf(stderr, "table closed: %zu entries, %.0fs\n", g.table.size(), since_start());

    FILE* f = std::fopen(out.c_str(), "wb");
    if (!f) die("cannot open output");
    auto put = [&](const void* p, std::size_t n) { std::fwrite(p, 1, n, f); };
    auto u32 = [&](std::uint32_t x) { put(&x, 4); };
    auto u64 = [&](std::uint64_t x) { put(&x, 8); };
    auto i64w = [&](i64 x) { put(&x, 8); };
    auto u8 = [&](std::uint8_t x) { put(&x, 1); };
    put("COLCERT5", 8);
    u32(h); u32(w); u32(K); u32(SHIFT);
    u64(root.a); u64(root.b); i64w(root.q); u8(root.s);
    u64(g.table.size());
    for (auto& [key, v] : g.table) { u64(key.first); u64(key.second); i64w(v.num); u8(v.star); }
    u64(states.size());
    for (std::size_t i = 0; i < states.size(); ++i) {
        const St& k = states[i];
        u64(k.a); u64(k.b); i64w(k.q); u8(k.s);
        std::uint16_t n = std::uint16_t(replies[i].size());
        put(&n, 2);
        for (auto& [a, b] : replies[i]) {
            std::int16_t x = std::int16_t(a), y = std::int16_t(b);
            put(&x, 2); put(&y, 2);
        }
    }
    std::fclose(f);
    std::printf("certificate %s: %zu checkpoints, %" PRIu64 " edges, %zu table entries, K=%d, %.0fs\n", out.c_str(),
                states.size(), edges, g.table.size(), K, since_start());
    return 0;
}
