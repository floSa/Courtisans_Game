"""Outils partages des tests de conformite.

Ces tests sont ecrits en lisant `documentations/01_regles.md` -- le paragraphe 9 pour la
liste des controles, et la section que chaque controle cite pour son contenu. Aucun code
de moteur n'a ete lu : au moment ou ils sont ecrits, le moteur n'existe pas. Ils
definissent donc aussi le contrat d'API que le moteur devra respecter.

Trois principes tenus dans tout ce paquet :

1. **Import differe.** Le paquet `courtisans` est importe a l'interieur des fonctions,
   jamais au chargement du module. Tant qu'il n'existe pas, chaque test echoue
   individuellement (rouge) au lieu d'empecher la collecte de toute la suite.

2. **Reimplementation independante.** La valeur des roles, le decompte et la formule de
   gain sont retranscrits ici depuis les regles, jamais demandes au moteur. Un test qui
   appelle le moteur pour calculer son attendu ne verifie rien.

3. **Tolerance a la phase CHANCE.** Le pilote de partie traite `CHANCE` comme n'importe
   quelle autre phase. Le coeur ne l'expose pas (la pioche est fixee par `reset`), mais
   l'adaptateur OpenSpiel de l'etape 7 l'exposera, et ces memes tests devront passer a
   travers lui sans modification.

Contrat du moteur -- quatre regles, pas des commentaires
--------------------------------------------------------
Arbitrees le 16/08. Un moteur qui les viole fait echouer les tests, meme si ses regles
de jeu sont justes.

**R-a. `reset(seed)` et `reset_depuis_pioche(cartes)` partagent le meme code.** Le seed ne
fait rien d'autre que produire l'ordre de la pioche : `reset(seed)` doit etre exactement
`reset_depuis_pioche(pioche_depuis_seed(seed))`. Tout ce qui suit la determination de la
pioche est commun aux deux chemins. Sinon les tests exercent un chemin que la partie reelle
n'emprunte pas -- c'est la divergence qui a coute trois mois au projet precedent.
Verifie par `tests/invariants/test_reset_equivalence.py`.

**R-b. La pioche est consommee dans l'ordre donne.** Les 3 premieres cartes vont au joueur
0, les 3 suivantes au joueur 1, et ainsi de suite, tour de table apres tour de table. Les
`nb_cartes mod (3 x joueurs)` dernieres ne sont jamais tirees ni revelees.

**R-c. `vue_privilegiee().mains[j]` est dans l'ordre canonique du decodage d'action.**
C'est le meme ordre que celui sur lequel `decoder_action_pose` indexe : main triee par
(indice de famille, indice de role). Sans cette egalite, l'indice d'une action ne designe
pas la meme carte pour le moteur et pour le test.

**R-d. `vue_privilegiee()` est une vue de dieu, reservee aux tests et a l'interface.** Elle
n'est jamais exposee a une IA : ce que voit un joueur, c'est `information_state_*`.

Contrat d'API attendu du moteur
-------------------------------
`courtisans.cards`
    `Role`          enum : ASSASSIN, GARDE, NOBLE, ESPION, NEUTRE
    `Position`      enum : ESTIME, DISGRACE
    `GenreZone`     enum : BANQUET, DOMAINE
    `Zone`          gele : `genre`, `position` (None hors banquet), `proprietaire`
                    (None hors domaine) -- les deux attributs existent toujours
    `Carte`         gele : `Carte(famille: int, role: Role, exemplaire: int)`
    `CartePosee`    gele : `carte`, `zone`, `poseur`

`courtisans.config`
    `GameConfig(familles, roles, exemplaires, joueurs)` -- leve si non conforme

`courtisans.rules`
    `decoder_action_pose(action: int, config) -> ActionPose`
        `ActionPose` : `indices_main` (banquet, domaine propre, domaine adverse),
        `position`, `adversaire_relatif`
    `gains_depuis_scores(scores: Sequence[int]) -> list[float]`

`courtisans.engine`
    `Engine(config)`, `.reset(seed) -> State`, `.reset_depuis_pioche(cartes) -> State`
    `Engine.pioche_depuis_seed(seed) -> tuple[Carte, ...]` -- l'ordre de pioche produit
        par un seed, seul effet du seed (regle R-a)
    `State` : `current_player`, `phase`, `legal_actions`, `apply`, `is_terminal`,
    `returns`, `scores`, `information_state_string`, `information_state_tensor`, `clone`
    `State.vue_privilegiee() -> VuePrivilegiee` : `pioche`, `mains`, `posees`, `defausse`
    `State.cibles_courantes() -> tuple[CartePosee, ...]` -- l'indice i de ce tuple est
        l'action i de la phase CIBLAGE, l'indice `len(cibles)` etant le refus de tuer
    `State.assassin_en_resolution() -> CartePosee | None`
"""

