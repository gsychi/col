// Test the "parity formula" on parity-respecting positions:
//   Blue stones P subset of majority cells, White stones Q subset of minority cells
//   (each colour independent automatically), formula F = 1 - |P| + |Q|.
// Enumerates all such positions with |P| <= pmax, |Q| <= qmax (up to nothing: brute force),
// and reports agreement counts by (|P|,|Q|) and the first few counterexamples.
// ./parity_formula H W pmax qmax
#include "../center/colcore_fast.hpp"
#include <map>
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    int pmax = std::atoi(argv[3]), qmax = std::atoi(argv[4]);
    setup(h, w);
    std::vector<int> maj, mnr;
    for (int v = 0; v < N; ++v) ((v / W + v % W) % 2 ? mnr : maj).push_back(v);
    std::map<std::pair<int,int>, std::pair<long,long>> tally;  // (ok, total)
    int shown = 0;
    std::vector<int> P, Q;
    auto eval = [&]() {
        u64 blue = 0, white = 0;
        for (int x : P) blue |= u64{1} << x;
        for (int y : Q) white |= u64{1} << y;
        u64 a, b; perms_from_stones(blue, white, a, b);
        Val g = value(a, b);
        i64 F = (1 - (i64)P.size() + (i64)Q.size()) * ONE;
        bool ok = g.e == 0 && g.x == F;
        auto& t = tally[{(int)P.size(), (int)Q.size()}];
        t.second++; if (ok) t.first++;
        if (!ok && shown < 25 && Q.size() >= 1) {
            ++shown; show(a, b);
            std::printf("  |P|=%zu |Q|=%zu value %s formula %lld\n", P.size(), Q.size(), fmt(g).c_str(), (long long)(F / ONE));
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
    for (auto& [k, t] : tally) std::printf("%dx%d |P|=%d |Q|=%d: formula holds %ld / %ld\n", h, w, k.first, k.second, t.first, t.second);
}
