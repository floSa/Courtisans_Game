"""Regle R-a -- arbitrage du 16/08, ecrite en tete de `tests/outils.py`.

« `reset(seed)` et `reset_depuis_pioche(cartes)` partagent le meme code. Le seed ne fait que
produire l'ordre de la pioche ; tout ce qui suit est commun aux deux chemins. »

Pourquoi ce test existe : les tests constructifs (C10, C18, I7, I9, I11) passent tous par
`reset_depuis_pioche`. Si ce chemin divergeait de celui qu'emprunte une partie reelle, ils
certifieraient un moteur qui n'est pas celui qui joue. C'est exactement la forme de
divergence qui a coute trois mois au projet precedent.

Ce que le test ne peut pas faire : lire le code pour verifier qu'il n'y a qu'une
implementation. Il verifie l'equivalence observable, sur toute la duree d'une partie et sur
l'empreinte complete des etats -- plateau, mains, pioche, chaines et tenseurs de tous les
joueurs.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    cle,
    construire,
    empreinte,
    noms,
    paquet_attendu,
)

NB_SEEDS = 10


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_pioche_depuis_seed_est_deterministe_et_complete(instance: Instance) -> None:
    _, moteur = construire(instance)

    for seed in range(NB_SEEDS):
        pioche = list(moteur.pioche_depuis_seed(seed))

        assert [cle(c) for c in pioche] == [
            cle(c) for c in moteur.pioche_depuis_seed(seed)
        ], f"{instance.nom}, seed {seed} : deux appels donnent deux pioches"
        assert sorted(cle(c) for c in pioche) == sorted(paquet_attendu(instance)), (
            f"{instance.nom}, seed {seed} : la pioche n'est pas exactement le paquet "
            f"({len(pioche)} cartes pour {instance.nb_cartes} attendues)"
        )


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_les_deux_chemins_de_reset_donnent_la_meme_partie(instance: Instance) -> None:
    _, moteur = construire(instance)

    for seed in range(NB_SEEDS):
        par_seed = moteur.reset(seed)
        par_pioche = moteur.reset_depuis_pioche(list(moteur.pioche_depuis_seed(seed)))
        rng = random.Random(seed)

        pas = 0
        while not par_seed.is_terminal():
            assert empreinte(par_seed, instance) == empreinte(par_pioche, instance), (
                f"{instance.nom}, seed {seed} : les deux chemins de reset divergent au pas "
                f"{pas} -- reset_depuis_pioche n'emprunte pas le meme code que reset"
            )
            action = rng.choice(actions_legales(par_seed))
            par_pioche.apply(action)
            par_seed.apply(action)
            pas += 1

        assert par_pioche.is_terminal(), (
            f"{instance.nom}, seed {seed} : les deux chemins ne donnent pas la meme longueur"
        )
        assert empreinte(par_seed, instance) == empreinte(par_pioche, instance)
        assert pas > 0


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_reset_depuis_pioche_refuse_un_paquet_qui_n_est_pas_le_bon(
    instance: Instance,
) -> None:
    """Un multiensemble faux doit lever : sinon un test constructif pourrait fabriquer un
    etat impossible et le certifier."""
    _, moteur = construire(instance)
    pioche = list(moteur.pioche_depuis_seed(0))

    with pytest.raises(Exception):  # noqa: B017 - le type d'exception n'est pas impose
        moteur.reset_depuis_pioche(pioche[:-1])

    with pytest.raises(Exception):  # noqa: B017
        moteur.reset_depuis_pioche([*pioche, pioche[0]])

    with pytest.raises(Exception):  # noqa: B017
        moteur.reset_depuis_pioche([pioche[0]] * len(pioche))
