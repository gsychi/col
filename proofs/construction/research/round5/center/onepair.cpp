// Value of the empty odd x odd board after Blue v and White rho(v), for every v != centre.
#include "colcore_fast.hpp"
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    setup(h, w);
    int c = N / 2;
    u64 full = fullmask();
    int zero = 0, star = 0;
    for (int v = 0; v < N; ++v) {
        if (v == c || v > rho(v)) continue;
        u64 blue = u64{1} << v, white = u64{1} << rho(v), a, b;
        perms_from_stones(blue, white, a, b);
        Val e = value(a, b);
        std::printf("  Blue (%d,%d) White (%d,%d): %s\n", v / W, v % W, rho(v) / W, rho(v) % W, fmt(e).c_str());
        (e.e ? star : zero)++;
    }
    std::printf("%dx%d mirror after one opening: zero %d, star %d\n", h, w, zero, star);
}
