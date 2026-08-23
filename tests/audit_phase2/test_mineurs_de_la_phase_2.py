"""Les quatre defauts mineurs de la phase 2, fermes au debut de la phase 3.

Chacun est ferme par ce qui l'empeche de se defaire, jamais par une cellule reecrite.

  1. `vue_du_joueur` ne validait pas son argument -- ferme dans `courtisans/infoset.py`,
     tenu par `tests/infoset/test_vue_du_joueur.py` et la mutation
     `vue-du-joueur-contourne-la-parade`. **Pas ici.**
  2. le rapport genere etait en cp1252 -- ferme par `mesure.phase2.main --sortie` et tenu
     par `test_reverification.py`. **Pas ici.**
  3. deux des douze directions comptees comme tenues alors qu'elles sont nulles par
     construction -- ici.
  4. une cellule « voir `B4-departage` » dans une table qui ne se lit qu'en juxtaposant
     deux nombres -- ici.

Les mineurs 3 et 4 sont tous deux des defauts de **texte publie**, donc ils se tiennent par
des cas qui lisent le texte publie. C'est plus faible qu'une exception levee, et il faut le
dire : un texte peut etre reecrit sans que le code bouge. C'est pourquoi le mineur 4 est
ferme **dans le generateur** -- le renvoi ne peut plus revenir sans que le compteur cesse
d'etre passe -- et pourquoi le cas ci-dessous verifie la coherence entre **deux** endroits
du rapport plutot que la presence d'une chaine.
"""

from __future__ import annotations

import pathlib
import re

DEFINITIONS = pathlib.Path("mesure/phase2_definitions_et_concurrentes.md")
JOURNAL_PROPOSE = pathlib.Path("mesure/phase2_entree_de_journal.md")
RAPPORT = pathlib.Path("mesure/resultats/phase2.md")

#: Les deux sens que la pre-inscription declare nuls par construction, **nommes**. Ils le
#: sont au paragraphe 6.4 de `mesure/phase2_hypothese_et_instrument.md` : « B4-contre-nature
#: doit valoir exactement 0 chez le greedy, puisque `choisir` prend un argmax ».
NULS_PAR_CONSTRUCTION: tuple[str, ...] = ("B4-contre-nature", "B4-meurtre-coûteux")


# ---------------------------------------------------------------------------------
# Mineur 3 -- un enonce qui ne peut pas etre faux n'est pas une direction annoncee
# ---------------------------------------------------------------------------------


def test_mineur_3_la_pre_inscription_declare_bien_ces_deux_sens_nuls_par_construction():
    """Le fondement du mineur 3, verifie AVANT le compte qui en decoule.

    Si la pre-inscription ne disait pas cela, la correction du compte serait arbitraire.
    L'unite se reconstruit avant la valeur, et separement.
    """
    pre = pathlib.Path("mesure/phase2_hypothese_et_instrument.md").read_text(
        encoding="utf-8"
    )
    assert "doit valoir exactement 0 chez le greedy" in pre, (
        "la pre-inscription n'annonce plus ces zeros comme obliges : le mineur 3 n'a plus "
        "de fondement, et le compte de sens doit etre relu depuis le texte, pas ajuste."
    )
    assert "`choisir` prend un\nargmax" in pre or "`choisir` prend un argmax" in pre, (
        "la RAISON du zero -- l'argmax -- a disparu de la pre-inscription"
    )


def test_mineur_3_le_compte_des_sens_ne_compte_plus_les_deux_controles():
    """« Onze des douze tiennent » empruntait sa marge a deux enonces que rien ne risquait.

    Le cas verifie les **deux** documents qui portaient le compte, et il verifie le compte
    **decompose** -- 2 controles + 1 infirme + 9 tenus = 12 -- plutot que la seule phrase de
    resume : une phrase se reecrit, une decomposition doit rester coherente.
    """
    definitions = DEFINITIONS.read_text(encoding="utf-8")
    journal = JOURNAL_PROPOSE.read_text(encoding="utf-8")

    for document, texte in ((DEFINITIONS, definitions), (JOURNAL_PROPOSE, journal)):
        assert "onze des douze sens annoncés tiennent" not in texte, (
            f"{document} compte a nouveau les deux controles comme des sens tenus"
        )

    lignes = [x for x in definitions.splitlines() if re.match(r"^\| \d+ \| ", x)]
    assert len(lignes) == 12, f"la table n'a plus douze lignes : {len(lignes)}"

    controles = [x for x in lignes if "⚙️" in x]
    infirmes = [x for x in lignes if "❌" in x]
    tenus = [x for x in lignes if "✅" in x]

    assert len(controles) == 2, f"controles : {len(controles)}, attendu 2"
    assert len(infirmes) == 1, f"sens infirmes : {len(infirmes)}, attendu 1"
    assert len(tenus) == 9, f"sens tenus : {len(tenus)}, attendu 9"
    assert len(controles) + len(infirmes) + len(tenus) == 12

    for nom in NULS_PAR_CONSTRUCTION:
        ligne = next((x for x in controles if nom in x), None)
        assert ligne is not None, (
            f"`{nom}` n'est plus marque comme controle dans la table des douze sens. "
            f"Les deux nuls par construction sont {NULS_PAR_CONSTRUCTION} -- des NOMS, "
            f"pas un compte."
        )


# ---------------------------------------------------------------------------------
# Mineur 4 -- une table qui renvoie ailleurs pour la moitie de son propos ne se lit pas
# ---------------------------------------------------------------------------------


def test_mineur_4_la_table_du_departage_porte_ses_deux_nombres():
    """Le texte dit « elle ne se lit qu'en juxtaposant les deux nombres » : les deux y sont.

    Le cas ne cherche pas l'absence du renvoi -- une absence se satisfait d'une cellule
    vide. Il exige que la cellule porte un **taux** et sa **fraction**, et que ce taux soit
    celui que la section 5 publie pour `B4-departage` : c'est la coherence entre deux
    endroits du meme rapport qui etablit qu'un seul site l'a calcule.
    """
    rapport = RAPPORT.read_text(encoding="utf-8")

    debut = rapport.index("Le departage change")
    table = rapport[debut : rapport.index("Autrement dit", debut)]

    assert "voir `B4-departage`" not in table, (
        "la cellule renvoie a nouveau vers la section 5 au lieu de porter son nombre"
    )

    cellule = re.search(
        r"part des refus du greedy que le \*\*departage\*\* decide.*?"
        r"\*\*([\d.]+) %\*\* \((\d+)/(\d+)\)",
        table,
    )
    assert cellule is not None, f"la cellule ne porte pas taux et fraction :\n{table}"
    taux_table, numerateur, denominateur = cellule.groups()

    section5 = re.search(
        r"\| `B4-departage` \| ([\d.]+) % \((\d+)/(\d+)\)", rapport
    )
    assert section5 is not None, "la ligne `B4-departage` a disparu de la section 5"

    assert (taux_table, numerateur, denominateur) == section5.groups(), (
        f"la table du departage et la section 5 ne disent plus le meme nombre : "
        f"table {cellule.groups()}, section 5 {section5.groups()}. Deux sites de calcul "
        f"ont diverge, ce qui est exactement ce que le passage du compteur devait empecher."
    )

    titre = re.search(r"### Le departage change ([\d.]+) % des refus", rapport)
    assert titre is not None, "le titre ne porte plus de taux"
    assert titre.group(1) == taux_table, (
        f"le titre annonce {titre.group(1)} % et la table {taux_table} % : le titre porte "
        f"a nouveau un nombre en dur, qui survivra a la mesure qui le contredit."
    )
