"""The Capture the Flag ply: a source/destination square pair.

Implements `game-engine-core`'s `GamePly` protocol. `str(ply)` is the simple
move notation (e.g. `"A4A5"`) — unique among a position's legal plies and
sufficient, together with the rules, to replay a game (the combat result is
recoverable, not stored). The combat notation (the `-`/`x` display variant,
`rules.md` Section 4.4) is the *logged* form, rendered by
`CtfGameLogging.ply_annotation`; it never replaces `str(ply)` as the identity.
"""

from typing import NamedTuple

from .board import Square


class CtfPly(NamedTuple):
    source: Square
    destination: Square

    def __str__(self) -> str:
        return f"{self.source}{self.destination}"
