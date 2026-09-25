"""Exact canonical forms of short partizan games, and Col on arbitrary graphs.

This module makes no Col-specific assumption about values. Canonical forms are
computed by the textbook procedure (delete dominated options, bypass reversible
options, repeat) and compared with Conway's recursive order. Every canonical
form is hash-consed, so two canonical games are equal exactly when their ids
coincide.

A Col position is a finite simple graph (closed neighbourhood masks) together
with two bit masks: A = cells legal for Blue (Left), B = cells legal for White
(Right). Blue at v gives (A & ~N[v], B & ~{v}); White at v gives
(A & ~{v}, B & ~N[v]).
"""

from fractions import Fraction
import math
import sys

sys.setrecursionlimit(1_000_000)


class GameTable:
    """Hash-consed game forms with a memoised order relation."""

    def __init__(self):
        self.left = []
        self.right = []
        self.index = {}
        self._leq = {}
        self._canon_cache = {}
        self.zero = self.form((), ())
        self.star = self.canon({self.zero}, {self.zero})
        self._numbers = {}
        self._number_of = {}

    # -- forms ---------------------------------------------------------------
    def form(self, lefts, rights):
        key = (frozenset(lefts), frozenset(rights))
        gid = self.index.get(key)
        if gid is None:
            gid = len(self.left)
            self.left.append(tuple(sorted(key[0])))
            self.right.append(tuple(sorted(key[1])))
            self.index[key] = gid
        return gid

    # -- order -----------------------------------------------------------------
    def leq(self, g, h):
        """Conway order: g <= h iff no g^L >= h and no h^R <= g."""
        key = (g, h)
        cached = self._leq.get(key)
        if cached is not None:
            return cached
        result = True
        for gl in self.left[g]:
            if self.leq(h, gl):
                result = False
                break
        if result:
            for hr in self.right[h]:
                if self.leq(hr, g):
                    result = False
                    break
        self._leq[key] = result
        return result

    def eq(self, g, h):
        return self.leq(g, h) and self.leq(h, g)

    # -- canonical form --------------------------------------------------------
    def canon(self, lefts, rights):
        """Canonical form of {lefts | rights}; all options must be canonical."""
        key = (frozenset(lefts), frozenset(rights))
        cached = self._canon_cache.get(key)
        if cached is not None:
            return cached
        ls, rs = set(lefts), set(rights)
        while True:
            ls = {a for a in ls if not any(b != a and self.leq(a, b) for b in ls)}
            rs = {a for a in rs if not any(b != a and self.leq(b, a) for b in rs)}
            g = self.form(ls, rs)
            changed = False
            new_ls = set()
            for gl in ls:
                rev = next((x for x in self.right[gl] if self.leq(x, g)), None)
                if rev is None:
                    new_ls.add(gl)
                else:
                    new_ls.update(self.left[rev])
                    changed = True
            new_rs = set()
            for gr in rs:
                rev = next((x for x in self.left[gr] if self.leq(g, x)), None)
                if rev is None:
                    new_rs.add(gr)
                else:
                    new_rs.update(self.right[rev])
                    changed = True
            if not changed:
                self._canon_cache[key] = g
                return g
            ls, rs = new_ls, new_rs

    # -- arithmetic on canonical forms -------------------------------------------
    def neg(self, g, _memo=None):
        if _memo is None:
            _memo = {}
        if g in _memo:
            return _memo[g]
        res = self.canon({self.neg(x, _memo) for x in self.right[g]},
                         {self.neg(x, _memo) for x in self.left[g]})
        _memo[g] = res
        return res

    def add(self, g, h, _memo=None):
        if _memo is None:
            _memo = {}
        key = (g, h)
        if key in _memo:
            return _memo[key]
        ls = {self.add(x, h, _memo) for x in self.left[g]}
        ls |= {self.add(g, x, _memo) for x in self.left[h]}
        rs = {self.add(x, h, _memo) for x in self.right[g]}
        rs |= {self.add(g, x, _memo) for x in self.right[h]}
        res = self.canon(ls, rs)
        _memo[key] = res
        return res

    # -- numbers -----------------------------------------------------------------
    def number(self, q):
        """Canonical form of the dyadic rational q, built from its definition."""
        q = Fraction(q)
        if q in self._numbers:
            return self._numbers[q]
        den = q.denominator
        if den & (den - 1):
            raise ValueError("not dyadic")
        if den == 1:
            n = q.numerator
            if n == 0:
                g = self.zero
            elif n > 0:
                g = self.canon({self.number(n - 1)}, set())
            else:
                g = self.canon(set(), {self.number(n + 1)})
        else:
            step = Fraction(1, den)
            g = self.canon({self.number(q - step)}, {self.number(q + step)})
        self._numbers[q] = g
        self._number_of[g] = q
        return g

    def classify(self, g, max_den_log=12, bound=64):
        """Return (x, eps) if g is canonically x or x+* for a dyadic x, else None.

        Uses the facts that canonical forms are unique and that the canonical
        form of x+* is {x | x}. The recogniser only reads the structure of g.
        """
        if g in self._number_of:
            return (self._number_of[g], 0)
        num = self._as_number(g, max_den_log, bound)
        if num is not None:
            return (num, 0)
        ls, rs = self.left[g], self.right[g]
        if len(ls) == 1 and len(rs) == 1 and ls[0] == rs[0]:
            x = self._as_number(ls[0], max_den_log, bound)
            if x is not None and self.canon({ls[0]}, {ls[0]}) == g:
                return (x, 1)
        return None

    def _as_number(self, g, max_den_log, bound):
        if g in self._number_of:
            return self._number_of[g]
        ls, rs = self.left[g], self.right[g]
        if len(ls) > 1 or len(rs) > 1:
            return None
        lo = self._as_number(ls[0], max_den_log, bound) if ls else None
        hi = self._as_number(rs[0], max_den_log, bound) if rs else None
        if (ls and lo is None) or (rs and hi is None):
            return None
        if lo is not None and hi is not None and not lo < hi:
            return None
        cand = simplest_between(lo, hi)
        if cand is None or abs(cand) > bound:
            return None
        if cand.denominator > (1 << max_den_log):
            return None
        return cand if self.number(cand) == g else None


