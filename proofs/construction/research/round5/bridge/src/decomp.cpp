// decomp: search one-sided vertical-cut decompositions after a Blue opening
// and a White reply on an empty H x W board (discovery only).
//
// For a partition of the columns into consecutive blocks, every seam edge whose
// two endpoints are both White-legal must have White retired at one endpoint.
// Blue keeps exactly its actual permissions (the minimal admissible choice) and
// White keeps every permission not retired (retiring more never helps White).
// A dynamic program over column boundaries keeps, per retirement state, the
// minimal number part of the block-value sum for each star parity.
//
// usage: decomp H W MAXW [opening_index|-1] [reply_index|-2 all|-1 none] [maxlog2]
// Output: one line per (opening, reply) giving the best sum and a witness.
#include <array>
#include <chrono>
#include <cinttypes>
#include <climits>
#include <iostream>
#include <vector>

#include "colcgt.hpp"
using namespace cc;

struct Step {
    int prevK = -1, prevS = -1, prevStar = -1, width = 0, leftRet = 0;
    Val val;
};

struct Result {
    bool ok = false;
    Val best;
    bool have = false;
    std::vector<std::string> blocks;
};

static const i64 INF = LLONG_MAX / 4;

Result run_dp(const Board& bd, Engine& eng, u64 A, u64 B, int maxw, bool strict) {
    const int H = bd.h, W = bd.w;
    int S = 1 << H;
    // best[k][s][star]
    std::vector<std::array<i64, 2>> best((W + 1) * S, {INF, INF});
    std::vector<std::array<Step, 2>> from((W + 1) * S);
    best[0][0] = 0;
    auto colbit = [&](int r, int c) { return u64(1) << (r * W + c); };
    for (int k = 0; k < W; ++k)
        for (int s = 0; s < S; ++s)
            for (int st = 0; st < 2; ++st) {
                i64 cur = best[k * S + s][st];
                if (cur >= INF) continue;
                for (int wd = 1; wd <= maxw && k + wd <= W; ++wd) {
                    u64 block = 0;
                    for (int r = 0; r < H; ++r)
                        for (int c = k; c < k + wd; ++c) block |= colbit(r, c);
                    u64 Bb = B & block;
                    for (int r = 0; r < H; ++r)
                        if (s >> r & 1) Bb &= ~colbit(r, k);
                    u64 Ab = A & block;
                    int last = k + wd - 1;
                    int choice = 0;
                    if (k + wd < W)
                        for (int r = 0; r < H; ++r)
                            if ((Bb & colbit(r, last)) && (B & colbit(r, last + 1))) choice |= 1 << r;
                    // enumerate subsets L of choice (retire at left endpoint)
                    for (int L = choice;; L = (L - 1) & choice) {
                        u64 Bl = Bb;
                        for (int r = 0; r < H; ++r)
                            if (L >> r & 1) Bl &= ~colbit(r, last);
                        Val v = eng.position(Ab, Bl);
                        int ns = (k + wd < W) ? (choice & ~L) : 0;
                        int nst = st ^ (v.star ? 1 : 0);
                        i64 nv = cur + v.num;
                        auto& slot = best[(k + wd) * S + ns][nst];
                        if (nv < slot) {
                            slot = nv;
                            Step stp;
                            stp.prevK = k;
                            stp.prevS = s;
                            stp.prevStar = st;
                            stp.width = wd;
                            stp.leftRet = L;
                            stp.val = v;
                            from[(k + wd) * S + ns][nst] = stp;
                        }
                        if (L == 0) break;
                    }
                }
            }
    Result res;
    i64 b0 = best[W * S + 0][0], b1 = best[W * S + 0][1];
    int pick = -1;
    if (strict) {
        if (b0 < 0 && (b1 >= INF || b0 <= b1)) pick = 0;
        if (b1 < 0 && (pick < 0 || b1 < b0)) pick = 1;
    } else {
        if (b0 <= 0) pick = 0;
        else if (b1 < 0) pick = 1;
    }
    if (pick < 0) {
        // report the best available anyway
        if (b0 < INF && (b1 >= INF || b0 <= b1)) pick = 0, res.ok = false;
        else if (b1 < INF) pick = 1, res.ok = false;
        else return res;
    } else
        res.ok = true;
    res.have = true;
    res.best = Val{best[W * S][pick], pick == 1};
    // reconstruct
    int k = W, s = 0, st = pick;
    std::vector<std::string> blocks;
    while (k > 0) {
        const Step& stp = from[k * S + s][st];
        int bk = stp.prevK, wd = stp.width;
        // rebuild block permissions for printing
        u64 block = 0;
        for (int r = 0; r < H; ++r)
            for (int c = bk; c < bk + wd; ++c) block |= colbit(r, c);
        u64 Bb = B & block;
        for (int r = 0; r < H; ++r)
            if (stp.prevS >> r & 1) Bb &= ~colbit(r, bk);
        for (int r = 0; r < H; ++r)
            if (stp.leftRet >> r & 1) Bb &= ~colbit(r, bk + wd - 1);
        u64 Ab = A & block;
        std::string pat;
        for (int r = 0; r < H; ++r) {
            if (r) pat += "/";
            for (int c = bk; c < bk + wd; ++c) {
                u64 b = colbit(r, c);
                bool a = Ab & b, w = Bb & b;
                pat += a && w ? 'o' : a ? 'b' : w ? 'w' : '.';
            }
        }
        blocks.push_back("c" + std::to_string(bk) + "w" + std::to_string(wd) + ":" + pat + "=" + valstr(stp.val));
        int pk = stp.prevK, ps = stp.prevS, pst = stp.prevStar;
        k = pk;
        s = ps;
        st = pst;
    }
    res.blocks.assign(blocks.rbegin(), blocks.rend());
    return res;
}

