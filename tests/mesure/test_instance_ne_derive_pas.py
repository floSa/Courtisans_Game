"""L'instance mesuree est celle que les tests decrivent -- et si elle derive, ca se DIT.

La reserve laissee ouverte par l'audit de la phase 1
----------------------------------------------------
`mesure/instance.py` porte `ENTRAINEMENT_3J`, un `GameConfig` : c'est l'instance que TOUTE
mesure du depot utilise. `tests/outils.py` en porte une seconde description du meme nom, un
`Instance`, qui recalcule l'arithmetique des regles **sans importer le moteur** et sert
d'attendu aux tests de conformite. Les deux sont volontairement des objets differents --
une description qui appellerait le moteur pour produire son attendu ne verifierait rien.

**Mais rien ne les reliait**, et c'est la reserve de la phase 1.

Ce que le pilote a mesure le 20/08/2026, et pourquoi ca ne suffisait pas
------------------------------------------------------------------------
Le garde-fou a ete EPROUVE en injectant la derive dans `mesure/instance.py`, `familles=4`
passe a `5` : **21 tests tombent**. Il n'est donc pas muet, et ce cas-ci ne pretend pas le
rendre moins muet.

Le probleme est ailleurs : **aucun des 21 ne dit que l'instance a derive.** Ils echouent
tous sur des nombres calcules a la main -- dans `tests/mesure/test_parties_construites.py`,
`tests/mesure/test_comportements.py` et `tests/audit/test_echelle_de_l_invisible.py` -- avec
pour message « son chiffre doit se reproduire ». Un lecteur qui voit 21 chiffres cesser de
se reproduire cherche un defaut dans les compteurs, pas dans la configuration : le garde-fou
existait **par accident, pas par intention**.

Ce cas est cette intention. Il n'ajoute pas de couverture, il ajoute un **message**.

**Ce qu'il est, MESURE, et ce qu'il n'est pas.** Injection refaite le 20/08/2026,
`familles=4` -> `5` dans `mesure/instance.py`, suite entiere : **22 cas tombent**, soit les
21 du pilote plus celui-ci -- 21 dans `tests/mesure/`, 1 dans `tests/audit/`. Les trois
fichiers que le pilote nommait sont bien la.

Il n'est **pas** le premier a tomber : `pytest tests/mesure tests/audit` le donne en
**deuxieme**, derriere
`test_comportements.py::test_la_trace_d_une_vraie_partie_a_les_bons_comptes`. Une premiere
redaction de cette docstring affirmait le contraire, par un raisonnement sur l'ordre
alphabetique des fichiers qui oubliait que `test_comportements` precede `test_instance`.
C'est ecrit ici plutot que corrige en silence : la phrase fausse etait dans le texte qui
fermait la reserve, ce qui est le mode de defaut du projet.

Ce qu'il apporte ne depend donc pas de son rang, mais de sa **phrase** : un lecteur qui voit
vingt-deux chiffres cesser de se reproduire trouve, dans le lot, une ligne qui nomme la
cause au lieu de vingt-deux qui decrivent chacune un symptome.

Pourquoi il compare les parametres ET l'arithmetique
-----------------------------------------------------
Comparer les quatre parametres etablirait que les deux descriptions s'accordent. Comparer
aussi les quatre grandeurs derivees -- 40 cartes, 4 tours, 36 jouees, 4 jamais piochees --
etablit que **l'arithmetique du protocole tient encore**, ce qui est une seconde chose : une
configuration pourrait s'accorder avec sa description et cesser d'etre celle sur laquelle
les phases 1 et 2 ont ete jouees, si le paragraphe 3.4 des regles etait relu autrement.

Les valeurs de droite sont ecrites **en clair, a la main**, depuis le paragraphe 3 du
protocole et le paragraphe 3.4 des regles. Les recalculer depuis l'une des deux descriptions
serait exactement la faute que la phase 2 a payee : deux implementations qui partagent la
meme hypothese fausse concordent parfaitement.
"""

from __future__ import annotations

from courtisans.config import CARTES_PAR_TOUR
from mesure.instance import ENTRAINEMENT_3J as MESUREE
from tests.outils import ENTRAINEMENT_3J as DECRITE

#: Le message que la phase 1 aurait voulu lire. Prefixe de chaque assertion : il faut qu'il
#: soit lisible en tete d'un `pytest -q`, avant le detail du parametre fautif.
DERIVE = (
    "L'INSTANCE A DERIVE. `mesure.instance.ENTRAINEMENT_3J` n'est plus l'instance sur "
    "laquelle les phases 1 et 2 ont ete jouees. Tous les autres echecs de mesure qui "
    "suivent -- chiffres qui ne se reproduisent plus dans test_parties_construites.py, "
    "test_comportements.py, test_echelle_de_l_invisible.py -- en decoulent : ne les "
    "corrige pas un par un, corrige la configuration."
)


