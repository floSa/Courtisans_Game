"""La machine a etats -- contrats que les suites de conformite ne verifient pas.

Les 18 tests de conformite et les 11 invariants verifient que le moteur **joue le jeu**.
Ce fichier verifie ce qu'ils traversent sans le regarder : la forme des valeurs rendues,
l'independance d'un clone, le refus d'une action illegale, et **l'ordre de resolution des
Assassins**, qui est une regle du paragraphe 3.2 sans test de conformite dedie.

Deux d'entre eux existent parce qu'un decalage d'indice y passerait inapercu a 3 joueurs
et casserait a 4 : les cles de `scores()`, et le destinataire de la carte adverse.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from tests.outils import (
    RAPIDE_2J,
    RAPIDE_3J,
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    cle,
    construire,
    module,
    noms,
    paquet_ordonne,
    partie,
    scores_attendus,
)


def _pioche_avec_premiere_main(instance: Instance, voulues: list[Any]) -> list[Any]:
    """Une pioche dont les premieres cartes sont celles demandees (regle R-b)."""
    identites = {cle(carte) for carte in voulues}
    reste = [carte for carte in paquet_ordonne(instance) if cle(carte) not in identites]
    assert len(identites) == len(voulues), "cartes demandees en double"
    return [*voulues, *reste]


def _carte(instance: Instance, famille: int, nom_role: str, exemplaire: int = 0) -> Any:
    cards = module("cards")
    return cards.Carte(famille, getattr(cards.Role, nom_role), exemplaire)


# ---------------------------------------------------------------------------------
# Forme des valeurs rendues
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_les_cles_de_scores_sont_exactement_les_indices_de_joueur(
    instance: Instance,
) -> None:
    """Un decalage d'indice ici passe inapercu a 3 joueurs et casse a 4."""
    _, moteur = construire(instance)
    etat = partie(moteur, 0)

    scores = etat.scores()

    assert isinstance(scores, dict), f"scores() rend {type(scores).__name__}, pas un dict"
    assert sorted(scores) == list(range(instance.joueurs)), (
        f"{instance.nom} : cles {sorted(scores)} au lieu de {list(range(instance.joueurs))}"
    )
    assert all(isinstance(valeur, int) for valeur in scores.values())
    assert [scores[joueur] for joueur in range(instance.joueurs)] == scores_attendus(
        etat.vue_privilegiee(), instance
    )


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_les_scores_sont_disponibles_avant_la_fin(instance: Instance) -> None:
    """Le vecteur d'etat expose un score provisoire (paragraphe 4.2 de la specification) :
    il faut donc pouvoir le calculer avant le decompte final."""
    _, moteur = construire(instance)
    etat = moteur.reset(0)
    rng = random.Random(0)

    scores = etat.scores()
    assert sorted(scores) == list(range(instance.joueurs))
    assert all(valeur == 0 for valeur in scores.values()), (
        "avant la premiere pose, aucun joueur n'a de point"
    )

    for _ in range(3):
        if etat.is_terminal():
            break
        etat.apply(rng.choice(actions_legales(etat)))
    assert sorted(etat.scores()) == list(range(instance.joueurs))


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_l_etat_terminal_n_a_ni_joueur_ni_action(instance: Instance) -> None:
    _, moteur = construire(instance)
    etat = partie(moteur, 1)

    assert etat.is_terminal()
    assert etat.phase().name == "TERMINAL"
    assert list(etat.legal_actions()) == []
    assert etat.current_player() < 0, (
        "a l'etat terminal, current_player doit etre un identifiant reserve, pas un joueur"
    )

    with pytest.raises(Exception):  # noqa: B017 - le type exact n'est pas impose
        etat.apply(0)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_les_gains_sont_nuls_tant_que_la_partie_dure(instance: Instance) -> None:
    """Paragraphe 2.1 : rien n'est marque avant le decompte."""
    _, moteur = construire(instance)
    etat = moteur.reset(2)

    assert list(etat.returns()) == [0.0] * instance.joueurs


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_hors_ciblage_il_n_y_a_ni_assassin_en_cours_ni_cible(instance: Instance) -> None:
    """Contrat documente de l'API, que les suites de conformite ne verifient jamais :
    elles ecartent les etats qui ne sont pas en phase de ciblage avant de regarder."""
    _, moteur = construire(instance)
    etat = moteur.reset(4)

    assert etat.phase().name == "POSE"
    assert etat.assassin_en_resolution() is None
    assert etat.cibles_courantes() == ()

    termine = partie(moteur, 4)
    assert termine.assassin_en_resolution() is None
    assert termine.cibles_courantes() == ()


