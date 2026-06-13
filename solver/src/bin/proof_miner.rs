//! Mine solved tablebases for tinted-component patterns.
//!
//! This is an analysis tool, not part of the solver. It interprets shadow-key
//! tablebase entries as generalized Linear Col tint states:
//!   o = legal for both players, b = P1-only, w = P2-only, x = dead/absent.

#[path = "../endgame.rs"]
mod endgame;

use flate2::read::ZlibDecoder;
use serde::Deserialize;
use std::collections::{HashMap, HashSet};
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

const TABLEBASE_VERSION: i64 = 4;

#[derive(Deserialize)]
struct Payload {
    version: i64,
    m: i64,
    n: i64,
    use_symmetry: bool,
    count: i64,
    #[serde(with = "serde_bytes")]
    deltas: Vec<u8>,
    #[serde(with = "serde_bytes")]
    bitmap: Vec<u8>,
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
enum Phase {
    Opening,
    Midgame,
    Endgame,
}

impl Phase {
    fn from_open_cells(open_cells: u32, num_cells: usize) -> Phase {
        let pct = open_cells as f64 / num_cells as f64;
        if pct > 0.66 {
            Phase::Opening
        } else if pct > 0.33 {
            Phase::Midgame
        } else {
            Phase::Endgame
        }
    }

    fn label(self) -> &'static str {
        match self {
            Phase::Opening => "opening",
            Phase::Midgame => "midgame",
            Phase::Endgame => "endgame",
        }
    }
}

#[derive(Default)]
struct PhaseCounts {
    opening: u64,
    midgame: u64,
    endgame: u64,
}

impl PhaseCounts {
    fn add(&mut self, phase: Phase) {
        match phase {
            Phase::Opening => self.opening += 1,
            Phase::Midgame => self.midgame += 1,
            Phase::Endgame => self.endgame += 1,
        }
    }

    fn total(&self) -> u64 {
        self.opening + self.midgame + self.endgame
    }
}

#[derive(Default)]
struct ComponentStats {
    occurrences: u64,
    stm_wins: u64,
    single_occurrences: u64,
    single_stm_wins: u64,
    total_cells: u64,
    o_cells: u64,
    b_cells: u64,
    w_cells: u64,
    phase: PhaseCounts,
    boards: HashMap<String, u64>,
    values: HashMap<String, u64>,
    value_observations: u64,
    too_large_for_value: u64,
    sample: String,
}

impl ComponentStats {
    fn record(
        &mut self,
        board: &str,
        phase: Phase,
        side_to_move_wins: bool,
        single_component_position: bool,
        counts: CellCounts,
        value_text: Option<&str>,
        sample: &str,
    ) {
        self.occurrences += 1;
        if side_to_move_wins {
            self.stm_wins += 1;
        }
        if single_component_position {
            self.single_occurrences += 1;
            if side_to_move_wins {
                self.single_stm_wins += 1;
            }
        }
        self.total_cells += counts.total as u64;
        self.o_cells += counts.o as u64;
        self.b_cells += counts.b as u64;
        self.w_cells += counts.w as u64;
        self.phase.add(phase);
        *self.boards.entry(board.to_string()).or_insert(0) += 1;
        if let Some(value_text) = value_text {
            self.value_observations += 1;
            *self.values.entry(value_text.to_string()).or_insert(0) += 1;
        } else {
            self.too_large_for_value += 1;
        }
        if self.sample.is_empty() {
            self.sample = sample.to_string();
        }
    }
}

#[derive(Default)]
struct BoardSummary {
    board: String,
    entries_total: usize,
    entries_scanned: u64,
    stm_wins: u64,
    components: u64,
    phase: PhaseCounts,
}

#[derive(Clone, Copy)]
struct CellCounts {
    total: usize,
    o: usize,
    b: usize,
    w: usize,
}

struct BoardGeom {
    m: usize,
    n: usize,
    num_cells: usize,
    all_cells_mask: u128,
    adjacency: Vec<u128>,
}

