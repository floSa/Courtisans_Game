"""Fonctions pures de `rules.py` -- 01_regles.md paragraphes 3.2, 3.4, 4.1 et 5.

Ces tests sont ecrits avant `rules.py`. Ils portent sur les fonctions que le moteur
appellera, prises isolement : ce que les tests de conformite verifient a travers une partie
entiere, ceux-ci le verifient sur un cas construit a la main, ou l'attendu est calculable
de tete.

**Le piege de cette etape a son propre bloc.** L'influence se compte en VALEUR, pas en
nombre de cartes : un Noble pese 2, tous les autres roles pesent 1, au banquet comme dans
les domaines. Une famille peut avoir autant de cartes de chaque cote et n'etre pas
Indifferente. Tous les attendus du bloc « influence » sont ecrits en valeur, a la main,
depuis le paragraphe 5.1.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.outils import (
    COMPLET_3J,
    RAPIDE_2J,
    TOUTES_LES_INSTANCES,
    Instance,
    cle,
    construire_config,
    module,
    noms,
    role,
)


def _carte(famille: int, nom_role: str, exemplaire: int = 0) -> Any:
    return module("cards").Carte(famille, role(nom_role), exemplaire)


def _banquet(position: str) -> Any:
    cards = module("cards")
    return cards.Zone.banquet(getattr(cards.Position, position))


def _domaine(proprietaire: int) -> Any:
    return module("cards").Zone.domaine(proprietaire)


def _posee(carte: Any, zone: Any, poseur: int = 0) -> Any:
    return module("cards").CartePosee(carte, zone, poseur)


# ---------------------------------------------------------------------------------
# Le paquet et la main
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_le_paquet_est_exactement_familles_x_roles_x_exemplaires(instance: Instance) -> None:
    rules = module("rules")
    config = construire_config(instance)

    paquet = rules.paquet(config)
    identites = [cle(carte) for carte in paquet]

    assert len(paquet) == instance.nb_cartes
    assert len(set(identites)) == len(identites), "une carte figure deux fois dans le paquet"
    assert sorted(identites) == sorted(
        (famille, nom_role, exemplaire)
        for famille in range(instance.familles)
        for nom_role in instance.roles
        for exemplaire in range(instance.exemplaires)
    )
    assert identites == [cle(carte) for carte in rules.paquet(config)], (
        "deux appels donnent deux paquets : l'ordre n'est pas deterministe"
    )


def test_la_main_canonique_est_triee_par_famille_puis_role() -> None:
    """03_specification_moteur.md paragraphe 4.2 : sans cet ordre, une meme action de pose
    designe des cartes differentes selon l'etat."""
    rules = module("rules")
    desordre = [
        _carte(2, "ASSASSIN"),
        _carte(0, "NEUTRE"),
        _carte(0, "ASSASSIN"),
    ]

    triee = rules.main_canonique(desordre)

    assert [cle(carte) for carte in triee] == [
        (0, "ASSASSIN", 0),
        (0, "NEUTRE", 0),
        (2, "ASSASSIN", 0),
    ]
    assert [cle(c) for c in rules.main_canonique(triee)] == [cle(c) for c in triee], (
        "le tri n'est pas idempotent"
    )


def test_la_main_canonique_ordonne_deux_cartes_identiques_de_facon_stable() -> None:
    """Deux exemplaires du meme couple (famille, role) doivent tomber dans un ordre fixe,
    sinon `reset(seed)` cesse d'etre reproductible (invariant I10)."""
    rules = module("rules")
    paire = [_carte(1, "NOBLE", 1), _carte(1, "NOBLE", 0)]

    assert [cle(c) for c in rules.main_canonique(paire)] == [
        (1, "NOBLE", 0),
        (1, "NOBLE", 1),
    ]


# ---------------------------------------------------------------------------------
# Les actions de pose
# ---------------------------------------------------------------------------------


