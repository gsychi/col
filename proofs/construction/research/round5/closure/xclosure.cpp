// xclosure: exact-bound (dyadic plus star) closure search for 5-row strip
// families. EVIDENCE tool: every rule it finds is written to a JSON-lines file
// for later independent replay. The obligations, the width-coverage argument
// and the soundness argument are in NOTES.md.
//
// A family F is a 5 x w strip with fixed 3-column end blocks and a neutral
// middle. Its bound q_F[p] (a dyadic x or x+*) is measured exactly at w = 6
// (p = 0) or w = 7 (p = 1), possibly weakened, and claimed for every w >= 6 of
// parity p. For w >= 8 the claim is proved by strong induction from one of:
//   table   (B) every Blue opening G^L: a White reply and a cut with sum <= q,
//               or no reply and a cut with sum <| q (White wins moving first);
//           (W) if q has a Right option q^R: a White move and a cut, sum <= q^R;
//   reserve F <= F' - 1 for a White-only end-block move giving family F',
//           with q_F' <= q + 1 (COL_VALUES Lemma 4(4));
//   rcut    a White move v and a cut with sum <= q + 1 (v White-only) or
//           sum <= q + * (v shared) (Lemma 4(3),(4)), at every width.
// Pieces of length <= 7 use their exact value; longer pieces must be family
// members (or be dominated by one) and use the family bound.
//
// Usage: xclosure [-j threads] [-L sec] [-o tag] [-M maxfam] [-S maxseams]
//                 [-test r c w1,w2,..] [-fam w7draw] ROOT
#define main colout5_main
#include "xcolout5.cpp"
#undef main

