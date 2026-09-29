// PF-type positions on an H x K strip with boundary modifications on the end columns.
// Stones: Blue on majority cells (r+c even), White on minority cells, all subsets.
// Column 0 and column K-1 get a 3-char spec (top to bottom) over
//   n = unchanged, w = White permission removed, b = Blue permission removed, d = both removed;
// upper-case W, B, D mean the same but the cell may also hold a stone (then nothing changes);
// lower-case modified cells are required to be free. Prints the histogram of value - F,
// F = #free X - #free Y (all free cells), split by whether White has a stone.
// ./wp_bnd H K Lspec Rspec [v]   (v: also print every position with its value - F)
#include "../center/colcore_fast.hpp"
#include <cctype>
#include <map>
#include <string>
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), k = std::atoi(argv[2]);
    std::string L = argv[3], R = argv[4];
    bool verbose = argc > 5;
    setup(h, k);
    u64 majm = 0;
    for (int v = 0; v < N; ++v) if ((v / W + v % W) % 2 == 0) majm |= u64{1} << v;
    u64 rmB = 0, rmW = 0, modm = 0;
    auto apply = [&](int c, const std::string& s) {
        for (int r = 0; r < h; ++r) {
            u64 bit = u64{1} << (r * W + c);
            char ch = s[r], lo = (char)std::tolower(ch);
            if (lo == 'w' || lo == 'd') rmW |= bit;
            if (lo == 'b' || lo == 'd') rmB |= bit;
            if (ch == 'w' || ch == 'b' || ch == 'd') modm |= bit;
        }
    };
    apply(0, L); apply(k - 1, R);
    std::map<std::pair<int, std::string>, long> hist;
    u64 full = fullmask();
    for (u64 blue = majm & ~modm;; blue = (blue - 1) & majm & ~modm) {
        u64 ym = full & ~majm & ~modm;
        for (u64 white = ym;; white = (white - 1) & ym) {
            u64 a, b; perms_from_stones(blue, white, a, b);
            a &= ~rmB; b &= ~rmW;            u64 occ = blue | white;
            i64 F = (i64)(__builtin_popcountll(majm & ~occ) - __builtin_popcountll(full & ~majm & ~occ)) * ONE;
            Val g = value(a, b);
            std::string d = fmt(Val{g.x - F, g.e});
            hist[{white != 0, d}]++;
            if (verbose) { show(a, b); std::printf("  F=%lld  G-F=%s\n", (long long)(F / ONE), d.c_str()); }
            if (!white) break;
        }
        if (!blue) break;
    }
    for (auto& [key, cnt] : hist)
        std::printf("%dx%d L=%s R=%s %s: G-F = %s x%ld\n", h, k, L.c_str(), R.c_str(),
                    key.first ? "Q!=0" : "Q=0 ", key.second.c_str(), cnt);
}
