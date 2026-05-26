"""Tests du mode "target" dans MCTS (B2 step β).

Vérifie que :
  - `mcts.search` détecte automatiquement le mode target quand
    `env.pending_assassin_context` est non None.
  - La distribution renvoyée a la bonne taille (`MAX_TARGETS + 1`).
  - L'arbre MCTS gère bien la transition main → target lors d'une descente.
  - Aucune incohérence de mode après ré-utilisation de la déterminisation
    figée au sein d'un monde (régression : avant le fix, sim_env était
    re-randomisé à chaque simulation, ce qui invalidait les modes du tree).
"""

import torch

from app.jeu import GameEnv, Role
from app.mcts_network import MAX_TARGETS, MCTS, CourtisansNet


def _setup_env_with_pending_assassin(seed: int = 0) -> GameEnv:
    """Construit un env où le joueur 0 vient de poser un assassin chez la
    Reine Estime, avec une victime déjà en Estime. Donc `env.pending_assassin_context`
    est non None après le retour."""
    torch.manual_seed(seed)
    env = GameEnv(2, seed=42)
    ass_id = next(
        i for i, c in enumerate(env.cartes)
        if c.role == Role.ASSASSIN and i in env.deck_indices
    )
    old = env.mains[0][0]
    deck_pos = env.deck_indices.index(ass_id)
    env.deck_indices[deck_pos] = old
    env.mains[0][0] = ass_id
    env.mains[0].sort(key=lambda i: env.cartes[i].sort_key)
    ass_pos = env.mains[0].index(ass_id)

    victim = next(
        c for c in env.cartes if c.role == Role.NEUTRE and c.id != ass_id
    )
    victim.position = "Estime"
    victim.visible = True
    victim.proprietaire_idx = 1
    victim.domaine_id = -1
    env.plateau_indices.append(victim.id)

    rest = [i for i in range(3) if i != ass_pos]
    perm = (ass_pos, rest[0], rest[1])
    action = env.mapper.encode(perm, "Estime", target_relative_idx=0)
    env.step(action)
    assert env.pending_assassin_context is not None
    return env


def _fresh_net(env: GameEnv, seed: int = 0) -> CourtisansNet:
    torch.manual_seed(seed)
    net = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size())
    net.eval()
    return net


def test_search_returns_target_size_when_pending() -> None:
    """En mode target, search() renvoie un vecteur de taille MAX_TARGETS + 1."""
    env = _setup_env_with_pending_assassin()
    net = _fresh_net(env)
    mcts = MCTS(net, num_sims=5)
    probs = mcts.search(env, add_root_noise=False)
    assert probs.shape == (MAX_TARGETS + 1,)
    assert abs(probs.sum() - 1.0) < 1e-5


def test_search_returns_main_size_when_no_pending() -> None:
    """Régression : en mode main, search() renvoie toujours `action_dim`."""
    env = GameEnv(2, seed=42)
    net = _fresh_net(env)
    mcts = MCTS(net, num_sims=5)
    probs = mcts.search(env)
    assert probs.shape == (env.mapper.get_action_space_size(),)


def test_target_search_mass_concentrated_on_legal_slots() -> None:
    """Seuls les slots correspondant à de vraies cibles + le slot skip doivent
    recevoir de la masse de proba."""
    env = _setup_env_with_pending_assassin()
    n_targets = len(env.pending_assassin_context["targets"])
    net = _fresh_net(env)
    mcts = MCTS(net, num_sims=5)
    probs = mcts.search(env, add_root_noise=False)

    legal_slots = set(range(n_targets)) | {MAX_TARGETS}
    illegal_mass = sum(probs[s] for s in range(MAX_TARGETS + 1) if s not in legal_slots)
    assert illegal_mass < 1e-6, f"Probas hors slots légaux : {illegal_mass}"


def test_no_mode_mismatch_during_search() -> None:
    """Régression : avant le fix, ~3-4 % des appels _apply_action voyaient
    `parent.mode='target'` mais `sim_env.pending=None`. Ce test vérifie 0 occurrences."""
    bug_count = [0]
    original_apply = MCTS._apply_action

    def traced_apply(self, parent, sim_env, action):
        if parent.mode == "target" and sim_env.pending_assassin_context is None:
            bug_count[0] += 1
        return original_apply(self, parent, sim_env, action)

    MCTS._apply_action = traced_apply
    try:
        for seed in range(10):
            env = _setup_env_with_pending_assassin(seed)
            net = _fresh_net(env, seed)
            mcts = MCTS(net, num_sims=10)
            mcts.search(env, add_root_noise=False)
    finally:
        MCTS._apply_action = original_apply

    assert bug_count[0] == 0, f"Mode mismatch fired {bug_count[0]} fois"


def test_target_with_batched_evaluator() -> None:
    """Le mode target doit aussi marcher avec le batched evaluator."""
    env = _setup_env_with_pending_assassin()
    net = _fresh_net(env)
    mcts = MCTS(net, num_sims=8, batch_size=4)
    probs = mcts.search(env, add_root_noise=False)
    assert probs.shape == (MAX_TARGETS + 1,)
    assert abs(probs.sum() - 1.0) < 1e-5


def test_target_with_multi_world() -> None:
    """num_worlds > 1 doit aggréger sur la dimension cible."""
    env = _setup_env_with_pending_assassin()
    net = _fresh_net(env)
    mcts = MCTS(net, num_sims=4, num_worlds=3)
    probs = mcts.search(env, add_root_noise=False)
    assert probs.shape == (MAX_TARGETS + 1,)
    assert abs(probs.sum() - 1.0) < 1e-5
