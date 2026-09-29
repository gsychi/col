// Dual cut certificates for the upper half of PF on 3 x K (W_PRIME.md section 6).
// Positions: Blue stones on X, White stones on Y, ANY content (also no White stone).
// For each Blue-legal z in Y (Blue off-parity move) compute an upper-bounding position Z and
// test the strong form (B): G^{L,z} <= F - 1, via
//   M   (z middle, (1,c)): Z = G^{L,z} with White permission removed at (0,c), (2,c)
//                          (upper-bound comparison; Z = L + R exactly).  Certifies if Z <= F - 1.
//   EB  (z edge, z' = opposite cell holds White): Z = G^{L,z} = L + R.  Certifies if Z <= F - 1.
//   EW  (z edge, a Blue stone at (2-r, c+s) next to z'): White answers w = (r, c+2s);
//       Lemma 4(4) at the White-only cell z': G^{z,w} <= G^{z,w,z'} - 1 =: Z.  (B') if Z <= F.
//   EO  (z edge, otherwise): White answers z', Z = G^{z,z'}.  (B') if Z <= F.
// For EW, EO the certificate gives (B'): G^{L,z} <| F.  Also reports whether (B) holds.
// Sides of column c: W = has White stone, b = Blue only, e = empty, 0 = no columns.
// ./wp_certB K [showmax]
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
    std::map<std::string, std::array<long, 3>> res;  // certified, not certified, (B) false
    std::map<std::string, std::map<std::string, long>> gap;
    std::map<std::string, int> shown;
    long pf_fail = 0, npos = 0;
    for (u64 blue = MAJ;; blue = (blue - 1) & MAJ) {
        for (u64 white = full & ~MAJ;; white = (white - 1) & full & ~MAJ) {
            u64 a, b; perms_from_stones(blue, white, a, b);
            u64 occ = blue | white;
            i64 F = (i64)(__builtin_popcountll(MAJ & ~occ) - __builtin_popcountll(full & ~MAJ & ~occ)) * ONE;
            Val g0 = value(a, b); ++npos;
            if (!(g0.e ? g0.x < F : g0.x <= F)) ++pf_fail;  // upper half G <= F
            for (u64 t = a & ~MAJ; t; t &= t - 1) {
                int z = __builtin_ctzll(t); u64 zb = u64{1} << z;
                int r = z / K, c = z % K;
                u64 a1 = a & ~NB[z], b1 = b & ~zb;
                u64 left = 0, right = 0;
                for (int rr = 0; rr < 3; ++rr) for (int cc = 0; cc < K; ++cc) {
                    if (cc < c) left |= bit(rr, cc); else if (cc > c) right |= bit(rr, cc);
                }
                auto side = [&](u64 m) { return m == 0 ? '0' : (white & m) ? 'W' : (blue & m) ? 'b' : 'e'; };
                std::string sides = std::string(1, side(left)) + side(right);
                std::string br; Val Z; bool strongB;
                if (r == 1) {
                    br = "M"; strongB = true;
                    Z = value(a1, b1 & ~bit(0, c) & ~bit(2, c));
                } else {
                    int o = cell(2 - r, c);
                    int s = 0;
                    for (int u : {-1, 1})
                        if (!s && c + u >= 0 && c + u < K && ((blue >> cell(2 - r, c + u)) & 1) && ((b1 >> cell(r, c + 2 * u)) & 1)) s = u;
                    if ((white >> o) & 1) { br = "EB"; strongB = true; Z = value(a1, b1); }
                    else if (s) {
                        br = "EW"; strongB = false;
                        int q = cell(r, c + 2 * s);
                        u64 a2 = a1 & ~(u64{1} << q), b2 = b1 & ~NB[q];
                        if (((a2 >> o) & 1) || !((b2 >> o) & 1)) { std::fprintf(stderr, "z' not White-only\n"); return 1; }
                        Z = value(a2 & ~(u64{1} << o), b2 & ~NB[o]); Z.x -= ONE;
                    } else {
                        br = "EO"; strongB = false;
                        Z = value(a1 & ~(u64{1} << o), b1 & ~NB[o]);
                    }
                }
                Val gz = value(a1, b1);
                bool Bstrong = gz.e ? gz.x < F - ONE : gz.x <= F - ONE;
                i64 T = strongB ? F - ONE : F;
                bool ok = Z.e ? Z.x < T : Z.x <= T;
                std::string key = br + " " + sides;
                res[key][ok ? 0 : 1]++;
                if (!Bstrong) res[key][2]++;
                if (!ok) {
                    gap[key][fmt(Val{Z.x - F, Z.e})]++;
                    if (shown[key] < showmax) {
                        ++shown[key];
                        std::printf("%-6s ", key.c_str());
                        for (int rr = 0; rr < 3; ++rr) {
                            for (int cc = 0; cc < K; ++cc) {
                                int v = cell(rr, cc); u64 bt = u64{1} << v;
                                std::putchar(v == z ? 'Z' : (blue & bt) ? 'B' : (white & bt) ? 'W' : ((MAJ >> v) & 1) ? '+' : '-');
                            }
                            if (rr < 2) std::putchar('/');
                        }
                        std::printf("  F=%lld  Z-F=%s  G^Lz-F=%s\n", (long long)(F / ONE), fmt(Val{Z.x - F, Z.e}).c_str(), fmt(Val{gz.x - F, gz.e}).c_str());
                    }
                }
            }
            if (!white) break;
        }
        if (!blue) break;
    }
    long tot[2] = {0, 0};
    for (auto& [key, R] : res) {
        std::printf("3x%d %-6s certified %ld, not certified %ld, (B) false %ld", K, key.c_str(), R[0], R[1], R[2]);
        for (auto& [g, n] : gap[key]) std::printf("  [Z-F=%s x%ld]", g.c_str(), n);
        std::printf("\n");
        tot[0] += R[0]; tot[1] += R[1];
    }
    std::printf("3x%d positions %ld, upper-half PF failures (G > F or G || F) %ld; total certified %ld, not certified %ld\n",
                K, npos, pf_fail, tot[0], tot[1]);
}
