"""I8 -- 03_specification_moteur.md paragraphe 5.

« Deux info-sets distincts ne produisent jamais le meme tenseur, et reciproquement. »

C16 controle la bijection sur les instances rapides. I8 y ajoute ce que « et
reciproquement » implique en pratique :

  - le tenseur est une fonction de l'info-set, donc stable d'un appel a l'autre et
    identique sur un clone ;
  - il ne contient que des nombres finis, de taille constante ;
  - la bijection tient aussi pour les joueurs qui ne sont pas a la main -- un info-set
    d'attente est un info-set.

Ce dernier point est une exigence assumee, pas une lecture des regles. OpenSpiel ne definit
`information_state_string(p)` que la ou `p` joue ; ce test demande plus. La justification :
la phase et le tour courant sont des informations publiques (paragraphe 2.6 des regles et
vecteur global du paragraphe 4.2 de la specification), donc un joueur qui attend les connait
et sa vue doit les encoder. Si le moteur ne peut pas le garantir, c'est une decision a
remonter, pas a contourner en affaiblissant le test.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    Instance,
    construire,
    noms,
    parcourir_decisions,
)

NB_PARTIES = 50


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_i08_la_bijection_tient_pour_tous_les_joueurs(instance: Instance) -> None:
    _, moteur = construire(instance)
    tenseur_par_chaine: dict[str, tuple[float, ...]] = {}
    chaine_par_tenseur: dict[tuple[float, ...], str] = {}

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        for joueur in range(instance.joueurs):
            chaine = etat.information_state_string(joueur)
            tenseur = tuple(etat.information_state_tensor(joueur))

            connu = tenseur_par_chaine.setdefault(chaine, tenseur)
            assert connu == tenseur, (
                f"{instance.nom}, seed {seed}, joueur {joueur} : un meme info-set produit "
                f"deux tenseurs differents"
            )
            connue = chaine_par_tenseur.setdefault(tenseur, chaine)
            assert connue == chaine, (
                f"{instance.nom}, seed {seed}, joueur {joueur} : deux info-sets distincts "
                f"partagent un tenseur\n  A : {connue}\n  B : {chaine}"
            )

    assert len(tenseur_par_chaine) == len(chaine_par_tenseur)
    assert len(tenseur_par_chaine) > instance.joueurs * instance.tours


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_i08_le_tenseur_est_stable_et_bien_forme(instance: Instance) -> None:
    _, moteur = construire(instance)
    tailles: set[int] = set()

    for seed, etat in parcourir_decisions(moteur, 10):
        clone = etat.clone()
        for joueur in range(instance.joueurs):
            tenseur = list(etat.information_state_tensor(joueur))
            tailles.add(len(tenseur))

            assert tenseur == list(etat.information_state_tensor(joueur)), (
                f"{instance.nom}, seed {seed} : deux appels successifs donnent deux "
                f"tenseurs differents"
            )
            assert tenseur == list(clone.information_state_tensor(joueur)), (
                f"{instance.nom}, seed {seed} : le clone n'a pas le meme tenseur que "
                f"l'original"
            )
            assert clone.information_state_string(joueur) == etat.information_state_string(
                joueur
            )
            assert all(valeur == valeur for valeur in tenseur), (
                f"{instance.nom}, seed {seed} : le tenseur contient un NaN"
            )
            assert all(abs(valeur) != float("inf") for valeur in tenseur), (
                f"{instance.nom}, seed {seed} : le tenseur contient un infini"
            )

    assert len(tailles) == 1, (
        f"{instance.nom} : le tenseur change de taille selon l'etat ({sorted(tailles)})"
    )