def _contenus(main: list[Any], legales: list[int], config: Any) -> set[tuple]:
    """Ce que chaque action pose vraiment, a l'exemplaire pres.

    Deux cartes de meme famille et de meme role sont interchangeables : meme valeur, meme
    visibilite, meme effet. Les distinguer par leur exemplaire ferait passer pour deux
    coups differents deux coups qui donnent le meme etat.
    """
    rules = module("rules")
    contenus = set()
    for action in legales:
        pose = rules.decoder_action_pose(action, config)
        contenus.add(
            (
                tuple((main[i].famille, main[i].role.name) for i in pose.indices_main),
                pose.position,
                pose.adversaire_relatif,
            )
        )
    return contenus


def test_une_main_de_trois_cartes_distinctes_ouvre_toutes_les_actions() -> None:
    rules = module("rules")
    config = construire_config(RAPIDE_2J)
    main = rules.main_canonique(
        [_carte(0, "NOBLE"), _carte(1, "ESPION"), _carte(2, "ASSASSIN")]
    )

    legales = list(rules.actions_de_pose_legales(main, config))

    assert sorted(legales) == list(range(config.actions_de_pose))
    assert len(legales) == RAPIDE_2J.actions_de_pose == 6 * 2 * 1


def test_deux_cartes_interchangeables_masquent_la_moitie_des_assignations() -> None:
    """03_specification_moteur.md paragraphe 4.2 : les actions dupliquees sont masquees,
    sinon le test C14 echoue. Deux cartes de meme famille et meme role ramenent les 6
    permutations a 3."""
    rules = module("rules")
    config = construire_config(RAPIDE_2J)
    main = rules.main_canonique(
        [_carte(1, "NOBLE", 0), _carte(1, "NOBLE", 1), _carte(2, "ASSASSIN")]
    )

    legales = list(rules.actions_de_pose_legales(main, config))

    assert len(legales) == 3 * 2 * (RAPIDE_2J.joueurs - 1)
    assert len(_contenus(main, legales, config)) == len(legales), (
        "deux actions legales posent la meme chose"
    )


def test_trois_cartes_interchangeables_ne_laissent_qu_une_assignation() -> None:
    rules = module("rules")
    config = construire_config(COMPLET_3J)
    main = rules.main_canonique(
        [_carte(1, "NOBLE", 0), _carte(1, "NOBLE", 1), _carte(1, "NOBLE", 2)]
    )

    legales = list(rules.actions_de_pose_legales(main, config))

    assert len(legales) == 1 * 2 * (COMPLET_3J.joueurs - 1)
    assert len(_contenus(main, legales, config)) == len(legales)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_le_destinataire_est_toujours_un_adversaire(instance: Instance) -> None:
    """Indexation relative : moi, le suivant, celui d'apres (paragraphe 4.2 de la spec)."""
    rules = module("rules")

    for joueur in range(instance.joueurs):
        cibles = [
            rules.destinataire(joueur, relatif, instance.joueurs)
            for relatif in range(instance.joueurs - 1)
        ]
        assert joueur not in cibles, "un joueur peut se designer lui-meme comme adversaire"
        assert sorted(cibles) == sorted(
            autre for autre in range(instance.joueurs) if autre != joueur
        ), "les adversaires relatifs ne couvrent pas exactement les autres joueurs"


def test_le_destinataire_suit_l_ordre_de_la_table() -> None:
    rules = module("rules")

    assert rules.destinataire(0, 0, 3) == 1
    assert rules.destinataire(0, 1, 3) == 2
    assert rules.destinataire(2, 0, 3) == 0
    assert rules.destinataire(2, 1, 3) == 1
    assert rules.destinataire(1, 0, 2) == 0


# ---------------------------------------------------------------------------------
# Les cibles de l'Assassin -- paragraphe 4.1
# ---------------------------------------------------------------------------------


