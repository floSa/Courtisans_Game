"""Le chiffre qui porte le rejet, epingle -- et l'incoherence qui l'a d'abord fait mentir.

Mon premier rapport a annonce **deux** comptes de retournements invisibles sur les **memes**
seeds 0-999 : 70 evenements dans 66 parties, puis 81 dans 75. Les deux etaient justes. Ils
different parce que le **decalage de politique** differait -- `DECALAGE_AUDITEUR` (`10**9`)
pour mon controle de stabilite, `DECALAGE_CONSTRUCTEUR` (`1_000_000`) pour la comparaison
chiffre a chiffre avec son rapport. Meme grain, meme definition, memes 1 000 donnes, mais
pas les memes parties : la politique ne fait pas les memes choix, donc les cartes ne vont
pas aux memes endroits.

Ce fichier existe pour que ca ne se reproduise pas. Il epingle les deux comptes avec leur
echantillon, et il nomme celui qui est opposable au sien.

**Le chiffre du rejet est celui sous `DECALAGE_CONSTRUCTEUR`** : c'est le seul calcule sur
les parties exactes ou son rapport annonce 0.
"""

from __future__ import annotations

import pytest

from audit.intervalle import par_quantile_beta
from audit.mesure import (
    DECALAGE_AUDITEUR,
    DECALAGE_CONSTRUCTEUR,
    INSTANCE_PHASE_1,
    joue_campagne,
)


@pytest.mark.lent
@pytest.mark.parametrize(
    ("decalage", "evenements", "parties"),
    [
        # Sous SON decalage : les parties exactes de son rapport. C'est le chiffre du rejet.
        (DECALAGE_CONSTRUCTEUR, 81, 75),
        # Sous le mien : d'autres parties sur les memes donnes, donc un autre compte.
        (DECALAGE_AUDITEUR, 70, 66),
    ],
    ids=["decalage constructeur -- opposable a son 0", "decalage auditeur -- mon controle"],
)
def test_les_deux_comptes_de_l_invisible_sur_les_memes_seeds(
    decalage: int, evenements: int, parties: int
) -> None:
    """Les deux comptes, chacun avec son echantillon. Aucun n'est faux ; ils ne se melangent pas."""
    campagne = joue_campagne(INSTANCE_PHASE_1, range(0, 1000), decalage)
    assert campagne.invisibles_totaux() == evenements
    assert campagne.parties_avec_invisible() == parties


@pytest.mark.lent
def test_le_chiffre_du_rejet_et_son_intervalle() -> None:
    """Sur les parties exactes ou son rapport annonce 0, j'en compte 81 dans 75 parties.

    Son rapport : « R2 vrai, vu par AUCUN des trois joueurs : 0.00% (0 / 1000) ».
    Ici, sur les memes 1 000 parties : 75/1000, IC99 [5,51 % ; 9,90 %]. La borne basse de
    l'intervalle exclut 0 -- ce n'est pas un desaccord d'arrondi.
    """
    campagne = joue_campagne(INSTANCE_PHASE_1, range(0, 1000), DECALAGE_CONSTRUCTEUR)
    parties = campagne.parties_avec_invisible()
    assert (campagne.invisibles_totaux(), parties) == (81, 75)
    basse, haute = par_quantile_beta(parties, 1000)
    assert round(basse * 100, 2) == 5.51
    assert round(haute * 100, 2) == 9.90
    assert basse > 0.0, "un intervalle qui contiendrait 0 ne contredirait pas son chiffre"


@pytest.mark.lent
def test_le_second_bloc_sous_son_decalage() -> None:
    """Seeds 1000-1999, son bloc de controle, ou il annonce aussi 0 : j'en compte 61 dans 57.

    Les deux blocs donnent donc 75/1000 et 57/1000, soit **une partie sur 13,3 a 17,5** --
    et non « sur treize a quinze », comme mon premier rapport l'ecrivait a tort.
    """
    campagne = joue_campagne(INSTANCE_PHASE_1, range(1000, 2000), DECALAGE_CONSTRUCTEUR)
    assert (campagne.invisibles_totaux(), campagne.parties_avec_invisible()) == (61, 57)
    assert round(1000 / 57, 1) == 17.5
    assert round(1000 / 75, 1) == 13.3


@pytest.mark.lent
def test_l_echelle_dagregation_sur_son_propre_code() -> None:
    """L'echelle qui localise son 0 : partie, puis famille, puis evenement.

    Le niveau 1 est **son** calcul, le niveau 2 est **son code et sa definition** avec la
    seule agregation des familles retiree, le niveau 3 est mon compteur d'evenements.

    Passe si `mesure/` est present dans l'arbre, ignore sinon : ce paquet appartient au
    constructeur et n'est pas commite dans cette branche d'audit.
    """
    rapport_constructeur = pytest.importorskip(
        "mesure.rapport", reason="mesure/ appartient au constructeur, absent de cette branche"
    )
    partie_constructeur = pytest.importorskip("mesure.partie")
    grain = partie_constructeur.Grain.TOUR
    vue = partie_constructeur.Vue

    siennes = rapport_constructeur.jouer_campagne(1000, 0)

    niveau_1 = sum(
        1
        for p in siennes
        if p.retournements(grain, vue.VRAIE).r2
        and not any(p.retournements(grain, vue.du_joueur(j)).r2 for j in range(3))
    )
    niveau_2 = sum(
        1
        for p in siennes
        for f in range(4)
        if p.retournements_par_famille(grain, vue.VRAIE)[f].r2
        and not any(
            p.retournements_par_famille(grain, vue.du_joueur(j))[f].r2 for j in range(3)
        )
    )
    campagne = joue_campagne(INSTANCE_PHASE_1, range(0, 1000), DECALAGE_CONSTRUCTEUR)
    niveau_3 = campagne.invisibles_totaux()

    assert niveau_1 == 0, "son chiffre doit se reproduire, sinon je critique autre chose"
    assert niveau_2 == 5, "sa definition, son code, sans agreger les familles"
    assert niveau_3 == 81
    assert niveau_1 < niveau_2 < niveau_3