def simplest_between(lo, hi):
    """Simplest dyadic x with lo < x < hi (None bounds are infinite)."""
    if lo is None and hi is None:
        return Fraction(0)
    if lo is None:
        return Fraction(0) if hi > 0 else Fraction(math.ceil(hi) - 1)
    if hi is None:
        return Fraction(0) if lo < 0 else Fraction(math.floor(lo) + 1)
    if lo < 0 < hi:
        return Fraction(0)
    if hi <= 0:
        return -simplest_between(-hi, -lo)
    n = math.floor(lo) + 1
    if n < hi:
        return Fraction(n)
    den = 1
    while True:
        den *= 2
        cand = Fraction(math.floor(lo * den) + 1, den)
        if cand < hi:
            return cand


def fmt(value):
    if value is None:
        return "NOT number/number+*"
    x, eps = value
    s = str(x)
    return s + ("+*" if eps else "") if not (x == 0 and eps) else "*"


# ---------------------------------------------------------------------------
# Col positions on arbitrary graphs
# ---------------------------------------------------------------------------

def grid_closed_nbhd(h, w):
    nb = []
    for v in range(h * w):
        r, c = divmod(v, w)
        m = 1 << v
        for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= rr < h and 0 <= cc < w:
                m |= 1 << (rr * w + cc)
        nb.append(m)
    return nb


def graph_closed_nbhd(n, edges):
    nb = [1 << v for v in range(n)]
    for u, v in edges:
        nb[u] |= 1 << v
        nb[v] |= 1 << u
    return nb


class ColEvaluator:
    """Canonical Col values on one fixed graph, memoised on (A, B)."""

    def __init__(self, table, closed_nbhd):
        self.t = table
        self.nb = closed_nbhd
        self.memo = {}

    def left_options(self, a, b):
        x = a
        while x:
            bit = x & -x
            x ^= bit
            v = bit.bit_length() - 1
            yield v, (a & ~self.nb[v], b & ~bit)

    def right_options(self, a, b):
        x = b
        while x:
            bit = x & -x
            x ^= bit
            v = bit.bit_length() - 1
            yield v, (a & ~bit, b & ~self.nb[v])

    def value(self, a, b):
        key = (a, b)
        g = self.memo.get(key)
        if g is not None:
            return g
        ls = {self.value(*p) for _, p in self.left_options(a, b)}
        rs = {self.value(*p) for _, p in self.right_options(a, b)}
        g = self.t.canon(ls, rs)
        self.memo[key] = g
        return g


class SumOutcome:
    """Independent outcome check of (Col position) + (explicit game form).

    The second summand is any hash-consed form of the table (for example a
    number built by GameTable.number). No canonical simplification is used:
    this is plain minimax on the disjoint sum, so it independently certifies
    a claimed value via 'G - x - eps* is a second-player win'.
    """

    def __init__(self, table, closed_nbhd):
        self.t = table
        self.nb = closed_nbhd
        self.memo = {}

    def wins(self, a, b, g, star, left_to_move):
        key = (a, b, g, star, left_to_move)
        r = self.memo.get(key)
        if r is not None:
            return r
        res = False
        if left_to_move:
            x = a
            while x and not res:
                bit = x & -x
                x ^= bit
                v = bit.bit_length() - 1
                if not self.wins(a & ~self.nb[v], b & ~bit, g, star, False):
                    res = True
            if not res:
                for gl in self.t.left[g]:
                    if not self.wins(a, b, gl, star, False):
                        res = True
                        break
            if not res and star and not self.wins(a, b, g, 0, False):
                res = True
        else:
            x = b
            while x and not res:
                bit = x & -x
                x ^= bit
                v = bit.bit_length() - 1
                if not self.wins(a & ~bit, b & ~self.nb[v], g, star, True):
                    res = True
            if not res:
                for gr in self.t.right[g]:
                    if not self.wins(a, b, gr, star, True):
                        res = True
                        break
            if not res and star and not self.wins(a, b, g, 0, True):
                res = True
        self.memo[key] = res
        return res

    def is_second_player_win(self, a, b, g, star):
        return (not self.wins(a, b, g, star, True)) and (not self.wins(a, b, g, star, False))
