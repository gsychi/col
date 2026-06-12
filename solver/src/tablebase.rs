//! Compact tablebase files compatible with Python `utils/tablebase.py` v4.
//!
//! Format: pickle dict with zlib-compressed varint key deltas + win/loss bitmap.

use flate2::read::ZlibDecoder;
use flate2::write::ZlibEncoder;
use flate2::Compression;
use rustc_hash::FxHashMap;
use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

pub const VERSION: i64 = 4;

#[derive(Serialize, Deserialize)]
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

pub fn path_for(root: &Path, m: usize, n: usize) -> PathBuf {
    root.join(format!("{m}x{n}_sym.pkl"))
}

fn push_varint(out: &mut Vec<u8>, mut value: u128) {
    loop {
        let mut byte = (value & 0x7F) as u8;
        value >>= 7;
        if value != 0 {
            byte |= 0x80;
        }
        out.push(byte);
        if value == 0 {
            break;
        }
    }
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

fn zlib_compress(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut encoder = ZlibEncoder::new(Vec::new(), Compression::new(9));
    encoder.write_all(data).map_err(|err| err.to_string())?;
    encoder.finish().map_err(|err| err.to_string())
}

fn zlib_decompress(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut decoder = ZlibDecoder::new(data);
    let mut out = Vec::new();
    decoder
        .read_to_end(&mut out)
        .map_err(|err| err.to_string())?;
    Ok(out)
}

pub fn encode(mut entries: Vec<(u128, bool)>) -> Result<(usize, Vec<u8>, Vec<u8>), String> {
    entries.sort_unstable_by_key(|&(key, _)| key);

    let mut deltas = Vec::new();
    let mut prev = 0u128;
    for &(key, _) in &entries {
        push_varint(&mut deltas, key - prev);
        prev = key;
    }

    let count = entries.len();
    let mut bitmap = vec![0u8; (count + 7) / 8];
    for (index, &(_, value)) in entries.iter().enumerate() {
        if value {
            bitmap[index >> 3] |= 1 << (index & 7);
        }
    }

    Ok((count, zlib_compress(&deltas)?, zlib_compress(&bitmap)?))
}

pub fn decode(
    count: usize,
    deltas_blob: &[u8],
    bitmap_blob: &[u8],
) -> Result<FxHashMap<u128, bool>, String> {
    let deltas = zlib_decompress(deltas_blob)?;
    let bitmap = zlib_decompress(bitmap_blob)?;

    let mut entries = FxHashMap::default();
    let mut key = 0u128;
    let mut pos = 0usize;
    for index in 0..count {
        key = key
            .checked_add(read_varint(&deltas, &mut pos)?)
            .ok_or_else(|| "tablebase key overflow".to_string())?;
        let win = bitmap[index >> 3] & (1 << (index & 7)) != 0;
        entries.insert(key, win);
    }
    Ok(entries)
}

pub fn save(
    root: &Path,
    m: usize,
    n: usize,
    entries: Vec<(u128, bool)>,
) -> Result<PathBuf, String> {
    if entries.is_empty() {
        return Err("refusing to save empty tablebase".into());
    }

    fs::create_dir_all(root).map_err(|err| err.to_string())?;
    let path = path_for(root, m, n);
    let (count, deltas, bitmap) = encode(entries)?;

    let payload = Payload {
        version: VERSION,
        m: m as i64,
        n: n as i64,
        use_symmetry: true,
        count: count as i64,
        deltas,
        bitmap,
    };

    let bytes =
        serde_pickle::to_vec(&payload, Default::default()).map_err(|err| err.to_string())?;
    let tmp = path.with_extension("pkl.tmp");
    fs::write(&tmp, bytes).map_err(|err| err.to_string())?;
    fs::rename(&tmp, &path).map_err(|err| err.to_string())?;

    Ok(path)
}

pub fn load(root: &Path, m: usize, n: usize) -> Result<FxHashMap<u128, bool>, String> {
    let path = path_for(root, m, n);
    if !path.is_file() {
        return Ok(FxHashMap::default());
    }

    let bytes = fs::read(&path).map_err(|err| err.to_string())?;
    let payload: Payload =
        serde_pickle::from_slice(&bytes, Default::default()).map_err(|err| err.to_string())?;

    if payload.version != VERSION {
        return Err(format!(
            "unsupported tablebase version {} in {}",
            payload.version,
            path.display()
        ));
    }
    if payload.m as usize != m || payload.n as usize != n {
        return Err(format!(
            "tablebase dimensions {}x{} do not match requested {m}x{n}",
            payload.m, payload.n
        ));
    }
    if !payload.use_symmetry {
        return Err(format!(
            "tablebase {} is not symmetry-canonical",
            path.display()
        ));
    }

    let count = payload.count as usize;
    decode(count, &payload.deltas, &payload.bitmap)
}
