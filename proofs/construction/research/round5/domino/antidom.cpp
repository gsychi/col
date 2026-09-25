// Domination test in the parity class (Blue stones on majority, White on minority, >= 1 White
// stone), F = 1 - |P| + |Q|:
//   (W) every White off-parity move y (majority) has value(G^{R,y}) >= F + 1
//   (B) every Blue off-parity move z (minority) has value(G^{L,z}) <= F - 1
// If both hold on the whole class, the parity formula follows by induction (see PROOF_ATTEMPTS.md).
// ./dominate H W pmax qmax [q0]   (q0 = minimum number of White stones, default 1)
#include "/workspace/proofs/construction/research/round5/center/colcore_fast.hpp"
static bool geq(Val g, i64 F) { return g.e == 0 ? g.x >= F : g.x > F; }
static bool leq(Val g, i64 F) { return g.e == 0 ? g.x <= F : g.x < F; }
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    int pmax = std::atoi(argv[3]), qmax = std::atoi(argv[4]);
    int q0 = argc > 5 ? std::atoi(argv[5]) : 1;
    setup(h, w);
    std::vector<int> maj, mnr; u64 majm = 0;
    for (int v = 0; v < N; ++v) { if ((v / W + v % W) % 2) mnr.push_back(v); else { maj.push_back(v); majm |= u64{1} << v; } }
    long nAllW = 0, nNoZ = 0, nW = 0, okW = 0, nB = 0, okB = 0, nPF = 0, okPF = 0;
    int shown = 0;
    std::vector<int> P, Q;
    auto eval = [&]() {
        if ((int)Q.size() < q0) return;
        u64 blue = 0, white = 0;
        for (int x : P) blue |= u64{1} << x;
        for (int y : Q) white |= u64{1} << y;
        i64 F = (1 - (i64)P.size() + (i64)Q.size()) * ONE;
        u64 a, b; perms_from_stones(blue, white, a, b);
        Val g = value(a, b); ++nPF; if (g.e == 0 && g.x == F) ++okPF;
        for (u64 z = b & majm; z; z &= z - 1) {
            int y = __builtin_ctzll(z); u64 yb = u64{1} << y;
            u64 a1 = a & ~yb, b1 = b & ~NB[y]; ++nW;
            bool some = false, all = true; int cnt = 0;
            for (u64 s = a1 & NB[y] & ~yb; s; s &= s - 1) {
                int zc = __builtin_ctzll(s); u64 zb = u64{1} << zc; ++cnt;
                Val o = value(a1 & ~NB[zc], b1 & ~zb);
                bool ok = o.e == 0 ? o.x > F - ONE : o.x >= F - ONE;   // o |> F-1
                if (ok) some = true; else all = false;
                if (!ok && shown < 15) { ++shown; show(a, b); std::printf("  F=%lld White (%d,%d), Blue (%d,%d) -> %s\n", (long long)(F / ONE), y / W, y % W, zc / W, zc % W, fmt(o).c_str()); }
            }
            if (some) ++okW;
            if (cnt && all) ++nAllW;
            if (!cnt) ++nNoZ;
        }
        for (u64 t = a & ~majm; t; t &= t - 1) {
            int zc = __builtin_ctzll(t); u64 zb = u64{1} << zc;
            Val o = value(a & ~NB[zc], b & ~zb); ++nB;
            if (leq(o, F - ONE)) ++okB;
            else if (false) { ++shown; show(a, b); std::printf("  F=%lld Blue off-parity (%d,%d) -> %s\n", (long long)(F / ONE), zc / W, zc % W, fmt(o).c_str()); }
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
    std::printf("%dx%d: PF %ld/%ld; White off-parity y: some Blue-only nbr z with G^{y,z} |> F-1: %ld/%ld, all such z: %ld, no such z: %ld\n", h, w, okPF, nPF, okW, nW, nAllW, nNoZ);
}
