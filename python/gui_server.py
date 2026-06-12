#!/usr/bin/env python3
"""Browser GUI for inspecting Col tablebase positions."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from col.dfs import DfsSolver
from col.cli import positive_int
from col.core import P1, P2
from col.tablebase import Tablebase


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Col Tablebase</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #fafafa;
      --panel: #ffffff;
      --ink: #1d1d1f;
      --muted: #6e6e73;
      --line: #e5e5ea;
      --line-strong: #d1d1d6;
      --accent: #0d9488;
      --accent-soft: rgba(13, 148, 136, 0.08);
      --good-bg: #ecfdf5;
      --good-ink: #047857;
      --bad-bg: #fef2f2;
      --bad-ink: #b91c1c;
      --neutral-bg: #f5f5f7;
      --black: #111827;
      --white: #ffffff;
    }

    * { box-sizing: border-box; }
    html {
      height: 100%;
      overflow: hidden;
    }

    body {
      margin: 0;
      height: 100%;
      overflow: hidden;
      background: var(--bg);
      color: var(--ink);
      font: 13px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .app {
      display: grid;
      grid-template-columns: minmax(440px, 1fr) 390px;
      height: 100vh;
      overflow: hidden;
    }

    .main {
      padding: 16px;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      gap: 12px;
      min-height: 0;
      overflow: hidden;
    }

    .topbar, .side {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 10px;
    }

    .topbar {
      padding: 10px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .title {
      font-size: 15px;
      font-weight: 600;
      letter-spacing: -0.01em;
    }

    .meta {
      color: var(--muted);
      font-size: 12px;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 2px;
    }

    #path {
      display: none;
    }

    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    button {
      border: 1px solid var(--line-strong);
      background: #ffffff;
      color: var(--ink);
      border-radius: 6px;
      min-height: 30px;
      padding: 5px 11px;
      font: inherit;
      font-size: 12px;
      cursor: pointer;
    }

    button:hover { background: #fafafa; }
    button.primary {
      background: var(--ink);
      border-color: var(--ink);
      color: white;
    }
    button.primary:hover { background: #27272a; }
    button.active {
      background: var(--accent-soft);
      border-color: rgba(13, 148, 136, 0.35);
      color: var(--accent);
    }
    button:disabled {
      cursor: default;
      opacity: 0.45;
    }

    .cell:disabled {
      opacity: 1;
    }

    .board-wrap {
      display: grid;
      place-items: center;
      min-height: 0;
      overflow: hidden;
      background: var(--bg);
      border: none;
      border-radius: 10px;
      padding: 20px;
      container-type: size;
    }

    .board {
      display: grid;
      gap: 3px;
      --board-ratio: 1;
      width: min(100cqw, calc(100cqh * var(--board-ratio)));
      aspect-ratio: var(--board-ratio);
    }

    .cell {
      position: relative;
      border: 1px solid var(--line);
      background: #ffffff;
      border-radius: 6px;
      display: grid;
      place-items: center;
      min-width: 0;
      min-height: 0;
      padding: 0;
      transition: box-shadow 120ms ease, border-color 120ms ease;
    }

    .cell.legal {
      background: #ffffff;
      border-color: var(--line-strong);
      cursor: pointer;
    }

    .cell.legal:hover {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-soft);
    }

    .cell.illegal-empty {
      background: #f5f5f7;
      border-color: #ececf0;
    }

    .cell.illegal-empty::after {
      content: "";
      width: 24%;
      height: 1.5px;
      background: #d1d1d6;
      transform: rotate(-35deg);
      border-radius: 999px;
    }

    .stone {
      width: 62%;
      height: 62%;
      border-radius: 999px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
    }
    .stone.p1 { background: var(--black); }
    .stone.p2 {
      background: var(--white);
      border: 1px solid #c7c7cc;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.8), 0 1px 2px rgba(0, 0, 0, 0.08);
    }

    .dot {
      width: 10%;
      height: 10%;
      border-radius: 999px;
      background: var(--accent);
      opacity: 0.45;
    }

    .coord {
      position: absolute;
      top: 3px;
      left: 4px;
      color: #aeaeb2;
      font-size: clamp(8px, 1vmin, 10px);
      opacity: 0;
      transition: opacity 120ms ease;
      pointer-events: none;
    }

    .cell:hover .coord {
      opacity: 1;
    }

    .side {
      border-radius: 0;
      border-width: 0 0 0 1px;
      padding: 16px;
      height: 100vh;
      overflow: auto;
    }

    .section {
      border-bottom: 1px solid var(--line);
      padding: 0 0 14px;
      margin: 0 0 14px;
    }

    .section:last-child {
      border-bottom: 0;
      margin-bottom: 0;
      padding-bottom: 0;
    }

    h2 {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0;
      color: var(--muted);
      margin: 0 0 9px;
      font-weight: 700;
    }

    .status {
      display: grid;
      gap: 8px;
    }

    .kv {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: baseline;
      min-height: 24px;
    }

    .value {
      font-weight: 650;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }

    .tag {
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 2px 7px;
      border-radius: 4px;
      background: var(--neutral-bg);
      color: #374151;
      font-weight: 650;
      font-size: 11px;
      line-height: 1;
      white-space: nowrap;
    }
    .tag.win { background: var(--good-bg); color: var(--good-ink); }
    .tag.loss { background: var(--bad-bg); color: var(--bad-ink); }
    .tag.unknown { background: var(--neutral-bg); color: #68717d; }
    .tag.memory { background: #edf2fa; color: #315174; }

    .moves {
      display: grid;
      gap: 0;
      border: 1px solid var(--line);
      border-radius: 4px;
      overflow: hidden;
    }

    .move-head {
      display: grid;
      grid-template-columns: 58px 1fr auto;
      gap: 10px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      padding: 0 8px 6px;
    }

    .move-head span:nth-child(2) {
      text-align: left;
    }

    .move {
      width: 100%;
      display: grid;
      grid-template-columns: 58px 1fr auto;
      align-items: center;
      gap: 10px;
      text-align: left;
      background: #fff;
      border: 0;
      border-bottom: 1px solid var(--line);
      border-radius: 0;
      min-height: 36px;
      padding: 6px 8px;
    }
    .move:last-child { border-bottom: 0; }
    .move:hover { background: #f8fafc; border-color: var(--line); }

    .move .coord-label {
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }

    .move .move-meta {
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .log {
      background: #f8fafc;
      color: #3b4652;
      border: 1px solid var(--line);
      border-radius: 4px;
      padding: 9px;
      min-height: 86px;
      max-height: 180px;
      overflow: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      white-space: pre-wrap;
    }

    @media (max-width: 860px) {
      html, body {
        overflow: auto;
      }
      .app {
        grid-template-columns: 1fr;
        height: auto;
        min-height: 100vh;
        overflow: visible;
      }
      .main {
        overflow: visible;
      }
      .side {
        border-width: 1px 0 0;
        border-radius: 0;
        height: auto;
        max-height: 55vh;
      }
      .board-wrap {
        min-height: min(70vh, 640px);
        container-type: size;
      }
      .board {
        width: min(100cqw, calc(100cqh * var(--board-ratio)));
      }
      .topbar {
        align-items: flex-start;
        flex-direction: column;
      }
      .actions { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="app">
    <main class="main">
      <section class="topbar">
        <div>
          <div class="title">Col Tablebase</div>
          <div class="meta">
            <span id="boardSize"></span>
            <span id="turn"></span>
            <span id="path"></span>
          </div>
        </div>
        <div class="actions">
          <a href="/dashboard" style="align-self:center;color:#0d9488;font-weight:600;text-decoration:none;font-size:12px">Solver status</a>
          <button id="vsComputerBtn">Play vs CPU</button>
          <button id="undoBtn">Undo</button>
          <button id="resetBtn">Reset</button>
          <button id="solveBtn" class="primary">Analyze current</button>
        </div>
      </section>
      <section class="board-wrap">
        <div id="board" class="board"></div>
      </section>
    </main>
    <aside class="side">
      <section class="section">
        <h2>Current Position</h2>
        <div class="status">
          <div class="kv"><span>Tablebase</span><span id="knownTag" class="tag unknown">unknown</span></div>
          <div class="kv"><span>Result</span><span id="winner" class="value">-</span></div>
          <div class="kv"><span>Game</span><span id="gameStatus" class="value">-</span></div>
          <div class="kv"><span>Side to move</span><span id="stmEval" class="value">-</span></div>
          <div class="kv"><span>Key</span><span id="key" class="value">-</span></div>
        </div>
      </section>
      <section class="section">
        <h2>Legal Moves</h2>
        <div class="move-head"><span>Move</span><span>Source</span><span>Result</span></div>
        <div id="moves" class="moves"></div>
      </section>
      <section class="section">
        <h2>Engine Log</h2>
        <div id="log" class="log"></div>
      </section>
    </aside>
  </div>
  <script>
    let state = null;
    const boardEl = document.getElementById('board');
    const movesEl = document.getElementById('moves');
    const logEl = document.getElementById('log');

    async function api(path, body = null) {
      const options = body ? {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
      } : {};
      const response = await fetch(path, options);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || response.statusText);
      return payload;
    }

    function log(message) {
      const time = new Date().toLocaleTimeString();
      logEl.textContent = `[${time}] ${message}\n` + logEl.textContent;
    }

    function cellText(cell) {
      return `${cell.row} ${cell.col}`;
    }

    function turnText(turn) {
      return turn === 0 ? 'P1' : 'P2';
    }

    function render(payload) {
      state = payload;
      document.getElementById('boardSize').textContent = `${state.m} x ${state.n}`;
      document.getElementById('turn').textContent = `${turnText(state.turn)} to move`;
      document.getElementById('path').textContent = state.tablebase_path;
      document.getElementById('undoBtn').disabled = !state.can_undo;
      document.getElementById('vsComputerBtn').classList.toggle('active', state.vs_computer);
      document.getElementById('vsComputerBtn').textContent = state.vs_computer ? 'Vs CPU: on' : 'Play vs CPU';
      document.getElementById('solveBtn').disabled = state.game_over;
      document.getElementById('gameStatus').textContent = state.game_over
        ? state.game_result
        : (state.vs_computer ? 'You are P1 vs CPU' : 'Free play');

      boardEl.style.gridTemplateColumns = `repeat(${state.n}, minmax(0, 1fr))`;
      boardEl.style.setProperty('--board-ratio', `${state.n / state.m}`);
      boardEl.innerHTML = '';
      for (const cell of state.cells) {
        const div = document.createElement('button');
        div.className = 'cell' + (cell.legal ? ' legal' : '') + (cell.blocked ? ' illegal-empty' : '');
        div.type = 'button';
        div.disabled = !cell.legal || !state.can_play;
        div.title = cell.blocked ? `row ${cell.row}, col ${cell.col}: illegal for ${turnText(state.turn)}` : `row ${cell.row}, col ${cell.col}`;
        div.innerHTML = `<span class="coord">${cell.row},${cell.col}</span>`;
        if (cell.occupant === 'P1') {
          div.innerHTML += '<span class="stone p1"></span>';
        } else if (cell.occupant === 'P2') {
          div.innerHTML += '<span class="stone p2"></span>';
        } else if (cell.legal) {
          div.innerHTML += '<span class="dot"></span>';
        }
        div.addEventListener('click', () => play(cell.row, cell.col));
        boardEl.appendChild(div);
      }

      renderCurrent();
      renderMoves();
    }

    function renderCurrent() {
      const current = state.current;
      const tag = document.getElementById('knownTag');
      tag.className = 'tag';
      if (!current.known) {
        tag.classList.add('unknown');
        tag.textContent = 'unknown';
        document.getElementById('stmEval').textContent = '-';
        document.getElementById('winner').textContent = '-';
      } else {
        tag.classList.add('memory');
        tag.textContent = current.source;
        document.getElementById('stmEval').textContent = current.side_to_move_result;
        document.getElementById('winner').textContent = current.result;
      }
      document.getElementById('key').textContent = current.key;
    }

    function renderMoves() {
      movesEl.innerHTML = '';
      if (!state.legal_moves.length) {
        movesEl.textContent = 'No legal moves.';
        return;
      }
      for (const move of state.legal_moves) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'move';
        const tagClass = move.known ? (move.winning_for_current ? 'win' : 'loss') : 'unknown';
        const tagText = move.known ? move.result : 'unknown';
        btn.innerHTML = `
          <span class="coord-label">${cellText(move)}</span>
          <span class="move-meta">${move.source || 'not in tablebase'}</span>
          <span class="tag ${tagClass}">${tagText}</span>
        `;
        btn.disabled = !state.can_play;
        btn.addEventListener('click', () => play(move.row, move.col));
        movesEl.appendChild(btn);
      }
    }

    async function refresh() {
      const payload = await api('/api/solve', {});
      render(payload.state);
      log(`analysis ready: ${payload.result}, new states ${payload.new_states}`);
    }

    async function play(row, col) {
      try {
        const payload = await api('/api/play', {row, col});
        render(payload.state);
        log(`you played ${row} ${col}`);
        if (payload.computer_move) {
          const cpu = payload.computer_move;
          log(`CPU played ${cpu.row} ${cpu.col}`);
        }
        if (payload.state.game_over && payload.state.game_result) {
          log(payload.state.game_result);
        }
      } catch (error) {
        log(error.message);
      }
    }

    async function toggleVsComputer() {
      try {
        const enabled = !(state && state.vs_computer);
        const payload = await api('/api/vs-computer', {enabled});
        render(payload.state);
        log(enabled ? 'play vs CPU enabled (you are P1)' : 'free play');
      } catch (error) {
        log(error.message);
      }
    }

    async function solveCurrent() {
      const started = performance.now();
      const payload = await api('/api/solve', {});
      render(payload.state);
      log(`analysis: ${payload.result}, new states ${payload.new_states}, ${(performance.now() - started).toFixed(1)}ms`);
    }

    document.getElementById('vsComputerBtn').addEventListener('click', toggleVsComputer);
    document.getElementById('undoBtn').addEventListener('click', async () => {
      const payload = await api('/api/undo', {});
      render(payload.state);
      log('undo');
    });
    document.getElementById('resetBtn').addEventListener('click', async () => {
      const payload = await api('/api/reset', {});
      render(payload.state);
      log('reset');
    });
    document.getElementById('solveBtn').addEventListener('click', solveCurrent);

    refresh().catch(error => log(error.message));
  </script>
</body>
</html>
"""