impl BoardGeom {
    fn new(m: usize, n: usize) -> BoardGeom {
        let num_cells = m * n;
        assert!(num_cells <= 63, "proof miner currently expects <=63 cells");
        let all_cells_mask = (1u128 << num_cells) - 1;
        let mut adjacency = vec![0u128; num_cells];
        for row in 0..m {
            for col in 0..n {
                let cell = row * n + col;
                let mut mask = 0u128;
                if row > 0 {
                    mask |= 1u128 << (cell - n);
                }
                if row + 1 < m {
                    mask |= 1u128 << (cell + n);
                }
                if col > 0 {
                    mask |= 1u128 << (cell - 1);
                }
                if col + 1 < n {
                    mask |= 1u128 << (cell + 1);
                }
                adjacency[cell] = mask;
            }
        }
        BoardGeom {
            m,
            n,
            num_cells,
            all_cells_mask,
            adjacency,
        }
    }

    fn unpack_key(&self, key: u128) -> (u128, u128, u8) {
        let turn = (key & 1) as u8;
        let p2 = (key >> 1) & self.all_cells_mask;
        let p1 = (key >> (self.num_cells + 1)) & self.all_cells_mask;
        (p1, p2, turn)
    }

    fn components(&self, p1_legal: u128, p2_legal: u128) -> Vec<u128> {
        let combined = p1_legal | p2_legal;
        let mut remaining = combined;
        let mut components = Vec::new();
        while remaining != 0 {
            let seed = remaining & (!remaining + 1);
            remaining ^= seed;
            let mut comp = seed;
            let mut stack = vec![seed];
            while let Some(bit) = stack.pop() {
                let cell = bit.trailing_zeros() as usize;
                let mut neighbors = self.adjacency[cell] & combined & !comp;
                while neighbors != 0 {
                    let next = neighbors & (!neighbors + 1);
                    neighbors ^= next;
                    comp |= next;
                    remaining &= !next;
                    stack.push(next);
                }
            }
            components.push(comp);
        }
        components
    }
}

struct TablebaseEntries {
    m: usize,
    n: usize,
    count: usize,
    deltas: Vec<u8>,
    bitmap: Vec<u8>,
}

impl TablebaseEntries {
    fn load(path: &Path) -> Result<TablebaseEntries, String> {
        let bytes = fs::read(path).map_err(|err| err.to_string())?;
        let payload: Payload =
            serde_pickle::from_slice(&bytes, Default::default()).map_err(|err| err.to_string())?;
        if payload.version != TABLEBASE_VERSION {
            return Err(format!(
                "unsupported tablebase version {} in {}",
                payload.version,
                path.display()
            ));
        }
        if !payload.use_symmetry {
            return Err(format!("{} is not symmetry-canonical", path.display()));
        }
        Ok(TablebaseEntries {
            m: payload.m as usize,
            n: payload.n as usize,
            count: payload.count as usize,
            deltas: zlib_decompress(&payload.deltas)?,
            bitmap: zlib_decompress(&payload.bitmap)?,
        })
    }

    fn iter(&self) -> EntryIter<'_> {
        EntryIter {
            entries: self,
            index: 0,
            key: 0,
            delta_pos: 0,
        }
    }
}

struct EntryIter<'a> {
    entries: &'a TablebaseEntries,
    index: usize,
    key: u128,
    delta_pos: usize,
}

impl Iterator for EntryIter<'_> {
    type Item = Result<(usize, u128, bool), String>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.index >= self.entries.count {
            return None;
        }
        let delta = match read_varint(&self.entries.deltas, &mut self.delta_pos) {
            Ok(delta) => delta,
            Err(err) => return Some(Err(err)),
        };
        self.key = match self.key.checked_add(delta) {
            Some(key) => key,
            None => return Some(Err("tablebase key overflow".to_string())),
        };
        let win = self.entries.bitmap[self.index >> 3] & (1 << (self.index & 7)) != 0;
        let index = self.index;
        self.index += 1;
        Some(Ok((index, self.key, win)))
    }
}

fn zlib_decompress(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut decoder = ZlibDecoder::new(data);
    let mut out = Vec::new();
    decoder
        .read_to_end(&mut out)
        .map_err(|err| err.to_string())?;
    Ok(out)
}

