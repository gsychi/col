// closure: search for a closed system of 5-row strip families with integer
// upper bounds (EVIDENCE tool; its output is a candidate proof object that
// still needs certification).
//
// A family F is a 5 x w strip whose first three and last three columns are
// fixed blocks and whose middle columns are neutral (legal for both). Its
// bound beta_F[p] for widths w >= 6 of parity p is measured at w = 6, 7 and
// is a conjecture for larger w. The conjecture is proved by strong induction
// on w if, for every w >= 8 of parity p and every Blue opening, a rule exists
// (INTEGER_BOUNDS.md, Lemma A):
//   * no White reply, cut into pieces with bound sum <= beta_F[p] - 1; or
//   * a White reply, cut into pieces with bound sum <= beta_F[p].
// A piece of length <= 7 is bounded directly (search); a longer piece must be
// a family member and is bounded by that family's beta. Widths 8..12 are
// checked explicitly; w = 16 / 17 represent every w >= 13 of that parity
// (all pieces then have length >= 6, and their bounds depend only on parity).
// A family with beta < 0 at some parity is reduced by a White private move in
// an end block (COL_VALUES Lemma 4(4)): F <= F' - 1 with F' = F after it.
//
// Usage: closure [-j threads] [-L seconds per search] [-C cache.txt] [-M maxfam] ROOT
//   ROOT = KD (DD after White (2,0)) | DD
#define main colout5_main
#include "colout5.cpp"
#undef main

#include <fstream>
#include <map>
#include <set>
#include <deque>
#include <functional>

struct Col { std::uint8_t a, b; };
using Strip = std::vector<Col>;
static const std::uint8_t FC = 31;

static bool bmove(Strip& s, int r, int c) {
    if (!((s[c].a >> r) & 1)) return false;
    s[c].a &= ~(1u << r); s[c].b &= ~(1u << r);
    if (r > 0) s[c].a &= ~(1u << (r - 1));
    if (r < 4) s[c].a &= ~(1u << (r + 1));
    if (c > 0) s[c - 1].a &= ~(1u << r);
    if (c + 1 < int(s.size())) s[c + 1].a &= ~(1u << r);
    return true;
}
static bool wmove(Strip& s, int r, int c) {
    if (!((s[c].b >> r) & 1)) return false;
    s[c].a &= ~(1u << r); s[c].b &= ~(1u << r);
    if (r > 0) s[c].b &= ~(1u << (r - 1));
    if (r < 4) s[c].b &= ~(1u << (r + 1));
    if (c > 0) s[c - 1].b &= ~(1u << r);
    if (c + 1 < int(s.size())) s[c + 1].b &= ~(1u << r);
    return true;
}
static std::uint8_t vflip5(std::uint8_t x) {
    std::uint8_t y = 0;
    for (int r = 0; r < 5; ++r) if ((x >> r) & 1) y |= 1u << (4 - r);
    return y;
}
static std::string skey(const Strip& s) {
    std::string k;
    for (auto& c : s) { k += char('a' + (c.a & 31)); k += char('A' + (c.b & 31)); }
    return k;
}
static std::string canon(const Strip& s) {
    Strip v = s, h(s.rbegin(), s.rend()), vh;
    for (auto& c : v) { c.a = vflip5(c.a); c.b = vflip5(c.b); }
    vh.assign(v.rbegin(), v.rend());
    return std::min(std::min(skey(s), skey(v)), std::min(skey(h), skey(vh)));
}
static std::string draw(const Strip& s) {
    std::string out;
    for (int r = 0; r < 5; ++r) {
        for (auto& c : s) {
            bool x = (c.a >> r) & 1, y = (c.b >> r) & 1;
            out += x && y ? 'o' : x ? 'b' : y ? 'w' : '.';
        }
        if (r < 4) out += '/';
    }
    return out;
}

// ------------------------------------------------------------ bound oracle
static int g_threads = 4, g_smax = 14;
static double g_limit = 300;
static Cache* g_vc;
static TT* g_tt;
static std::map<std::string, int> g_bound;   // canonical strip -> ceil bound (INT_MIN = unknown)
static std::string g_cachePath;
static std::uint64_t g_queries = 0;
static const int UNKNOWN = -1000;

