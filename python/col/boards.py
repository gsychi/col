"""Canonical board enumeration shared by Col experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True, order=True)
class BoardSpec:
    m: int
    n: int

    def __post_init__(self) -> None:
        if self.m <= 0 or self.n <= 0:
            raise ValueError("board dimensions must be positive")
        if self.m > self.n:
            raise ValueError("BoardSpec dimensions must be normalized")

    @classmethod
    def normalized(cls, m: int, n: int) -> "BoardSpec":
        return cls(m, n) if m <= n else cls(n, m)

    @classmethod
    def parse(cls, text: str) -> "BoardSpec":
        parts = text.lower().split("x")
        if len(parts) != 2:
            raise ValueError(f"bad board {text!r}; expected MxN")
        return cls.normalized(int(parts[0]), int(parts[1]))

    @property
    def cells(self) -> int:
        return self.m * self.n

    @property
    def label(self) -> str:
        return f"{self.m}x{self.n}"

    @property
    def is_path(self) -> bool:
        return self.m == 1


def odd_boards(max_cells: int, *, include_one_by_one: bool = False) -> list[BoardSpec]:
    """Return every normalized odd-by-odd rectangle within an area cap."""
    if max_cells <= 0:
        return []

    boards: list[BoardSpec] = []
    for m in range(1, max_cells + 1, 2):
        if m * m > max_cells:
            break
        for n in range(m, max_cells // m + 1, 2):
            if not include_one_by_one and m == n == 1:
                continue
            boards.append(BoardSpec(m, n))
    return sorted(boards, key=lambda board: (board.cells, board.m, board.n))


def odd_totals(start: int, max_total: int | None) -> Iterator[int]:
    """Yield odd totals, including the first odd total at or above ``start``."""
    total = start if start % 2 else start + 1
    while max_total is None or total <= max_total:
        yield total
        total += 2