TABLEBASE_NAME_RE = re.compile(r"^(\d+)x(\d+)_sym\.pkl$")

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Col Solver Dashboard</title>
  <style>
    :root { color-scheme: light; --bg: #fafafa; --panel: #fff; --ink: #1d1d1f; --muted: #6e6e73; --line: #e5e5ea; --accent: #0d9488; }
    * { box-sizing: border-box; }
    body { margin: 0; font: 14px/1.5 ui-sans-serif, system-ui, sans-serif; background: var(--bg); color: var(--ink); }
    header { display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; background: var(--panel); border-bottom: 1px solid var(--line); }
    header a { color: var(--accent); text-decoration: none; font-weight: 600; }
    main { max-width: 960px; margin: 0 auto; padding: 20px; display: grid; gap: 16px; }
    section { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
    h1 { margin: 0; font-size: 18px; }
    h2 { margin: 0 0 10px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
    .stat { background: #f8fafc; border-radius: 8px; padding: 12px; }
    .stat label { display: block; font-size: 11px; color: var(--muted); margin-bottom: 4px; }
    .stat value { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--line); }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; }
    .idle { color: var(--muted); }
    .running { color: var(--accent); font-weight: 600; }
  </style>
</head>
<body>
  <header>
    <h1>Col continuous solve</h1>
    <a href="/">Open tablebase explorer →</a>
  </header>
  <main>
    <section>
      <h2>Current run</h2>
      <div id="currentSummary" class="idle">Waiting for worker…</div>
      <div class="grid" style="margin-top:12px">
        <div class="stat"><label>States searched</label><div class="stat value" id="states">-</div></div>
        <div class="stat"><label>Rate</label><div class="stat value" id="rate">-</div></div>
        <div class="stat"><label>Elapsed</label><div class="stat value" id="elapsed">-</div></div>
        <div class="stat"><label>Memo entries</label><div class="stat value" id="memo">-</div></div>
      </div>
    </section>
    <section>
      <h2>Finished boards</h2>
      <table>
        <thead><tr><th>Board</th><th>Winner</th><th>States</th><th>Time</th><th>Notes</th></tr></thead>
        <tbody id="finished"></tbody>
      </table>
    </section>
    <section>
      <h2>Tablebases on disk</h2>
      <table>
        <thead><tr><th>Board</th><th>Size</th><th>Updated</th></tr></thead>
        <tbody id="tablebases"></tbody>
      </table>
    </section>
  </main>
  <script>
    function fmt(n) {
      if (n == null || n === '') return '-';
      return Number(n).toLocaleString();
    }
    function fmtRate(n) {
      if (n == null) return '-';
      return fmt(Math.round(n)) + '/s';
    }
    function fmtSec(n) {
      if (n == null) return '-';
      return Number(n).toFixed(1) + 's';
    }
    function fmtBytes(n) {
      if (!n) return '-';
      const units = ['B', 'KB', 'MB', 'GB'];
      let v = n, u = 0;
      while (v >= 1024 && u < units.length - 1) { v /= 1024; u++; }
      return v.toFixed(u ? 1 : 0) + ' ' + units[u];
    }
    async function refresh() {
      const [statusRes, tbRes] = await Promise.all([
        fetch('/api/solver/status'),
        fetch('/api/tablebases'),
      ]);
      const status = await statusRes.json();
      const tb = await tbRes.json();
      const cur = status.current;
      const summary = document.getElementById('currentSummary');
      if (status.running && cur) {
        summary.className = 'running';
        summary.textContent = `Solving ${cur.m} x ${cur.n} (total area ${status.queue?.current_total ?? '?'})`;
      } else if (status.last_finished) {
        summary.className = 'idle';
        summary.textContent = `Idle — last finished ${status.last_finished.m} x ${status.last_finished.n}`;
      } else {
        summary.className = 'idle';
        summary.textContent = status.available ? 'Idle' : 'No status file yet (worker starting?)';
      }
      document.getElementById('states').textContent = cur ? fmt(cur.states) : '-';
      document.getElementById('rate').textContent = cur ? fmtRate(cur.rate) : '-';
      document.getElementById('elapsed').textContent = cur ? fmtSec(cur.elapsed_s) : '-';
      document.getElementById('memo').textContent = cur && cur.memo != null ? fmt(cur.memo) : '-';
      const finished = document.getElementById('finished');
      finished.innerHTML = '';
      for (const row of (status.finished || []).slice().reverse()) {
        const tr = document.createElement('tr');
        const notes = row.skipped ? 'skipped' : (row.saved ? 'saved' : '');
        tr.innerHTML = `<td>${row.m} x ${row.n}</td><td>${row.winner}</td><td>${fmt(row.states)}</td><td>${fmtSec(row.seconds)}</td><td>${notes}</td>`;
        finished.appendChild(tr);
      }
      const tbody = document.getElementById('tablebases');
      tbody.innerHTML = '';
      for (const row of tb.tablebases || []) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${row.m} x ${row.n}</td><td>${fmtBytes(row.size_bytes)}</td><td>${row.updated_at || '-'}</td>`;
        tbody.appendChild(tr);
      }
    }
    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""


def list_tablebases(tablebase_dir: Path) -> List[Dict[str, Any]]:
    if not tablebase_dir.is_dir():
        return []
    rows: List[Dict[str, Any]] = []
    for path in sorted(tablebase_dir.glob("*_sym.pkl")):
        match = TABLEBASE_NAME_RE.match(path.name)
        if not match:
            continue
        stat = path.stat()
        rows.append(
            {
                "m": int(match.group(1)),
                "n": int(match.group(2)),
                "filename": path.name,
                "size_bytes": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            }
        )
    return rows


def read_solver_status(status_file: Optional[Path]) -> Dict[str, Any]:
    if status_file is None or not status_file.is_file():
        return {"available": False, "running": False, "finished": []}
    try:
        payload = json.loads(status_file.read_text(encoding="utf-8"))
        payload["available"] = True
        return payload
    except (OSError, json.JSONDecodeError):
        return {"available": False, "running": False, "finished": []}


class GuiState:
    def __init__(
        self,
        m: int,
        n: int,
        use_symmetry: bool,
        tablebase_dir: Path,
    ) -> None:
        self.solver = DfsSolver(
            m,
            n,
            use_symmetry=use_symmetry,
            tablebase=Tablebase(tablebase_dir, enabled=True),
        )
        self.board = self.solver.board
        self.p1_mask = 0
        self.p2_mask = 0
        self.turn = P1
        self.history: List[Tuple[int, int, int]] = []
        self.vs_computer = False

    def snapshot(self) -> Dict[str, Any]:
        legal_cells = set(self.board.legal_moves(self.p1_mask, self.p2_mask, self.turn))
        game_over, game_result = self.game_status()
        can_play = not game_over and (
            not self.vs_computer or self.turn == P1
        )
        return {
            "m": self.board.m,
            "n": self.board.n,
            "turn": self.turn,
            "vs_computer": self.vs_computer,
            "can_play": can_play,
            "game_over": game_over,
            "game_result": game_result,
            "tablebase_path": str(self.solver.tablebase.path_for(self.board)),
            "can_undo": bool(self.history),
            "p1_mask": self.p1_mask,
            "p2_mask": self.p2_mask,
            "cells": [self.cell_payload(cell, legal_cells) for cell in range(self.board.num_cells)],
            "current": self.position_result(self.p1_mask, self.p2_mask, self.turn),
            "legal_moves": self.sorted_legal_moves(),
        }

    def game_status(self) -> Tuple[bool, Optional[str]]:
        legal = self.board.legal_moves(self.p1_mask, self.p2_mask, self.turn)
        if legal:
            return False, None
        winner = self.other_turn(self.turn)
        return True, f"{self.turn_name(winner)} wins ({self.turn_name(self.turn)} has no legal moves)"

    def sorted_legal_moves(self) -> List[Dict[str, Any]]:
        moves = [
            self.move_payload(cell)
            for cell in self.board.legal_moves(self.p1_mask, self.p2_mask, self.turn)
        ]
        moves.sort(key=self.move_sort_key)
        return moves

    @staticmethod
    def move_sort_key(move: Dict[str, Any]) -> Tuple[int, int]:
        if not move["known"]:
            rank = 2
        elif move["winning_for_current"]:
            rank = 0
        else:
            rank = 1
        return (rank, move["cell"])

    def cell_payload(self, cell: int, legal_cells: set[int]) -> Dict[str, Any]:
        bit = 1 << cell
        occupant = None
        if self.p1_mask & bit:
            occupant = "P1"
        elif self.p2_mask & bit:
            occupant = "P2"
        blocked = occupant is None and cell not in legal_cells
        return {
            "cell": cell,
            "row": cell // self.board.n + 1,
            "col": cell % self.board.n + 1,
            "occupant": occupant,
            "legal": cell in legal_cells,
            "blocked": blocked,
        }

    def move_payload(self, cell: int) -> Dict[str, Any]:
        next_p1, next_p2, next_turn = self.child_after(cell)
        result = self.position_result(next_p1, next_p2, next_turn)
        known = result["known"]
        opponent_wins = result["side_to_move_wins"] if known else None
        return {
            "cell": cell,
            "row": cell // self.board.n + 1,
            "col": cell % self.board.n + 1,
            "known": known,
            "source": result["source"],
            "child_key": result["key"],
            "winning_for_current": None if opponent_wins is None else not opponent_wins,
            "winner": result["winner"],
            "result": result["result"],
        }

    def position_result(self, p1_mask: int, p2_mask: int, turn: int) -> Dict[str, Any]:
        key = self.board.shadow_key_from_stones(p1_mask, p2_mask, turn)
        if key not in self.solver.memo:
            return {
                "known": False,
                "source": None,
                "key": self.format_key(key),
                "side_to_move_wins": None,
                "side_to_move_result": None,
                "winner": None,
                "result": None,
            }

        side_to_move_wins = self.solver.memo[key]
        winner = turn if side_to_move_wins else self.other_turn(turn)
        winner_name = self.turn_name(winner)
        source = "tablebase" if key in self.solver.tablebase_keys else "memory"
        return {
            "known": True,
            "source": source,
            "key": self.format_key(key),
            "side_to_move_wins": side_to_move_wins,
            "side_to_move_result": "winning" if side_to_move_wins else "losing",
            "winner": winner_name,
            "result": f"{winner_name} win",
        }

    def play(self, row: int, col: int, *, allow_cpu: bool = False) -> None:
        if self.vs_computer and self.turn != P1 and not allow_cpu:
            raise ValueError("wait for the CPU to move")
        cell = self.parse_cell(row, col)
        legal = set(self.board.legal_moves(self.p1_mask, self.p2_mask, self.turn))
        if cell not in legal:
            raise ValueError("illegal move")

        self.history.append((self.p1_mask, self.p2_mask, self.turn))
        bit = 1 << cell
        if self.turn == P1:
            self.p1_mask |= bit
            self.turn = P2
        else:
            self.p2_mask |= bit
            self.turn = P1

    def play_with_computer(self, row: int, col: int) -> Dict[str, Any]:
        self.play(row, col)
        computer_move: Optional[Dict[str, int]] = None
        if self.vs_computer and not self.game_status()[0]:
            cell = self.pick_best_move()
            if cell is not None:
                computer_move = {
                    "cell": cell,
                    "row": cell // self.board.n + 1,
                    "col": cell % self.board.n + 1,
                }
                self.play(computer_move["row"], computer_move["col"], allow_cpu=True)
        return {"state": self.snapshot(), "computer_move": computer_move}

    def set_vs_computer(self, enabled: bool) -> None:
        if enabled and self.turn != P1:
            raise ValueError("enable vs CPU only when you (P1) are to move")
        if enabled and self.game_status()[0]:
            raise ValueError("cannot enable vs CPU on a finished game")
        self.vs_computer = enabled

    def pick_best_move(self) -> Optional[int]:
        moves = self.sorted_legal_moves()
        if not moves:
            return None

        fallback = moves[0]["cell"]
        for move in moves:
            if move["known"]:
                if move["winning_for_current"]:
                    return move["cell"]
                continue
            next_p1, next_p2, next_turn = self.child_after(move["cell"])
            if not self.solver.is_winning(next_p1, next_p2, next_turn):
                return move["cell"]

        for move in moves:
            if move["known"] and not move["winning_for_current"]:
                return move["cell"]
        return fallback

    def undo(self) -> None:
        if self.history:
            self.p1_mask, self.p2_mask, self.turn = self.history.pop()

    def reset(self) -> None:
        self.p1_mask = 0
        self.p2_mask = 0
        self.turn = P1
        self.history.clear()

    def response_state(self) -> Dict[str, Any]:
        return {"state": self.snapshot()}

    def solve_current(self) -> Dict[str, Any]:
        before = self.solver.stats.states_searched
        started_at = time.perf_counter()
        wins = self.solver.is_winning(self.p1_mask, self.p2_mask, self.turn)
        for cell in self.board.legal_moves(self.p1_mask, self.p2_mask, self.turn):
            self.solver.is_winning(*self.child_after(cell))
        elapsed = time.perf_counter() - started_at
        if self.solver.stats.states_searched > before:
            self.solver.tablebase.save(self.board, self.solver.memo)
        winner = self.turn if wins else self.other_turn(self.turn)
        return {
            "result": f"{self.turn_name(winner)} win",
            "side_to_move": "winning" if wins else "losing",
            "new_states": self.solver.stats.states_searched - before,
            "elapsed": elapsed,
            "state": self.snapshot(),
        }

    def child_after(self, cell: int) -> Tuple[int, int, int]:
        bit = 1 << cell
        if self.turn == P1:
            return (self.p1_mask | bit, self.p2_mask, P2)
        return (self.p1_mask, self.p2_mask | bit, P1)

    def parse_cell(self, row: int, col: int) -> int:
        if not (1 <= row <= self.board.m and 1 <= col <= self.board.n):
            raise ValueError("cell outside board")
        return (row - 1) * self.board.n + (col - 1)

    def format_key(self, key: int) -> str:
        p1_mask, p2_mask, turn = self.board.unpack_key(key)
        return f"({p1_mask}, {p2_mask}, {turn})"

    @staticmethod
    def turn_name(turn: int) -> str:
        return "P1" if turn == P1 else "P2"

    @staticmethod
    def other_turn(turn: int) -> int:
        return P2 if turn == P1 else P1


class GuiHandler(BaseHTTPRequestHandler):
    app: GuiState
    status_file: Optional[Path] = None
    tablebase_dir: Path = Path("data/tablebases")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_html(HTML)
        elif path == "/dashboard":
            self.send_html(DASHBOARD_HTML)
        elif path == "/api/state":
            self.send_json(self.app.snapshot())
        elif path == "/api/solver/status":
            self.send_json(read_solver_status(self.status_file))
        elif path == "/api/tablebases":
            self.send_json({"tablebases": list_tablebases(self.tablebase_dir)})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/play":
                self.send_json(
                    self.app.play_with_computer(int(payload["row"]), int(payload["col"]))
                )
            elif path == "/api/vs-computer":
                self.app.set_vs_computer(bool(payload.get("enabled", False)))
                self.send_json(self.app.response_state())
            elif path == "/api/undo":
                self.app.undo()
                self.send_json(self.app.response_state())
            elif path == "/api/reset":
                self.app.reset()
                self.send_json(self.app.response_state())
            elif path == "/api/solve":
                self.send_json(self.app.solve_current())
            else:
                self.send_error(404)
        except (KeyError, TypeError, ValueError) as exc:
            self.send_json({"error": str(exc)}, status=400)

    def read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        data = self.rfile.read(length)
        return json.loads(data.decode("utf-8"))

    def send_html(self, html: str) -> None:
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Col tablebase browser GUI.")
    parser.add_argument("--m", type=positive_int, required=True, help="number of rows")
    parser.add_argument("--n", type=positive_int, required=True, help="number of columns")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    parser.add_argument(
        "--no-symmetry",
        action="store_true",
        help="disable geometric symmetry canonicalization",
    )
    parser.add_argument(
        "--tablebase-dir",
        type=Path,
        default=Path("data/tablebases"),
        help="directory for persistent tablebase files",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help="JSON status file written by continuous-solve (for /dashboard)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    status_file = args.status_file
    if status_file is None and os.environ.get("STATUS_FILE"):
        status_file = Path(os.environ["STATUS_FILE"])

    print("Loading tablebase...", flush=True)
    GuiHandler.app = GuiState(
        args.m,
        args.n,
        use_symmetry=not args.no_symmetry,
        tablebase_dir=args.tablebase_dir,
    )
    GuiHandler.status_file = status_file
    GuiHandler.tablebase_dir = args.tablebase_dir
    entries = len(GuiHandler.app.solver.memo)
    print(f"Tablebase ready ({entries:,} entries).", flush=True)
    server = ThreadingHTTPServer((args.host, args.port), GuiHandler)
    url = f"http://{args.host}:{server.server_port}"
    print(f"Col tablebase GUI: {url}", flush=True)
    print(f"Solver dashboard: {url}/dashboard", flush=True)
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