def test_les_cibles_excluent_le_garde_l_assassin_lui_meme_et_les_autres_zones() -> None:
    rules = module("rules")
    zone = _banquet("ESTIME")
    ailleurs = _banquet("DISGRACE")

    assassin = _posee(_carte(0, "ASSASSIN", 0), zone, poseur=0)
    garde = _posee(_carte(1, "GARDE"), zone, poseur=1)
    autre_assassin = _posee(_carte(2, "ASSASSIN", 1), zone, poseur=1)
    espion = _posee(_carte(3, "ESPION"), zone, poseur=1)
    noble = _posee(_carte(0, "NOBLE"), zone, poseur=2)
    hors_zone = _posee(_carte(0, "NEUTRE"), ailleurs, poseur=1)

    cibles = rules.cibles_valides(
        [assassin, garde, autre_assassin, espion, noble, hors_zone], assassin
    )

    assert sorted(cle(c.carte) for c in cibles) == sorted(
        cle(c.carte) for c in (autre_assassin, espion, noble)
    )


def test_un_assassin_seul_dans_sa_zone_n_a_aucune_cible() -> None:
    rules = module("rules")
    zone = _domaine(1)
    assassin = _posee(_carte(0, "ASSASSIN"), zone, poseur=0)
    garde = _posee(_carte(1, "GARDE"), zone, poseur=1)

    assert rules.cibles_valides([assassin, garde], assassin) == ()


def test_deux_assassins_de_la_meme_zone_se_ciblent_l_un_l_autre() -> None:
    rules = module("rules")
    zone = _domaine(0)
    premier = _posee(_carte(0, "ASSASSIN", 0), zone, poseur=0)
    second = _posee(_carte(0, "ASSASSIN", 1), zone, poseur=1)

    assert [cle(c.carte) for c in rules.cibles_valides([premier, second], premier)] == [
        cle(second.carte)
    ]
    assert [cle(c.carte) for c in rules.cibles_valides([premier, second], second)] == [
        cle(premier.carte)
    ]


# ---------------------------------------------------------------------------------
# L'influence -- paragraphe 5.1. TOUT SE COMPTE EN VALEUR.
# ---------------------------------------------------------------------------------

#: (intitule, cartes au banquet en (famille, role, position), influence attendue de la
#: famille 0, statut attendu). Ecrits a la main depuis les paragraphes 2.2 et 5.1.
CAS_INFLUENCE: list[tuple[str, list[tuple[int, str, str]], int, str]] = [
    (
        "deux Nobles en Estime contre deux cartes standard en Disgrace",
        [(0, "NOBLE", "ESTIME"), (0, "NOBLE", "ESTIME"),
         (0, "NEUTRE", "DISGRACE"), (0, "ESPION", "DISGRACE")],
        2,  # 2 + 2 - 1 - 1
        "LUMIERE",
    ),
    (
        "un Noble en Disgrace contre une carte standard en Estime",
        [(0, "NOBLE", "DISGRACE"), (0, "NEUTRE", "ESTIME")],
        -1,  # 1 - 2
        "OBSCURITE",
    ),
    (
        "un Noble de chaque cote",
        [(0, "NOBLE", "ESTIME"), (0, "NOBLE", "DISGRACE")],
        0,
        "INDIFFERENTE",
    ),
    (
        "un Noble en Estime contre deux cartes standard en Disgrace",
        [(0, "NOBLE", "ESTIME"), (0, "NEUTRE", "DISGRACE"), (0, "GARDE", "DISGRACE")],
        0,  # 2 - 1 - 1
        "INDIFFERENTE",
    ),
    (
        "marge de 1, une carte standard annule",
        [(0, "NEUTRE", "ESTIME"), (0, "ASSASSIN", "ESTIME"), (0, "GARDE", "DISGRACE")],
        1,  # 1 + 1 - 1
        "LUMIERE",
    ),
    (
        "marge de 1, un Noble inverse",
        [(0, "NEUTRE", "ESTIME"), (0, "ASSASSIN", "ESTIME"), (0, "NOBLE", "DISGRACE")],
        0,  # 1 + 1 - 2
        "INDIFFERENTE",
    ),
    (
        "aucune carte de la famille au banquet",
        [(1, "NOBLE", "ESTIME")],
        0,
        "INDIFFERENTE",
    ),
]
IDS_INFLUENCE = [intitule for intitule, _, _, _ in CAS_INFLUENCE]