def test_l_instance_mesuree_est_celle_que_les_tests_decrivent():
    """Les quatre parametres, puis les quatre grandeurs derivees. Un seul cas, a dessein."""
    assert MESUREE.familles == DECRITE.familles == 4, (
        f"{DERIVE}\n  familles : mesuree={MESUREE.familles}, "
        f"decrite={DECRITE.familles}, protocole=4"
    )
    assert tuple(role.name for role in MESUREE.roles) == DECRITE.roles, (
        f"{DERIVE}\n  roles : mesuree={tuple(r.name for r in MESUREE.roles)}, "
        f"decrite={DECRITE.roles}"
    )
    assert len(MESUREE.roles) == 5, (
        f"{DERIVE}\n  roles : {len(MESUREE.roles)} au lieu des 5 du protocole -- "
        f"« les 5 roles, aucun mecanisme retire »"
    )
    assert MESUREE.exemplaires == DECRITE.exemplaires == 2, (
        f"{DERIVE}\n  exemplaires : mesuree={MESUREE.exemplaires}, "
        f"decrite={DECRITE.exemplaires}, protocole=2"
    )
    assert MESUREE.joueurs == DECRITE.joueurs == 3, (
        f"{DERIVE}\n  joueurs : mesuree={MESUREE.joueurs}, "
        f"decrite={DECRITE.joueurs}, protocole=3"
    )

    # Les quatre grandeurs derivees. `4 x 5 x 2 = 40 ; 40 // 9 = 4 ; 4 x 9 = 36 ; 40 - 36 = 4`.
    assert MESUREE.nb_cartes == DECRITE.nb_cartes == 40, (
        f"{DERIVE}\n  cartes : mesuree={MESUREE.nb_cartes}, "
        f"decrite={DECRITE.nb_cartes}, protocole=40 (4 x 5 x 2)"
    )
    assert MESUREE.tours == DECRITE.tours == 4, (
        f"{DERIVE}\n  tours par joueur : mesuree={MESUREE.tours}, "
        f"decrite={DECRITE.tours}, protocole=4 (40 // 9)"
    )
    assert DECRITE.cartes_jouees == 36, (
        f"{DERIVE}\n  cartes jouees : decrite={DECRITE.cartes_jouees}, protocole=36"
    )
    assert DECRITE.reste_en_pioche == 4, (
        f"{DERIVE}\n  jamais piochees : decrite={DECRITE.reste_en_pioche}, protocole=4"
    )

    # Le plancher du paragraphe 8 des regles, qui est la RAISON de ces valeurs et non une
    # consequence : la variante a 20 cartes est refusee a la construction par `tours >= 3`,
    # et `familles > joueurs` est la contrainte de conception enoncee par l'auteur.
    assert MESUREE.tours >= 3, f"{DERIVE}\n  le plancher `tours >= 3` du paragraphe 8 tombe"
    assert MESUREE.familles > MESUREE.joueurs, (
        f"{DERIVE}\n  le plancher `familles > joueurs` du paragraphe 8 tombe : aucune "
        f"strategie d'alliance n'emerge quand chacun a sa propre famille"
    )


def test_les_deux_descriptions_restent_deux_objets_differents():
    """La reserve ne se ferme pas en fusionnant les deux descriptions.

    Si un lecteur pressse `mesure.instance` et `tests.outils` l'une dans l'autre pour faire
    taire le cas ci-dessus, l'attendu serait produit par ce qu'il verifie et les tests de
    conformite ne testeraient plus rien. Ce cas rend cette fusion bruyante.

    `CARTES_PAR_TOUR` est importe pour etablir que la description **n'en depend pas** : elle
    ecrit son propre `3` depuis le paragraphe 3.2 des regles.
    """
    assert type(MESUREE) is not type(DECRITE), (
        "`mesure.instance.ENTRAINEMENT_3J` et `tests.outils.ENTRAINEMENT_3J` sont devenus "
        "le meme type : la description cote test ne peut plus servir d'attendu independant."
    )
    assert not hasattr(DECRITE, "nb_cartes_depuis_le_moteur"), (
        "la description cote test interroge le moteur pour produire son attendu"
    )
    assert CARTES_PAR_TOUR == 3, (
        "le moteur ne pose plus 3 cartes par tour : la description cote test, qui ecrit ce "
        "3 a la main depuis le paragraphe 3.2, doit etre relue avant d'etre reparee"
    )
