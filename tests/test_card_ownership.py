"""Tests des règles d'identité et de mémoire des espions.

Couvre :
  - `Carte.proprietaire_idx` est correctement défini après `step()` pour les
    3 cartes (y compris celle posée chez la Reine et celle posée chez l'adv).
  - Un espion posé chez la Reine reste face cachée (`visible == False`).
  - `_knows_identity` reflète "je vois cette carte" (visible OU posée par moi).
  - `_randomize_unseen` ne touche pas aux espions posés par le joueur courant.
  - Un espion posé par l'adversaire chez la Reine est bien randomisé par PIMC.
"""

from app.jeu import GameEnv, Role


def _play_one_action(env: GameEnv, action_idx: int = 0) -> None:
    """Joue une action et résout les éventuels assassins en attente."""
    _, _, _, info = env.step(action_idx)
    while info.get("assassin_pending"):
        ctx = env.pending_assassin_context
        v = ctx["targets"][0] if ctx and ctx["targets"] else None
        _, _, _, info = env.resolve_assassin_manual(v)


def _swap_into_hand(env: GameEnv, target_card_id: int, hand_slot: int = 0) -> None:
    """Échange proprement une carte de la main du joueur courant avec une
    carte spécifique du deck. Garantit qu'aucun id n'est dupliqué entre
    main et deck."""
    cp = env.current_player
    if target_card_id in env.deck_indices:
        old = env.mains[cp][hand_slot]
        deck_pos = env.deck_indices.index(target_card_id)
        env.deck_indices[deck_pos] = old
        env.mains[cp][hand_slot] = target_card_id
        env.mains[cp].sort(key=lambda i: env.cartes[i].sort_key)


def test_proprietaire_idx_set_after_step() -> None:
    """Les 3 cartes jouées ce tour doivent avoir proprietaire_idx == current_player,
    y compris la carte chez la Reine (auparavant -1) et celle chez l'adversaire."""
    env = GameEnv(2, seed=42)
    hand_before = list(env.mains[env.current_player])
    cp = env.current_player
    _play_one_action(env, 0)
    for card_id in hand_before:
        c = env.cartes[card_id]
        assert c.proprietaire_idx == cp, (
            f"Carte {card_id} ({c}) — proprietaire_idx attendu {cp}, vu {c.proprietaire_idx}"
        )


def test_proprietaire_idx_does_not_drive_scoring() -> None:
    """Le scoring ne doit s'appuyer que sur `domaine_id` et `position` —
    `proprietaire_idx` est ignoré côté décompte des points.

    On vérifie en jouant une partie complète : modifier `proprietaire_idx`
    après coup ne doit pas changer le score.
    """
    env = GameEnv(2, seed=42)
    import random as _r
    rng = _r.Random(0)
    while not env.is_done():
        actions = env.get_legal_actions()
        if not actions:
            break
        _play_one_action(env, rng.choice(actions))

    scores_before = dict(env._calcul_scores())
    # On vandalise proprietaire_idx sur toutes les cartes.
    for c in env.cartes:
        c.proprietaire_idx = -42
    scores_after = dict(env._calcul_scores())
    assert scores_before == scores_after, (
        f"Le scoring dépend de proprietaire_idx ! avant={scores_before} après={scores_after}"
    )


def test_spy_at_queen_stays_hidden() -> None:
    """Un espion posé chez la Reine doit avoir `visible == False` et
    `proprietaire_idx == celui qui l'a posé`."""
    env = GameEnv(2, seed=42)
    spy_id = next(
        i for i, c in enumerate(env.cartes)
        if c.role == Role.ESPION and i in env.deck_indices
    )
    _swap_into_hand(env, spy_id, hand_slot=0)
    spy_pos = env.mains[0].index(spy_id)
    rest = [i for i in range(3) if i != spy_pos]
    perm = (spy_pos, rest[0], rest[1])
    action = env.mapper.encode(perm, "Estime", target_relative_idx=0)
    _play_one_action(env, action)

    spy = env.cartes[spy_id]
    assert spy.position == "Estime"
    assert spy.visible is False, "L'espion chez la Reine doit rester face cachée"
    assert spy.proprietaire_idx == 0
    assert spy.domaine_id == -1  # chez la Reine, pas dans un domaine


def test_knows_identity_for_own_hidden_spy() -> None:
    """Un espion face cachée posé par moi est 'connu' (j'en connais l'identité)."""
    env = GameEnv(2, seed=42)
    spy_id = next(
        i for i, c in enumerate(env.cartes)
        if c.role == Role.ESPION and i in env.deck_indices
    )
    _swap_into_hand(env, spy_id, hand_slot=0)
    spy_pos = env.mains[0].index(spy_id)
    rest = [i for i in range(3) if i != spy_pos]
    perm = (rest[0], spy_pos, rest[1])  # spy chez Soi
    action = env.mapper.encode(perm, "Estime", target_relative_idx=0)
    _play_one_action(env, action)

    spy = env.cartes[spy_id]
    assert spy.proprietaire_idx == 0
    assert not spy.visible

    env.current_player = 0
    assert env._knows_identity(spy) is True


def test_pimc_does_not_randomize_own_placed_spies() -> None:
    """L'espion posé par le joueur courant ne doit jamais voir son identité
    changée par la randomisation PIMC, peu importe la zone (Reine ici)."""
    env = GameEnv(2, seed=42)
    spy_id = next(
        i for i, c in enumerate(env.cartes)
        if c.role == Role.ESPION and i in env.deck_indices
    )
    _swap_into_hand(env, spy_id, hand_slot=0)
    spy_pos = env.mains[0].index(spy_id)
    rest = [i for i in range(3) if i != spy_pos]
    perm = (spy_pos, rest[0], rest[1])  # spy chez la Reine
    action = env.mapper.encode(perm, "Estime", target_relative_idx=0)
    _play_one_action(env, action)

    env.current_player = 0
    original_fam = env.cartes[spy_id].famille
    original_role = env.cartes[spy_id].role

    for _ in range(20):
        clone = env.clone_determinized(randomize=True)
        assert clone.cartes[spy_id].famille == original_fam
        assert clone.cartes[spy_id].role == original_role


def test_pimc_can_randomize_opponent_placed_spy_at_queen() -> None:
    """Un espion posé par l'adversaire chez la Reine doit pouvoir être
    randomisé pour la perspective du joueur courant — son rôle reste
    ESPION (contrainte), mais sa famille doit varier."""
    env = GameEnv(2, seed=42)
    spy = next(c for c in env.cartes if c.role == Role.ESPION)
    spy.position = "Disgrace"
    spy.visible = False
    spy.proprietaire_idx = 1  # adversaire
    spy.domaine_id = -1
    env.plateau_indices.append(spy.id)

    env.current_player = 0
    seen_families = set()
    for _ in range(30):
        clone = env.clone_determinized(randomize=True)
        assert clone.cartes[spy.id].role == Role.ESPION
        seen_families.add(clone.cartes[spy.id].famille)
    assert len(seen_families) > 1, (
        f"PIMC n'a vu qu'une famille sur 30 tirages : {seen_families}"
    )
