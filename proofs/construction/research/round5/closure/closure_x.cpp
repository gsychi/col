// closure_x: exact-bound closure search for 5-row strip families (EVIDENCE
// tool; its output is a candidate proof object that needs certification).
//
// Each family F gets a bound q_F[p] (a dyadic number, possibly plus a star)
// for all widths w >= 6 of parity p, measured exactly at w = 6, 7. The claim
// F_w <= q is proved by strong induction on w using, for every w >= 8 of
// parity p (G <= H iff no G^L >= H and no H^R <= G):
//   (B) every Blue opening G^L: a White reply and a cut whose piece values sum
//       to <= q, or no reply and a cut summing to strictly < q;
//   (W) every Right option r of q in canonical form: a White move and a cut
//       summing to <= r.  (k >= 0 integer: none; -k: -k+1; m/2^j, m odd:
//       (m+1)/2^j; x+*: x.)
// A piece of length <= 7 is valued exactly by search; a longer piece must be a
// family member and is bounded by that family's current bound. Reply and
// seam windows as in closure.cpp; widths 8..18 contain every opening class.
// A White-first rule at the largest checked width must place White's move
// within 6 columns of an end, so the same rule serves every larger width.
// If a family's checks fail, its bound is weakened (1/4 grid, 1/2 grid,
// integers) and every family that used the old bound is re-checked.
//
// Usage: closure_x [-j threads] [-L seconds] [-V valuecache] [-M maxfam] [-R rules.jsonl] [ROOT=KD|DD]
#define CLOSURE_NO_MAIN
#include "closure.cpp"

static bool xle(const XV& s, const XV& q) { i64 d = q.num - s.num; bool st = q.star ^ s.star; return d > 0 || (d == 0 && !st); }
static bool xlt(const XV& s, const XV& q) { return s.num < q.num; }
static bool xless_bound(const XV& a, const XV& b) { return a.num < b.num || (a.num == b.num && !a.star && b.star); }

static std::vector<XV> right_options(const XV& q) {
    XV r; r.ok = true;
    if (q.star) { r.num = q.num; r.star = false; return {r}; }
    if (q.num % ONE == 0) {
        if (q.num >= 0) return {};
        r.num = q.num + ONE; return {r};
    }
    i64 step = q.num & -q.num;
    r.num = q.num + step;
    return {r};
}
static XV round_up(const XV& v, i64 step) {
    XV r; r.ok = true; r.star = false;
    i64 m = v.num >= 0 ? (v.num / step) * step : -((-v.num + step - 1) / step) * step;
    if (m < v.num) m += step;
    if (v.star && m == v.num) m += step;
    r.num = m;
    return r;
}

struct XFam {
    Fam f;
    std::string key;
    XV q0[2], q[2];
    int level[2] = {0, 0};
    int status[2] = {0, 0};   // 0 untouched, 1 queued, 2 closed, -1 failed
    std::string why[2];
};
static std::vector<XFam> xf;
static std::map<std::string, int> xidx;
static std::map<std::pair<int,int>, std::set<std::pair<int,int>>> dependents;
static std::deque<std::pair<int,int>> xwork;
static std::string g_valuePath, g_rulesPath;
static FILE* g_rules = nullptr;

static void save_values_x() {
    if (g_valuePath.empty()) return;
    std::ofstream f(g_valuePath);
    for (auto& [k, v] : g_exact) if (v.ok) f << k << ' ' << v.num << ' ' << int(v.star) << '\n';
}
static void load_values_x() {
    std::ifstream f(g_valuePath);
    std::string k; long long n; int s;
    while (f >> k >> n >> s) { XV v; v.num = n; v.star = s; v.ok = true; g_exact[k] = v; }
}