fn read_varint(deltas: &[u8], pos: &mut usize) -> Result<u128, String> {
    let mut delta = 0u128;
    let mut shift = 0u32;
    loop {
        if *pos >= deltas.len() {
            return Err("truncated varint in tablebase".into());
        }
        let byte = deltas[*pos];
        *pos += 1;
        delta |= ((byte & 0x7F) as u128) << shift;
        if byte & 0x80 == 0 {
            return Ok(delta);
        }
        shift += 7;
        if shift > 128 {
            return Err("varint too long in tablebase".into());
        }
    }
}

fn bit_cells(mut mask: u128) -> Vec<usize> {
    let mut cells = Vec::new();
    while mask != 0 {
        let bit = mask & (!mask + 1);
        cells.push(bit.trailing_zeros() as usize);
        mask ^= bit;
    }
    cells
}

fn cell_char(p1_legal: u128, p2_legal: u128, bit: u128) -> char {
    match (p1_legal & bit != 0, p2_legal & bit != 0) {
        (true, true) => 'o',
        (true, false) => 'b',
        (false, true) => 'w',
        (false, false) => '.',
    }
}

fn component_signature(
    board: &BoardGeom,
    p1_legal: u128,
    p2_legal: u128,
    comp: u128,
) -> (String, String, CellCounts) {
    let cells = bit_cells(comp);
    let mut min_r = usize::MAX;
    let mut min_c = usize::MAX;
    let mut max_r = 0usize;
    let mut max_c = 0usize;
    let mut counts = CellCounts {
        total: cells.len(),
        o: 0,
        b: 0,
        w: 0,
    };
    for &cell in &cells {
        let row = cell / board.n;
        let col = cell % board.n;
        min_r = min_r.min(row);
        min_c = min_c.min(col);
        max_r = max_r.max(row);
        max_c = max_c.max(col);
        match cell_char(p1_legal, p2_legal, 1u128 << cell) {
            'o' => counts.o += 1,
            'b' => counts.b += 1,
            'w' => counts.w += 1,
            _ => {}
        }
    }
    let h = max_r - min_r + 1;
    let w = max_c - min_c + 1;
    let mut rel = Vec::with_capacity(cells.len());
    for cell in cells {
        let row = cell / board.n - min_r;
        let col = cell % board.n - min_c;
        let ch = cell_char(p1_legal, p2_legal, 1u128 << cell);
        rel.push((row, col, ch));
    }
    (
        canonical_component(&rel, h, w, true),
        canonical_component(&rel, h, w, false),
        counts,
    )
}

fn canonical_component(cells: &[(usize, usize, char)], h: usize, w: usize, color_swap: bool) -> String {
    let mut variants = Vec::new();
    for swap in [false, true] {
        if swap && !color_swap {
            continue;
        }
        variants.push(render_transform(cells, h, w, swap, |r, c, h, w| (r, c, h, w)));
        variants.push(render_transform(cells, h, w, swap, |r, c, h, w| (h - 1 - r, c, h, w)));
        variants.push(render_transform(cells, h, w, swap, |r, c, h, w| (r, w - 1 - c, h, w)));
        variants.push(render_transform(cells, h, w, swap, |r, c, h, w| {
            (h - 1 - r, w - 1 - c, h, w)
        }));
        variants.push(render_transform(cells, h, w, swap, |r, c, h, w| (c, r, w, h)));
        variants.push(render_transform(cells, h, w, swap, |r, c, h, w| {
            (c, h - 1 - r, w, h)
        }));
        variants.push(render_transform(cells, h, w, swap, |r, c, h, w| {
            (w - 1 - c, r, w, h)
        }));
        variants.push(render_transform(cells, h, w, swap, |r, c, h, w| {
            (w - 1 - c, h - 1 - r, w, h)
        }));
    }
    variants.sort_unstable();
    variants.into_iter().next().unwrap()
}

