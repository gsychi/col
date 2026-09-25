// certgen: emit a Blue-first-losing response DAG for T - q + s*, i.e. a
// certificate of the claim T <= q + s* (discovery tool; the Python verifier
// rechecks every edge without search).
//
// usage: certgen h w PATTERN|A,B q s out.json [maxlog2]
//   q = dyadic like -1/2 or 0, s = 0 or 1.
// Node format: [A, B, pnum, pden, star, [[move, reply], ...]] with Blue to
// move; moves are cell indices, -1 = move in the auxiliary number, -2 = star.
#include <chrono>
#include <cinttypes>
#include <fstream>
#include <iostream>
#include <unordered_map>

#include "colcgt.hpp"
using namespace cc;

struct Key {
    u64 a, b;
    i64 p;
    bool s;
    bool operator==(const Key& o) const { return a == o.a && b == o.b && p == o.p && s == o.s; }
};
struct KeyHash {
    std::size_t operator()(const Key& k) const {
        u64 x = k.a * 0x9E3779B97F4A7C15ULL ^ (k.b + 0x632BE59BD9B4E019ULL) * 0xC2B2AE3D27D4EB4FULL ^
                (u64(k.p) * 0x94d049bb133111ebULL) ^ (k.s ? 0x5555 : 0);
        x ^= x >> 31;
        x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 29;
        return std::size_t(x);
    }
};

int main(int argc, char** argv) {
    if (argc < 7) die("usage: certgen h w PATTERN|A,B q s out.json [maxlog2]");
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    Board bd(h, w);
    u64 A, B;
    std::string spec = argv[3];
    if (spec.find(',') != std::string::npos && spec.find_first_of("obw.") == std::string::npos) {
        auto k = spec.find(',');
        A = std::stoull(spec.substr(0, k));
        B = std::stoull(spec.substr(k + 1));
    } else
        parse_rows(bd, spec, A, B);
    i64 q = parse_num(argv[4]);
    bool s = std::atoi(argv[5]) != 0;
    std::string out = argv[6];
    int maxlog = argc > 7 ? std::atoi(argv[7]) : 25;
    Table memo(maxlog);
    Canon canon;
    Engine eng(bd, memo, canon);
    auto t0 = std::chrono::steady_clock::now();
    auto loses = [&](const Key& k) { return vle0(eng.with_aux(k.a, k.b, k.p, k.s)); };
    Key root{A, B, -q, s};
    Val rv = eng.position(A, B);
    std::fprintf(stderr, "tile value %s, claim <= %s%s\n", valstr(rv).c_str(), numstr(q).c_str(), s ? "+*" : "");
    if (!loses(root)) die("claim false: tile value " + valstr(rv));
    std::vector<Key> nodes{root};
    std::unordered_map<Key, int, KeyHash> index;
    index.emplace(root, 0);
    std::vector<std::vector<std::pair<int, int>>> replies;
    u64 edges = 0;
    for (std::size_t i = 0; i < nodes.size(); ++i) {
        Key k = nodes[i];
        std::vector<std::pair<int, int>> rs;
        std::vector<std::pair<int, Key>> mids;
        for (u64 m = k.a; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            mids.push_back({v, Key{k.a & ~bd.closed[v], k.b & ~(u64(1) << v), k.p, k.s}});
        }
        i64 pl;
        if (left_of_number(k.p, pl)) mids.push_back({-1, Key{k.a, k.b, pl, k.s}});
        if (k.s) mids.push_back({-2, Key{k.a, k.b, k.p, false}});
        for (auto& [mv, mid] : mids) {
            // candidate White replies
            std::vector<std::pair<int, Key>> cands;
            for (u64 m = mid.b; m; m &= m - 1) {
                int u = __builtin_ctzll(m);
                cands.push_back({u, Key{mid.a & ~(u64(1) << u), mid.b & ~bd.closed[u], mid.p, mid.s}});
            }
            i64 pr;
            if (right_of_number(mid.p, pr)) cands.push_back({-1, Key{mid.a, mid.b, pr, mid.s}});
            if (mid.s) cands.push_back({-2, Key{mid.a, mid.b, mid.p, false}});
            int chosen = -99;
            Key ck{};
            // prefer an existing checkpoint, then the first losing child
            for (auto& [u, c] : cands)
                if (index.count(c) && loses(c)) {
                    chosen = u;
                    ck = c;
                    break;
                }
            if (chosen == -99)
                for (auto& [u, c] : cands)
                    if (loses(c)) {
                        chosen = u;
                        ck = c;
                        break;
                    }
            if (chosen == -99) die("no White reply at a purported losing checkpoint");
            if (!index.count(ck)) {
                index.emplace(ck, int(nodes.size()));
                nodes.push_back(ck);
            }
            rs.push_back({mv, chosen});
            ++edges;
        }
        replies.push_back(std::move(rs));
    }
    std::ofstream os(out);
    if (!os) die("cannot open output");
    auto frac = [&](i64 p, i64& pn, i64& pd) { numfrac(p, pn, pd); };
    i64 rn, rd;
    frac(root.p, rn, rd);
    os << "{\"format\":\"col-bridge-dag-v1\",\"height\":" << h << ",\"width\":" << w << ",\"root\":[" << root.a << ","
       << root.b << "," << rn << "," << rd << "," << (root.s ? 1 : 0) << "],\"nodes\":[";
    for (std::size_t i = 0; i < nodes.size(); ++i) {
        if (i) os << ",";
        i64 pn, pd;
        frac(nodes[i].p, pn, pd);
        os << "[" << nodes[i].a << "," << nodes[i].b << "," << pn << "," << pd << "," << (nodes[i].s ? 1 : 0) << ",[";
        for (std::size_t j = 0; j < replies[i].size(); ++j) {
            if (j) os << ",";
            os << "[" << replies[i][j].first << "," << replies[i][j].second << "]";
        }
        os << "]]";
    }
    os << "],\"edges\":" << edges << "}\n";
    double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    std::printf("nodes=%zu edges=%" PRIu64 " seconds=%.2f memo=%zu\n", nodes.size(), edges, secs, memo.used);
    return 0;
}
