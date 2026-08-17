"""Le tableau du paragraphe 3.4 des regles, en nombres litteraux.

**Pourquoi ce fichier existe.** Partout ailleurs, l'attendu d'un test d'arithmetique est
`Instance.tours`, `Instance.cartes_jouees`, `Instance.reste_en_pioche` -- et ces trois
proprietes de `tests/outils.py` appliquent **les memes formules** que `GameConfig`. Une
assertion du type `config.tours == instance.tours` compare donc deux transcriptions d'une
seule formule : elle attrape une faute de frappe, pas une **mauvaise lecture de la regle**.
Si les deux cotes lisaient `ceil` la ou le paragraphe 3.4 ecrit `floor`, ou divisaient par
`3 x joueurs - 1`, les deux bougeraient ensemble et tout resterait vert.

Ce fichier ne contient donc **aucune formule**. Il recopie les nombres imprimes dans le
tableau du paragraphe 3.4 de `01_regles.md`, et les confronte a `GameConfig` puis a une
partie reellement jouee jusqu'au terminal. C'est la seule facon de verifier une regle
contre la regle, et non contre sa propre transcription.

    | Joueurs | Cartes par tour de table | Tours par joueur | Cartes jouees | Restant |
    |---:|---:|---:|---:|---:|
    | 2 | 6 | 15 | 90 | 0 |
    | 3 | 9 | 10 | 90 | 0 |
    | 4 | 12 | 7 | 84 | 6 |

Le paragraphe 3.4 ajoute deux enonces que les nombres seuls ne portent pas, et qui ont
chacun leur test ici : le nombre de tours **decroit** quand le nombre de joueurs augmente
-- « toute table qui ne respecte pas cette monotonie contient une erreur » -- et **tous les
joueurs jouent exactement le meme nombre de tours**.

La ligne 5 joueurs du tableau des regles (6 tours) n'est pas testable : le paragraphe 8 de
la specification ne specifie pas 5 joueurs et `GameConfig` refuse la configuration. C'est un
trou assume, pas un oubli.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    COMPLET_2J,
    COMPLET_3J,
    COMPLET_4J,
    Instance,
    actions_legales,
    construire,
    construire_config,
)

#: 01_regles.md paragraphe 3.1 : 6 familles x 5 roles x 3 exemplaires = 90 cartes. Recopie,
#: jamais calcule -- c'est le paquet auquel le tableau du paragraphe 3.4 s'applique.
FAMILLES_DU_JEU_COMPLET = 6
ROLES_DU_JEU_COMPLET = 5
EXEMPLAIRES_DU_JEU_COMPLET = 3
CARTES_DU_JEU_COMPLET = 90

#: Le tableau du paragraphe 3.4, ligne par ligne :
#: (instance, joueurs, cartes par tour de table, tours par joueur, cartes jouees, restant).
TABLEAU_3_4: tuple[tuple[Instance, int, int, int, int, int], ...] = (
    (COMPLET_2J, 2, 6, 15, 90, 0),
    (COMPLET_3J, 3, 9, 10, 90, 0),
    (COMPLET_4J, 4, 12, 7, 84, 6),
)
IDS_3_4 = [f"{ligne[1]}-joueurs" for ligne in TABLEAU_3_4]


@pytest.mark.parametrize(
    ("instance", "joueurs", "par_tour_de_table", "tours", "cartes_jouees", "restant"),
    TABLEAU_3_4,
    ids=IDS_3_4,
)
def test_la_configuration_donne_les_nombres_du_tableau(
    instance: Instance,
    joueurs: int,
    par_tour_de_table: int,
    tours: int,
    cartes_jouees: int,
    restant: int,
) -> None:
    """`GameConfig` doit rendre les nombres imprimes, pas ceux d'une formule recopiee."""
    config = construire_config(instance)

    # Le tableau ne vaut que pour le paquet complet : on verifie d'abord qu'on lui applique
    # bien le bon paquet, avec les nombres du paragraphe 3.1.
    assert config.familles == FAMILLES_DU_JEU_COMPLET
    assert config.nb_roles == ROLES_DU_JEU_COMPLET
    assert config.exemplaires == EXEMPLAIRES_DU_JEU_COMPLET
    assert config.nb_cartes == CARTES_DU_JEU_COMPLET
    assert config.joueurs == joueurs

    assert config.tours == tours, (
        f"{joueurs} joueurs : {config.tours} tours par joueur, le tableau du paragraphe "
        f"3.4 en imprime {tours}"
    )
    assert config.cartes_jouees == cartes_jouees, (
        f"{joueurs} joueurs : {config.cartes_jouees} cartes jouees, le tableau en imprime "
        f"{cartes_jouees}"
    )
    assert config.reste_en_pioche == restant, (
        f"{joueurs} joueurs : {config.reste_en_pioche} cartes jamais piochees, le tableau "
        f"en imprime {restant}"
    )
    assert cartes_jouees == par_tour_de_table * tours, (
        "la ligne recopiee du tableau est incoherente avec elle-meme : "
        f"{par_tour_de_table} x {tours} != {cartes_jouees}"
    )


