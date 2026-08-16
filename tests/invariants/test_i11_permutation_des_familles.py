"""I11 -- 03_specification_moteur.md paragraphe 5.

« Permuter les familles laisse les gains invariants. »

C18 utilise une seule permutation, la rotation. I11 en tire une au hasard a chaque partie,
y compris des permutations qui laissent des familles en place, et verifie en plus que
l'invariance porte sur les scores bruts et sur toute la trajectoire, pas seulement sur le
gain final : a chaque noeud, les scores provisoires et le nombre de cibles doivent
correspondre.

C'est le prerequis de la canonicalisation. S'il tombe, canonicaliser par permutation des
familles change le jeu au lieu de le replier.
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

NB_PARTIES = 15


def _permutation_aleatoire(instance: Instance, rng: random.Random) -> dict[int, int]:
    images = list(range(instance.familles))
    rng.shuffle(images)
    return dict(enumerate(images))


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_i11_toute_permutation_des_familles_laisse_le_jeu_invariant(
    instance: Instance,
) -> None:
    config, moteur = construire(instance)
    carte = module("cards").Carte
    permutations_non_triviales = 0

    for seed in range(NB_PARTIES):
        rng = random.Random(seed)
        sigma = _permutation_aleatoire(instance, rng)
        if any(famille != image for famille, image in sigma.items()):
            permutations_non_triviales += 1

        pioche_a = paquet_ordonne(instance)
        rng.shuffle(pioche_a)
        pioche_b = [carte(sigma[c.famille], c.role, c.exemplaire) for c in pioche_a]

        etat_a = moteur.reset_depuis_pioche(pioche_a)
        etat_b = moteur.reset_depuis_pioche(pioche_b)

        while not etat_a.is_terminal():
            assert not etat_b.is_terminal()
            assert etat_a.phase().name == etat_b.phase().name
            assert etat_a.current_player() == etat_b.current_player()
            assert len(etat_a.legal_actions()) == len(etat_b.legal_actions()), (
                f"{instance.nom}, seed {seed}, sigma {sigma} : {len(etat_a.legal_actions())} "
                f"actions en A contre {len(etat_b.legal_actions())} en B"
            )
            assert scores_moteur(etat_a, instance) == scores_moteur(etat_b, instance), (
                f"{instance.nom}, seed {seed}, sigma {sigma} : scores provisoires "
                f"divergents en cours de partie"
            )

            action_a = rng.choice(actions_legales(etat_a))
            action_b = action_image(etat_a, action_a, etat_b, sigma, config)
            etat_a.apply(action_a)
            etat_b.apply(action_b)

        assert etat_b.is_terminal()
        assert scores_moteur(etat_a, instance) == scores_moteur(etat_b, instance), (
            f"{instance.nom}, seed {seed}, sigma {sigma} : scores finaux divergents"
        )
        assert list(etat_a.returns()) == pytest.approx(list(etat_b.returns())), (
            f"{instance.nom}, seed {seed}, sigma {sigma} : gains divergents"
        )

    assert permutations_non_triviales > 0, (
        f"{instance.nom} : toutes les permutations tirees etaient l'identite"
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_i11_la_permutation_change_bien_le_paquet(instance: Instance) -> None:
    """Garde-fou : si l'image de la pioche etait identique, le test precedent serait vide."""
    carte = module("cards").Carte
    sigma = {famille: (famille + 1) % instance.familles for famille in range(instance.familles)}

    pioche = paquet_ordonne(instance)
    image = [carte(sigma[c.famille], c.role, c.exemplaire) for c in pioche]

    assert [cle(c) for c in pioche] != [cle(c) for c in image]
    assert sorted(cle(c) for c in pioche) == sorted(cle(c) for c in image), (
        f"{instance.nom} : la permutation ne conserve pas le paquet"
    )
