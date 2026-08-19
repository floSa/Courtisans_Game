"""Mes sept compteurs B1 a B7, ecrits depuis le paragraphe 7.2 des regles.

Trois principes, chacun tire d'une faute deja payee par ce projet.

**Un taux porte son unite et son denominateur.** L'erreur du tour 1 de la phase 1 n'etait
ni un calcul faux ni un DEDUIT presente comme un MESURE : c'etait un chiffre juste dont
la phrase parlait de retournements quand le calcul parlait de parties. `Taux` oblige donc
a nommer ce qu'on compte, et refuse de repondre autrement.

**Un denominateur vide n'est pas un zero.** `0/0` n'a pas de valeur. Une instance sans
Assassin n'a « 0 % de refus de tuer » : elle n'a **aucun noeud de ciblage**, et la
question ne se pose pas. `Taux.valeur` rend `None`, et le rendu ecrit le denominateur
vide en toutes lettres.

**Ce qui est mesure ici est un motif, pas une intention.** Le greedy a un horizon d'un
tour (paragraphe 7.1) : il ne planifie rien. B1 et B3 comptent donc chez lui la frequence
a laquelle le **motif** apparait par coincidence. C'est la bonne ligne de base -- c'est
meme la seule interpretable -- mais la phrase qui la publie doit le dire.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from audit.phase2.decompte import LUMIERE, statut, valeur
from audit.phase2.trace import EvenementCiblage, EvenementPose, Trace
from courtisans.cards import GenreZone, Position, Role


@dataclass(frozen=True)
class Taux:
    """Un comptage, avec ce qu'il compte et sur quoi il le rapporte.

    Attributes:
        nom: l'identifiant du compteur.
        unite: **l'objet compte**, au singulier. C'est le sujet grammatical que la phrase
            publiee devra employer : « x % des poses chez un adversaire », pas « x % des
            parties », si l'unite est la pose.
        numerateur: combien d'unites satisfont le critere.
        denominateur: combien d'unites ont ete examinees.
    """

    nom: str
    unite: str
    numerateur: int
    denominateur: int

    def __post_init__(self) -> None:
        if self.denominateur < 0 or self.numerateur < 0:
            raise ValueError(f"{self.nom} : comptes negatifs")
        if self.numerateur > self.denominateur:
            raise ValueError(
                f"{self.nom} : numerateur {self.numerateur} > denominateur "
                f"{self.denominateur}"
            )

    @property
    def valeur(self) -> float | None:
        """La proportion, ou `None` si le denominateur est vide.

        **Ne rend jamais 0.0 sur un denominateur vide.** Un taux sans observation n'est
        pas un taux nul : c'est une question qui ne se pose pas.
        """
        if self.denominateur == 0:
            return None
        return self.numerateur / self.denominateur

    def texte(self) -> str:
        """Le taux rendu lisible, denominateur compris. Jamais un pourcentage seul."""
        if self.denominateur == 0:
            return (
                f"{self.nom} : NON DEFINI -- 0 {self.unite} observe, un taux sur un "
                f"denominateur vide n'existe pas"
            )
        return (
            f"{self.nom} : {self.numerateur} / {self.denominateur} {self.unite} = "
            f"{100 * self.numerateur / self.denominateur:.2f} %"
        )

    def plus(self, autre: Taux) -> Taux:
        """Somme de deux comptages du meme compteur -- pour agreger des parties."""
        if self.nom != autre.nom or self.unite != autre.unite:
            raise ValueError(f"comptages incompatibles : {self.nom} et {autre.nom}")
        return Taux(
            self.nom,
            self.unite,
            self.numerateur + autre.numerateur,
            self.denominateur + autre.denominateur,
        )


def cumule(taux: Iterable[Taux]) -> Taux:
    """Agrege des comptages du meme compteur sur plusieurs parties."""
    total: Taux | None = None
    for un in taux:
        total = un if total is None else total.plus(un)
    if total is None:
        raise ValueError("aucun comptage a cumuler")
    return total


# ---------------------------------------------------------------------------------
# Outils partages
# ---------------------------------------------------------------------------------


def _signe(position: Position) -> int:
    """`+1` en Estime, `-1` en Disgrace : le signe que la carte apporte a `d`."""
    return 1 if position is Position.ESTIME else -1


def _renforce(d: int, pose: EvenementPose) -> bool:
    """Vrai si la carte du banquet **eloigne** sa famille de l'Indifference.

    Le seuil est celui du paragraphe 2.2 : ce qui compte est la distance a `d = 0`.
    """
    apport = _signe(pose.banquet.zone.position) * valeur(pose.banquet.carte.role)
    return abs(d + apport) > abs(d)


def _reduit(d: int, apport: int) -> bool:
    """Vrai si `apport` rapproche `d` de zero ou le traverse."""
    return abs(d + apport) < abs(d) or (d > 0 > d + apport) or (d < 0 < d + apport)


def _zone_assassin(evenement: EvenementCiblage) -> str:
    """La categorie de zone ou l'Assassin a ete pose, pour la distribution de B2."""
    zone = evenement.assassin.zone
    if zone.genre is GenreZone.BANQUET:
        return "banquet_estime" if zone.position is Position.ESTIME else "banquet_disgrace"
    return "domaine_propre" if zone.proprietaire == evenement.joueur else "domaine_adverse"


