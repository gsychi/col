// PF-type positions on an H x K strip with boundary modifications on the end columns.
// Stones: Blue on majority cells (r+c even), White on minority cells, all subsets.
// Column 0 and column K-1 get a 3-char spec (top to bottom) over
//   n = unchanged, w = White permission removed, b = Blue permission removed, d = both removed;
// upper-case W, B, D mean the same but the cell may also hold a stone (then nothing changes);
// lower-case modified cells are required to be free. Prints the histogram of value - F,
// F = #free X - #free Y (all free cells), split by content: W = some White stone
// (W* = a White stone on an upper-case spec cell), b = Blue stones only, e = empty.
// Environment: QZERO=1 enumerates White-free positions only; FORCEB=r,c forces a Blue stone.
// ./wp_bnd H K Lspec Rspec [v]   (v: also print every position with its value - F)
#include "../center/colcore_fast.hpp"
#include <cctype>
#include <cstring>
#include <map>
#include <string>
int main(int argc, char** argv) {
    int h = std::atoi(argv[1]), k = std::atoi(argv[2]);
    std::string L = argv[3], R = argv[4];
    bool verbose = argc > 5;
    bool qzero = std::getenv("QZERO") != nullptr;
    setup(h, k);
    u64 majm = 0;
    for (int v = 0; v < N; ++v) if ((v / W + v % W) % 2 == 0) majm |= u64{1} << v;
    u64 forced = 0;
    if (const char* f = std::getenv("FORCEB")) {
        int r = std::atoi(f), c = std::atoi(std::strchr(f, ',') + 1);
        forced = u64{1} << (r * W + c);
        if (!(forced & majm)) { std::fprintf(stderr, "FORCEB must be a majority cell\n"); return 1; }
    }
    u64 rmB = 0, rmW = 0, modm = 0, upm = 0;
    auto apply = [&](int c, const std::string& s) {
        for (int r = 0; r < h; ++r) {
            u64 bit = u64{1} << (r * W + c);
            char ch = s[r], lo = (char)std::tolower(ch);
            if (lo == 'w' || lo == 'd') rmW |= bit;
            if (lo == 'b' || lo == 'd') rmB |= bit;
            if (ch == 'w' || ch == 'b' || ch == 'd') modm |= bit;
            if (ch == 'W' || ch == 'B' || ch == 'D') upm |= bit;
        }
    };
    apply(0, L); apply(k - 1, R);
    std::map<std::pair<std::string, std::string>, long> hist;
    u64 full = fullmask();
    u64 xm = majm & ~modm & ~forced;
    for (u64 bsub = xm;; bsub = (bsub - 1) & xm) {
        u64 blue = bsub | forced;
        u64 ym = qzero ? 0 : full & ~majm & ~modm;
        for (u64 white = ym;; white = (white - 1) & ym) {
            u64 a, b; perms_from_stones(blue, white, a, b);
            a &= ~rmB; b &= ~rmW;
            u64 occ = blue | white;
            i64 F = (i64)(__builtin_popcountll(majm & ~occ) - __builtin_popcountll(full & ~majm & ~occ)) * ONE;
            Val g = value(a, b);
            std::string d = fmt(Val{g.x - F, g.e});
            std::string cls = white ? ((white & upm) ? "W*" : "W") : (blue ? "b" : "e");
            hist[{cls, d}]++;
            if (verbose) { show(a, b); std::printf("  F=%lld  G-F=%s\n", (long long)(F / ONE), d.c_str()); }
            if (!white) break;
        }
        if (!bsub) break;
    }
    for (auto& [key, cnt] : hist)
        std::printf("%dx%d L=%s R=%s%s %-2s: G-F = %s x%ld\n", h, k, L.c_str(), R.c_str(),
                    forced ? " (forced Blue)" : "", key.first.c_str(), key.second.c_str(), cnt);
}
