// Extended class C2: Blue stones on majority only, White stones anywhere (independent),
// at least one White stone on a minority cell.  Candidate count
//   V2 = #free majority - #free White-legal minority
// (free majority cells are all Blue-legal in C2).  Report how often value == V2,
// value >= V2, value <= V2, by the number of White majority stones.
// ./class2 H W pmax qmax
#include "/workspace/proofs/construction/research/round5/center/colcore_fast.hpp"
#include <array>
#include <map>
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    int pmax = std::atoi(argv[3]), qmax = std::atoi(argv[4]);
    setup(h, w);
    u64 majm = 0;
    std::vector<int> maj, all;
    for (int v = 0; v < N; ++v) { all.push_back(v); if ((v / W + v % W) % 2 == 0) { maj.push_back(v); majm |= u64{1} << v; } }
    std::map<int, std::array<long, 4>> tally;  // key: #White majority stones -> eq, ge, le, total
    int shown = 0; long lowOK = 0, lowTot = 0; int lshown = 0;
    std::vector<int> P, Q;
    auto eval = [&]() {
        u64 blue = 0, white = 0;
        for (int x : P) blue |= u64{1} << x;
        for (int y : Q) white |= u64{1} << y;
        if (!(white & ~majm)) return;
        u64 a, b; perms_from_stones(blue, white, a, b);
        u64 occ = blue | white, full = fullmask();
        u64 freeMaj = majm & ~occ, freeMinW = b & ~majm;
        i64 V2 = (i64)(__builtin_popcountll(freeMaj) - __builtin_popcountll(freeMinW)) * ONE;
        Val g = value(a, b);
        i64 pen = 0; for (u64 t = white & majm; t; t &= t - 1) { int y = __builtin_ctzll(t); pen += (__builtin_popcountll(NB[y]) - 1 - 2); }
        i64 L2 = V2 - pen * ONE;
        bool lok = g.e == 0 ? g.x >= L2 : g.x > L2;
        lowOK += lok; lowTot++;
        if (!lok && lshown < 8) { ++lshown; show(a, b); std::printf("  value %s < V2 - pen = %lld\n", fmt(g).c_str(), (long long)(L2 / ONE)); }
        bool eq = g.e == 0 && g.x == V2, ge = g.e == 0 ? g.x >= V2 : g.x > V2, le = g.e == 0 ? g.x <= V2 : g.x < V2;
        int k = __builtin_popcountll(white & majm);
        auto& t = tally[k]; t[0] += eq; t[1] += ge; t[2] += le; t[3]++;
        if (false) { ++shown; show(a, b); std::printf("  value %s < V2 %lld\n", fmt(g).c_str(), (long long)(V2 / ONE)); }
        (void)full;
    };
    auto recQ = [&](auto&& self, std::size_t i, u64 white) -> void {
        eval();
        if ((int)Q.size() == qmax) return;
        u64 blue = 0; for (int x : P) blue |= u64{1} << x;
        for (std::size_t j = i; j < all.size(); ++j) {
            int y = all[j]; u64 yb = u64{1} << y;
            if ((blue & yb) || (NB[y] & ~yb & white)) continue;
            Q.push_back(y); self(self, j + 1, white | yb); Q.pop_back();
        }
    };
    auto recP = [&](auto&& self, std::size_t i) -> void {
        recQ(recQ, 0, 0);
        if ((int)P.size() == pmax) return;
        for (std::size_t j = i; j < maj.size(); ++j) { P.push_back(maj[j]); self(self, j + 1); P.pop_back(); }
    };
    recP(recP, 0);
    std::printf("lower candidate value >= V2 - sum(deg(y)-2): %ld / %ld\n", lowOK, lowTot);
    for (auto& [k, t] : tally)
        std::printf("%dx%d White majority stones %d: value==V2 %ld, >= %ld, <= %ld, of %ld\n", h, w, k, t[0], t[1], t[2], t[3]);
}