fn render_transform<F>(
    cells: &[(usize, usize, char)],
    h: usize,
    w: usize,
    swap: bool,
    transform: F,
) -> String
where
    F: Fn(usize, usize, usize, usize) -> (usize, usize, usize, usize),
{
    let (_, _, out_h, out_w) = transform(0, 0, h, w);
    let mut grid = vec![vec!['.'; out_w]; out_h];
    for &(r, c, ch) in cells {
        let (rr, cc, _, _) = transform(r, c, h, w);
        grid[rr][cc] = if swap { swap_color(ch) } else { ch };
    }
    let rows: Vec<String> = grid
        .into_iter()
        .map(|row| row.into_iter().collect::<String>())
        .collect();
    format!("{out_h}x{out_w}:{}", rows.join("/"))
}

fn swap_color(ch: char) -> char {
    match ch {
        'b' => 'w',
        'w' => 'b',
        other => other,
    }
}

fn signature_body(signature: &str) -> &str {
    signature.split_once(':').map(|(_, body)| body).unwrap_or(signature)
}

fn parse_board_arg(arg: &str) -> Result<(usize, usize), String> {
    let (m, n) = arg
        .split_once('x')
        .ok_or_else(|| format!("bad board '{arg}', expected MxN"))?;
    let m = m.parse::<usize>().map_err(|err| err.to_string())?;
    let n = n.parse::<usize>().map_err(|err| err.to_string())?;
    Ok(if m <= n { (m, n) } else { (n, m) })
}

fn parse_filename(path: &Path) -> Option<(usize, usize)> {
    let name = path.file_name()?.to_str()?;
    let stem = name.strip_suffix("_sym.pkl")?;
    parse_board_arg(stem).ok()
}

struct Config {
    tablebase_dir: PathBuf,
    out: PathBuf,
    boards: Option<HashSet<(usize, usize)>>,
    sample_stride: usize,
    top: usize,
}

fn parse_args() -> Result<Config, String> {
    let mut tablebase_dir = PathBuf::from("data/tablebases");
    let mut out = PathBuf::from("reports/proof-miner.md");
    let mut boards = None;
    let mut sample_stride = 1usize;
    let mut top = 20usize;
    let args: Vec<String> = std::env::args().collect();
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--tablebase-dir" => {
                tablebase_dir = PathBuf::from(&args[i + 1]);
                i += 2;
            }
            "--out" => {
                out = PathBuf::from(&args[i + 1]);
                i += 2;
            }
            "--boards" => {
                let mut set = HashSet::new();
                for part in args[i + 1].split(',') {
                    set.insert(parse_board_arg(part)?);
                }
                boards = Some(set);
                i += 2;
            }
            "--sample-stride" => {
                sample_stride = args[i + 1]
                    .parse::<usize>()
                    .map_err(|err| format!("bad --sample-stride: {err}"))?;
                sample_stride = sample_stride.max(1);
                i += 2;
            }
            "--top" => {
                top = args[i + 1]
                    .parse::<usize>()
                    .map_err(|err| format!("bad --top: {err}"))?;
                i += 2;
            }
            other => return Err(format!("unknown arg {other}")),
        }
    }
    Ok(Config {
        tablebase_dir,
        out,
        boards,
        sample_stride,
        top,
    })
}

fn discover_tablebases(config: &Config) -> Result<Vec<PathBuf>, String> {
    let mut paths = Vec::new();
    for entry in fs::read_dir(&config.tablebase_dir).map_err(|err| err.to_string())? {
        let path = entry.map_err(|err| err.to_string())?.path();
        let Some((m, n)) = parse_filename(&path) else {
            continue;
        };
        if m == 1 || m % 2 == 0 || n % 2 == 0 {
            continue;
        }
        if let Some(boards) = &config.boards {
            if !boards.contains(&(m, n)) {
                continue;
            }
        }
        paths.push(path);
    }
    paths.sort_by_key(|path| {
        let (m, n) = parse_filename(path).unwrap();
        (m * n, m, n)
    });
    Ok(paths)
}

