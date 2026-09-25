#!/usr/bin/env python3
"""Generate the TikZ figures used by both 3 x n papers.

Every board drawn from the proof (gadgets, tilings, case examples, case map)
is computed from the verified package in proofs/construction/three_row, so the
pictures cannot drift from the certified data.

    python3 papers/figures/gen_figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
THREE_ROW = HERE.parents[1] / "proofs" / "construction" / "three_row"
LEAN_GEN = HERE.parents[1] / "proofs" / "lean" / "gen"
sys.path.insert(0, str(THREE_ROW))
sys.path.insert(0, str(LEAN_GEN))

import verify as V  # noqa: E402
from windows import CASE_WINDOWS, window_masks  # noqa: E402

OUT = HERE / "gen"
S = 0.5  # cell size in cm

FILL = {
    "o": "colboth",
    "b": "colblue",
    "w": "colwhite",
    ".": "coldead",
}


# ---------------------------------------------------------------------------
# Low-level drawing
# ---------------------------------------------------------------------------

def cell_xy(r, c, x0=0.0, y0=0.0, s=S):
    return x0 + c * s, y0 - r * s


def draw_cells(rows, x0=0.0, y0=0.0, s=S, dead_pattern=True):
    out = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            x, y = cell_xy(r, c, x0, y0, s)
            fill = FILL[ch]
            out.append(f"\\fill[{fill}] ({x:.3f},{y:.3f}) rectangle ++({s:.3f},{-s:.3f});")
            if ch == "." and dead_pattern:
                out.append(f"\\fill[pattern=north east lines, pattern color=black!45] "
                           f"({x:.3f},{y:.3f}) rectangle ++({s:.3f},{-s:.3f});")
    h, w = len(rows), len(rows[0])
    out += grid_lines(x0, y0, w, h, s)
    out.append(f"\\draw[boardline] ({x0:.3f},{y0:.3f}) rectangle ++({w * s:.3f},{-h * s:.3f});")
    return out


def grid_lines(x0, y0, w, h, s=S):
    """Cell grid anchored at (x0, y0); TikZ's `grid` snaps to global multiples of the step."""
    out = []
    for c in range(1, w):
        out.append(f"\\draw[gridline] ({x0 + c * s:.3f},{y0:.3f}) -- ++(0,{-h * s:.3f});")
    for r in range(1, h):
        out.append(f"\\draw[gridline] ({x0:.3f},{y0 - r * s:.3f}) -- ++({w * s:.3f},0);")
    return out


def stone(r, c, player, x0=0.0, y0=0.0, s=S, label=None):
    x, y = cell_xy(r, c, x0, y0, s)
    cx, cy = x + s / 2, y - s / 2
    style = "bluestone" if player == "Blue" else "whitestone"
    out = [f"\\node[{style}, minimum size={0.78 * s:.3f}cm] at ({cx:.3f},{cy:.3f}) {{}};"]
    if label is not None:
        color = "white" if player == "Blue" else "black"
        out.append(f"\\node[text={color}, font=\\tiny\\bfseries] at ({cx:.3f},{cy:.3f}) {{{label}}};")
    return out


def block_box(start, width, label, x0=0.0, y0=0.0, s=S, rows=3, below=None, color="black"):
    x = x0 + start * s
    out = [f"\\draw[blockline, draw={color}] ({x:.3f},{y0:.3f}) rectangle ++({width * s:.3f},{-rows * s:.3f});"]
    if label:
        out.append(f"\\node[blocklabel, text={color}] at ({x + width * s / 2:.3f},{y0 + 0.28:.3f}) {{{label}}};")
    if below:
        out.append(f"\\node[boundlabel] at ({x + width * s / 2:.3f},{y0 - rows * s - 0.28:.3f}) {{{below}}};")
    return out


def picture(body, scale=1.0):
    return ("\\begin{tikzpicture}[scale=%.3f, every node/.style={transform shape}]\n" % scale
            + "\n".join(body) + "\n\\end{tikzpicture}\n")


def write(name, text):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.tex").write_text(text)


def mask_rows(blue, white, n):
    return V.diagram(blue, white, n)


def stones_rows(rows, stones):
    """Cells holding stones are drawn as neither-legal under the stone."""
    rows = [list(r) for r in rows]
    for _, (r, c) in stones:
        rows[r][c] = "."
    return ["".join(r) for r in rows]


