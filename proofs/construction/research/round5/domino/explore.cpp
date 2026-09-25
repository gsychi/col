// Print a position given by stones and the value of every option.
// ./explore H W "B r c" "W r c" ...   (stones in any order)
#include "../center/colcore_fast.hpp"
#include <cstring>
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    setup(h, w);
    u64 blue = 0, white = 0;
    for (int i = 3; i < argc; ++i) {
        char c; int r, cc;
        if (std::sscanf(argv[i], "%c %d %d", &c, &r, &cc) != 3) return 1;
        (c == 'B' ? blue : white) |= u64{1} << (r * W + cc);
    }
    u64 a, b; perms_from_stones(blue, white, a, b);
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int v = r * W + c;
            char ch = (blue >> v & 1) ? 'B' : (white >> v & 1) ? 'W' : ((a >> v & 1) && (b >> v & 1)) ? 'o' : (a >> v & 1) ? 'b' : (b >> v & 1) ? 'w' : '.';
            std::putchar(ch);
        }
        std::putchar('\n');
    }
    std::printf("value %s\n", fmt(value(a, b)).c_str());
    std::printf("Blue options:");
    for (u64 z = a; z; z &= z - 1) { int v = __builtin_ctzll(z); std::printf(" (%d,%d)%s:%s", v / W, v % W, (v / W + v % W) % 2 ? "m" : "M", fmt(value(a & ~NB[v], b & ~(u64{1} << v))).c_str()); }
    std::printf("\nWhite options:");
    for (u64 z = b; z; z &= z - 1) { int v = __builtin_ctzll(z); std::printf(" (%d,%d)%s:%s", v / W, v % W, (v / W + v % W) % 2 ? "m" : "M", fmt(value(a & ~(u64{1} << v), b & ~NB[v])).c_str()); }
    std::printf("\n");
}
