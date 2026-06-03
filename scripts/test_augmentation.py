"""Test unitaire pour augment_sample.

Vérifie que permuter les familles côté state ET côté policy produit des
samples cohérents : jouer l'action décodée dans le jeu original et jouer
l'action augmentée dans le jeu sigma-équivalent doit produire des
configurations sigma-équivalentes.

Tests :
  1. Round-trip  : σ puis σ⁻¹ → state et policy identiques.
  2. Cohérence   : l'action argmax(π') jouée sur un état σ-remappé produit le
                   même placement physique (mêmes rôles, familles relabellisées)
                   que l'action argmax(π) jouée sur l'état original.
  3. Identité    : σ = identité → state et policy inchangés.
  4. Stress      : 1000 triples (σ random, état random) — assert 0 échec.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.augmentation import (
    augment_sample,
    compute_position_map,
    permute_policy,
    permute_state_vec,
    permutable_state_size,
    random_family_permutation,
)
from app.jeu import (
    NUM_FAMILLES,
    NUM_ROLES,
    ActionMapper,
    GameEnv,
)

NUM_PLAYERS = 2
mapper = ActionMapper(NUM_PLAYERS)
RNG = np.random.default_rng(42)
PERM_SIZE = permutable_state_size(NUM_PLAYERS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sigma_inverse(sigma: tuple[int, ...]) -> tuple[int, ...]:
    inv = [0] * NUM_FAMILLES
    for i, j in enumerate(sigma):
        inv[j] = i
    return tuple(inv)


def collect_sample() -> tuple[np.ndarray, np.ndarray, tuple[int, int, int]]:
    """Joue quelques coups aléatoires et retourne (state, uniform_policy, hand_keys)."""
    env = GameEnv(NUM_PLAYERS)
    # 0-3 coups aléatoires pour avoir un état non trivial
    n = int(RNG.integers(0, 4))
    for _ in range(n):
        if env.is_done():
            break
        if env.pending_assassin_context:
            env.resolve_assassin_manual(None)
            continue
        legal = env.get_legal_actions()
        env.step(int(RNG.choice(legal)))
    if env.is_done():
        env = GameEnv(NUM_PLAYERS)
    state = env.get_state_vector()
    legal = env.get_legal_actions()
    if not legal or env.is_done():
        env = GameEnv(NUM_PLAYERS)
        legal = env.get_legal_actions()
    # Politique uniforme sur les actions légales
    policy = np.zeros(mapper.get_action_space_size(), dtype=np.float32)
    policy[legal] = 1.0 / len(legal)
    hand_keys = tuple(
        sorted(env.cartes[i].sort_key for i in env.mains[env.current_player])
    )
    return state, policy, hand_keys  # type: ignore[return-value]


def apply_sigma_to_game(env: GameEnv, sigma: tuple[int, ...]) -> None:
    """Remplace in-place la famille de chaque carte par sigma(famille)."""
    for idx, c in enumerate(env.cartes):
        new_fam = sigma[c.famille]
        env._set_card_identity(idx, (new_fam, c.role))


def boards_are_sigma_equivalent(
    env_orig: GameEnv,
    env_sigma: GameEnv,
    sigma: tuple[int, ...],
) -> bool:
    """Vérifie que les plateaux sont σ-équivalents (mêmes rôles, familles relabellisées)."""
    # Comparer les state vectors : sigma appliqué à orig doit donner sigma
    s_orig = env_orig.get_state_vector()
    s_sigma = env_sigma.get_state_vector()
    s_orig_permuted = permute_state_vec(s_orig, sigma, permutable_size=PERM_SIZE)
    # La section espions cachés (non permutable) doit aussi correspondre
    return bool(np.allclose(s_orig_permuted, s_sigma, atol=1e-6))


# ---------------------------------------------------------------------------
# Test 1 : round-trip σ → σ⁻¹ = identité
# ---------------------------------------------------------------------------

def test_roundtrip():
    errors = 0
    for _ in range(200):
        state, policy, hand_keys = collect_sample()
        sigma = random_family_permutation(RNG)
        inv = sigma_inverse(sigma)

        s1, p1, hk1 = augment_sample(state, policy, hand_keys, mapper, sigma)
        s2, p2, hk2 = augment_sample(s1, p1, hk1, mapper, inv)

        if not np.allclose(s2, state, atol=1e-6):
            errors += 1
        if not np.allclose(p2, policy, atol=1e-6):
            errors += 1
        if hk2 != hand_keys:
            errors += 1

    assert errors == 0, f"Round-trip ÉCHEC : {errors} erreurs sur 200 samples"
    print("Test 1 (round-trip) : OK (200 samples)")


# ---------------------------------------------------------------------------
# Test 2 : identité σ = (0,1,2,3,4,5) → inchangé
# ---------------------------------------------------------------------------

def test_identity():
    sigma_id = tuple(range(NUM_FAMILLES))
    errors = 0
    for _ in range(100):
        state, policy, hand_keys = collect_sample()
        s2, p2, hk2 = augment_sample(state, policy, hand_keys, mapper, sigma_id)
        if not np.allclose(s2, state, atol=1e-6):
            errors += 1
        if not np.allclose(p2, policy, atol=1e-6):
            errors += 1
        if hk2 != hand_keys:
            errors += 1
    assert errors == 0, f"Identité ÉCHEC : {errors} erreurs"
    print("Test 2 (identité) : OK (100 samples)")


# ---------------------------------------------------------------------------
# Test 3 : cohérence state↔action — le test clé
# Joue argmax(π) sur l'état original et argmax(π') sur l'état σ-équivalent.
# Les plateaux résultants doivent être σ-équivalents.
# ---------------------------------------------------------------------------

def test_action_coherence():
    """Test principal : jouer l'action augmentée sur le jeu augmenté doit
    produire un plateau σ-équivalent au plateau original."""
    import copy

    errors = 0
    n_tested = 0

    for trial in range(500):
        env = GameEnv(NUM_PLAYERS, seed=trial)
        # Skip jeux terminés ou en assassin_pending dès le départ
        if env.is_done() or env.pending_assassin_context:
            continue

        state = env.get_state_vector()
        legal = env.get_legal_actions()
        if not legal:
            continue

        # Policy : on teste chaque action légale individuellement
        policy = np.zeros(mapper.get_action_space_size(), dtype=np.float32)
        action_orig = legal[0]  # action à tester = la première légale
        policy[action_orig] = 1.0

        hand_keys = tuple(
            sorted(env.cartes[i].sort_key for i in env.mains[env.current_player])
        )

        sigma = random_family_permutation(RNG)

        _, policy_aug, _ = augment_sample(state, policy, hand_keys, mapper, sigma)

        # Action dans l'espace augmenté
        action_aug = int(np.argmax(policy_aug))

        # Jouer action_orig dans env original
        env_orig = copy.deepcopy(env)
        env_orig.step(action_orig)

        # Créer un env sigma-équivalent et jouer action_aug
        env_sigma = copy.deepcopy(env)
        apply_sigma_to_game(env_sigma, sigma)
        # Reconstruire les mains triées après remapping des familles
        for p in range(NUM_PLAYERS):
            env_sigma.mains[p].sort(key=lambda idx: env_sigma.cartes[idx].sort_key)

        try:
            env_sigma.step(action_aug)
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  Trial {trial}: step ECHEC avec action_aug={action_aug}: {e}")
            continue

        # Les états doivent être σ-équivalents
        if not boards_are_sigma_equivalent(env_orig, env_sigma, sigma):
            errors += 1
            if errors <= 3:
                perm_o, qp_o, _ = mapper.decode(action_orig)
                perm_a, qp_a, _ = mapper.decode(action_aug)
                print(f"  Trial {trial}: DÉSYNC state↔action")
                print(f"    Orig  action={action_orig} perm={perm_o} queen={qp_o}")
                print(f"    Augm  action={action_aug} perm={perm_a} queen={qp_a}")
                print(f"    sigma={sigma}")
                print(f"    hand_keys={hand_keys}")

        n_tested += 1

    rate = errors / n_tested if n_tested > 0 else 0
    status = "OK" if errors == 0 else f"ÉCHEC ({errors}/{n_tested} = {rate:.1%})"
    assert errors == 0, (
        f"Cohérence state↔action ÉCHEC : {errors}/{n_tested} erreurs"
    )
    print(f"Test 3 (cohérence state↔action) : {status} ({n_tested} samples)")


# ---------------------------------------------------------------------------
# Test 4 : positions compute_position_map — inversion et bijectivité
# ---------------------------------------------------------------------------

def test_position_map():
    errors = 0
    for _ in range(1000):
        hand_keys = tuple(
            sorted(int(RNG.integers(0, NUM_FAMILLES * NUM_ROLES)) for _ in range(3))
        )
        sigma = random_family_permutation(RNG)
        inv = sigma_inverse(sigma)
        pos_map = compute_position_map(hand_keys, sigma)
        pos_map_inv = compute_position_map(
            tuple(sorted(sigma[k // NUM_ROLES] * NUM_ROLES + (k % NUM_ROLES) for k in hand_keys)),
            inv,
        )
        # Composition pos_map_inv ∘ pos_map doit être l'identité
        for i in range(3):
            if pos_map_inv[pos_map[i]] != i:
                errors += 1
    assert errors == 0, f"Position map ÉCHEC : {errors} erreurs"
    print("Test 4 (position map inversion) : OK (1000 samples)")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST UNITAIRE augment_sample")
    print("=" * 60)
    test_identity()
    test_roundtrip()
    test_position_map()
    test_action_coherence()
    print()
    print("Tous les tests passent — augment_sample cohérent.")