from __future__ import annotations

import importlib
import os
import random
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------------
# Transcription des regles, cote test
# ---------------------------------------------------------------------------------

#: 01_regles.md paragraphe 4 -- table des roles. Le Noble vaut 2, tous les autres 1,
#: au banquet comme en domaine (paragraphe 5.1).
VALEUR_PAR_ROLE: dict[str, int] = {
    "ASSASSIN": 1,
    "GARDE": 1,
    "NOBLE": 2,
    "ESPION": 1,
    "NEUTRE": 1,
}

#: 01_regles.md paragraphe 3.1 -- les cinq roles du jeu complet.
ROLES_COMPLETS: tuple[str, ...] = ("ASSASSIN", "GARDE", "NOBLE", "ESPION", "NEUTRE")

#: Sous-ensemble suffisant pour les tests rapides : l'Assassin (paragraphe 4.1), le Garde
#: (cible interdite), l'Espion (carte cachee) et le Noble (valeur 2). Retirer des roles
#: entiers est une reduction autorisee (paragraphe 8).
ROLES_RAPIDES: tuple[str, ...] = ("ASSASSIN", "GARDE", "NOBLE", "ESPION")


@dataclass(frozen=True)
class Instance:
    """Description d'une configuration, cote test, sans dependre du moteur.

    Les proprietes recalculent l'arithmetique du paragraphe 3.4 des regles. Elles servent
    d'attendu : le moteur ne doit jamais etre interroge pour produire la valeur qu'on
    verifie chez lui.
    """

    nom: str
    familles: int
    roles: tuple[str, ...]
    exemplaires: int
    joueurs: int

    @property
    def nb_cartes(self) -> int:
        """01_regles.md paragraphe 3.1 : familles x roles x exemplaires."""
        return self.familles * len(self.roles) * self.exemplaires

    @property
    def tours(self) -> int:
        """01_regles.md paragraphe 3.4 : floor(nb_cartes / (3 x joueurs))."""
        return self.nb_cartes // (3 * self.joueurs)

    @property
    def cartes_jouees(self) -> int:
        """01_regles.md paragraphe 3.4 : 3 x joueurs x tours."""
        return 3 * self.joueurs * self.tours

    @property
    def reste_en_pioche(self) -> int:
        """01_regles.md paragraphe 3.4 / controle C4 : nb_cartes mod (3 x joueurs)."""
        return self.nb_cartes % (3 * self.joueurs)

    @property
    def actions_de_pose(self) -> int:
        """01_regles.md paragraphe 3.2 : 6 x 2 x (joueurs - 1)."""
        return 6 * 2 * (self.joueurs - 1)


# ---------------------------------------------------------------------------------
# Les configurations de test
#
# Toutes respectent les deux planchers du paragraphe 8 des regles :
#   familles > joueurs   et   tours >= 3
# Aucune instance historique (mini, assassin, redeal, combo) n'est reproduite : elles
# violaient les regles, et leur suppression est un arbitrage de l'auteur du 16/08.
# ---------------------------------------------------------------------------------

#: 3 x 4 x 2 = 24 cartes ; 24 // 6 = 4 tours ; 24 mod 6 = 0 carte restante.
RAPIDE_2J = Instance("rapide-2j", familles=3, roles=ROLES_RAPIDES, exemplaires=2, joueurs=2)

#: 4 x 4 x 2 = 32 cartes ; 32 // 9 = 3 tours ; 32 mod 9 = 5 cartes restantes.
RAPIDE_3J = Instance("rapide-3j", familles=4, roles=ROLES_RAPIDES, exemplaires=2, joueurs=3)

#: 5 x 4 x 2 = 40 cartes ; 40 // 12 = 3 tours ; 40 mod 12 = 4 cartes restantes.
RAPIDE_4J = Instance("rapide-4j", familles=5, roles=ROLES_RAPIDES, exemplaires=2, joueurs=4)

