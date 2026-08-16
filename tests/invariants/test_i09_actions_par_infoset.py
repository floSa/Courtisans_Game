"""I9 -- 03_specification_moteur.md paragraphe 5.

« Tous les etats d'un meme info-set exposent le meme ensemble d'actions legales. »

C17 le verifie sur les info-sets rencontres au hasard. I9 ajoute le cas construit, qui est
le seul a garantir que deux etats VRAIMENT distincts tombent dans le meme info-set : les
deux pioches jumelles de I7 produisent, pour tout joueur autre que le poseur, le meme
info-set a partir de deux etats du monde differents. Les actions legales doivent y etre
identiques -- y compris le nombre de cibles d'un Assassin.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    INSTANCES_AVEC_RESTE,
    INSTANCES_RAPIDES,
    Instance,
    cle,
    construire,
    mortes,
    noms,
    parcourir_decisions,
    pioches_jumelles_espion,
    rejouer_en_parallele,
)

NB_PARTIES = 50
SEED_ACTIONS = 20260818


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_i09_un_info_set_expose_toujours_les_memes_actions(instance: Instance) -> None:
    _, moteur = construire(instance)
    actions_par_chaine: dict[str, tuple[int, ...]] = {}

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        joueur = etat.current_player()
        if joueur < 0:
            continue
        chaine = etat.information_state_string(joueur)
        actions = tuple(sorted(etat.legal_actions()))
        connues = actions_par_chaine.setdefault(chaine, actions)
        assert connues == actions, (
            f"{instance.nom}, seed {seed} : l'info-set\n  {chaine}\nexpose {connues} puis "
            f"{actions}"
        )

    assert len(actions_par_chaine) > instance.tours


@pytest.mark.parametrize("instance", INSTANCES_AVEC_RESTE, ids=noms(INSTANCES_AVEC_RESTE))
def test_i09_deux_etats_du_meme_info_set_offrent_les_memes_actions(
    instance: Instance,
) -> None:
    """Cas construit : deux mondes differents, un seul info-set pour l'observateur."""
    _, moteur = construire(instance)
    pioche_a, pioche_b, espion_a, espion_b = pioches_jumelles_espion(instance, joueur=0)

    etat_a = moteur.reset_depuis_pioche(pioche_a)
    etat_b = moteur.reset_depuis_pioche(pioche_b)
    rng = random.Random(SEED_ACTIONS)

    noeuds_confondus = 0
    for courant_a, courant_b in rejouer_en_parallele(etat_a, etat_b, rng):
        if cle(espion_a) in mortes(courant_a) or cle(espion_b) in mortes(courant_b):
            break
        joueur = courant_a.current_player()
        if joueur <= 0:
            continue  # le joueur 0 est le poseur : ses deux info-sets different a bon droit

        assert courant_a.information_state_string(joueur) == courant_b.information_state_string(
            joueur
        )
        noeuds_confondus += 1
        assert sorted(courant_a.legal_actions()) == sorted(courant_b.legal_actions()), (
            f"{instance.nom} : deux etats du meme info-set du joueur {joueur} offrent des "
            f"actions differentes"
        )

    assert noeuds_confondus > 0, (
        f"{instance.nom} : aucun noeud ou un adversaire du poseur ait eu la main"
    )
