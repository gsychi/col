// colval: exact values of Col permission positions (discovery only).
// Input lines:  h w PATTERN [label]   or   h w A B [label]
// PATTERN rows separated by '/', letters o b w . (permissions, not stones).
// Options: -t LOG2 memo size (default 25), -o print root options.
#include <chrono>
#include <cinttypes>
#include <iostream>
#include <map>
#include <memory>

#include "colcgt.hpp"
using namespace cc;

int main(int argc, char** argv) {
    int log2 = 25;
    bool showOptions = false;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-t" && i + 1 < argc)
            log2 = std::atoi(argv[++i]);
        else if (a == "-o")
            showOptions = true;
        else
            die("unknown argument " + a);
    }
    Table memo(log2);
    Canon canon;
    std::map<std::pair<int, int>, std::unique_ptr<Board>> boards;
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream is(line);
        int h, w;
        std::string t1;
        if (!(is >> h >> w >> t1)) die("bad input line: " + line);
        auto& bp = boards[{h, w}];
        if (!bp) bp.reset(new Board(h, w));
        const Board& bd = *bp;
        u64 A, B;
        if (t1.find_first_of("obw.") != std::string::npos) {
            parse_rows(bd, t1, A, B);
        } else {
            std::string t2;
            is >> t2;
            A = std::stoull(t1);
            B = std::stoull(t2);
        }
        std::string label;
        std::getline(is, label);
        while (!label.empty() && label[0] == ' ') label.erase(0, 1);
        if ((A | B) & ~bd.full) die("mask outside board: " + line);
        Engine eng(bd, memo, canon);
        auto t0 = std::chrono::steady_clock::now();
        Val v = eng.position(A, B);
        double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        std::printf("%s\t%s\t%.3fs\tnew=%" PRIu64 "\tmemo=%zu\n", label.c_str(), valstr(v).c_str(), secs,
                    eng.misses, memo.used);
        if (showOptions) {
            for (int who = 0; who < 2; ++who) {
                u64 M = who == 0 ? A : B;
                for (u64 m = M; m; m &= m - 1) {
                    int c = __builtin_ctzll(m);
                    u64 bit = u64(1) << c;
                    Val o = who == 0 ? eng.position(A & ~bd.closed[c], B & ~bit)
                                     : eng.position(A & ~bit, B & ~bd.closed[c]);
                    std::printf("  %s(%d,%d) -> %s\n", who == 0 ? "Blue" : "White", c / w, c % w,
                                valstr(o).c_str());
                }
            }
        }
        std::fflush(stdout);
    }
    return 0;
}
