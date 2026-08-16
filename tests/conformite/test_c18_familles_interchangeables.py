"""C18 -- prerequis a la canonicalisation, cite au paragraphe 9 de 01_regles.md.

« Familles strictement interchangeables : permuter les familles laisse les gains
invariants. »

Le test joue une partie A depuis une pioche explicite, puis rejoue la meme partie sur la
pioche ou toutes les familles ont subi une permutation. Les actions ne sont PAS rejouees
par indice : le tri canonique de la main est fait sur l'indice de famille, donc une
permutation reordonne la main et un meme indice d'action y designerait d'autres cartes.
Le test rejoue donc l'action dont le contenu -- quelles cartes, dans quelles zones -- est
l'image par la permutation de celle jouee en A.

C'est exactement le piege signale au paragraphe 4.2 de la specification du moteur : un
rejeu par indice passerait ce test sur une implementation fausse.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    Instance,
    actions_legales,
    cle,
    construire,
    module,
    noms,
    paquet_ordonne,
    scores_moteur,
)

NB_PARTIES_C18 = 20


def _permutation(instance: Instance) -> dict[int, int]:
    """Rotation des familles : 0 -> 1 -> ... -> familles - 1 -> 0."""
    return {famille: (famille + 1) % instance.familles for famille in range(instance.familles)}


def _image_identite(
    identite: tuple[int, str, int], sigma: dict[int, int]
) -> tuple[int, str, int]:
    famille, nom_role, exemplaire = identite
    return (sigma[famille], nom_role, exemplaire)


def _semantique_pose(etat: Any, action: int, config: Any, rules: Any) -> tuple:
    """Ce qu'une action de pose fait reellement : quelles cartes, ou, chez qui."""
    pose = rules.decoder_action_pose(action, config)
    main = etat.vue_privilegiee().mains[etat.current_player()]
    return (
        tuple(cle(main[indice]) for indice in pose.indices_main),
        pose.position.name,
        pose.adversaire_relatif,
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c18_permuter_les_familles_laisse_les_gains_invariants(instance: Instance) -> None:
    config, moteur = construire(instance)
    rules = module("rules")
    carte = module("cards").Carte
    sigma = _permutation(instance)

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
            phase = etat_a.phase().name
            assert etat_b.phase().name == phase
            assert etat_a.current_player() == etat_b.current_player()

            action_a = rng.choice(actions_legales(etat_a))

            if phase == "POSE":
                identites, position, adversaire = _semantique_pose(
                    etat_a, action_a, config, rules
                )
                cible = (
                    tuple(_image_identite(identite, sigma) for identite in identites),
                    position,
                    adversaire,
                )
                candidates = [
                    action
                    for action in etat_b.legal_actions()
                    if _semantique_pose(etat_b, action, config, rules) == cible
                ]
                assert len(candidates) == 1, (
                    f"{instance.nom}, seed {seed} : {len(candidates)} action(s) de B "
                    f"correspondent a l'action {action_a} de A"
                )
                action_b = candidates[0]

            elif phase == "CIBLAGE":
                cibles_a = list(etat_a.cibles_courantes())
                cibles_b = list(etat_b.cibles_courantes())
                assert len(cibles_a) == len(cibles_b), (
                    f"{instance.nom}, seed {seed} : {len(cibles_a)} cibles en A contre "
                    f"{len(cibles_b)} en B"
                )
                if action_a == len(cibles_a):
                    action_b = len(cibles_b)
                else:
                    attendu = _image_identite(cle(cibles_a[action_a].carte), sigma)
                    candidates = [
                        indice
                        for indice, cible in enumerate(cibles_b)
                        if cle(cible.carte) == attendu
                    ]
                    assert len(candidates) == 1
                    action_b = candidates[0]

            else:
                raise AssertionError(
                    f"{instance.nom} : phase {phase} non geree par ce test -- le rejeu par "
                    f"permutation n'est defini que pour POSE et CIBLAGE"
                )

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
