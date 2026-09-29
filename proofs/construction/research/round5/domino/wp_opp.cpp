// 3 x K, PF class (Blue on X, White on Y, White has a stone), White-legal y in X on an edge row.
// Let y' be the cell opposite y in its column.  Classify:
//   y' Blue stone: is G^{R,y} |> F ?
//   y' free: is G^{y,y'} >= F ?   (histogram of G^{y,y'} - F)
// Prints failing positions (up to a limit).
// ./wp_opp K [pmax qmax]
#include "../center/colcore_fast.hpp"
#include <map>
int main(int argc, char** argv) {
    int k = std::atoi(argv[1]);
    int pmax = argc > 2 ? std::atoi(argv[2]) : 99, qmax = argc > 3 ? std::atoi(argv[3]) : 99;
    setup(3, k);
    u64 majm = 0, full = fullmask();
    for (int v = 0; v < N; ++v) if ((v / W + v % W) % 2 == 0) majm |= u64{1} << v;
    std::map<std::string, long> hstone, hfree;
    int shown = 0;
    for (u64 blue = majm;; blue = (blue - 1) & majm) {
        if (__builtin_popcountll(blue) <= pmax)
        for (u64 white = full & ~majm; white; white = (white - 1) & full & ~majm) {
            if (__builtin_popcountll(white) > qmax) continue;
            u64 a, b; perms_from_stones(blue, white, a, b);
            u64 occ = blue | white;
            i64 F = (i64)(__builtin_popcountll(majm & ~occ) - __builtin_popcountll(full & ~majm & ~occ)) * ONE;
            for (u64 z = b & majm; z; z &= z - 1) {
                int y = __builtin_ctzll(z); u64 yb = u64{1} << y;
                int r = y / W, c = y % W;
                if (r == 1) continue;
                int yo = (2 - r) * W + c; u64 ob = u64{1} << yo;
                u64 a1 = a & ~yb, b1 = b & ~NB[y];
                if (blue & ob) {
                    Val g = value(a1, b1);
                    hstone[fmt(Val{g.x - F, g.e})]++;
                } else {
                    Val g = value(a1 & ~NB[yo], b1 & ~ob);
                    std::string d = fmt(Val{g.x - F, g.e});
                    hfree[d]++;
                    bool ok = g.e == 0 ? g.x >= F : g.x > F;
                    if (!ok && shown < 30) {
                        ++shown;
                        for (int rr = 0; rr < 3; ++rr) {
                            for (int cc = 0; cc < k; ++cc) {
                                int v = rr * W + cc; u64 bit = u64{1} << v;
                                std::putchar(v == y ? 'Y' : (blue & bit) ? 'B' : (white & bit) ? 'W' : ((majm >> v) & 1) ? '+' : '-');
                            }
                            if (rr < 2) std::putchar('/');
                        }
                        std::printf("  F=%lld  G^{y,y'}-F=%s\n", (long long)(F / ONE), d.c_str());
                    }
                }
            }
        }
        if (!blue) break;
    }
    for (auto& [d, cnt] : hstone) std::printf("3x%d y' Blue: G^{R,y}-F = %s x%ld\n", k, d.c_str(), cnt);
    for (auto& [d, cnt] : hfree) std::printf("3x%d y' free: G^{y,y'}-F = %s x%ld\n", k, d.c_str(), cnt);
}