#: 4 x 5 x 2 = 40 cartes ; 40 // 9 = 4 tours ; 40 mod 9 = 4 cartes restantes.
ENTRAINEMENT_3J = Instance(
    "entrainement-3j", familles=4, roles=ROLES_COMPLETS, exemplaires=2, joueurs=3
)

#: 6 x 5 x 3 = 90 cartes ; 90 // 6 = 15 tours ; 0 carte restante.
COMPLET_2J = Instance("complet-2j", familles=6, roles=ROLES_COMPLETS, exemplaires=3, joueurs=2)

#: 6 x 5 x 3 = 90 cartes ; 90 // 9 = 10 tours ; 0 carte restante.
COMPLET_3J = Instance("complet-3j", familles=6, roles=ROLES_COMPLETS, exemplaires=3, joueurs=3)

#: 6 x 5 x 3 = 90 cartes ; 90 // 12 = 7 tours ; 90 mod 12 = 6 cartes restantes.
COMPLET_4J = Instance("complet-4j", familles=6, roles=ROLES_COMPLETS, exemplaires=3, joueurs=4)

INSTANCES_RAPIDES: tuple[Instance, ...] = (RAPIDE_2J, RAPIDE_3J, RAPIDE_4J, ENTRAINEMENT_3J)
INSTANCES_COMPLETES: tuple[Instance, ...] = (COMPLET_2J, COMPLET_3J, COMPLET_4J)
TOUTES_LES_INSTANCES: tuple[Instance, ...] = INSTANCES_RAPIDES + INSTANCES_COMPLETES

#: Instances ou des cartes ne sont jamais piochees : seules celles-la permettent d'y
#: cacher une information qu'aucun joueur ne peut deduire (constructions de I7).
INSTANCES_AVEC_RESTE: tuple[Instance, ...] = tuple(
    instance for instance in TOUTES_LES_INSTANCES if instance.reste_en_pioche >= 2
)

#: Nombre de parties par cas de test. C2 exige explicitement 1000 parties (paragraphe 9).
NB_PARTIES_C2 = 1000
NB_PARTIES_C2_COMPLET = 200
NB_PARTIES_BALAYAGE = 200
NB_PARTIES_COURT = 20
NB_PARTIES_INFOSET = 100


def noms(instances: Iterable[Instance]) -> list[str]:
    """Identifiants lisibles pour `pytest.mark.parametrize`."""
    return [instance.nom for instance in instances]


# ---------------------------------------------------------------------------------
# Acces differe au moteur
# ---------------------------------------------------------------------------------


def module(nom: str) -> Any:
    """Importe `courtisans.<nom>`. Leve tant que le moteur n'existe pas."""
    return importlib.import_module(f"courtisans.{nom}")


def role(nom: str) -> Any:
    """Le membre de l'enum `Role` portant ce nom."""
    return getattr(module("cards").Role, nom)


def construire_config(instance: Instance) -> Any:
    """Construit la seule `GameConfig`, sans toucher au moteur.

    Separee de `construire` pour que les tests de configuration ne dependent pas de
    l'existence de `courtisans.engine`.
    """
    return module("config").GameConfig(
        familles=instance.familles,
        roles=tuple(role(nom) for nom in instance.roles),
        exemplaires=instance.exemplaires,
        joueurs=instance.joueurs,
    )


#: Sur quoi tourne la suite. Pilote par la variable d'environnement `COURTISANS_MOTEUR`,
#: pour que les MEMES tests s'executent sur le coeur et a travers l'adaptateur, sans
#: qu'une seule ligne de test ne change (regle d'architecture du paragraphe 2 de la
#: specification).
#:
#:   coeur            le moteur nu. Defaut.
#:   openspiel        l'adaptateur pyspiel, pioche fixee comme dans le coeur.
#:   openspiel-hasard l'adaptateur, mais `reset` ouvre l'arbre a noeuds de chance.
#:                    Reserve a la suite de conformite : la regle R-a compare les deux
#:                    chemins de reset, qui ne peuvent pas coincider quand l'un passe par
#:                    le hasard et l'autre non.
MODE_MOTEUR = os.environ.get("COURTISANS_MOTEUR", "coeur")
MODES_CONNUS = ("coeur", "openspiel", "openspiel-hasard")


