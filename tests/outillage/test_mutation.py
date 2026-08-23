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
import subprocess
from collections import Counter

import pytest

from outillage.mutation import (
    FICHIERS_EXEMPTS,
    MUTATIONS,
    RACINE,
    refus_de_la_passe_de_base,
    tombes_sous_TOUTES_les_mutations,
)


def _source_commitee(fichier: str) -> str:
    """Le contenu du fichier **tel que HEAD le porte**, jamais celui du disque.

    **Ce detour corrige un defaut que ces cas ont porte le 23/08/2026, et il vaut d'etre
    raconte parce qu'il est ne dans une correction.**

    Les deux cas ci-dessous verifient des invariants du CATALOGUE : « ce motif apparait
    exactement une fois dans sa source », « cette version mutee reste du Python valide ».
    Ecrits contre le disque, ils tombent des qu'une mutation est appliquee -- `_appliquer`
    REMPLACE `avant` par `apres`, donc le fichier ne contient plus le motif cherche.

    Or `outillage/mutation.py` joue la suite ENTIERE avec la mutation en place. Ces deux cas
    tombaient donc **sur les 56 mutations a la fois**, et la campagne rejouee a rendu
    **56 detectees, 0 survivante** : exactement `+2 rouges` sur chaque ligne, sans exception,
    et les onze survivantes reelles effacees.

    **C'est le mode de defaillance que la passe de base venait de fermer, refait par la
    correction elle-meme.** La passe de base ne pouvait pas le voir : elle mesure le zero
    AVANT la premiere mutation, et ces deux cas sont verts tant qu'aucune n'est en place.

    La source commitee est la bonne population : `principal` refuse de tourner sur un depot
    sale et restaure par `git checkout`, donc **HEAD est l'etat pristine par construction**.
    L'invariant porte sur le catalogue contre le depot, pas contre un fichier momentanement
    mute.
    """
    return subprocess.run(
        ["git", "show", f"HEAD:{fichier}"],
        cwd=RACINE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

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
    comptes = {m.nom: _source_commitee(m.fichier).count(m.avant) for m in MUTATIONS}
    fautifs = {nom: c for nom, c in comptes.items() if c != 1}
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
        source = _source_commitee(mutation.fichier)
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

    **Celui-ci lit le disque, et c'est correct** : une mutation en place ne fait pas
    disparaitre son fichier, donc il est insensible a l'etat mute. Voir `_source_commitee`
    pour ce que cette distinction a coute.
    """
    absents = [m.nom for m in MUTATIONS if not (RACINE / m.fichier).is_file()]
    assert not absents, absents


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda m: m.nom)
def test_chaque_mutation_dit_ce_qu_elle_vise(mutation):
    """Etablit : chaque mutation porte un `vise` non vide. Population : le catalogue.

    Une mutation sans `vise` qui survit nomme un trou que personne ne peut lire.
    """
    assert mutation.vise.strip(), f"{mutation.nom} ne dit pas ce qu'elle casse"


# ---------------------------------------------------------------------------------
# Le detecteur de miroir -- ce qui aurait vu le defaut du 23/08/2026
# ---------------------------------------------------------------------------------


def test_un_test_qui_tombe_sous_TOUTES_les_mutations_est_signale():
    """Etablit : l'intersection des tests tombes est rendue. Population : trois passes dont
    un test commun.

    **C'est le cas du defaut reel.** Le 23/08/2026, deux cas de ce fichier meme lisaient le
    disque pour verifier les invariants du catalogue ; sous mutation le motif n'y est plus,
    les deux tombaient, et la campagne a rendu 56 detectees / 0 survivante au lieu de
    45 / 11. Un test qui tombe sous toutes les mutations ne reagit a aucune d'elles.
    """
    miroirs = tombes_sous_TOUTES_les_mutations(
        [
            frozenset({"t::miroir", "t::vrai_a"}),
            frozenset({"t::miroir", "t::vrai_b"}),
            frozenset({"t::miroir"}),
        ]
    )
    assert miroirs == frozenset({"t::miroir"}), miroirs


def test_des_detections_LEGITIMES_ne_sont_pas_signalees():
    """Etablit : sans test commun, rien n'est signale. Population : deux passes disjointes.

    **Le controle doit pouvoir NE PAS se declencher.** Un detecteur qui signale toujours ne
    signale rien -- c'est la meme faute que le garde-fou de portee 1 de la phase 3.
    """
    assert not tombes_sous_TOUTES_les_mutations(
        [frozenset({"t::a"}), frozenset({"t::b"})]
    )


def test_le_detecteur_de_miroir_ne_leve_pas_sur_ZERO_passe():
    """Etablit : sur aucune passe, l'ensemble vide. Population : le cas degenere.

    L'intersection de rien n'est pas definie ; rendre l'ensemble vide est la seule reponse
    qui ne fabrique pas un signalement a partir d'une absence de mesure.
    """
    assert tombes_sous_TOUTES_les_mutations([]) == frozenset()
