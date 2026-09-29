// pval: exact values of 5-row pieces by bottom-up evaluation (colcore.h
// Solver::position: option values, simplest-number rule, component splitting,
// memo shared across queries). EVIDENCE tool used by djcut.py.
// Input lines "w A B" (row-major masks on a 5 x w board); output one value per line.
#include "colcore.h"

int main(int argc, char** argv) {
    int vlog = argc > 1 ? std::atoi(argv[1]) : 22;
    Cache memo(vlog);
    std::vector<std::unique_ptr<Board>> boards(17);
    std::vector<std::unique_ptr<Solver>> solvers(17);
    int w;
    unsigned long long A, B;
    while (std::scanf("%d %llu %llu", &w, &A, &B) == 3) {
        if (w < 1 || w > 12) die("width out of range");
        if (!boards[w]) {
            boards[w].reset(new Board(5, w));
            solvers[w].reset(new Solver(*boards[w], memo));
        }
        Val v = solvers[w]->position(A, B);
        std::printf("%s\n", valstr(v).c_str());
        std::fflush(stdout);
    }
    return 0;
}
