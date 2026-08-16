"""I3 -- 03_specification_moteur.md paragraphe 5.

« Tous les joueurs jouent exactement config.tours tours. »

C2 verifie l'egalite entre joueurs sur un gros echantillon ; I3 verifie en plus la valeur
exacte attendue et l'ordre : les regles imposent un ordre fixe (paragraphe 3.3), donc la
suite des joueurs aux noeuds de pose doit etre 0, 1, ..., n-1 repetee `tours` fois. Un
moteur qui laisserait un joueur doubler puis rendrait la main plus tard passerait C2 mais
pas ce test.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    construire,
    noms,
)

NB_PARTIES = 20


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i03_l_ordre_de_jeu_est_un_tour_de_table_fixe(instance: Instance) -> None:
    config, moteur = construire(instance)
    attendu = list(range(instance.joueurs)) * instance.tours

    assert config.tours == instance.tours
    assert config.cartes_jouees == instance.cartes_jouees, (
        f"{instance.nom} : cartes_jouees = {config.cartes_jouees} au lieu de "
        f"3 x {instance.joueurs} x {instance.tours} = {instance.cartes_jouees}"
    )

    for seed in range(NB_PARTIES):
        etat = moteur.reset(seed)
        rng = random.Random(seed)
        ordre: list[int] = []

        while not etat.is_terminal():
            if etat.phase().name == "POSE":
                ordre.append(etat.current_player())
            etat.apply(rng.choice(actions_legales(etat)))

        assert ordre == attendu, (
            f"{instance.nom}, seed {seed} : ordre des poses {ordre[:12]}... au lieu de "
            f"{attendu[:12]}... ({len(ordre)} poses pour {len(attendu)} attendues)"
        )
