"""C11 -- 01_regles.md paragraphe 5, points 2 et 3.

« Les points vont au proprietaire du domaine, pas au poseur. »

Meme methode qu'en C9 : recalcul independant, puis variante fausse -- crediter le poseur --
qui doit donner un resultat different au moins une fois. Chaque tour obligeant a poser une
carte chez un adversaire (paragraphe 3.2), les deux lectures divergent des qu'une famille
n'est pas Indifferente.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    Instance,
    construire,
    noms,
    partie,
    scores_attendus,
    scores_credites_au_poseur,
    scores_moteur,
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c11_les_points_vont_au_proprietaire_du_domaine(instance: Instance) -> None:
    _, moteur = construire(instance)
    parties_discriminantes = 0

    for seed in range(NB_PARTIES_BALAYAGE):
        etat = partie(moteur, seed)
        vue = etat.vue_privilegiee()

        attendus = scores_attendus(vue, instance)
        assert scores_moteur(etat, instance) == attendus, (
            f"{instance.nom}, seed {seed} : scores {scores_moteur(etat, instance)} au lieu "
            f"de {attendus} (points credites au proprietaire du domaine)"
        )
        if scores_credites_au_poseur(vue, instance) != attendus:
            parties_discriminantes += 1

    assert parties_discriminantes > 0, (
        f"{instance.nom} : crediter le poseur au lieu du proprietaire ne change jamais le "
        f"score sur {NB_PARTIES_BALAYAGE} parties -- le test ne discrimine pas"
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c11_une_carte_donnee_a_un_adversaire_rapporte_a_cet_adversaire(
    instance: Instance,
) -> None:
    """Controle direct, carte par carte, sur les seules cartes posees chez autrui."""
    _, moteur = construire(instance)
    cadeaux_observes = 0

    for seed in range(NB_PARTIES_BALAYAGE):
        etat = partie(moteur, seed)
        vue = etat.vue_privilegiee()

        for posee in vue.posees:
            if posee.zone.genre.name != "DOMAINE":
                continue
            if posee.zone.proprietaire == posee.poseur:
                continue
            cadeaux_observes += 1

    assert cadeaux_observes > 0, (
        f"{instance.nom} : aucune carte posee chez un adversaire, alors que le paragraphe "
        f"3.2 en impose une par tour"
    )
    attendu = instance.joueurs * instance.tours * NB_PARTIES_BALAYAGE
    assert cadeaux_observes <= attendu, (
        f"{instance.nom} : {cadeaux_observes} cartes chez autrui pour un maximum de "
        f"{instance.joueurs} x {instance.tours} x {NB_PARTIES_BALAYAGE} = {attendu}"
    )