fn scan_tablebase(
    path: &Path,
    config: &Config,
    components: &mut HashMap<String, ComponentStats>,
    value_cache: &mut HashMap<String, String>,
) -> Result<BoardSummary, String> {
    let entries = TablebaseEntries::load(path)?;
    let board = BoardGeom::new(entries.m, entries.n);
    let board_label = format!("{}x{}", entries.m, entries.n);
    let mut summary = BoardSummary {
        board: board_label.clone(),
        entries_total: entries.count,
        ..BoardSummary::default()
    };

    for item in entries.iter() {
        let (index, key, side_to_move_wins) = item?;
        if index % config.sample_stride != 0 {
            continue;
        }
        let (p1_legal, p2_legal, _turn) = board.unpack_key(key);
        let open_cells = (p1_legal | p2_legal).count_ones();
        let phase = Phase::from_open_cells(open_cells, board.num_cells);
        summary.entries_scanned += 1;
        if side_to_move_wins {
            summary.stm_wins += 1;
        }
        summary.phase.add(phase);

        let comps = board.components(p1_legal, p2_legal);
        let single_component_position = comps.len() == 1;
        for comp in comps {
            let (signature, exact_signature, counts) =
                component_signature(&board, p1_legal, p2_legal, comp);
            let comp_p1 = p1_legal & comp;
            let comp_p2 = p2_legal & comp;
            let value_text = if counts.total <= 12 {
                if !value_cache.contains_key(&exact_signature) {
                    if let Some(value) =
                        endgame::component_value_text(board.n, comp_p1 as u64, comp_p2 as u64)
                    {
                        value_cache.insert(exact_signature.clone(), value);
                    }
                }
                value_cache.get(&exact_signature).map(String::as_str)
            } else {
                None
            };
            components
                .entry(signature.clone())
                .or_default()
                .record(
                    &board_label,
                    phase,
                    side_to_move_wins,
                    single_component_position,
                    counts,
                    value_text.as_deref(),
                    signature_body(&signature),
                );
            summary.components += 1;
        }
    }

    Ok(summary)
}

fn percent(part: u64, whole: u64) -> f64 {
    if whole == 0 {
        0.0
    } else {
        100.0 * part as f64 / whole as f64
    }
}

