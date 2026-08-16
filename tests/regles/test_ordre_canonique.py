"""L'ordre canonique des enumerations -- test a valeur figee, volontairement.

**Pourquoi ce test existe.** L'ordre de declaration de `Role` n'est pas une preference
d'ecriture : c'est un contrat. La main est triee par (famille, role, exemplaire), et une
action de pose designe des cartes **par leur rang dans cette main triee**. Deplacer un role
dans l'enumeration deplace donc silencieusement les cartes que chaque action designe --
sans qu'aucun autre test ne tombe, parce que tous les autres tests recalculent leur attendu
avec la meme enumeration que le code.

**Si ce test devient rouge, ce n'est pas lui qu'il faut mettre a jour.** Il faut se
demander pourquoi l'ordre a change, et ce que ce changement casse ailleurs : politiques
entrainees, tenseurs enregistres, parties rejouees depuis un seed. Un ordre modifie rend
toute mesure anterieure incomparable.

C'est le seul endroit du projet ou une valeur est ecrite en dur volontairement. La regle
« aucune valeur en dur » vise le moteur : un test dont l'attendu est calcule par la meme
logique que le code ne verifie rien.
"""

from __future__ import annotations

from tests.outils import cle, module

#: Ordre fige le 16/08. Toute modification est un changement de contrat.
ORDRE_DES_ROLES: tuple[tuple[str, int], ...] = (
    ("ASSASSIN", 0),
    ("GARDE", 1),
    ("NOBLE", 2),
    ("ESPION", 3),
    ("NEUTRE", 4),
)

#: Ordre fige le 16/08. Le signe de l'influence en depend : Estime ajoute, Disgrace retire.
ORDRE_DES_POSITIONS: tuple[tuple[str, int], ...] = (
    ("ESTIME", 0),
    ("DISGRACE", 1),
)

#: Ordre fige le 16/08.
ORDRE_DES_GENRES_DE_ZONE: tuple[tuple[str, int], ...] = (
    ("BANQUET", 0),
    ("DOMAINE", 1),
)


def test_l_ordre_des_roles_est_fige() -> None:
    role_enum = module("cards").Role

    assert [(membre.name, int(membre)) for membre in role_enum] == list(ORDRE_DES_ROLES), (
        "l'ordre de Role a change : le tri canonique de la main change avec lui, donc la "
        "carte que chaque action de pose designe. Ne mets pas ce test a jour sans avoir "
        "verifie ce que ce changement invalide."
    )


def test_l_ordre_des_positions_et_des_genres_de_zone_est_fige() -> None:
    cards = module("cards")

    assert [(m.name, int(m)) for m in cards.Position] == list(ORDRE_DES_POSITIONS)
    assert [(m.name, int(m)) for m in cards.GenreZone] == list(ORDRE_DES_GENRES_DE_ZONE)


def test_le_tri_canonique_produit_l_ordre_attendu_sur_un_cas_fige() -> None:
    """La consequence observable de l'ordre : une main melangee, triee, carte par carte."""
    cards = module("cards")
    rules = module("rules")

    desordre = [
        cards.Carte(1, cards.Role.NEUTRE, 0),
        cards.Carte(0, cards.Role.NOBLE, 1),
        cards.Carte(0, cards.Role.ASSASSIN, 0),
        cards.Carte(0, cards.Role.NOBLE, 0),
        cards.Carte(1, cards.Role.GARDE, 0),
    ]

    assert [cle(carte) for carte in rules.main_canonique(desordre)] == [
        (0, "ASSASSIN", 0),
        (0, "NOBLE", 0),
        (0, "NOBLE", 1),
        (1, "GARDE", 0),
        (1, "NEUTRE", 0),
    ]
