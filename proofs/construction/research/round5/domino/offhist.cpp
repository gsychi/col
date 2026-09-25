// Histogram of value(G^{R,y}) - F over parity-class positions G (Blue on X, White on Y, >= 1
// White stone) and White-legal majority cells y, split by deg(y) and by
// k = number of y's minority neighbours that are Blue-legal in G (they become Blue-only).
// ./offhist H W pmax qmax
#include "../center/colcore_fast.hpp"
#include <map>
#include <tuple>
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    int pmax = std::atoi(argv[3]), qmax = std::atoi(argv[4]);
    setup(h, w);
    std::vector<int> maj, mnr; u64 majm = 0;
    for (int v = 0; v < N; ++v) { if ((v / W + v % W) % 2) mnr.push_back(v); else { maj.push_back(v); majm |= u64{1} << v; } }
    std::map<std::tuple<int,int,std::string>, long> hist;
    std::vector<int> P, Q;
    auto eval = [&]() {
        if (Q.empty()) return;
        u64 blue = 0, white = 0;
        for (int x : P) blue |= u64{1} << x;
        for (int y : Q) white |= u64{1} << y;
        u64 a, b; perms_from_stones(blue, white, a, b);
        u64 occ = blue | white;
        i64 F = (i64)(__builtin_popcountll(majm & ~occ) - __builtin_popcountll(fullmask() & ~majm & ~occ)) * ONE;
        for (u64 z = b & majm; z; z &= z - 1) {
            int y = __builtin_ctzll(z); u64 yb = u64{1} << y;
            Val o = value(a & ~yb, b & ~NB[y]);
            int deg = __builtin_popcountll(NB[y]) - 1;
            int k = __builtin_popcountll(NB[y] & ~yb & a);
            hist[{deg, k, fmt(Val{o.x - F, o.e})}]++;
        }
    };
    auto recQ = [&](auto&& self, std::size_t i) -> void {
        eval();
        if ((int)Q.size() == qmax) return;
        for (std::size_t j = i; j < mnr.size(); ++j) { Q.push_back(mnr[j]); self(self, j + 1); Q.pop_back(); }
    };
    auto recP = [&](auto&& self, std::size_t i) -> void {
        recQ(recQ, 0);
        if ((int)P.size() == pmax) return;
        for (std::size_t j = i; j < maj.size(); ++j) { P.push_back(maj[j]); self(self, j + 1); P.pop_back(); }
    };
    recP(recP, 0);
    for (auto& [key, cnt] : hist)
        std::printf("%dx%d deg(y)=%d k=%d: G^{R,y}-F = %s  x%ld\n", h, w, std::get<0>(key), std::get<1>(key), std::get<2>(key).c_str(), cnt);
}