static void save_cache() {
    if (g_cachePath.empty()) return;
    std::ofstream f(g_cachePath);
    for (auto& [k, v] : g_bound) if (v != UNKNOWN) f << k << ' ' << v << '\n';
}
static void load_cache() {
    std::ifstream f(g_cachePath);
    std::string k; int v;
    while (f >> k >> v) g_bound[k] = v;
}
// 1 = Blue-first LOSES G - k (so G <= k), 0 = Blue wins, -1 = timeout
static int le(const Strip& s, int k) {
    int w = int(s.size());
    Board bd(5, w);
    Mask A = 0, B = 0;
    for (int c = 0; c < w; ++c)
        for (int r = 0; r < 5; ++r) {
            if ((s[c].a >> r) & 1) A |= Mask(1) << (r * w + c);
            if ((s[c].b >> r) & 1) B |= Mask(1) << (r * w + c);
        }
    if (!(A | B)) return k >= 0 ? 1 : 0;
    ++g_queries;
    g_deadline = since_start() + g_limit;
    if (__builtin_popcountll(A | B) <= 30) {
        // Small pieces: one persistent single-threaded search per width; the
        // threaded root driver sleeps 200 ms per query and dominates here.
        static std::map<int, std::unique_ptr<Board>> boards;
        static std::map<int, std::unique_ptr<Search>> searches;
        auto& bp = boards[w];
        if (!bp) bp.reset(new Board(5, w));
        auto& sp = searches[w];
        if (!sp) sp.reset(new Search(*bp, *g_vc, *g_tt, g_smax));
        int r = sp->win(A, B, -i64(k) * ONE, false, 0);
        if (r < 0) return -1;
        return r ? 0 : 1;
    }
    RootResult r = root_win(bd, *g_vc, *g_tt, g_smax, g_threads, A, B, -i64(k) * ONE, false, "le");
    if (r.win < 0) return -1;
    return r.win ? 0 : 1;
}
static int bound(const Strip& s) {
    std::string k = canon(s);
    auto it = g_bound.find(k);
    if (it != g_bound.end()) return it->second;
    bool live = false;
    for (auto& c : s) if (c.a | c.b) live = true;
    int res;
    if (!live) res = 0;
    else {
        int x = 0, t = le(s, x);
        if (t < 0) res = UNKNOWN;
        else if (t == 1) {
            res = x;
            while (res > -8) { int u = le(s, res - 1); if (u < 0) { res = UNKNOWN; break; } if (!u) break; --res; }
        } else {
            res = UNKNOWN;
            for (int y = 1; y <= 10; ++y) { int u = le(s, y); if (u < 0) break; if (u) { res = y; break; } }
        }
    }
    g_bound[k] = res;
    if (g_bound.size() % 50 == 0) save_cache();
    return res;
}

// ------------------------------------------------------------ families
struct Fam { Col L[3], R[3]; };
static Strip member(const Fam& f, int w) {
    Strip s(w, Col{FC, FC});
    for (int i = 0; i < 3; ++i) { s[i] = f.L[i]; s[w - 3 + i] = f.R[i]; }
    return s;
}
static std::string fkey(const Fam& f) { return canon(member(f, 7)); }
struct FamInfo {
    Fam f;
    std::string key, name;
    int beta[2] = {UNKNOWN, UNKNOWN};
    int status[2] = {0, 0};   // 0 untouched, 1 queued, 2 proved-by-table, 3 proved-by-reserve, -1 failed
    std::string why[2];
    int reserveChild[2] = {-1, -1};
};
static std::vector<FamInfo> fams;
static std::map<std::string, int> famIndex;
static int g_maxFam = 300;
static std::deque<std::pair<int,int>> work;   // (family, parity)