static int get_xfamily(const Fam& f) {
    std::string k = fkey(f);
    auto it = xidx.find(k);
    if (it != xidx.end()) return it->second;
    if (!g_allowNew || g_newBudget <= 0) return -2;
    --g_newBudget;
    XFam x; x.f = f; x.key = k;
    x.q0[0] = x.q[0] = exact_value(member(f, 6));
    x.q0[1] = x.q[1] = exact_value(member(f, 7));
    xf.push_back(x);
    int id = int(xf.size()) - 1;
    xidx[k] = id;
    std::printf("  new family X%d q(even,odd)=(%s,%s)  w7=%s\n", id, xvstr(x.q[0]).c_str(), xvstr(x.q[1]).c_str(),
                draw(member(f, 7)).c_str());
    std::fflush(stdout);
    if (xf.size() % 10 == 0) save_values_x();
    return id;
}
static void xrequire(int id, int p) {
    if (xf[id].status[p] == 0) { xf[id].status[p] = 1; xwork.push_back({id, p}); }
}
static int xpiece_family(const Strip& piece) {
    int n = int(piece.size());
    for (int c = 3; c < n - 3; ++c) if (piece[c].a != FC || piece[c].b != FC) return -1;
    Fam f;
    for (int i = 0; i < 3; ++i) { f.L[i] = piece[i]; f.R[i] = piece[n - 3 + i]; }
    auto it = xidx.find(fkey(f));
    if (it != xidx.end()) return it->second;
    if (g_allowNew && g_newBudget > 0) return get_xfamily(f);
    int p = n & 1, best = -1;
    auto vs = variants(f);
    for (std::size_t i = 0; i < xf.size(); ++i) {
        if (!xf[i].q[p].ok) continue;
        for (auto& g : vs)
            if (dominated_by(g, xf[i].f)) {
                if (best < 0 || xless_bound(xf[i].q[p], xf[best].q[p])) best = int(i);
                break;
            }
    }
    return best >= 0 ? best : -2;
}
// Sum of piece values for the cut; false if some piece cannot be bounded.
static bool xevaluate(const Strip& s, const std::vector<int>& seams, XV& sum, std::string& desc,
                      std::vector<std::pair<int,int>>& needs) {
    int prev = 0;
    std::vector<int> cuts = seams;
    cuts.push_back(int(s.size()) - 1);
    sum = XV(); sum.ok = true;
    desc.clear();
    for (int j : cuts) {
        Strip piece(s.begin() + prev, s.begin() + j + 1);
        int len = int(piece.size());
        XV v;
        if (len <= 7) {
            v = exact_value(piece);
            if (!v.ok) return false;
            desc += "[" + std::to_string(len) + ":" + xvstr(v) + "]";
        } else {
            int id = xpiece_family(piece);
            if (id < 0) return false;
            v = xf[id].q[len & 1];
            if (!v.ok) return false;
            needs.push_back({id, len & 1});
            desc += "[X" + std::to_string(id) + "/" + std::to_string(len & 1) + ":" + xvstr(v) + "]";
        }
        sum.num += v.num; sum.star ^= v.star;
        prev = j + 1;
    }
    return true;
}
static std::vector<std::vector<int>> seam_sets_around(int c, int w) {
    const int RW = std::min(c, w - 1 - c) <= 6 ? 4 : 2;
    std::vector<int> sl;
    for (int j = c - RW; j <= c + RW - 1; ++j) if (j >= 0 && j <= w - 2) sl.push_back(j);
    std::vector<std::vector<int>> out;
    for (int j : sl) out.push_back({j});
    for (std::size_t i = 0; i < sl.size(); ++i)
        for (std::size_t k = i + 1; k < sl.size(); ++k) out.push_back({sl[i], sl[k]});
    return out;
}
// (B): Blue opened at column c of s1 (White to move).
static bool xfind_B_pass(const Strip& s1, int c, const XV& q, std::string& desc, std::vector<std::pair<int,int>>& needs) {
    int w = int(s1.size());
    const int RW = std::min(c, w - 1 - c) <= 6 ? 4 : 2;
    std::vector<std::pair<int,int>> replies{{-1, -1}};
    for (int cc = std::max(0, c - RW); cc <= std::min(w - 1, c + RW); ++cc)
        for (int rr = 0; rr < 5; ++rr) if ((s1[cc].b >> rr) & 1) replies.push_back({rr, cc});
    auto sets = seam_sets_around(c, w);
    for (int stage = 0; stage < 2; ++stage)
        for (auto [rr, cc] : replies) {
            Strip s2 = s1;
            if (rr >= 0) wmove(s2, rr, cc);
            for (auto& seams : sets) {
                if (int(seams.size()) != stage + 1) continue;
                for (auto& s3 : drop_variants(s2, seams, 0)) {
                    XV sum; std::string d; std::vector<std::pair<int,int>> nd;
                    if (!xevaluate(s3, seams, sum, d, nd)) continue;
                    bool ok = rr >= 0 ? xle(sum, q) : xlt(sum, q);
                    if (!ok) continue;
                    desc = (rr >= 0 ? "reply(" + std::to_string(rr) + "," + std::to_string(cc) + ")" : std::string("noreply")) + " " + d;
                    needs = nd;
                    return true;
                }
            }
        }
    return false;
}
// (W): White moves first in s (Blue to move after it); need a cut summing to <= r.
static bool xfind_W_pass(const Strip& s, const XV& r, bool nearEndOnly, std::string& desc,
                         std::vector<std::pair<int,int>>& needs) {
    int w = int(s.size());
    for (int y = 0; y < w; ++y) {
        if (nearEndOnly && std::min(y, w - 1 - y) > 6) continue;
        for (int yr = 0; yr < 5; ++yr) {
            if (!((s[y].b >> yr) & 1)) continue;
            Strip s2 = s;
            wmove(s2, yr, y);
            for (auto& seams : seam_sets_around(y, w))
                for (auto& s3 : drop_variants(s2, seams, 0)) {
                    XV sum; std::string d; std::vector<std::pair<int,int>> nd;
                    if (!xevaluate(s3, seams, sum, d, nd)) continue;
                    if (!xle(sum, r)) continue;
                    desc = "white(" + std::to_string(yr) + "," + std::to_string(y) + ") " + d;
                    needs = nd;
                    return true;
                }
        }
    }
    return false;
}
template <class F> static bool two_pass(F f) {
    g_allowNew = false;
    bool ok = f();
    g_allowNew = true;
    if (ok) return true;
    g_newBudget = 8;
    ok = f();
    g_newBudget = 1 << 30;
    return ok;
}
static void log_rule(int id, int p, int w, const std::string& kind, const std::string& what, const std::string& desc) {
    if (!g_rules) return;
    std::fprintf(g_rules, "{\"fam\":%d,\"parity\":%d,\"w\":%d,\"kind\":\"%s\",\"what\":\"%s\",\"rule\":\"%s\"}\n", id, p, w,
                 kind.c_str(), what.c_str(), desc.c_str());
}
static void xweaken(int id, int p, const std::string& reason) {
    XFam& F = xf[id];
    static const i64 steps[3] = {ONE / 4, ONE / 2, ONE};
    while (F.level[p] < 3) {
        XV nq = round_up(F.q0[p], steps[F.level[p]]);
        ++F.level[p];
        if (xless_bound(F.q[p], nq)) {
            std::printf("  X%d/%d weakened %s -> %s (%s)\n", id, p, xvstr(F.q[p]).c_str(), xvstr(nq).c_str(), reason.c_str());
            F.q[p] = nq;
            F.status[p] = 1;
            xwork.push_back({id, p});
            for (auto dp : dependents[{id, p}])
                if (xf[dp.first].status[dp.second] == 2) { xf[dp.first].status[dp.second] = 1; xwork.push_back(dp); }
            return;
        }
    }
    F.status[p] = -1;
    F.why[p] = reason;
    std::printf("  X%d/%d FAILED: %s\n", id, p, reason.c_str());
}
static void xcheck(int id, int p) {
    XV q = xf[id].q[p];
    if (!q.ok) { xf[id].status[p] = -1; xf[id].why[p] = "value unknown"; return; }
    std::vector<std::pair<int,int>> all;
    int nB = 0, nW = 0;
    for (int w = 8; w <= 18; ++w) {
        if ((w & 1) != p) continue;
        Strip s = member(xf[id].f, w);
        for (int c = 0; c < w; ++c)
            for (int r = 0; r < 5; ++r) {
                if (!((s[c].a >> r) & 1)) continue;
                Strip s1 = s;
                bmove(s1, r, c);
                std::string desc; std::vector<std::pair<int,int>> nd;
                if (!two_pass([&] { return xfind_B_pass(s1, c, xf[id].q[p], desc, nd); })) {
                    xweaken(id, p, "no B-rule at w=" + std::to_string(w) + " opening (" + std::to_string(r) + "," + std::to_string(c) + ")");
                    return;
                }
                log_rule(id, p, w, "B", "(" + std::to_string(r) + "," + std::to_string(c) + ")", desc);
                ++nB;
                for (auto& x : nd) all.push_back(x);
            }
        for (auto& ro : right_options(xf[id].q[p])) {
            std::string desc; std::vector<std::pair<int,int>> nd;
            bool nearEnd = w >= 17;
            if (!two_pass([&] { return xfind_W_pass(s, ro, nearEnd, desc, nd); })) {
                xweaken(id, p, "no W-rule for q^R=" + xvstr(ro) + " at w=" + std::to_string(w));
                return;
            }
            log_rule(id, p, w, "W", xvstr(ro), desc);
            ++nW;
            for (auto& x : nd) all.push_back(x);
        }
    }
    xf[id].status[p] = 2;
    xf[id].why[p] = std::to_string(nB) + " B-rules, " + std::to_string(nW) + " W-rules";
    for (auto [nid, np] : all) {
        dependents[{nid, np}].insert({id, p});
        xrequire(nid, np);
    }
    std::printf("  X%d/%d q=%s CLOSED at this level (%s)\n", id, p, xvstr(xf[id].q[p]).c_str(), xf[id].why[p].c_str());
    std::fflush(stdout);
    if (g_rules) std::fflush(g_rules);
}