def actual_board(n, moves, x0=0.0, y0=0.0, labels=True, dead_pattern=False):
    blue, white = V.play(n, moves)
    rows = stones_rows(mask_rows(blue, white, n), moves)
    body = draw_cells(rows, x0, y0, dead_pattern=dead_pattern)
    for i, (player, (r, c)) in enumerate(moves):
        body += stone(r, c, player, x0, y0, label=(str(i + 1) if labels and len(moves) > 1 else None))
    return body


def col_ticks(n, x0=0.0, y0=0.0, every=1, s=S):
    out = []
    for c in range(0, n, every):
        x = x0 + c * s + s / 2
        out.append(f"\\node[font=\\tiny, text=black!55] at ({x:.3f},{y0 + 0.2:.3f}) {{{c}}};")
    return out


def row_ticks(x0=0.0, y0=0.0, s=S):
    return [f"\\node[font=\\tiny, text=black!55] at ({x0 - 0.2:.3f},{y0 - r * s - s / 2:.3f}) {{{r}}};"
            for r in range(3)]


# ---------------------------------------------------------------------------
# Package helpers
# ---------------------------------------------------------------------------

PKG = V.load_package()


def role_rows(name):
    role = PKG.roles[name]
    return V.diagram(role.blue, role.white, role.width)


ROLE_TEX = {
    "E4": r"$E_4$", "E4bar": r"$\bar E_4$", "F1": r"$F_1$", "K_corner": r"$K_{\mathrm{corner}}$",
    "K_outer2": r"$K_{\mathrm{outer2}}$", "K_outer4": r"$K_{\mathrm{outer4}}$",
    "T_middle1": r"$T_{\mathrm{middle1}}$", "J5": r"$J_5$", "Z7": r"$Z_7$", "Z7_end": r"$Z_7^{\mathrm{end}}$",
    "C3": r"$C_3$", "H_c": r"$H_c$",
}


def role_tex(label):
    if label.startswith("E4_open_"):
        r, c = label.split("_")[2:]
        return rf"$E_4^{{({r},{c})}}$"
    return ROLE_TEX.get(label, label)


def bound_tex(bound):
    if bound == 0:
        return r"$\le 0$"
    if bound.denominator == 1:
        return rf"$\le {bound.numerator}$"
    sign = "-" if bound < 0 else ""
    return rf"$\le {sign}\tfrac{{{abs(bound.numerator)}}}{{{bound.denominator}}}$"


# ---------------------------------------------------------------------------
# Figures: rules and basics
# ---------------------------------------------------------------------------

def fig_rules_legality():
    moves = [("Blue", (1, 1)), ("White", (1, 2)), ("Blue", (0, 3)), ("White", (2, 0))]
    body = actual_board(5, moves) + col_ticks(5) + row_ticks()
    write("rules_legality", picture(body, 1.25))


def fig_rules_forbidden():
    body = []
    # Blue cannot play next to Blue; White can.
    body += draw_cells(["ooo"], 0, 0)
    body += stone(0, 1, "Blue", 0, 0)
    body.append(r"\node[font=\small, text=red!70!black] at (0.25,-0.25) {$\times$};")
    body.append(r"\node[font=\small, text=red!70!black] at (1.25,-0.25) {$\times$};")
    body.append(r"\node[font=\scriptsize, align=center] at (0.75,-0.95) {Blue may not\\play beside Blue};")
    body += draw_cells(["ooo"], 3, 0)
    body += stone(0, 1, "Blue", 3, 0)
    body += stone(0, 0, "White", 3, 0)
    body.append(r"\node[font=\small, text=green!45!black] at (4.25,-0.25) {\checkmark};")
    body.append(r"\node[font=\scriptsize, align=center] at (3.75,-0.95) {White may play\\beside Blue};")
    write("rules_forbidden", picture(body, 1.3))


def fig_legend():
    body = []
    items = [("o", "legal for both"), ("b", "Blue only"), ("w", "White only"), (".", "legal for neither")]
    x = 0.0
    for ch, text in items:
        body += draw_cells([ch], x, 0)
        body.append(f"\\node[anchor=west, font=\\scriptsize] at ({x + 0.6:.3f},-0.25) {{{text}}};")
        x += 2.9
    body += stone(0, 0, "Blue", x, 0)
    body.append(f"\\node[anchor=west, font=\\scriptsize] at ({x + 0.6:.3f},-0.25) {{Blue stone}};")
    x += 2.4
    body += stone(0, 0, "White", x, 0)
    body.append(f"\\node[anchor=west, font=\\scriptsize] at ({x + 0.6:.3f},-0.25) {{White stone}};")
    write("legend", picture(body, 1.0))


