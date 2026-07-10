"""Game-record file writer (see `doc/ruleset/technical-notes.md`, "Record
file format").

Assembles a complete record file from a completed `MatchResult`: PGN-style
header tags, the setup position block, and the move sequence built from
`StandardGame`'s game log.
"""

from collections.abc import Sequence

from .match import MatchResult

_RESULT_TAGS = {1: "1-0", -1: "0-1", 0: "1/2-1/2"}

# The ruleset a record is written under, emitted as the mandatory `Ruleset` tag
# in the form `NAME:VERSION`. `PRIMARY` is the main (currently only) ruleset
# variant; the version tracks `doc/ruleset/`'s current version and MUST be
# bumped alongside a rules change (see `changelog.md`/`technical-notes.md`).
# This engine writes -- and supports -- only the latest version; there is no
# backward-compatibility path for records written under earlier versions.
RULESET_NAME = "PRIMARY"
RULESET_VERSION = "1.1"
_RULESET_TAG_VALUE = f"{RULESET_NAME}:{RULESET_VERSION}"


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
    match_result: MatchResult,
    *,
    white_name: str | None = None,
    black_name: str | None = None,
    event: str | None = None,
    site: str | None = None,
    date: str | None = None,
    round_number: str | None = None,
) -> str:
    """Build a complete game-record file for a finished match.

    `white_name`, `black_name`, `event`, `site`, `date`, and `round_number`
    are best-effort roster tags: each is included only if supplied, and
    omitted entirely otherwise. `Result` is derived from the match's
    absolute outcome; `ResultReason` is always `"Unknown"` until
    `game-engine-core` can surface a termination reason. `Ruleset`, `Result`,
    and `ResultReason` are always present: `Ruleset` records the ruleset the
    game was played under (`PRIMARY:<version>`; see `RULESET_VERSION`).

    Tag values are escaped for the `[Name "value"]` syntax (see
    `_escape_tag_value`): `\\` and `"` are backslash-escaped and newlines are
    collapsed to spaces, so an arbitrary player or event name always yields a
    well-formed, parseable header.
    """
    game_result = match_result.game_result
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
    header_lines.append('[ResultReason "Unknown"]')

    header = "\n".join(header_lines)
    move_sequence = _build_move_sequence(game_result.game_log)
    return f"{header}\n\n{game_result.opening_board}\n\n{move_sequence}\n"