int main(int argc, char** argv) {
    if (argc < 4) die("usage: decomp H W MAXW [opening|-1] [reply|-2 all|-1 none] [maxlog2]");
    int H = std::atoi(argv[1]), W = std::atoi(argv[2]), maxw = std::atoi(argv[3]);
    int onlyOpen = argc > 4 ? std::atoi(argv[4]) : -1;
    int onlyReply = argc > 5 ? std::atoi(argv[5]) : -2;
    int maxlog = argc > 6 ? std::atoi(argv[6]) : 25;
    Board bd(H, W);
    Table memo(maxlog);
    Canon canon;
    Engine eng(bd, memo, canon);
    for (int r = 0; r < (H + 1) / 2; ++r)
        for (int c = 0; c < (W + 1) / 2; ++c) {
            int v = r * W + c;
            if (onlyOpen >= 0 && v != onlyOpen) continue;
            u64 A0 = bd.full & ~bd.closed[v], B0 = bd.full & ~(u64(1) << v);
            int nsucc = 0;
            auto t0 = std::chrono::steady_clock::now();
            // no-reply strict decomposition
            if (onlyReply == -2 || onlyReply == -1) {
                Result res = run_dp(bd, eng, A0, B0, maxw, true);
                std::printf("open (%d,%d) reply none: %s best=%s", r, c, res.ok ? "OK" : "--",
                            res.have ? valstr(res.best).c_str() : "none");
                if (res.ok)
                    for (auto& b : res.blocks) std::printf(" | %s", b.c_str());
                std::printf("\n");
                if (res.ok) ++nsucc;
                std::fflush(stdout);
            }
            for (int u = 0; u < bd.n; ++u) {
                if (onlyReply >= 0 && u != onlyReply) continue;
                if (onlyReply == -1) break;
                if (!(B0 >> u & 1)) continue;
                u64 A = A0 & ~(u64(1) << u), B = B0 & ~bd.closed[u];
                Result res = run_dp(bd, eng, A, B, maxw, false);
                if (res.ok) {
                    ++nsucc;
                    std::printf("open (%d,%d) reply (%d,%d): OK best=%s", r, c, u / W, u % W,
                                valstr(res.best).c_str());
                    for (auto& b : res.blocks) std::printf(" | %s", b.c_str());
                    std::printf("\n");
                } else if (onlyReply >= 0) {
                    std::printf("open (%d,%d) reply (%d,%d): -- best=%s\n", r, c, u / W, u % W,
                                res.have ? valstr(res.best).c_str() : "none");
                }
                std::fflush(stdout);
            }
            double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            std::printf("SUMMARY open (%d,%d): %d successes, %.1fs, memo=%zu\n", r, c, nsucc, secs, memo.used);
            std::fflush(stdout);
        }
    return 0;
}
