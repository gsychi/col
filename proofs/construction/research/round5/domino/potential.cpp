// Anti-parity potential test.  Class: White stones only on majority cells, Blue stones anywhere
// (independent), at least one Blue stone on a minority cell.
//   Phi = #(free minority cells Blue-legal) - #(free majority cells White-legal)
// Question: is value <= Phi on the whole class?  (Minority opening: Phi = -2;
// Blue minority w + White majority x adjacent: Phi = -1.)
// ./potential H W bmax wmax
#include "../center/colcore_fast.hpp"
#include <array>
#include <map>
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    int bmax = std::atoi(argv[3]), wmax = std::atoi(argv[4]);
    setup(h, w);
    u64 majm = 0; std::vector<int> maj, all;
    for (int v = 0; v < N; ++v) { all.push_back(v); if ((v / W + v % W) % 2 == 0) { maj.push_back(v); majm |= u64{1} << v; } }
    std::map<std::pair<int,int>, std::array<long, 3>> tally;  // (#Blue majority stones, #White) -> le, eq, total
    int shown = 0;
    std::vector<int> P, Q;
    auto eval = [&]() {
        u64 blue = 0, white = 0;
        for (int x : P) blue |= u64{1} << x;
        for (int y : Q) white |= u64{1} << y;
        if (!(blue & ~majm)) return;
        u64 a, b; perms_from_stones(blue, white, a, b);
        i64 Phi = (i64)(__builtin_popcountll(a & ~majm) - __builtin_popcountll(b & majm)) * ONE;
        Val g = value(a, b);
        bool le = g.e == 0 ? g.x <= Phi : g.x < Phi, eq = g.e == 0 && g.x == Phi;
        auto& t = tally[{__builtin_popcountll(blue & majm), (int)Q.size()}]; t[0] += le; t[1] += eq; t[2]++;
        if (!le && shown < 12) { ++shown; show(a, b); std::printf("  value %s > Phi %lld\n", fmt(g).c_str(), (long long)(Phi / ONE)); }
    };
    auto recQ = [&](auto&& self, std::size_t i, u64 blue, u64 white) -> void {
        eval();
        if ((int)Q.size() == wmax) return;
        for (std::size_t j = i; j < maj.size(); ++j) {
            int y = maj[j]; u64 yb = u64{1} << y;
            if (blue & yb) continue;
            Q.push_back(y); self(self, j + 1, blue, white | yb); Q.pop_back();
        }
    };
    auto recP = [&](auto&& self, std::size_t i, u64 blue) -> void {
        recQ(recQ, 0, blue, 0);
        if ((int)P.size() == bmax) return;
        for (std::size_t j = i; j < all.size(); ++j) {
            int x = all[j]; u64 xb = u64{1} << x;
            if (NB[x] & ~xb & blue) continue;
            P.push_back(x); self(self, j + 1, blue | xb); P.pop_back();
        }
    };
    recP(recP, 0, 0);
    for (auto& [k, t] : tally)
        std::printf("%dx%d Blue-majority-stones %d, White stones %d: value<=Phi %ld, ==Phi %ld, of %ld\n", h, w, k.first, k.second, t[0], t[1], t[2]);
}
