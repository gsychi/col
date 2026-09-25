// Domino positions D(v,u) and the two parity-restricted games that sandwich them.
//   Dmaj = D with Blue restricted to majority cells   (Dmaj <= D, monotonicity)
//   Dmin = D with White restricted to minority cells  (D <= Dmin)
// Both restrictions together give exactly 1, so Dmaj = 1 would prove D >= 1 and
// Dmin = 1 would prove D <= 1.  Also prints O_v (Blue opening at v) and O_u.
// Build: g++ -O2 -std=c++17 restrict.cpp -o restrict ; run: ./restrict H W
#include "../center/colcore_fast.hpp"
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    setup(h, w);
    u64 full = fullmask(), maj = 0, mnr = 0;
    for (int v = 0; v < N; ++v) ((v / W + v % W) % 2 ? mnr : maj) |= u64{1} << v;
    for (int v = 0; v < N; ++v) {
        int r = v / W, c = v % W;
        if ((r + c) % 2 || r > (H - 1) / 2 || c > (W - 1) / 2) continue;
        Val ov = value(full & ~NB[v], full & ~(u64{1} << v));
        for (u64 z = NB[v] & ~(u64{1} << v); z; z &= z - 1) {
            int u = __builtin_ctzll(z);
            u64 a, b; perms_from_stones(u64{1} << v, u64{1} << u, a, b);
            Val d = value(a, b), dmaj = value(a & maj, b), dmin = value(a, b & mnr);
            Val ou = value(full & ~NB[u], full & ~(u64{1} << u));
            std::printf("%dx%d B(%d,%d) W(%d,%d): D=%s Dmaj=%s Dmin=%s  O_v=%s  O_u(minority, Blue)=%s\n",
                        h, w, r, c, u / W, u % W, fmt(d).c_str(), fmt(dmaj).c_str(), fmt(dmin).c_str(),
                        fmt(ov).c_str(), fmt(ou).c_str());
            std::fflush(stdout);
        }
    }
}
