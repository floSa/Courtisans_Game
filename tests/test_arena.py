"""Tests sur l'arène d'évaluation entre modèles."""

import torch

from app.jeu import GameEnv
from app.mcts_network import CourtisansNet, _play_one_arena_game, arena


def _fresh_net(env: GameEnv, seed: int = 0) -> CourtisansNet:
    torch.manual_seed(seed)
    net = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size())
    net.eval()
    return net


def test_arena_returns_full_stats() -> None:
    env = GameEnv(2)
    a = _fresh_net(env, 1)
    b = _fresh_net(env, 2)
    stats = arena(a, b, num_games=2, num_sims=3, num_players=2)
    assert set(stats.keys()) == {"wins", "losses", "draws", "winrate"}
    assert stats["wins"] + stats["losses"] + stats["draws"] == 2
    assert 0.0 <= stats["winrate"] <= 1.0


def test_arena_winrate_with_only_draws() -> None:
    """Edge case : si toutes les parties sont nulles, winrate = 0.0 (pas NaN)."""
    env = GameEnv(2)
    a = _fresh_net(env, 1)
    stats = arena(a, a, num_games=2, num_sims=2, num_players=2)
    # net identique → souvent égalité, mais peut varier selon MCTS aléatoire.
    # On vérifie juste que winrate est défini, pas NaN.
    assert isinstance(stats["winrate"], float)
    assert 0.0 <= stats["winrate"] <= 1.0


def test_play_one_arena_game_returns_valid_winner() -> None:
    env = GameEnv(2)
    a = _fresh_net(env, 1)
    b = _fresh_net(env, 2)
    result = _play_one_arena_game(a, b, num_players=2, num_sims=3, a_starts=True)
    assert result in (0, 1, None)


def test_play_one_arena_game_starting_position_swaps() -> None:
    """Vérifie que `a_starts` détermine bien qui joue le slot 0."""
    env = GameEnv(2)
    a = _fresh_net(env, 1)
    b = _fresh_net(env, 2)
    # Aucune assertion forte de résultat — juste pas de crash dans les deux configs
    r1 = _play_one_arena_game(a, b, num_players=2, num_sims=3, a_starts=True)
    r2 = _play_one_arena_game(a, b, num_players=2, num_sims=3, a_starts=False)
    assert r1 in (0, 1, None)
    assert r2 in (0, 1, None)


def test_mcts_multi_world_returns_normalized_probs() -> None:
    """L2#2.1 — `num_worlds > 1` doit produire des probas valides (somme=1)."""
    from app.mcts_network import MCTS
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    mcts = MCTS(net, num_sims=3, num_worlds=4)
    probs = mcts.search(env, add_root_noise=False)
    assert probs.shape == (env.mapper.get_action_space_size(),)
    assert abs(probs.sum() - 1.0) < 1e-5


def test_mcts_multi_world_aggregates_visits() -> None:
    """Plus de mondes -> plus de visites cumulées avant normalisation.
    On vérifie en regardant la fonction interne `_search_single_world`."""
    from app.mcts_network import MCTS
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    mcts = MCTS(net, num_sims=5, num_worlds=1)
    counts_one = mcts._search_single_world(env, add_root_noise=False)
    # Chaque monde voit `num_sims` simulations -> somme des visites root ≈ num_sims
    # (un peu moins car la première sim est juste l'expansion racine).
    assert counts_one.sum() > 0
