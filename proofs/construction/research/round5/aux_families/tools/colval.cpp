// colval.cpp -- DISCOVERY evaluator for five-row Col permission strips.
//
// Computes the exact value x + e* of a shadow state (A,B) on a 5 x W grid
// (W <= 12), assuming the classical theorem that every Col position is a
// number or a number plus star.  Nothing computed here is a proof; every
// claim used later is backed by a response-DAG certificate checked by an
// independent, search-free verifier.
//
// Input (stdin), one query per line:
//   W s0 s1 s2 s3 s4          rows top->bottom, W chars each from {o,b,w,.}
//   W s0 s1 s2 s3 s4 opts     also print the value of every option
// Output: the value, e.g. "-1/2+*", or with opts a list of options.
//
// Internal layout is column-major (bit c*5+r).  The interaction graph joins
// adjacent cells legal for a common player; its components are independent
// summands.  Components are memoized up to translation and the four strip
// symmetries.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

typedef uint64_t U;
static const int H = 5;
static const int K = 30;  // values are integers scaled by 2^K
static const long long ONE = 1LL << K;

struct Val {
  long long x;
  int s;
};

static U ROW0 = 0, ROW4 = 0, FULLALL = 0;
static U NBC[64];  // closed neighbourhoods on the 5 x 12 board
static int REV5[32];

static inline U nbrs(U S) {
  U up = (S >> 1) & ~ROW4;
  U down = (S << 1) & ~ROW0 & FULLALL;
  U left = S >> 5;
  U right = (S << 5) & FULLALL;
  return up | down | left | right;
}

// ---------------------------------------------------------------- memo
struct Entry {
  U a, b;
  long long v;  // x*2 + s
};
static Entry* table_ = nullptr;
static size_t cap_ = 0, used_ = 0;
static inline size_t hsh(U a, U b) {
  U x = a * 0x9E3779B97F4A7C15ULL ^ (b + 0x632BE59BD9B4E019ULL) * 0xC2B2AE3D27D4EB4FULL;
  x ^= x >> 31;
  x *= 0xBF58476D1CE4E5B9ULL;
  x ^= x >> 29;
  return (size_t)x;
}
static const U OCC = 1ULL << 63;  // occupied flag; calloc'd zero = empty
static bool lookup(U a, U b, Val& out) {
  size_t i = hsh(a, b) & (cap_ - 1);
  U ka = a | OCC;
  while (true) {
    Entry& e = table_[i];
    if (e.a == 0) return false;
    if (e.a == ka && e.b == b) {
      out.x = e.v >> 1;
      out.s = (int)(e.v & 1);
      return true;
    }
    i = (i + 1) & (cap_ - 1);
  }
}
static void store(U a, U b, Val v) {
  if (used_ * 10 > cap_ * 7) {
    fprintf(stderr, "memo table full (%zu entries)\n", used_);
    exit(3);
  }
  size_t i = hsh(a, b) & (cap_ - 1);
  while (table_[i].a != 0) i = (i + 1) & (cap_ - 1);
  table_[i].a = a | OCC;
  table_[i].b = b;
  table_[i].v = v.x * 2 + v.s;
  used_++;
}

// ------------------------------------------------------ simplest number
static long long simplest(bool hasLo, long long lo, bool loOpen, bool hasHi, long long hi, bool hiOpen) {
  auto inI = [&](long long x) {
    if (hasLo && (x < lo || (loOpen && x == lo))) return false;
    if (hasHi && (x > hi || (hiOpen && x == hi))) return false;
    return true;
  };
  if (inI(0)) return 0;
  bool positive = hasLo && (lo > 0 || (lo == 0 && loOpen));
  if (!positive) {
    // entirely negative: mirror
    long long r = simplest(hasHi, -hi, hiOpen, hasLo, -lo, loOpen);
    return -r;
  }
  // smallest integer >= lo in I
  long long n = (lo + ONE - 1) / ONE * ONE;  // lo > 0 here
  if (n == lo && loOpen) n += ONE;
  if (inI(n)) return n;
  for (int k = 1; k <= K; k++) {
    long long step = 1LL << (K - k);
    long long c = (lo + step - 1) / step * step;
    if (c == lo && loOpen) c += step;
    if (inI(c)) return c;
  }
  fprintf(stderr, "precision exhausted\n");
  exit(4);
}

static Val combine(const std::vector<Val>& L, const std::vector<Val>& R) {
  bool hasLo = false, loOpen = false, hasHi = false, hiOpen = false;
  long long lo = 0, hi = 0;
  for (const Val& v : L) {
    bool open = (v.s == 0);
    if (!hasLo || v.x > lo) {
      hasLo = true;
      lo = v.x;
      loOpen = open;
    } else if (v.x == lo)
      loOpen = loOpen || open;
  }
  for (const Val& v : R) {
    bool open = (v.s == 0);
    if (!hasHi || v.x < hi) {
      hasHi = true;
      hi = v.x;
      hiOpen = open;
    } else if (v.x == hi)
      hiOpen = hiOpen || open;
  }
  bool nonempty = !hasLo || !hasHi || lo < hi || (lo == hi && !loOpen && !hiOpen);
  if (nonempty) return Val{simplest(hasLo, lo, loOpen, hasHi, hi, hiOpen), 0};
  if (lo != hi) {
    fprintf(stderr, "number+star structure violated (lo>hi)\n");
    exit(5);
  }
  return Val{lo, 1};
}

// --------------------------------------------------------- evaluation
static inline U revcols(U m, int w) {
  U r = 0;
  for (int c = 0; c < w; c++) r |= ((m >> (5 * c)) & 31ULL) << (5 * (w - 1 - c));
  return r;
}
static inline U vflip(U m, int w) {
  U r = 0;
  for (int c = 0; c < w; c++) r |= (U)REV5[(m >> (5 * c)) & 31] << (5 * c);
  return r;
}

