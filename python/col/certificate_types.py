"""Role-explicit results. Local construction failures are never board outcomes."""
from dataclasses import dataclass
from enum import Enum, IntEnum


class Actor(IntEnum):
    BLUE = 0
    WHITE = 1


class BoundKind(str, Enum):
    UPPER_ZERO = 'upper_bound_zero'
    EXACT_ZERO = 'exact_zero'


@dataclass(frozen=True)
class Unknown:
    reason: str


@dataclass(frozen=True)
class ConstructionRejected:
    """A local obligation is unsafe; says nothing about its enclosing board."""
    height: int
    width: int
    first: int
    responder: int
    reason: str = 'complete_full_first_classification'


@dataclass(frozen=True)
class ActualProof:
    """A complete adaptive proof for an actual position, with an executable DAG."""
    winner: Actor
    root: tuple
    artifact: dict


def matched_bound(first, responder):
    """Call only AFTER establishing an upper bound on these actual masks.

    Subset promotion uses the induced live graph, retaining every hole.
    It is not inferred from the value of the tile used for inclusion matching.
    """
    return BoundKind.EXACT_ZERO if not responder & ~first else BoundKind.UPPER_ZERO
