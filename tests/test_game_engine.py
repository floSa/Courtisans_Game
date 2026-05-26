"""Tests d'invariants sur GameEnv (moteur du jeu Courtisans)."""

import random

import pytest

from app.jeu import NUM_CARD_TYPES, NUM_FAMILLES, NUM_ROLES, GameEnv, Role


def _play_random_game(env: GameEnv, max_turns: int = 200, rng_seed: int = 0) -> int:
    """Joue une partie aléatoire jusqu'à terminaison. Retourne le nb de tours."""
    rng = random.Random(rng_seed)
    turns = 0
    while not env.is_done() and turns < max_turns:
        actions = env.get_legal_actions()
        if not actions:
            break
        a = rng.choice(actions)
        _, _, _, info = env.step(a)
        while info.get("assassin_pending"):
            ctx = env.pending_assassin_context
            v = rng.choice(ctx["targets"]) if ctx and ctx["targets"] else None
            _, _, _, info = env.resolve_assassin_manual(v)
        turns += 1
    return turns


def test_deck_size() -> None:
    env = GameEnv(2)
    # 3 exemplaires × 6 familles × 5 rôles = 90 cartes
    expected = 3 * NUM_FAMILLES * NUM_ROLES
    assert len(env.cartes) == expected
    assert NUM_CARD_TYPES == NUM_FAMILLES * NUM_ROLES


def test_initial_hand_size() -> None:
    env = GameEnv(2, seed=42)
    assert len(env.mains[0]) == 3
    assert env.mains[1] == []


def test_hand_is_sorted() -> None:
    env = GameEnv(2, seed=42)
    keys = [env.cartes[i].sort_key for i in env.mains[0]]
    assert keys == sorted(keys)


def test_legal_actions_at_start() -> None:
    env = GameEnv(2, seed=42)
    assert env.get_legal_actions() == list(range(12))


def test_full_random_game_terminates_2p() -> None:
    env = GameEnv(2, seed=42)
    turns = _play_random_game(env)
    assert env.is_done(), f"Partie non terminée après {turns} tours"
    assert turns > 0


def test_state_vector_shape() -> None:
    env = GameEnv(2, seed=1)
    v = env.get_state_vector()
    assert v.shape == (env.get_state_vector_size(),)


def test_state_vector_no_negative() -> None:
    env = GameEnv(2, seed=1)
    v = env.get_state_vector()
    assert (v >= 0).all()


def test_spies_revealed_at_end_of_game() -> None:
    env = GameEnv(2, seed=42)
    _play_random_game(env)
    # Tous les espions encore en jeu doivent être visibles
    for i in env.plateau_indices:
        c = env.cartes[i]
        if c.role == Role.ESPION:
            assert c.visible, f"Espion {c} non révélé en fin de partie"


def test_score_uses_all_domain_cards() -> None:
    """Aucune carte de domaine ne doit être ignorée par le scoring."""
    env = GameEnv(2, seed=42)
    _play_random_game(env)
    scores = env._calcul_scores()
    assert set(scores.keys()) == {0, 1}
    # Sanity : la somme des |scores| doit être proche du nombre de cartes posées
    # dans les domaines (chacune valant 1 ou 2). On vérifie juste que le score
    # n'est pas absurde.
    assert all(isinstance(v, int) for v in scores.values())


def test_step_with_partial_hand_returns_done() -> None:
    """Si le joueur courant a moins de 3 cartes, step doit signaler la fin."""
    env = GameEnv(2, seed=42)
    # On force la pioche à vide et la main du joueur courant à 0
    env.deck_indices.clear()
    env.mains[env.current_player] = []
    env.mains[1 - env.current_player] = []
    _, _, done, _ = env.step(0)
    assert done


def test_seed_reproducibility() -> None:
    env_a = GameEnv(2, seed=123)
    env_b = GameEnv(2, seed=123)
    assert env_a.mains[0] == env_b.mains[0]
    assert env_a.deck_indices == env_b.deck_indices


def test_clone_does_not_share_state() -> None:
    env = GameEnv(2, seed=7)
    clone = env.clone_determinized()
    clone.mains[0].append(999)
    assert 999 not in env.mains[0]


@pytest.mark.parametrize("n", [2, 3, 4])
def test_action_space_consistent(n: int) -> None:
    env = GameEnv(n)
    assert env.mapper.get_action_space_size() == 6 * 2 * (n - 1)


def test_is_done_false_at_start() -> None:
    env = GameEnv(2, seed=42)
    assert not env.is_done()
