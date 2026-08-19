"""`infoset.vue_du_joueur` : le nom est public, et c'est bien ce que l'encodage consomme.

Le producteur de `VueDuJoueur` etait le seul nom prive de la paire -- une incoherence de la
phase 0, pas une frontiere voulue. Il est rendu public parce que **tout agent** en a besoin :
celui de la phase 2 comme celui de la phase 3. Le garder prive obligerait chaque agent a
importer un nom prive, et l'API publique du moteur pour un agent n'existerait jamais.

Ces cas etablissent trois choses, et la troisieme est la seule qui justifie le nom :

1. le nom **existe** et rend le predicat du paragraphe 4.2 des regles, reimplemente ici sans
   appeler la fonction testee ;
2. la partition ne **perd** ni ne **duplique** aucune carte posee ;
3. **`chaine` et `tenseur` ne consomment que cette partition** -- permuter l'identite des dos
   les laisse identiques, changer une carte visible les fait bouger. Sans le second sens, le
   premier passerait aussi bien si les deux sorties etaient constantes.
"""

from __future__ import annotations

import random

import pytest

from courtisans.cards import ROLES_CACHES, Carte, CartePosee
from courtisans.engine import Engine
from courtisans.infoset import chaine, tenseur, vue_du_joueur
from mesure.instance import ENTRAINEMENT_3J

CONFIG = ENTRAINEMENT_3J


def _etat_avec_des_dos(seed: int, poses: int):
    """Une partie avancee de `poses` tours, jouee au hasard, pour qu'il y ait des Espions."""
    alea = random.Random(50_000 + seed)
    etat = Engine(CONFIG).reset(seed)
    for _ in range(poses):
        if etat.is_terminal():
            break
        etat.apply(alea.choice(etat.legal_actions()))
    return etat


def _partition_selon_les_regles(
    posees: tuple[CartePosee, ...], joueur: int
) -> tuple[list[CartePosee], list[CartePosee]]:
    """Le predicat du paragraphe 4.2, reecrit ici depuis le texte des regles.

    « Pose face cachee dans toutes les zones [...] Le poseur connait son identite ; les autres
    ne voient qu'un dos. » Donc : une carte est un **dos** si son role est cache **et** qu'un
    autre l'a posee. Tout le reste est connu -- faces visibles, et ses propres Espions.

    Reimplemente et non demande au moteur : un test qui appelle la fonction testee pour
    calculer son attendu ne verifie rien (principe 2 de `tests/outils.py`).
    """
    connues, dos = [], []
    for posee in posees:
        if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:
            dos.append(posee)
        else:
            connues.append(posee)
    return connues, dos


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
@pytest.mark.parametrize("joueur", [0, 1, 2])
def test_le_nom_public_rend_la_partition_des_regles(seed: int, joueur: int):
    """`vue_du_joueur` existe, est publique, et rend exactement le predicat du 4.2."""
    etat = _etat_avec_des_dos(seed, poses=8)
    attendues, attendus_dos = _partition_selon_les_regles(
        etat.vue_privilegiee().posees, joueur
    )
    vue = vue_du_joueur(etat, joueur)
    assert list(vue.connues) == attendues
    assert list(vue.dos_adverses) == attendus_dos


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_la_partition_ne_perd_ni_ne_duplique_aucune_carte(seed: int):
    """Chaque carte posee est d'un cote et d'un seul, pour chacun des trois sieges."""
    etat = _etat_avec_des_dos(seed, poses=9)
    posees = etat.vue_privilegiee().posees
    for joueur in range(CONFIG.joueurs):
        vue = vue_du_joueur(etat, joueur)
        reunion = list(vue.connues) + list(vue.dos_adverses)
        assert sorted(reunion, key=lambda p: (p.carte, p.zone.genre)) == sorted(
            posees, key=lambda p: (p.carte, p.zone.genre)
        )
        assert not set(vue.connues) & set(vue.dos_adverses)


def _un_etat_avec_au_moins_deux_dos_pour(joueur: int):
    """Le premier etat rencontre ou `joueur` voit au moins deux dos adverses distincts."""
    for seed in range(40):
        for poses in range(6, 12):
            etat = _etat_avec_des_dos(seed, poses)
            dos = vue_du_joueur(etat, joueur).dos_adverses
            familles = {posee.carte.famille for posee in dos}
            if len(dos) >= 2 and len(familles) >= 2:
                return etat, dos
    raise AssertionError(
        "aucun etat avec deux dos de familles differentes : le cas ne testerait rien"
    )


@pytest.mark.parametrize("joueur", [0, 1, 2])
def test_l_encodage_ne_consomme_que_cette_partition(joueur: int):
    """Permuter l'identite des dos laisse `chaine` et `tenseur` identiques.

    C'est la propriete qui justifie le nom public : ce que l'encodage consomme, **c'est cette
    vue-la**. Les identites sont permutees entre les emplacements, jamais reassignees : une
    reassignation pourrait recreer une carte deja posee ailleurs, donc un plateau impossible.
    """
    etat, dos = _un_etat_avec_au_moins_deux_dos_pour(joueur)
    avant_chaine, avant_tenseur = chaine(etat, joueur), tenseur(etat, joueur)

    indices = [
        indice
        for indice, posee in enumerate(etat.vue_privilegiee().posees)
        if posee in dos
    ]
    cartes = [etat.vue_privilegiee().posees[indice].carte for indice in indices]
    random.Random(1).shuffle(cartes)
    for indice, carte in zip(indices, cartes, strict=True):
        posee = etat._posees[indice]  # noqa: SLF001 - le test triche, pas l'agent
        etat._posees[indice] = CartePosee(carte, posee.zone, posee.poseur)  # noqa: SLF001

    assert chaine(etat, joueur) == avant_chaine
    assert tenseur(etat, joueur) == avant_tenseur


def test_changer_une_carte_visible_fait_bouger_l_encodage():
    """Le sens inverse. Sans lui, le cas precedent passerait si les sorties etaient constantes."""
    etat = _etat_avec_des_dos(0, poses=9)
    joueur = 0
    avant = chaine(etat, joueur)
    visible = next(
        indice
        for indice, posee in enumerate(etat.vue_privilegiee().posees)
        if posee.carte.role not in ROLES_CACHES
    )
    posee = etat._posees[visible]  # noqa: SLF001
    autre_famille = (posee.carte.famille + 1) % CONFIG.familles
    etat._posees[visible] = CartePosee(  # noqa: SLF001
        Carte(autre_famille, posee.carte.role, posee.carte.exemplaire), posee.zone, posee.poseur
    )
    assert chaine(etat, joueur) != avant