def tiny_strip(stones, x, y, s=0.32):
    """A 1 x 3 strip used in the game tree."""
    out = []
    for c in range(3):
        cx = x + c * s
        out.append(f"\\draw[gridline, fill=colboth] ({cx:.3f},{y:.3f}) rectangle ++({s:.3f},{-s:.3f});")
    for player, c in stones:
        out.append(f"\\node[{'bluestone' if player == 'Blue' else 'whitestone'}, minimum size={0.8 * s:.3f}cm] "
                   f"at ({x + c * s + s / 2:.3f},{y - s / 2:.3f}) {{}};")
    return out


def fig_game_tree():
    """Complete Blue-first game tree of the 1 x 3 strip (up to mirror symmetry)."""
    body = []
    nodes = {
        "root": ([], 3.0, 0.0),
        "L": ([("Blue", 0)], 1.2, -1.4),
        "M": ([("Blue", 1)], 4.8, -1.4),
        "LM": ([("Blue", 0), ("White", 1)], 0.0, -2.8),
        "LR": ([("Blue", 0), ("White", 2)], 2.4, -2.8),
        "LMR": ([("Blue", 0), ("White", 1), ("Blue", 2)], 0.0, -4.2),
        "ML": ([("Blue", 1), ("White", 0)], 5.4, -2.8),
    }
    edges = [("root", "L", "Blue"), ("root", "M", "Blue"), ("L", "LM", "White"), ("L", "LR", "White"),
             ("LM", "LMR", "Blue"), ("M", "ML", "White")]
    w = 0.96
    for a, b, who in edges:
        _, xa, ya = nodes[a]
        _, xb, yb = nodes[b]
        color = "colbluedark" if who == "Blue" else "black!60"
        body.append(f"\\draw[-{{Stealth}}, {color}, thick] ({xa + w / 2:.3f},{ya - 0.4:.3f}) -- "
                    f"({xb + w / 2:.3f},{yb + 0.08:.3f});")
    for key, (st, x, y) in nodes.items():
        body += tiny_strip(st, x, y)
    notes = {
        "root": r"Blue to move",
        "LR": r"\textbf{Blue stuck:}\\\textbf{White wins}",
        "LMR": r"White stuck:\\Blue wins",
        "ML": r"\textbf{Blue stuck:}\\\textbf{White wins}",
    }
    for key, text in notes.items():
        _, x, y = nodes[key]
        body.append(f"\\node[font=\\tiny, align=center, anchor=north] at ({x + w / 2:.3f},{y - 0.4:.3f}) {{{text}}};")
    body.append(r"\node[font=\tiny, text=black!60, align=left, anchor=west] at (6.2,-1.25) "
                r"{(Blue on the right end\\is the mirror image\\of the left end)};")
    write("game_tree", picture(body, 1.25))


def fig_mirror():
    n = 6
    seq = [("Blue", (0, 1)), ("White", (2, 4)), ("Blue", (1, 3)), ("White", (1, 2)),
           ("Blue", (2, 0)), ("White", (0, 5))]
    body = actual_board(n, seq)
    cx, cy = n * S / 2, -1.5 * S
    body.append(f"\\fill[red!70!black] ({cx:.3f},{cy:.3f}) circle (1.6pt);")
    body.append(f"\\draw[<-, red!70!black] ({cx:.3f},{cy - 0.08:.3f}) -- ({cx:.3f},{-3 * S - 0.3:.3f}) "
                f"node[below, font=\\tiny] {{centre of the half-turn}};")
    for (p1, (r1, c1)), (p2, (r2, c2)) in zip(seq[0::2], seq[1::2]):
        x1, y1 = cell_xy(r1, c1)
        x2, y2 = cell_xy(r2, c2)
        body.append(f"\\draw[densely dotted, red!60!black, thick] ({x1 + S / 2:.3f},{y1 - S / 2:.3f}) -- "
                    f"({x2 + S / 2:.3f},{y2 - S / 2:.3f});")
    write("mirror_even", picture(body, 1.5))


def fig_odd_center():
    n = 5
    body = draw_cells(["ooooo"] * 3)
    x, y = cell_xy(1, 2)
    body.append(f"\\draw[red!70!black, very thick] ({x:.3f},{y:.3f}) rectangle ++({S:.3f},{-S:.3f});")
    body.append(f"\\fill[red!70!black] ({x + S / 2:.3f},{y - S / 2:.3f}) circle (1.6pt);")
    body.append(f"\\node[font=\\scriptsize, text=red!70!black, anchor=west] at ({n * S + 0.2:.3f},{y - S / 2:.3f}) "
                f"{{the centre cell is its own mirror image}};")
    write("odd_center", picture(body, 1.4))


