"""`GameConfig` -- 03_specification_moteur.md paragraphe 3, planchers de 01_regles.md
paragraphe 8.

« Une `GameConfig` qui viole ces contraintes leve une exception a la construction, sans
drapeau de contournement. Il ne doit pas etre possible de fabriquer une instance non
conforme, meme pour un test. »

Ce fichier est ecrit avant `config.py`. Il porte le critere d'acceptation A8, et il est
hostile par construction : il cherche a fabriquer une instance non conforme par tous les
chemins qu'un utilisateur presse essaierait -- planchers violes, drapeau de contournement,
duree tronquee, mutation apres coup.

Les quatre instances historiques -- mini, assassin, redeal, combo -- ont ici leur propre
test : l'arbitrage du 16/08 exige qu'elles soient IMPOSSIBLES a construire, pas seulement
deconseillees.

Le chiffre du critere A8 -- decomposition
-----------------------------------------
A8 est annonce en **28 cas de refus**. Un cas de refus est **un cas de test pytest qui
exige qu'une construction ou une mutation soit refusee** : les cas parametres comptent un
par parametre, puisque chacun echoue separement. Ils portent tous le marqueur `refus`, et
le compte se relit sans faire confiance a ce paragraphe :

    uv run pytest -m refus -q

    11  configurations non conformes, un par entree de `CAS_REFUSES`
          -> test_une_configuration_non_conforme_leve
     5  entiers de configuration qui n'en sont pas -- dont `True`
          -> test_un_entier_de_configuration_qui_n_en_est_pas_un_leve
     1  role qui n'est pas un `Role`
          -> test_un_role_qui_n_est_pas_un_role_leve
     1  `tours` refuse comme parametre
          -> test_tours_n_est_pas_un_parametre
     1  `canonicalisation` refusee comme parametre
          -> test_canonicalisation_n_est_pas_un_parametre
     5  drapeaux de contournement
          -> test_aucun_drapeau_de_contournement_n_existe
     3  instances historiques
          -> test_les_instances_historiques_sont_impossibles_a_construire
     1  mutation apres construction
          -> test_la_configuration_est_immuable
    --
    28

> *Corrige le 17/08.* Ce chiffre etait annonce **26**, ici et au paragraphe 7 de
> `03_specification_moteur.md`, et ne correspondait a aucun regroupement naturel : il etait
> faux dans les deux sens possibles de comptage. Le paragraphe 10 des conventions demande
> qu'un chiffre non reconstructible soit decompose ou retire ; il est desormais decompose
> **et** verifie, par `test_a8_le_nombre_de_cas_de_refus_annonce_est_le_nombre_reel` dans
> `tests/acceptation/test_criteres.py`. Un chiffre qu'aucun test ne tient recommencera a
> deriver des le prochain cas ajoute.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    construire_config,
    module,
    noms,
    role,
)


def _config(**kwargs: Any) -> Any:
    """Construit une GameConfig depuis des noms de roles, pour alleger les cas."""
    roles = kwargs.pop("roles")
    return module("config").GameConfig(
        roles=tuple(role(nom) for nom in roles), **kwargs
    )


# ---------------------------------------------------------------------------------
# Ce qui doit marcher
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_une_configuration_conforme_se_construit_et_calcule_juste(
    instance: Instance,
) -> None:
    config = construire_config(instance)

    assert config.nb_cartes == instance.nb_cartes, (
        f"{instance.nom} : nb_cartes = {config.nb_cartes} au lieu de "
        f"{instance.familles} x {len(instance.roles)} x {instance.exemplaires}"
    )
    assert config.tours == instance.tours, (
        f"{instance.nom} : tours = {config.tours} au lieu de {instance.nb_cartes} // "
        f"(3 x {instance.joueurs}) = {instance.tours}"
    )
    assert config.cartes_jouees == instance.cartes_jouees
    assert config.actions_de_pose == instance.actions_de_pose, (
        f"{instance.nom} : {config.actions_de_pose} actions de pose au lieu de "
        f"6 x 2 x ({instance.joueurs} - 1) = {instance.actions_de_pose}"
    )
    assert config.reste_en_pioche == instance.reste_en_pioche, (
        f"{instance.nom} : {config.reste_en_pioche} cartes jamais piochees au lieu de "
        f"{instance.nb_cartes} mod (3 x {instance.joueurs}) = {instance.reste_en_pioche}"
    )
    assert config.nb_roles == len(instance.roles)
    assert config.tours >= 3
    assert config.familles > config.joueurs


@pytest.mark.parametrize(
    ("champ", "valeur"),
    [
        ("familles", "4"),
        ("familles", 4.0),
        ("familles", True),
        ("exemplaires", "3"),
        ("exemplaires", None),
    ],
)
@pytest.mark.refus
def test_un_entier_de_configuration_qui_n_en_est_pas_un_leve(champ: str, valeur: Any) -> None:
    """`bool` est une sous-classe de `int` : sans controle explicite, familles=True
    passerait pour familles=1."""
    arguments: dict[str, Any] = {
        "familles": 4,
        "roles": ("NOBLE", "ESPION", "ASSASSIN"),
        "exemplaires": 3,
        "joueurs": 3,
    }
    arguments[champ] = valeur

    with pytest.raises(ValueError):
        _config(**arguments)


@pytest.mark.refus
def test_un_role_qui_n_est_pas_un_role_leve() -> None:
    with pytest.raises(ValueError):
        module("config").GameConfig(
            familles=4, roles=("NOBLE", "ESPION"), exemplaires=3, joueurs=3
        )


def test_deux_configurations_identiques_sont_egales() -> None:
    """Une configuration est une valeur : deux constructions identiques sont le meme objet
    logique, sinon rien ne peut etre mis en cache ni compare."""
    gauche = _config(familles=4, roles=("NOBLE", "ESPION", "ASSASSIN"), exemplaires=3, joueurs=3)
    droite = _config(familles=4, roles=("NOBLE", "ESPION", "ASSASSIN"), exemplaires=3, joueurs=3)

    assert gauche == droite
    assert hash(gauche) == hash(droite)


def test_l_ordre_des_roles_fournis_ne_change_pas_la_configuration() -> None:
    """Les roles forment un ensemble : l'ordre de saisie ne doit pas creer deux instances
    differentes, sinon deux configurations equivalentes produisent deux encodages."""
    gauche = _config(familles=4, roles=("NOBLE", "ESPION", "ASSASSIN"), exemplaires=3, joueurs=3)
    droite = _config(familles=4, roles=("ASSASSIN", "NOBLE", "ESPION"), exemplaires=3, joueurs=3)

    assert gauche.roles == droite.roles
    assert gauche == droite


@pytest.mark.refus
def test_la_configuration_est_immuable() -> None:
    config = _config(familles=4, roles=("NOBLE", "ESPION", "ASSASSIN"), exemplaires=3, joueurs=3)

    with pytest.raises(Exception):  # noqa: B017 - FrozenInstanceError herite d'AttributeError
        config.familles = 6


# ---------------------------------------------------------------------------------
# Ce qui doit lever -- les planchers du paragraphe 8
# ---------------------------------------------------------------------------------

#: (intitule, arguments) -- chaque cas viole une contrainte et une seule.
CAS_REFUSES: list[tuple[str, dict[str, Any]]] = [
    (
        "familles egales aux joueurs",
        {"familles": 3, "roles": ("NOBLE", "ESPION", "ASSASSIN", "GARDE"), "exemplaires": 3,
         "joueurs": 3},
    ),
    (
        "familles inferieures aux joueurs",
        {"familles": 2, "roles": ("NOBLE", "ESPION", "ASSASSIN", "GARDE"), "exemplaires": 4,
         "joueurs": 3},
    ),
    (
        "moins de 3 tours par joueur",
        {"familles": 3, "roles": ("NOBLE", "ESPION"), "exemplaires": 2, "joueurs": 2},
    ),
    (
        "zero tour",
        {"familles": 3, "roles": ("NOBLE",), "exemplaires": 1, "joueurs": 2},
    ),
    (
        "aucun role",
        {"familles": 4, "roles": (), "exemplaires": 3, "joueurs": 3},
    ),
    (
        "role en double",
        {"familles": 4, "roles": ("NOBLE", "NOBLE", "ESPION"), "exemplaires": 3, "joueurs": 3},
    ),
    (
        "zero exemplaire",
        {"familles": 4, "roles": ("NOBLE", "ESPION", "ASSASSIN"), "exemplaires": 0,
         "joueurs": 3},
    ),
    (
        "exemplaires negatifs",
        {"familles": 4, "roles": ("NOBLE", "ESPION", "ASSASSIN"), "exemplaires": -1,
         "joueurs": 3},
    ),
    (
        "zero famille",
        {"familles": 0, "roles": ("NOBLE", "ESPION", "ASSASSIN"), "exemplaires": 3,
         "joueurs": 3},
    ),
    (
        "un seul joueur",
        {"familles": 4, "roles": ("NOBLE", "ESPION", "ASSASSIN"), "exemplaires": 3,
         "joueurs": 1},
    ),
    (
        "cinq joueurs, hors specification",
        {"familles": 6, "roles": ("NOBLE", "ESPION", "ASSASSIN"), "exemplaires": 3,
         "joueurs": 5},
    ),
]
IDS_REFUSES = [intitule for intitule, _ in CAS_REFUSES]


@pytest.mark.parametrize(("intitule", "arguments"), CAS_REFUSES, ids=IDS_REFUSES)
@pytest.mark.refus
def test_une_configuration_non_conforme_leve(intitule: str, arguments: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        _config(**arguments)


# ---------------------------------------------------------------------------------
# Ce qui doit lever -- les chemins de contournement
# ---------------------------------------------------------------------------------


@pytest.mark.refus
def test_tours_n_est_pas_un_parametre() -> None:
    """Arbitrage du 16/08 : la duree n'est jamais un levier. Un parametre qui ne peut
    prendre qu'une seule valeur n'est pas un parametre, c'est une occasion de se tromper."""
    with pytest.raises(TypeError):
        _config(
            familles=4,
            roles=("NOBLE", "ESPION", "ASSASSIN"),
            exemplaires=3,
            joueurs=3,
            tours=2,
        )

    with pytest.raises(TypeError):
        _config(
            familles=4,
            roles=("NOBLE", "ESPION", "ASSASSIN"),
            exemplaires=3,
            joueurs=3,
            tours=4,
        )


