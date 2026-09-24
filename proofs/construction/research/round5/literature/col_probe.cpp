// Falsification probes for general-height ideas (GENERAL_IDEAS.md).
// Plain memoised minimax on Col grid positions, optionally summed with one
// dyadic number (canonical options) and one star. Single thread, lossy
// transposition table of fixed size (memory bounded).
//
// Values: value(A,B) returns x, eps with G - x - eps* certified to be a
// second-player win by direct search (this certification does not rely on the
// number-or-number-plus-star theorem; the theorem only guarantees success).
//
// Build: c++ -O2 -std=c++17 col_probe.cpp -o col_probe
// Modes:
//   col_probe mirror H W [maxS]   pure half-turn mirror with centre defect:
//                                 list mirror-reachable positions where Blue's
//                                 centre move wins
//   col_probe openings H W        exact values of all Blue openings (empty board)
//   col_probe centerdom H W       centre-domination test on mirror positions
//   col_probe value H W A B       exact value of one position
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
using u64 = std::uint64_t;

static int H, W, N;
static std::vector<u64> NB;  // closed neighbourhoods
static const int DEN = 64;   // number component in units of 1/64

struct Entry { u64 a, b; std::int32_t r; std::uint8_t flags, used, val; };
static std::vector<Entry> TT;
static u64 TT_MASK;
static u64 nodes = 0;

static inline u64 mix(u64 x) {
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL; x ^= x >> 27; x *= 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

static void setup(int h, int w, int ttlog) {
    H = h; W = w; N = h * w;
    if (N > 64) { std::fprintf(stderr, "board too large\n"); std::exit(1); }
    NB.assign(N, 0);
    for (int v = 0; v < N; ++v) {
        int r = v / W, c = v % W;
        u64 m = u64{1} << v;
        if (r > 0) m |= u64{1} << (v - W);
        if (r + 1 < H) m |= u64{1} << (v + W);
        if (c > 0) m |= u64{1} << (v - 1);
        if (c + 1 < W) m |= u64{1} << (v + 1);
        NB[v] = m;
    }
    TT.assign(std::size_t{1} << ttlog, Entry{0, 0, 0, 0, 0, 0});
    TT_MASK = (u64{1} << ttlog) - 1;
}

static inline int lowbit_units(int m) { return m & -m; }

// Number component r (units of 1/DEN): canonical Left/Right options.
static bool num_left(int r, int& out) {
    if (r % DEN == 0) { if (r > 0) { out = r - DEN; return true; } return false; }
    out = r - lowbit_units(r); return true;
}
static bool num_right(int r, int& out) {
    if (r % DEN == 0) { if (r < 0) { out = r + DEN; return true; } return false; }
    out = r + lowbit_units(r); return true;
}

// Does the player to move win?  blue_to_move selects the mover.
static bool win(u64 a, u64 b, int r, int star, bool blue) {
    ++nodes;
    u64 own = blue ? a : b;
    if (!own && star == 0) {
        int t;
        if (blue ? !num_left(r, t) : !num_right(r, t)) return false;
    }
    u64 key = mix(a * 0x9E3779B97F4A7C15ULL ^ mix(b) ^ (u64)(std::uint32_t)r * 0x100000001B3ULL ^ (u64)star << 1 ^ (u64)blue);
    Entry& e = TT[key & TT_MASK];
    std::uint8_t fl = (std::uint8_t)(star << 1 | (blue ? 1 : 0));
    if (e.used && e.a == a && e.b == b && e.r == r && e.flags == fl) return e.val;
    bool res = false;
    // board moves, shared cells first
    u64 opp = blue ? b : a;
    u64 order[2] = {own & opp, own & ~opp};
    for (int pass = 0; pass < 2 && !res; ++pass) {
        for (u64 z = order[pass]; z && !res; z &= z - 1) {
            int v = __builtin_ctzll(z);
            u64 bit = u64{1} << v;
            if (blue) res = !win(a & ~NB[v], b & ~bit, r, star, false);
            else res = !win(a & ~bit, b & ~NB[v], r, star, true);
        }
    }
    if (!res && star) res = !win(a, b, r, 0, !blue);
    if (!res) {
        int t;
        if (blue ? num_left(r, t) : num_right(r, t)) res = !win(a, b, t, star, !blue);
    }
    e.a = a; e.b = b; e.r = r; e.flags = fl; e.used = 1; e.val = res;
    return res;
}

// G <= q  iff Blue moving first loses in G - q.
static bool le(u64 a, u64 b, int qunits, int star = 0) { return !win(a, b, -qunits, star, true); }
static bool is_zero_sum(u64 a, u64 b, int qunits, int star) {
    return !win(a, b, -qunits, star, true) && !win(a, b, -qunits, star, false);
}

struct Val { bool ok; int x; int eps; };  // x in units of 1/DEN

static Val value(u64 a, u64 b) {
    int lo = -40 * DEN, hi = 40 * DEN;  // le(hi) true, le(lo) false for our boards
    while (hi - lo > 1) {
        int mid = lo + (hi - lo) / 2;
        if (le(a, b, mid)) hi = mid; else lo = mid;
    }
    if (is_zero_sum(a, b, hi, 0)) return {true, hi, 0};
    if (is_zero_sum(a, b, hi - 1, 1)) return {true, hi - 1, 1};
    return {false, hi, -1};
}

static std::string fmtv(Val v) {
    if (!v.ok) return "FAIL";
    int num = v.x, den = DEN;
    while (den > 1 && num % 2 == 0) { num /= 2; den /= 2; }
    std::string s;
    if (num == 0 && v.eps) return "*";
    s = std::to_string(num);
    if (den > 1) s += "/" + std::to_string(den);
    if (v.eps) s += "+*";
    return s;
}

static int rho(int v) { return N - 1 - v; }

// Enumerate mirror-reachable antisymmetric positions with centre live.
static void enumerate_mirror(std::vector<std::pair<u64, u64>>& out, int maxS) {
    int c = N / 2;
    std::vector<int> reps;  // one representative per rho-pair, outside N[c]
    for (int v = 0; v < N; ++v)
        if (v < rho(v) && !((NB[c] >> v) & 1)) reps.push_back(v);
    // DFS over pairs: choose none / v Blue / rho(v) Blue.
    auto dfs = [&](auto&& self, std::size_t i, u64 blue, u64 white, int cnt) -> void {
        if (i == reps.size()) {
            u64 full = (N == 64) ? ~u64{0} : ((u64{1} << N) - 1);
            u64 occ = blue | white;
            u64 bl = 0, wl = 0;
            for (int v = 0; v < N; ++v) {
                if ((occ >> v) & 1) continue;
                if (!(NB[v] & blue)) bl |= u64{1} << v;
                if (!(NB[v] & white)) wl |= u64{1} << v;
            }
            (void)full;
            out.push_back({bl, wl});
            return;
        }
        self(self, i + 1, blue, white, cnt);
        if (cnt >= maxS) return;
        int v = reps[i];
        for (int side = 0; side < 2; ++side) {
            int bv = side ? rho(v) : v, wv = rho(bv);
            if (NB[bv] & ~(u64{1} << bv) & blue) continue;  // Blue independent
            self(self, i + 1, blue | (u64{1} << bv), white | (u64{1} << wv), cnt + 1);
        }
    };
    dfs(dfs, 0, 0, 0, 0);
}

static void show(u64 a, u64 b) {
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int v = r * W + c;
            bool x = (a >> v) & 1, y = (b >> v) & 1;
            std::putchar(x && y ? 'o' : x ? 'b' : y ? 'w' : '.');
        }
        std::putchar(r + 1 < H ? '/' : ' ');
    }
}