# ---------------------------------------------------------------------------
# Figures: gadgets, seams, comparison
# ---------------------------------------------------------------------------

def gadget_panel(name, x0, y0, show_ports=True, show_moves=True, title=None):
    role = PKG.roles[name]
    rows = role_rows(name)
    body = draw_cells(rows, x0, y0)
    manifest_role = next(r for r in RAW_ROLES if r["role"] == name)
    moves = manifest_role.get("local_moves", {})
    if show_moves:
        for player in ("blue", "white"):
            if player in moves:
                r, c = moves[player]
                if c < 0:
                    continue
                body += stone(r, c, "Blue" if player == "blue" else "White", x0, y0)
    w = role.width
    body.append(f"\\node[font=\\small] at ({x0 + w * S / 2:.3f},{y0 + 0.3:.3f}) {{{title or role_tex(name)}}};")
    body.append(f"\\node[font=\\scriptsize] at ({x0 + w * S / 2:.3f},{y0 - 3 * S - 0.25:.3f}) "
                f"{{{bound_tex(role.bound)}}};")
    if show_ports:
        left, right = V.ports(role.white, w)
        for r in range(3):
            for side, port, xx in (("L", left, x0 - 0.12), ("R", right, x0 + w * S + 0.12)):
                col = "colwhitedark" if port[r] == "1" else "black!25"
                body.append(f"\\fill[{col}] ({xx:.3f},{y0 - r * S - S / 2:.3f}) circle (1.5pt);")
    return body


def fig_gadget_gallery():
    names = [["E4", "E4bar", "F1", "C3", "K_corner"],
             ["K_outer2", "K_outer4", "T_middle1"],
             ["J5", "Z7", "Z7_end"]]
    body = []
    y = 0.0
    for line in names:
        x = 0.0
        for name in line:
            body += gadget_panel(name, x, y)
            x += PKG.roles[name].width * S + 1.1
        y -= 3 * S + 1.4
    write("gadget_gallery", picture(body, 1.15))


def fig_opened_e4():
    body = []
    x = 0.0
    for r, c in V.ODD_E4_CELLS:
        name = f"E4_open_{r}_{c}"
        rows = role_rows(name)
        body += draw_cells(rows, x, 0)
        body += stone(r, c, "Blue", x, 0)
        body.append(f"\\node[font=\\small] at ({x + 1:.3f},0.3) {{{role_tex(name)}}};")
        body.append(f"\\node[font=\\scriptsize] at ({x + 1:.3f},{-3 * S - 0.25:.3f}) {{$\\le -1$}};")
        x += 4 * S + 0.8
    write("opened_e4", picture(body, 1.15))


def fig_e4_parity():
    rows = role_rows("E4")
    body = draw_cells(rows)
    for r in range(3):
        for c in range(4):
            x, y = cell_xy(r, c)
            if (r + c) % 2 == 1:
                body.append(f"\\fill[red!70!black] ({x + S / 2:.3f},{y - S / 2:.3f}) circle (2pt);")
    write("e4_parity", picture(body, 1.5))


def fig_seams():
    body = []
    # good: E4 | E4
    body += draw_cells(role_rows("E4"), 0, 0)
    body += draw_cells(role_rows("E4"), 4 * S, 0)
    body.append(f"\\draw[seam] ({4 * S:.3f},0.15) -- ({4 * S:.3f},{-3 * S - 0.15:.3f});")
    body.append(r"\node[font=\small] at (2,0.35) {$E_4\,\big|\,E_4$};")
    body.append(r"\node[font=\scriptsize, align=center, text=green!40!black] at (2,-2.05) "
                r"{right port 010 meets left port 101:\\no row is White-legal on both sides \checkmark};")
    # bad: Z7_end | E4bar
    x0 = 5.6
    body += draw_cells(role_rows("Z7_end"), x0, 0)
    body += draw_cells(role_rows("E4bar"), x0 + 7 * S, 0)
    xs = x0 + 7 * S
    body.append(f"\\draw[seam] ({xs:.3f},0.15) -- ({xs:.3f},{-3 * S - 0.15:.3f});")
    body.append(f"\\draw[red!75!black, very thick] ({xs - S:.3f},{-S:.3f}) rectangle ++({2 * S:.3f},{-S:.3f});")
    body.append(f"\\node[font=\\small] at ({x0 + 5.5 * S:.3f},0.35) {{$Z_7^{{\\mathrm{{end}}}}\\,\\big|\\,\\bar E_4$}};")
    body.append(f"\\node[font=\\scriptsize, align=center, text=red!70!black] at ({x0 + 5.5 * S:.3f},-2.05) "
                r"{port 111 meets port 010: the middle row\\is White-legal on both sides $\times$};")
    write("seams", picture(body, 1.2))