@pytest.mark.parametrize(
    ("intitule", "cartes", "attendue", "statut"), CAS_INFLUENCE, ids=IDS_INFLUENCE
)
def test_l_influence_se_compte_en_valeur(
    intitule: str, cartes: list[tuple[int, str, str]], attendue: int, statut: str
) -> None:
    rules = module("rules")
    posees = [
        _posee(_carte(famille, nom_role, exemplaire), _banquet(position))
        for exemplaire, (famille, nom_role, position) in enumerate(cartes)
    ]

    influence = rules.influence(posees, familles=2)
    statuts = rules.statuts(posees, familles=2)

    assert influence[0] == attendue, (
        f"{intitule} : influence {influence[0]} au lieu de {attendue} -- "
        f"le Noble pese 2, tous les autres 1"
    )
    assert statuts[0].name == statut
    assert int(statuts[0]) == (1 if attendue >= 1 else (-1 if attendue <= -1 else 0))


def test_une_carte_de_domaine_ne_change_pas_l_influence() -> None:
    """Seul le banquet determine le statut d'une famille (paragraphe 5, point 5)."""
    rules = module("rules")
    posees = [
        _posee(_carte(0, "NOBLE", 0), _banquet("ESTIME")),
        _posee(_carte(0, "NOBLE", 1), _domaine(0)),
        _posee(_carte(0, "NOBLE", 2), _domaine(1)),
    ]

    assert rules.influence(posees, familles=2)[0] == 2


# ---------------------------------------------------------------------------------
# Les points -- paragraphe 5, points 2, 3 et 5
# ---------------------------------------------------------------------------------


def test_les_points_vont_au_proprietaire_et_valent_la_valeur_de_la_carte() -> None:
    rules = module("rules")
    lumiere = {0: rules.Statut.LUMIERE, 1: rules.Statut.OBSCURITE, 2: rules.Statut.INDIFFERENTE}
    posees = [
        _posee(_carte(0, "NOBLE"), _domaine(1), poseur=0),  # +2 pour le joueur 1
        _posee(_carte(1, "NEUTRE"), _domaine(1), poseur=2),  # -1 pour le joueur 1
        _posee(_carte(2, "NOBLE"), _domaine(0), poseur=0),  # 0, famille Indifferente
        _posee(_carte(0, "GARDE"), _domaine(2), poseur=1),  # +1 pour le joueur 2
    ]

    points = rules.points(posees, lumiere, joueurs=3)

    assert points == [0, 1, 1], (
        f"points {points} au lieu de [0, 1, 1] : joueur 1 recoit +2 - 1, joueur 2 recoit +1, "
        f"le poseur ne recoit rien"
    )


def test_le_banquet_ne_rapporte_aucun_point() -> None:
    rules = module("rules")
    statuts = {0: rules.Statut.LUMIERE}
    posees = [
        _posee(_carte(0, "NOBLE"), _banquet("ESTIME"), poseur=0),
        _posee(_carte(0, "NOBLE"), _banquet("DISGRACE"), poseur=1),
    ]

    assert rules.points(posees, statuts, joueurs=2) == [0, 0]


# ---------------------------------------------------------------------------------
# La fin de partie -- paragraphe 3.4
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("joueurs", [2, 3, 4])
def test_un_tour_de_table_exige_trois_cartes_par_joueur(joueurs: int) -> None:
    """« Avant d'entamer un tour de table, si len(pioche) < 3 x nb_joueurs, c'est fini. »
    Tester la fin joueur par joueur est non conforme."""
    rules = module("rules")
    seuil = 3 * joueurs

    assert rules.peut_entamer_un_tour_de_table(seuil, joueurs) is True
    assert rules.peut_entamer_un_tour_de_table(seuil - 1, joueurs) is False
    assert rules.peut_entamer_un_tour_de_table(0, joueurs) is False
    assert rules.peut_entamer_un_tour_de_table(seuil + 1, joueurs) is True
