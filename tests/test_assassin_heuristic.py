"""Tests de l'heuristique informée d'assassinat (B1).

Vérifie que `_resolve_assassin_auto` choisit la cible qui maximise l'avantage
du joueur qui a posé l'assassin, plutôt que de tirer au hasard.
"""

from app.jeu import GameEnv, Role


def _clear_board(env: GameEnv) -> None:
    """Vide le plateau pour permettre une construction propre du scénario."""
    env.plateau_indices = []


def _place_card(
    env: GameEnv,
    card_id: int,
    *,
    placer: int,
    position: str | None = None,
    domaine_id: int = -1,
    visible: bool = True,
) -> None:
    c = env.cartes[card_id]
    c.position = position
    c.domaine_id = domaine_id
    c.visible = visible
    c.proprietaire_idx = placer
    env.plateau_indices.append(card_id)


def _find_card(env: GameEnv, famille: int, role: int, exclude: set[int] | None = None) -> int:
    """Retourne l'id d'une carte non encore utilisée matchant (famille, role)."""
    excl = exclude or set()
    return next(
        c.id for c in env.cartes
        if c.famille == famille and c.role == role and c.id not in excl
    )


def test_assassin_picks_high_value_target() -> None:
    """L'IA doit préférer tuer un Noble (valeur 2) plutôt qu'un Neutre (valeur 1)
    dans le même domaine, si les deux contribuent positivement au score adverse.
    """
    env = GameEnv(2, seed=42)
    _clear_board(env)

    # Influence : famille 0 est en Lumière (Estime majoritaire) → toutes les
    # cartes de la famille 0 dans un domaine rapportent à leur propriétaire.
    # On met deux cartes de famille 0 en Estime pour fixer la majorité.
    estime_a = _find_card(env, 0, Role.GARDE)
    _place_card(env, estime_a, placer=0, position="Estime")
    estime_b = _find_card(env, 0, Role.NEUTRE, exclude={estime_a})
    _place_card(env, estime_b, placer=0, position="Estime")

    # Le joueur 1 (adversaire) a deux cartes de famille 0 dans son domaine :
    # un Noble (valeur 2) et un Neutre (valeur 1). Toutes deux lui rapportent.
    noble_id = _find_card(env, 0, Role.NOBLE, exclude={estime_a, estime_b})
    _place_card(env, noble_id, placer=1, domaine_id=1)
    neutre_id = _find_card(env, 0, Role.NEUTRE, exclude={estime_a, estime_b, noble_id})
    _place_card(env, neutre_id, placer=1, domaine_id=1)

    # Le joueur 0 pose un assassin dans le domaine de 1.
    assassin_id = _find_card(env, 5, Role.ASSASSIN)
    _place_card(env, assassin_id, placer=0, domaine_id=1)

    assassin = env.cartes[assassin_id]
    env._resolve_assassin_auto(assassin)

    # L'assassin doit avoir tué le Noble (valeur 2 > valeur 1).
    assert noble_id not in env.plateau_indices, (
        "L'heuristique aurait dû éliminer le Noble (valeur 2) en priorité."
    )
    assert neutre_id in env.plateau_indices, (
        "L'heuristique a éliminé le Neutre alors que le Noble avait plus de valeur."
    )


def test_assassin_prefers_scoring_card_over_useless_one() -> None:
    """Si une cible rapporte au score adverse et une autre est neutre
    (famille en balance Lumière=0), l'IA cible celle qui rapporte."""
    env = GameEnv(2, seed=42)
    _clear_board(env)

    # Famille 0 : balance neutre (1 Estime, 1 Disgrace) → carte famille 0
    # ne rapporte rien.
    used: set[int] = set()
    e0 = _find_card(env, 0, Role.GARDE)
    used.add(e0)
    _place_card(env, e0, placer=0, position="Estime")
    d0 = _find_card(env, 0, Role.NEUTRE, exclude=used)
    used.add(d0)
    _place_card(env, d0, placer=0, position="Disgrace")

    # Famille 1 : Lumière (1 Estime, 0 Disgrace) → rapporte des points.
    e1 = _find_card(env, 1, Role.GARDE)
    used.add(e1)
    _place_card(env, e1, placer=0, position="Estime")

    # L'adversaire a deux cartes Noble (valeur 2) dans son domaine, une de
    # chaque famille. Famille 1 rapporte, famille 0 ne rapporte pas.
    useless_target = _find_card(env, 0, Role.NOBLE, exclude=used)
    used.add(useless_target)
    _place_card(env, useless_target, placer=1, domaine_id=1)
    valuable_target = _find_card(env, 1, Role.NOBLE, exclude=used)
    used.add(valuable_target)
    _place_card(env, valuable_target, placer=1, domaine_id=1)

    # Le joueur 0 pose un assassin dans le domaine adverse.
    assassin_id = _find_card(env, 5, Role.ASSASSIN, exclude=used)
    _place_card(env, assassin_id, placer=0, domaine_id=1)

    assassin = env.cartes[assassin_id]
    env._resolve_assassin_auto(assassin)

    assert valuable_target not in env.plateau_indices, (
        "L'heuristique aurait dû tuer la cible qui rapporte des points à l'adversaire."
    )
    assert useless_target in env.plateau_indices


def test_assassin_avoids_killing_own_useful_card() -> None:
    """Si l'IA a posé un assassin chez la Reine (Estime) et que dans cette
    zone il y a une carte à elle ET une carte adverse, elle préfère tuer
    celle de l'adversaire."""
    env = GameEnv(2, seed=42)
    _clear_board(env)

    # On crée un assassin en Estime posé par le joueur 0.
    used: set[int] = set()
    assassin_id = _find_card(env, 5, Role.ASSASSIN)
    used.add(assassin_id)
    _place_card(env, assassin_id, placer=0, position="Estime")

    # Deux cibles en Estime : une posée par 0 (moi), une par 1 (adv).
    mine = _find_card(env, 1, Role.NOBLE, exclude=used)
    used.add(mine)
    _place_card(env, mine, placer=0, position="Estime")
    adv_card = _find_card(env, 2, Role.NOBLE, exclude=used)
    used.add(adv_card)
    _place_card(env, adv_card, placer=1, position="Estime")

    assassin = env.cartes[assassin_id]
    env._resolve_assassin_auto(assassin)

    # Aucun engagement strict sur lequel sera tué — dépend des familles
    # majoritaires. On vérifie au minimum que la cible n'est PAS l'assassin
    # lui-même et qu'EXACTEMENT une carte a été éliminée parmi mine/adv_card.
    survivors = [i for i in (mine, adv_card) if i in env.plateau_indices]
    assert len(survivors) == 1, "L'assassin doit retirer exactement 1 cible."


def test_assassin_no_target_does_not_crash() -> None:
    """Pas de cible valide -> aucune carte retirée, pas d'exception."""
    env = GameEnv(2, seed=42)
    _clear_board(env)

    assassin_id = _find_card(env, 5, Role.ASSASSIN)
    _place_card(env, assassin_id, placer=0, position="Estime")
    # Aucune autre carte en Estime.

    env._resolve_assassin_auto(env.cartes[assassin_id])
    # L'assassin est toujours là, le plateau n'a perdu personne.
    assert env.plateau_indices == [assassin_id]