static bool g_allowNew = true;
static int g_newBudget = 1 << 30;
static int get_family(const Fam& f, const std::string& name) {
    std::string k = fkey(f);
    auto it = famIndex.find(k);
    if (it != famIndex.end()) return it->second;
    if (!g_allowNew || g_newBudget <= 0) return -2;
    --g_newBudget;
    FamInfo fi; fi.f = f; fi.key = k; fi.name = name;
    fi.beta[0] = bound(member(f, 6));
    fi.beta[1] = bound(member(f, 7));
    fams.push_back(fi);
    int id = int(fams.size()) - 1;
    famIndex[k] = id;
    std::printf("  new family #%d %s beta(even,odd)=(%d,%d)  w7=%s\n", id, name.c_str(), fi.beta[0], fi.beta[1],
                draw(member(f, 7)).c_str());
    std::fflush(stdout);
    return id;
}
static void require(int id, int p) {
    if (fams[id].status[p] == 0) { fams[id].status[p] = 1; work.push_back({id, p}); }
}
// Monotonicity (comparison principle with a single region): if P's Blue
// permissions are a subset of Q's and P's White permissions a superset of Q's,
// on the same geometry, then P <= Q. A piece may therefore reuse the bound of
// any known family that dominates it in this sense.
static bool dominated_by(const Fam& p, const Fam& q) {
    for (int i = 0; i < 3; ++i) {
        if ((p.L[i].a & ~q.L[i].a) || (q.L[i].b & ~p.L[i].b)) return false;
        if ((p.R[i].a & ~q.R[i].a) || (q.R[i].b & ~p.R[i].b)) return false;
    }
    return true;
}
static std::vector<Fam> variants(const Fam& f) {
    auto vf = [](Col c) { return Col{vflip5(c.a), vflip5(c.b)}; };
    Fam v, h, vh;
    for (int i = 0; i < 3; ++i) {
        v.L[i] = vf(f.L[i]); v.R[i] = vf(f.R[i]);
        h.L[i] = f.R[2 - i]; h.R[i] = f.L[2 - i];
        vh.L[i] = vf(f.R[2 - i]); vh.R[i] = vf(f.L[2 - i]);
    }
    return {f, v, h, vh};
}
// piece of length len >= 8 must be a family member: blocks at the ends, neutral middle
static int piece_family(const Strip& piece) {
    int n = int(piece.size());
    for (int c = 3; c < n - 3; ++c) if (piece[c].a != FC || piece[c].b != FC) return -1;
    Fam f;
    for (int i = 0; i < 3; ++i) { f.L[i] = piece[i]; f.R[i] = piece[n - 3 + i]; }
    auto it = famIndex.find(fkey(f));
    if (it != famIndex.end()) return it->second;
    if (g_allowNew && g_newBudget > 0) return get_family(f, "piece");
    int p = n & 1, best = -1;
    auto vs = variants(f);
    for (std::size_t i = 0; i < fams.size(); ++i) {
        if (fams[i].beta[p] == UNKNOWN) continue;
        for (auto& g : vs)
            if (dominated_by(g, fams[i].f)) {
                if (best < 0 || fams[i].beta[p] < fams[best].beta[p]) best = int(i);
                break;
            }
    }
    if (best >= 0) return best;
    return get_family(f, "piece");
}

// ------------------------------------------------------------ rule search
struct Rule { int reply_r = -1, reply_c = -1; std::vector<int> seams; std::vector<int> drops; int sum = 0; std::string desc; };

// Evaluate a cut; returns bound sum or UNKNOWN. Registers requirements only if commit.
static int evaluate(const Strip& s, const std::vector<int>& seams, bool commit, std::string& desc,
                    std::vector<std::pair<int,int>>& needs) {
    int prev = 0, sum = 0;
    std::vector<int> cuts = seams;
    cuts.push_back(int(s.size()) - 1);
    desc.clear();
    for (int j : cuts) {
        Strip piece(s.begin() + prev, s.begin() + j + 1);
        int len = int(piece.size());
        int b;
        if (len <= 7) {
            b = bound(piece);
            if (b == UNKNOWN) return UNKNOWN;
            desc += "[" + std::to_string(len) + ":" + std::to_string(b) + "]";
        } else {
            int id = piece_family(piece);
            if (id < 0) return UNKNOWN;
            b = fams[id].beta[len & 1];
            if (b == UNKNOWN) return UNKNOWN;
            needs.push_back({id, len & 1});
            desc += "[F" + std::to_string(id) + "/" + std::to_string(len & 1) + ":" + std::to_string(b) + "]";
        }
        sum += b;
        prev = j + 1;
    }
    (void)commit;
    return sum;
}

// All ways to satisfy the seam condition at seam j (between j and j+1): for each
// row with White legal on both sides, drop White on one side. Four patterns.
static std::vector<Strip> drop_variants(const Strip& s, const std::vector<int>& seams, int wstart) {
    std::vector<Strip> out{s};
    for (int j : seams) {
        std::vector<Strip> next;
        std::uint8_t both = s[j].b & s[j + 1].b;
        if (!both) { next = out; out = next; continue; }
        std::uint8_t minorityLeft = 0;
        for (int r = 0; r < 5; ++r) if (((r + wstart + j) & 1)) minorityLeft |= 1u << r;
        std::uint8_t choices[4] = {both, 0, std::uint8_t(both & minorityLeft), std::uint8_t(both & ~minorityLeft)};
        std::set<std::uint8_t> seen;
        for (auto dl : choices) {
            if (!seen.insert(dl).second) continue;
            for (auto& t : out) {
                Strip u = t;
                u[j].b &= ~dl;                       // drop on left side for rows in dl
                u[j + 1].b &= ~std::uint8_t(both & ~dl);  // drop on right side for the others
                next.push_back(u);
            }
        }
        out = next;
    }
    return out;
}

