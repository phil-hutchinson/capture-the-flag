"""Tests for the `make_player` factory the runners seat players through."""

import random

import pytest

from capture_the_flag.game_setup import PRE_RELEASE_SETUP
from capture_the_flag.game_ui import CtfGameUI
from capture_the_flag.player import (
    HumanCtfPlayer,
    PlayerContext,
    RandomCtfPlayer,
    make_player,
)


def test_make_random_player():
    player = make_player("random", "R", context=PlayerContext(rng=random.Random(1)))
    assert isinstance(player, RandomCtfPlayer)
    assert player.name == "R"


def test_make_human_player_needs_a_game_ui():
    # Human seats read input through a UI; the factory refuses to build one without.
    with pytest.raises(ValueError, match="game UI"):
        make_player("human", "H", context=PlayerContext(game_ui=None))

    player = make_player(
        "human", "H", context=PlayerContext(game_ui=CtfGameUI(PRE_RELEASE_SETUP))
    )
    assert isinstance(player, HumanCtfPlayer)


def test_make_neural_player():
    # Imported lazily so this only pulls in torch when the neural kind is asked for.
    from capture_the_flag.engines.neural_network.neural_ctf_player import (
        NeuralCtfPlayer,
    )

    player = make_player(
        "neural",
        "N",
        context=PlayerContext(rng=random.Random(1), setup=PRE_RELEASE_SETUP),
        iterations=5,
    )
    assert isinstance(player, NeuralCtfPlayer)
    assert player.name == "N"


def test_make_neural_player_needs_a_setup():
    # A neural seat's network is built to the board it will play on, so there is
    # no defensible default: refusing is the alternative to quietly seating a
    # mismatched network.
    with pytest.raises(ValueError, match="game setup"):
        make_player("neural", "N", context=PlayerContext(rng=random.Random(1)))


def test_make_player_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown player kind"):
        make_player("bogus", "B", context=PlayerContext())