def fig_comparison_schematic():
    """An actual position above; the same board cut into virtual blocks below."""
    n = 15
    plan = V.plan_width_4k3(PKG, n, 0, 6)
    moves = plan.moves()
    body = actual_board(n, moves, 0, 0, labels=False)
    body.append(f"\\node[anchor=east, font=\\scriptsize] at (-0.3,-0.75) {{actual}};")
    gap = 0.35
    y1 = -3.0
    x = 0.0
    for blk in plan.blocks:
        rows = V.diagram(blk.blue, blk.white, blk.width)
        body += draw_cells(rows, x, y1)
        body.append(f"\\node[font=\\scriptsize] at ({x + blk.width * S / 2:.3f},{y1 + 0.28:.3f}) {{{role_tex(blk.label)}}};")
        body.append(f"\\node[font=\\tiny] at ({x + blk.width * S / 2:.3f},{y1 - 3 * S - 0.22:.3f}) {{{bound_tex(blk.bound)}}};")
        x += blk.width * S + gap
    body.append(f"\\node[anchor=east, font=\\scriptsize] at (-0.3,{y1 - 0.75:.3f}) {{virtual}};")
    body.append(f"\\draw[-{{Stealth}}, thick] ({n * S / 2:.3f},-1.65) -- ({n * S / 2:.3f},-2.35) "
                f"node[midway, right, font=\\scriptsize] {{cut at seams, give Blue more, give White less}};")
    write("comparison_schematic", picture(body, 1.1))


def fig_tiling_4k1():
    n = 13
    plan = V.plan_width_4k1(PKG, n)
    body = draw_cells(["o" * n] * 3, 0, 0)
    body.append(r"\node[anchor=east, font=\scriptsize] at (-0.3,-0.75) {empty $3\times13$};")
    y1 = -2.3
    body += draw_virtual(plan.blocks, n, y1)
    body.append(f"\\node[anchor=east, font=\\scriptsize] at (-0.3,{y1 - 0.75:.3f}) {{$E_4^3F_1$}};")
    write("tiling_4k1", picture(body, 1.2))


def draw_virtual(blocks, n, y0, dead=(), gap=0.0):
    body = []
    for blk in blocks:
        rows = V.diagram(blk.blue, blk.white, blk.width)
        x = blk.start * S
        body += draw_cells(rows, x, y0)
        body += block_box(blk.start, blk.width, role_tex(blk.label), 0, y0, below=bound_tex(blk.bound))
    for c in dead:
        body += draw_cells(["."] * 3, c * S, y0)
        body += block_box(c, 1, r"\tiny dead", 0, y0)
    for blk in blocks[1:]:
        x = blk.start * S
        body.append(f"\\draw[seam] ({x:.3f},{y0 + 0.08:.3f}) -- ({x:.3f},{y0 - 3 * S - 0.08:.3f});")
    return body


# ---------------------------------------------------------------------------
# Figures: the 4k+3 induction
# ---------------------------------------------------------------------------

def fig_normalization():
    n = 15
    k = 3
    body = []
    rows = []
    for r in range(3):
        rows.append("".join("b" if (r <= 1 and c <= 2 * k + 1) else "o" for c in range(n)))
    body += draw_cells(rows)
    body += col_ticks(n) + row_ticks()
    mx = n * S / 2
    body.append(f"\\draw[red!70!black, dashed, thick] ({mx:.3f},0.35) -- ({mx:.3f},{-3 * S - 0.15:.3f});")
    body.append(f"\\draw[red!70!black, dashed, thick] (-0.1,{-1.5 * S:.3f}) -- ({n * S + 0.1:.3f},{-1.5 * S:.3f});")
    body.append(f"\\draw[<->, red!70!black] ({mx - 1.2:.3f},{-3 * S - 0.35:.3f}) -- ({mx + 1.2:.3f},{-3 * S - 0.35:.3f}) "
                f"node[midway, below, font=\\tiny] {{left--right flip}};")
    body.append(f"\\draw[<->, red!70!black] ({n * S + 0.35:.3f},-0.1) -- ({n * S + 0.35:.3f},{-3 * S + 0.1:.3f}) "
                f"node[midway, right, font=\\tiny] {{top--bottom flip}};")
    write("normalization", picture(body, 1.2))


CASE_COLORS = {1: "case1", 2: "case2", 3: "case3", 4: "case4", 5: "case5", 6: "case6"}


def case_of(n, r, c):
    return V.plan_width_4k3(PKG, n, r, c).case


