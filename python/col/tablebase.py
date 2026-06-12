"""Compact pickle-backed tablebase shared by DFS and BFS solvers.

Entries are stored as zlib-compressed varint deltas over the sorted keys
plus a packed result bitmap (~1 byte/state) instead of a raw pickled dict
(~10 bytes/state). Varints handle keys wider than 64 bits, which occur on
boards with more than 31 cells.
"""

from __future__ import annotations

import pickle
import zlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Mapping, Optional, Tuple

from col.core import ColBoard, StateKey


TablebaseEntries = Dict[StateKey, bool]


def _encode_entries(entries: Mapping[StateKey, bool]) -> Tuple[int, bytes, bytes]:
    keys = sorted(entries)
    deltas = bytearray()
    prev = 0
    for key in keys:
        delta = key - prev
        prev = key
        while True:
            byte = delta & 0x7F
            delta >>= 7
            if delta:
                deltas.append(byte | 0x80)
            else:
                deltas.append(byte)
                break

    bitmap = bytearray((len(keys) + 7) // 8)
    for index, key in enumerate(keys):
        if entries[key]:
            bitmap[index >> 3] |= 1 << (index & 7)

    return len(keys), zlib.compress(bytes(deltas), 9), zlib.compress(bytes(bitmap), 9)


def _decode_entries(count: int, deltas_blob: bytes, bitmap_blob: bytes) -> TablebaseEntries:
    deltas = zlib.decompress(deltas_blob)
    bitmap = zlib.decompress(bitmap_blob)

    entries: TablebaseEntries = {}
    key = 0
    position = 0
    for index in range(count):
        delta = 0
        shift = 0
        while True:
            byte = deltas[position]
            position += 1
            delta |= (byte & 0x7F) << shift
            if byte & 0x80:
                shift += 7
            else:
                break
        key += delta
        entries[key] = bool(bitmap[index >> 3] & (1 << (index & 7)))
    return entries


class Tablebase:
    VERSION = 4

    def __init__(self, root: Optional[Path] = None, enabled: bool = True) -> None:
        self.enabled = enabled
        self.root = Path(root) if root is not None else Path("data/tablebases")

    def path_for(self, board: ColBoard) -> Path:
        symmetry = "sym" if board.use_symmetry else "nosym"
        return self.root / f"{board.storage_m}x{board.storage_n}_{symmetry}.pkl"

    def checkpoint_path_for(self, board: ColBoard) -> Path:
        return self.path_for(board).with_suffix(".pkl.log")

    def load(self, board: ColBoard) -> TablebaseEntries:
        if not self.enabled:
            return {}

        entries: TablebaseEntries = {}
        path = self.path_for(board)
        if path.exists():
            with path.open("rb") as handle:
                payload = pickle.load(handle)

            if not self._valid_payload(payload, board):
                return {}
            entries.update(self._payload_entries(payload))

        checkpoint_path = self.checkpoint_path_for(board)
        if checkpoint_path.exists():
            with checkpoint_path.open("rb") as handle:
                while True:
                    try:
                        payload = pickle.load(handle)
                    except EOFError:
                        break

                    if not self._valid_payload(payload, board):
                        return entries
                    for key, result in self._payload_entries(payload).items():
                        existing = entries.get(key)
                        if existing is not None and existing != result:
                            raise ValueError(f"conflicting tablebase entry for key {key}")
                        entries[key] = result
        return entries

    def save(self, board: ColBoard, entries: TablebaseEntries) -> None:
        if not self.enabled:
            return

        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(board)
        payload = self._payload(board, entries)

        with NamedTemporaryFile("wb", dir=self.root, delete=False) as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
            tmp_path = Path(handle.name)
        tmp_path.replace(path)
        checkpoint_path = self.checkpoint_path_for(board)
        if checkpoint_path.exists():
            checkpoint_path.unlink()

    def append(self, board: ColBoard, entries: Mapping[StateKey, bool]) -> None:
        if not self.enabled or not entries:
            return

        self.root.mkdir(parents=True, exist_ok=True)
        payload = self._payload(board, entries)
        with self.checkpoint_path_for(board).open("ab") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def _payload(self, board: ColBoard, entries: Mapping[StateKey, bool]) -> Dict[str, object]:
        count, deltas_blob, bitmap_blob = _encode_entries(entries)
        return {
            "version": self.VERSION,
            "m": board.storage_m,
            "n": board.storage_n,
            "use_symmetry": board.use_symmetry,
            "count": count,
            "deltas": deltas_blob,
            "bitmap": bitmap_blob,
        }

    @staticmethod
    def _payload_entries(payload: Dict[str, object]) -> TablebaseEntries:
        count = payload.get("count")
        deltas_blob = payload.get("deltas")
        bitmap_blob = payload.get("bitmap")
        if not isinstance(count, int) or not isinstance(deltas_blob, bytes) or not isinstance(bitmap_blob, bytes):
            return {}
        return _decode_entries(count, deltas_blob, bitmap_blob)

    def _valid_payload(self, payload: object, board: ColBoard) -> bool:
        return (
            isinstance(payload, dict)
            and payload.get("version") == self.VERSION
            and payload.get("m") == board.storage_m
            and payload.get("n") == board.storage_n
            and payload.get("use_symmetry") == board.use_symmetry
        )
