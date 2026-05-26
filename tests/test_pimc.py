"""Tests de la déterminisation PIMC : `GameEnv.clone_determinized`."""

from collections import Counter

import pytest

from app.jeu import NUM_FAMILLES, NUM_ROLES, GameEnv, Role


def _identity_counter(env: GameEnv) -> Counter:
    """Multiset des (famille, role) sur l'ensemble des 90 cartes."""
    return Counter((c.famille, c.role) for c in env.cartes)


def test_no_randomize_keeps_identities() -> None:
    env = GameEnv(2, seed=42)
    clone = env.clone_determinized(randomize=False)
    # Toutes les cartes ont la même identité
    for original, c in zip(env.cartes, clone.cartes, strict=True):
        assert (original.famille, original.role) == (c.famille, c.role)


def test_pimc_preserves_global_identity_multiset() -> None:
    """Le multiset des (fam, role) sur l'ensemble des 90 cartes est invariant."""
    env = GameEnv(2, seed=42)
    expected = Counter()
    # 3 exemplaires de chaque (fam, role)
    for f in range(NUM_FAMILLES):
        for r in range(NUM_ROLES):
            expected[(f, r)] = 3

    clone = env.clone_determinized(randomize=True)
    assert _identity_counter(clone) == expected


def test_pimc_preserves_player_own_hand() -> None:
    """La main du joueur courant doit être identique après randomisation."""
    env = GameEnv(2, seed=42)
    cur = env.current_player
    own_hand_identities = [
        (env.cartes[i].famille, env.cartes[i].role) for i in env.mains[cur]
    ]
    clone = env.clone_determinized(randomize=True)
    clone_hand_identities = [
        (clone.cartes[i].famille, clone.cartes[i].role) for i in clone.mains[cur]
    ]
    assert own_hand_identities == clone_hand_identities


def test_pimc_preserves_visible_plateau_cards() -> None:
    """Toutes les cartes visibles sur le plateau gardent leur identité."""
    env = GameEnv(2, seed=42)
    # On joue quelques tours pour peupler le plateau
    import random as _r
    rng = _r.Random(0)
    for _ in range(3):
        if env.is_done():
            break
        actions = env.get_legal_actions()
        if not actions:
            break
        _, _, _, info = env.step(rng.choice(actions))
        while info.get("assassin_pending"):
            ctx = env.pending_assassin_context
            v = rng.choice(ctx["targets"]) if ctx and ctx["targets"] else None
            _, _, _, info = env.resolve_assassin_manual(v)

    visible_before = {
        i: (env.cartes[i].famille, env.cartes[i].role)
        for i in env.plateau_indices
        if env.cartes[i].visible
    }
    clone = env.clone_determinized(randomize=True)
    visible_after = {
        i: (clone.cartes[i].famille, clone.cartes[i].role) for i in visible_before
    }
    assert visible_before == visible_after


def test_pimc_face_down_opponent_cards_stay_spies() -> None:
    """Les cartes face cachée chez l'adversaire restent des espions après PIMC."""
    env = GameEnv(2, seed=42)
    # Forcer la pose d'un espion face cachée dans le domaine adverse
    # (on construit la situation à la main pour ce test).
    spy = next(c for c in env.cartes if c.role == Role.ESPION)
    spy.domaine_id = 1  # chez l'adversaire
    spy.position = None
    spy.proprietaire_idx = 1
    spy.visible = False
    env.plateau_indices.append(spy.id)

    clone = env.clone_determinized(randomize=True)
    # Le slot est toujours occupé par UN espion (peut-être un autre)
    assert clone.cartes[spy.id].role == Role.ESPION


def test_pimc_changes_unseen_identities_eventually() -> None:
    """Sur plusieurs clones, on doit voir au moins une variation des identités
    cachées (test probabiliste : très peu de chance de faux négatif)."""
    env = GameEnv(2, seed=42)
    opp = 1 - env.current_player
    # On fait piocher l'adversaire pour avoir une main "cachée"
    env._piocher(opp)

    baseline = [(env.cartes[i].famille, env.cartes[i].role) for i in env.mains[opp]]
    different_count = 0
    for _ in range(20):
        clone = env.clone_determinized(randomize=True)
        sample = [(clone.cartes[i].famille, clone.cartes[i].role) for i in clone.mains[opp]]
        if sample != baseline:
            different_count += 1
    assert different_count > 0, "PIMC n'a jamais randomisé sur 20 essais"


def test_pimc_clone_independent_of_original() -> None:
    """Muter le clone ne touche pas l'original."""
    env = GameEnv(2, seed=7)
    clone = env.clone_determinized(randomize=True)
    clone.mains[0].append(999)
    assert 999 not in env.mains[0]


@pytest.mark.parametrize("n", [2, 3, 4])
def test_pimc_works_for_n_players(n: int) -> None:
    env = GameEnv(n, seed=11)
    clone = env.clone_determinized(randomize=True)
    # Sanity: l'inventaire global est préservé
    expected = Counter()
    for f in range(NUM_FAMILLES):
        for r in range(NUM_ROLES):
            expected[(f, r)] = 3
    assert _identity_counter(clone) == expected