fn report_markdown(
    config: &Config,
    summaries: &[BoardSummary],
    components: &HashMap<String, ComponentStats>,
) -> String {
    let mut out = String::new();
    out.push_str("# Col Tablebase Proof-Mining Report\n\n");
    out.push_str("This report scans shadow-key tablebases as generalized tinted positions: `o` legal for both players, `b` P1-only, `w` P2-only, and `.` absent/dead inside a component bounding box.\n\n");
    out.push_str(&format!(
        "- Tablebase directory: `{}`\n- Sample stride: `{}` (1 means full scan)\n- Boards scanned: `{}`\n- Distinct component families: `{}`\n\n",
        config.tablebase_dir.display(),
        config.sample_stride,
        summaries.len(),
        components.len()
    ));

    out.push_str("## Board Summary\n\n");
    out.push_str("| Board | Entries | Scanned | STM win % | Components | Avg comps/position | Opening % | Midgame % | Endgame % |\n");
    out.push_str("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n");
    for summary in summaries {
        let scanned = summary.entries_scanned;
        out.push_str(&format!(
            "| {} | {} | {} | {:.1}% | {} | {:.2} | {:.1}% | {:.1}% | {:.1}% |\n",
            summary.board,
            summary.entries_total,
            scanned,
            percent(summary.stm_wins, scanned),
            summary.components,
            summary.components as f64 / scanned.max(1) as f64,
            percent(summary.phase.opening, scanned),
            percent(summary.phase.midgame, scanned),
            percent(summary.phase.endgame, scanned),
        ));
    }

    let mut top_components: Vec<(&String, &ComponentStats)> = components.iter().collect();
    top_components.sort_by_key(|(_, stats)| std::cmp::Reverse(stats.occurrences));
    out.push_str("\n## Most Frequent Tinted Component Families\n\n");
    out.push_str("These are component families after translation/symmetry/color-swap canonicalization. `STM win %` is the outcome of the whole tablebase position, so treat it as correlation, not a component value proof.\n\n");
    for (rank, (signature, stats)) in top_components.iter().take(config.top).enumerate() {
        out.push_str(&format!(
            "### {}. `{}`\n\n",
            rank + 1,
            signature.split_once(':').map(|(head, _)| head).unwrap_or(signature)
        ));
        out.push_str(&format!(
            "- Occurrences: `{}`\n- STM win %: `{:.1}%`\n- Local values (<=12 cells): {}\n- Avg cells: `{:.1}` (`o` {:.1}%, `b` {:.1}%, `w` {:.1}%)\n- Phase mix: opening {:.1}%, midgame {:.1}%, endgame {:.1}%\n- Top boards: {}\n\n",
            stats.occurrences,
            percent(stats.stm_wins, stats.occurrences),
            top_values(&stats.values, stats.value_observations, 4),
            stats.total_cells as f64 / stats.occurrences.max(1) as f64,
            percent(stats.o_cells, stats.total_cells),
            percent(stats.b_cells, stats.total_cells),
            percent(stats.w_cells, stats.total_cells),
            percent(stats.phase.opening, stats.phase.total()),
            percent(stats.phase.midgame, stats.phase.total()),
            percent(stats.phase.endgame, stats.phase.total()),
            top_boards(&stats.boards, 5),
        ));
        out.push_str("```text\n");
        out.push_str(&stats.sample.replace('/', "\n"));
        out.push_str("\n```\n\n");
    }

    let mut exact_zero: Vec<(&String, &ComponentStats)> = components
        .iter()
        .filter(|(_, stats)| {
            stats.value_observations >= 100
                && stats.values.len() == 1
                && stats.values.get("0").copied().unwrap_or(0) == stats.value_observations
        })
        .collect();
    exact_zero.sort_by_key(|(_, stats)| std::cmp::Reverse(stats.value_observations));
    out.push_str("## Exact Local Zero Component Candidates\n\n");
    out.push_str("These component families were locally evaluable by the CGT engine and every sampled observation had exact value `0`. Because component signatures are canonicalized under color swap, `0` is the safest value to mine this way.\n\n");
    out.push_str("| Signature | Value observations | Occurrences | Phase mix | Sample |\n");
    out.push_str("|---|---:|---:|---|---|\n");
    for (signature, stats) in exact_zero.into_iter().take(15) {
        let head = signature.split_once(':').map(|(head, _)| head).unwrap_or(signature);
        out.push_str(&format!(
            "| `{}` | {} | {} | O {:.0}% / M {:.0}% / E {:.0}% | `{}` |\n",
            head,
            stats.value_observations,
            stats.occurrences,
            percent(stats.phase.opening, stats.phase.total()),
            percent(stats.phase.midgame, stats.phase.total()),
            percent(stats.phase.endgame, stats.phase.total()),
            stats.sample,
        ));
    }

    let mut losing_correlated: Vec<(&String, &ComponentStats)> = components
        .iter()
        .filter(|(_, stats)| stats.occurrences >= 1000)
        .collect();
    losing_correlated.sort_by(|(_, a), (_, b)| {
        let a_loss = (a.occurrences - a.stm_wins) as f64 / a.occurrences as f64;
        let b_loss = (b.occurrences - b.stm_wins) as f64 / b.occurrences as f64;
        b_loss
            .partial_cmp(&a_loss)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| b.occurrences.cmp(&a.occurrences))
    });
    out.push_str("## Candidate Neutral / Defensive Components\n\n");
    out.push_str("This section uses only positions with exactly one legal component, so the win/loss observation belongs to that component instead of a sum of components. It is still win/loss, not a full CGT value.\n\n");
    let mut single_losing: Vec<(&String, &ComponentStats)> = components
        .iter()
        .filter(|(_, stats)| stats.single_occurrences >= 5)
        .collect();
    single_losing.sort_by(|(_, a), (_, b)| {
        let a_loss = (a.single_occurrences - a.single_stm_wins) as f64 / a.single_occurrences as f64;
        let b_loss = (b.single_occurrences - b.single_stm_wins) as f64 / b.single_occurrences as f64;
        b_loss
            .partial_cmp(&a_loss)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| b.single_occurrences.cmp(&a.single_occurrences))
    });
    out.push_str("| Signature | Single-component observations | STM loss % | All occurrences | Sample |\n");
    out.push_str("|---|---:|---:|---|---|\n");
    for (signature, stats) in single_losing.into_iter().take(12) {
        let head = signature.split_once(':').map(|(head, _)| head).unwrap_or(signature);
        out.push_str(&format!(
            "| `{}` | {} | {:.1}% | {} | `{}` |\n",
            head,
            stats.single_occurrences,
            percent(
                stats.single_occurrences - stats.single_stm_wins,
                stats.single_occurrences
            ),
            stats.occurrences,
            stats.sample,
        ));
    }

    out.push_str("\n## Whole-Position Correlation Check\n\n");
    out.push_str("For comparison, these components appear often in losing whole positions, but those positions can contain multiple components.\n\n");
    out.push_str("| Signature | Occurrences | STM loss % | Phase mix | Sample |\n");
    out.push_str("|---|---:|---:|---|---|\n");
    for (signature, stats) in losing_correlated.into_iter().take(8) {
        let head = signature.split_once(':').map(|(head, _)| head).unwrap_or(signature);
        out.push_str(&format!(
            "| `{}` | {} | {:.1}% | O {:.0}% / M {:.0}% / E {:.0}% | `{}` |\n",
            head,
            stats.occurrences,
            percent(stats.occurrences - stats.stm_wins, stats.occurrences),
            percent(stats.phase.opening, stats.phase.total()),
            percent(stats.phase.midgame, stats.phase.total()),
            percent(stats.phase.endgame, stats.phase.total()),
            stats.sample,
        ));
    }

    out.push_str("\n## Initial Interpretation\n\n");
    out.push_str("- Repeated small tinted components are the likely analogue of the Linear Col boundary classes (`b...o`, `b...b`, `b...w`).\n");
    out.push_str("- Families with heavy midgame frequency are the best candidates for explaining solver behavior and move-ordering crossovers.\n");
    out.push_str("- The next step is to validate top families by isolating component values, not just correlating them with whole-position outcomes.\n");
    out
}

