// 3 x K, PF class, White-legal y in X.  Split by the row of y and by which sides of y's column
// (columns < c, columns > c) contain White stones / any stones.  For each class print the
// number of cases and, for the first few, the position and the list of good Blue replies
// (value(G^{y,b}) >= F), given as offsets (dr,dc) from y.
// ./wp_qempty K [show]
#include "../center/colcore_fast.hpp"
#include <map>
#include <string>
int main(int argc, char** argv) {
    int k = std::atoi(argv[1]); int showmax = argc > 2 ? std::atoi(argv[2]) : 3;
    setup(3, k);
    u64 majm = 0, full = fullmask();
    for (int v = 0; v < N; ++v) if ((v / W + v % W) % 2 == 0) majm |= u64{1} << v;
    std::map<std::string, long> cnt, offs;
    std::map<std::string, int> shown;
    for (u64 blue = majm;; blue = (blue - 1) & majm) {
        for (u64 white = full & ~majm; white; white = (white - 1) & full & ~majm) {
            u64 a, b; perms_from_stones(blue, white, a, b);
            u64 occ = blue | white;
            i64 F = (i64)(__builtin_popcountll(majm & ~occ) - __builtin_popcountll(full & ~majm & ~occ)) * ONE;
            for (u64 z = b & majm; z; z &= z - 1) {
                int y = __builtin_ctzll(z); u64 yb = u64{1} << y;
                int r = y / W, c = y % W;
                u64 left = 0, right = 0;
                for (int rr = 0; rr < 3; ++rr) for (int cc = 0; cc < k; ++cc) {
                    u64 bit = u64{1} << (rr * W + cc);
                    if (cc < c) left |= bit; if (cc > c) right |= bit;
                }
                auto side = [&](u64 m) { return (white & m) ? 'W' : (blue & m) ? 'b' : (m ? 'e' : '0'); };
                std::string key = std::string(r == 1 ? "mid " : "edge ") + side(left) + side(right);
                if (std::getenv("WIDTHKEY")) key += " c=" + std::to_string(c);
                u64 a1 = a & ~yb, b1 = b & ~NB[y];
                std::string goods;
                for (u64 t = a1; t; t &= t - 1) {
                    int q = __builtin_ctzll(t); u64 qb = u64{1} << q;
                    Val g = value(a1 & ~NB[q], b1 & ~qb);
                    if (g.e == 0 ? g.x >= F : g.x > F) {
                        std::string o = "(" + std::to_string(q / W - r) + "," + std::to_string(q % W - c) + ")";
                        goods += o;
                        offs[key + " " + o]++;
                    }
                }
                if (goods.empty()) goods = "none";
                cnt[key]++;
                if (shown[key] < showmax) {
                    ++shown[key];
                    std::printf("%s: ", key.c_str());
                    for (int rr = 0; rr < 3; ++rr) {
                        for (int cc = 0; cc < k; ++cc) {
                            int v = rr * W + cc; u64 bit = u64{1} << v;
                            std::putchar(v == y ? 'Y' : (blue & bit) ? 'B' : (white & bit) ? 'W' : ((majm >> v) & 1) ? '+' : '-');
                        }
                        if (rr < 2) std::putchar('/');
                    }
                    std::printf(" F=%lld good: %s\n", (long long)(F / ONE), goods.c_str());
                }
            }
        }
        if (!blue) break;
    }
    for (auto& [key, n] : cnt) std::printf("3x%d %s: %ld\n", k, key.c_str(), n);
    for (auto& [key, n] : offs) std::printf("3x%d offset %s: %ld\n", k, key.c_str(), n);
}
