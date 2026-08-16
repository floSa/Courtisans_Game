"""C16 -- prerequis IA, cite au paragraphe 9 de 01_regles.md.

« Encodage info-set injectif : deux info-sets distincts ne partagent jamais un tenseur. »

La correspondance doit etre bijective dans les deux sens : une chaine d'info-set donne
toujours le meme tenseur, et un tenseur ne peut pas provenir de deux chaines differentes.
Une collision signifie que le reseau recoit la meme entree pour deux situations qu'il doit
distinguer.

Garde-fou : un encodage constant satisferait trivialement les deux sens. Le test exige
donc plus d'info-sets distincts qu'il n'y a de noeuds de decision dans une seule partie.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_INFOSET,
    Instance,
    construire,
    noms,
    parcourir_decisions,
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c16_l_encodage_info_set_est_injectif(instance: Instance) -> None:
    _, moteur = construire(instance)
    tenseur_par_chaine: dict[str, tuple[float, ...]] = {}
    chaine_par_tenseur: dict[tuple[float, ...], str] = {}
    noeuds = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES_INFOSET):
        joueur = etat.current_player()
        if joueur < 0:
            continue  # noeud de hasard : pas d'info-set de joueur
        noeuds += 1

        chaine = etat.information_state_string(joueur)
        tenseur = tuple(etat.information_state_tensor(joueur))

        if chaine in tenseur_par_chaine:
            assert tenseur_par_chaine[chaine] == tenseur, (
                f"{instance.nom}, seed {seed} : un meme info-set produit deux tenseurs"
            )
        else:
            tenseur_par_chaine[chaine] = tenseur

        if tenseur in chaine_par_tenseur:
            assert chaine_par_tenseur[tenseur] == chaine, (
                f"{instance.nom}, seed {seed} : deux info-sets distincts partagent un "
                f"tenseur\n  A : {chaine_par_tenseur[tenseur]}\n  B : {chaine}"
            )
        else:
            chaine_par_tenseur[tenseur] = chaine

    assert noeuds > 0
    assert len(tenseur_par_chaine) == len(chaine_par_tenseur), (
        f"{instance.nom} : {len(tenseur_par_chaine)} info-sets pour "
        f"{len(chaine_par_tenseur)} tenseurs distincts"
    )
    plancher = instance.joueurs * instance.tours
    assert len(tenseur_par_chaine) > plancher, (
        f"{instance.nom} : seulement {len(tenseur_par_chaine)} info-sets distincts sur "
        f"{noeuds} noeuds -- encodage trop pauvre pour etre injectif de bonne foi"
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c16_le_tenseur_a_une_taille_constante(instance: Instance) -> None:
    _, moteur = construire(instance)
    tailles: set[int] = set()

    for _seed, etat in parcourir_decisions(moteur, 10):
        for joueur in range(instance.joueurs):
            tailles.add(len(etat.information_state_tensor(joueur)))

    assert len(tailles) == 1, (
        f"{instance.nom} : le tenseur change de taille selon l'etat ({sorted(tailles)})"
    )
