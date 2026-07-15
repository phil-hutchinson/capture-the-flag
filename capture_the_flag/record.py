"""Game-record file writer (see `doc/ruleset/technical-notes.md`, "Record
file format").

Assembles a complete record file from a finished `GameResult`: PGN-style
header tags, the setup position block, and the move sequence built from
`StandardGame`'s game log. A `GameResult` is what both `play_match` (via
`MatchResult.game_result`) and the shared `Tournament` (`GameRecord.result`)
produce, so the writer serves either path.
"""

from collections.abc import Sequence

from game_engine_core.models.game_result import GameResult

_RESULT_TAGS = {1: "1-0", -1: "0-1", 0: "1/2-1/2"}

# The ruleset a record is written under, emitted as the mandatory `Ruleset` tag
# in the form `VERSION:NAME`. `PRE-RELEASE` is the current ruleset name (the game
# is pre-release and the rules are still being shaped); the version tracks
# `doc/ruleset/`'s current version and MUST be bumped alongside a rules change
# (see `changelog.md`/`technical-notes.md`). This engine writes -- and supports
# -- only the latest version; there is no backward-compatibility path for records
# written under earlier versions.
RULESET_NAME = "PRE-RELEASE"
RULESET_VERSION = "1.2"
_RULESET_TAG_VALUE = f"{RULESET_VERSION}:{RULESET_NAME}"


def _escape_tag_value(value: str) -> str:
    """Escape a tag value for the `[Name "value"]` header syntax.

    Follows PGN: a literal backslash becomes `\\\\` and a double-quote becomes
    `\\"`, so a value containing either can't terminate or corrupt the tag.
    Newlines (which a single-line tag cannot carry) are collapsed to spaces so
    a stray line break can't split the header into unparseable fragments.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return escaped.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _build_move_sequence(game_log: Sequence[tuple[str, str]]) -> str:
    ply_strings = [ply for ply, _board_after in game_log]
    lines = []
    for round_start in range(0, len(ply_strings), 2):
        round_number = round_start // 2 + 1
        white_ply = ply_strings[round_start]
        if round_start + 1 < len(ply_strings):
            black_ply = ply_strings[round_start + 1]
            lines.append(f"{round_number}. {white_ply} {black_ply}")
        else:
            lines.append(f"{round_number}. {white_ply}")
    return "\n".join(lines)


def write_record(
    game_result: GameResult,
    *,
    white_name: str | None = None,
    black_name: str | None = None,
    event: str | None = None,
    site: str | None = None,
    date: str | None = None,
    round_number: str | None = None,
) -> str:
    """Build a complete game-record file for a finished game.

    `white_name`, `black_name`, `event`, `site`, `date`, and `round_number`
    are best-effort roster tags: each is included only if supplied, and
    omitted entirely otherwise. `Result` is derived from the game's absolute
    outcome and `ResultReason` from `game_result.result_reason` (the terminal
    position's `outcome_reason`, e.g. `Flag Captured`). `Ruleset`, `Result`,
    and `ResultReason` are always present: `Ruleset` records the ruleset the
    game was played under (`<version>:PRE-RELEASE`; see `RULESET_VERSION`).

    Tag values are escaped for the `[Name "value"]` syntax (see
    `_escape_tag_value`): `\\` and `"` are backslash-escaped and newlines are
    collapsed to spaces, so an arbitrary player or event name always yields a
    well-formed, parseable header.
    """
    optional_tags = [
        ("Event", event),
        ("Site", site),
        ("Date", date),
        ("Round", round_number),
        ("White", white_name),
        ("Black", black_name),
    ]
    header_lines = [
        f'[{name} "{_escape_tag_value(value)}"]'
        for name, value in optional_tags
        if value is not None
    ]
    header_lines.append(f'[Ruleset "{_RULESET_TAG_VALUE}"]')
    header_lines.append(f'[Result "{_RESULT_TAGS[game_result.outcome]}"]')
    header_lines.append(f'[ResultReason "{_escape_tag_value(game_result.result_reason)}"]')

    header = "\n".join(header_lines)
    move_sequence = _build_move_sequence(game_result.game_log)
    return f"{header}\n\n{game_result.opening_board}\n\n{move_sequence}\n"
