"""Augmentation de données par symétrie des familles (L2 #2.2).

Les 6 familles de Courtisans sont **interchangeables** : aucune règle ne
distingue la famille rouge de la bleue. On peut donc générer 6! = 720 variantes
strategiquement équivalentes pour chaque sample du replay buffer.

Subtilité : l'action encode la position d'une carte dans la **main triée** par
`sort_key = famille * NUM_ROLES + role`. Permuter les familles change
les sort_keys, donc l'ordre des cartes en main, donc la signification de
"position 0" / "position 1" / "position 2" dans la permutation d'action.

Ce module fournit :
  - `permute_state_vec` : permute les blocs de famille dans le state vector.
  - `compute_position_map` : à partir des keys de la main, calcule le mapping
    (ancienne_position → nouvelle_position) sous une permutation σ.
  - `permute_policy` : applique le mapping à un vecteur de policy.
  - `augment_sample` : raccourci pour appliquer σ aléatoire à un sample complet.
"""

from __future__ import annotations

import numpy as np

from app.jeu import NUM_CARD_TYPES, NUM_FAMILLES, NUM_ROLES, ActionMapper


def random_family_permutation(rng: np.random.Generator | None = None) -> tuple[int, ...]:
    """Tire une permutation aléatoire de {0..NUM_FAMILLES-1}."""
    if rng is None:
        rng = np.random.default_rng()
    return tuple(int(x) for x in rng.permutation(NUM_FAMILLES))


def permute_state_vec(
    state_vec: np.ndarray,
    sigma: tuple[int, ...],
    permutable_size: int | None = None,
) -> np.ndarray:
    """Permute les blocs de famille dans le state vector.

    `sigma[i] = j` signifie « la famille i devient j » (la valeur stockée en
    cellule de famille i passe en cellule de famille j, dans chaque zone).

    Le vecteur d'état contient :
      - une section permutable de `permutable_size` cellules, organisée en
        zones de `NUM_CARD_TYPES = 30` cellules, chaque zone étant 6 blocs
        famille × `NUM_ROLES = 5` rôles ;
      - une section non permutable (compteurs d'espions cachés par
        (zone, poseur) — invariants par symétrie de famille).

    Si `permutable_size` est None, on assume que tout le vecteur est
    permutable (rétro-compat).
    """
    assert len(sigma) == NUM_FAMILLES, f"sigma doit avoir {NUM_FAMILLES} éléments"
    assert sorted(sigma) == list(range(NUM_FAMILLES)), f"sigma doit être une permutation : {sigma}"

    if permutable_size is None:
        permutable_size = state_vec.size
    assert permutable_size % NUM_CARD_TYPES == 0, "permutable_size doit être un multiple de NUM_CARD_TYPES"
    assert permutable_size <= state_vec.size, "permutable_size dépasse la taille du vecteur"

    # Copie initiale : la section non permutable est conservée telle quelle.
    new_vec = state_vec.copy()

    num_zones = permutable_size // NUM_CARD_TYPES
    for z in range(num_zones):
        zone_offset = z * NUM_CARD_TYPES
        for i in range(NUM_FAMILLES):
            j = sigma[i]
            src = zone_offset + i * NUM_ROLES
            dst = zone_offset + j * NUM_ROLES
            new_vec[dst : dst + NUM_ROLES] = state_vec[src : src + NUM_ROLES]
    return new_vec


def permutable_state_size(num_players: int) -> int:
    """Taille de la section "identités par famille" (permutable par σ)
    du state vector. Doit rester synchronisée avec
    `GameEnv._permutable_section_size`.
    """
    total_zones = 2 + num_players + 1  # Estime + Disgrace + N domaines + main
    return total_zones * NUM_CARD_TYPES


def compute_position_map(
    hand_keys: tuple[int, int, int], sigma: tuple[int, ...]
) -> tuple[int, int, int]:
    """Calcule la table (ancienne_position → nouvelle_position) sous σ.

    `hand_keys` est un triplet d'entiers `famille * NUM_ROLES + role`,
    **trié par ordre croissant** (= ordre dans lequel les cartes apparaissent
    dans la main du moteur).

    Après permutation σ, la nouvelle sort_key d'une carte de (fam, role) est
    `σ(fam) * NUM_ROLES + role`. On re-trie les cartes selon ces nouvelles
    keys et on en déduit la nouvelle position de chaque carte initiale.
    """
    assert len(hand_keys) == 3
    new_keys = []
    for k in hand_keys:
        fam, role = divmod(k, NUM_ROLES)
        new_k = sigma[fam] * NUM_ROLES + role
        new_keys.append(new_k)

    # Stable sort des nouvelles keys, puis on retourne la position (rang) de
    # chaque carte initiale dans le nouvel ordre. argsort donne l'ordre des
    # indices originaux ; on l'inverse pour avoir position_originale -> rang.
    order = sorted(range(3), key=lambda i: new_keys[i])
    pos_map = [0, 0, 0]
    for new_pos, old_pos in enumerate(order):
        pos_map[old_pos] = new_pos
    return tuple(pos_map)  # type: ignore[return-value]


def permute_policy(
    policy: np.ndarray,
    pos_map: tuple[int, int, int],
    mapper: ActionMapper,
) -> np.ndarray:
    """Permute le vecteur de policy en suivant le mapping de positions.

    Pour chaque action d'indice `a`, on décode `(perm, queen_pos, target)`,
    on remappe `perm` via `pos_map`, et on encode la nouvelle action :
    `new_policy[new_a] = policy[a]`.

    NB : si plusieurs cartes en main ont la même `sort_key` (cartes
    identiques), le mapping peut être ambigu. Le moteur de jeu utilise un
    tri stable, donc dans la pratique on garde la cohérence.
    """
    new_policy = np.zeros_like(policy)
    n = mapper.get_action_space_size()
    for a in range(n):
        if policy[a] == 0:
            continue
        perm, q, t = mapper.decode(a)
        new_perm = (pos_map[perm[0]], pos_map[perm[1]], pos_map[perm[2]])
        new_a = mapper.encode(new_perm, q, t)
        new_policy[new_a] = policy[a]
    return new_policy


def augment_sample(
    state_vec: np.ndarray,
    policy: np.ndarray,
    hand_keys: tuple[int, int, int],
    mapper: ActionMapper,
    sigma: tuple[int, ...] | None = None,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int]]:
    """Applique une permutation de familles (tirée au sort ou fournie) à un
    sample complet (state, policy, hand_keys). La valeur est inchangée — le
    score final ne dépend pas du nommage des familles.

    La section "compteurs d'espions cachés" du state_vector (en fin de
    vecteur) est invariante par σ et donc préservée à l'identique.
    """
    if sigma is None:
        sigma = random_family_permutation(rng)
    permutable_size = permutable_state_size(mapper.num_players)
    new_state = permute_state_vec(state_vec, sigma, permutable_size=permutable_size)
    pos_map = compute_position_map(hand_keys, sigma)
    new_policy = permute_policy(policy, pos_map, mapper)
    new_hand_keys = tuple(
        sorted(sigma[k // NUM_ROLES] * NUM_ROLES + (k % NUM_ROLES) for k in hand_keys)
    )
    return new_state, new_policy, new_hand_keys  # type: ignore[return-value]
