"""C18 -- prerequis a la canonicalisation, cite au paragraphe 9 de 01_regles.md.

« Familles strictement interchangeables : permuter les familles laisse les gains
invariants. »

Le test joue une partie A depuis une pioche explicite, puis rejoue la meme partie sur la
pioche ou toutes les familles ont subi une permutation. Les actions ne sont PAS rejouees
par indice : le tri canonique de la main est fait sur l'indice de famille, donc une
permutation reordonne la main et un meme indice d'action y designerait d'autres cartes.
Le test rejoue donc l'action dont le contenu -- quelles cartes, dans quelles zones -- est
l'image par la permutation de celle jouee en A. La traduction est dans `tests/outils.py`.

C'est exactement le piege signale au paragraphe 4.2 de la specification du moteur : un
rejeu par indice passerait ce test sur une implementation fausse.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    Instance,
    action_image,
    actions_legales,
    cle,
    construire,
    module,
    noms,
    paquet_ordonne,
    scores_moteur,
)

NB_PARTIES_C18 = 20


def _rotation(instance: Instance) -> dict[int, int]:
    """Rotation des familles : 0 -> 1 -> ... -> familles - 1 -> 0."""
    return {famille: (famille + 1) % instance.familles for famille in range(instance.familles)}


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c18_permuter_les_familles_laisse_les_gains_invariants(instance: Instance) -> None:
    config, moteur = construire(instance)
    carte = module("cards").Carte
    sigma = _rotation(instance)

    for seed in range(NB_PARTIES_C18):
        pioche_a = paquet_ordonne(instance)
        random.Random(seed).shuffle(pioche_a)
        pioche_b = [carte(sigma[c.famille], c.role, c.exemplaire) for c in pioche_a]
        assert [cle(c) for c in pioche_a] != [cle(c) for c in pioche_b], (
            "la permutation choisie est l'identite : le test ne prouverait rien"
        )

        etat_a = moteur.reset_depuis_pioche(pioche_a)
        etat_b = moteur.reset_depuis_pioche(pioche_b)
        rng = random.Random(seed)

        while not etat_a.is_terminal():
            assert not etat_b.is_terminal(), (
                f"{instance.nom}, seed {seed} : les deux parties n'ont pas la meme longueur"
            )
            assert etat_a.phase().name == etat_b.phase().name
            assert etat_a.current_player() == etat_b.current_player()

            action_a = rng.choice(actions_legales(etat_a))
            action_b = action_image(etat_a, action_a, etat_b, sigma, config)
            etat_a.apply(action_a)
            etat_b.apply(action_b)

        assert etat_b.is_terminal()
        scores_a = scores_moteur(etat_a, instance)
        scores_b = scores_moteur(etat_b, instance)
        assert scores_a == scores_b, (
            f"{instance.nom}, seed {seed} : scores {scores_a} contre {scores_b} apres "
            f"permutation des familles"
        )
        assert list(etat_a.returns()) == pytest.approx(list(etat_b.returns())), (
            f"{instance.nom}, seed {seed} : gains {etat_a.returns()} contre "
            f"{etat_b.returns()} apres permutation des familles"
        )