class _JeuParHasard:
    """Expose l'arbre a noeuds de chance sous le nom `reset`, pour la suite existante."""

    def __init__(self, jeu: Any) -> None:
        self._jeu = jeu

    def reset(self, seed: int) -> Any:
        return self._jeu.new_initial_state()

    def __getattr__(self, nom: str) -> Any:
        return getattr(self._jeu, nom)


def construire(instance: Instance) -> tuple[Any, Any]:
    """Construit le couple (config, moteur) correspondant a une instance de test."""
    config = construire_config(instance)
    if MODE_MOTEUR == "coeur":
        return config, module("engine").Engine(config)
    if MODE_MOTEUR not in MODES_CONNUS:
        raise ValueError(
            f"COURTISANS_MOTEUR={MODE_MOTEUR!r} inconnu, attendu l'un de {MODES_CONNUS}"
        )
    jeu = module("openspiel_adapter").CourtisansGame(config=config)
    if MODE_MOTEUR == "openspiel":
        return config, jeu
    return config, _JeuParHasard(jeu)


def paquet_ordonne(instance: Instance) -> list[Any]:
    """Le paquet complet en objets `Carte`, dans un ordre deterministe.

    Sert a fabriquer des pioches explicites pour les tests constructifs (C10, C18).
    """
    carte = module("cards").Carte
    return [
        carte(famille, role(nom_role), exemplaire)
        for famille in range(instance.familles)
        for nom_role in instance.roles
        for exemplaire in range(instance.exemplaires)
    ]


def pioches_jumelles_espion(
    instance: Instance, joueur: int = 0
) -> tuple[list[Any], list[Any], Any, Any]:
    """Deux pioches identiques a l'echange pres de deux Espions caches.

    En A, l'Espion de famille 0 est dans la premiere main de `joueur` et celui de famille 1
    dort dans les cartes jamais piochees ; en B, les deux sont echanges. Le paragraphe 3.4
    des regles garantit que les cartes restantes ne sont ni piochees ni revelees : aucun
    autre joueur ne peut donc distinguer A de B.

    Les deux autres cartes de cette main appartiennent a la derniere famille, donc
    l'Espion occupe le meme rang dans la main triee des deux cotes (regle R-c) et une meme
    action y designe les memes cartes.

    Exige `reste_en_pioche >= 1` et `familles >= 3`.
    """
    assert instance.reste_en_pioche >= 1, (
        f"{instance.nom} : aucune carte jamais piochee, impossible d'y cacher le jumeau"
    )
    assert instance.familles >= 3, f"{instance.nom} : moins de 3 familles"

    carte = module("cards").Carte
    espion_a = carte(0, role("ESPION"), 0)
    espion_b = carte(1, role("ESPION"), 0)
    haute = instance.familles - 1
    accompagnement = [c for c in paquet_ordonne(instance) if c.famille == haute][:2]

    exclues = {cle(espion_a), cle(espion_b)} | {cle(c) for c in accompagnement}
    reste = [c for c in paquet_ordonne(instance) if cle(c) not in exclues]

    avant = 3 * joueur  # cartes distribuees avant la main visee
    apres = instance.cartes_jouees - avant - 3  # cartes tirees ensuite

    def assembler(premier: Any, jumeau: Any) -> list[Any]:
        return [
            *reste[:avant],
            premier,
            *accompagnement,
            *reste[avant : avant + apres],
            jumeau,
            *reste[avant + apres :],
        ]

    return assembler(espion_a, espion_b), assembler(espion_b, espion_a), espion_a, espion_b


# ---------------------------------------------------------------------------------
# Permutation des familles
# ---------------------------------------------------------------------------------


def image_identite(
    identite: tuple[int, str, int], sigma: dict[int, int]
) -> tuple[int, str, int]:
    """L'identite d'une carte apres permutation des familles."""
    famille, nom_role, exemplaire = identite
    return (sigma[famille], nom_role, exemplaire)


def semantique_pose(etat: Any, action: int, config: Any) -> tuple:
    """Ce qu'une action de pose fait reellement : quelles cartes, ou, chez qui.

    Repose sur la regle R-c : `vue_privilegiee().mains[j]` est dans l'ordre sur lequel
    `decoder_action_pose` indexe.
    """
    pose = module("rules").decoder_action_pose(action, config)
    main = etat.vue_privilegiee().mains[etat.current_player()]
    return (
        tuple(cle(main[indice]) for indice in pose.indices_main),
        pose.position.name,
        pose.adversaire_relatif,
    )