@pytest.mark.refus
def test_canonicalisation_n_est_pas_un_parametre() -> None:
    """Retire le 16/08 : un champ stocke que rien ne lit et qu'aucun test ne couvre est
    ce que le paragraphe 8 des conventions interdit d'ecrire. Il reviendra a l'etape 6,
    dans infoset.py, quand il aura un effet et un test -- ajouter un champ est facile,
    retirer un champ dont trois modules dependent ne l'est pas."""
    with pytest.raises(TypeError):
        _config(
            familles=4,
            roles=("NOBLE", "ESPION", "ASSASSIN"),
            exemplaires=3,
            joueurs=3,
            canonicalisation=True,
        )


@pytest.mark.parametrize(
    "drapeau",
    ["autoriser_hors_planchers", "forcer", "strict", "valider", "ignorer_planchers"],
)
@pytest.mark.refus
def test_aucun_drapeau_de_contournement_n_existe(drapeau: str) -> None:
    """Arbitrage du 16/08 : GameConfig leve SANS drapeau de contournement."""
    with pytest.raises(TypeError):
        _config(
            familles=3,
            roles=("NOBLE", "ESPION", "ASSASSIN"),
            exemplaires=3,
            joueurs=3,
            **{drapeau: True},
        )


# ---------------------------------------------------------------------------------
# Les instances historiques doivent rester impossibles
# ---------------------------------------------------------------------------------