# ---------------------------------------------------------------------------------
# B1 -- planifier un retournement
# ---------------------------------------------------------------------------------


def b1(trace: Trace, *, seuil_final: str = "hors_lumiere", exiger_cadeau: bool = False) -> Taux:
    """Nourrir une famille chez un adversaire, puis la basculer.

    Paragraphe 7.2 : « nourrir une famille chez un adversaire, puis la basculer en
    Obscurite en fin de partie ». Le seuil retenu est pourtant l'**Indifference**, et non
    l'Obscurite, parce que l'encadre du paragraphe 2.2 tranche deja : « Le seuil qui
    compte est l'Indifference, pas l'Obscurite. [...] Raisonner uniquement sur le
    basculement en Obscurite fait croire une position sure alors qu'elle est fragile. »
    Une famille passee de Lumiere a Indifferente a bien annule le cadeau : les cartes de
    l'adversaire ne rapportent plus rien.

    Args:
        seuil_final: `hors_lumiere` (retenu) ou `obscurite` (concurrente, lecture stricte
            du paragraphe 7.2).
        exiger_cadeau: si vrai, la famille doit avoir ete en Lumiere a l'instant de la
            pose -- concurrente qui ne compte que les cadeaux devenus poison.

    Returns:
        Un taux dont l'unite est **la pose chez un adversaire**. Chaque tour en produit
        exactement une, donc le denominateur vaut `joueurs x tours`.
    """
    if seuil_final not in ("hors_lumiere", "obscurite"):
        raise ValueError(f"seuil final inconnu : {seuil_final!r}")

    bascules: dict[tuple[int, int], list[int]] = {}
    for pose in trace.poses:
        if pose.banquet.zone.position is Position.DISGRACE:
            cle = (pose.joueur, pose.banquet.carte.famille)
            bascules.setdefault(cle, []).append(pose.index)
    for tir in trace.ciblages:
        victime = tir.victime
        if victime is None or victime.zone.genre is not GenreZone.BANQUET:
            continue
        if victime.zone.position is not Position.ESTIME:
            continue
        cle = (tir.joueur, victime.carte.famille)
        bascules.setdefault(cle, []).append(tir.index)

    numerateur = 0
    for pose in trace.poses:
        famille = pose.adverse.carte.famille
        final = trace.statuts_finaux[famille]
        atteint = final != LUMIERE if seuil_final == "hors_lumiere" else final < 0
        if not atteint:
            continue
        if exiger_cadeau and statut(pose.d_avant[famille]) != LUMIERE:
            continue
        suivantes = bascules.get((pose.joueur, famille), ())
        if any(index > pose.index for index in suivantes):
            numerateur += 1
    return Taux("B1", "pose chez un adversaire", numerateur, len(trace.poses))


