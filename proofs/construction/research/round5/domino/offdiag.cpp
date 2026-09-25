// For parity-respecting positions G (Blue stones on majority, White on minority, >= 1 White
// stone), F = 1 - |P| + |Q|.  For each White off-parity move y (a majority cell), classify the
// Blue replies b with value(G^{y,b}) >= F (Blue then wins G - F as second player):
//   adjacent minority replies (anti-domino), other minority, majority.
// Also the colour dual: Blue off-parity z (minority), White replies r with value <= F.
// ./offparity H W pmax qmax
#include "/workspace/proofs/construction/research/round5/center/colcore_fast.hpp"
#include <cstdlib>
#include <map>
static bool geq_int(Val g, i64 F) { return g.e == 0 ? g.x >= F : g.x > F; }
static bool leq_int(Val g, i64 F) { return g.e == 0 ? g.x <= F : g.x < F; }
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    int pmax = std::atoi(argv[3]), qmax = std::atoi(argv[4]);
    setup(h, w);
    std::vector<int> maj, mnr; u64 majm = 0;
    for (int v = 0; v < N; ++v) { if ((v / W + v % W) % 2) mnr.push_back(v); else { maj.push_back(v); majm |= u64{1} << v; } }
    long diagGood = 0, dist2Good = 0; int shown2 = 0; long cases = 0, adjAlways = 0, anyGood = 0, adjSomeGood = 0, majGood = 0;
    long casesB = 0, adjAlwaysB = 0, anyGoodB = 0, adjSomeGoodB = 0, minGoodB = 0;
    int shown = 0;
    std::vector<int> P, Q;
    auto eval = [&]() {
        if (Q.empty()) return;
        u64 blue = 0, white = 0;
        for (int x : P) blue |= u64{1} << x;
        for (int y : Q) white |= u64{1} << y;
        i64 F = (1 - (i64)P.size() + (i64)Q.size()) * ONE;
        u64 a, b; perms_from_stones(blue, white, a, b);
        // White off-parity y
        for (u64 z = b & majm; z; z &= z - 1) {
            int y = __builtin_ctzll(z); u64 yb = u64{1} << y;
            u64 a1 = a & ~yb, b1 = b & ~NB[y];
            ++cases;
            bool any = false, allAdj = true, someAdj = false, maj1 = false, diag = false, dist2 = false; int nadj = 0;
            for (u64 t = a1; t; t &= t - 1) {
                int r = __builtin_ctzll(t); u64 rb = u64{1} << r;
                bool good = geq_int(value(a1 & ~NB[r], b1 & ~rb), F);
                bool adj = (NB[y] >> r) & 1;
                if (good) any = true;
                if (adj) { ++nadj; if (good) someAdj = true; else allAdj = false; }
                if (good && (majm >> r & 1)) maj1 = true;
                int dr = std::abs(r / W - y / W), dc = std::abs(r % W - y % W);
                if (good && dr == 1 && dc == 1) diag = true;
                if (good && dr + dc == 2) dist2 = true;
            }
            if (diag) ++diagGood;
            if (dist2) ++dist2Good;
            if (any && !dist2 && shown2 < 6) { ++shown2; show(a1, b1); std::printf("  good replies exist but none at distance 2 (y=(%d,%d))\n", y / W, y % W); }
            if (any) ++anyGood;
            if (nadj && allAdj) ++adjAlways;
            if (someAdj) ++adjSomeGood;
            if (maj1) ++majGood;
            if (false) { ++shown; show(a1, b1); std::printf("  after White off-parity: no Blue reply reaches F\n"); }
        }
        // Blue off-parity z (minority)
        for (u64 t = a & ~majm; t; t &= t - 1) {
            int zc = __builtin_ctzll(t); u64 zb = u64{1} << zc;
            u64 a1 = a & ~NB[zc], b1 = b & ~zb;
            ++casesB;
            bool any = false, allAdj = true, someAdj = false, min1 = false; int nadj = 0;
            for (u64 s = b1; s; s &= s - 1) {
                int r = __builtin_ctzll(s); u64 rb = u64{1} << r;
                bool good = leq_int(value(a1 & ~rb, b1 & ~NB[r]), F);
                bool adj = (NB[zc] >> r) & 1;
                if (good) any = true;
                if (adj) { ++nadj; if (good) someAdj = true; else allAdj = false; }
                if (good && !(majm >> r & 1)) min1 = true;
            }
            if (any) ++anyGoodB;
            if (nadj && allAdj) ++adjAlwaysB;
            if (someAdj) ++adjSomeGoodB;
            if (min1) ++minGoodB;
            if (false) { ++shown; show(a1, b1); std::printf("  after Blue off-parity: no White reply reaches F\n"); }
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
    std::printf("%dx%d White off-parity: %ld cases; some good Blue reply %ld; some adjacent-minority reply good %ld; "
                "every adjacent-minority reply good %ld; some majority reply good %ld\n",
                h, w, cases, anyGood, adjSomeGood, adjAlways, majGood);
    std::printf("%dx%d White off-parity: good diagonal reply %ld, good distance-2 reply %ld (of %ld with any good reply)\n", h, w, diagGood, dist2Good, anyGood);
    std::printf("%dx%d Blue off-parity: %ld cases; some good White reply %ld; some adjacent-majority reply good %ld; "
                "every adjacent-majority reply good %ld; some minority reply good %ld\n",
                h, w, casesB, anyGoodB, adjSomeGoodB, adjAlwaysB, minGoodB);
}
