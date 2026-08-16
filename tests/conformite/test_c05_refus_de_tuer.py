"""C5 -- 01_regles.md paragraphe 4.1, arbitrage R2.

« En resolution d'Assassin avec au moins 1 cible, "ne pas tuer" est une action legale. »

C'est la regle que les implementations precedentes violaient. Le refus porte l'indice
`len(cibles_valides)` et doit etre legal meme quand des cibles existent. Le test verifie
en plus qu'il ne tue effectivement personne : un refus qui tuerait quand meme serait une
action legale au nom mensonger.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    Instance,
    construire,
    nb_placees,
    noms,
    parcourir_decisions,
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c05_ne_pas_tuer_est_toujours_une_action_legale(instance: Instance) -> None:
    _, moteur = construire(instance)
    noeuds_avec_cibles = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES_BALAYAGE):
        if etat.phase().name != "CIBLAGE":
            continue

        cibles = etat.cibles_courantes()
        actions = list(etat.legal_actions())
        refus = len(cibles)

        assert refus in actions, (
            f"{instance.nom}, seed {seed} : refus de tuer absent des actions legales "
            f"alors qu'il y a {len(cibles)} cible(s) -- regle R2"
        )
        if not cibles:
            continue
        noeuds_avec_cibles += 1

        clone = etat.clone()
        avant = clone.vue_privilegiee()
        morts_avant = len(avant.defausse)
        placees_avant = nb_placees(avant)

        clone.apply(refus)

        apres = clone.vue_privilegiee()
        assert len(apres.defausse) == morts_avant, (
            f"{instance.nom}, seed {seed} : le refus de tuer a envoye une carte a la defausse"
        )
        assert nb_placees(apres) == placees_avant

    assert noeuds_avec_cibles > 0, (
        f"{instance.nom} : aucun noeud de ciblage avec cible rencontre sur "
        f"{NB_PARTIES_BALAYAGE} parties -- le test ne prouve rien"
    )