# ---------------------------------------------------------------------------------
# B2 -- placer l'Assassin la ou il pourra servir
# ---------------------------------------------------------------------------------


def b2_distribution(trace: Trace) -> dict[str, Taux]:
    """La distribution des zones ou les Assassins sont **poses**.

    Paragraphe 7.2 : « distribution des zones ou l'IA place ses Assassins ». C'est la
    mesure primaire, et elle n'exige aucun seuil invente. Unite : l'Assassin pose.
    """
    zones = ("banquet_estime", "banquet_disgrace", "domaine_propre", "domaine_adverse")
    total = len(trace.ciblages)
    comptes = dict.fromkeys(zones, 0)
    for tir in trace.ciblages:
        comptes[_zone_assassin(tir)] += 1
    return {
        zone: Taux(f"B2.{zone}", "Assassin pose", comptes[zone], total) for zone in zones
    }


def b2_bascule(trace: Trace) -> Taux:
    """Assassins poses la ou un meurtre **changerait le statut** d'une famille.

    Lecture operationnelle de « la ou il pourra servir ». Seules les cartes du banquet
    portent le statut (paragraphe 5), donc un Assassin de domaine ne peut structurellement
    pas satisfaire ce critere -- c'est une propriete des regles, pas un artefact, et le
    controle negatif l'exige.
    """
    numerateur = 0
    for tir in trace.ciblages:
        if any(_meurtre_bascule(tir, indice) for indice in range(len(tir.cibles))):
            numerateur += 1
    return Taux("B2.bascule", "Assassin pose", numerateur, len(trace.ciblages))


def _meurtre_bascule(tir: EvenementCiblage, indice: int) -> bool:
    """Vrai si tuer `cibles[indice]` change le statut de la famille de la cible."""
    cible = tir.cibles[indice]
    if cible.zone.genre is not GenreZone.BANQUET:
        return False
    famille = cible.carte.famille
    avant = tir.d_avant[famille]
    apres = avant - _signe(cible.zone.position) * valeur(cible.carte.role)
    return statut(avant) != statut(apres)


# ---------------------------------------------------------------------------------
# B3 -- fabriquer une alliance
# ---------------------------------------------------------------------------------


def b3(trace: Trace, *, vue: str = "analyste") -> Taux:
    """Nourrir un joueur sur une famille ou le poseur est lui-meme expose.

    Paragraphe 7.2 : « nourrir un joueur sur une famille ou l'IA est elle-meme exposee ».
    Etre expose = detenir une carte vivante de cette famille dans **son propre** domaine :
    ce sont ces cartes-la qui rapportent au poseur si la famille finit en Lumiere
    (paragraphe 5), donc c'est la que naissent les interets communs du paragraphe 2.5.

    Args:
        vue: `analyste` (retenue, plateau reel) ou `siege` (concurrente : l'exposition
            telle que le poseur peut la voir, donc sans les Espions adverses poses dans
            son domaine).

    Returns:
        Un taux dont l'unite est **la pose chez un adversaire**.
    """
    if vue not in ("analyste", "siege"):
        raise ValueError(f"vue inconnue : {vue!r}")
    numerateur = 0
    for pose in trace.poses:
        expose = pose.expose_avant if vue == "analyste" else pose.expose_visible_avant
        if pose.adverse.carte.famille in expose:
            numerateur += 1
    return Taux("B3", "pose chez un adversaire", numerateur, len(trace.poses))


# ---------------------------------------------------------------------------------
# B4 -- refuser de tuer
# ---------------------------------------------------------------------------------


