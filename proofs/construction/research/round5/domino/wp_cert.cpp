// Cut certificates for (W') on 3 x K (see W_PRIME.md section 3).  For every PF-class position G
// (Blue on X, White on Y, >= 1 White stone) and White-legal y in X, compute the value of the
// lower-bounding position used by the proof and test whether it certifies (W'):
//   M   (y middle, (1,c)): Z = G^{R,y} with Blue permission removed at (0,c), (2,c) (dead cells);
//                         Z = L + R exactly.  Certifies if Z |> F.
//   EB  (y edge, y' = opposite cell holds Blue): Z = G^{R,y} = L + R exactly.  Certifies if Z |> F.
//   EW  (y edge, a White stone at (2-r, c+s) next to y'): answer b = (r, c+2s), and Z = G^{y,b}
//       with Blue permission removed at (1,c).  Certifies if Z >= F.
//   EO  (y edge, otherwise): answer y', Z = G^{y,y'} = L + R exactly.  Certifies if Z >= F.
// Each branch is further split by the White content of the two sides of column c
// (W = has a White stone, b = Blue stones only, e = empty, 0 = no columns).
// ./wp_cert K [showmax]
#include "../center/colcore_fast.hpp"
#include <array>
#include <map>
#include <string>
int main(int argc, char** argv) {
    int K = std::atoi(argv[1]); int showmax = argc > 2 ? std::atoi(argv[2]) : 3;
    setup(3, K);
    u64 MAJ = 0, full = fullmask();
    for (int v = 0; v < N; ++v) if ((v / W + v % W) % 2 == 0) MAJ |= u64{1} << v;
    auto cell = [&](int r, int c) { return r * K + c; };
    auto bit = [&](int r, int c) { return u64{1} << (r * K + c); };
    std::map<std::string, std::array<long, 2>> res;   // certified, not certified
    std::map<std::string, std::map<std::string, long>> gap;  // Z - F histogram of failures
    std::map<std::string, int> shown;
    for (u64 blue = MAJ;; blue = (blue - 1) & MAJ) {
        for (u64 white = full & ~MAJ; white; white = (white - 1) & full & ~MAJ) {
            u64 a, b; perms_from_stones(blue, white, a, b);
            u64 occ = blue | white;
            i64 F = (i64)(__builtin_popcountll(MAJ & ~occ) - __builtin_popcountll(full & ~MAJ & ~occ)) * ONE;
            for (u64 z = b & MAJ; z; z &= z - 1) {
                int y = __builtin_ctzll(z); u64 yb = u64{1} << y;
                int r = y / K, c = y % K;
                u64 a1 = a & ~yb, b1 = b & ~NB[y];
                u64 left = 0, right = 0;
                for (int rr = 0; rr < 3; ++rr) for (int cc = 0; cc < K; ++cc) {
                    if (cc < c) left |= bit(rr, cc); else if (cc > c) right |= bit(rr, cc);
                }
                auto side = [&](u64 m) { return m == 0 ? '0' : (white & m) ? 'W' : (blue & m) ? 'b' : 'e'; };
                std::string sides = std::string(1, side(left)) + side(right);
                std::string br; Val Z; bool strict;
                if (r == 1) {
                    br = "M"; strict = true;
                    Z = value(a1 & ~bit(0, c) & ~bit(2, c), b1);
                } else {
                    int o = cell(2 - r, c);
                    int s = 0;
                    for (int t : {-1, 1})
                        if (!s && c + t >= 0 && c + t < K && ((white >> cell(2 - r, c + t)) & 1) && ((a1 >> cell(r, c + 2 * t)) & 1)) s = t;
                    if (s) {
                        br = "EW"; strict = false;
                        int q = cell(r, c + 2 * s);
                        if (std::getenv("EWLEMMA")) {
                            // Lemma 4(2) at the Blue-only cell y': G^{y,b} >= G^{y,b,y'} + 1 (exact split)
                            u64 a2 = a1 & ~NB[q], b2 = b1 & ~(u64{1} << q);
                            if ((blue >> o) & 1) Z = value(a2, b2);  // y' already Blue: exact split
                            else {
                                if (!((a2 >> o) & 1) || ((b2 >> o) & 1)) { std::fprintf(stderr, "y' not Blue-only\n"); return 1; }
                                Z = value(a2 & ~NB[o], b2 & ~(u64{1} << o)); Z.x += ONE;
                            }
                        } else
                        Z = value(a1 & ~NB[q] & ~bit(1, c), b1 & ~(u64{1} << q));
                    } else if ((blue >> o) & 1) {
                        br = "EB"; strict = true;
                        Z = value(a1, b1);
                    } else {
                        br = "EO"; strict = false;
                        Z = value(a1 & ~NB[o], b1 & ~(u64{1} << o));
                    }
                }
                bool ok = strict ? (Z.e ? Z.x >= F : Z.x > F) : (Z.e ? Z.x > F : Z.x >= F);
                std::string key = br + " " + sides;
                res[key][ok ? 0 : 1]++;
                if (!ok) {
                    gap[key][fmt(Val{Z.x - F, Z.e})]++;
                    if (shown[key] < showmax) {
                        ++shown[key];
                        std::printf("%-6s ", key.c_str());
                        for (int rr = 0; rr < 3; ++rr) {
                            for (int cc = 0; cc < K; ++cc) {
                                int v = cell(rr, cc); u64 bt = u64{1} << v;
                                std::putchar(v == y ? 'Y' : (blue & bt) ? 'B' : (white & bt) ? 'W' : ((MAJ >> v) & 1) ? '+' : '-');
                            }
                            if (rr < 2) std::putchar('/');
                        }
                        Val gy = value(a1, b1);
                        std::printf("  F=%lld  Z-F=%s  G^Ry-F=%s\n", (long long)(F / ONE), fmt(Val{Z.x - F, Z.e}).c_str(), fmt(Val{gy.x - F, gy.e}).c_str());
                    }
                }
            }
        }
        if (!blue) break;
    }
    long tot[2] = {0, 0};
    for (auto& [key, R] : res) {
        std::printf("3x%d %-6s certified %ld, not certified %ld", K, key.c_str(), R[0], R[1]);
        for (auto& [g, n] : gap[key]) std::printf("  [Z-F=%s x%ld]", g.c_str(), n);
        std::printf("\n");
        tot[0] += R[0]; tot[1] += R[1];
    }
    std::printf("3x%d total certified %ld, not certified %ld\n", K, tot[0], tot[1]);
}
