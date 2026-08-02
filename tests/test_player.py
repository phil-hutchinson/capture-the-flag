"""Tests for the `make_player` factory the runners seat players through."""

import random

import pytest

from capture_the_flag.game_setup import BATTLE_SETUP
from capture_the_flag.game_ui import CtfGameUI
from capture_the_flag.player import (
    HumanCtfPlayer,
    PlayerContext,
    RandomCtfPlayer,
    make_player,
)
from capture_the_flag.side import Side


def test_make_random_player():
    player = make_player("random", "R", context=PlayerContext(rng=random.Random(1)))
    assert isinstance(player, RandomCtfPlayer)
    # A random seat can produce a legal placement without a UI.
    assert len(player.get_placement(Side.WHITE, BATTLE_SETUP)) == 25


def test_make_human_player_needs_a_game_ui():
    # Human seats read input through a UI; the factory refuses to build one without.
    with pytest.raises(ValueError, match="game UI"):
        make_player("human", "H", context=PlayerContext(game_ui=None))

    player = make_player("human", "H", context=PlayerContext(game_ui=CtfGameUI()))
    assert isinstance(player, HumanCtfPlayer)


def test_make_neural_player():
    # Imported lazily so this only pulls in torch when the neural kind is asked for.
    from capture_the_flag.engines.neural_network.neural_ctf_player import (
        NeuralCtfPlayer,
    )

    player = make_player(
        "neural",
        "N",
        context=PlayerContext(rng=random.Random(1), setup=BATTLE_SETUP),
        iterations=5,
    )
    assert isinstance(player, NeuralCtfPlayer)
    assert len(player.get_placement(Side.BLACK, BATTLE_SETUP)) == 25


def test_make_neural_player_needs_a_setup():
    # A neural seat's network is built to the board it will play on, so there is
    # no defensible default: refusing is the alternative to quietly seating a
    # Battle-shaped network in a Skirmish game.
    with pytest.raises(ValueError, match="game setup"):
        make_player("neural", "N", context=PlayerContext(rng=random.Random(1)))


def test_make_player_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown player kind"):
        make_player("bogus", "B", context=PlayerContext())