def b4(trace: Trace, *, denominateur: str = "avec_cible") -> Taux:
    """Le refus de tuer.

    Paragraphe 4.1 : « il n'est pas tenu de tuer s'il ne veut pas, meme lorsque des cibles
    existent. "Ne pas tuer" est une action a part entiere ». Le denominateur retenu est
    donc **le noeud offrant au moins une cible** : lui seul porte une decision.

    Le denominateur litteral -- tous les noeuds de ciblage -- ajoute les noeuds sans cible,
    ou le refus est **force** et entre donc aussi au numerateur. Le taux obtenu est une
    moyenne ponderee entre le refus delibere et un constat mecanique ; il ne mesure plus
    une decision, et il monte avec la frequence des Assassins isoles. Il est calcule ici
    pour que l'ecart entre les deux lectures soit chiffre, pas suppose.

    Args:
        denominateur: `avec_cible` (retenu) ou `tous_noeuds` (concurrente litterale).
    """
    if denominateur not in ("avec_cible", "tous_noeuds"):
        raise ValueError(f"denominateur inconnu : {denominateur!r}")
    if denominateur == "tous_noeuds":
        return Taux(
            "B4.litteral",
            "noeud de ciblage",
            sum(1 for tir in trace.ciblages if tir.refus),
            len(trace.ciblages),
        )
    avec = [tir for tir in trace.ciblages if tir.cibles]
    return Taux(
        "B4",
        "noeud de ciblage offrant au moins une cible",
        sum(1 for tir in avec if tir.refus),
        len(avec),
    )


def b4_defavorable(trace: Trace) -> Taux:
    """Le refus **la ou tuer couterait**, seule lecture qui teste la seconde moitie de B4.

    Paragraphe 7.2 : « frequence du refus, **et verification qu'il survient dans les cas
    defavorables** ». Un noeud est defavorable quand tout meurtre laisse le tueur avec un
    ecart strictement inferieur a celui du refus, ecart calcule sur le plateau reel : la
    question est si le refus etait juste, pas s'il etait coherent avec la croyance du
    tueur.
    """
    noeuds = [
        tir
        for tir in trace.ciblages
        if tir.cibles and max(tir.ecarts_si_meurtre) < tir.ecart_si_refus
    ]
    return Taux(
        "B4.defavorable",
        "noeud ou tout meurtre couterait au tueur",
        sum(1 for tir in noeuds if tir.refus),
        len(noeuds),
    )


def b4_favorable(trace: Trace) -> Taux:
    """Le refus **la ou tuer rapporterait** : le refus a tort, temoin du sens de B4."""
    noeuds = [
        tir
        for tir in trace.ciblages
        if tir.cibles and max(tir.ecarts_si_meurtre) > tir.ecart_si_refus
    ]
    return Taux(
        "B4.favorable",
        "noeud ou un meurtre rapporterait au tueur",
        sum(1 for tir in noeuds if tir.refus),
        len(noeuds),
    )


# ---------------------------------------------------------------------------------
# B5 -- se mefier des Espions
# ---------------------------------------------------------------------------------


def b5(trace: Trace) -> Taux:
    """Ne pas traiter une majorite d'une seule unite comme acquise s'il reste des dos.

    Paragraphe 7.2 : « comportement face aux majorites a une carte d'ecart ». La situation
    est definie **du point de vue du siege** -- c'est lui qui doit se mefier, donc c'est sa
    marge visible qui compte -- : il existe une famille dont il voit `|d| = 1` et il voit
    au moins un dos adverse au banquet.

    Le numerateur compte les tours ou le joueur **consolide** une telle famille, c'est-a-
    dire eloigne son `d` de zero par la carte qu'il met au banquet. Unite : le tour ou la
    situation se presente.
    """
    concernes = [
        pose
        for pose in trace.poses
        if pose.dos_adverses_banquet >= 1
        and any(abs(d) == 1 for d in pose.d_visible_avant.values())
    ]
    numerateur = 0
    for pose in concernes:
        famille = pose.banquet.carte.famille
        d = pose.d_visible_avant[famille]
        if abs(d) == 1 and _renforce(d, pose):
            numerateur += 1
    return Taux(
        "B5",
        "tour ou une famille est vue a |d| = 1 avec un dos adverse au banquet",
        numerateur,
        len(concernes),
    )


# ---------------------------------------------------------------------------------
# B6 -- exploiter la pioche connue
# ---------------------------------------------------------------------------------


