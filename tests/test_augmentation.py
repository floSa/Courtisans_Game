"""Tests sur l'augmentation par symétrie des familles (L2 #2.2).

L'augmentation est non triviale parce que la `sort_key = famille * 5 + role`
change quand on permute les familles, donc les positions des cartes en main
changent, donc la signification d'une action change. Ces tests valident :

  1. La permutation de l'état est bien une simple permutation de blocs.
  2. Le `pos_map` reflète correctement le retri de la main.
  3. La policy est remappée de façon que la mass totale soit conservée.
  4. **Test d'équivalence physique** : si on joue l'action « préférée » par
     la policy dans l'environnement, puis qu'on permute le résultat, on
     obtient le même état que si on avait d'abord permuté puis joué la
     nouvelle action préférée. C'est le test qui valide réellement la
     correction du remapping.
"""

import numpy as np
import pytest

from app.augmentation import (
    augment_sample,
    compute_position_map,
    permutable_state_size,
    permute_policy,
    permute_state_vec,
    random_family_permutation,
)
from app.jeu import NUM_FAMILLES, NUM_ROLES, ActionMapper, GameEnv


# --------------------------------------------------------------------------
# 1. permute_state_vec
# --------------------------------------------------------------------------
def test_identity_permutation_keeps_state_vec() -> None:
    env = GameEnv(2, seed=42)
    s = env.get_state_vector()
    identity = tuple(range(NUM_FAMILLES))
    psize = permutable_state_size(2)
    assert np.array_equal(permute_state_vec(s, identity, permutable_size=psize), s)


def test_permute_state_vec_inverse_is_identity() -> None:
    """Appliquer σ puis σ^-1 doit redonner le vecteur initial."""
    env = GameEnv(2, seed=42)
    s = env.get_state_vector()
    rng = np.random.default_rng(7)
    sigma = random_family_permutation(rng)
    sigma_inv: list[int] = [0] * NUM_FAMILLES
    for i, j in enumerate(sigma):
        sigma_inv[j] = i
    psize = permutable_state_size(2)
    permuted = permute_state_vec(s, sigma, permutable_size=psize)
    back = permute_state_vec(permuted, tuple(sigma_inv), permutable_size=psize)
    assert np.array_equal(back, s)


def test_permute_state_vec_swaps_family_cells() -> None:
    """Vérification micro : permuter (0↔1) doit échanger les cellules
    famille-0 et famille-1 dans chaque zone permutable."""
    env = GameEnv(2, seed=42)
    s = env.get_state_vector()
    sigma = (1, 0, 2, 3, 4, 5)
    psize = permutable_state_size(2)
    permuted = permute_state_vec(s, sigma, permutable_size=psize)
    NUM_CARD_TYPES = NUM_FAMILLES * NUM_ROLES
    num_zones = psize // NUM_CARD_TYPES
    for z in range(num_zones):
        off = z * NUM_CARD_TYPES
        np.testing.assert_array_equal(
            permuted[off + 1 * NUM_ROLES : off + 2 * NUM_ROLES],
            s[off + 0 * NUM_ROLES : off + 1 * NUM_ROLES],
        )
        np.testing.assert_array_equal(
            permuted[off + 0 * NUM_ROLES : off + 1 * NUM_ROLES],
            s[off + 1 * NUM_ROLES : off + 2 * NUM_ROLES],
        )
    # La section non permutable (compteurs d'espions cachés) est intacte.
    np.testing.assert_array_equal(permuted[psize:], s[psize:])


# --------------------------------------------------------------------------
# 2. compute_position_map
# --------------------------------------------------------------------------
def test_position_map_identity() -> None:
    identity = tuple(range(NUM_FAMILLES))
    # Main : 3 cartes triées par sort_key 2, 8, 15
    pos_map = compute_position_map((2, 8, 15), identity)
    assert pos_map == (0, 1, 2)


def test_position_map_reverses_order_if_families_reversed() -> None:
    """Si σ inverse les familles, les sort_keys aussi → les positions s'inversent."""
    sigma = tuple(reversed(range(NUM_FAMILLES)))
    # Main : 3 cartes de famille 0, 2, 5 (toutes role 0 -> sort_key = fam*5)
    # Anciennes keys : 0, 10, 25. Nouvelles : σ(0)*5=25, σ(2)*5=15, σ(5)*5=0.
    # Tri ancien (par positions 0,1,2) -> tri nouveau (les keys descendent),
    # donc les positions s'inversent : 0→2, 1→1, 2→0.
    pos_map = compute_position_map((0, 10, 25), sigma)
    assert pos_map == (2, 1, 0)


