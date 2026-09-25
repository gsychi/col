//! One-sided strategy certificates. Outcomes here are bounds, never CGT values.
use crate::Board;
use flate2::read::GzDecoder;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

pub type Columns = Vec<[u8; 2]>;
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TileDoc {
    pub height: usize,
    pub width: usize,
    pub root: [u64; 2],
    pub nodes: Vec<(u64, u64, Vec<usize>)>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Tile {
    pub id: String,
    pub source_sha256: String,
    pub doc: TileDoc,
}
#[derive(Deserialize)]
struct Manifest {
    format: String,
    certificates: Vec<Metadata>,
}
#[derive(Deserialize)]
struct Metadata {
    file: String,
    sha256: String,
    height: usize,
    width: usize,
    root: [u64; 2],
    nodes: usize,
    edges: usize,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Placement {
    pub start_column: usize,
    pub tile: String,
    pub row_flip: bool,
    pub column_flip: bool,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Witness {
    pub blocks: Vec<Placement>,
}
#[derive(Clone)]
struct Variant {
    tile: usize,
    root: [u64; 2],
    left: u8,
    right: u8,
    rf: bool,
    cf: bool,
}
#[derive(Default)]
pub struct Counters {
    queries: AtomicU64,
    matches: AtomicU64,
    covers: AtomicU64,
    cutoffs: AtomicU64,
    nanos: AtomicU64,
}
#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct Metrics {
    pub queries: u64,
    pub matching_tiles: u64,
    pub successful_covers: u64,
    pub dfs_cutoffs: u64,
    pub query_seconds: f64,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Opening {
    pub opening: usize,
    pub response: usize,
    pub witness: Witness,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Leaf {
    pub columns: Columns,
    pub turn: u8,
    pub response: Option<usize>,
    pub witness: Witness,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Report {
    pub format: String,
    pub height: usize,
    pub width: usize,
    pub turn: u8,
    /// Absolute P1/P2 permissions; each column contains two row masks.
    pub columns: Columns,
    /// Side-to-move outcome: loss, win, or unknown.
    pub outcome: String,
    pub witness: Option<Witness>,
    pub response: Option<usize>,
    pub openings: Vec<Opening>,
    pub uncovered: Vec<usize>,
    pub library: Vec<Tile>,
    pub metrics: Metrics,
    #[serde(default)]
    pub cutoffs: Vec<Leaf>,
}
pub struct Evaluator {
    pub tiles: Vec<Tile>,
    variants: Vec<Variant>,
    pub counters: Counters,
}

pub fn default_library() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../proofs/3x15")
}

/// Validate every branch using the production engine's exact move updates.
pub fn check_tile(doc: &TileDoc) -> Result<usize, String> {
    let h = doc.height;
    let w = doc.width;
    if !(1..=7).contains(&h) || w == 0 || w > 63 / h {
        return Err("tile dimensions must have height 1..7 and at most 63 cells".into());
    }
    let board = Board::new(h, w);
    let full = board.all_cells_mask;
    let mut nodes = HashMap::new();
    for (a, b, replies) in &doc.nodes {
        if (a | b) & !full != 0 || nodes.insert((*a, *b), replies).is_some() {
            return Err("invalid masks or duplicate checkpoint".into());
        }
    }
    if !nodes.contains_key(&(doc.root[0], doc.root[1])) {
        return Err("missing root checkpoint".into());
    }
    let mut edges = 0;
    let mut successors = HashMap::new();
    for (&(a, b), replies) in &nodes {
        if replies.len() != a.count_ones() as usize {
            return Err("not every Blue move has exactly one reply".into());
        }
        let mut moves = a;
        let mut children = Vec::new();
        for &reply in replies.iter() {
            if reply >= h * w {
                return Err("reply outside tile".into());
            }
            let bit = moves & moves.wrapping_neg();
            moves ^= bit;
            let (a1, b1) = board.child_legals(a, b, 0, bit);
            if b1 & (1 << reply) == 0 {
                return Err("illegal White reply".into());
            }
            let (a2, b2) = board.child_legals(a1, b1, 1, 1 << reply);
            if !nodes.contains_key(&(a2, b2)) || (a2 | b2).count_ones() + 2 > (a | b).count_ones() {
                return Err("missing successor or nondecreasing edge".into());
            }
            children.push((a2, b2));
            edges += 1;
        }
        successors.insert((a, b), children);
    }
    let mut seen = HashSet::new();
    let mut stack = vec![(doc.root[0], doc.root[1])];
    while let Some(key) = stack.pop() {
        if seen.insert(key) {
            stack.extend(&successors[&key]);
        }
    }
    if seen.len() != nodes.len() {
        return Err("unreachable checkpoints".into());
    }
    Ok(edges)
}

pub fn transform(mask: u64, h: usize, w: usize, rf: bool, cf: bool) -> u64 {
    let mut result = 0;
    for r in 0..h {
        for c in 0..w {
            if mask & (1 << (r * w + c)) != 0 {
                result |=
                    1 << ((if rf { h - 1 - r } else { r }) * w + if cf { w - 1 - c } else { c });
            }
        }
    }
    result
}

impl Evaluator {
    pub fn load(directory: &Path) -> Result<Self, String> {
        let manifest: Manifest = serde_json::from_slice(
            &std::fs::read(directory.join("manifest.json")).map_err(|e| e.to_string())?,
        )
        .map_err(|e| e.to_string())?;
        if manifest.format != "col-one-sided-tiles-v1" {
            return Err("unknown tile format".into());
        }
        let base = directory.canonicalize().map_err(|e| e.to_string())?;
        let mut tiles = Vec::new();
        for meta in manifest.certificates {
            let path = base
                .join(&meta.file)
                .canonicalize()
                .map_err(|e| e.to_string())?;
            if !path.starts_with(&base) {
                return Err("certificate outside library".into());
            }
            let bytes = std::fs::read(path).map_err(|e| e.to_string())?;
            if format!("{:x}", Sha256::digest(&bytes)) != meta.sha256 {
                return Err("certificate checksum mismatch".into());
            }
            let mut decoded = String::new();
            GzDecoder::new(bytes.as_slice())
                .read_to_string(&mut decoded)
                .map_err(|e| e.to_string())?;
            let doc: TileDoc = serde_json::from_str(&decoded).map_err(|e| e.to_string())?;
            if doc.height != meta.height
                || doc.width != meta.width
                || doc.root != meta.root
                || doc.nodes.len() != meta.nodes
                || check_tile(&doc)? != meta.edges
            {
                return Err("certificate metadata mismatch".into());
            }
            tiles.push(Tile {
                id: meta.file,
                source_sha256: meta.sha256,
                doc,
            });
        }
        Self::from_checked(tiles)
    }
    fn from_checked(tiles: Vec<Tile>) -> Result<Self, String> {
        let mut ids = HashSet::new();
        let mut seen = HashSet::new();
        let mut variants = Vec::new();
        for (i, tile) in tiles.iter().enumerate() {
            if !ids.insert(tile.id.clone()) {
                return Err("duplicate tile ID".into());
            }
            let d = &tile.doc;
            for (rf, cf) in [(false, false), (true, false), (false, true), (true, true)] {
                let root = d.root.map(|m| transform(m, d.height, d.width, rf, cf));
                if !seen.insert((d.height, d.width, root)) {
                    continue;
                }
                let edge = |c| {
                    (0..d.height).fold(0u8, |m, r| {
                        m | ((((root[1] >> (r * d.width + c)) & 1) as u8) << r)
                    })
                };
                variants.push(Variant {
                    tile: i,
                    root,
                    left: edge(0),
                    right: edge(d.width - 1),
                    rf,
                    cf,
                });
            }
        }
        Ok(Self {
            tiles,
            variants,
            counters: Counters::default(),
        })
    }
    pub fn supports(&self, height: usize) -> bool {
        self.tiles.iter().any(|t| t.doc.height == height)
    }
    pub fn metrics(&self) -> Metrics {
        let c = &self.counters;
        Metrics {
            queries: c.queries.load(Ordering::Relaxed),
            matching_tiles: c.matches.load(Ordering::Relaxed),
            successful_covers: c.covers.load(Ordering::Relaxed),
            dfs_cutoffs: c.cutoffs.load(Ordering::Relaxed),
            query_seconds: c.nanos.load(Ordering::Relaxed) as f64 / 1e9,
        }
    }
    pub fn cutoff(&self) {
        self.counters.cutoffs.fetch_add(1, Ordering::Relaxed);
    }
    pub fn plan(&self, h: usize, columns: &[[u8; 2]], actor: u8) -> Option<Witness> {
        let started = Instant::now();
        self.counters.queries.fetch_add(1, Ordering::Relaxed);
        let result = self.plan_inner(h, columns, actor);
        self.counters
            .nanos
            .fetch_add(started.elapsed().as_nanos() as u64, Ordering::Relaxed);
        if result.is_some() {
            self.counters.covers.fetch_add(1, Ordering::Relaxed);
        }
        result
    }
    fn plan_inner(&self, h: usize, columns: &[[u8; 2]], actor: u8) -> Option<Witness> {
        if !valid_columns(h, columns) || actor > 1 {
            return None;
        }
        let n = columns.len();
        let states = 1usize << h;
        // (previous column, previous boundary mask, variant index or dead gap).
        let mut dp = vec![vec![None::<(usize, usize, Option<usize>)>; states]; n + 1];
        dp[0][0] = Some((0, 0, None));
        for c in 0..n {
            if dp[c].iter().all(Option::is_none) {
                continue;
            }
            let mut matches = Vec::new();
            for (i, v) in self.variants.iter().enumerate() {
                let d = &self.tiles[v.tile].doc;
                if d.height != h || c + d.width > n {
                    continue;
                }
                let actual = extract(columns, c, d.width, h);
                if actual[actor as usize] & !v.root[0] == 0
                    && v.root[1] & !actual[1 - actor as usize] == 0
                {
                    self.counters.matches.fetch_add(1, Ordering::Relaxed);
                    matches.push(i);
                }
            }
            for p in 0..states {
                if dp[c][p].is_none() {
                    continue;
                }
                if columns[c][actor as usize] == 0 && dp[c + 1][0].is_none() {
                    dp[c + 1][0] = Some((c, p, None));
                }
                for &i in &matches {
                    let v = &self.variants[i];
                    let end = c + self.tiles[v.tile].doc.width;
                    if p & v.left as usize == 0 && dp[end][v.right as usize].is_none() {
                        dp[end][v.right as usize] = Some((c, p, Some(i)));
                    }
                }
            }
        }
        let mut p = dp[n].iter().position(Option::is_some)?;
        let mut c = n;
        let mut blocks = Vec::new();
        while c > 0 {
            let (prev, mask, variant) = dp[c][p]?;
            if let Some(i) = variant {
                let v = &self.variants[i];
                blocks.push(Placement {
                    start_column: prev,
                    tile: self.tiles[v.tile].id.clone(),
                    row_flip: v.rf,
                    column_flip: v.cf,
                });
            }
            c = prev;
            p = mask;
        }
        blocks.reverse();
        Some(Witness { blocks })
    }
    pub fn winning_response(
        &self,
        h: usize,
        columns: &[[u8; 2]],
        actor: u8,
    ) -> Option<(usize, Witness)> {
        for cell in legal_cells(columns, h, actor) {
            let child = play(columns, h, actor, cell).ok()?;
            if let Some(w) = self.plan(h, &child, 1 - actor) {
                return Some((cell, w));
            }
        }
        None
    }
    pub fn certify(&self, h: usize, columns: Columns, actor: u8, cover_openings: bool) -> Report {
        let mut report = Report {
            format: "col-tiling-proof-v1".into(),
            height: h,
            width: columns.len(),
            turn: actor,
            columns: columns.clone(),
            outcome: "unknown".into(),
            witness: None,
            response: None,
            openings: Vec::new(),
            uncovered: Vec::new(),
            library: self.tiles.clone(),
            metrics: Metrics::default(),
            cutoffs: Vec::new(),
        };
        if let Some(w) = self.plan(h, &columns, actor) {
            report.outcome = "loss".into();
            report.witness = Some(w);
        } else if let Some((cell, w)) = self.winning_response(h, &columns, actor) {
            report.outcome = "win".into();
            report.response = Some(cell);
            report.witness = Some(w);
        } else if cover_openings {
            for cell in legal_cells(&columns, h, actor) {
                let child = play(&columns, h, actor, cell).expect("legal move");
                if let Some((response, witness)) = self.winning_response(h, &child, 1 - actor) {
                    report.openings.push(Opening {
                        opening: cell,
                        response,
                        witness,
                    });
                } else {
                    report.uncovered.push(cell);
                }
            }
            if report.uncovered.is_empty() {
                report.outcome = "loss".into();
            }
        }
        report.metrics = self.metrics();
        report
    }
}

pub fn valid_columns(h: usize, c: &[[u8; 2]]) -> bool {
    (1..=7).contains(&h) && !c.is_empty() && c.iter().all(|p| (p[0] | p[1]) < (1u8 << h))
}
pub fn extract(columns: &[[u8; 2]], start: usize, width: usize, h: usize) -> [u64; 2] {
    let mut masks = [0, 0];
    for r in 0..h {
        for c in 0..width {
            for a in 0..2 {
                masks[a] |= (((columns[start + c][a] >> r) & 1) as u64) << (r * width + c);
            }
        }
    }
    masks
}
pub fn from_masks(h: usize, n: usize, a: u64, b: u64) -> Columns {
    (0..n)
        .map(|c| [a, b].map(|m| (0..h).fold(0u8, |s, r| s | (((m >> (r * n + c)) & 1) as u8) << r)))
        .collect()
}
pub fn legal_cells(columns: &[[u8; 2]], h: usize, actor: u8) -> Vec<usize> {
    (0..h * columns.len())
        .filter(|v| columns[v % columns.len()][actor as usize] & (1 << (v / columns.len())) != 0)
        .collect()
}
pub fn play(columns: &[[u8; 2]], h: usize, actor: u8, cell: usize) -> Result<Columns, String> {
    if !valid_columns(h, columns) || actor > 1 || cell >= h * columns.len() {
        return Err("invalid move input".into());
    }
    let n = columns.len();
    let r = cell / n;
    let c = cell % n;
    let bit = 1 << r;
    if columns[c][actor as usize] & bit == 0 {
        return Err("illegal move".into());
    }
    let mut out = columns.to_vec();
    out[c][0] &= !bit;
    out[c][1] &= !bit;
    if r > 0 {
        out[c][actor as usize] &= !(bit >> 1);
    }
    if r + 1 < h {
        out[c][actor as usize] &= !(bit << 1);
    }
    if c > 0 {
        out[c - 1][actor as usize] &= !bit;
    }
    if c + 1 < n {
        out[c + 1][actor as usize] &= !bit;
    }
    Ok(out)
}
pub fn position(h: usize, n: usize, text: Option<&str>) -> Result<Columns, String> {
    if !(1..=7).contains(&h) || n == 0 {
        return Err("certificate boards require height 1..7 and positive width".into());
    }
    let mut cols = vec![[(1u8 << h) - 1; 2]; n];
    if let Some(text) = text {
        let rows: Vec<_> = text.split('/').collect();
        if rows.len() != h || rows.iter().any(|s| s.chars().count() != n) {
            return Err("position dimensions mismatch".into());
        }
        // Apply stones without alternation; same-color adjacent stones are rejected.
        for (r, row) in rows.iter().enumerate() {
            for (c, ch) in row.chars().enumerate() {
                let actor = match ch {
                    'B' | 'b' | '1' => Some(0),
                    'W' | 'w' | '2' => Some(1),
                    '.' | '_' | '-' => None,
                    _ => return Err("use B, W, or . in position".into()),
                };
                if let Some(a) = actor {
                    cols = play(&cols, h, a, r * n + c)?;
                }
            }
        }
    }
    Ok(cols)
}

/// Independent global validation: check every physical cross-block edge.
pub fn check_witness(
    h: usize,
    columns: &[[u8; 2]],
    actor: u8,
    w: &Witness,
    tiles: &[Tile],
) -> Result<(), String> {
    if !valid_columns(h, columns) || actor > 1 {
        return Err("invalid board".into());
    }
    let n = columns.len();
    let mut virtuals = vec![[0u8; 2]; n];
    let mut owner = vec![None; n];
    for (i, p) in w.blocks.iter().enumerate() {
        let tile = tiles
            .iter()
            .find(|t| t.id == p.tile)
            .ok_or("unknown tile")?;
        let d = &tile.doc;
        if d.height != h || p.start_column > n || d.width > n - p.start_column {
            return Err("tile outside board".into());
        }
        let root = d
            .root
            .map(|m| transform(m, h, d.width, p.row_flip, p.column_flip));
        for c in 0..d.width {
            let g = p.start_column + c;
            if owner[g].replace(i).is_some() {
                return Err("overlapping tiles".into());
            }
            for r in 0..h {
                for a in 0..2 {
                    virtuals[g][a] |= (((root[a] >> (r * d.width + c)) & 1) as u8) << r;
                }
            }
        }
    }
    for c in 0..n {
        if columns[c][actor as usize] & !virtuals[c][0] != 0 {
            return Err("uncovered Blue move".into());
        }
        if virtuals[c][1] & !columns[c][1 - actor as usize] != 0 {
            return Err("invented White move".into());
        }
        if c > 0 && owner[c] != owner[c - 1] && virtuals[c][1] & virtuals[c - 1][1] != 0 {
            return Err("White interaction across blocks".into());
        }
    }
    Ok(())
}

pub fn check_report(report: &Report) -> Result<(), String> {
    if report.format != "col-tiling-proof-v1"
        || report.width != report.columns.len()
        || !valid_columns(report.height, &report.columns)
        || report.turn > 1
    {
        return Err("invalid proof header".into());
    }
    let mut ids = HashSet::new();
    for t in &report.library {
        if !ids.insert(&t.id) {
            return Err("duplicate tile ID".into());
        }
        check_tile(&t.doc)?;
    }
    let h = report.height;
    let a = report.turn;
    for leaf in &report.cutoffs {
        if leaf.columns.len() != report.width {
            return Err("cutoff width mismatch".into());
        }
        let (cols, actor) = if let Some(cell) = leaf.response {
            (play(&leaf.columns, h, leaf.turn, cell)?, 1 - leaf.turn)
        } else {
            (leaf.columns.clone(), leaf.turn)
        };
        check_witness(h, &cols, actor, &leaf.witness, &report.library)?;
    }
    match (&report.witness, report.response, report.outcome.as_str()) {
        (Some(w), None, "loss") => {
            if !report.openings.is_empty() || !report.uncovered.is_empty() {
                return Err("mixed proof forms".into());
            }
            check_witness(h, &report.columns, a, w, &report.library)?;
        }
        (Some(w), Some(cell), "win") => {
            if !report.openings.is_empty() || !report.uncovered.is_empty() {
                return Err("mixed proof forms".into());
            }
            check_witness(
                h,
                &play(&report.columns, h, a, cell)?,
                1 - a,
                w,
                &report.library,
            )?;
        }
        (None, None, "loss" | "unknown") => {
            let legal: HashSet<_> = legal_cells(&report.columns, h, a).into_iter().collect();
            let mut seen = HashSet::new();
            for o in &report.openings {
                if !seen.insert(o.opening) {
                    return Err("duplicate opening".into());
                }
                let child = play(
                    &play(&report.columns, h, a, o.opening)?,
                    h,
                    1 - a,
                    o.response,
                )?;
                check_witness(h, &child, a, &o.witness, &report.library)?;
            }
            for &v in &report.uncovered {
                if !legal.contains(&v) || !seen.insert(v) {
                    return Err("invalid uncovered opening".into());
                }
            }
            if report.outcome == "loss" && (!report.uncovered.is_empty() || seen != legal) {
                return Err("incomplete opening proof".into());
            }
        }
        _ => return Err("invalid proof outcome/form".into()),
    }
    Ok(())
}

pub fn write_report(path: &Path, report: &Report) -> Result<(), String> {
    check_report(report)?;
    if let Some(p) = path.parent() {
        if !p.as_os_str().is_empty() {
            std::fs::create_dir_all(p).map_err(|e| e.to_string())?;
        }
    }
    let data = serde_json::to_vec(report).map_err(|e| e.to_string())?;
    std::fs::write(path, data).map_err(|e| e.to_string())
}

/// Audit the original 3x15 package's fixed opening and family claims as well
/// as its local DAGs. This is separate from the generalized artifact checker.
pub fn check_fixture(directory: &Path) -> Result<(), String> {
    let e = Evaluator::load(directory)?;
    let manifest: serde_json::Value = serde_json::from_slice(
        &std::fs::read(directory.join("manifest.json")).map_err(|e| e.to_string())?,
    )
    .map_err(|e| e.to_string())?;
    if manifest["board"] != serde_json::json!({"height":3,"width":15}) {
        return Err("expected original 3x15 fixture".into());
    }
    let convert = |v: &serde_json::Value| -> Result<Witness, String> {
        let mut blocks = Vec::new();
        for p in v["blocks"].as_array().ok_or("missing blocks")? {
            let id = p["certificate"].as_str().ok_or("missing certificate")?;
            let t = e.tiles.iter().find(|t| t.id == id).ok_or("unknown tile")?;
            if p["width"].as_u64() != Some(t.doc.width as u64) {
                return Err("block width mismatch".into());
            }
            blocks.push(Placement {
                start_column: p["start_column"].as_u64().ok_or("invalid start")? as usize,
                tile: id.into(),
                row_flip: false,
                column_flip: false,
            });
        }
        Ok(Witness { blocks })
    };
    let empty = position(3, 15, None)?;
    let mut reps = HashSet::new();
    let mut covered = HashSet::new();
    for o in manifest["openings"].as_array().ok_or("missing openings")? {
        let b = o["blue_opening"].as_u64().ok_or("bad opening")? as usize;
        let w = o["white_response"].as_u64().ok_or("bad response")? as usize;
        if b / 15 > 1 || b % 15 > 7 || !reps.insert(b) {
            return Err("invalid opening representatives".into());
        }
        let cols = play(&play(&empty, 3, 0, b)?, 3, 1, w)?;
        check_witness(3, &cols, 0, &convert(o)?, &e.tiles)?;
        for r in [b / 15, 2 - b / 15] {
            for c in [b % 15, 14 - b % 15] {
                covered.insert(r * 15 + c);
            }
        }
    }
    if reps.len() != 16 || covered.len() != 45 {
        return Err("incomplete opening coverage".into());
    }
    let demon = &manifest["demon_case"];
    if demon["blue_stones"] != serde_json::json!([0, 14])
        || demon["white_stones"] != serde_json::json!([44])
        || demon["white_response"] != 12
    {
        return Err("wrong demon claim".into());
    }
    let cols = position(
        3,
        15,
        Some("B.............B/.............../..............W"),
    )?;
    check_witness(3, &play(&cols, 3, 1, 12)?, 0, &convert(demon)?, &e.tiles)?;
    for (name, width, root) in [
        ("A4", 4, [4076, 2038]),
        ("E4", 4, [4095, 2023]),
        ("B2", 2, [60, 24]),
        ("F1", 1, [7, 5]),
    ] {
        let id = manifest["family_tiles"][name]
            .as_str()
            .ok_or("missing family")?;
        let t = e
            .tiles
            .iter()
            .find(|t| t.id == id)
            .ok_or("unknown family tile")?;
        if t.doc.width != width || t.doc.root != root {
            return Err("wrong family root".into());
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::OnceLock;
    fn evaluator() -> &'static Evaluator {
        static LIB: OnceLock<Evaluator> = OnceLock::new();
        LIB.get_or_init(|| Evaluator::load(&default_library()).unwrap())
    }
    #[test]
    fn original_package_and_every_edge() {
        check_fixture(&default_library()).unwrap();
        let e = evaluator();
        assert_eq!(e.tiles.len(), 25);
        assert_eq!(
            e.tiles.iter().map(|t| t.doc.nodes.len()).sum::<usize>(),
            22423
        );
        assert_eq!(
            e.tiles
                .iter()
                .map(|t| check_tile(&t.doc).unwrap())
                .sum::<usize>(),
            91789
        );
    }
    #[test]
    fn full_root_long_strip_and_demon() {
        let e = evaluator();
        for n in [15, 17, 21, 101] {
            let r = e.certify(3, position(3, n, None).unwrap(), 0, true);
            assert_eq!(r.outcome, "loss");
            check_report(&r).unwrap();
        }
        let cols = position(
            3,
            15,
            Some("B.............B/.............../..............W"),
        )
        .unwrap();
        let r = e.certify(3, cols.clone(), 1, false);
        assert_eq!(r.outcome, "win");
        assert_eq!(r.response, Some(12));
        check_report(&r).unwrap();
        assert!(e.plan(3, &play(&cols, 3, 1, 30).unwrap(), 0).is_none());
        let swapped: Columns = cols.iter().map(|p| [p[1], p[0]]).collect();
        assert_eq!(e.certify(3, swapped, 0, false).response, Some(12));
    }
    #[test]
    fn remaining_19_gap_and_corruption_rejection() {
        let e = evaluator();
        let r = e.certify(3, position(3, 19, None).unwrap(), 0, true);
        assert_eq!(r.outcome, "unknown");
        assert_eq!(r.uncovered, vec![26, 30]);
        check_report(&r).unwrap();
        let mut bad = r.clone();
        bad.outcome = "loss".into();
        assert!(check_report(&bad).is_err());
        let mut r = e.certify(3, position(3, 15, None).unwrap(), 0, true);
        r.openings[0].response = r.openings[0].opening;
        assert!(check_report(&r).is_err());
        let mut doc = e
            .tiles
            .iter()
            .find(|t| t.doc.root[0] != 0)
            .unwrap()
            .doc
            .clone();
        let node = doc.nodes.iter_mut().find(|n| !n.2.is_empty()).unwrap();
        node.2[0] = node.0.trailing_zeros() as usize;
        assert!(check_tile(&doc).is_err());
    }
    fn exact(board: &Board, a: u64, b: u64, memo: &mut HashMap<(u64, u64), bool>) -> bool {
        if let Some(&v) = memo.get(&(a, b)) {
            return v;
        }
        let mut moves = a;
        let mut wins = false;
        while moves != 0 {
            let bit = moves & moves.wrapping_neg();
            moves ^= bit;
            let (aa, bb) = board.child_legals(a, b, 0, bit);
            if !exact(board, bb, aa, memo) {
                wins = true;
                break;
            }
        }
        memo.insert((a, b), wins);
        wins
    }
    #[test]
    fn all_small_shadows_and_column_transitions() {
        let e = evaluator();
        let board = Board::new(3, 2);
        let mut memo = HashMap::new();
        let mut accepted = 0;
        for a in 0..64 {
            for b in 0..64 {
                let cols = from_masks(3, 2, a, b);
                for actor in 0..2 {
                    if let Some(w) = e.plan(3, &cols, actor) {
                        check_witness(3, &cols, actor, &w, &e.tiles).unwrap();
                        accepted += 1;
                        assert!(!exact(
                            &board,
                            if actor == 0 { a } else { b },
                            if actor == 0 { b } else { a },
                            &mut memo
                        ));
                    }
                    for cell in legal_cells(&cols, 3, actor) {
                        let child = play(&cols, 3, actor, cell).unwrap();
                        let masks = board.child_legals(a, b, actor, 1 << cell);
                        assert_eq!(child, from_masks(3, 2, masks.0, masks.1));
                    }
                }
            }
        }
        assert!(accepted > 100);
    }
    #[test]
    fn boundary_join_and_coverage_rejected() {
        let e = evaluator();
        let cols = position(3, 9, None).unwrap();
        let w = e.plan(3, &cols, 0).unwrap();
        let mut missing = w.clone();
        missing.blocks.remove(0);
        assert!(check_witness(3, &cols, 0, &missing, &e.tiles).is_err());
        let mut overlap = w.clone();
        overlap.blocks[1].start_column = 0;
        assert!(check_witness(3, &cols, 0, &overlap, &e.tiles).is_err());
        let mut tiles = e.tiles.clone();
        // Test assembly checker in isolation with an invalid White bridge.
        let id = w.blocks[0].tile.clone();
        let t = tiles.iter_mut().find(|t| t.id == id).unwrap();
        t.doc.root[1] = (1 << (3 * t.doc.width)) - 1;
        assert!(check_witness(3, &cols, 0, &w, &tiles).is_err());
    }
}