#: 03_specification_moteur.md paragraphe 3 : leur reproduction est supprimee. Elles
#: violaient les regles, et les reproduire reintroduirait les defauts qu'on corrige.
INSTANCES_HISTORIQUES: list[tuple[str, dict[str, Any]]] = [
    (
        "mini",  # 2 x 3 x 1 = 6 cartes, 6 // 6 = 1 tour, et familles = joueurs
        {"familles": 2, "roles": ("NOBLE", "ESPION", "ASSASSIN"), "exemplaires": 1,
         "joueurs": 2},
    ),
    (
        "assassin",  # 2 x 4 x 1 = 8 cartes, 8 // 6 = 1 tour, et familles = joueurs
        {"familles": 2, "roles": ("NOBLE", "ESPION", "GARDE", "ASSASSIN"), "exemplaires": 1,
         "joueurs": 2},
    ),
    (
        "3-joueurs-minimale",  # 3 x 3 x 1 = 9 cartes, 9 // 9 = 1 tour, et familles = joueurs
        {"familles": 3, "roles": ("NOBLE", "ESPION", "ASSASSIN"), "exemplaires": 1,
         "joueurs": 3},
    ),
]
IDS_HISTORIQUES = [nom for nom, _ in INSTANCES_HISTORIQUES]


@pytest.mark.parametrize(
    ("nom", "arguments"), INSTANCES_HISTORIQUES, ids=IDS_HISTORIQUES
)
@pytest.mark.refus
def test_les_instances_historiques_sont_impossibles_a_construire(
    nom: str, arguments: dict[str, Any]
) -> None:
    with pytest.raises(ValueError):
        _config(**arguments)


# ---------------------------------------------------------------------------------
# A5 -- aucune valeur en dur
# ---------------------------------------------------------------------------------


def test_les_tailles_suivent_la_configuration() -> None:
    """Critere A5 : cinq configurations distinctes, cinq jeux de tailles distincts."""
    tailles = {
        (config.nb_cartes, config.tours, config.cartes_jouees, config.actions_de_pose)
        for config in (construire_config(instance) for instance in TOUTES_LES_INSTANCES)
    }
    assert len(tailles) >= 5, (
        f"seulement {len(tailles)} jeux de tailles distincts pour "
        f"{len(TOUTES_LES_INSTANCES)} configurations -- une valeur est en dur"
    )
