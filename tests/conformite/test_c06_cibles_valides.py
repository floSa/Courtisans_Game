"""C6 -- 01_regles.md paragraphe 4.1.

« Les cibles valides excluent les Gardes et l'Assassin lui-meme, et sont toutes dans sa
zone. »

Le test recalcule l'ensemble attendu depuis la vue de dieu -- toute carte vivante de la
meme zone, Gardes exclus, Assassin resolu exclu -- et exige l'egalite exacte avec
`cibles_courantes()`. Une egalite, pas une inclusion : une cible manquante est une faute
au meme titre qu'une cible en trop.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    Instance,
    cle,
    cles,
    construire,
    noms,
    parcourir_decisions,
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c06_les_cibles_valides_sont_exactement_celles_de_la_regle(instance: Instance) -> None:
    _, moteur = construire(instance)
    noeuds = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES_BALAYAGE):
        if etat.phase().name != "CIBLAGE":
            continue
        noeuds += 1

        assassin = etat.assassin_en_resolution()
        assert assassin is not None, f"{instance.nom}, seed {seed} : ciblage sans Assassin"
        assert assassin.carte.role.name == "ASSASSIN"
        assert assassin.poseur == etat.current_player(), (
            f"{instance.nom}, seed {seed} : l'Assassin est resolu par un autre joueur que "
            f"son poseur"
        )

        vue = etat.vue_privilegiee()
        attendues = [
            posee
            for posee in vue.posees
            if posee.zone == assassin.zone
            and posee.carte.role.name != "GARDE"
            and cle(posee.carte) != cle(assassin.carte)
        ]
        cibles = list(etat.cibles_courantes())

        assert sorted(cles(cibles)) == sorted(cles(attendues)), (
            f"{instance.nom}, seed {seed} : cibles {sorted(cles(cibles))} au lieu de "
            f"{sorted(cles(attendues))}"
        )
        assert all(cible.zone == assassin.zone for cible in cibles), (
            f"{instance.nom}, seed {seed} : une cible est hors de la zone de l'Assassin"
        )
        assert all(cible.carte.role.name != "GARDE" for cible in cibles), (
            f"{instance.nom}, seed {seed} : un Garde est cible alors qu'il est immunise"
        )
        assert all(cle(cible.carte) != cle(assassin.carte) for cible in cibles), (
            f"{instance.nom}, seed {seed} : l'Assassin peut se cibler lui-meme"
        )

    assert noeuds > 0, (
        f"{instance.nom} : aucun noeud de ciblage sur {NB_PARTIES_BALAYAGE} parties"
    )
