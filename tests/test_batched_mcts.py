"""Tests sur l'évaluateur MCTS batché (L3 #3.1)."""

import numpy as np
import torch

from app.jeu import GameEnv
from app.mcts_network import MCTS, CourtisansNet


def _fresh_net(env: GameEnv, seed: int = 0) -> CourtisansNet:
    torch.manual_seed(seed)
    net = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size())
    net.eval()
    return net


# --------------------------------------------------------------------------
# 1. batch_size=1 dispatch correctement vers le code séquentiel
# --------------------------------------------------------------------------
def test_batch_size_1_dispatches_to_sequential() -> None:
    """Avec `batch_size=1`, `_search_single_world` doit appeler la version
    séquentielle (pas la batchée). On le vérifie par monkey-patch."""
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    mcts = MCTS(net, num_sims=4, batch_size=1)

    called: dict[str, bool] = {"seq": False, "batched": False}
    orig_seq = mcts._search_single_world_sequential
    orig_b = mcts._search_single_world_batched

    def fake_seq(env, add_root_noise):
        called["seq"] = True
        return orig_seq(env, add_root_noise)

    def fake_b(env, add_root_noise):
        called["batched"] = True
        return orig_b(env, add_root_noise)

    mcts._search_single_world_sequential = fake_seq  # type: ignore[assignment]
    mcts._search_single_world_batched = fake_b  # type: ignore[assignment]

    mcts._search_single_world(env, add_root_noise=False)
    assert called["seq"] and not called["batched"]


def test_batch_size_gt_1_dispatches_to_batched() -> None:
    """Avec `batch_size > 1`, c'est l'inverse."""
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    mcts = MCTS(net, num_sims=4, batch_size=2)

    called: dict[str, bool] = {"seq": False, "batched": False}
    orig_seq = mcts._search_single_world_sequential
    orig_b = mcts._search_single_world_batched

    def fake_seq(env, add_root_noise):
        called["seq"] = True
        return orig_seq(env, add_root_noise)

    def fake_b(env, add_root_noise):
        called["batched"] = True
        return orig_b(env, add_root_noise)

    mcts._search_single_world_sequential = fake_seq  # type: ignore[assignment]
    mcts._search_single_world_batched = fake_b  # type: ignore[assignment]

    mcts._search_single_world(env, add_root_noise=False)
    assert called["batched"] and not called["seq"]


# --------------------------------------------------------------------------
# 2. Probabilités valides avec batch_size > 1
# --------------------------------------------------------------------------
def test_batched_search_returns_valid_distribution() -> None:
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    mcts = MCTS(net, num_sims=16, batch_size=4)
    probs = mcts.search(env, add_root_noise=False)
    assert probs.shape == (env.mapper.get_action_space_size(),)
    assert abs(probs.sum() - 1.0) < 1e-5
    assert (probs >= 0).all()


def test_batched_search_with_root_noise() -> None:
    """Dirichlet noise ne doit pas casser le mode batché."""
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    mcts = MCTS(net, num_sims=8, batch_size=4)
    probs = mcts.search(env, add_root_noise=True)
    assert abs(probs.sum() - 1.0) < 1e-5


def test_batched_search_with_multi_world() -> None:
    """Combinaison PIMC multi (num_worlds) + batché (batch_size)."""
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    mcts = MCTS(net, num_sims=6, batch_size=3, num_worlds=2)
    probs = mcts.search(env, add_root_noise=False)
    assert abs(probs.sum() - 1.0) < 1e-5


# --------------------------------------------------------------------------
# 3. Test critique : pas de virtual loss résiduelle après search()
# --------------------------------------------------------------------------
def test_batched_search_leaves_no_residual_virtual_loss() -> None:
    """Après la fin de `search`, les visit_count des nœuds du root doivent
    refléter le nombre de simulations qui ont passé par chacun — pas
    d'inflation par virtual loss non annulée."""
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    num_sims = 12
    mcts = MCTS(net, num_sims=num_sims, batch_size=4)

    # On accède au seul "monde" via la méthode interne pour inspecter l'arbre.
    # On ré-implémente la logique de search() de manière minimale :
    root_env = env.clone_determinized()
    counts = mcts._search_single_world_batched(env, add_root_noise=False)

    # Total des visits des enfants du root = num_sims exactement
    # (chaque simulation traverse 1 enfant racine en backprop).
    total_visits = int(counts.sum())
    assert total_visits == num_sims, f"Attendu {num_sims} visites, vu {total_visits}"


def test_batched_visits_match_sequential_count() -> None:
    """Le nombre total de visites à la racine doit être le même en batché
    qu'en séquentiel — ce qui prouve l'absence de visites virtuelles
    résiduelles."""
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    num_sims = 9

    mcts_seq = MCTS(net, num_sims=num_sims, batch_size=1)
    counts_seq = mcts_seq._search_single_world(env, add_root_noise=False)

    mcts_batched = MCTS(net, num_sims=num_sims, batch_size=3)
    counts_b = mcts_batched._search_single_world(env, add_root_noise=False)

    assert int(counts_seq.sum()) == num_sims
    assert int(counts_b.sum()) == num_sims


# --------------------------------------------------------------------------
# 4. Batch > num_sims : on ne fait jamais plus que num_sims simulations
# --------------------------------------------------------------------------
def test_batch_size_larger_than_num_sims_clamps() -> None:
    env = GameEnv(2, seed=42)
    net = _fresh_net(env, 0)
    mcts = MCTS(net, num_sims=3, batch_size=10)
    counts = mcts._search_single_world(env, add_root_noise=False)
    assert int(counts.sum()) == 3