def fig_case_map():
    n = 23
    k = (n - 3) // 4
    body = []
    for r in range(3):
        for c in range(n):
            x, y = cell_xy(r, c)
            if r <= 1 and c <= 2 * k + 1:
                cs = case_of(n, r, c)
                body.append(f"\\fill[{CASE_COLORS[cs]}] ({x:.3f},{y:.3f}) rectangle ++({S:.3f},{-S:.3f});")
                body.append(f"\\node[font=\\tiny\\bfseries] at ({x + S / 2:.3f},{y - S / 2:.3f}) {{{cs}}};")
            else:
                body.append(f"\\fill[black!7] ({x:.3f},{y:.3f}) rectangle ++({S:.3f},{-S:.3f});")
    body += grid_lines(0, 0, n, 3)
    body.append(f"\\draw[boardline] (0,0) rectangle ({n * S:.3f},{-3 * S:.3f});")
    body += col_ticks(n) + row_ticks()
    write("case_map", picture(body, 1.05))


def case_example(name, n, r, c, caption_moves=True):
    plan = V.plan_width_4k3(PKG, n, r, c)
    moves = plan.moves()
    body = actual_board(n, moves, 0, 0, labels=False)
    body += col_ticks(n, every=1)
    body.append(r"\node[anchor=east, font=\scriptsize] at (-0.25,-0.75) {actual};")
    y1 = -2.5
    body += draw_virtual(plan.blocks, n, y1, dead=plan.dead)
    body.append(f"\\node[anchor=east, font=\\scriptsize] at (-0.25,{y1 - 0.75:.3f}) {{virtual}};")
    # mark moves on virtual board too, faintly
    for player, (rr, cc) in moves:
        x, y = cell_xy(rr, cc, 0, y1)
        body.append(f"\\draw[{'colbluedark' if player == 'Blue' else 'black'}, thick] "
                    f"({x + S / 2:.3f},{y - S / 2:.3f}) circle ({0.3 * S:.3f});")
    write(name, picture(body, 1.0))
    return plan


def fig_case_examples():
    n = 19
    examples = {
        "case1": (0, 5), "case2": (0, 0), "case3": (0, 6),
        "case4": (0, 8), "case5": (1, 5), "case6": (1, 7),
    }
    for name, (r, c) in examples.items():
        case_example(f"example_{name}", n, r, c)
    case_example("example_case6_big", 23, 1, 11)


def fig_base3():
    """The four normalized 3x3 openings and White's certified replies."""
    scan = json.loads((THREE_ROW / "certificates" / "base" / "existing_library_scan.json").read_text())
    answers = next(entry for entry in scan if entry["n"] == 3)["answers"]
    body = []
    for i, ans in enumerate(answers):
        moves = [("Blue", tuple(ans["open"])), ("White", tuple(ans["reply"]))]
        x0 = i * 2.4
        body += actual_board(3, moves, x0, 0)
        body.append(f"\\node[font=\\scriptsize] at ({x0 + 0.75:.3f},0.3) "
                    f"{{Blue $({ans['open'][0]},{ans['open'][1]})$}};")
    write("base3", picture(body, 1.3))


def fig_case6_zoom():
    """Close-up of the dead separator column."""
    n = 13
    c = 5
    moves = [("Blue", (1, c)), ("White", (0, c + 1))]
    blue, white = V.play(n, moves)
    rows = stones_rows(mask_rows(blue, white, n), moves)
    body = draw_cells(rows, 0, 0, dead_pattern=False)
    for player, (r, cc) in moves:
        body += stone(r, cc, player)
    x = c * S
    body.append(f"\\draw[red!75!black, very thick] ({x:.3f},0.08) rectangle ++({S:.3f},{-3 * S - 0.16:.3f});")
    body.append(f"\\node[font=\\scriptsize, text=red!70!black] at ({x + S / 2:.3f},{-3 * S - 0.35:.3f}) {{dead column}};")
    body.append(f"\\draw[decorate, decoration={{brace, amplitude=4pt}}] (0,0.15) -- ({c * S:.3f},0.15) "
                f"node[midway, above=3pt, font=\\scriptsize] {{empty $3\\times c$}};")
    body.append(f"\\draw[decorate, decoration={{brace, amplitude=4pt}}] ({(c + 1) * S:.3f},0.15) -- ({n * S:.3f},0.15) "
                f"node[midway, above=3pt, font=\\scriptsize] {{right region, width $s=n-c-1$}};")
    body.append(f"\\node[anchor=west, font=\\tiny, align=left] at ({n * S + 0.25:.3f},{-0.75:.3f}) "
                r"{column $c$: every cell is Blue-illegal\\(the Blue stone and its two neighbours);\\"
                r"top: White-illegal, beside White's reply;\\bottom: White voluntarily never plays it};")
    write("case6_zoom", picture(body, 1.4))


