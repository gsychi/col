// For every half-turn antisymmetric position on an odd x odd board (Blue to
// move), record the state of the centre and its four neighbours and the value
// (0 or *).  Report, for each local pattern, how many positions are 0 and *.
// A pattern with both 0 and * means the value is NOT determined locally.
#include "colcore_fast.hpp"
#include <map>
#include <string>
static void perms(u64 blue, u64 white, u64& a, u64& b) {
    a = b = 0; u64 occ = blue | white;
    for (int v = 0; v < N; ++v) {
        if ((occ >> v) & 1) continue;
        if (!(NB[v] & blue)) a |= u64{1} << v;
        if (!(NB[v] & white)) b |= u64{1} << v;
    }
}
static char st(u64 blue, u64 white, u64 a, u64 b, int v) {
    u64 m = u64{1} << v;
    return (blue & m) ? 'B' : (white & m) ? 'W' : ((a & m) && (b & m)) ? 'o' : (a & m) ? 'b' : (b & m) ? 'w' : '.';
}
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    setup(h, w);
    int c = N / 2, r0 = c / W, c0 = c % W;
    int up = (r0 - 1) * W + c0, dn = (r0 + 1) * W + c0, lf = r0 * W + c0 - 1, rt = r0 * W + c0 + 1;
    std::vector<int> reps;
    for (int v = 0; v < N; ++v) if (v < rho(v)) reps.push_back(v);
    std::map<std::string, std::pair<long,long>> tally;  // pattern -> (zero, star)
    std::map<std::string, std::string> example_star, example_zero;
    auto visit = [&](u64 blue, u64 white) {
        u64 a, b; perms(blue, white, a, b);
        Val e = value(a, b);
        std::string key; key += st(blue, white, a, b, c); key += ':';
        key += st(blue, white, a, b, up); key += st(blue, white, a, b, dn);
        key += st(blue, white, a, b, lf); key += st(blue, white, a, b, rt);
        auto& t = tally[key];
        std::string ex;
        for (int r = 0; r < H; ++r) { for (int cc = 0; cc < W; ++cc) ex += st(blue, white, a, b, r * W + cc); if (r + 1 < H) ex += '/'; }
        if (e.e) { ++t.second; example_star.emplace(key, ex); } else { ++t.first; example_zero.emplace(key, ex); }
    };
    auto dfs = [&](auto&& self, std::size_t i, u64 blue, u64 white) -> void {
        if (i == reps.size()) { visit(blue, white); return; }
        self(self, i + 1, blue, white);
        int v = reps[i];
        for (int side = 0; side < 2; ++side) {
            int bv = side ? rho(v) : v, wv = rho(bv);
            u64 bb = u64{1} << bv, wb = u64{1} << wv;
            if (NB[bv] & ~bb & blue) continue;
            if (NB[wv] & ~wb & white) continue;
            self(self, i + 1, blue | bb, white | wb);
        }
    };
    dfs(dfs, 0, 0, 0);
    long mixed = 0;
    std::printf("%dx%d  pattern = centre:up,down,left,right   zero/star\n", h, w);
    for (auto& [k, t] : tally) {
        if (k[0] != 'o') continue;  // centre not shared -> always 0 (dead) or occupied impossible
        bool mix = t.first && t.second; mixed += mix;
        std::printf("  %s  %ld/%ld%s\n", k.c_str(), t.first, t.second, mix ? "  MIXED" : "");
        if (mix) std::printf("      zero: %s\n      star: %s\n", example_zero[k].c_str(), example_star[k].c_str());
    }
    std::printf("mixed patterns: %ld\n", mixed);
}