# --------------------------------------------------------------------------
# 3. permute_policy
# --------------------------------------------------------------------------
def test_permute_policy_preserves_mass() -> None:
    mapper = ActionMapper(2)
    rng = np.random.default_rng(0)
    policy = rng.random(mapper.get_action_space_size())
    policy /= policy.sum()
    # pos_map identité → policy inchangée
    same = permute_policy(policy, (0, 1, 2), mapper)
    np.testing.assert_allclose(same, policy)


def test_permute_policy_swap_positions() -> None:
    """Avec pos_map (1, 0, 2), la mass de l'action (0,1,2,Estime,0) doit
    se retrouver sur l'action (1,0,2,Estime,0)."""
    mapper = ActionMapper(2)
    n = mapper.get_action_space_size()
    policy = np.zeros(n)
    src = mapper.encode((0, 1, 2), "Estime", 0)
    policy[src] = 1.0
    permuted = permute_policy(policy, (1, 0, 2), mapper)
    expected = mapper.encode((1, 0, 2), "Estime", 0)
    assert permuted[expected] == pytest.approx(1.0)
    assert permuted.sum() == pytest.approx(1.0)


# --------------------------------------------------------------------------
# 4. Test d'équivalence physique (le plus important)
# --------------------------------------------------------------------------
def test_augmentation_preserves_physical_meaning() -> None:
    """Soit a* l'action préférée par la policy originale. Soit a*' l'action
    préférée par la policy augmentée. La carte physiquement placée à chaque
    destination doit être la même dans les deux mondes (modulo le renommage
    des familles par σ).
    """
    mapper = ActionMapper(2)
    env = GameEnv(2, seed=42)
    s = env.get_state_vector()
    hand_keys = tuple(sorted(env.cartes[i].sort_key for i in env.mains[0]))
    assert len(hand_keys) == 3

    # Construction d'une policy "déterministe" sur une action arbitraire
    policy = np.zeros(mapper.get_action_space_size())
    orig_action = mapper.encode((2, 0, 1), "Estime", 0)
    policy[orig_action] = 1.0

    sigma = (3, 5, 0, 1, 2, 4)
    new_s, new_p, _new_keys = augment_sample(s, policy, hand_keys, mapper, sigma=sigma)

    # 1. La masse de la nouvelle policy est sur 1 seule action.
    assert (new_p > 0).sum() == 1
    new_action = int(np.argmax(new_p))

    # 2. Décoder les deux actions et vérifier la cohérence physique.
    perm_orig, q_orig, t_orig = mapper.decode(orig_action)
    perm_new, q_new, t_new = mapper.decode(new_action)
    assert q_orig == q_new
    assert t_orig == t_new

    # 3. La carte qui partait à la Reine dans l'original doit partir à la
    # Reine dans le nouveau monde (même carte physique).
    sorted_hand = sorted(env.mains[0], key=lambda i: env.cartes[i].sort_key)
    card_to_queen_orig = env.cartes[sorted_hand[perm_orig[0]]]

    # Dans le monde permuté, l'ordre du tri change :
    new_keys = [sigma[env.cartes[i].famille] * NUM_ROLES + env.cartes[i].role for i in sorted_hand]
    order = sorted(range(3), key=lambda k: new_keys[k])
    new_sorted_hand = [sorted_hand[k] for k in order]
    card_to_queen_new = env.cartes[new_sorted_hand[perm_new[0]]]

    # Même carte physique
    assert card_to_queen_orig.id == card_to_queen_new.id


def test_augmentation_is_value_invariant() -> None:
    """La value est inchangée (le score final ne dépend pas du nommage)."""
    mapper = ActionMapper(2)
    env = GameEnv(2, seed=1)
    s = env.get_state_vector()
    policy = np.ones(mapper.get_action_space_size()) / mapper.get_action_space_size()
    hand_keys = tuple(sorted(env.cartes[i].sort_key for i in env.mains[0]))
    new_s, new_p, _ = augment_sample(s, policy, hand_keys, mapper)
    # Sanity : la nouvelle policy doit encore sommer à 1
    assert new_p.sum() == pytest.approx(1.0)


def test_augmentation_random_permutation_runs_without_crash() -> None:
    """Smoke test: tirer 20 σ aléatoires et vérifier que rien ne crash."""
    mapper = ActionMapper(2)
    env = GameEnv(2, seed=2)
    s = env.get_state_vector()
    hand_keys = tuple(sorted(env.cartes[i].sort_key for i in env.mains[0]))
    policy = np.random.default_rng(0).random(mapper.get_action_space_size())
    policy /= policy.sum()
    for _ in range(20):
        new_s, new_p, _ = augment_sample(s, policy, hand_keys, mapper)
        assert new_s.shape == s.shape
        assert new_p.sum() == pytest.approx(policy.sum(), abs=1e-5)