static bool find_rule_pass(const Strip& s, int r, int c, int target, Rule& best, std::vector<std::pair<int,int>>& needs);
// Pass 1 uses only known families; pass 2 may create up to 8 new ones.
static bool find_rule(const Strip& s, int r, int c, int target, Rule& best, std::vector<std::pair<int,int>>& needs) {
    g_allowNew = false;
    bool ok = find_rule_pass(s, r, c, target, best, needs);
    g_allowNew = true;
    if (ok) return true;
    g_newBudget = 8;
    ok = find_rule_pass(s, r, c, target, best, needs);
    g_newBudget = 1 << 30;
    return ok;
}
// Rule search on a position s1 in which Blue has just moved (White to move).
// Replies and seams are placed within a window around each centre column.
// Window: 4 columns for a centre within 6 of an end, else 2. With these
// windows every piece bound depends only on the centres' distances to the ends
// (exactly up to 9, by parity beyond), so widths 8..18 contain every class
// for single-centre rules (see check_family).
static bool find_rule_after(const Strip& s1, const std::vector<int>& centers, int target, Rule& best,
                            std::vector<std::pair<int,int>>& needs) {
    int w = int(s1.size());
    std::vector<std::pair<int,int>> replies{{-1, -1}};
    std::set<int> seamSet, replyCols;
    for (int c : centers) {
        const int RW = std::min(c, w - 1 - c) <= 6 ? 4 : 2;
        for (int cc = std::max(0, c - RW); cc <= std::min(w - 1, c + RW); ++cc) replyCols.insert(cc);
        for (int j = c - RW; j <= c + RW - 1; ++j) if (j >= 0 && j <= w - 2) seamSet.insert(j);
    }
    for (int cc : replyCols)
        for (int rr = 0; rr < 5; ++rr) if ((s1[cc].b >> rr) & 1) replies.push_back({rr, cc});
    std::vector<int> sl(seamSet.begin(), seamSet.end());
    std::vector<std::vector<int>> seamSets;
    for (int j : sl) seamSets.push_back({j});
    for (std::size_t i = 0; i < sl.size(); ++i)
        for (std::size_t k = i + 1; k < sl.size(); ++k) seamSets.push_back({sl[i], sl[k]});
    for (std::size_t i = 0; centers.size() > 1 && i < sl.size(); ++i)      // three seams for two-centre rules
        for (std::size_t k = i + 1; k < sl.size(); ++k)
            for (std::size_t m = k + 1; m < sl.size(); ++m) seamSets.push_back({sl[i], sl[k], sl[m]});
    for (int stage = 0; stage < 3; ++stage) {           // stage = number of seams - 1
        for (auto [rr, cc] : replies) {
            Strip s2 = s1;
            if (rr >= 0) wmove(s2, rr, cc);
            int tgt = rr >= 0 ? target : target - 1;
            for (auto& seams : seamSets) {
                if (int(seams.size()) != stage + 1) continue;
                for (auto& s3 : drop_variants(s2, seams, 0)) {
                    std::string desc;
                    std::vector<std::pair<int,int>> nd;
                    int sum = evaluate(s3, seams, false, desc, nd);
                    if (sum == UNKNOWN || sum > tgt) continue;
                    best.reply_r = rr; best.reply_c = cc; best.seams = seams; best.sum = sum; best.desc = desc;
                    needs = nd;
                    return true;
                }
            }
        }
    }
    return false;
}
static bool find_rule_pass(const Strip& s, int r, int c, int target, Rule& best, std::vector<std::pair<int,int>>& needs) {
    Strip s1 = s;
    if (!bmove(s1, r, c)) return true;  // not a legal opening
    return find_rule_after(s1, {c}, target, best, needs);
}

