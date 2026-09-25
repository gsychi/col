// Majority openings: for each majority Blue opening v (one per symmetry class), the value of
// S(v,y) = Blue at v, White at y, for every majority cell y, as a grid.
// A reply with S(v,y) <= 0 gives O_v <= S + * <= *, so O_v != 0.
// ./samepar H W
#include "../center/colcore_fast.hpp"
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    setup(h, w);
    u64 full = fullmask();
    for (int v = 0; v < N; ++v) {
        int r = v / W, c = v % W;
        if ((r + c) % 2 || r > (H - 1) / 2 || c > (W - 1) / 2) continue;
        Val ov = value(full & ~NB[v], full & ~(u64{1} << v));
        std::printf("%dx%d Blue (%d,%d): O_v = %s; S(v,y) for majority y (B = v, . = minority):\n", h, w, r, c, fmt(ov).c_str());
        int nonpos = 0;
        for (int rr = 0; rr < H; ++rr) {
            for (int cc = 0; cc < W; ++cc) {
                int y = rr * W + cc;
                if (y == v) { std::printf(" %6s", "B"); continue; }
                if ((rr + cc) % 2) { std::printf(" %6s", "."); continue; }
                u64 a, b; perms_from_stones(u64{1} << v, u64{1} << y, a, b);
                Val s = value(a, b);
                if (s.e == 0 ? s.x <= 0 : s.x < 0) ++nonpos;
                std::printf(" %6s", fmt(s).c_str());
            }
            std::printf("\n");
        }
        std::printf("  replies with S <= 0: %d\n", nonpos);
        std::fflush(stdout);
    }
}