@pytest.mark.parametrize(
    ("instance", "joueurs", "par_tour_de_table", "tours", "cartes_jouees", "restant"),
    TABLEAU_3_4,
    ids=IDS_3_4,
)
def test_une_partie_jouee_donne_les_nombres_du_tableau(
    instance: Instance,
    joueurs: int,
    par_tour_de_table: int,
    tours: int,
    cartes_jouees: int,
    restant: int,
) -> None:
    """Les memes nombres, mais mesures sur une partie jouee jusqu'au terminal.

    Une configuration juste et un moteur qui joue autre chose resteraient invisibles au
    test precedent. Celui-ci compte les poses joueur par joueur -- « tous les joueurs jouent
    exactement le meme nombre de tours » -- et lit la pioche a la fin.
    """
    _, moteur = construire(instance)
    etat = moteur.reset(0)
    rng = random.Random(0)
    poses = [0] * joueurs

    while not etat.is_terminal():
        if etat.phase().name == "POSE":
            poses[etat.current_player()] += 1
        etat.apply(rng.choice(actions_legales(etat)))

    vue = etat.vue_privilegiee()
    assert poses == [tours] * joueurs, (
        f"{joueurs} joueurs : poses par joueur {poses}, le tableau du paragraphe 3.4 "
        f"imprime {tours} tours pour chacun"
    )
    assert len(vue.posees) + len(vue.defausse) == cartes_jouees, (
        f"{joueurs} joueurs : {len(vue.posees) + len(vue.defausse)} cartes sur la table, "
        f"le tableau en imprime {cartes_jouees}"
    )
    assert len(vue.pioche) == restant, (
        f"{joueurs} joueurs : {len(vue.pioche)} cartes jamais piochees, le tableau en "
        f"imprime {restant}"
    )
    assert sum(poses) * 3 == par_tour_de_table * tours


def test_le_nombre_de_tours_decroit_quand_les_joueurs_augmentent() -> None:
    """« Le nombre de tours decroit quand le nombre de joueurs augmente -- 15, 10, 7, 6.

    Toute table qui ne respecte pas cette monotonie contient une erreur. »

    Enonce du paragraphe 3.4, verifie a part : les trois nombres du tableau peuvent etre
    justes un a un et la relation entre eux fausse, si le paquet change en meme temps. Ici
    le paquet est le meme pour les trois.
    """
    tours = [
        construire_config(instance).tours for instance, *_ in TABLEAU_3_4
    ]
    joueurs = [ligne[1] for ligne in TABLEAU_3_4]

    assert joueurs == sorted(joueurs), "les lignes du tableau ne sont pas dans l'ordre"
    assert tours == [15, 10, 7], f"tours mesures {tours}, le tableau imprime 15, 10, 7"
    assert all(
        precedent > suivant for precedent, suivant in zip(tours, tours[1:], strict=False)
    ), f"la monotonie decroissante du paragraphe 3.4 est violee : {tours}"


@pytest.mark.parametrize(
    ("instance", "joueurs", "zones"),
    [(COMPLET_2J, 2, 4), (COMPLET_3J, 3, 5), (COMPLET_4J, 4, 6)],
    ids=IDS_3_4,
)
def test_le_nombre_de_zones_de_ciblage_est_celui_du_paragraphe_6(
    instance: Instance, joueurs: int, zones: int
) -> None:
    """« Zones de ciblage d'Assassin : 4 a 2 joueurs, 5 a 3, 6 a 4 » -- paragraphe 6.

    Nombres litteraux, la aussi : deux positions au banquet, plus un domaine par joueur. Un
    Assassin ne peut tuer que dans **sa** zone (paragraphe 4.1), donc ce nombre est la
    granularite exacte du ciblage. On le mesure en collectant les zones distinctes qu'une
    partie complete utilise.
    """
    _, moteur = construire(instance)
    etat = moteur.reset(1)
    rng = random.Random(1)
    vues: set[tuple[str, str | None, int | None]] = set()

    while not etat.is_terminal():
        for posee in (*etat.vue_privilegiee().posees, *etat.vue_privilegiee().defausse):
            zone = posee.zone
            vues.add(
                (
                    zone.genre.name,
                    zone.position.name if zone.position is not None else None,
                    zone.proprietaire,
                )
            )
        etat.apply(rng.choice(actions_legales(etat)))

    assert len(vues) == zones, (
        f"{joueurs} joueurs : {len(vues)} zones distinctes utilisees {sorted(vues)}, le "
        f"paragraphe 6 en imprime {zones}"
    )