// Two-round rule (Lemma A applied twice): White replies y1; then EVERY Blue
// move x2 must get a one-round rule, with replies and seams placed around the
// opening column and around x2. Returns the reply used, or false.
static bool find_rule_two_round(const Strip& s, int r, int c, int target, std::string& desc,
                                std::vector<std::pair<int,int>>& needs, int& nx2) {
    int w = int(s.size());
    Strip s1 = s;
    if (!bmove(s1, r, c)) return true;
    const int RW = std::min(c, w - 1 - c) <= 6 ? 4 : 2;
    for (int cc = std::max(0, c - RW); cc <= std::min(w - 1, c + RW); ++cc)
        for (int rr = 0; rr < 5; ++rr) {
            if (!((s1[cc].b >> rr) & 1)) continue;
            Strip p1 = s1;
            wmove(p1, rr, cc);
            std::vector<std::pair<int,int>> all;
            bool ok = true;
            int count = 0;
            for (int x = 0; x < w && ok; ++x)
                for (int xr = 0; xr < 5 && ok; ++xr) {
                    Strip p2 = p1;
                    if (!bmove(p2, xr, x)) continue;
                    ++count;
                    Rule rule;
                    std::vector<std::pair<int,int>> nd;
                    g_allowNew = false;
                    bool got = find_rule_after(p2, {c, x}, target, rule, nd);
                    g_allowNew = true;
                    if (!got) { g_newBudget = 4; got = find_rule_after(p2, {c, x}, target, rule, nd); g_newBudget = 1 << 30; }
                    if (!got) ok = false;
                    else for (auto& q : nd) all.push_back(q);
                }
            if (ok) {
                desc = "reply (" + std::to_string(rr) + "," + std::to_string(cc) + ")";
                needs = all;
                nx2 = count;
                return true;
            }
        }
    return false;
}

static void check_family(int id, int p) {
    FamInfo& F = fams[id];
    int beta = F.beta[p];
    if (beta == UNKNOWN) { F.status[p] = -1; F.why[p] = "beta unknown"; return; }
    if (beta < 0) {
        // private White move in an end block: columns 0,1 of L (effects stay in L) or 1,2 of R
        for (int side = 0; side < 2; ++side)
            for (int cc = 0; cc < 2; ++cc)
                for (int rr = 0; rr < 5; ++rr) {
                    Strip s = member(F.f, 8);
                    int col = side ? 7 - cc : cc;
                    bool whiteOnly = ((s[col].b >> rr) & 1) && !((s[col].a >> rr) & 1);
                    if (!whiteOnly) continue;
                    wmove(s, rr, col);
                    Fam g;
                    for (int i = 0; i < 3; ++i) { g.L[i] = s[i]; g.R[i] = s[5 + i]; }
                    int gid = get_family(g, F.name + "+W");
                    FamInfo& G = fams[gid];
                    FamInfo& F2 = fams[id];
                    if (G.beta[p] != UNKNOWN && G.beta[p] <= beta + 1) {
                        F2.status[p] = 3; F2.reserveChild[p] = gid;
                        F2.why[p] = "reserve (" + std::to_string(rr) + "," + std::to_string(col) + ") -> F" + std::to_string(gid);
                        require(gid, p);
                        std::printf("  F%d/%d beta=%d by reserve -> F%d (beta %d)\n", id, p, beta, gid, G.beta[p]);
                        return;
                    }
                }
        fams[id].status[p] = -1; fams[id].why[p] = "negative bound but no usable reserve move";
        return;
    }
    // Every opening at distance c from the left and c' from the right end falls
    // in a class; piece bounds depend only on that class (near-end openings:
    // near distance exact, far distance exact up to 9 then parity; far openings:
    // both distances by parity from 7). Widths 8..18 contain every class.
    std::vector<int> widths;
    for (int w = 8; w <= 18; ++w) if ((w & 1) == p) widths.push_back(w);
    std::vector<std::pair<int,int>> allNeeds;
    int rules = 0;
    for (int w : widths) {
        Strip s = member(fams[id].f, w);
        for (int c = 0; c < w; ++c)
            for (int r = 0; r < 5; ++r) {
                if (!((s[c].a >> r) & 1)) continue;
                Rule rule;
                std::vector<std::pair<int,int>> nd;
                if (!find_rule(s, r, c, beta, rule, nd)) {
                    fams[id].status[p] = -1;
                    fams[id].why[p] = "no rule at w=" + std::to_string(w) + " opening (" + std::to_string(r) + "," +
                                      std::to_string(c) + ")";
                    std::printf("  F%d/%d FAILED: %s\n", id, p, fams[id].why[p].c_str());
                    std::fflush(stdout);
                    return;
                }
                ++rules;
                for (auto& x : nd) allNeeds.push_back(x);
            }
    }
    fams[id].status[p] = 2;
    fams[id].why[p] = std::to_string(rules) + " openings handled";
    for (auto [nid, q] : allNeeds) require(nid, q);
    std::printf("  F%d/%d beta=%d CLOSED at this level (%d openings)\n", id, p, beta, rules);
    std::fflush(stdout);
}