def _profil(poses: Sequence[EvenementPose]) -> dict[tuple[Position, Role], int]:
    """La distribution jointe (position au banquet, role pose au banquet)."""
    profil: dict[tuple[Position, Role], int] = {}
    for pose in poses:
        cle = (pose.banquet.zone.position, pose.banquet.carte.role)
        profil[cle] = profil.get(cle, 0) + 1
    return profil


def distance_tv(a: dict, b: dict) -> float:
    """Distance en variation totale entre deux distributions empiriques.

    **Biaisee vers le haut.** Deux echantillons finis tires de la MEME loi rendent une
    distance strictement positive, d'autant plus grande que l'echantillon est petit et que
    les cellules sont nombreuses. Un chiffre de B6 sans son plancher de nullite ne se lit
    donc pas : `plancher_tv` le fournit.
    """
    na, nb = sum(a.values()), sum(b.values())
    if na == 0 or nb == 0:
        raise ValueError("distance indefinie : un des deux echantillons est vide")
    cles = set(a) | set(b)
    return 0.5 * sum(abs(a.get(k, 0) / na - b.get(k, 0) / nb) for k in cles)


def b6_profils(
    traces: Sequence[Trace], tours: int
) -> tuple[dict, dict, int, int]:
    """Les profils du premier et du dernier tour, avec leurs effectifs."""
    premiers = [p for t in traces for p in t.poses if p.tour == 0]
    derniers = [p for t in traces for p in t.poses if p.tour == tours - 1]
    return _profil(premiers), _profil(derniers), len(premiers), len(derniers)


def plancher_tv(
    traces: Sequence[Trace], tour: int, graine: int, repetitions: int = 200
) -> tuple[float, float]:
    """Le plancher de nullite : distance TV entre deux moities du **meme** tour.

    Rend `(moyenne, quantile 95 %)`. C'est ce qu'une distance de B6 vaut quand rien ne
    change : toute distance inferieure a ce plancher ne temoigne d'aucun changement de
    style.
    """
    poses = [p for t in traces for p in t.poses if p.tour == tour]
    if len(poses) < 4:
        raise ValueError("echantillon trop petit pour un plancher")
    rng = random.Random(graine)
    distances = []
    for _ in range(repetitions):
        melange = list(poses)
        rng.shuffle(melange)
        moitie = len(melange) // 2
        distances.append(
            distance_tv(_profil(melange[:moitie]), _profil(melange[moitie:]))
        )
    distances.sort()
    return sum(distances) / len(distances), distances[int(0.95 * len(distances))]


# ---------------------------------------------------------------------------------
# B7 -- ne pas defendre ce qui est deja sur
# ---------------------------------------------------------------------------------


def b7(trace: Trace) -> Taux:
    """Les cartes gaspillees a renforcer une famille deja hors d'atteinte.

    Paragraphe 7.2 : « mesurer la frequence des cartes "gaspillees" a renforcer une
    majorite deja imprenable ». Imprenable est calcule a l'instant de la pose par la borne
    de `trace._imprenables`, qui suit le paragraphe 2.6 : residu de la famille, occasions
    restantes, et cartes tuables du cote favorable.

    Unite : **la pose au banquet**. Chaque tour en produit exactement une.
    """
    numerateur = 0
    for pose in trace.poses:
        famille = pose.banquet.carte.famille
        if famille not in pose.imprenables_avant:
            continue
        if _renforce(pose.d_avant[famille], pose):
            numerateur += 1
    return Taux("B7", "pose au banquet", numerateur, len(trace.poses))


def occasions_b7(trace: Trace) -> Taux:
    """Combien de poses au banquet **avaient** une famille imprenable a renforcer.

    Sans ce chiffre, un B7 nul est indistinguable de « la situation ne s'est jamais
    presentee » -- exactement la confusion entre un zero et un denominateur vide que cet
    audit traque ailleurs.
    """
    return Taux(
        "B7.occasions",
        "pose au banquet",
        sum(1 for pose in trace.poses if pose.imprenables_avant),
        len(trace.poses),
    )
