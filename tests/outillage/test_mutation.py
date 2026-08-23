"""L'outil de mutation, eprouve. **Il n'avait aucun cas, et c'est lui qui juge la suite.**

Ce qui a rendu ce module necessaire, le 23/08/2026 : le releve d'etape 0 de la phase 4 a ete
commite avec un document qu'un cas de la suite exigeait de nommer. La suite est passee au
rouge, et `outillage/mutation.py` n'a **aucun moyen de le savoir** -- il ecrivait `detectee`
des que `rouges` etait non nul, sans jamais mesurer le rouge preexistant.

Une campagne rejouee sur ce depot aurait rendu **56 detectees, 0 survivante, 1 expiree** : un
feu vert integral et faux, sur l'instrument meme qui venait de publier onze survivantes.

Les cas ci-dessous ne rejouent aucune suite -- ils couteraient 169 s chacun. Ils exercent les
**invariants** de l'outil, ceux dont la violation rend un releve faux sans rien lever.
"""

from __future__ import annotations

import ast
from collections import Counter

import pytest

from outillage.mutation import (
    FICHIERS_EXEMPTS,
    MUTATIONS,
    RACINE,
    refus_de_la_passe_de_base,
)

# ---------------------------------------------------------------------------------
# La passe de base -- la regle qui refuse de lire un ecart contre un zero inconnu
# ---------------------------------------------------------------------------------


def test_une_passe_de_base_VERTE_laisse_la_campagne_commencer():
    """Etablit : sur `(1172 verts, 0 rouge)`, l'outil ne refuse pas. Population : la passe
    de base d'un depot sain."""
    assert refus_de_la_passe_de_base(1172, 0, len(MUTATIONS)) is None


def test_une_passe_de_base_ROUGE_ARRETE_la_campagne():
    """Etablit : sur `(1171 verts, 1 rouge)` -- l'etat exact du depot le 23/08/2026 --,
    l'outil refuse et nomme la consequence. Population : la passe de base d'un depot casse.

    **C'est le cas qui empeche le defaut de se refaire.** Sans lui, la regle vit dans le corps
    de `principal`, qui joue 57 passes de 169 s : personne ne peut l'exercer.
    """
    refus = refus_de_la_passe_de_base(1171, 1, len(MUTATIONS))
    assert refus is not None, (
        "un seul rouge preexistant suffit a faire sortir les 57 mutations `detectee` : "
        "l'outil doit refuser de commencer, pas rapporter une suite parfaite"
    )
    assert "ROUGE" in refus and str(len(MUTATIONS)) in refus, refus


def test_une_cible_qui_ne_collecte_RIEN_arrete_aussi_la_campagne():
    """Etablit : `(0 vert, 0 rouge)` est refuse. Population : une cible pytest vide.

    Un zero-zero passe le test « pas de rouge » et ne mesure rien du tout : les mutations
    seraient toutes lues contre une suite vide, et sortiraient toutes survivantes. C'est le
    symetrique du cas precedent -- l'autre facon dont un instrument ment sans lever.
    """
    assert refus_de_la_passe_de_base(0, 0, len(MUTATIONS)) is not None


# ---------------------------------------------------------------------------------
# Les invariants du catalogue -- ce qui rend un releve lisible
# ---------------------------------------------------------------------------------


def test_chaque_motif_apparait_EXACTEMENT_une_fois_dans_son_fichier():
    """Etablit : les 57 `avant` sont uniques dans leur fichier. Population : le catalogue.

    `_appliquer` leve deja sur ce cas, mais **en pleine campagne**, apres avoir joue les
    mutations precedentes. Le verifier ici le fait tomber en une seconde au lieu d'une heure.
    """
    fautifs = {
        m.nom: (RACINE / m.fichier).read_text(encoding="utf-8").count(m.avant)
        for m in MUTATIONS
        if (RACINE / m.fichier).read_text(encoding="utf-8").count(m.avant) != 1
    }
    assert not fautifs, (
        f"un motif qui n'apparait pas exactement une fois ne designe pas la ligne qu'il "
        f"croit muter : {fautifs}"
    )


def test_chaque_version_mutee_reste_du_PYTHON_VALIDE():
    """Etablit : les 57 textes mutes se parsent. Population : le catalogue.

    **Sans ce cas, une « detection » peut n'etre qu'une `SyntaxError`** : la suite entiere
    tombe a la collecte, l'outil compte des rouges, et le releve porte `detectee` sur une
    mutation qui n'a jamais rien exerce. Le chiffre serait juste et la conclusion fausse.
    """
    fautifs = []
    for mutation in MUTATIONS:
        source = (RACINE / mutation.fichier).read_text(encoding="utf-8")
        mute = source.replace(mutation.avant, mutation.apres)
        assert mute != source, f"{mutation.nom} ne change rien"
        try:
            ast.parse(mute)
        except SyntaxError as erreur:
            fautifs.append(f"{mutation.nom} : {erreur}")
    assert not fautifs, "versions mutees invalides :\n  " + "\n  ".join(fautifs)


def test_les_noms_de_mutation_sont_deux_a_deux_distincts():
    """Etablit : aucun doublon parmi les 57 noms. Population : le catalogue.

    `--nom` et `--noms` selectionnent par le nom, et le releve s'y indexe : deux mutations
    homonymes rendraient deux verdicts sous une seule ligne.
    """
    doublons = {n: c for n, c in Counter(m.nom for m in MUTATIONS).items() if c > 1}
    assert not doublons, doublons


def test_aucune_mutation_ne_vise_l_ETALON():
    """Etablit : `agents/greedy.py` porte 0 mutation. Population : le catalogue.

    C'est le §0.3 du protocole, et le seul invariant que la regle du perimetre protegeait :
    un agent de reference se documente au lieu de se corriger, et le muter deplacerait la
    ligne de base a laquelle toutes les phases se comparent.
    """
    vises = [m.nom for m in MUTATIONS if m.fichier in FICHIERS_EXEMPTS]
    assert not vises, (
        f"ces mutations visent un fichier exempt ({sorted(FICHIERS_EXEMPTS)}) : {vises}"
    )


def test_chaque_mutation_vise_un_fichier_QUI_EXISTE():
    """Etablit : les 57 chemins existent. Population : le catalogue.

    Un fichier renomme laisse une mutation qui ne s'applique plus ; `_appliquer` leverait,
    mais seulement quand la campagne y arrive.
    """
    absents = [m.nom for m in MUTATIONS if not (RACINE / m.fichier).is_file()]
    assert not absents, absents


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda m: m.nom)
def test_chaque_mutation_dit_ce_qu_elle_vise(mutation):
    """Etablit : chaque mutation porte un `vise` non vide. Population : le catalogue.

    Une mutation sans `vise` qui survit nomme un trou que personne ne peut lire.
    """
    assert mutation.vise.strip(), f"{mutation.nom} ne dit pas ce qu'elle casse"
