// Restricted domino games for one pair: ./dmaj H W vr vc ur uc [what]
// what: bitmask 1 = D, 2 = Dmaj (Blue on majority only), 4 = Dmin (White on minority only)
#include "../center/colcore_fast.hpp"
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    int vr = std::atoi(argv[3]), vc = std::atoi(argv[4]), ur = std::atoi(argv[5]), uc = std::atoi(argv[6]);
    int what = argc > 7 ? std::atoi(argv[7]) : 7;
    setup(h, w);
    u64 maj = 0, mnr = 0;
    for (int v = 0; v < N; ++v) ((v / W + v % W) % 2 ? mnr : maj) |= u64{1} << v;
    u64 a, b; perms_from_stones(u64{1} << (vr * W + vc), u64{1} << (ur * W + uc), a, b);
    if (((vr + vc) & 1) == 1) std::swap(maj, mnr);  // "majority" = the parity class of v
    std::printf("%dx%d B(%d,%d) W(%d,%d):", h, w, vr, vc, ur, uc);
    if (what & 1) { std::printf(" D=%s", fmt(value(a, b)).c_str()); std::fflush(stdout); }
    if (what & 2) { std::printf(" Dmaj=%s", fmt(value(a & maj, b)).c_str()); std::fflush(stdout); }
    if (what & 4) { std::printf(" Dmin=%s", fmt(value(a, b & mnr)).c_str()); std::fflush(stdout); }
    std::printf("  memo=%zu\n", memo.size());
}