static Val evalPos(U A, U B);
static long long nodes = 0;

static Val evalComp(U A, U B) {
  // canonicalize
  U L = A | B;
  int sh = (__builtin_ctzll(L) / 5) * 5;
  A >>= sh;
  B >>= sh;
  L >>= sh;
  int w = (63 - __builtin_clzll(L)) / 5 + 1;
  U bestA = A, bestB = B;
  {
    U a2 = revcols(A, w), b2 = revcols(B, w);
    if (a2 < bestA || (a2 == bestA && b2 < bestB)) bestA = a2, bestB = b2;
    U a3 = vflip(A, w), b3 = vflip(B, w);
    if (a3 < bestA || (a3 == bestA && b3 < bestB)) bestA = a3, bestB = b3;
    U a4 = revcols(a3, w), b4 = revcols(b3, w);
    if (a4 < bestA || (a4 == bestA && b4 < bestB)) bestA = a4, bestB = b4;
  }
  A = bestA;
  B = bestB;
  Val v;
  if (lookup(A, B, v)) return v;
  nodes++;
  std::vector<Val> Lo, Ro;
  for (U x = A; x; x &= x - 1) {
    int c = __builtin_ctzll(x);
    Lo.push_back(evalPos(A & ~NBC[c], B & ~(1ULL << c)));
  }
  for (U x = B; x; x &= x - 1) {
    int c = __builtin_ctzll(x);
    Ro.push_back(evalPos(A & ~(1ULL << c), B & ~NBC[c]));
  }
  v = combine(Lo, Ro);
  store(A, B, v);
  return v;
}

static Val evalPos(U A, U B) {
  Val tot{0, 0};
  U L = A | B;
  while (L) {
    U comp = L & (~L + 1);
    while (true) {
      U nc = comp | (nbrs(comp & A) & A) | (nbrs(comp & B) & B);
      if (nc == comp) break;
      comp = nc;
    }
    Val v = evalComp(A & comp, B & comp);
    tot.x += v.x;
    tot.s ^= v.s;
    L &= ~comp;
  }
  return tot;
}

static std::string fmt(Val v) {
  std::ostringstream o;
  long long x = v.x;
  if (x == 0 && v.s) return "*";
  long long num = x, den = ONE;
  while (den > 1 && num % 2 == 0) num /= 2, den /= 2;
  if (den == 1)
    o << num;
  else
    o << num << "/" << den;
  if (v.s) o << "+*";
  return o.str();
}

int main(int argc, char** argv) {
  int logcap = argc > 1 ? atoi(argv[1]) : 24;
  cap_ = 1ULL << logcap;
  if (logcap > 26) {
    fprintf(stderr, "logcap capped at 26 (1.6 GB) by the shared compute budget\n");
    return 1;
  }
  table_ = (Entry*)calloc(cap_, sizeof(Entry));
  if (!table_) {
    fprintf(stderr, "alloc failed\n");
    return 1;
  }
  for (int i = 0; i < 32; i++) {
    int r = 0;
    for (int j = 0; j < 5; j++)
      if (i >> j & 1) r |= 1 << (4 - j);
    REV5[i] = r;
  }
  const int WMAX = 12;
  for (int c = 0; c < WMAX; c++) {
    ROW0 |= 1ULL << (5 * c);
    ROW4 |= 1ULL << (5 * c + 4);
  }
  FULLALL = (1ULL << (5 * WMAX)) - 1;
  for (int c = 0; c < WMAX; c++)
    for (int r = 0; r < H; r++) {
      int v = 5 * c + r;
      U m = 1ULL << v;
      if (r > 0) m |= 1ULL << (v - 1);
      if (r < H - 1) m |= 1ULL << (v + 1);
      if (c > 0) m |= 1ULL << (v - 5);
      if (c < WMAX - 1) m |= 1ULL << (v + 5);
      NBC[v] = m;
    }
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream in(line);
    int W;
    std::string s[5], opt;
    in >> W >> s[0] >> s[1] >> s[2] >> s[3] >> s[4];
    in >> opt;
    if (W < 1 || W > WMAX) {
      printf("ERR width\n");
      continue;
    }
    U A = 0, B = 0;
    bool bad = false;
    for (int r = 0; r < 5; r++) {
      if ((int)s[r].size() != W) bad = true;
      for (int c = 0; c < W && !bad; c++) {
        char ch = s[r][c];
        int v = 5 * c + r;
        if (ch == 'o' || ch == 'b') A |= 1ULL << v;
        if (ch == 'o' || ch == 'w') B |= 1ULL << v;
        if (ch != 'o' && ch != 'b' && ch != 'w' && ch != '.') bad = true;
      }
    }
    if (bad) {
      printf("ERR pattern\n");
      fflush(stdout);
      continue;
    }
    Val v = evalPos(A, B);
    if (opt == "opts") {
      printf("%s |", fmt(v).c_str());
      for (U x = A; x; x &= x - 1) {
        int c = __builtin_ctzll(x);
        printf(" B(%d,%d)=%s", c % 5, c / 5, fmt(evalPos(A & ~NBC[c], B & ~(1ULL << c))).c_str());
      }
      printf(" |");
      for (U x = B; x; x &= x - 1) {
        int c = __builtin_ctzll(x);
        printf(" W(%d,%d)=%s", c % 5, c / 5, fmt(evalPos(A & ~(1ULL << c), B & ~NBC[c])).c_str());
      }
      printf("\n");
    } else
      printf("%s\n", fmt(v).c_str());
    fflush(stdout);
  }
  fprintf(stderr, "nodes=%lld memo=%zu\n", nodes, used_);
  return 0;
}