def test_une_action_illegale_est_refusee() -> None:
    _, moteur = construire(RAPIDE_3J)
    etat = moteur.reset(0)

    hors_espace = 10_000
    assert hors_espace not in etat.legal_actions()
    with pytest.raises(Exception):  # noqa: B017
        etat.apply(hors_espace)

    with pytest.raises(Exception):  # noqa: B017
        etat.apply(-1)


# ---------------------------------------------------------------------------------
# Le clone
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_un_clone_est_independant_de_son_original(instance: Instance) -> None:
    """Sans independance, toute recherche arborescente corrompt l'etat qu'elle explore."""
    _, moteur = construire(instance)
    etat = moteur.reset(3)
    clone = etat.clone()

    assert clone.phase().name == etat.phase().name
    assert clone.current_player() == etat.current_player()
    assert list(clone.legal_actions()) == list(etat.legal_actions())

    avant = etat.vue_privilegiee()
    cartes_avant = (
        [cle(c) for main in avant.mains for c in main],
        [cle(p.carte) for p in avant.posees],
        len(avant.pioche),
    )

    rng = random.Random(3)
    while not clone.is_terminal():
        clone.apply(rng.choice(actions_legales(clone)))

    apres = etat.vue_privilegiee()
    assert (
        [cle(c) for main in apres.mains for c in main],
        [cle(p.carte) for p in apres.posees],
        len(apres.pioche),
    ) == cartes_avant, "jouer le clone jusqu'au bout a modifie l'original"
    assert not etat.is_terminal()


# ---------------------------------------------------------------------------------
# L'ordre de resolution des Assassins -- paragraphe 3.2
# ---------------------------------------------------------------------------------


def test_les_assassins_se_resolvent_banquet_puis_domaine_propre_puis_adverse() -> None:
    """« Resolus dans l'ordre : banquet, puis son propre domaine, puis le domaine
    adverse. » Aucun test de conformite ne couvre cet ordre."""
    instance = RAPIDE_2J
    config, moteur = construire(instance)
    rules = module("rules")

    main = [
        _carte(instance, 0, "ASSASSIN"),
        _carte(instance, 1, "ASSASSIN"),
        _carte(instance, 2, "ASSASSIN"),
    ]
    etat = moteur.reset_depuis_pioche(_pioche_avec_premiere_main(instance, main))

    assert [cle(c) for c in etat.vue_privilegiee().mains[0]] == [
        (0, "ASSASSIN", 0),
        (1, "ASSASSIN", 0),
        (2, "ASSASSIN", 0),
    ]

    voulue = None
    for action in etat.legal_actions():
        pose = rules.decoder_action_pose(action, config)
        if pose.indices_main == (0, 1, 2):
            voulue = action
            break
    assert voulue is not None, "aucune action ne pose la main dans l'ordre (0, 1, 2)"

    etat.apply(voulue)

    familles_resolues = []
    zones_resolues = []
    while etat.phase().name == "CIBLAGE":
        assassin = etat.assassin_en_resolution()
        familles_resolues.append(assassin.carte.famille)
        zones_resolues.append(assassin.zone.genre.name)
        etat.apply(len(etat.cibles_courantes()))  # refus de tuer

    assert familles_resolues == [0, 1, 2], (
        f"ordre de resolution {familles_resolues} au lieu de banquet, domaine propre, "
        f"domaine adverse"
    )
    assert zones_resolues == ["BANQUET", "DOMAINE", "DOMAINE"]


def test_un_assassin_pose_ne_peut_pas_cibler_ses_compagnons_de_tour() -> None:
    """Consequence directe des trois zones distinctes (paragraphe 3.2)."""
    instance = RAPIDE_2J
    config, moteur = construire(instance)
    rules = module("rules")

    main = [
        _carte(instance, 0, "ASSASSIN"),
        _carte(instance, 1, "NOBLE"),
        _carte(instance, 2, "NOBLE"),
    ]
    etat = moteur.reset_depuis_pioche(_pioche_avec_premiere_main(instance, main))

    voulue = next(
        action
        for action in etat.legal_actions()
        if rules.decoder_action_pose(action, config).indices_main[0] == 0
    )
    etat.apply(voulue)

    assert etat.phase().name == "CIBLAGE"
    assert etat.assassin_en_resolution().carte.famille == 0
    assert etat.cibles_courantes() == (), (
        "l'Assassin du banquet cible une carte posee le meme tour, alors que les trois "
        "zones sont disjointes"
    )
    assert list(etat.legal_actions()) == [0], "seul le refus de tuer doit rester"

    etat.apply(0)
    assert etat.phase().name == "POSE"
    assert etat.current_player() == 1
