// hylocal: certificate for a single claim G(PATTERN) <= Q + S* using exact
// local values only (discovery tool; verified by verify.py).
// usage: hylocal h w PATTERN|A,B Q S out.json [maxlog2]
#include <chrono>

#include "hybrid.hpp"
using namespace hy;

int main(int argc, char** argv) {
    if (argc < 7) die("usage: hylocal h w PATTERN|A,B Q S out.json [maxlog2]");
    int h = std::atoi(argv[1]), w = std::atoi(argv[2]);
    std::string spec = argv[3];
    int maxlog = argc > 7 ? std::atoi(argv[7]) : 25;
    Store st(maxlog);
    const Board& bd = st.board(h, w);
    u64 A, B;
    if (spec.find(',') != std::string::npos) {
        auto k = spec.find(',');
        A = std::stoull(spec.substr(0, k));
        B = std::stoull(spec.substr(k + 1));
    } else
        parse_rows(bd, spec, A, B);
    i64 q = parse_num(argv[4]);
    bool s = std::atoi(argv[5]) != 0;
    auto t0 = std::chrono::steady_clock::now();
    Val v = st.value(h, w, A, B);
    std::fprintf(stderr, "value %s claim <= %s%s\n", valstr(v).c_str(), numstr(q).c_str(), s ? "+*" : "");
    if (!st.claim_true(h, w, A, B, -q, s)) die("claim false");
    // Root in the h x w frame: identity transform expected for reporting only.
    Ref root = st.intern(h, w, A, B, -q, s);
    st.drain();
    st.emit(argv[6], {{"root", root.id}});
    double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    std::fprintf(stderr, "store nodes=%zu seconds=%.2f memo=%zu root_xf=(%d,%d,%d)\n", st.nodes.size(), secs,
                 st.memo.used, root.xf.sym, root.xf.dr, root.xf.dc);
    return 0;
}