static int g_tr = -1, g_tc = -1;
static std::vector<int> g_test2;
int main(int argc, char** argv) {
    std::string root = "KD";
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-j") g_threads = std::atoi(argv[++i]);
        else if (a == "-L") g_limit = std::atof(argv[++i]);
        else if (a == "-C") g_cachePath = argv[++i];
        else if (a == "-M") g_maxFam = std::atoi(argv[++i]);
        else if (a == "-T2") {
            g_tr = std::atoi(argv[++i]); g_tc = std::atoi(argv[++i]);
            std::stringstream ws(argv[++i]); std::string t;
            while (std::getline(ws, t, ',')) g_test2.push_back(std::atoi(t.c_str()));
        }
        else root = a;
    }
    g_start = std::chrono::steady_clock::now();
    Cache vc(24); TT tt(24);
    g_vc = &vc; g_tt = &tt;
    if (!g_cachePath.empty()) load_cache();
    auto letter = [](const char* p) { Col c{0, 0}; for (int r = 0; r < 5; ++r) { if (p[r] == 'o' || p[r] == 'b') c.a |= 1u << r; if (p[r] == 'o' || p[r] == 'w') c.b |= 1u << r; } return c; };
    Fam f;
    Col N{FC, FC};
    f.L[0] = letter("obwbo"); f.L[1] = N; f.L[2] = N;
    f.R[0] = N; f.R[1] = N; f.R[2] = letter("obwbo");
    if (root == "KD") { Strip s = member(f, 8); wmove(s, 2, 0); for (int i = 0; i < 3; ++i) f.L[i] = s[i]; }
    int rid = get_family(f, root);
    if (!g_test2.empty()) {
        // test mode: two-round rule for opening (g_tr, g_tc) of the root at the listed widths
        for (int w : g_test2) {
            Strip s = member(fams[rid].f, w);
            int beta = fams[rid].beta[w & 1];
            std::string desc;
            std::vector<std::pair<int,int>> nd;
            int nx2 = 0;
            Rule one;
            std::vector<std::pair<int,int>> nd1;
            bool oneRound = find_rule(s, g_tr, g_tc, beta, one, nd1);
            bool two = find_rule_two_round(s, g_tr, g_tc, beta, desc, nd, nx2);
            std::printf("w=%d opening (%d,%d) beta %d: one-round %s; two-round %s %s (%d second Blue moves), families %zu, searches %" PRIu64 ", %.0fs\n",
                        w, g_tr, g_tc, beta, oneRound ? ("OK " + one.desc).c_str() : "none", two ? "OK" : "FAILED",
                        desc.c_str(), nx2, fams.size(), g_queries, since_start());
            std::fflush(stdout);
            save_cache();
        }
        return 0;
    }
    for (int p = 0; p < 2; ++p) require(rid, p);
    while (!work.empty() && int(fams.size()) <= g_maxFam) {
        auto [id, p] = work.front(); work.pop_front();
        std::printf("check F%d parity %d (beta %d)  [families %zu, queue %zu, searches %" PRIu64 ", %.0fs]\n", id, p,
                    fams[id].beta[p], fams.size(), work.size(), g_queries, since_start());
        std::fflush(stdout);
        check_family(id, p);
        save_cache();
    }
    int proved = 0, failed = 0, pending = 0;
    for (std::size_t i = 0; i < fams.size(); ++i)
        for (int p = 0; p < 2; ++p) {
            if (fams[i].status[p] == 2 || fams[i].status[p] == 3) ++proved;
            else if (fams[i].status[p] == -1) ++failed;
            else if (fams[i].status[p] == 1) ++pending;
        }
    std::printf("\nSUMMARY families %zu; required (family,parity) closed %d, failed %d, pending %d; searches %" PRIu64 "\n",
                fams.size(), proved, failed, pending, g_queries);
    for (std::size_t i = 0; i < fams.size(); ++i)
        for (int p = 0; p < 2; ++p)
            if (fams[i].status[p] != 0)
                std::printf("  F%zu/%d beta %d status %d  %s   %s\n", i, p, fams[i].beta[p], fams[i].status[p],
                            fams[i].why[p].c_str(), draw(member(fams[i].f, 7)).c_str());
    save_cache();
    return failed ? 1 : 0;
}
