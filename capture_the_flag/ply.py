"""The Capture the Flag ply: a source/destination square pair.

Implements `game-engine-core`'s `GamePly` protocol. `str(ply)` is the simple
move notation (e.g. `"A4A5"`) — unique among a position's legal plies and
sufficient, together with the rules, to replay a game (the combat result is
recoverable, not stored). `parse_ply` is its exact inverse, used for human
move entry. The combat notation (the `-`/`x` display variant, `rules.md`
Section 4.4) is the *logged* form, rendered by
`CtfGameLogging.ply_annotation`; it never replaces `str(ply)` as the identity.
"""

import re
from typing import NamedTuple

from .board import Square, parse_square

_PLY_PATTERN = re.compile(r"([A-L]\d{1,2})([A-L]\d{1,2})")


class CtfPly(NamedTuple):
    source: Square
    destination: Square

    def __str__(self) -> str:
        return f"{self.source}{self.destination}"


def parse_ply(text: str) -> CtfPly:
    """Parse simple move notation (the inverse of `str(ply)`, e.g. 'A2A3').

    Raises `ValueError` with a player-facing message on malformed text or an
    out-of-range row.
    """
    match = _PLY_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"Malformed move: {text!r} (expected e.g. 'A2A3')")
    return CtfPly(parse_square(match.group(1)), parse_square(match.group(2)))