def fig_recursion_chain():
    """How Case 6 calls narrower boards on 3x23 at c = 11 -> H_11 etc."""
    body = []
    widths = [3, 7, 11, 15, 19, 23]
    for i, w in enumerate(widths):
        x = i * 2.1
        base = w in (3, 7, 11)
        style = "basebox" if base else "stepbox"
        body.append(f"\\node[{style}] (n{w}) at ({x:.3f},0) {{$3\\times{w}$}};")
    for i, w in enumerate(widths):
        if w in (3, 7, 11):
            continue
        for smaller in widths:
            if smaller < w and (w - smaller - 1) >= 7:
                bend = 12 + 5 * (widths.index(w) - widths.index(smaller))
                body.append(f"\\draw[-{{Stealth}}, black!55] (n{w}.north) to[bend right={bend}] (n{smaller}.north);")
    body.append(r"\node[font=\scriptsize, text=black!60] at (2.1,-0.75) {certified base cases};")
    body.append(r"\node[font=\scriptsize, text=black!60] at (8.4,-0.75) {six-case step (arrows: Case 6 uses a narrower board)};")
    write("recursion_chain", picture(body, 1.0))


def fig_roadmap():
    body = [
        r"\node[rootbox] (root) at (0,0) {empty $3\times n$ board: is it a second-player win?};",
        r"\node[leafbox] (even) at (-4.6,-1.6) {$n$ even\\half-turn mirror};",
        r"\node[leafbox] (one) at (0,-1.6) {$n=4k+1$\\tiling $E_4^kF_1$};",
        r"\node[leafbox] (three) at (4.6,-1.6) {$n=4k+3$\\bases $3,7,11$ + induction};",
        r"\node[smallbox] (c1) at (1.3,-3.3) {Case 1\\odd parity};",
        r"\node[smallbox] (c25) at (4.1,-3.3) {Cases 2--5\\explicit reply + tiling};",
        r"\node[smallbox] (c6) at (6.9,-3.3) {Case 6\\dead column\\+ smaller board};",
        r"\draw[-{Stealth}] (root) -- (even);",
        r"\draw[-{Stealth}] (root) -- (one);",
        r"\draw[-{Stealth}] (root) -- (three);",
        r"\draw[-{Stealth}] (three) -- (c1);",
        r"\draw[-{Stealth}] (three) -- (c25);",
        r"\draw[-{Stealth}] (three) -- (c6);",
        r"\draw[-{Stealth}, dashed, red!65!black] (c6.east) to[out=0, in=0, looseness=1.4] "
        r"node[right, font=\tiny, align=left] {strong\\induction} (three.east);",
    ]
    write("roadmap", picture(body, 1.0))


def fig_number_line():
    body = [
        r"\draw[-{Stealth}] (-5.4,0) -- (2.4,0);",
    ]
    for val, lab in ((-4, "$-1$"), (-3, r"$-\frac34$"), (0, "$0$"), (1, r"$\frac14$")):
        body.append(f"\\draw ({val * 1.2:.2f},0.1) -- ({val * 1.2:.2f},-0.1) node[below, font=\\scriptsize] {{{lab}}};")
    body.append(r"\fill[colbluedark] (-4.8,0) circle (2pt) node[above=2pt, font=\tiny, align=center] {opened $E_4$};")
    body.append(r"\draw[-{Stealth}, orange!75!black, thick] (-4.8,0.55) to[bend left=25] "
                r"node[above, font=\tiny] {$+\frac14$ from $C_3$} (-3.6,0.55);")
    body.append(r"\fill[red!70!black] (-3.6,0) circle (2pt);")
    body.append(r"\node[font=\tiny, text=red!70!black] at (-3.6,-0.75) {total $<0$: White wins};")
    body.append(r"\fill[black!15] (0,-0.05) rectangle (2.3,0.05);")
    write("number_line", picture(body, 1.2))