def action_image(
    etat_a: Any, action_a: int, etat_b: Any, sigma: dict[int, int], config: Any
) -> int:
    """L'action de B qui fait a la permutation pres ce que `action_a` fait en A.

    Jamais l'action de meme indice : le tri canonique de la main porte sur l'indice de
    famille, donc permuter les familles reordonne la main.
    """
    phase = etat_a.phase().name
    if phase == "POSE":
        identites, position, adversaire = semantique_pose(etat_a, action_a, config)
        cible = (
            tuple(image_identite(identite, sigma) for identite in identites),
            position,
            adversaire,
        )
        candidates = [
            action
            for action in etat_b.legal_actions()
            if semantique_pose(etat_b, action, config) == cible
        ]
        assert len(candidates) == 1, (
            f"{len(candidates)} action(s) de B correspondent a l'action {action_a} de A"
        )
        return candidates[0]

    if phase == "CIBLAGE":
        cibles_a = list(etat_a.cibles_courantes())
        cibles_b = list(etat_b.cibles_courantes())
        assert len(cibles_a) == len(cibles_b), (
            f"{len(cibles_a)} cibles en A contre {len(cibles_b)} en B"
        )
        if action_a == len(cibles_a):
            return len(cibles_b)
        attendu = image_identite(cle(cibles_a[action_a].carte), sigma)
        candidates = [
            indice for indice, cible in enumerate(cibles_b) if cle(cible.carte) == attendu
        ]
        assert len(candidates) == 1
        return candidates[0]

    raise AssertionError(
        f"phase {phase} non geree : le rejeu par permutation n'est defini que pour POSE "
        f"et CIBLAGE"
    )


# ---------------------------------------------------------------------------------
# Lecture de la vue privilegiee
# ---------------------------------------------------------------------------------


def cle(carte: Any) -> tuple[int, str, int]:
    """Identite d'une carte : (famille, nom du role, exemplaire). Unique dans le paquet."""
    return (carte.famille, carte.role.name, carte.exemplaire)


def cles(cartes_posees: Iterable[Any]) -> list[tuple[int, str, int]]:
    """Identites des cartes portees par une suite de `CartePosee`."""
    return [cle(posee.carte) for posee in cartes_posees]


def cartes_presentes(vue: Any) -> list[tuple[int, str, int]]:
    """Toutes les cartes du jeu, ou qu'elles soient : pioche, mains, plateau, defausse."""
    presentes = [cle(carte) for carte in vue.pioche]
    for main in vue.mains:
        presentes.extend(cle(carte) for carte in main)
    presentes.extend(cles(vue.posees))
    presentes.extend(cles(vue.defausse))
    return presentes


def paquet_attendu(instance: Instance) -> list[tuple[int, str, int]]:
    """Le multiensemble de cartes qu'une instance doit contenir (paragraphe 3.1)."""
    return [
        (famille, nom_role, exemplaire)
        for famille in range(instance.familles)
        for nom_role in instance.roles
        for exemplaire in range(instance.exemplaires)
    ]


def nb_placees(vue: Any) -> int:
    """Nombre de cartes deja posees, vivantes ou mortes.

    Un meurtre deplace une carte de `posees` vers `defausse` : ce total n'est donc modifie
    que par une pose, jamais par une resolution d'Assassin.
    """
    return len(vue.posees) + len(vue.defausse)


def mortes(etat: Any) -> set[tuple[int, str, int]]:
    """Identites des cartes deja tuees."""
    return {cle(posee.carte) for posee in etat.vue_privilegiee().defausse}


def signature_zone(zone: Any) -> tuple[str, str | None, int | None]:
    """Une zone, sous une forme comparable et lisible dans un message d'erreur."""
    return (
        zone.genre.name,
        zone.position.name if zone.position is not None else None,
        zone.proprietaire,
    )


def signature_posee(posee: Any) -> tuple:
    """Une carte posee : son identite, sa zone, son poseur."""
    return (cle(posee.carte), signature_zone(posee.zone), posee.poseur)


def au_banquet(cartes_posees: Iterable[Any]) -> list[Any]:
    return [posee for posee in cartes_posees if posee.zone.genre.name == "BANQUET"]


def en_domaine(cartes_posees: Iterable[Any]) -> list[Any]:
    return [posee for posee in cartes_posees if posee.zone.genre.name == "DOMAINE"]


# ---------------------------------------------------------------------------------
# Pilote de partie
# ---------------------------------------------------------------------------------


