// Parity formula on general grid regions (a rectangle with some cells deleted).
// X = cells with r+c even, Y = r+c odd.  Class: Blue stones in X, White stones in Y, >= 1 White stone.
// Formula F = #free X - #free Y.  Reports agreement counts.
// ./pf_regions H W holesMask pmax qmax
#include "../center/colcore_fast.hpp"
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    u64 holes = std::strtoull(argv[3], nullptr, 10);
    int pmax = std::atoi(argv[4]), qmax = std::atoi(argv[5]);
    setup(h, w);
    u64 cells = fullmask() & ~holes;
    std::vector<int> X, Y; u64 Xm = 0;
    for (int v = 0; v < N; ++v) if (cells >> v & 1) { if ((v / W + v % W) % 2 == 0) { X.push_back(v); Xm |= u64{1} << v; } else Y.push_back(v); }
    long ok = 0, tot = 0, ge = 0, le = 0; int shown = 0;
    std::vector<int> P, Q;
    auto eval = [&]() {
        if (Q.empty()) return;
        u64 blue = 0, white = 0;
        for (int x : P) blue |= u64{1} << x;
        for (int y : Q) white |= u64{1} << y;
        u64 a, b; perms_from_stones(blue, white, a, b);
        a &= cells; b &= cells;
        u64 occ = blue | white;
        i64 F = (i64)(__builtin_popcountll(Xm & ~occ) - __builtin_popcountll(cells & ~Xm & ~occ)) * ONE;
        Val g = value(a, b);
        ++tot; if (g.e == 0 && g.x == F) ++ok;
        if (g.e == 0 ? g.x >= F : g.x > F) ++ge;
        if (g.e == 0 ? g.x <= F : g.x < F) ++le;
        if (!(g.e == 0 && g.x == F) && shown < 8) { ++shown; show(a, b); std::printf("  value %s formula %lld\n", fmt(g).c_str(), (long long)(F / ONE)); }
    };
    auto recQ = [&](auto&& self, std::size_t i) -> void {
        eval();
        if ((int)Q.size() == qmax) return;
        for (std::size_t j = i; j < Y.size(); ++j) { Q.push_back(Y[j]); self(self, j + 1); Q.pop_back(); }
    };
    auto recP = [&](auto&& self, std::size_t i) -> void {
        recQ(recQ, 0);
        if ((int)P.size() == pmax) return;
        for (std::size_t j = i; j < X.size(); ++j) { P.push_back(X[j]); self(self, j + 1); P.pop_back(); }
    };
    recP(recP, 0);
    std::printf("%dx%d holes=%llu |X|=%zu |Y|=%zu: formula holds %ld/%ld (value>=F %ld, value<=F %ld)\n",
                h, w, (unsigned long long)holes, X.size(), Y.size(), ok, tot, ge, le);
}
