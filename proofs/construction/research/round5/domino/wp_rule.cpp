// Test a Blue answer rule for White off-parity moves on 3 x K (all PF-class positions: Blue
// stones on X, White stones on Y, at least one White stone; optional caps on |P|, |Q|).
// For each White-legal y in X the rule returns a branch label and a Blue cell b (or -1).
// A case is
//   ANSWER  b is Blue-legal after y and value(G^{y,b}) >= F  (so G^{R,y} |> F),
//   FREE    value(G^{R,y}) >= F + 1 (no answer needed: (W') holds, and F + 1 is F's right option
//           only when F < 0, but G^{R,y} >= F + 1 > F gives G^{R,y} |> F in any case),
//   FAIL    otherwise (printed with the list of good answers, up to a limit).
// Counts are reported per branch.  Also verifies (W') itself (G^{R,y} |> F) in every case.
// ./wp_rule K [pmax qmax [showmax]]
#include "../center/colcore_fast.hpp"
#include <array>
#include <map>
#include <string>

static int K;
static u64 MAJ;
static inline int cell(int r, int c) { return r * K + c; }

struct Choice { const char* label; int b; };

// blue/white: stones before y; a1: Blue permissions after y.
static Choice rule(u64 blue, u64 white, u64 a1, int y) {
    int r = y / K, c = y % K;
    auto occ = [&](int v) { return ((blue | white) >> v) & 1; };
    auto isW = [&](int v) { return (white >> v) & 1; };
    auto legal = [&](int v) { return (int)((a1 >> v) & 1); };
    u64 left = 0, right = 0;
    for (int rr = 0; rr < 3; ++rr) for (int cc = 0; cc < K; ++cc) {
        u64 bit = u64{1} << cell(rr, cc);
        if (cc < c) left |= bit; else if (cc > c) right |= bit;
    }
    bool lEmpty = c > 0 && !((blue | white) & left), rEmpty = c < K - 1 && !((blue | white) & right);
    bool lW = (white & left) != 0, rW = (white & right) != 0;
    if (r == 1) {
        if (lW && rW) return {"M-WW", -1};
        int s = lW ? 1 : -1;  // towards the side without White stones
        const char* lab = (s < 0 ? lEmpty : rEmpty) ? "M-empty" : "M-Bonly";
        if (legal(cell(0, c + s))) return {lab, cell(0, c + s)};
        if (legal(cell(2, c + s))) return {lab, cell(2, c + s)};
        return {"M-Bonly-cut", -1};
    }
    if (lEmpty && c >= 2) return {"E-empty", cell(r, c - 2)};
    if (rEmpty && c <= K - 3) return {"E-empty", cell(r, c + 2)};
    int o = cell(2 - r, c);
    for (int s : {-1, 1})
        if (c + s >= 0 && c + s < K && isW(cell(2 - r, c + s)) && c + 2 * s >= 0 && c + 2 * s < K && legal(cell(r, c + 2 * s)))
            return {occ(o) ? "E-oppB-W" : "E-opp-W", cell(r, c + 2 * s)};
    if (occ(o)) return {"E-oppB", -1};
    return {"E-opp", o};
}

int main(int argc, char** argv) {
    K = std::atoi(argv[1]);
    int pmax = argc > 2 ? std::atoi(argv[2]) : 99, qmax = argc > 3 ? std::atoi(argv[3]) : 99;
    int showmax = argc > 4 ? std::atoi(argv[4]) : 20;
    setup(3, K);
    u64 full = fullmask();
    for (int v = 0; v < N; ++v) if ((v / W + v % W) % 2 == 0) MAJ |= u64{1} << v;
    long total = 0, wfail = 0;
    std::map<std::string, std::array<long, 3>> res;  // answer, free, fail
    int shown = 0;
    for (u64 blue = MAJ;; blue = (blue - 1) & MAJ) {
        if (__builtin_popcountll(blue) <= pmax)
        for (u64 white = full & ~MAJ; white; white = (white - 1) & full & ~MAJ) {
            if (__builtin_popcountll(white) > qmax) continue;
            u64 a, b; perms_from_stones(blue, white, a, b);
            u64 occ = blue | white;
            i64 F = (i64)(__builtin_popcountll(MAJ & ~occ) - __builtin_popcountll(full & ~MAJ & ~occ)) * ONE;
            for (u64 z = b & MAJ; z; z &= z - 1) {
                int y = __builtin_ctzll(z); u64 yb = u64{1} << y;
                u64 a1 = a & ~yb, b1 = b & ~NB[y];
                ++total;
                Val gy = value(a1, b1);
                if (!(gy.e ? gy.x >= F : gy.x > F)) ++wfail;
                Choice ch = rule(blue, white, a1, y);
                auto& R = res[ch.label];
                if (ch.b >= 0 && ((a1 >> ch.b) & 1)) {
                    Val g = value(a1 & ~NB[ch.b], b1 & ~(u64{1} << ch.b));
                    if (g.e == 0 ? g.x >= F : g.x > F) { R[0]++; continue; }
                }
                if (gy.e == 0 ? gy.x >= F + ONE : gy.x > F + ONE) { R[1]++; continue; }
                R[2]++;
                if (shown < showmax) {
                    ++shown;
                    std::string goods;
                    for (u64 t = a1; t; t &= t - 1) {
                        int q = __builtin_ctzll(t); u64 qb = u64{1} << q;
                        Val g = value(a1 & ~NB[q], b1 & ~qb);
                        if (g.e == 0 ? g.x >= F : g.x > F)
                            goods += "(" + std::to_string(q / W) + "," + std::to_string(q % W) + ")";
                    }
                    std::printf("%-10s ", ch.label);
                    for (int rr = 0; rr < 3; ++rr) {
                        for (int cc = 0; cc < K; ++cc) {
                            int v = rr * W + cc; u64 bit = u64{1} << v;
                            std::putchar(v == y ? 'Y' : (blue & bit) ? 'B' : (white & bit) ? 'W' : ((MAJ >> v) & 1) ? '+' : '-');
                        }
                        if (rr < 2) std::putchar('/');
                    }
                    std::string rs = ch.b >= 0 ? "(" + std::to_string(ch.b / W) + "," + std::to_string(ch.b % W) + ")" : "none";
                    std::printf("  F=%lld G^Ry-F=%s rule=%s good:%s\n", (long long)(F / ONE),
                                fmt(Val{gy.x - F, gy.e}).c_str(), rs.c_str(), goods.empty() ? " none" : goods.c_str());
                }
            }
        }
        if (!blue) break;
    }
    long fails = 0;
    for (auto& [lab, R] : res) {
        std::printf("3x%d %-10s answer-ok %ld, free-ok %ld, FAIL %ld\n", K, lab.c_str(), R[0], R[1], R[2]);
        fails += R[2];
    }
    std::printf("3x%d pmax=%d qmax=%d: cases %ld, rule failures %ld, (W') failures %ld\n", K, pmax, qmax, total, fails, wfail);
}