#include <array>
#include <deque>
#include <fstream>
#include <functional>
#include <map>
#include <set>
#include <shared_mutex>
#include <unordered_map>
#include <sys/stat.h>

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
static Strip vflip(const Strip& s) {
    Strip v = s;
    for (auto& c : v) { c.a = vflip5(c.a); c.b = vflip5(c.b); }
    return v;
}
static Strip hflip(const Strip& s) { return Strip(s.rbegin(), s.rend()); }
static std::string canon(const Strip& s) {
    Strip v = vflip(s), h = hflip(s), vh = hflip(v);
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
static Strip undraw(const std::string& d) {
    std::vector<std::string> rows;
    std::stringstream ss(d);
    std::string t;
    while (std::getline(ss, t, '/')) rows.push_back(t);
    if (rows.size() != 5) die("bad strip drawing " + d);
    Strip s(rows[0].size(), Col{0, 0});
    for (int r = 0; r < 5; ++r)
        for (std::size_t c = 0; c < s.size(); ++c) {
            char ch = rows[r][c];
            if (ch == 'o' || ch == 'b') s[c].a |= 1u << r;
            if (ch == 'o' || ch == 'w') s[c].b |= 1u << r;
        }
    return s;
}
static std::string hexs(const std::string& s) {
    static const char* H = "0123456789abcdef";
    std::string o;
    for (unsigned char ch : s) { o += H[ch >> 4]; o += H[ch & 15]; }
    return o;
}
static std::string unhex(const std::string& s) {
    std::string o;
    for (std::size_t i = 0; i + 1 < s.size(); i += 2) o += char(std::stoi(s.substr(i, 2), nullptr, 16));
    return o;
}

// ------------------------------------------------------------ values x or x+*
struct XV { i64 num = 0; bool star = false; bool ok = true; };
static const XV XBAD{0, false, false};
static XV xadd(XV a, XV b) { return XV{a.num + b.num, a.star != b.star, a.ok && b.ok}; }
// Order between values of Col type (COL_VALUES Table 1 / F4).
static bool xle(XV a, XV b) { return a.star == b.star ? a.num <= b.num : a.num < b.num; }
static bool xlf(XV a, XV b) { return !xle(b, a); }   // a <| b
static std::string xs(XV v) { return v.ok ? valstr(Val{v.num, v.star}) : "?"; }
static bool xparse(const std::string& s0, XV& v) {
    if (s0 == "?") return false;
    std::string s = s0;
    v = XV{};
    if (s == "*") { v.star = true; return true; }
    if (s.size() > 2 && s.substr(s.size() - 2) == "+*") { v.star = true; s = s.substr(0, s.size() - 2); }
    v.num = parse_dyadic(s);
    return true;
}
// Right option of the canonical form of q (none for integers >= 0).
static bool right_option(XV q, XV& r) {
    if (q.star) { r = XV{q.num, false}; return true; }
    if ((q.num & (ONE - 1)) == 0) {
        if (q.num >= 0) return false;
        r = XV{q.num + ONE, false};
        return true;
    }
    r = XV{q.num + (q.num & -q.num), false};
    return true;
}
// Smallest multiple m*unit (a number) with v <= m*unit.
static XV round_up(XV v, i64 unit) {
    i64 c = v.num >= 0 ? ((v.num + unit - 1) / unit) * unit : -((-v.num) / unit) * unit;
    if (v.star && c == v.num) c += unit;
    return XV{c, false};
}
static XV bound_at(XV v, int level) {
    if (!v.ok) return v;
    switch (level) {
        case 0: return v;
        case 1: return round_up(v, ONE / 4);
        case 2: return round_up(v, ONE / 2);
        default: return round_up(v, ONE);
    }
}
static const char* LEVEL_NAME[4] = {"exact", "quarter", "half", "integer"};

// ------------------------------------------------------------ contexts
static int g_threads = 3, g_smax = 14, g_maxSeams = 2, g_maxFam = 400, g_newBudget = 8, g_tlog = 24;
static bool g_diag = false, g_allDrops = false;
static int g_rwFar = 2;
static int g_T = 6;             // gap-representative rules: gaps >= g_T stand for all longer ones
static bool g_gapRule = true;
static double g_limit = 900;
static Cache* g_vc;
static TT* g_tt;
static std::atomic<bool> g_stop{false}, g_quit{false};
static std::string g_stopPath = "/workspace/proofs/construction/research/round5/STOP";
struct Ctx {
    std::map<int, std::unique_ptr<Board>> boards;
    std::map<int, std::unique_ptr<Search>> searches;
    std::atomic<bool> abort{false};
    std::atomic<double> deadline{1e18};
};
static std::unique_ptr<Ctx[]> g_ctx;
static std::mutex g_logMu;
#define LOG(...) do { std::lock_guard<std::mutex> _lk(g_logMu); std::printf(__VA_ARGS__); std::fflush(stdout); } while (0)

static Search& ctx_search(int cid, int w) {
    Ctx& c = g_ctx[cid];
    auto& bp = c.boards[w];
    if (!bp) bp.reset(new Board(5, w));
    auto& sp = c.searches[w];
    if (!sp) { sp.reset(new Search(*bp, *g_vc, *g_tt, g_smax)); sp->abortL = &c.abort; }
    return *sp;
}

// ------------------------------------------------------------ exact piece values
static std::unordered_map<std::string, XV> g_val;
static std::shared_mutex g_valMu;
static std::unordered_map<std::string, int> g_hint;
static std::string g_valPath;
static std::mutex g_valFileMu;
static std::atomic<std::uint64_t> g_nExact{0}, g_nTimeout{0}, g_nSearch{0};

static bool val_lookup(const std::string& k, XV& v) {
    std::shared_lock<std::shared_mutex> lk(g_valMu);
    auto it = g_val.find(k);
    if (it == g_val.end()) return false;
    v = it->second;
    return true;
}
static void val_store(const std::string& k, XV v) {
    {
        std::unique_lock<std::shared_mutex> lk(g_valMu);
        g_val[k] = v;
    }
    if (v.ok && !g_valPath.empty()) {
        std::lock_guard<std::mutex> lk(g_valFileMu);
        FILE* f = std::fopen(g_valPath.c_str(), "a");
        if (f) { std::fprintf(f, "%s %s\n", hexs(k).c_str(), xs(v).c_str()); std::fclose(f); }
    }
}
static double now_s() { return since_start(); }

// Exact value by bisection on outcomes of G - t (Cor 4.3: P means G = t,
// N means G = t + *, L means x > t, R means x < t).
static XV compute_exact(const Strip& s, int cid, const std::string& key) {
    int w = int(s.size());
    Search& S = ctx_search(cid, w);
    Mask A = 0, B = 0;
    for (int c = 0; c < w; ++c)
        for (int r = 0; r < 5; ++r) {
            if ((s[c].a >> r) & 1) A |= Mask(1) << (r * w + c);
            if ((s[c].b >> r) & 1) B |= Mask(1) << (r * w + c);
        }
    Ctx& C = g_ctx[cid];
    C.abort = false;
    C.deadline = now_s() + g_limit;
    const i64 flo = -i64(S.alpha_upper(B) + 1) * ONE, fhi = i64(S.alpha_upper(A) + 1) * ONE;
    i64 lo = flo, hi = fhi;
    bool loOpen = false, hiOpen = false, hinted = false;
    auto hit = g_hint.find(key);
    if (hit != g_hint.end() && hit->second > -8 && hit->second <= 10) {
        lo = i64(hit->second - 1) * ONE; hi = i64(hit->second) * ONE; hinted = true;
    }
    XV res = XBAD;
    for (int step = 0; step < 100; ++step) {
        bool empty = lo > hi || (lo == hi && (loOpen || hiOpen));
        if (empty) {
            if (!hinted) die("exact value: empty interval for " + draw(s));
            lo = flo; hi = fhi; loOpen = hiOpen = false; hinted = false;
            continue;
        }
        i64 t = simplest(true, lo, loOpen, true, hi, hiOpen);
        g_nSearch += 2;
        int b = S.win(A, B, -t, false, 0);
        if (b < 0) break;
        int wr = S.win(B, A, t, false, 0);
        if (wr < 0) break;
        if (!b && !wr) { res = XV{t, false}; break; }
        if (b && wr) { res = XV{t, true}; break; }
        if (b) { lo = t; loOpen = true; } else { hi = t; hiOpen = true; }
    }
    C.deadline = 1e18;
    if (!res.ok) ++g_nTimeout; else ++g_nExact;
    return res;
}
static XV xvalue(const Strip& s, int cid, bool cachedOnly) {
    bool live = false;
    for (auto& c : s) if (c.a | c.b) { live = true; break; }
    if (!live) return XV{0, false};
    std::string k = canon(s);
    XV v;
    if (val_lookup(k, v)) return v;
    if (cachedOnly || g_stop) return XBAD;
    v = compute_exact(s, cid, k);
    if (!v.ok && g_stop) return v;   // interrupted, do not remember
    val_store(k, v);
    return v;
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
    int parent = -1;
    XV v[2], q[2];
    int level[2] = {0, 0};
    int status[2] = {0, 0};   // 0 untouched, 1 queued, 2 table, 3 reserve, 4 rcut, -1 failed
    std::string why[2], method[2];
    int att[2] = {-1, -1};
    std::set<std::pair<int, int>> users[2];
    std::vector<std::pair<int, int>> needs[2];
    std::vector<std::string> history[2];
};
static std::deque<FamInfo> fams;
static std::map<std::string, int> famIndex;
static std::mutex g_famMu;

static int find_family(const Fam& f) {
    std::string k = fkey(f);
    std::lock_guard<std::mutex> lk(g_famMu);
    auto it = famIndex.find(k);
    return it == famIndex.end() ? -1 : it->second;
}
static XV fam_q(int id, int p) {
    std::lock_guard<std::mutex> lk(g_famMu);
    return fams[id].q[p];
}
static int get_family(const Fam& f, const std::string& name, int cid, int parent) {
    std::string k = fkey(f);
    {
        std::lock_guard<std::mutex> lk(g_famMu);
        auto it = famIndex.find(k);
        if (it != famIndex.end()) return it->second;
        if (int(fams.size()) >= g_maxFam) return -2;
    }
    XV v6 = xvalue(member(f, 6), cid, false);
    XV v7 = xvalue(member(f, 7), cid, false);
    if (g_stop) return -2;
    std::lock_guard<std::mutex> lk(g_famMu);
    auto it = famIndex.find(k);
    if (it != famIndex.end()) return it->second;
    FamInfo fi;
    fi.f = f; fi.key = k; fi.name = name; fi.parent = parent;
    fi.v[0] = v6; fi.v[1] = v7; fi.q[0] = v6; fi.q[1] = v7;
    fams.push_back(fi);
    int id = int(fams.size()) - 1;
    famIndex[k] = id;
    std::lock_guard<std::mutex> lk2(g_logMu);
    std::printf("  new family #%d %s values(w6,w7)=(%s,%s)  w7=%s\n", id, name.c_str(), xs(v6).c_str(), xs(v7).c_str(),
                draw(member(f, 7)).c_str());
    std::fflush(stdout);
    return id;
}
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

// ------------------------------------------------------------ rules
struct PieceRec { int a = 0, b = 0; char src = 'x'; int fam = -1, par = -1; XV val; std::string dr; };
struct Rule {
    char type = 'B';          // B blue opening, b two-round, W white-first, R reserve-cut, E end-block reserve
    int w = 0, orow = -1, ocol = -1, rrow = -1, rcol = -1;
    std::vector<int> seams;
    std::vector<std::array<int, 3>> drops;   // seam, rows dropped on left column, rows dropped on right column
    std::vector<PieceRec> pieces;
    XV sum, target;
    char cmp = 'L';           // L: sum <= target, F: sum <| target
    std::string stretch, sym;
    std::vector<Rule> subs;   // two-round rule ('b'): one rule per second Blue move, plus a 'W' rule if needed
    // Gap-representative rule ('G') and its sub-rules: gap lengths of the configuration
    // the rule was checked on, and column ranges that must stay stretchable.
    std::vector<int> gaps;
    std::vector<std::pair<int, int>> sranges;
    std::string board;
};
struct SC { int cid; bool cachedOnly, allowNew, allowDom; int newBudget; };

static bool piece_bound(const Strip& piece, SC& sc, PieceRec& rec) {
    int n = int(piece.size());
    for (int c = 3; c < n - 3; ++c) if (piece[c].a != FC || piece[c].b != FC) return false;
    Fam f;
    for (int i = 0; i < 3; ++i) { f.L[i] = piece[i]; f.R[i] = piece[n - 3 + i]; }
    int p = n & 1;
    int id = find_family(f);
    if (id < 0 && sc.allowNew && sc.newBudget > 0) {
        --sc.newBudget;
        id = get_family(f, "piece", sc.cid, -1);
        if (id < 0) return false;
    }
    if (id >= 0) {
        XV q = fam_q(id, p);
        if (!q.ok) return false;
        rec.src = 'f'; rec.fam = id; rec.par = p; rec.val = q;
        return true;
    }
    if (!sc.allowDom) return false;
    auto vs = variants(f);
    int best = -1;
    XV bq;
    std::lock_guard<std::mutex> lk(g_famMu);
    for (std::size_t i = 0; i < fams.size(); ++i) {
        XV q = fams[i].q[p];
        if (!q.ok) continue;
        for (auto& g : vs)
            if (dominated_by(g, fams[i].f)) {
                if (best < 0 || q.num < bq.num || (q.num == bq.num && !q.star && bq.star)) { best = int(i); bq = q; }
                break;
            }
    }
    if (best < 0) return false;
    rec.src = 'd'; rec.fam = best; rec.par = p; rec.val = bq;
    return true;
}

static bool evaluate(const Strip& s3, const std::vector<int>& seams, SC& sc, std::vector<PieceRec>& pcs, XV& sum) {
    int prev = 0;
    std::vector<int> cuts = seams;
    cuts.push_back(int(s3.size()) - 1);
    pcs.clear();
    sum = XV{0, false};
    for (int j : cuts) {
        Strip piece(s3.begin() + prev, s3.begin() + j + 1);
        PieceRec rec;
        rec.a = prev; rec.b = j;
        if (int(piece.size()) <= 7) {
            XV v = xvalue(piece, sc.cid, sc.cachedOnly);
            if (!v.ok) return false;
            rec.src = 'x'; rec.val = v;
        } else if (!piece_bound(piece, sc, rec)) return false;
        rec.dr = draw(piece);
        sum = xadd(sum, rec.val);
        pcs.push_back(rec);
        prev = j + 1;
    }
    return true;
}

// Seam condition: for every row whose two cells at a seam are both White-legal,
// White is dropped on one side. Four drop patterns per seam.
struct DropV { Strip s; std::vector<std::array<int, 3>> d; };
static std::vector<DropV> drop_variants(const Strip& s, const std::vector<int>& seams) {
    std::vector<DropV> out{{s, {}}};
    for (int j : seams) {
        std::vector<DropV> next;
        std::uint8_t both = s[j].b & s[j + 1].b;
        if (!both) { for (auto& o : out) o.d.push_back({j, 0, 0}); continue; }
        std::uint8_t minorityLeft = 0;
        for (int r = 0; r < 5; ++r) if ((r + j) & 1) minorityLeft |= 1u << r;
        std::vector<std::uint8_t> choices{both, 0, std::uint8_t(both & minorityLeft), std::uint8_t(both & ~minorityLeft)};
        if (g_allDrops)
            for (unsigned sub = both;; sub = (sub - 1) & both) {
                choices.push_back(std::uint8_t(sub));
                if (!sub) break;
            }
        std::set<std::uint8_t> seen;
        for (auto dl : choices) {
            if (!seen.insert(dl).second) continue;
            std::uint8_t dr = both & ~dl;
            for (auto& t : out) {
                DropV u = t;
                u.s[j].b &= ~dl;
                u.s[j + 1].b &= ~dr;
                u.d.push_back({j, dl, dr});
                next.push_back(u);
            }
        }
        out = next;
    }
    return out;
}
static int window_rw(int w, int c) { return std::min(c, w - 1 - c) <= 6 ? 4 : g_rwFar; }
static std::vector<std::vector<int>> seam_sets(int w, int c, int stage) {
    int RW = window_rw(w, c);
    std::vector<int> sl;
    for (int j = c - RW; j <= c + RW - 1; ++j) if (j >= 0 && j <= w - 2) sl.push_back(j);
    std::vector<std::vector<int>> out;
    int n = int(sl.size());
    if (stage == 1) for (int i = 0; i < n; ++i) out.push_back({sl[i]});
    if (stage == 2) for (int i = 0; i < n; ++i) for (int k = i + 1; k < n; ++k) out.push_back({sl[i], sl[k]});
    if (stage == 3)
        for (int i = 0; i < n; ++i) for (int k = i + 1; k < n; ++k) for (int m = k + 1; m < n; ++m) out.push_back({sl[i], sl[k], sl[m]});
    return out;
}

// A candidate White move (r < 0: none) with the comparison it must satisfy.
struct Cand { int r, c; XV target; char cmp; };
// Stretch requirement at the largest checked width: 0 none, 1 both flagged
// sides, 2 at least one side.
struct Stretch {
    int mode = 0;
    bool L = false, R = false;
    // Each range [lo, hi] (a run of neutral columns) needs an insertion point between
    // columns j and j+1, j in [lo - 1, hi], inside the neutral middle of a family piece.
    std::vector<std::pair<int, int>> ranges;
};
static bool ranges_ok(const Stretch& st, const std::vector<PieceRec>& pcs) {
    for (auto [lo, hi] : st.ranges) {
        bool ok = false;
        for (auto& p : pcs) {
            if (p.src == 'x') continue;
            if (std::max(p.a + 2, lo - 1) <= std::min(p.b - 3, hi)) { ok = true; break; }
        }
        if (!ok) return false;
    }
    return true;
}

static std::vector<std::vector<int>> combos(const std::vector<int>& sl, int k) {
    std::vector<std::vector<int>> out;
    int n = int(sl.size());
    if (k == 1) for (int i = 0; i < n; ++i) out.push_back({sl[i]});
    if (k == 2) for (int i = 0; i < n; ++i) for (int j = i + 1; j < n; ++j) out.push_back({sl[i], sl[j]});
    if (k == 3)
        for (int i = 0; i < n; ++i) for (int j = i + 1; j < n; ++j) for (int m = j + 1; m < n; ++m) out.push_back({sl[i], sl[j], sl[m]});
    return out;
}
static std::vector<int> seam_list(int w, const std::vector<int>& centres) {
    std::set<int> ss;
    for (int c : centres) {
        int RW = window_rw(w, c);
        for (int j = c - RW; j <= c + RW - 1; ++j) if (j >= 0 && j <= w - 2) ss.insert(j);
    }
    return std::vector<int>(ss.begin(), ss.end());
}
// Seams lie in the windows around the fixed centres and, if moveIsCentre, around
// the White move's column. budget (if given) caps the number of cuts evaluated.
static bool search_cands(const Strip& s1, const std::vector<Cand>& moves, const std::vector<int>& fixedCentres,
                         bool moveIsCentre, int maxStage, const Stretch& st, SC& sc, Rule& out, long* budget = nullptr) {
    int w = int(s1.size());
    std::vector<int> fixedList = seam_list(w, fixedCentres);
    for (int stage = 1; stage <= maxStage; ++stage)
        for (auto& mv : moves) {
            Strip s2 = s1;
            if (mv.r >= 0 && !wmove(s2, mv.r, mv.c)) continue;
            std::vector<int> sl = fixedList;
            if (moveIsCentre) {
                std::vector<int> cs = fixedCentres;
                if (mv.r >= 0) cs.push_back(mv.c);
                else { cs.push_back(3); cs.push_back(w - 4); }
                sl = seam_list(w, cs);
            }
            for (auto& seams : combos(sl, stage))
                for (auto& dv : drop_variants(s2, seams)) {
                    if (g_stop) return false;
                    if (budget && --*budget < 0) return false;
                    std::vector<PieceRec> pcs;
                    XV sum;
                    if (!evaluate(dv.s, seams, sc, pcs, sum)) continue;
                    bool ok = mv.cmp == 'L' ? xle(sum, mv.target) : xlf(sum, mv.target);
                    if (!ok) continue;
                    bool fl = pcs.front().b - pcs.front().a + 1 >= 8, fr = pcs.back().b - pcs.back().a + 1 >= 8;
                    if (st.mode == 1 && ((st.L && !fl) || (st.R && !fr))) continue;
                    if (st.mode == 2 && !fl && !fr) continue;
                    if (!ranges_ok(st, pcs)) continue;
                    out.w = w; out.rrow = mv.r; out.rcol = mv.r >= 0 ? mv.c : -1;
                    out.seams = seams; out.drops = dv.d; out.pieces = pcs; out.sum = sum;
                    out.target = mv.target; out.cmp = mv.cmp;
                    out.sranges = st.ranges;
                    out.stretch = st.mode == 0 ? "" : std::string(fl ? "L" : "") + (fr ? "R" : "");
                    return true;
                }
        }
    return false;
}
template <class Fn> static bool three_pass(int cid, Fn fn) {
    SC a{cid, true, false, true, 0};
    if (fn(a)) return true;
    SC b{cid, false, false, true, 0};
    if (fn(b)) return true;
    SC c{cid, false, true, true, g_newBudget};
    return fn(c);
}
static bool is_vsym(const Strip& s) { return skey(vflip(s)) == skey(s); }
static bool is_hsym(const Strip& s) { return skey(hflip(s)) == skey(s); }

static int wmax_of(int p) { return p ? 21 : 20; }
static int g_wmaxOverride = 0;
static std::vector<int> widths_of(int p) {
    std::vector<int> ws;
    int top = g_wmaxOverride ? g_wmaxOverride - ((g_wmaxOverride - p) & 1) : wmax_of(p);
    for (int w = 8; w <= top; ++w) if ((w & 1) == p) ws.push_back(w);
    return ws;
}

static bool find_B(const Strip& s, int r, int c, XV q, int cid, Rule& out) {
    Strip s1 = s;
    if (!bmove(s1, r, c)) return false;
    int w = int(s.size()), RW = window_rw(w, c);
    std::vector<Cand> moves{{-1, -1, q, 'F'}};
    for (int cc = std::max(0, c - RW); cc <= std::min(w - 1, c + RW); ++cc)
        for (int rr = 0; rr < 5; ++rr) if ((s1[cc].b >> rr) & 1) moves.push_back({rr, cc, q, 'L'});
    Stretch st;
    if (w == wmax_of(w & 1) && !g_wmaxOverride) { st.mode = 1; st.L = c >= 9; st.R = w - 1 - c >= 9; }
    out.type = 'B'; out.orow = r; out.ocol = c;
    return three_pass(cid, [&](SC& sc) { return search_cands(s1, moves, {c}, false, g_maxSeams, st, sc, out); });
}
static std::vector<Cand> white_moves(const Strip& s, bool rcut, XV q) {
    int w = int(s.size());
    bool vs = is_vsym(s), hs = is_hsym(s);
    std::vector<std::pair<int, std::pair<int, int>>> order;
    for (int c = 0; c < w; ++c)
        for (int r = 0; r < 5; ++r) {
            if (!((s[c].b >> r) & 1)) continue;
            if (vs && r > 2) continue;
            if (hs && c > (w - 1) / 2) continue;
            order.push_back({std::min(c, w - 1 - c), {r, c}});
        }
    std::stable_sort(order.begin(), order.end(), [](auto& x, auto& y) { return x.first < y.first; });
    std::vector<Cand> out;
    // No White move: G <= sum and sum <| q^R give G <| q^R.
    if (!rcut) out.push_back({-1, -1, q, 'F'});
    for (auto& o : order) {
        int r = o.second.first, c = o.second.second;
        XV t = q;
        if (rcut) {
            bool priv = !((s[c].a >> r) & 1);
            t = priv ? XV{q.num + ONE, q.star} : XV{q.num, !q.star};
        }
        out.push_back({r, c, t, 'L'});
    }
    return out;
}
static bool find_W(const Strip& s, XV target, bool rcut, int cid, Rule& out) {
    auto moves = white_moves(s, rcut, target);
    Stretch st;
    if (int(s.size()) == wmax_of(int(s.size()) & 1) && !g_wmaxOverride) st.mode = 2;
    out.type = rcut ? 'R' : 'W';
    return three_pass(cid, [&](SC& sc) { return search_cands(s, moves, {}, true, g_maxSeams, st, sc, out); });
}

// Two-round rule for a Blue opening (used only below the largest checked
// width, where it is a finite fact about that one width): a White reply y1
// such that P = G^{L,y1} <= q, proved by (B) for every Blue move x2 in P with
// windows around the opening and x2, and (W) for q's Right option.
static bool g_twoRound = true, g_verbose = false;
static long g_b2Budget = 400000;
static bool find_B2(const Strip& s, int r, int c, XV q, int cid, Rule& out) {
    Strip s1 = s;
    if (!bmove(s1, r, c)) return false;
    int w = int(s.size()), RW = window_rw(w, c);
    XV qR;
    bool hasR = right_option(q, qR);
    Stretch none;
    // One obligation of P: a second Blue move (xr, x), or xr < 0 for the (W) part.
    auto sub_search = [&](const Strip& P, int xr, int x, bool cheap, Rule& sub) -> bool {
        long budget = cheap ? 20000 : g_b2Budget;
        int stages = cheap ? 2 : 3;
        std::vector<Cand> moves;
        std::vector<int> centres{c};
        bool moveCentre = false;
        Strip base = P;
        if (xr >= 0) {
            bmove(base, xr, x);
            int RW2 = window_rw(w, x);
            moves.push_back({-1, -1, q, 'F'});
            std::set<std::pair<int, int>> seen;
            for (int ctr : {c, x}) {
                int rw = ctr == c ? RW : RW2;
                for (int c2 = std::max(0, ctr - rw); c2 <= std::min(w - 1, ctr + rw); ++c2)
                    for (int r2 = 0; r2 < 5; ++r2)
                        if (((base[c2].b >> r2) & 1) && seen.insert({r2, c2}).second) moves.push_back({r2, c2, q, 'L'});
            }
            centres.push_back(x);
            sub.type = 'B'; sub.orow = xr; sub.ocol = x;
        } else {
            moves = white_moves(P, false, qR);
            moveCentre = true;
            sub.type = 'W';
        }
        if (cheap) {
            SC sc{cid, true, false, true, 0};
            return search_cands(base, moves, centres, moveCentre, stages, none, sc, sub, &budget);
        }
        for (int cap : {2, 3}) {
            bool got = three_pass(cid, [&](SC& sc) {
                long b = budget;
                return search_cands(base, moves, centres, moveCentre, cap, none, sc, sub, &b);
            });
            if (got) return true;
        }
        return false;
    };
    struct Rep { int rr, cc, fails; std::vector<Rule> subs; std::vector<std::pair<int, int>> todo; };
    std::vector<Rep> reps;
    for (int cc = std::max(0, c - RW); cc <= std::min(w - 1, c + RW); ++cc)
        for (int rr = 0; rr < 5; ++rr) {
            if (!((s1[cc].b >> rr) & 1)) continue;
            Strip P = s1;
            wmove(P, rr, cc);
            Rep R{rr, cc, 0, {}, {}};
            std::vector<std::pair<int, int>> items;
            for (int x = 0; x < w; ++x)
                for (int xr = 0; xr < 5; ++xr) if ((P[x].a >> xr) & 1) items.push_back({xr, x});
            if (hasR) items.push_back({-1, -1});
            for (auto [xr, x] : items) {
                if (g_stop) return false;
                Rule sub;
                if (sub_search(P, xr, x, true, sub)) R.subs.push_back(sub);
                else { ++R.fails; R.todo.push_back({xr, x}); }
            }
            reps.push_back(R);
        }
    std::stable_sort(reps.begin(), reps.end(), [](const Rep& a, const Rep& b) { return a.fails < b.fails; });
    int tried = 0;
    for (auto& R : reps) {
        if (++tried > 8 || g_stop) break;
        Strip P = s1;
        wmove(P, R.rr, R.cc);
        bool ok = true;
        int done = 0;
        if (g_verbose)
            LOG("      two-round w=%d (%d,%d) reply (%d,%d): %d cheap failures, deep pass [%.0fs]\n", w, r, c, R.rr,
                R.cc, R.fails, now_s());
        for (auto [xr, x] : R.todo) {
            Rule sub;
            bool got = sub_search(P, xr, x, false, sub);
            if (g_verbose)
                LOG("        second move (%d,%d): %s sum %s [%.0fs]\n", xr, x, got ? "closed" : "STUCK",
                    got ? xs(sub.sum).c_str() : "-", now_s());
            if (!got) { ok = false; break; }
            R.subs.push_back(sub);
            ++done;
        }
        LOG("      two-round %s reply (%d,%d): %d cheap failures, %s\n", ("w=" + std::to_string(w) + " (" +
            std::to_string(r) + "," + std::to_string(c) + ")").c_str(), R.rr, R.cc, R.fails,
            ok ? "all closed" : ("stuck after " + std::to_string(done)).c_str());
        if (g_stop) return false;
        if (ok) {
            out = Rule();
            out.type = 'b'; out.w = w; out.orow = r; out.ocol = c; out.rrow = R.rr; out.rcol = R.cc;
            out.target = q; out.cmp = 'L'; out.subs = R.subs;
            return true;
        }
    }
    return false;
}

// Diagnostic: for every White reply (or none) to an opening, the smallest cut
// sum over the window with up to g_maxSeams seams.
static void diagnose(const Strip& s, int r, int c, XV q, int cid) {
    Strip s1 = s;
    if (!bmove(s1, r, c)) { LOG("illegal opening\n"); return; }
    int w = int(s.size()), RW = window_rw(w, c);
    std::vector<std::pair<int, int>> replies{{-1, -1}};
    for (int cc = std::max(0, c - RW); cc <= std::min(w - 1, c + RW); ++cc)
        for (int rr = 0; rr < 5; ++rr) if ((s1[cc].b >> rr) & 1) replies.push_back({rr, cc});
    SC sc{cid, false, true, true, 1 << 30};
    for (auto [rr, cc] : replies) {
        Strip s2 = s1;
        if (rr >= 0) wmove(s2, rr, cc);
        XV best = XBAD;
        std::string bd;
        for (int stage = 1; stage <= g_maxSeams; ++stage)
            for (auto& seams : seam_sets(w, c, stage))
                for (auto& dv : drop_variants(s2, seams)) {
                    std::vector<PieceRec> pcs;
                    XV sum;
                    if (!evaluate(dv.s, seams, sc, pcs, sum)) continue;
                    if (!best.ok || sum.num < best.num || (sum.num == best.num && !sum.star && best.star)) {
                        best = sum;
                        bd.clear();
                        for (auto& p : pcs)
                            bd += "[" + std::to_string(p.b - p.a + 1) + (p.src == 'x' ? "" : p.src == 'f' ? "F" : "D") +
                                  (p.fam >= 0 ? std::to_string(p.fam) : "") + ":" + xs(p.val) + "]";
                    }
                }
        bool ok = best.ok && (rr < 0 ? xlf(best, q) : xle(best, q));
        LOG("  reply %s: best %s %s%s\n",
            rr < 0 ? "none" : ("(" + std::to_string(rr) + "," + std::to_string(cc) + ")").c_str(), xs(best).c_str(),
            bd.c_str(), ok ? "  OK" : "");
    }
}

// ------------------------------------------------------------ JSON
static std::string jstr(const std::string& s) { return "\"" + s + "\""; }
static std::string rule_json(const Rule& R, int fam, int par, int att, XV q) {
    std::ostringstream o;
    o << "{\"fam\":" << fam << ",\"par\":" << par << ",\"att\":" << att << ",\"bound\":" << jstr(xs(q))
      << ",\"type\":\"" << R.type << "\",\"w\":" << R.w;
    if (R.orow >= 0) o << ",\"open\":[" << R.orow << "," << R.ocol << "]";
    if (R.rrow >= 0) o << ",\"white\":[" << R.rrow << "," << R.rcol << "]"; else o << ",\"white\":null";
    o << ",\"seams\":[";
    for (std::size_t i = 0; i < R.seams.size(); ++i) o << (i ? "," : "") << R.seams[i];
    o << "],\"drops\":[";
    for (std::size_t i = 0; i < R.drops.size(); ++i)
        o << (i ? "," : "") << "[" << R.drops[i][0] << "," << R.drops[i][1] << "," << R.drops[i][2] << "]";
    o << "],\"pieces\":[";
    for (std::size_t i = 0; i < R.pieces.size(); ++i) {
        auto& p = R.pieces[i];
        o << (i ? "," : "") << "{\"cols\":[" << p.a << "," << p.b << "],\"src\":\"" << p.src << "\"";
        if (p.fam >= 0) o << ",\"fam\":" << p.fam << ",\"fpar\":" << p.par;
        o << ",\"val\":" << jstr(xs(p.val)) << ",\"draw\":" << jstr(p.dr) << "}";
    }
    o << "],\"sum\":" << jstr(xs(R.sum)) << ",\"target\":" << jstr(xs(R.target)) << ",\"cmp\":\""
      << (R.cmp == 'L' ? "le" : "lf") << "\"";
    if (!R.stretch.empty()) o << ",\"stretch\":" << jstr(R.stretch);
    if (!R.sym.empty()) o << ",\"sym\":" << jstr(R.sym);
    if (!R.board.empty()) {
        o << ",\"board\":" << jstr(R.board) << ",\"gaps\":[";
        for (std::size_t i = 0; i < R.gaps.size(); ++i) o << (i ? "," : "") << R.gaps[i];
        o << "]";
    }
    if (R.type == 'G') o << ",\"T\":" << g_T;
    if (!R.sranges.empty()) {
        o << ",\"stretch_cols\":[";
        for (std::size_t i = 0; i < R.sranges.size(); ++i)
            o << (i ? "," : "") << "[" << R.sranges[i].first << "," << R.sranges[i].second << "]";
        o << "]";
    }
    if (!R.subs.empty()) {
        o << ",\"subs\":[";
        for (std::size_t i = 0; i < R.subs.size(); ++i) o << (i ? "," : "") << rule_json(R.subs[i], fam, par, att, q);
        o << "]";
    }
    o << "}";
    return o.str();
}
static std::string g_rulesPath, g_famPath;
static void append_line(const std::string& path, const std::string& line) {
    if (path.empty()) return;
    std::ofstream f(path, std::ios::app);
    f << line << '\n';
}

// ------------------------------------------------------------ parallel for
template <class F> static void pfor(int n, F fn) {
    std::atomic<int> next{0};
    std::vector<std::thread> th;
    for (int t = 0; t < g_threads; ++t)
        th.emplace_back([&, t] {
            for (;;) {
                int i = next.fetch_add(1);
                if (i >= n || g_stop) break;
                fn(i, t);
            }
        });
    for (auto& x : th) x.join();
}

// ------------------------------------------------------------ gap-representative two-round rule
// After the opening and White's reply, P = B0 N^g1 B1 ... N^gk Bk: blocks Bi
// without neutral columns, separated by runs of neutral columns N. A gap with
// g < T stands for itself; a gap with g >= T for every g' >= T of the same
// parity. Every second Blue move is checked on a reduced configuration, and
// every long (sub)gap must be stretchable in its sub-rule (NOTES §4a).
static bool is_neutral(Col c) { return c.a == FC && c.b == FC; }
struct Layout { std::vector<Strip> blocks; std::vector<int> gaps; };
static Layout layout_of(const Strip& P) {
    Layout L;
    Strip cur;
    int w = int(P.size());
    for (int j = 0; j < w;) {
        if (!is_neutral(P[j])) { cur.push_back(P[j++]); continue; }
        int k = j;
        while (k < w && is_neutral(P[k])) ++k;
        if (j == 0 || k == w) for (int t = j; t < k; ++t) cur.push_back(P[t]);
        else { L.blocks.push_back(cur); cur.clear(); L.gaps.push_back(k - j); }
        j = k;
    }
    L.blocks.push_back(cur);
    return L;
}
static Strip build(const Layout& L, const std::vector<int>& g, std::vector<int>* gstart = nullptr,
                   std::vector<int>* bstart = nullptr) {
    Strip s;
    for (std::size_t i = 0; i < L.blocks.size(); ++i) {
        if (bstart) bstart->push_back(int(s.size()));
        s.insert(s.end(), L.blocks[i].begin(), L.blocks[i].end());
        if (i < g.size()) {
            if (gstart) gstart->push_back(int(s.size()));
            s.insert(s.end(), std::size_t(g[i]), Col{FC, FC});
        }
    }
    return s;
}
static int rep_gap(int g) { return g < g_T ? g : g_T + ((g - g_T) & 1); }
static int map_col(const Layout& L, const std::vector<int>& from, const std::vector<int>& to, int c) {
    std::vector<int> bf, bt;
    build(L, from, nullptr, &bf);
    build(L, to, nullptr, &bt);
    for (std::size_t i = 0; i < L.blocks.size(); ++i)
        if (c >= bf[i] && c < bf[i] + int(L.blocks[i].size())) return bt[i] + (c - bf[i]);
    return -1;
}
// One obligation of P on a reduced configuration: a second Blue move (xr, x),
// or xr < 0 for the White-first part.
struct GCfg { std::vector<int> gaps; int xr, x; std::vector<std::pair<int, int>> ranges; };
static std::vector<GCfg> gap_configs(const Layout& L, bool hasR) {
    int k = int(L.gaps.size());
    std::vector<int> rep(k);
    for (int i = 0; i < k; ++i) rep[i] = rep_gap(L.gaps[i]);
    auto long_ranges = [&](const std::vector<int>& g, const std::vector<int>& st, int skip) {
        std::vector<std::pair<int, int>> r;
        for (int i = 0; i < k; ++i) if (i != skip && L.gaps[i] >= g_T) r.push_back({st[i], st[i] + g[i] - 1});
        return r;
    };
    std::vector<GCfg> out;
    {
        std::vector<int> st;
        Strip s = build(L, rep, &st);
        auto rr = long_ranges(rep, st, -1);
        std::vector<char> inGap(s.size(), 0);
        for (int i = 0; i < k; ++i) for (int t = 0; t < rep[i]; ++t) inGap[st[i] + t] = 1;
        for (int x = 0; x < int(s.size()); ++x)
            if (!inGap[x]) for (int r = 0; r < 5; ++r) if ((s[x].a >> r) & 1) out.push_back({rep, r, x, rr});
        if (hasR) out.push_back({rep, -1, -1, rr});
    }
    for (int i = 0; i < k; ++i) {
        bool lg = L.gaps[i] >= g_T;
        std::vector<int> lens;
        if (!lg) lens.push_back(L.gaps[i]);
        else for (int l = g_T; l <= 2 * g_T + 3; ++l) if (((l - L.gaps[i]) & 1) == 0) lens.push_back(l);
        for (int l : lens) {
            std::vector<int> g = rep;
            g[i] = l;
            std::vector<int> st;
            Strip s = build(L, g, &st);
            for (int u = 0; u < l; ++u) {
                int v = l - 1 - u;
                if (lg && (u > g_T + 1 || v > g_T + 1)) continue;
                auto rr = long_ranges(g, st, i);
                if (lg && u >= g_T) rr.push_back({st[i], st[i] + u - 1});
                if (lg && v >= g_T) rr.push_back({st[i] + u + 1, st[i] + l - 1});
                int x = st[i] + u;
                for (int r = 0; r < 5; ++r) if ((s[x].a >> r) & 1) out.push_back({g, r, x, rr});
            }
        }
    }
    return out;
}
static bool gap_sub(const Layout& L, const GCfg& cf, int oc, XV q, XV qR, int cid, bool cheap, Rule& sub) {
    Strip P = build(L, cf.gaps);
    int w = int(P.size());
    Stretch st;
    st.ranges = cf.ranges;
    std::vector<Cand> moves;
    std::vector<int> centres{oc};
    bool moveCentre = false;
    Strip base = P;
    if (cf.xr >= 0) {
        bmove(base, cf.xr, cf.x);
        moves.push_back({-1, -1, q, 'F'});
        std::set<std::pair<int, int>> seen;
        for (int ctr : {oc, cf.x}) {
            int rw = window_rw(w, ctr);
            for (int c2 = std::max(0, ctr - rw); c2 <= std::min(w - 1, ctr + rw); ++c2)
                for (int r2 = 0; r2 < 5; ++r2)
                    if (((base[c2].b >> r2) & 1) && seen.insert({r2, c2}).second) moves.push_back({r2, c2, q, 'L'});
        }
        centres.push_back(cf.x);
        sub.type = 'B'; sub.orow = cf.xr; sub.ocol = cf.x;
    } else {
        for (auto& m : white_moves(P, false, qR)) {
            bool inLong = false;
            for (auto [lo, hi] : cf.ranges) if (m.r >= 0 && m.c >= lo && m.c <= hi) inLong = true;
            if (!inLong) moves.push_back(m);
        }
        moveCentre = true;
        sub.type = 'W';
    }
    sub.gaps = cf.gaps;
    sub.board = draw(P);
    long budget = cheap ? 5000 : g_b2Budget;
    if (cheap) {
        SC sc{cid, true, false, true, 0};
        return search_cands(base, moves, centres, moveCentre, 2, st, sc, sub, &budget);
    }
    for (int cap : {2, 3}) {
        bool got = three_pass(cid, [&](SC& sc) {
            long b = budget;
            return search_cands(base, moves, centres, moveCentre, cap, st, sc, sub, &b);
        });
        if (got) return true;
    }
    return false;
}
// par: spread the sub-rules over g_threads contexts (only when not already inside pfor).
static bool find_BG(const Strip& s, int r, int c, XV q, int cid, Rule& out, bool par) {
    Strip s1 = s;
    if (!bmove(s1, r, c)) return false;
    int w = int(s.size()), RW = window_rw(w, c);
    XV qR;
    bool hasR = right_option(q, qR);
    bool atMax = w == wmax_of(w & 1) && !g_wmaxOverride;
    struct Rep {
        int rr, cc, fails = 0;
        Layout L;
        std::vector<GCfg> cfgs;
        std::vector<int> oc;
        std::vector<Rule> subs;
        std::vector<char> done;
    };
    std::vector<Rep> reps;
    auto run = [&](int n, const std::function<void(int, int)>& fn) {
        if (par) pfor(n, fn);
        else for (int i = 0; i < n && !g_stop; ++i) fn(i, cid);
    };
    for (int cc = std::max(0, c - RW); cc <= std::min(w - 1, c + RW); ++cc)
        for (int rr = 0; rr < 5; ++rr) {
            if (!((s1[cc].b >> rr) & 1)) continue;
            Strip P = s1;
            wmove(P, rr, cc);
            Rep R;
            R.rr = rr; R.cc = cc;
            R.L = layout_of(P);
            int k = int(R.L.gaps.size());
            if (atMax) {
                // The stretched side's gap must be a long gap on that side of the opening.
                std::vector<int> st;
                build(R.L, R.L.gaps, &st);
                bool okL = c < 9 || (k > 0 && R.L.gaps[0] >= g_T && st[0] + R.L.gaps[0] <= c);
                bool okR = w - 1 - c < 9 || (k > 0 && R.L.gaps[k - 1] >= g_T && st[k - 1] > c);
                if (!okL || !okR) continue;
            }
            R.cfgs = gap_configs(R.L, hasR);
            for (auto& cf : R.cfgs) R.oc.push_back(map_col(R.L, R.L.gaps, cf.gaps, c));
            R.subs.resize(R.cfgs.size());
            R.done.assign(R.cfgs.size(), 0);
            std::atomic<int> fails{0};
            run(int(R.cfgs.size()), [&](int i, int t) {
                if (gap_sub(R.L, R.cfgs[i], R.oc[i], q, qR, t, true, R.subs[i])) R.done[i] = 1;
                else ++fails;
            });
            if (g_stop) return false;
            R.fails = fails;
            if (g_verbose) {
                std::string gs;
                for (int g : R.L.gaps) gs += " " + std::to_string(g);
                LOG("      gap rule w=%d (%d,%d) reply (%d,%d): gaps%s, %zu configurations, %d cheap failures [%.0fs]\n",
                    w, r, c, rr, cc, gs.c_str(), R.cfgs.size(), R.fails, now_s());
            }
            reps.push_back(std::move(R));
        }
    std::stable_sort(reps.begin(), reps.end(), [](const Rep& a, const Rep& b) { return a.fails < b.fails; });
    int tried = 0;
    for (auto& R : reps) {
        if (++tried > 6 || g_stop) break;
        std::vector<int> todo;
        for (std::size_t i = 0; i < R.cfgs.size(); ++i) if (!R.done[i]) todo.push_back(int(i));
        std::atomic<bool> stuck{false};
        std::atomic<int> closed{0};
        std::mutex smu;
        std::string stuckAt;
        run(int(todo.size()), [&](int k, int t) {
            if (stuck) return;
            int i = todo[k];
            if (gap_sub(R.L, R.cfgs[i], R.oc[i], q, qR, t, false, R.subs[i])) { R.done[i] = 1; ++closed; return; }
            if (g_stop) return;
            std::lock_guard<std::mutex> lk(smu);
            if (!stuck) {
                stuck = true;
                auto& cf = R.cfgs[i];
                std::string gs;
                for (int g : cf.gaps) gs += (gs.empty() ? "" : ",") + std::to_string(g);
                stuckAt = "gaps [" + gs + "] second move (" + std::to_string(cf.xr) + "," + std::to_string(cf.x) +
                          ") on " + draw(build(R.L, cf.gaps));
            }
        });
        if (g_stop) return false;
        LOG("      gap rule w=%d (%d,%d) reply (%d,%d): %zu configurations, %d cheap failures, %s\n", w, r, c, R.rr,
            R.cc, R.cfgs.size(), R.fails, stuck ? ("stuck after " + std::to_string(closed.load()) + ": " + stuckAt).c_str()
                                                : "all closed");
        if (stuck) continue;
        Strip P = s1;
        wmove(P, R.rr, R.cc);
        out = Rule();
        out.type = 'G'; out.w = w; out.orow = r; out.ocol = c; out.rrow = R.rr; out.rcol = R.cc;
        out.target = q; out.cmp = 'L'; out.subs = R.subs; out.gaps = R.L.gaps; out.board = draw(P);
        return true;
    }
    return false;
}

// ------------------------------------------------------------ strategies
struct Outcome {
    bool ok = false;
    std::string why;
    std::vector<Rule> rules;
    std::vector<std::pair<int, int>> needs;
    std::vector<std::string> fails;
};
static void rule_needs(const Rule& r, std::set<std::pair<int, int>>& ns) {
    for (auto& p : r.pieces) if (p.fam >= 0) ns.insert({p.fam, p.par});
    for (auto& s : r.subs) rule_needs(s, ns);
}
static void collect_needs(Outcome& o) {
    std::set<std::pair<int, int>> ns;
    for (auto& r : o.rules) rule_needs(r, ns);
    o.needs.assign(ns.begin(), ns.end());
}
static std::string opening_str(int w, int r, int c) {
    return "w=" + std::to_string(w) + " (" + std::to_string(r) + "," + std::to_string(c) + ")";
}

static Outcome run_table(int id, int p, XV q, bool collectAll) {
    Fam f;
    {
        std::lock_guard<std::mutex> lk(g_famMu);
        f = fams[id].f;
    }
    struct Task { char type; int w, r, c; };
    std::vector<Task> tasks;
    XV qR;
    bool hasR = right_option(q, qR);
    auto ws = widths_of(p);
    if (hasR) for (int w : ws) tasks.push_back({'W', w, -1, -1});
    for (int w : ws) {
        Strip s = member(f, w);
        bool vs = is_vsym(s), hs = is_hsym(s);
        for (int c = 0; c < w; ++c)
            for (int r = 0; r < 5; ++r) {
                if (!((s[c].a >> r) & 1)) continue;
                if (vs && r > 2) continue;
                if (hs && c > (w - 1) / 2) continue;
                tasks.push_back({'B', w, r, c});
            }
    }
    std::vector<Rule> rules(tasks.size());
    std::vector<char> done(tasks.size(), 0);
    std::atomic<bool> failed{false};
    std::mutex fmu;
    Outcome o;
    double t0 = now_s();
    std::vector<int> retry;
    int twoRoundUsed = 0;
    auto fail_task = [&](int i, const std::string& extra) {
        auto& T = tasks[i];
        failed = true;
        std::lock_guard<std::mutex> lk(fmu);
        std::string d = T.type == 'W' ? "W w=" + std::to_string(T.w) + " (target " + xs(qR) + ")"
                                      : "B " + opening_str(T.w, T.r, T.c) + extra;
        o.fails.push_back(d);
        LOG("    F%d/%d q=%s FAIL %s\n", id, p, xs(q).c_str(), d.c_str());
    };
    pfor(int(tasks.size()), [&](int i, int t) {
        if (failed && !collectAll) return;
        auto& T = tasks[i];
        Strip s = member(f, T.w);
        bool got;
        if (T.type == 'W') got = find_W(s, qR, false, t, rules[i]);
        else got = find_B(s, T.r, T.c, q, t, rules[i]);
        if (g_stop) return;
        if (got) {
            done[i] = 1;
            rules[i].sym = std::string(is_vsym(s) ? "v" : "") + (is_hsym(s) ? "h" : "");
        } else if (T.type == 'B' && (g_gapRule || (g_twoRound && (T.w < wmax_of(p) || g_wmaxOverride)))) {
            std::lock_guard<std::mutex> lk(fmu);
            retry.push_back(i);
        } else fail_task(i, "");
    });
    if (!g_stop && (!failed || collectAll) && !retry.empty()) {
        std::sort(retry.begin(), retry.end());
        LOG("    F%d/%d q=%s: %zu opening(s) need two-round rules\n", id, p, xs(q).c_str(), retry.size());
        pfor(int(retry.size()), [&](int k, int t) {
            if (failed && !collectAll) return;
            int i = retry[k];
            auto& T = tasks[i];
            Strip s = member(f, T.w);
            bool got = g_gapRule && find_BG(s, T.r, T.c, q, t, rules[i], false);
            if (!got && !g_stop && g_twoRound && (T.w < wmax_of(p) || g_wmaxOverride))
                got = find_B2(s, T.r, T.c, q, t, rules[i]);
            if (g_stop) return;
            if (got) {
                done[i] = 1;
                rules[i].sym = std::string(is_vsym(s) ? "v" : "") + (is_hsym(s) ? "h" : "");
                std::lock_guard<std::mutex> lk(fmu);
                ++twoRoundUsed;
                LOG("    F%d/%d q=%s two-round (%c) OK %s reply (%d,%d), %zu sub-rules\n", id, p, xs(q).c_str(),
                    rules[i].type, opening_str(T.w, T.r, T.c).c_str(), rules[i].rrow, rules[i].rcol,
                    rules[i].subs.size());
            } else fail_task(i, " (also two-round)");
        });
    } else if (!retry.empty()) {
        for (int i : retry) fail_task(i, " (two-round not tried)");
    }
    if (g_stop) { o.why = "stopped"; return o; }
    if (failed) {
        std::sort(o.fails.begin(), o.fails.end());
        o.why = "table: " + std::to_string(o.fails.size()) + " failure(s), first " + o.fails.front();
        return o;
    }
    for (std::size_t i = 0; i < tasks.size(); ++i) o.rules.push_back(rules[i]);
    o.ok = true;
    int nb = 0, nw = 0;
    for (auto& t : tasks) (t.type == 'B' ? nb : nw)++;
    o.why = "table: " + std::to_string(nb) + " openings (" + std::to_string(twoRoundUsed) + " two-round), " +
            std::to_string(nw) + " white-first widths (" + std::to_string(int(now_s() - t0)) + "s)";
    collect_needs(o);
    return o;
}
static Outcome run_rcut(int id, int p, XV q) {
    Fam f;
    {
        std::lock_guard<std::mutex> lk(g_famMu);
        f = fams[id].f;
    }
    auto ws = widths_of(p);
    std::vector<Rule> rules(ws.size());
    std::atomic<bool> failed{false};
    Outcome o;
    std::mutex fmu;
    pfor(int(ws.size()), [&](int i, int t) {
        if (failed) return;
        bool got = find_W(member(f, ws[i]), q, true, t, rules[i]);
        if (!got && !g_stop) {
            failed = true;
            std::lock_guard<std::mutex> lk(fmu);
            o.fails.push_back("rcut w=" + std::to_string(ws[i]));
        }
    });
    if (g_stop) { o.why = "stopped"; return o; }
    if (failed) { o.why = "rcut failed at " + o.fails.front(); return o; }
    o.rules = rules;
    o.ok = true;
    o.why = "reserve-cut at every width";
    collect_needs(o);
    return o;
}
static Outcome run_reserve(int id, int p, XV q) {
    Fam f;
    std::string name;
    {
        std::lock_guard<std::mutex> lk(g_famMu);
        f = fams[id].f; name = fams[id].name;
    }
    Outcome o;
    int cid = g_threads;
    for (int side = 0; side < 2; ++side)
        for (int cc = 0; cc < 2; ++cc)
            for (int rr = 0; rr < 5; ++rr) {
                Strip s = member(f, 8);
                int col = side ? 7 - cc : cc;
                bool whiteOnly = ((s[col].b >> rr) & 1) && !((s[col].a >> rr) & 1);
                if (!whiteOnly) continue;
                wmove(s, rr, col);
                Fam g;
                for (int i = 0; i < 3; ++i) { g.L[i] = s[i]; g.R[i] = s[5 + i]; }
                int gid = get_family(g, name + "+W", cid, id);
                if (gid < 0) continue;
                XV qg = fam_q(gid, p);
                if (!qg.ok || !xle(qg, XV{q.num + ONE, q.star})) continue;
                Rule R;
                R.type = 'E'; R.w = 0; R.rrow = rr; R.rcol = col; R.target = XV{q.num + ONE, q.star}; R.sum = qg;
                PieceRec pr;
                pr.a = 0; pr.b = -1; pr.src = 'f'; pr.fam = gid; pr.par = p; pr.val = qg; pr.dr = draw(member(g, 7));
                R.pieces.push_back(pr);
                o.rules.push_back(R);
                o.ok = true;
                o.why = "reserve (" + std::to_string(rr) + "," + std::to_string(col) + " at w=8 coordinates) -> F" +
                        std::to_string(gid) + " (bound " + xs(qg) + ")";
                collect_needs(o);
                return o;
            }
    o.why = "no usable end-block reserve move";
    return o;
}

// ------------------------------------------------------------ main loop
static std::deque<std::pair<int, int>> work;
static int g_attempt = 0;
static void require(int id, int p) {
    std::lock_guard<std::mutex> lk(g_famMu);
    if (fams[id].status[p] == 0) { fams[id].status[p] = 1; work.push_back({id, p}); }
}
static void write_families() {
    if (g_famPath.empty()) return;
    std::lock_guard<std::mutex> lk(g_famMu);
    std::ofstream f(g_famPath + ".tmp");
    f << "[\n";
    for (std::size_t i = 0; i < fams.size(); ++i) {
        auto& F = fams[i];
        f << " {\"id\":" << i << ",\"name\":" << jstr(F.name) << ",\"parent\":" << F.parent
          << ",\"w6\":" << jstr(draw(member(F.f, 6))) << ",\"w7\":" << jstr(draw(member(F.f, 7))) << ",\"par\":[";
        for (int p = 0; p < 2; ++p) {
            f << (p ? "," : "") << "{\"measured\":" << jstr(xs(F.v[p])) << ",\"bound\":" << jstr(xs(F.q[p]))
              << ",\"level\":" << jstr(LEVEL_NAME[F.level[p]]) << ",\"status\":" << F.status[p]
              << ",\"method\":" << jstr(F.method[p]) << ",\"att\":" << F.att[p] << ",\"why\":" << jstr(F.why[p])
              << ",\"needs\":[";
            for (std::size_t k = 0; k < F.needs[p].size(); ++k)
                f << (k ? "," : "") << "[" << F.needs[p][k].first << "," << F.needs[p][k].second << "]";
            f << "],\"history\":[";
            for (std::size_t k = 0; k < F.history[p].size(); ++k) f << (k ? "," : "") << jstr(F.history[p][k]);
            f << "]}";
        }
        f << "]}" << (i + 1 < fams.size() ? "," : "") << "\n";
    }
    f << "]\n";
    f.close();
    std::rename((g_famPath + ".tmp").c_str(), g_famPath.c_str());
}
static int next_level(const FamInfo& F, int p) {
    for (int L = F.level[p] + 1; L <= 3; ++L) {
        XV b = bound_at(F.v[p], L);
        if (b.ok && !(b.num == F.q[p].num && b.star == F.q[p].star) && xle(F.q[p], b)) return L;
    }
    return -1;
}
static bool file_exists(const std::string& p) { struct stat st; return stat(p.c_str(), &st) == 0; }

static void check_family(int id, int p) {
    XV q;
    int level;
    {
        std::lock_guard<std::mutex> lk(g_famMu);
        q = fams[id].q[p]; level = fams[id].level[p];
    }
    int att = ++g_attempt;
    LOG("check F%d/%d q=%s (%s) att %d  [families %zu, queue %zu, exact %" PRIu64 " timeouts %" PRIu64 " searches %" PRIu64
        ", %.0fs]\n",
        id, p, xs(q).c_str(), LEVEL_NAME[level], att, fams.size(), work.size(), g_nExact.load(), g_nTimeout.load(),
        g_nSearch.load(), now_s());
    Outcome o;
    std::string method;
    std::vector<std::string> tried;
    if (!q.ok) { o.why = "bound unknown"; }
    else {
        std::vector<std::string> order;
        if (q.num < 0) order = {"reserve", "table", "rcut"};
        else order = {"table", "rcut"};
        for (auto& m : order) {
            bool last = &m == &order.back();
            int nl;
            {
                std::lock_guard<std::mutex> lk(g_famMu);
                nl = next_level(fams[id], p);
            }
            if (m == "reserve") o = run_reserve(id, p, q);
            else if (m == "table") o = run_table(id, p, q, nl < 0 && last);
            else o = run_rcut(id, p, q);
            tried.push_back(m + ": " + o.why);
            if (g_stop) return;
            if (o.ok) { method = m; break; }
            LOG("  F%d/%d q=%s %s\n", id, p, xs(q).c_str(), o.why.c_str());
        }
    }
    if (o.ok) {
        for (auto& r : o.rules) append_line(g_rulesPath, rule_json(r, id, p, att, q));
        {
            std::lock_guard<std::mutex> lk(g_famMu);
            FamInfo& F = fams[id];
            F.status[p] = method == "table" ? 2 : method == "reserve" ? 3 : 4;
            F.method[p] = method; F.why[p] = o.why; F.att[p] = att;
            F.needs[p] = o.needs;
            F.history[p].push_back("att " + std::to_string(att) + " q=" + xs(q) + " " + method + " OK");
            for (auto& [g, gp] : o.needs) fams[g].users[gp].insert({id, p});
        }
        LOG("  F%d/%d q=%s CLOSED by %s: %s\n", id, p, xs(q).c_str(), method.c_str(), o.why.c_str());
        for (auto& [g, gp] : o.needs) require(g, gp);
        return;
    }
    // failure: weaken if possible and recheck everyone who used the old bound
    std::lock_guard<std::mutex> lk(g_famMu);
    FamInfo& F = fams[id];
    std::string all;
    for (auto& t : tried) all += (all.empty() ? "" : "; ") + t;
    F.history[p].push_back("att " + std::to_string(att) + " q=" + xs(q) + " FAILED: " + all);
    append_line(g_rulesPath, "{\"fam\":" + std::to_string(id) + ",\"par\":" + std::to_string(p) + ",\"att\":" +
                                 std::to_string(att) + ",\"bound\":" + jstr(xs(q)) + ",\"failed\":" + jstr(all) + "}");
    int nl = next_level(F, p);
    if (nl < 0) {
        F.status[p] = -1; F.why[p] = all;
        std::lock_guard<std::mutex> lk2(g_logMu);
        std::printf("  F%d/%d FAILED at every bound level: %s\n", id, p, all.c_str());
        std::fflush(stdout);
        return;
    }
    F.level[p] = nl;
    F.q[p] = bound_at(F.v[p], nl);
    F.status[p] = 1;
    work.push_front({id, p});
    std::vector<std::pair<int, int>> users(F.users[p].begin(), F.users[p].end());
    F.users[p].clear();
    {
        std::lock_guard<std::mutex> lk2(g_logMu);
        std::printf("  F%d/%d weakened to %s (%s); rechecking %zu user(s)\n", id, p, xs(F.q[p]).c_str(),
                    LEVEL_NAME[nl], users.size());
        std::fflush(stdout);
    }
    for (auto& [u, up] : users) {
        FamInfo& U = fams[u];
        if (U.status[up] >= 2) {
            for (auto& [g, gp] : U.needs[up]) fams[g].users[gp].erase({u, up});
            U.needs[up].clear();
            U.status[up] = 1;
            U.history[up].push_back("requeued: F" + std::to_string(id) + "/" + std::to_string(p) + " weakened");
            work.push_back({u, up});
        }
    }
}

static void load_values(const std::string& path) {
    std::ifstream f(path);
    std::string k, v;
    std::size_t n = 0;
    while (f >> k >> v) {
        XV x;
        if (xparse(v, x)) { g_val[unhex(k)] = x; ++n; }
    }
    std::fprintf(stderr, "loaded %zu exact values from %s\n", n, path.c_str());
}
static void load_hints(const std::string& path) {
    std::ifstream f(path);
    std::string k;
    int v;
    std::size_t n = 0;
    while (f >> k >> v) { g_hint[k] = v; ++n; }
    std::fprintf(stderr, "loaded %zu integer hints from %s\n", n, path.c_str());
}

int main(int argc, char** argv) {
    std::string root = "KD", tag = "xrun", famDraw;
    int tr = -1, tc = -1;
    bool gOnly = false;
    std::vector<int> testW;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-j") g_threads = std::atoi(argv[++i]);
        else if (a == "-L") g_limit = std::atof(argv[++i]);
        else if (a == "-o") tag = argv[++i];
        else if (a == "-M") g_maxFam = std::atoi(argv[++i]);
        else if (a == "-S") g_maxSeams = std::atoi(argv[++i]);
        else if (a == "-N") g_newBudget = std::atoi(argv[++i]);
        else if (a == "-Wmax") g_wmaxOverride = std::atoi(argv[++i]);
        else if (a == "-fam") famDraw = argv[++i];
        else if (a == "-t") g_tlog = std::atoi(argv[++i]);
        else if (a == "-diag") g_diag = true;
        else if (a == "-no2") g_twoRound = false;
        else if (a == "-v") g_verbose = true;
        else if (a == "-alldrops") g_allDrops = true;
        else if (a == "-rwfar") g_rwFar = std::atoi(argv[++i]);
        else if (a == "-T") g_T = std::atoi(argv[++i]);
        else if (a == "-noG") g_gapRule = false;
        else if (a == "-G") gOnly = true;
        else if (a == "-B2") g_b2Budget = std::atol(argv[++i]);
        else if (a == "-test") {
            tr = std::atoi(argv[++i]); tc = std::atoi(argv[++i]);
            std::stringstream ws(argv[++i]);
            std::string t;
            while (std::getline(ws, t, ',')) testW.push_back(std::atoi(t.c_str()));
        } else root = a;
    }
    g_start = std::chrono::steady_clock::now();
    Cache vc(g_tlog);
    TT tt(g_tlog);
    g_vc = &vc; g_tt = &tt;
    g_ctx.reset(new Ctx[g_threads + 1]);
    const std::string dir = "/workspace/proofs/construction/research/round5/closure/runs/";
    g_valPath = dir + "xc_values.txt";
    load_values(g_valPath);
    for (const char* h : {"bounds_cache.txt", "bounds_cache_t2.txt", "bounds_cache_r5.txt"}) load_hints(dir + h);
    g_rulesPath = dir + tag + "_rules.jsonl";
    g_famPath = dir + tag + "_families.json";

    std::thread watchdog([] {
        int tick = 0;
        while (!g_quit) {
            std::this_thread::sleep_for(std::chrono::milliseconds(250));
            double t = now_s();
            for (int i = 0; i <= g_threads; ++i)
                if (t > g_ctx[i].deadline.load()) g_ctx[i].abort = true;
            if (++tick % 40 == 0 && file_exists(g_stopPath)) {
                g_stop = true;
                for (int i = 0; i <= g_threads; ++i) g_ctx[i].abort = true;
            }
            if (g_stop) for (int i = 0; i <= g_threads; ++i) g_ctx[i].abort = true;
        }
    });

    auto letter = [](const char* p) {
        Col c{0, 0};
        for (int r = 0; r < 5; ++r) {
            if (p[r] == 'o' || p[r] == 'b') c.a |= 1u << r;
            if (p[r] == 'o' || p[r] == 'w') c.b |= 1u << r;
        }
        return c;
    };
    Fam f;
    if (!famDraw.empty()) {
        Strip s = undraw(famDraw);
        if (s.size() != 7) die("-fam needs a width-7 drawing");
        for (int i = 0; i < 3; ++i) { f.L[i] = s[i]; f.R[i] = s[4 + i]; }
        root = "FAM";
    } else {
        Col N{FC, FC};
        f.L[0] = letter("obwbo"); f.L[1] = N; f.L[2] = N;
        f.R[0] = N; f.R[1] = N; f.R[2] = letter("obwbo");
        if (root == "KD") { Strip s = member(f, 8); wmove(s, 2, 0); for (int i = 0; i < 3; ++i) f.L[i] = s[i]; }
    }
    int rid = get_family(f, root, g_threads, -1);
    int rc = 0;
    if (!testW.empty()) {
        for (int w : testW) {
            Strip s = member(fams[rid].f, w);
            XV q = fams[rid].q[w & 1];
            if (g_diag) {
                LOG("w=%d opening (%d,%d) q=%s diagnosis:\n", w, tr, tc, xs(q).c_str());
                diagnose(s, tr, tc, q, g_threads);
                continue;
            }
            Rule R;
            bool got = !gOnly && find_B(s, tr, tc, q, g_threads, R);
            if (!got && g_gapRule) {
                LOG("w=%d opening (%d,%d): trying gap-representative two-round rule, T=%d [%.0fs]\n", w, tr, tc, g_T,
                    now_s());
                got = find_BG(s, tr, tc, q, g_threads, R, true);
            }
            if (!got && g_twoRound && !gOnly) {
                LOG("w=%d opening (%d,%d): no one-round rule, trying two-round [%.0fs]\n", w, tr, tc, now_s());
                got = find_B2(s, tr, tc, q, g_threads, R);
            }
            LOG("w=%d opening (%d,%d) q=%s: %s  [%.0fs]\n", w, tr, tc, xs(q).c_str(),
                got ? rule_json(R, rid, w & 1, 0, q).c_str() : "NO RULE", now_s());
        }
    } else {
        for (int p = 0; p < 2; ++p) require(rid, p);
        while (!work.empty() && !g_stop) {
            if (file_exists(g_stopPath)) { g_stop = true; break; }
            auto [id, p] = work.front();
            work.pop_front();
            check_family(id, p);
            write_families();
        }
        int closed = 0, failed = 0, pending = 0;
        for (std::size_t i = 0; i < fams.size(); ++i)
            for (int p = 0; p < 2; ++p) {
                int st = fams[i].status[p];
                if (st >= 2) ++closed; else if (st == -1) ++failed; else if (st == 1) ++pending;
            }
        LOG("\n%sSUMMARY families %zu; (family,parity) closed %d, failed %d, pending %d; exact values %" PRIu64
            ", timeouts %" PRIu64 ", %.0fs\n",
            g_stop ? "STOPPED " : "", fams.size(), closed, failed, pending, g_nExact.load(), g_nTimeout.load(), now_s());
        for (std::size_t i = 0; i < fams.size(); ++i)
            for (int p = 0; p < 2; ++p)
                if (fams[i].status[p] != 0)
                    LOG("  F%zu/%d measured %s bound %s (%s) status %d %s  %s\n", i, p, xs(fams[i].v[p]).c_str(),
                        xs(fams[i].q[p]).c_str(), LEVEL_NAME[fams[i].level[p]], fams[i].status[p],
                        fams[i].why[p].c_str(), draw(member(fams[i].f, 7)).c_str());
        write_families();
        rc = failed ? 1 : 0;
    }
    g_quit = true;
    watchdog.join();
    return rc;
}
