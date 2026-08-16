"""C10 -- 01_regles.md paragraphes 2.6 et 4.2.

« Un Espion est invisible pour tous sauf son poseur, et compte au decompte. »

Le premier test est constructif. Il fabrique deux parties qui ne different QUE par
l'identite d'un Espion cache : en A le joueur 0 recoit l'Espion de famille 0 et celui de
famille 1 dort dans les cartes jamais piochees, en B les deux sont echanges. Les deux
parties recoivent la meme suite d'actions.

Le paragraphe 3.4 garantit que les cartes restantes ne sont jamais piochees ni revelees :
aucun joueur autre que 0 ne peut donc distinguer A de B, et leurs
`information_state_string` doivent etre identiques a chaque noeud. Celle du joueur 0, elle,
doit differer -- sinon il ne connaitrait pas sa propre carte.

La construction est dans `tests/outils.py` : elle sert aussi au test hostile de
l'invariant I7.

Le second test verifie l'autre moitie de la regle : les Espions comptent au decompte.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    RAPIDE_3J,
    Instance,
    cle,
    construire,
    mortes,
    noms,
    partie,
    pioches_jumelles_espion,
    rejouer_en_parallele,
    scores_attendus,
    scores_moteur,
    scores_sans_espions,
)

SEED_ACTIONS = 20260816


def test_c10_un_espion_est_invisible_pour_tous_sauf_son_poseur() -> None:
    instance = RAPIDE_3J
    _, moteur = construire(instance)
    pioche_a, pioche_b, espion_a, espion_b = pioches_jumelles_espion(instance, joueur=0)

    etat_a = moteur.reset_depuis_pioche(pioche_a)
    etat_b = moteur.reset_depuis_pioche(pioche_b)

    assert sorted(cle(carte) for carte in etat_a.vue_privilegiee().mains[0]) == sorted(
        cle(carte) for carte in pioche_a[:3]
    ), "regle R-b : les 3 premieres cartes de la pioche ne forment pas la main du joueur 0"

    noeuds_compares = 0
    noeuds_ou_le_poseur_distingue = 0
    rng = random.Random(SEED_ACTIONS)

    for courant_a, courant_b in rejouer_en_parallele(etat_a, etat_b, rng):
        if cle(espion_a) in mortes(courant_a) or cle(espion_b) in mortes(courant_b):
            break  # l'Espion est mort donc revele : la divergence devient legitime

        noeuds_compares += 1
        for joueur in range(1, instance.joueurs):
            assert courant_a.information_state_string(
                joueur
            ) == courant_b.information_state_string(joueur), (
                f"noeud {noeuds_compares} : le joueur {joueur} distingue deux etats qui ne "
                f"different que par l'identite d'un Espion qu'il n'a pas pose"
            )
        if courant_a.information_state_string(0) != courant_b.information_state_string(0):
            noeuds_ou_le_poseur_distingue += 1

    assert noeuds_compares > 0, "aucun noeud compare : le test ne prouve rien"
    assert noeuds_ou_le_poseur_distingue > 0, (
        "le poseur ne distingue jamais son propre Espion : son information privee est perdue"
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c10_les_espions_comptent_au_decompte(instance: Instance) -> None:
    _, moteur = construire(instance)
    parties_discriminantes = 0
    espions_vivants = 0

    for seed in range(NB_PARTIES_BALAYAGE):
        etat = partie(moteur, seed)
        vue = etat.vue_privilegiee()
        espions_vivants += sum(1 for posee in vue.posees if posee.carte.role.name == "ESPION")

        attendus = scores_attendus(vue, instance)
        assert scores_moteur(etat, instance) == attendus, (
            f"{instance.nom}, seed {seed} : scores {scores_moteur(etat, instance)} au lieu "
            f"de {attendus} (Espions retournes et comptes normalement)"
        )
        if scores_sans_espions(vue, instance) != attendus:
            parties_discriminantes += 1

    assert espions_vivants > 0, f"{instance.nom} : aucun Espion vivant en fin de partie"
    assert parties_discriminantes > 0, (
        f"{instance.nom} : ignorer les Espions ne change jamais le score sur "
        f"{NB_PARTIES_BALAYAGE} parties -- le test ne discrimine pas"
    )
