"""Tests for the interactive game view."""

import random
from dataclasses import replace

from capture_the_flag.game_view import render_game_view
from capture_the_flag.pieces import PieceType
from capture_the_flag.placement import assemble_position, random_placement
from capture_the_flag.side import Side


def _start_position():
    return assemble_position(
        random_placement(Side.WHITE, random.Random(1)),
        random_placement(Side.BLACK, random.Random(2)),
    )


def _without_pieces(position, removals):
    """A copy of `position` with `removals` — (side, piece, count) triples —
    taken off the board."""
    board = dict(position.board)
    for side, piece, count in removals:
        squares = [sq for sq, occupant in board.items() if occupant == (side, piece)]
        for square in squares[:count]:
            del board[square]
    return replace(position, board=board)


def test_board_is_labelled_with_the_move_notation_frame():
    lines = render_game_view(_start_position()).splitlines()
    header, board_lines = lines[0], lines[1:13]
    # Column letters sit over the middle character of each 3-character cell.
    assert header.index("A") == 5
    assert header.index("L") == 5 + 11 * 4
    assert board_lines[0].startswith("12  ")
    assert board_lines[11].startswith(" 1  ")
    # The labelled cells align under the header letters.
    assert board_lines[0][4] in "[*"


def test_start_position_status_lines():
    view = render_game_view(_start_position())
    assert "White to move" in view
    assert "Captured — White: none" in view
    assert "Captured — Black: none" in view
    assert "Inactivity — 0/50" in view


def test_captured_pieces_are_derived_from_the_board():
    position = _without_pieces(
        _start_position(),
        [
            (Side.BLACK, PieceType.KNIGHT, 2),
            (Side.BLACK, PieceType.HALBERDIER, 1),
            (Side.WHITE, PieceType.MILITIA, 1),
        ],
    )
    view = render_game_view(position)
    # Multiples get a count, singles just the name, in piece-rank order.
    assert "Captured — Black: Knight x2, Halberdier" in view
    assert "Captured — White: Militia" in view


def test_turn_and_clock_line_reports_the_position_fields():
    position = replace(
        _start_position(),
        side_to_move=Side.BLACK,
        inactivity_counter=7,
    )
    view = render_game_view(position)
    assert "Black to move" in view
    assert "Inactivity — 7/50" in view