int main(int argc, char** argv) {
    std::string root = "KD";
    int maxFam = 400;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-j") g_threads = std::atoi(argv[++i]);
        else if (a == "-L") g_limit = std::atof(argv[++i]);
        else if (a == "-V") g_valuePath = argv[++i];
        else if (a == "-M") maxFam = std::atoi(argv[++i]);
        else if (a == "-R") g_rulesPath = argv[++i];
        else root = a;
    }
    g_start = std::chrono::steady_clock::now();
    Cache vc(24); TT tt(24);
    g_vc = &vc; g_tt = &tt;
    if (!g_valuePath.empty()) load_values_x();
    if (!g_rulesPath.empty()) g_rules = std::fopen(g_rulesPath.c_str(), "w");
    auto letter = [](const char* p) { Col c{0, 0}; for (int r = 0; r < 5; ++r) { if (p[r] == 'o' || p[r] == 'b') c.a |= 1u << r; if (p[r] == 'o' || p[r] == 'w') c.b |= 1u << r; } return c; };
    Fam f;
    Col N{FC, FC};
    f.L[0] = letter("obwbo"); f.L[1] = N; f.L[2] = N;
    f.R[0] = N; f.R[1] = N; f.R[2] = letter("obwbo");
    if (root == "KD") { Strip s = member(f, 8); wmove(s, 2, 0); for (int i = 0; i < 3; ++i) f.L[i] = s[i]; }
    int rid = get_xfamily(f);
    // Root target: K_n <= 0 (odd), K_n <= 1 (even); the exact values measured at 6, 7.
    for (int p = 0; p < 2; ++p) xrequire(rid, p);
    while (!xwork.empty() && int(xf.size()) <= maxFam) {
        auto [id, p] = xwork.front(); xwork.pop_front();
        if (xf[id].status[p] != 1) continue;
        std::printf("check X%d parity %d (q %s, level %d)  [families %zu, queue %zu, searches %" PRIu64 ", %.0fs]\n", id, p,
                    xvstr(xf[id].q[p]).c_str(), xf[id].level[p], xf.size(), xwork.size(), g_queries, since_start());
        std::fflush(stdout);
        xcheck(id, p);
        save_values_x();
        if (std::ifstream("/workspace/proofs/construction/research/round5/STOP")) { std::printf("STOP file found\n"); break; }
    }
    int closed = 0, failed = 0, pending = 0;
    for (auto& x : xf) for (int p = 0; p < 2; ++p) {
        if (x.status[p] == 2) ++closed; else if (x.status[p] == -1) ++failed; else if (x.status[p] == 1) ++pending;
    }
    std::printf("\nSUMMARY families %zu; required (family,parity): closed %d, failed %d, pending %d; searches %" PRIu64 "; %.0fs\n",
                xf.size(), closed, failed, pending, g_queries, since_start());
    for (std::size_t i = 0; i < xf.size(); ++i)
        for (int p = 0; p < 2; ++p)
            if (xf[i].status[p] != 0)
                std::printf("  X%zu/%d q %s (exact %s, level %d) status %d %s   %s\n", i, p, xvstr(xf[i].q[p]).c_str(),
                            xvstr(xf[i].q0[p]).c_str(), xf[i].level[p], xf[i].status[p], xf[i].why[p].c_str(),
                            draw(member(xf[i].f, 7)).c_str());
    save_values_x();
    if (g_rules) std::fclose(g_rules);
    return failed ? 1 : 0;
}
