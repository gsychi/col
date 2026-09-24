// colval: exact CGT values of Col permission positions (A,B) on an h x w grid.
//
// Discovery tool (EVIDENCE level). Values are exact dyadic numbers plus an
// optional star. The recursion does NOT assume the classical Col theorem:
//   * the value of a disjoint sum is the sum of the component values
//     (components = connected pieces of the "interaction graph": adjacent
//     cells interact iff some player may play on both);
//   * dominated options are removed only when domination follows from the
//     permission comparison principle (same graph, Blue superset, White subset);
//   * the value of {options} is computed by the simplicity theorem when the
//     option interval is nonempty, and as {a|a} = a+* when both boundary
//     options are the pure number a (all other options being dominated).
// Any option set outside these cases (hot, or a mixed star boundary such as
// {a | a+*}) aborts with a diagnostic, since it would not be a number or a
// number plus star.
//
// Input (stdin), one query per line:   h w A B label
//   A = Blue-legal mask, B = White-legal mask, row-major, bit r*w+c.
// Output: label value time new-misses cache-used
// Options: -t LOG2  cache size in buckets of 4 entries (default 22)
//          -j N     threads (default 1)
//          -o       also print the value after every root move
#include "colcore.h"

int main(int argc, char** argv) {
    int log2 = 22, threads = 1;
    bool showOptions = false;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-t" && i + 1 < argc) log2 = std::atoi(argv[++i]);
        else if (a == "-j" && i + 1 < argc) threads = std::atoi(argv[++i]);
        else if (a == "-o") showOptions = true;
        else die("unknown argument " + a);
    }
    Cache memo(log2);
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream is(line);
        int h, w;
        unsigned long long A, B;
        std::string label;
        if (!(is >> h >> w >> A >> B)) die("bad input line: " + line);
        std::getline(is, label);
        while (!label.empty() && label[0] == ' ') label.erase(0, 1);
        Board bd(h, w);
        if ((A | B) & ~bd.full) die("mask outside board: " + line);
        auto t0 = std::chrono::steady_clock::now();
        std::vector<std::unique_ptr<Solver>> solvers;
        for (int t = 0; t < std::max(1, threads); ++t) solvers.emplace_back(new Solver(bd, memo));
        if (threads > 1) {
            // Depth-2 task split: evaluate all grandchildren in parallel.
            std::vector<std::pair<Mask, Mask>> tasks;
            for (auto& c : solvers[0]->children(A, B))
                for (auto& g : solvers[0]->children(c.first, c.second)) tasks.push_back(g);
            std::atomic<std::size_t> next{0};
            std::vector<std::thread> pool;
            for (int t = 0; t < threads; ++t)
                pool.emplace_back([&, t] {
                    for (;;) {
                        std::size_t i = next.fetch_add(1);
                        if (i >= tasks.size()) break;
                        solvers[t]->position(tasks[i].first, tasks[i].second);
                    }
                });
            for (auto& th : pool) th.join();
        }
        Val v = solvers[0]->position(A, B);
        double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        std::uint64_t miss = 0;
        for (auto& s : solvers) miss += s->misses;
        std::printf("%s\t%s\t%.3fs\tnew=%" PRIu64 "\tused=%" PRIu64 "\tevict=%" PRIu64 "\n", label.c_str(),
                    valstr(v).c_str(), secs, miss, (std::uint64_t)memo.used.load(),
                    (std::uint64_t)memo.evictions.load());
        if (showOptions) {
            for (int who = 0; who < 2; ++who) {
                Mask M = who == 0 ? A : B;
                for (Mask m = M; m; m &= m - 1) {
                    int c = __builtin_ctzll(m);
                    Mask bit = Mask(1) << c;
                    Val o = who == 0 ? solvers[0]->position(A & ~bd.closed[c], B & ~bit)
                                     : solvers[0]->position(A & ~bit, B & ~bd.closed[c]);
                    std::printf("  %s(%d,%d) -> %s\n", who == 0 ? "Blue" : "White", c / w, c % w,
                                valstr(o).c_str());
                }
            }
        }
        std::fflush(stdout);
    }
    return 0;
}