def actions_legales(etat: Any) -> list[int]:
    """Les actions legales, avec le controle qu'il en existe toujours au moins une.

    01_regles.md paragraphe 10bis : il n'existe aucun etat de blocage legal.
    """
    actions = list(etat.legal_actions())
    assert actions, "etat non terminal sans aucune action legale (regles, paragraphe 10bis)"
    return actions


def jouer(etat: Any, rng: random.Random) -> Any:
    """Joue jusqu'au terminal en tirant uniformement parmi les actions legales.

    Traite `CHANCE` comme les autres phases, pour que ces tests restent valables une fois
    rejoues a travers l'adaptateur OpenSpiel.
    """
    while not etat.is_terminal():
        etat.apply(rng.choice(actions_legales(etat)))
    return etat


def partie(moteur: Any, seed: int) -> Any:
    """Une partie complete, jouee au hasard mais de facon reproductible."""
    return jouer(moteur.reset(seed), random.Random(seed))


def rejouer_en_parallele(etat_a: Any, etat_b: Any, rng: random.Random) -> Iterator[tuple[Any, Any]]:
    """Rejoue deux parties en lockstep : meme action appliquee aux deux.

    Livre le couple d'etats avant chaque action. N'a de sens que si les deux parties ne
    different que par une information cachee : si les actions legales divergent, le test
    echoue ici, ce qui est le resultat recherche.
    """
    while not etat_a.is_terminal():
        assert not etat_b.is_terminal(), "les deux parties n'ont pas la meme longueur"
        assert etat_a.phase().name == etat_b.phase().name, (
            f"phases divergentes : {etat_a.phase().name} contre {etat_b.phase().name}"
        )
        assert etat_a.current_player() == etat_b.current_player()
        assert list(etat_a.legal_actions()) == list(etat_b.legal_actions()), (
            "une information cachee change les actions legales"
        )
        yield etat_a, etat_b
        action = rng.choice(actions_legales(etat_a))
        etat_a.apply(action)
        etat_b.apply(action)
    assert etat_b.is_terminal(), "les deux parties n'ont pas la meme longueur"


def empreinte(etat: Any, instance: Instance) -> tuple:
    """Signature complete d'un etat : tout ce qu'un test peut en observer.

    Sert a exiger que deux etats soient identiques, pas seulement equivalents : phase,
    joueur courant, actions legales, contenu integral du plateau, et la vue de chaque
    joueur. Utilisee par la regle R-a et l'invariant I10.
    """
    vue = etat.vue_privilegiee()
    plateau = (
        tuple(cle(carte) for carte in vue.pioche),
        tuple(tuple(cle(carte) for carte in main) for main in vue.mains),
        tuple(signature_posee(posee) for posee in vue.posees),
        tuple(signature_posee(posee) for posee in vue.defausse),
    )
    if etat.is_terminal():
        return (
            "TERMINAL",
            plateau,
            tuple(scores_moteur(etat, instance)),
            tuple(round(gain, 12) for gain in etat.returns()),
        )
    return (
        etat.phase().name,
        etat.current_player(),
        tuple(etat.legal_actions()),
        plateau,
        tuple(etat.information_state_string(j) for j in range(instance.joueurs)),
        tuple(
            tuple(etat.information_state_tensor(j)) for j in range(instance.joueurs)
        ),
    )


def parcourir_decisions(moteur: Any, nb_parties: int) -> Iterator[tuple[int, Any]]:
    """Parcourt `nb_parties` parties et livre (seed, etat) a chaque noeud de decision.

    L'etat livre est vivant : le test l'inspecte, puis le parcours joue une action au
    hasard et continue. Les etats terminaux ne sont pas livres.
    """
    for seed in range(nb_parties):
        etat = moteur.reset(seed)
        rng = random.Random(seed)
        while not etat.is_terminal():
            yield seed, etat
            etat.apply(rng.choice(actions_legales(etat)))


# ---------------------------------------------------------------------------------
# Decompte, reimplemente depuis le paragraphe 5 des regles
# ---------------------------------------------------------------------------------


def influence_par_famille(cartes_banquet: Iterable[Any], instance: Instance) -> dict[int, int]:
    """`d` = somme des valeurs en Estime moins somme des valeurs en Disgrace.

    01_regles.md paragraphe 5.1. Tout se compte en VALEUR : un Noble pese 2.
    """
    influence = dict.fromkeys(range(instance.familles), 0)
    for posee in cartes_banquet:
        signe = 1 if posee.zone.position.name == "ESTIME" else -1
        influence[posee.carte.famille] += signe * VALEUR_PAR_ROLE[posee.carte.role.name]
    return influence


