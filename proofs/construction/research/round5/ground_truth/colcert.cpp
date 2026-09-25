// colcert: emit a plain response-DAG certificate that the player to move LOSES
// in  G + q (+*),  where G = (A,B) is a Col permission position.
//
// The folded outcome search of colout.cpp is used only to FIND replies. The
// emitted certificate lists full-board states (no folding, no component
// values) and is meant to be replayed by an independent search-free checker:
//   * star = 0 and h*w <= 30: number_certificates.verify (existing checker),
//     format {height,width,root:[a,b,qn,qd],nodes:[[a,b,qn,qd,[[first,reply],...]]],edges}
//   * otherwise: verify_cert.py in this directory, format with an extra star
//     field: root [a,b,qn,qd,s], nodes [[a,b,qn,qd,s,[[first,reply],...]]].
// States are in the mover's frame (a = cells of the player to move). Move
// codes: cell index v >= 0; -1 = move in the number; -2 = take the star.
//
// Usage: colcert h w A B q star out.json [-S smax] [-t log2] [-T log2]
//   q is the number in the mover's frame (e.g. to certify G <= r with Blue
//   first, pass A B and q = -r).
#include "colcore.h"

#include <unordered_set>

#define main colout_main_unused
#include "colout.cpp"
#undef main

struct Key {
    Mask a, b;
    i64 q;
    bool s;
    bool operator==(const Key& o) const { return a == o.a && b == o.b && q == o.q && s == o.s; }
};
struct KeyHash {
    std::size_t operator()(const Key& k) const {
        return std::size_t(Cache::hash(k.a ^ (Mask(k.s) << 63), k.b) ^ (Mask(k.q) * 0x9E3779B97F4A7C15ULL));
    }
};

static void dyadic_parts(i64 q, long long& num, long long& den) {
    if (q == 0) { num = 0; den = 1; return; }
    int sh = SHIFT;
    i64 x = q;
    while (sh > 0 && (x & 1) == 0) { x >>= 1; --sh; }
    num = x;
    den = 1LL << sh;
}

int main(int argc, char** argv) {
    if (argc < 8) die("usage: colcert h w A B q star out.json [-S smax] [-t log2] [-T log2]");
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    Mask A = std::strtoull(argv[3], nullptr, 10), B = std::strtoull(argv[4], nullptr, 10);
    i64 q0 = parse_dyadic(argv[5]);
    bool s0 = std::atoi(argv[6]) != 0;
    std::string out = argv[7];
    int smax = 14, vlog = 20, tlog = 20;
    for (int i = 8; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-S" && i + 1 < argc) smax = std::atoi(argv[++i]);
        else if (a == "-t" && i + 1 < argc) vlog = std::atoi(argv[++i]);
        else if (a == "-T" && i + 1 < argc) tlog = std::atoi(argv[++i]);
    }
    Board bd(h, w);
    Cache vc(vlog);
    TT tt(tlog);
    Search sr(bd, vc, tt, smax);
    if (sr.win(A, B, q0, s0, 0) != 0) die("root is not a loss for the player to move");

    auto options = [&](const Key& k) {
        // (code, child) for every option of the player to move in state k.
        std::vector<std::pair<int, Key>> o;
        for (Mask m = k.a; m; m &= m - 1) {
            int v = __builtin_ctzll(m);
            o.push_back({v, Key{k.b & ~(Mask(1) << v), k.a & ~bd.closed[v], -k.q, k.s}});
        }
        i64 ql;
        if (left_option(k.q, ql)) o.push_back({-1, Key{k.b, k.a, -ql, k.s}});
        if (k.s) o.push_back({-2, Key{k.b, k.a, -k.q, false}});
        return o;
    };

    std::vector<Key> states{Key{A, B, q0, s0}};
    std::unordered_set<Key, KeyHash> seen{states[0]};
    std::vector<std::vector<std::pair<int, int>>> replies;
    std::uint64_t edges = 0;
    for (std::size_t i = 0; i < states.size(); ++i) {
        Key k = states[i];
        std::vector<std::pair<int, int>> rs;
        for (auto& [code, mid] : options(k)) {
            // Find a reply after which the first player (to move again) loses.
            bool ok = false;
            auto ro = options(mid);
            // Prefer replies whose result is already in the certificate.
            for (int pass = 0; pass < 2 && !ok; ++pass) {
                for (auto& [rc, child] : ro) {
                    bool known = seen.count(child) > 0;
                    if (pass == 0 && !known) continue;
                    if (pass == 1 && known) continue;
                    if (sr.win(child.a, child.b, child.q, child.s, 0) == 0) {
                        rs.push_back({code, rc});
                        if (!known) { seen.insert(child); states.push_back(child); }
                        ok = true;
                        break;
                    }
                }
            }
            if (!ok) die("no winning reply found at a purported losing node");
            ++edges;
        }
        replies.push_back(std::move(rs));
        if ((i & 0xffff) == 0)
            std::fprintf(stderr, "  certificate nodes %zu / %zu, edges %" PRIu64 "\n", i, states.size(), edges);
    }
    bool legacy = !s0 && h * w <= 30;
    for (auto& k : states) if (k.s) legacy = false;
    FILE* f = std::fopen(out.c_str(), "w");
    if (!f) die("cannot open output");
    long long qn, qd;
    dyadic_parts(q0, qn, qd);
    std::fprintf(f, "{\"height\":%d,\"width\":%d,\"schema\":\"%s\",\"root\":[%llu,%llu,%lld,%lld%s],\"nodes\":[", h, w,
                 legacy ? "canonical-dyadic-response-dag-v1" : "dyadic-star-response-dag-v1",
                 (unsigned long long)A, (unsigned long long)B, qn, qd, legacy ? "" : (s0 ? ",1" : ",0"));
    for (std::size_t i = 0; i < states.size(); ++i) {
        const Key& k = states[i];
        dyadic_parts(k.q, qn, qd);
        std::fprintf(f, "%s[%llu,%llu,%lld,%lld,", i ? "," : "", (unsigned long long)k.a,
                     (unsigned long long)k.b, qn, qd);
        if (!legacy) std::fprintf(f, "%d,", k.s ? 1 : 0);
        std::fprintf(f, "[");
        for (std::size_t j = 0; j < replies[i].size(); ++j)
            std::fprintf(f, "%s[%d,%d]", j ? "," : "", replies[i][j].first, replies[i][j].second);
        std::fprintf(f, "]]");
    }
    std::fprintf(f, "],\"edges\":%" PRIu64 "}\n", edges);
    std::fclose(f);
    std::printf("certificate %s: %zu checkpoints, %" PRIu64 " edges, schema %s\n", out.c_str(), states.size(),
                edges, legacy ? "legacy" : "star");
    return 0;
}