fn top_boards(boards: &HashMap<String, u64>, limit: usize) -> String {
    let mut pairs: Vec<(&String, &u64)> = boards.iter().collect();
    pairs.sort_by_key(|(_, count)| std::cmp::Reverse(**count));
    pairs
        .into_iter()
        .take(limit)
        .map(|(board, count)| format!("{board} ({count})"))
        .collect::<Vec<_>>()
        .join(", ")
}

fn top_values(values: &HashMap<String, u64>, total: u64, limit: usize) -> String {
    if total == 0 {
        return "none".to_string();
    }
    let mut pairs: Vec<(&String, &u64)> = values.iter().collect();
    pairs.sort_by_key(|(_, count)| std::cmp::Reverse(**count));
    pairs
        .into_iter()
        .take(limit)
        .map(|(value, count)| format!("{value} ({:.0}%)", percent(*count, total)))
        .collect::<Vec<_>>()
        .join(", ")
}

fn main() {
    if let Err(err) = run() {
        eprintln!("error: {err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let config = parse_args()?;
    let paths = discover_tablebases(&config)?;
    if paths.is_empty() {
        return Err("no matching odd m>1 tablebases found".to_string());
    }
    let mut components: HashMap<String, ComponentStats> = HashMap::new();
    let mut value_cache: HashMap<String, String> = HashMap::new();
    let mut summaries = Vec::new();
    for path in paths {
        eprintln!("scanning {}", path.display());
        summaries.push(scan_tablebase(
            &path,
            &config,
            &mut components,
            &mut value_cache,
        )?);
    }
    if let Some(parent) = config.out.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    let report = report_markdown(&config, &summaries, &components);
    fs::write(&config.out, report).map_err(|err| err.to_string())?;
    println!("wrote {}", config.out.display());
    Ok(())
}
