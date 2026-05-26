"""Tests sur ActionMapper : bijection encode/decode."""

from itertools import permutations

import pytest

from app.jeu import ActionMapper


@pytest.mark.parametrize("n_players", [2, 3, 4, 5])
def test_action_space_size(n_players: int) -> None:
    m = ActionMapper(n_players)
    assert m.get_action_space_size() == 6 * 2 * (n_players - 1)


@pytest.mark.parametrize("n_players", [2, 3, 4, 5])
def test_decode_encode_bijection(n_players: int) -> None:
    m = ActionMapper(n_players)
    seen = set()
    for i in range(m.get_action_space_size()):
        perm, q, t = m.decode(i)
        assert perm in list(permutations([0, 1, 2]))
        assert q in ("Estime", "Disgrace")
        assert 0 <= t < n_players - 1
        encoded = m.encode(perm, q, t)
        assert encoded == i, f"decode({i}) -> encode = {encoded}"
        # Unicité du triplet décodé
        assert (perm, q, t) not in seen
        seen.add((perm, q, t))


def test_encode_invalid_perm() -> None:
    m = ActionMapper(2)
    with pytest.raises(ValueError):
        m.encode((9, 0, 1), "Estime", 0)


def test_encode_invalid_queen_pos() -> None:
    m = ActionMapper(2)
    with pytest.raises(ValueError):
        m.encode((0, 1, 2), "Glory", 0)


def test_encode_invalid_target() -> None:
    m = ActionMapper(2)
    with pytest.raises(ValueError):
        m.encode((0, 1, 2), "Estime", 5)
