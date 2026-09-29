// For PF-class positions G on H x K (Blue on X, White on Y, White has a stone) and White-legal
// y in X, count for each relative offset (dr, dc) of a Blue reply b how often
// value(G^{y,b}) >= F, split by the row of y (edge or middle).  Also counts cases with no good
// reply and with G^{R,y} not |> F (i.e. (W') failures; expected zero).
// ./wp_offsets H K [pmax qmax]
#include "../center/colcore_fast.hpp"
#include <map>
#include <tuple>
static bool geq_int(Val g, i64 F) { return g.e == 0 ? g.x >= F : g.x > F; }
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), k = std::atoi(argv[2]);
    int pmax = argc > 3 ? std::atoi(argv[3]) : 99, qmax = argc > 4 ? std::atoi(argv[4]) : 99;
    setup(h, k);
    u64 majm = 0, full = fullmask();
    for (int v = 0; v < N; ++v) if ((v / W + v % W) % 2 == 0) majm |= u64{1} << v;
    std::map<std::tuple<int, int, int>, long> good;  // (ymid, dr, dc)
    long cases[2] = {0, 0}, none[2] = {0, 0}, wfail = 0;
    for (u64 blue = majm;; blue = (blue - 1) & majm) {
        if (__builtin_popcountll(blue) <= pmax)
        for (u64 white = full & ~majm; white; white = (white - 1) & full & ~majm) {
            if (__builtin_popcountll(white) > qmax) continue;
            u64 a, b; perms_from_stones(blue, white, a, b);
            u64 occ = blue | white;
            i64 F = (i64)(__builtin_popcountll(majm & ~occ) - __builtin_popcountll(full & ~majm & ~occ)) * ONE;
            for (u64 z = b & majm; z; z &= z - 1) {
                int y = __builtin_ctzll(z); u64 yb = u64{1} << y;
                int ymid = (y / W != 0 && y / W != h - 1);
                u64 a1 = a & ~yb, b1 = b & ~NB[y];
                ++cases[ymid];
                bool any = false;
                for (u64 t = a1; t; t &= t - 1) {
                    int r = __builtin_ctzll(t); u64 rb = u64{1} << r;
                    if (geq_int(value(a1 & ~NB[r], b1 & ~rb), F)) {
                        any = true;
                        good[{ymid, r / W - y / W, r % W - y % W}]++;
                    }
                }
                if (!any) { ++none[ymid]; Val g = value(a1, b1); if (!(g.e ? g.x >= F : g.x > F)) ++wfail; }
            }
        }
        if (!blue) break;
    }
    std::printf("%dx%d edge-row y: %ld cases, %ld without a good reply; middle-row y: %ld cases, %ld without; (W') failures %ld\n",
                h, k, cases[0], none[0], cases[1], none[1], wfail);
    for (auto& [key, cnt] : good)
        if (cnt * 20 >= cases[std::get<0>(key)])
            std::printf("  %s y, offset (%d,%d): good in %ld\n", std::get<0>(key) ? "middle" : "edge", std::get<1>(key), std::get<2>(key), cnt);
}
