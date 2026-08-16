"""I7 -- 03_specification_moteur.md paragraphe 5, test hostile.

« `information_state_string(p)` ne contient aucune information que `p` ne possede pas. »

C'est l'invariant le plus facile a violer sans le voir : il suffit qu'un champ de debug
fuite l'identite d'un Espion adverse, et rien ne leve. La specification exige un test
hostile qui construise deux etats ne differant QUE par une information cachee et verifie
que les chaines sont identiques. Ce fichier en construit trois, plus un garde-fou.

  1. **Espion adverse.** Deux pioches echangeant un Espion pose et son jumeau jamais
     pioche. Personne sauf le poseur ne peut les distinguer. Teste pour chaque joueur
     poseur, sur chaque instance ayant des cartes jamais piochees.

  2. **Fond de pioche.** Deux pioches identiques sauf l'ordre des cartes jamais tirees.
     Le paragraphe 3.4 dit que leur identite n'est jamais revelee : AUCUN joueur, pas meme
     le joueur 0, ne doit voir la moindre difference -- ni dans sa chaine, ni dans son
     tenseur, ni dans le score final.

  3. **Garde-fou anti-degenerescence.** Une chaine constante passerait les deux premiers
     tests sans rien encoder. Le troisieme exige que chaque joueur ait, sur un balayage,
     beaucoup plus de chaines distinctes que la partie ne compte de tours.

Ce que ce fichier ne teste PAS : la fuite par le tenseur seul, couverte par I8 via la
bijection chaine <-> tenseur.
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
    paquet_ordonne,
    parcourir_decisions,
    pioches_jumelles_espion,
    rejouer_en_parallele,
    scores_moteur,
)

SEED_ACTIONS = 20260817

CAS_ESPION = [
    (instance, joueur)
    for instance in INSTANCES_AVEC_RESTE
    for joueur in range(instance.joueurs)
]
IDS_ESPION = [f"{instance.nom}-poseur{joueur}" for instance, joueur in CAS_ESPION]


@pytest.mark.parametrize(("instance", "poseur"), CAS_ESPION, ids=IDS_ESPION)
def test_i07_l_identite_d_un_espion_adverse_ne_fuit_pas(
    instance: Instance, poseur: int
) -> None:
    _, moteur = construire(instance)
    pioche_a, pioche_b, espion_a, espion_b = pioches_jumelles_espion(instance, joueur=poseur)

    etat_a = moteur.reset_depuis_pioche(pioche_a)
    etat_b = moteur.reset_depuis_pioche(pioche_b)
    rng = random.Random(SEED_ACTIONS)

    noeuds = 0
    for courant_a, courant_b in rejouer_en_parallele(etat_a, etat_b, rng):
        if cle(espion_a) in mortes(courant_a) or cle(espion_b) in mortes(courant_b):
            break  # tuee donc revelee : la defausse est publique (paragraphe 4.1)
        noeuds += 1
        for joueur in range(instance.joueurs):
            if joueur == poseur:
                continue
            assert courant_a.information_state_string(
                joueur
            ) == courant_b.information_state_string(joueur), (
                f"{instance.nom}, noeud {noeuds} : le joueur {joueur} distingue l'Espion de "
                f"famille 0 de celui de famille 1, alors qu'il ne les a pas poses"
            )
            assert list(courant_a.information_state_tensor(joueur)) == list(
                courant_b.information_state_tensor(joueur)
            ), (
                f"{instance.nom}, noeud {noeuds} : le tenseur du joueur {joueur} fuit "
                f"l'identite d'un Espion adverse"
            )

    assert noeuds > 0, f"{instance.nom} : aucun noeud compare"


@pytest.mark.parametrize(
    "instance", INSTANCES_AVEC_RESTE, ids=noms(INSTANCES_AVEC_RESTE)
)
def test_i07_le_fond_de_pioche_ne_fuit_pas(instance: Instance) -> None:
    """Les cartes jamais piochees ne sont revelees a personne (paragraphe 3.4)."""
    _, moteur = construire(instance)

    pioche_a = paquet_ordonne(instance)
    random.Random(7).shuffle(pioche_a)
    tirees = instance.cartes_jouees
    fond = pioche_a[tirees:]
    assert len(fond) == instance.reste_en_pioche
    assert len(fond) >= 2

    pioche_b = [*pioche_a[:tirees], *reversed(fond)]
    assert [cle(c) for c in pioche_a] != [cle(c) for c in pioche_b], (
        f"{instance.nom} : le fond de pioche renverse est identique a lui-meme"
    )

    etat_a = moteur.reset_depuis_pioche(pioche_a)
    etat_b = moteur.reset_depuis_pioche(pioche_b)
    rng = random.Random(SEED_ACTIONS)

    noeuds = 0
    for courant_a, courant_b in rejouer_en_parallele(etat_a, etat_b, rng):
        noeuds += 1
        for joueur in range(instance.joueurs):
            assert courant_a.information_state_string(
                joueur
            ) == courant_b.information_state_string(joueur), (
                f"{instance.nom}, noeud {noeuds} : le joueur {joueur} voit l'ordre des "
                f"cartes qui ne seront jamais piochees"
            )
            assert list(courant_a.information_state_tensor(joueur)) == list(
                courant_b.information_state_tensor(joueur)
            )

    assert noeuds > 0
    assert scores_moteur(etat_a, instance) == scores_moteur(etat_b, instance)
    assert list(etat_a.returns()) == pytest.approx(list(etat_b.returns()))


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_i07_la_chaine_n_est_pas_degeneree(instance: Instance) -> None:
    """Garde-fou : une chaine constante passerait les deux tests precedents."""
    _, moteur = construire(instance)
    chaines: list[set[str]] = [set() for _ in range(instance.joueurs)]

    for _seed, etat in parcourir_decisions(moteur, 30):
        for joueur in range(instance.joueurs):
            chaines[joueur].add(etat.information_state_string(joueur))

    for joueur, distinctes in enumerate(chaines):
        assert len(distinctes) > instance.tours, (
            f"{instance.nom} : le joueur {joueur} n'a que {len(distinctes)} chaines "
            f"distinctes sur 30 parties -- l'encodage n'encode presque rien"
        )
