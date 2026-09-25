// Values of h x k strips whose last column has a prescribed tint pattern (rest neutral).
// Pattern string over {o,b,w,.} top to bottom, e.g. "bwo".
// ./strips h kmax pattern [pattern2]   (pattern2, if given, tints the first column too)
#include "../center/colcore_fast.hpp"
#include <cstring>
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), kmax = std::atoi(argv[2]);
    const char* pat = argv[3];
    const char* pat2 = argc > 4 ? argv[4] : nullptr;
    for (int k = 1; k <= kmax; ++k) {
        setup(h, k);
        u64 a = fullmask(), b = fullmask();
        auto tint = [&](int c, const char* p) {
            for (int r = 0; r < h; ++r) {
                u64 bit = u64{1} << (r * k + c);
                if (p[r] == 'b' || p[r] == '.') b &= ~bit;
                if (p[r] == 'w' || p[r] == '.') a &= ~bit;
            }
        };
        if (pat2) tint(0, pat2);
        tint(k - 1, pat);
        std::printf("%dx%d [%s%s%s] = %s\n", h, k, pat2 ? pat2 : "", pat2 ? "|..|" : "", pat, fmt(value(a, b)).c_str());
        std::fflush(stdout);
    }
}
