"""Les sept comportements B1 a B7, rendus mesurables.

Le paragraphe 7.2 des regles les decrit **en prose**. Ce module applique les sept definitions
operationnelles pre-inscrites au paragraphe 6 de `mesure/phase2_hypothese_et_instrument.md`,
et pour chacune la ou les definitions **concurrentes**, dont le chiffre est publie a cote.

Le type porte ce qu'un chiffre doit porter
------------------------------------------
`Compte` transporte son numerateur, son **denominateur**, le **grain** de ce denominateur et la
**vue** sur laquelle le compteur est defini. Ce n'est pas de la decoration : la faute de la
phase 1 etait un chiffre juste dont la phrase parlait de retournements quand le calcul parlait
de parties. Un taux dont le sujet grammatical n'est pas l'unite comptee doit publier son
denominateur -- ici il ne peut pas ne pas le publier.

La regle d'arbitrage des vues, appliquee aux sept
-------------------------------------------------
**Un comportement est une decision, et une decision se prend sur ce que le decideur sait.** La
vue du decideur est donc primaire partout ou le compteur qualifie un choix ; la vue publique
-- le savoir commun -- est rapportee a cote, parce qu'elle repond a une autre question : « le
coup etait-il conteste aux yeux d'un observateur ». **La vue publique n'est la vue de
personne.**

Une exception, de regle et non de gout : **ce qui PAIE se calcule sur la vue vraie**, tous les
Espions etant retournes avant le decompte (paragraphes 4.2 et 5 des regles). B1 et B7 ont donc
des clauses sur deux vues differentes, et leur docstring dit laquelle porte sur quoi.

Ce que ces compteurs ne disent pas
----------------------------------
**Le greedy a un horizon d'un tour.** Un motif B1 ou B3 observe chez lui est une
**coincidence**, jamais un plan. Les fonctions s'appellent `motif_b1` et `motif_b3` pour cette
raison : un nom ne mente pas (paragraphe 7 des conventions).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from courtisans import rules
from courtisans.cards import VALEURS, Carte, CartePosee, GenreZone, Position, Role
from courtisans.config import GameConfig
from courtisans.engine import Phase
from courtisans.rules import Statut
from mesure.trace import Decision, TracePartie, est_au_banquet

#: Les trois vues, nommees pour qu'un `Compte` dise sur laquelle il est defini. Reprend les
#: noms de `mesure.partie.Vue`, dont la docstring etablit que la vue publique n'est la vue de
#: personne.
VUE_DECIDEUR = "decideur"
VUE_PUBLIQUE = "publique"
VUE_VRAIE = "vraie"
VUE_MIXTE = "decideur pour le choix, vraie pour ce qui paie"


@dataclass(frozen=True)
class Compte:
    """Un numerateur, son denominateur, le grain de ce denominateur, et sa vue.

    Attributes:
        nom: l'identifiant de la definition, concurrentes comprises.
        succes: le numerateur.
        total: le denominateur.
        grain: **ce que compte le denominateur**, en mots. « parties », « poses au banquet »,
            « refus »... Sans lui, un taux ne dit pas de quoi il est le taux.
        vue: sur quelle vue le compteur est defini.
    """

    nom: str
    succes: int
    total: int
    grain: str
    vue: str

    def taux(self) -> float | None:
        """La proportion, ou `None` si le denominateur est nul.

        **Rend `None` et ne leve pas** : un denominateur nul est un resultat -- l'occasion ne
        s'est pas presentee -- et il doit se rapporter tel quel. Rendre 0 ferait lire « ce
        comportement n'apparait jamais » la ou il faut lire « la situation n'est jamais
        survenue ». C'est la meme faute que celle de la phase 1, a un cran de plus.
        """
        return None if self.total == 0 else self.succes / self.total

    def __str__(self) -> str:
        taux = self.taux()
        part = "sans objet" if taux is None else f"{100 * taux:.2f} %"
        return f"{self.nom} : {part} ({self.succes}/{self.total} {self.grain}, vue {self.vue})"


# ---------------------------------------------------------------------------------
# Briques communes
# ---------------------------------------------------------------------------------


def _vue_apres_la_pose(decision: Decision) -> tuple[CartePosee, ...]:
    """Ce que le poseur voit juste apres son coup, avant toute resolution d'Assassin.

    Ses trois cartes lui sont connues par construction : il vient de les poser.
    """
    return decision.connues + decision.cartes_posees


def _compte_par_type(cartes: Sequence[Carte]) -> dict[tuple[int, Role], int]:
    """Comptes par `(famille, role)`."""
    comptes: dict[tuple[int, Role], int] = {}
    for carte in cartes:
        cle = (carte.famille, carte.role)
        comptes[cle] = comptes.get(cle, 0) + 1
    return comptes


def _residu_vu(decision: Decision, config: GameConfig) -> dict[tuple[int, Role], int]:
    """Le residu par type, tel que le decideur peut le calculer.

    `exemplaires - connues - main - mortes`, exactement la regle 2 du bloc `residu` de
    l'encodage : **la defausse est publique** (paragraphe 4.1), donc le residu est exact. En
    oublier les morts surestime ce qui circule et fait defendre des familles hors d'atteinte.
    """
    connues = _compte_par_type([posee.carte for posee in decision.connues])
    main = _compte_par_type(decision.main)
    mortes = _compte_par_type(decision.mortes)
    return {
        (famille, role): config.exemplaires
        - connues.get((famille, role), 0)
        - main.get((famille, role), 0)
        - mortes.get((famille, role), 0)
        for famille in range(config.familles)
        for role in config.roles
    }


def _poids_de_bascule_disponible(
    decision: Decision, famille: int, influence: int, config: GameConfig
) -> int:
    """Combien l'influence de `famille` peut encore varier, borne par deux contraintes.

    **Borne de materiel** : la valeur totale des cartes de `famille` encore en circulation --
    chacune posable du cote defavorable -- plus la valeur des cartes de `famille` vivantes du
    cote **favorable** au banquet qu'un Assassin pourrait tuer, un Garde excepte.

    **Borne d'occasions** : chaque pose restante place exactement une carte au banquet, qui
    fait varier `d` d'au plus 2 (un Noble) ; et si cette carte est un Assassin, elle peut en
    retirer 2 de plus. Donc `4` par pose restante, ce qui est large et **volontairement
    genereux** : une borne trop serree declarerait « hors d'atteinte » des familles qui ne le
    sont pas, et gonflerait B7.

    Le minimum des deux. *Proposition de l'agent*, comme le dit le paragraphe 6.7 de la
    pre-inscription : elle est chiffree et publiee, pas reprise d'un document existant.
    """
    residu = _residu_vu(decision, config)
    materiel = sum(
        compte * VALEURS[role]
        for (fam, role), compte in residu.items()
        if fam == famille and compte > 0
    )
    favorable = Position.ESTIME if influence > 0 else Position.DISGRACE
    materiel += sum(
        posee.carte.valeur
        for posee in decision.connues
        if posee.carte.famille == famille
        and est_au_banquet(posee, favorable)
        and posee.carte.role not in rules.ROLES_IMMUNISES_CONTRE_ASSASSIN
    )
    occasions = 4 * sum(decision.tours_restants)
    return min(materiel, occasions)


def _sieges(sieges: Sequence[int] | None, config: GameConfig) -> tuple[int, ...]:
    """Les sieges comptes. `None` veut dire tous -- utile pour la ligne de base aleatoire."""
    return tuple(range(config.joueurs)) if sieges is None else tuple(sieges)


# ---------------------------------------------------------------------------------
# B1 -- le MOTIF de la planification d'un retournement
# ---------------------------------------------------------------------------------


def _evenements_b1(
    trace: TracePartie, siege: int, config: GameConfig
) -> tuple[dict[tuple[int, int], list[int]], dict[int, list[int]]]:
    """Les deux familles d'evenements de B1, pour un siege.

    Rend `(nourrir, baisser)` : `nourrir[(famille, adversaire)]` liste les numeros de nœud ou
    `siege` a donne une carte de cette famille a cet adversaire alors que la famille etait
    **Lumiere ou Indifferente dans SA vue** -- nourrir n'a de sens que si ce n'est pas deja un
    poison. `baisser[famille]` liste les numeros ou il a fait baisser l'influence de la
    famille : une pose au banquet en **Disgrace**, ou un meurtre d'une carte de cette famille
    en **Estime**.
    """
    nourrir: dict[tuple[int, int], list[int]] = {}
    baisser: dict[int, list[int]] = {}
    for decision in trace.decisions:
        if decision.joueur != siege:
            continue
        if decision.phase is Phase.POSE:
            statuts = rules.statuts(decision.connues, config.familles)
            adverse = decision.carte_chez_l_adversaire()
            if adverse is not None and adverse.zone.proprietaire is not None:
                famille = adverse.carte.famille
                if statuts[famille] in (Statut.LUMIERE, Statut.INDIFFERENTE):
                    cle = (famille, adverse.zone.proprietaire)
                    nourrir.setdefault(cle, []).append(decision.numero)
            banquet = decision.carte_de_banquet()
            if banquet is not None and est_au_banquet(banquet, Position.DISGRACE):
                baisser.setdefault(banquet.carte.famille, []).append(decision.numero)
        elif decision.tuee is not None and est_au_banquet(decision.tuee, Position.ESTIME):
            baisser.setdefault(decision.tuee.carte.famille, []).append(decision.numero)
    return nourrir, baisser


def _paye(
    trace: TracePartie, famille: int, adversaire: int, exige_obscurite: bool
) -> bool:
    """Les clauses 3 et 4 de B1, celles qui portent sur la **vue vraie**.

    Clause 3 : au decompte, `famille` n'est pas en Lumiere -- ou est en Obscurite si
    `exige_obscurite`, ce qui est la variante B1-strict. Le statut est celui du plateau final,
    Espions retournes, parce que c'est lui qui **paie** (paragraphes 4.2 et 5 des regles).

    Clause 4 : `adversaire` detient encore au moins une carte **vivante** de la famille. Sans
    elle, un poison qui n'atteint personne compterait comme un retournement planifie.

    Fonction de module et non fermeture : capturer la variable de boucle serait correct ici
    mais fragile, et le refus de `ruff` (B023) vaut mieux qu'un commentaire.
    """
    statut = trace.statuts_finaux[famille]
    attendu = (
        statut is Statut.OBSCURITE if exige_obscurite else statut is not Statut.LUMIERE
    )
    reste = any(
        posee.carte.famille == famille
        for posee in trace.cartes_vivantes_du_domaine(adversaire)
    )
    return attendu and reste


def motif_b1(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """B1 : le MOTIF « nourrir une famille chez un adversaire, puis la basculer ».

    **Ce n'est pas une planification** quand l'agent mesure a un horizon d'un tour. Chez le
    greedy, le motif apparait par **coincidence** : deux actions separees, chacune localement
    optimale, qui forment apres coup la figure d'un plan. Le nom de cette fonction le dit, et
    le rapport doit l'ecrire.

    Retenue -- **B1-motif**, quatre clauses (paragraphe 6.1) :
      1. a `t1`, `siege` pose une carte de famille `f` chez `j`, `f` etant Lumiere ou
         Indifferente **dans sa vue** ;
      2. a `t2 > t1`, il fait baisser l'influence de `f` ;
      3. au decompte, `f` est Indifferente ou en Obscurite **dans la vue vraie** -- c'est le
         statut qui paie ;
      4. au decompte, `j` detient encore au moins une carte de `f` **vivante**.

    Concurrentes publiees a cote : **B1-tentative** sans les clauses 3 et 4, **B1-strict** dont
    la clause 3 exige l'Obscurite, et **B1-collectif** dont `t1` et `t2` peuvent etre de
    joueurs differents.
    """
    comptes = {
        "B1-motif": [0, 0],
        "B1-tentative": [0, 0],
        "B1-strict": [0, 0],
        "B1-collectif": [0, 0],
    }
    retenus = _sieges(sieges, config)
    for trace in traces:
        motif = tentative = strict = collectif = False
        tous_nourrir: dict[tuple[int, int], list[int]] = {}
        tous_baisser: dict[int, list[int]] = {}
        par_siege = {}
        for siege in retenus:
            nourrir, baisser = _evenements_b1(trace, siege, config)
            par_siege[siege] = (nourrir, baisser)
            for cle, numeros in nourrir.items():
                tous_nourrir.setdefault(cle, []).extend(numeros)
            for famille, numeros in baisser.items():
                tous_baisser.setdefault(famille, []).extend(numeros)

        for siege in retenus:
            nourrir, baisser = par_siege[siege]
            for (famille, adversaire), donnes in nourrir.items():
                suivants = [n for n in baisser.get(famille, []) if n > min(donnes)]
                if not suivants:
                    continue
                tentative = True
                if _paye(trace, famille, adversaire, exige_obscurite=False):
                    motif = True
                if _paye(trace, famille, adversaire, exige_obscurite=True):
                    strict = True
        for (famille, adversaire), donnes in tous_nourrir.items():
            suivants = [n for n in tous_baisser.get(famille, []) if n > min(donnes)]
            if suivants and _paye(trace, famille, adversaire, exige_obscurite=False):
                collectif = True

        for nom, valeur in (
            ("B1-motif", motif),
            ("B1-tentative", tentative),
            ("B1-strict", strict),
            ("B1-collectif", collectif),
        ):
            comptes[nom][0] += int(valeur)
            comptes[nom][1] += 1

    return {
        nom: Compte(nom, succes, total, "parties", VUE_MIXTE)
        for nom, (succes, total) in comptes.items()
    }


# ---------------------------------------------------------------------------------
# B2 -- l'Assassin en zone contestee
# ---------------------------------------------------------------------------------


def b2(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """B2 : parmi les poses d'Assassin, celles qui atterrissent dans une zone contestee.

    Retenue -- **B2-contestee** : la zone de destination contient, juste apres la pose, au
    moins une cible valide dont la famille a `|d| <= 1` **dans la vue du poseur**. `|d| <= 1`
    est la fragilite du paragraphe 2.2 des regles : a `d = +/-1`, une carte standard annule et
    un Noble inverse.

    **Pourquoi la vue du poseur et pas le savoir commun.** Un joueur qui a lui-meme pose un
    Espion au banquet voit une zone plus -- ou moins -- contestee que le savoir commun. Compter
    au savoir commun repondrait a « le coup etait-il conteste aux yeux d'un observateur », pas
    a « le decideur croyait-il placer son Assassin la ou il servirait ». Les deux sont publies,
    et leur ecart mesure de combien le savoir prive deplace le jugement.

    Concurrentes : **B2-banquet** (part des Assassins poses au banquet, sans condition
    d'enjeu), **B2-fragile-2** (`|d| <= 2`), **B2-cibles** (au moins une cible valide, sans
    condition d'enjeu -- la borne haute).
    """
    noms = ("B2-contestee", "B2-contestee-publique", "B2-fragile-2", "B2-banquet", "B2-cibles")
    comptes = {nom: 0 for nom in noms}
    total = 0
    retenus = _sieges(sieges, config)
    for trace in traces:
        for decision in trace.poses():
            if decision.joueur not in retenus:
                continue
            for posee in decision.cartes_posees:
                if posee.carte.role not in rules.ROLES_ASSASSINS:
                    continue
                total += 1
                vue = _vue_apres_la_pose(decision)
                publique = tuple(p for p in vue if not p.carte.face_cachee)
                cibles = rules.cibles_valides(vue, posee)
                if cibles:
                    comptes["B2-cibles"] += 1
                if est_au_banquet(posee):
                    comptes["B2-banquet"] += 1
                for nom, source, seuil in (
                    ("B2-contestee", vue, 1),
                    ("B2-contestee-publique", publique, 1),
                    ("B2-fragile-2", vue, 2),
                ):
                    influences = rules.influence(source, config.familles)
                    visees = rules.cibles_valides(source, posee)
                    if any(
                        abs(influences[cible.carte.famille]) <= seuil for cible in visees
                    ):
                        comptes[nom] += 1
    vues = {
        "B2-contestee": VUE_DECIDEUR,
        "B2-contestee-publique": VUE_PUBLIQUE,
        "B2-fragile-2": VUE_DECIDEUR,
        "B2-banquet": VUE_PUBLIQUE,
        "B2-cibles": VUE_DECIDEUR,
    }
    return {
        nom: Compte(nom, comptes[nom], total, "poses d'Assassin", vues[nom]) for nom in noms
    }


def distribution_b2(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """La distribution des quatre destinations d'Assassin, que le paragraphe 7.2 demande.

    Denominateur commun : les poses d'Assassin. Les quatre parts somment donc a 1 -- un
    Assassin va dans une zone et une seule -- et le rapport le verifie.
    """
    noms = ("banquet-Estime", "banquet-Disgrace", "domaine propre", "domaine adverse")
    comptes = {nom: 0 for nom in noms}
    total = 0
    retenus = _sieges(sieges, config)
    for trace in traces:
        for decision in trace.poses():
            if decision.joueur not in retenus:
                continue
            for rang, posee in enumerate(decision.cartes_posees):
                if posee.carte.role not in rules.ROLES_ASSASSINS:
                    continue
                total += 1
                if rang == 0:
                    estime = posee.zone.position is Position.ESTIME
                    comptes["banquet-Estime" if estime else "banquet-Disgrace"] += 1
                elif rang == 1:
                    comptes["domaine propre"] += 1
                else:
                    comptes["domaine adverse"] += 1
    return {
        nom: Compte(nom, comptes[nom], total, "poses d'Assassin", VUE_PUBLIQUE) for nom in noms
    }


# ---------------------------------------------------------------------------------
# B3 -- le MOTIF de l'alliance
# ---------------------------------------------------------------------------------


def motif_b3(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """B3 : donner une carte de famille `f` a `j` alors qu'on est soi-meme expose sur `f`.

    « Expose » : son propre domaine contient deja au moins une carte **vivante** de `f`, connue
    de lui. Les deux ont alors interet a ce que `f` finisse en Lumiere -- c'est l'alliance
    objective du paragraphe 2.4 des regles.

    **Ce n'est pas une alliance fabriquee** quand l'agent a un horizon d'un tour : le greedy ne
    modelise pas l'interet qu'il cree en donnant (paragraphe 7.1). Le motif mesure la
    coincidence entre ce qu'il detient et ce qu'il donne.

    Retenue -- **B3-expose**, sur la vue du decideur : les Espions adverses poses chez lui ne
    lui sont pas identifiables, donc son exposition est ce qu'il en sait. **B3-expose-vraie**
    est publiee a cote. **B3-simultane** exige en plus que `f` soit en Lumiere dans sa vue au
    moment du don -- plus proche d'une intention, donc plus petite.
    """
    noms = ("B3-expose", "B3-expose-vraie", "B3-simultane")
    comptes = {nom: 0 for nom in noms}
    total = 0
    retenus = _sieges(sieges, config)
    for trace in traces:
        for decision in trace.poses():
            if decision.joueur not in retenus:
                continue
            adverse = decision.carte_chez_l_adversaire()
            if adverse is None:
                continue
            total += 1
            famille = adverse.carte.famille
            sources = (
                ("B3-expose", decision.connues),
                ("B3-expose-vraie", decision.posees),
            )
            for nom, source in sources:
                expose = any(
                    posee.carte.famille == famille
                    and posee.zone.proprietaire == decision.joueur
                    and posee.zone.genre is GenreZone.DOMAINE
                    for posee in source
                )
                if expose:
                    comptes[nom] += 1
            expose_vu = any(
                posee.carte.famille == famille
                and posee.zone.proprietaire == decision.joueur
                and posee.zone.genre is GenreZone.DOMAINE
                for posee in decision.connues
            )
            statuts = rules.statuts(decision.connues, config.familles)
            if expose_vu and statuts[famille] is Statut.LUMIERE:
                comptes["B3-simultane"] += 1
    vues = {
        "B3-expose": VUE_DECIDEUR,
        "B3-expose-vraie": VUE_VRAIE,
        "B3-simultane": VUE_DECIDEUR,
    }
    return {
        nom: Compte(nom, comptes[nom], total, "poses en domaine adverse", vues[nom])
        for nom in noms
    }


# ---------------------------------------------------------------------------------
# B4 -- refuser de tuer, en trois nombres
# ---------------------------------------------------------------------------------


def b4(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """B4 : le refus de tuer, decompose en trois -- et deux chiffres de contexte.

    **Le denominateur du taux brut est les nœuds offrant au moins une cible**, jamais tous les
    nœuds : refuser est toujours legal (paragraphe 4.1, arbitrage R2), donc « situations ou
    refuser est possible » vaut 100 % par construction. La phase 1 a mesure que ces nœuds sont
    82,53 % des 7 206 nœuds de 1 000 parties aleatoires.

    Les trois, denominateur = les **refus** (paragraphe 6.4) :
      - **B4-strict** : tout meurtre disponible baissait strictement l'ecart. Un comportement.
      - **B4-departage** : refuser etait a egalite avec au moins un meurtre. Un tirage au sort.
      - **B4-contre-nature** : au moins un meurtre etait strictement meilleur. Un defaut, qui
        doit valoir **0** chez le greedy puisque `choisir` prend un argmax -- publie quand meme,
        parce qu'un zero qu'on n'imprime pas n'est pas un zero verifie.

    Les trois somment a 100 % des refus par construction ; `verifier_b4` le controle.

    Deux chiffres de contexte, sans lesquels les trois precedents ne s'interpretent pas :
      - **B4-brut** : la part de refus, la grandeur que le paragraphe 7.2 demande litteralement ;
      - **B4-tout-dos** : la part des nœuds dont TOUTES les cibles sont des dos. Sur ceux-la
        l'evaluation est plate et c'est le **departage** qui choisit. Si ce chiffre est eleve,
        B4 mesure surtout le departage, et le rapport le dit a cet endroit.

    « Couterait » est juge sur `greedy.evaluer_actions`, pour **tout** agent : deux agents juges
    par deux etalons differents ne se comparent pas.
    """
    noeuds_avec_cible = 0
    tout_dos = 0
    refus = 0
    strict = departage = contre_nature = 0
    meurtres = 0
    meurtre_couteux = 0
    retenus = _sieges(sieges, config)
    for trace in traces:
        for decision in trace.ciblages():
            if decision.joueur not in retenus or not decision.cibles:
                continue
            noeuds_avec_cible += 1
            if decision.toutes_les_cibles_sont_des_dos():
                tout_dos += 1
            indice_refus = len(decision.cibles)
            valeur_refus = decision.valeurs[indice_refus]
            valeurs_meurtres = [
                valeur for action, valeur in decision.valeurs.items() if action != indice_refus
            ]
            meilleur_meurtre = max(valeurs_meurtres)
            if decision.refus():
                refus += 1
                if meilleur_meurtre < valeur_refus:
                    strict += 1
                elif meilleur_meurtre == valeur_refus:
                    departage += 1
                else:
                    contre_nature += 1
            else:
                meurtres += 1
                if meilleur_meurtre < valeur_refus:
                    meurtre_couteux += 1
    return {
        "B4-brut": Compte(
            "B4-brut", refus, noeuds_avec_cible, "nœuds de ciblage a >= 1 cible", VUE_DECIDEUR
        ),
        "B4-strict": Compte("B4-strict", strict, refus, "refus", VUE_DECIDEUR),
        "B4-departage": Compte("B4-departage", departage, refus, "refus", VUE_DECIDEUR),
        "B4-contre-nature": Compte(
            "B4-contre-nature", contre_nature, refus, "refus", VUE_DECIDEUR
        ),
        "B4-tout-dos": Compte(
            "B4-tout-dos",
            tout_dos,
            noeuds_avec_cible,
            "nœuds de ciblage a >= 1 cible",
            VUE_DECIDEUR,
        ),
        "B4-meurtre-couteux": Compte(
            "B4-meurtre-couteux", meurtre_couteux, meurtres, "meurtres", VUE_DECIDEUR
        ),
    }


def verifier_b4(comptes: dict[str, Compte]) -> None:
    """Le controle d'identite : les trois parts somment aux refus.

    Un controle, pas une deduction. Il leve plutot que de rendre un booleen : une identite qui
    tombe designe un compteur faux, et continuer a publier ses chiffres serait pire que
    s'arreter.

    Raises:
        ValueError: si la somme des trois ne vaut pas le nombre de refus.
    """
    trois = ("B4-strict", "B4-departage", "B4-contre-nature")
    somme = sum(comptes[nom].succes for nom in trois)
    refus = comptes["B4-brut"].succes
    if somme != refus:
        raise ValueError(
            f"identite de B4 violee : strict + departage + contre-nature = {somme}, "
            f"or il y a {refus} refus. Un des compteurs est faux."
        )
    for nom in trois:
        if comptes[nom].total != refus:
            raise ValueError(
                f"{nom} a pour denominateur {comptes[nom].total}, or il y a {refus} refus"
            )


# ---------------------------------------------------------------------------------
# B5 -- se mefier des Espions
# ---------------------------------------------------------------------------------


def b5(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """B5 : renforcer le cote deja favorable d'une majorite serree, malgre un dos au banquet.

    Le denominateur est un **couple (nœud, famille)** et non un nœud : plusieurs familles
    peuvent satisfaire les conditions au meme nœud, et compter par nœud melangerait des
    situations distinctes. Conditions, dans la vue du decideur :
      - `|d| = 1` pour la famille `f` au banquet ;
      - au moins **un dos** au banquet, donc la vraie influence peut deja differer ;
      - au moins une carte de `f` en main, donc le renforcement est **possible**.

    Numerateur : le coup pose une carte de `f` au banquet **du cote du signe de `d`**.

    **Chez le greedy ce chiffre ne mesure pas une mefiance** : un dos ne figure pas dans son
    evaluation, donc sa presence n'entre pas dans sa decision. Sa mefiance est nulle par
    construction, et B5 chez lui mesure seulement a quelle frequence son evaluation myope
    l'amene a renforcer. C'est le point de comparaison dont la phase 3 a besoin, et il doit
    etre **ecrit** plutot que deduit.

    Concurrente -- **B5-pire-cas** : `|d|` est remplace par la marge pire cas du paragraphe 2.6
    des regles, `d` diminue de 1 par dos du cote favorable, un dos etant toujours un Espion
    donc de valeur 1. Elle selectionne d'autres couples.
    """
    comptes = {"B5-renfort": [0, 0], "B5-pire-cas": [0, 0]}
    retenus = _sieges(sieges, config)
    for trace in traces:
        for decision in trace.poses():
            if decision.joueur not in retenus:
                continue
            dos_banquet = [p for p in decision.dos_du_plateau() if est_au_banquet(p)]
            if not dos_banquet:
                continue
            influences = rules.influence(decision.connues, config.familles)
            banquet = decision.carte_de_banquet()
            for famille in range(config.familles):
                if not any(carte.famille == famille for carte in decision.main):
                    continue
                marge = influences[famille]
                cote_favorable = Position.ESTIME if marge > 0 else Position.DISGRACE
                renforce = (
                    banquet is not None
                    and banquet.carte.famille == famille
                    and est_au_banquet(banquet, cote_favorable)
                )
                if abs(marge) == 1:
                    comptes["B5-renfort"][1] += 1
                    comptes["B5-renfort"][0] += int(renforce)
                if marge == 0:
                    # **Pas de cote favorable, donc pas de marge pire cas.** Le paragraphe 2.6
                    # des regles definit le pire cas comme « `d` diminue de 1 par dos du cote
                    # favorable » : a `d = 0` la famille est Indifferente, il n'y a rien a
                    # defendre et aucun cote a nommer. Compter ce cas faisait entrer dans le
                    # denominateur des familles dont la marge pire cas valait `0 + 1 = 1` par
                    # le seul effet d'un dos, ce qui est un artefact du calcul et non une
                    # majorite serree. Defaut trouve par
                    # `test_b5_le_pire_cas_selectionne_d_autres_couples`.
                    continue
                dos_favorables = sum(
                    1 for p in dos_banquet if p.zone.position is cote_favorable
                )
                pire = marge - dos_favorables if marge > 0 else marge + dos_favorables
                if abs(pire) == 1:
                    comptes["B5-pire-cas"][1] += 1
                    comptes["B5-pire-cas"][0] += int(renforce)
    return {
        nom: Compte(nom, succes, total, "couples (nœud, famille)", VUE_DECIDEUR)
        for nom, (succes, total) in comptes.items()
    }


# ---------------------------------------------------------------------------------
# B6 -- jouer differemment en fin de partie
# ---------------------------------------------------------------------------------

#: Les categories d'action, fixees AVANT la mesure (paragraphe 6.6). Trois groupes, chacun
#: avec son propre denominateur : melanger les trois dans une seule distribution ferait un
#: chiffre dont on ne saurait pas de quoi il est la part.
GROUPES_B6: dict[str, tuple[str, ...]] = {
    "banquet": ("Estime", "Disgrace"),
    "domaine adverse": ("cadeau", "neutre", "poison"),
    "ciblage": ("refus", "meurtre"),
}


def _categories_du_noeud(decision: Decision, config: GameConfig) -> dict[str, str]:
    """La categorie de ce nœud dans chaque groupe applicable."""
    trouvees: dict[str, str] = {}
    if decision.phase is Phase.POSE:
        banquet = decision.carte_de_banquet()
        if banquet is not None:
            trouvees["banquet"] = (
                "Estime" if banquet.zone.position is Position.ESTIME else "Disgrace"
            )
        adverse = decision.carte_chez_l_adversaire()
        if adverse is not None:
            statuts = rules.statuts(decision.connues, config.familles)
            statut = statuts[adverse.carte.famille]
            trouvees["domaine adverse"] = {
                Statut.LUMIERE: "cadeau",
                Statut.INDIFFERENTE: "neutre",
                Statut.OBSCURITE: "poison",
            }[statut]
    elif decision.cibles:
        trouvees["ciblage"] = "refus" if decision.refus() else "meurtre"
    return trouvees


def distributions_b6(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[tuple[str, int], dict[str, Compte]]:
    """Pour chaque groupe et chaque tour, la distribution des categories.

    Rendue **par tour**, tours intermediaires compris, pour qu'on voie si l'ecart entre le
    premier et le dernier est monotone ou un saut. Chaque `Compte` porte le denominateur de son
    groupe et de son tour ; rien n'est agrege.
    """
    brut: dict[tuple[str, int], dict[str, int]] = {}
    totaux: dict[tuple[str, int], int] = {}
    retenus = _sieges(sieges, config)
    for trace in traces:
        for decision in trace.decisions:
            if decision.joueur not in retenus:
                continue
            for groupe, categorie in _categories_du_noeud(decision, config).items():
                cle = (groupe, decision.tour)
                brut.setdefault(cle, dict.fromkeys(GROUPES_B6[groupe], 0))
                brut[cle][categorie] += 1
                totaux[cle] = totaux.get(cle, 0) + 1
    return {
        cle: {
            categorie: Compte(
                f"B6/{cle[0]}/tour {cle[1]}/{categorie}",
                compte,
                totaux[cle],
                f"nœuds du groupe « {cle[0]} » au tour {cle[1]}",
                VUE_DECIDEUR,
            )
            for categorie, compte in comptes.items()
        }
        for cle, comptes in brut.items()
    }


def distance_de_variation_totale(
    distributions: dict[tuple[str, int], dict[str, Compte]], groupe: str, premier: int, dernier: int
) -> float | None:
    """La distance de variation totale entre le tour `premier` et le tour `dernier`.

    `0,5 * somme des |p_i - q_i|`, donc dans `[0, 1]`.

    **Elle n'est pas nulle chez le greedy, et ce n'est pas une preuve de comprehension** :
    l'etat du plateau change avec le tour, donc un agent a horizon un tour joue mecaniquement
    differemment sans rien savoir de la pioche. C'est exactement pourquoi la ligne de base est
    necessaire -- la phase 3 ne conclura que sur l'**ecart** entre sa distance et celle-ci.

    Rend `None` si l'un des deux tours n'a aucun nœud dans ce groupe : un denominateur nul est
    un resultat, pas un zero.
    """
    debut = distributions.get((groupe, premier))
    fin = distributions.get((groupe, dernier))
    if debut is None or fin is None:
        return None
    total_debut = next(iter(debut.values())).total
    total_fin = next(iter(fin.values())).total
    if total_debut == 0 or total_fin == 0:
        return None
    return 0.5 * sum(
        abs(debut[categorie].succes / total_debut - fin[categorie].succes / total_fin)
        for categorie in GROUPES_B6[groupe]
    )


# ---------------------------------------------------------------------------------
# B7 -- ne pas defendre ce qui est deja sur
# ---------------------------------------------------------------------------------


def b7(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """B7 : les cartes « gaspillees » a renforcer une famille hors d'atteinte.

    Une famille est **hors d'atteinte** si `|d|` depasse le poids de bascule encore
    mobilisable contre elle -- voir `_poids_de_bascule_disponible`, dont les deux bornes sont
    une proposition chiffree de l'agent (paragraphe 6.7).

    Retenue -- **B7-gaspillage** : la pose au banquet place une carte de famille `f` du cote
    **deja favorable** d'une `f` hors d'atteinte, dans la vue du decideur. Denominateur : les
    poses au banquet.

    **B7-occasions** est indispensable a la lecture : la part des poses au banquet ou au moins
    une famille est hors d'atteinte. Sans elle, un B7 bas peut vouloir dire « il ne gaspille
    pas » **ou** « l'occasion ne s'est pas presentee », et rien ne les distingue.

    Concurrente -- **B7-lumiere** : toute pose renforcant une famille deja en Lumiere, sans
    condition de portee. C'est la definition qu'on obtient en oubliant la borne, donc celle qui
    ferait croire a un gaspillage massif ; publier les deux montre ce que la borne retire.
    """
    comptes = {"B7-gaspillage": 0, "B7-gaspillage-vraie": 0, "B7-lumiere": 0, "B7-occasions": 0}
    total = 0
    retenus = _sieges(sieges, config)
    for trace in traces:
        for decision in trace.poses():
            if decision.joueur not in retenus:
                continue
            banquet = decision.carte_de_banquet()
            if banquet is None:
                continue
            total += 1
            for nom, source in (
                ("B7-gaspillage", decision.connues),
                ("B7-gaspillage-vraie", decision.posees),
            ):
                influences = rules.influence(source, config.familles)
                famille = banquet.carte.famille
                marge = influences[famille]
                cote = Position.ESTIME if marge > 0 else Position.DISGRACE
                hors = marge != 0 and abs(marge) > _poids_de_bascule_disponible(
                    decision, famille, marge, config
                )
                if hors and est_au_banquet(banquet, cote):
                    comptes[nom] += 1
            influences = rules.influence(decision.connues, config.familles)
            if influences[banquet.carte.famille] > 0 and est_au_banquet(
                banquet, Position.ESTIME
            ):
                comptes["B7-lumiere"] += 1
            if any(
                influences[famille] != 0
                and abs(influences[famille])
                > _poids_de_bascule_disponible(decision, famille, influences[famille], config)
                for famille in range(config.familles)
            ):
                comptes["B7-occasions"] += 1
    vues = {
        "B7-gaspillage": VUE_DECIDEUR,
        "B7-gaspillage-vraie": VUE_VRAIE,
        "B7-lumiere": VUE_DECIDEUR,
        "B7-occasions": VUE_DECIDEUR,
    }
    return {
        nom: Compte(nom, comptes[nom], total, "poses au banquet", vues[nom]) for nom in vues
    }


# ---------------------------------------------------------------------------------
# Les sept d'un coup
# ---------------------------------------------------------------------------------


def tous_les_comportements(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """Les sept compteurs, definitions concurrentes comprises, dans un seul dictionnaire.

    B6 en est absent : il rend une distribution par tour et par groupe, pas un taux, donc il
    n'a pas la forme d'un `Compte`. `distributions_b6` et `distance_de_variation_totale` le
    rendent separement -- forcer sa forme sur celle des six autres produirait un chiffre dont
    le denominateur ne voudrait rien dire.
    """
    resultats: dict[str, Compte] = {}
    for compteur in (motif_b1, b2, distribution_b2, motif_b3, b4, b5, b7):
        resultats.update(compteur(traces, config, sieges))
    verifier_b4(resultats)
    return resultats