def statuts(cartes_banquet: Iterable[Any], instance: Instance) -> dict[int, int]:
    """Statut de chaque famille : +1 Lumiere, -1 Obscurite, 0 Indifferente.

    01_regles.md paragraphe 5.1. Une famille sans carte vivante au banquet est
    Indifferente.
    """
    return {
        famille: (1 if valeur >= 1 else (-1 if valeur <= -1 else 0))
        for famille, valeur in influence_par_famille(cartes_banquet, instance).items()
    }


def scores_attendus(vue: Any, instance: Instance) -> list[int]:
    """Le decompte du paragraphe 5, reimplemente ici.

    Cartes vivantes seulement, points au proprietaire du domaine, rien pour le banquet.
    """
    statut = statuts(au_banquet(vue.posees), instance)
    points = [0] * instance.joueurs
    for posee in en_domaine(vue.posees):
        valeur = VALEUR_PAR_ROLE[posee.carte.role.name]
        points[posee.zone.proprietaire] += statut[posee.carte.famille] * valeur
    return points


def scores_si_morts_comptes(vue: Any, instance: Instance) -> list[int]:
    """Variante FAUSSE : les cartes tuees comptent. Sert a prouver que C9 discrimine."""
    toutes = list(vue.posees) + list(vue.defausse)
    statut = statuts(au_banquet(toutes), instance)
    points = [0] * instance.joueurs
    for posee in en_domaine(toutes):
        valeur = VALEUR_PAR_ROLE[posee.carte.role.name]
        points[posee.zone.proprietaire] += statut[posee.carte.famille] * valeur
    return points


def scores_credites_au_poseur(vue: Any, instance: Instance) -> list[int]:
    """Variante FAUSSE : les points vont au poseur. Sert a prouver que C11 discrimine."""
    statut = statuts(au_banquet(vue.posees), instance)
    points = [0] * instance.joueurs
    for posee in en_domaine(vue.posees):
        valeur = VALEUR_PAR_ROLE[posee.carte.role.name]
        points[posee.poseur] += statut[posee.carte.famille] * valeur
    return points


def scores_avec_banquet_paye(vue: Any, instance: Instance) -> list[int]:
    """Variante FAUSSE : le banquet rapporte a son poseur. Sert a prouver que C12 discrimine."""
    statut = statuts(au_banquet(vue.posees), instance)
    points = scores_attendus(vue, instance)
    for posee in au_banquet(vue.posees):
        valeur = VALEUR_PAR_ROLE[posee.carte.role.name]
        points[posee.poseur] += statut[posee.carte.famille] * valeur
    return points


def scores_sans_espions(vue: Any, instance: Instance) -> list[int]:
    """Variante FAUSSE : les Espions ne comptent pas. Sert a prouver que C10 discrimine."""
    vivantes = [posee for posee in vue.posees if posee.carte.role.name != "ESPION"]
    statut = statuts(au_banquet(vivantes), instance)
    points = [0] * instance.joueurs
    for posee in en_domaine(vivantes):
        valeur = VALEUR_PAR_ROLE[posee.carte.role.name]
        points[posee.zone.proprietaire] += statut[posee.carte.famille] * valeur
    return points


def scores_moteur(etat: Any, instance: Instance) -> list[int]:
    """Les scores bruts rendus par le moteur, ramenes a une liste indexee par joueur."""
    scores = etat.scores()
    return [scores[joueur] for joueur in range(instance.joueurs)]


def gains_attendus(scores: Sequence[int]) -> list[float]:
    """La formule de gain du paragraphe 5.2, reimplementee ici.

    Vainqueur unique : +1 ; k ex aequo : +(n - k) / (k (n - 1)) ; perdant : -1 / (n - 1).
    """
    nb_joueurs = len(scores)
    meilleur = max(scores)
    nb_vainqueurs = sum(1 for score in scores if score == meilleur)
    gain_vainqueur = (nb_joueurs - nb_vainqueurs) / (nb_vainqueurs * (nb_joueurs - 1))
    return [
        gain_vainqueur if score == meilleur else -1 / (nb_joueurs - 1) for score in scores
    ]