int main(int argc, char** argv) {
    if (argc < 4) { std::fprintf(stderr, "usage: see header\n"); return 1; }
    std::string mode = argv[1];
    int h = std::atoi(argv[2]), w = std::atoi(argv[3]);
    setup(h, w, 25);
    int c = N / 2;
    u64 full = (N == 64) ? ~u64{0} : ((u64{1} << N) - 1);
    if (mode == "value") {
        u64 a = std::strtoull(argv[4], nullptr, 10), b = std::strtoull(argv[5], nullptr, 10);
        Val v = value(a, b);
        show(a, b); std::printf(" value %s nodes %llu\n", fmtv(v).c_str(), (unsigned long long)nodes);
        return 0;
    }
    if (mode == "openings") {
        for (int v = 0; v < N; ++v) {
            int r = v / W, cc = v % W;
            if (r > (H - 1) / 2 || cc > (W - 1) / 2) continue;  // symmetry quadrant
            Val val = value(full & ~NB[v], full & ~(u64{1} << v));
            std::printf("opening (%d,%d): value %s\n", r, cc, fmtv(val).c_str());
            std::fflush(stdout);
        }
        std::printf("nodes %llu\n", (unsigned long long)nodes);
        return 0;
    }
    if (mode == "mirror" || mode == "centerdom") {
        int maxS = argc > 4 ? std::atoi(argv[4]) : 64;
        std::vector<std::pair<u64, u64>> pos;
        enumerate_mirror(pos, maxS);
        std::printf("mirror-reachable positions with centre live: %zu\n", pos.size());
        long bad = 0, dom_fail = 0, cstar = 0, cneg = 0, czero = 0;
        for (auto [a, b] : pos) {
            if (!((a >> c) & 1)) continue;
            u64 a1 = a & ~NB[c], b1 = b & ~(u64{1} << c);
            if (mode == "mirror") {
                bool white_wins = win(a1, b1, 0, 0, false);
                if (!white_wins) {
                    ++bad;
                    if (bad <= 10) { std::printf("CENTRE WINS FOR BLUE at "); show(a, b); std::printf("\n"); }
                }
            } else {
                Val vc = value(a1, b1);
                if (!vc.ok) { std::printf("value failure\n"); continue; }
                if (vc.x == 0 && vc.eps == 0) ++czero;
                else if (vc.x == 0 && vc.eps == 1) ++cstar;
                else ++cneg;
                bool dominated = false;
                for (u64 z = a & ~(u64{1} << c); z && !dominated; z &= z - 1) {
                    int v = __builtin_ctzll(z);
                    Val vv = value(a & ~NB[v], b & ~(u64{1} << v));
                    // is  vc <= vv ?  compare x + eps*
                    int dx = vc.x - vv.x, de = (vc.eps + vv.eps) & 1;
                    bool leq = de ? (dx < 0) : (dx <= 0);
                    if (leq) dominated = true;
                }
                if (!dominated) {
                    ++dom_fail;
                    if (dom_fail <= 10) { std::printf("NOT DOMINATED: "); show(a, b); std::printf(" centre-child %s\n", fmtv(vc).c_str()); }
                }
            }
            std::fflush(stdout);
        }
        if (mode == "mirror") std::printf("positions where Blue's centre move wins: %ld\n", bad);
        else std::printf("centre child: negative %ld, star %ld, zero %ld; domination failures %ld\n", cneg, cstar, czero, dom_fail);
        std::printf("nodes %llu\n", (unsigned long long)nodes);
        return 0;
    }
    std::fprintf(stderr, "unknown mode\n");
    return 1;
}
