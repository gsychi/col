// Enumerate every half-turn antisymmetric position (Blue stones S, White
// stones rho(S), S independent, S and rho(S) disjoint) on an odd x odd board,
// Blue to move.  For each: value, value of the component containing the
// centre, and a structural description of that component.  Prints summary
// statistics and examples of positions whose value is * (Blue to move wins).
#include "colcore_fast.hpp"
#include <map>
#include <algorithm>

static void perms(u64 blue, u64 white, u64& a, u64& b) {
    a = b = 0; u64 occ = blue | white;
    for (int v = 0; v < N; ++v) {
        if ((occ >> v) & 1) continue;
        if (!(NB[v] & blue)) a |= u64{1} << v;
        if (!(NB[v] & white)) b |= u64{1} << v;
    }
}
static u64 comp_of(u64 a, u64 b, int v0) {
    u64 live = a | b, comp = u64{1} << v0, fr = comp;
    while (fr) {
        int v = __builtin_ctzll(fr); fr &= fr - 1;
        u64 usable = 0;
        if ((a >> v) & 1) usable |= a;
        if ((b >> v) & 1) usable |= b;
        u64 nb = NB[v] & usable & live & ~comp;
        comp |= nb; fr |= nb;
    }
    return comp;
}
static void showpos(u64 blue, u64 white, u64 a, u64 b) {
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int v = r * W + c; u64 m = u64{1} << v;
            char ch = (blue & m) ? 'B' : (white & m) ? 'W' : ((a & m) && (b & m)) ? 'o' : (a & m) ? 'b' : (b & m) ? 'w' : '.';
            std::putchar(ch);
        }
        std::putchar(r + 1 < H ? '/' : ' ');
    }
}
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    int maxshow = argc > 3 ? std::atoi(argv[3]) : 10;
    setup(h, w);
    int c = N / 2;
    std::vector<int> reps;
    for (int v = 0; v < N; ++v) if (v < rho(v)) reps.push_back(v);
    long total = 0, star = 0, reduction_fail = 0, star_isolated = 0, star_nonisolated = 0, zero_isolated_live = 0;
    std::map<int, long> star_by_compsize, all_by_compsize;
    int shown = 0;
    auto visit = [&](u64 blue, u64 white) {
        u64 a, b; perms(blue, white, a, b);
        ++total;
        Val e = value(a, b);
        bool centre_live = ((a | b) >> c) & 1;
        Val ec{0, 0}; int csize = 0; u64 comp = 0;
        if (centre_live) { comp = comp_of(a, b, c); ec = value(a & comp, b & comp); csize = __builtin_popcountll(comp); }
        if (!(ec.x == e.x && ec.e == e.e)) ++reduction_fail;
        bool isolated_shared = centre_live && csize == 1 && ((a >> c) & 1) && ((b >> c) & 1);
        all_by_compsize[csize]++;
        if (e.x == 0 && e.e == 1) {
            ++star; star_by_compsize[csize]++;
            if (isolated_shared) ++star_isolated; else {
                ++star_nonisolated;
                if (shown < maxshow) { ++shown; std::printf("STAR non-isolated centre comp size %d: ", csize); showpos(blue, white, a, b); std::printf("\n"); }
            }
        } else if (isolated_shared) ++zero_isolated_live;
        if (!(e.x == 0 && (e.e == 0 || e.e == 1))) { std::printf("NOT 0/*: %s ", fmt(e).c_str()); showpos(blue, white, a, b); std::printf("\n"); }
    };
    auto dfs = [&](auto&& self, std::size_t i, u64 blue, u64 white) -> void {
        if (i == reps.size()) { visit(blue, white); return; }
        self(self, i + 1, blue, white);
        int v = reps[i];
        for (int side = 0; side < 2; ++side) {
            int bv = side ? rho(v) : v, wv = rho(bv);
            u64 bb = u64{1} << bv, wb = u64{1} << wv;
            if (NB[bv] & ~bb & blue) continue;       // Blue stones independent
            if (NB[wv] & ~wb & white) continue;      // White stones independent
            if (NB[bv] & wb) { /* adjacent B,W allowed */ }
            self(self, i + 1, blue | bb, white | wb);
        }
    };
    dfs(dfs, 0, 0, 0);
    std::printf("%dx%d antisymmetric positions: %ld; value *: %ld (isolated live centre %ld, other %ld); "
                "isolated live centre but value 0: %ld; reduction failures: %ld\n",
                h, w, total, star, star_isolated, star_nonisolated, zero_isolated_live, reduction_fail);
    std::printf("centre-component size: count(all) / count(star):");
    for (auto& [s, n] : all_by_compsize) std::printf(" %d:%ld/%ld", s, n, star_by_compsize[s]);
    std::printf("\nmemo %zu\n", memo.size());
}
