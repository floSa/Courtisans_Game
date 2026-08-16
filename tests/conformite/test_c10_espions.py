"""C10 -- 01_regles.md paragraphes 2.6 et 4.2.

« Un Espion est invisible pour tous sauf son poseur, et compte au decompte. »

Le premier test est constructif. Il fabrique deux parties qui ne different QUE par
l'identite d'un Espion cache :

  - partie A : le joueur 0 recoit l'Espion de famille 0 ; l'Espion de famille 1 dort dans
    les cartes jamais piochees ;
  - partie B : les deux Espions sont echanges.

Les deux parties recoivent la meme suite d'actions. Le paragraphe 3.4 garantit que les
cartes restantes ne sont jamais piochees ni revelees : aucun joueur autre que 0 ne peut
donc distinguer A de B, et leurs `information_state_string` doivent etre identiques a
chaque noeud. Celle du joueur 0, elle, doit differer -- sinon il ne connaitrait pas sa
propre carte.

Les deux Espions choisis sont de familles 0 et 1, les deux autres cartes de la main de
familles 2 et 3 : le tri canonique de la main place l'Espion au meme rang dans les deux
parties, donc une meme action y designe bien les memes cartes.

Le second test verifie l'autre moitie de la regle : les Espions comptent au decompte.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    RAPIDE_3J,
    Instance,
    actions_legales,
    cle,
    construire,
    module,
    noms,
    paquet_ordonne,
    partie,
    role,
    scores_attendus,
    scores_moteur,
    scores_sans_espions,
)

SEED_ACTIONS = 20260816


def _pioches_jumelles(instance: Instance) -> tuple[list[Any], list[Any], Any, Any]:
    """Deux pioches identiques a l'echange pres de deux Espions caches."""
    carte = module("cards").Carte
    espion_a = carte(0, role("ESPION"), 0)
    espion_b = carte(1, role("ESPION"), 0)
    accompagnement = [carte(2, role("NOBLE"), 0), carte(3, role("NOBLE"), 0)]

    exclues = {cle(espion_a), cle(espion_b)} | {cle(c) for c in accompagnement}
    reste = [c for c in paquet_ordonne(instance) if cle(c) not in exclues]

    piochees = instance.cartes_jouees - 3  # cartes tirees apres la premiere main du joueur 0
    pioche_a = [espion_a, *accompagnement, *reste[:piochees], espion_b, *reste[piochees:]]
    pioche_b = [espion_b, *accompagnement, *reste[:piochees], espion_a, *reste[piochees:]]
    return pioche_a, pioche_b, espion_a, espion_b


def _mortes(etat: Any) -> set[tuple[int, str, int]]:
    return {cle(posee.carte) for posee in etat.vue_privilegiee().defausse}


def test_c10_un_espion_est_invisible_pour_tous_sauf_son_poseur() -> None:
    instance = RAPIDE_3J
    _, moteur = construire(instance)
    pioche_a, pioche_b, espion_a, espion_b = _pioches_jumelles(instance)

    etat_a = moteur.reset_depuis_pioche(pioche_a)
    etat_b = moteur.reset_depuis_pioche(pioche_b)

    assert sorted(cle(c) for c in etat_a.vue_privilegiee().mains[0]) == sorted(
        cle(c) for c in pioche_a[:3]
    ), "la premiere main du joueur 0 n'est pas le debut de la pioche fournie"

    rng = random.Random(SEED_ACTIONS)
    noeuds_compares = 0
    noeuds_ou_le_poseur_distingue = 0

    while not etat_a.is_terminal():
        assert not etat_b.is_terminal(), "les deux parties n'ont pas la meme longueur"
        assert etat_a.phase().name == etat_b.phase().name
        assert etat_a.current_player() == etat_b.current_player()
        assert list(etat_a.legal_actions()) == list(etat_b.legal_actions()), (
            "l'identite d'un Espion cache change les actions legales"
        )

        if cle(espion_a) in _mortes(etat_a) or cle(espion_b) in _mortes(etat_b):
            break  # l'Espion est mort donc revele : la divergence devient legitime

        noeuds_compares += 1
        for joueur in range(1, instance.joueurs):
            assert etat_a.information_state_string(joueur) == etat_b.information_state_string(
                joueur
            ), (
                f"noeud {noeuds_compares} : le joueur {joueur} distingue deux etats qui ne "
                f"different que par l'identite d'un Espion qu'il n'a pas pose"
            )
        if etat_a.information_state_string(0) != etat_b.information_state_string(0):
            noeuds_ou_le_poseur_distingue += 1

        action = rng.choice(actions_legales(etat_a))
        etat_a.apply(action)
        etat_b.apply(action)

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
        espions_vivants += sum(
            1 for posee in vue.posees if posee.carte.role.name == "ESPION"
        )

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