def fig_sum_intuition():
    """Two independent regions: White answers in the region Blue just played."""
    body = []
    for x0, moves, labels in ((0.0, [("Blue", (1, 1)), ("White", (0, 2))], ("1", "2")),
                              (3.0, [("Blue", (0, 1)), ("White", (2, 2))], ("3", "4"))):
        blue, white = V.play(4, moves)
        body += draw_cells(stones_rows(mask_rows(blue, white, 4), moves), x0, 0, dead_pattern=False)
        for (player, (r, c)), lab in zip(moves, labels):
            body += stone(r, c, player, x0, 0, label=lab)
    body.append(r"\node[font=\small] at (1,0.35) {region $A$};")
    body.append(r"\node[font=\small] at (4,0.35) {region $B$};")
    body.append(r"\node[font=\scriptsize, align=center] at (2.5,-2.05) "
                r"{White always answers in the same region as Blue.\\If White wins each region as second player, she wins the sum.};")
    write("sum_intuition", picture(body, 1.3))


LEAN_WINDOW_TITLES = {
    "case1_0_1": r"Case 1, $(0,1)$", "case1_0_3": r"Case 1, $(0,3)$", "case1_1_0": r"Case 1, $(1,0)$",
    "case1_1_2": r"Case 1, $(1,2)$", "case2": "Case 2", "case3": "Case 3", "case4": "Case 4",
    "case5": "Case 5", "case6": "Case 6",
}


def fig_lean_windows():
    """The window gadgets of the Lean proof, with Blue's opening and White's reply."""
    body = []
    x, y = 0.0, 0.0
    per_row = 3
    for i, (name, spec) in enumerate(CASE_WINDOWS.items()):
        ww, v, u, _, _ = spec
        _, a, b = window_masks(*spec)
        rows = stones_rows(V.diagram(a, b, ww), [("Blue", v), ("White", u)])
        body += draw_cells(rows, x, y)
        body += stone(*v, "Blue", x, y)
        body += stone(*u, "White", x, y)
        body.append(f"\\node[font=\\small] at ({x + ww * S / 2:.3f},{y + 0.3:.3f}) {{{LEAN_WINDOW_TITLES[name]}}};")
        if (i + 1) % per_row == 0:
            x, y = 0.0, y - 3 * S - 1.0
        else:
            x += 8 * S + 1.0
    write("lean_windows", picture(body, 1.1))


def fig_lean_scheme():
    """The uniform shape of every inductive case in the Lean proof."""
    n = 19
    spec = CASE_WINDOWS["case3"]
    ww, v, u, _, _ = spec
    _, a, b = window_masks(*spec)
    start = 4
    body = []
    e4 = role_rows("E4")
    ebar = role_rows("E4bar")
    body += draw_cells(e4, 0, 0)
    body += block_box(0, 4, r"$E_4^{a}$", 0, 0)
    rows = stones_rows(V.diagram(a, b, ww), [("Blue", v), ("White", u)])
    body += draw_cells(rows, start * S, 0)
    body += stone(v[0], v[1], "Blue", start * S, 0)
    body += stone(u[0], u[1], "White", start * S, 0)
    body += block_box(start, ww, r"window $W$", 0, 0)
    for j in range((n - start - ww) // 4):
        body += draw_cells(ebar, (start + ww + 4 * j) * S, 0)
        body += block_box(start + ww + 4 * j, 4, r"$\bar E_4$" if j == 0 else "", 0, 0)
    for c in (start, start + ww) + tuple(start + ww + 4 * j for j in range(1, (n - start - ww) // 4)):
        body.append(f"\\draw[seam] ({c * S:.3f},0.08) -- ({c * S:.3f},{-3 * S - 0.08:.3f});")
    body.append(f"\\draw[decorate, decoration={{brace, amplitude=4pt, mirror}}] "
                f"({(start + ww) * S:.3f},{-3 * S - 0.15:.3f}) -- ({n * S:.3f},{-3 * S - 0.15:.3f}) "
                r"node[midway, below=4pt, font=\scriptsize] {$\bar E_4^{\,b}$, $b=k-a-1$};")
    write("lean_scheme", picture(body, 1.1))


RAW_ROLES = []


def main():
    RAW_ROLES.extend(json.loads((THREE_ROW / "manifest.json").read_text())["roles"])
    fig_rules_legality()
    fig_rules_forbidden()
    fig_legend()
    fig_game_tree()
    fig_mirror()
    fig_odd_center()
    fig_gadget_gallery()
    fig_opened_e4()
    fig_e4_parity()
    fig_seams()
    fig_comparison_schematic()
    fig_tiling_4k1()
    fig_normalization()
    fig_case_map()
    fig_case_examples()
    fig_base3()
    fig_case6_zoom()
    fig_recursion_chain()
    fig_roadmap()
    fig_number_line()
    fig_sum_intuition()
    fig_lean_windows()
    fig_lean_scheme()
    print(f"wrote {len(list(OUT.glob('*.tex')))} figures to {OUT}")


if __name__ == "__main__":
    main()
