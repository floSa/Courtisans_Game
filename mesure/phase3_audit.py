"""L'audit de mon propre resultat -- **ecrit AVANT de le voir**.

Etape 6 de la boucle du paragraphe 2 du protocole : « le resultat est audite avant d'etre cru ».
Ce module existe pour une raison precise : un controle ecrit **apres** avoir vu un chiffre est
un controle que le chiffre a passe par construction. Celui-ci est ecrit et commite avant que
l'agent ne soit mesure.

Les trois questions du protocole, et les cinq du paragraphe 0.2
----------------------------------------------------------------
Chaque controle porte le numero de la question qu'il instruit.

  Q1. La mesure mesure-t-elle ce que je crois ?
  Q2. Sur quel support est-elle definie ?
  Q3. Est-elle comparable a quoi ?

  R1. Chaque taux a-t-il le bon denominateur ?
  R2. Chaque chiffre nomme-t-il la POPULATION dont il parle ?
  R3. Deux lignes comparees sont-elles au meme grain ?
  R4. Un zero ou un cent pour cent a-t-il ete confronte a un cas construit a la main ?
  R5. L'unite a-t-elle ete reconstruite AVANT la valeur, et separement ?

Ce qu'un controle a le droit d'etre, depuis l'audit du tour 1
--------------------------------------------------------------
**Deux des dix controles ci-dessous ne pouvaient pas echouer** : ils passaient un `True`
litteral, et le compte rendu les comptait quand meme dans « dix controles, aucun en echec »
tout en affirmant que **chacun** etait verifie capable d'echouer. Deux autres n'etaient pas
casses par leurs tests -- l'un eprouvait `bootstrap_par_donne` sur des donnees fabriquees,
l'autre la **forme** de la preuve.

Trois consequences, et elles sont dans le code plutot que dans cette docstring :

  - un controle qui liste sans juger se construit par `_releve` et porte le statut `releve`.
    Il ne se compte pas parmi les concluants ;
  - un controle qui juge se construit par `_epreuve`, et un test **lit l'AST de ce module**
    pour refuser qu'un booleen litteral y soit passe ;
  - les quatre controles non casses le sont desormais, chacun par reinjection de la faute
    qu'il pretend attraper -- y compris `controle_niveau_nul`, qui a recu pour cela un
    parametre `agent`.

Ce que ce module ne fait pas
------------------------------
Il ne rejuge pas l'agent et ne recalcule pas le verdict par un second chemin qui partagerait
les memes hypotheses. **Reproduire un nombre ne le valide pas** : deux implementations qui
partagent la meme hypothese fausse concordent parfaitement, et un facteur trois indu a survecu
a deux verifications reussies pour cette raison. Les controles ci-dessous portent donc sur des
**unites**, des **denominateurs** et des **populations**, pas sur des valeurs.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from mesure import bootstrap as boot
from mesure import comportements as comp
from mesure import phase2, phase3, phase3_mesure


#: Les trois statuts d'un controle. **`releve` n'est pas un troisieme degre de reussite** :
#: c'est l'aveu qu'un controle ne peut pas echouer, donc qu'il n'eprouve rien.
STATUTS: tuple[str, ...] = ("concluant", "en echec", "releve")


@dataclass(frozen=True)
class Controle:
    """Un controle hostile, son statut et sa preuve.

    **Un controle qui ne peut pas echouer ne se compte pas parmi les controles concluants**, et
    c'est desormais une regle du paragraphe 0.2 du protocole. Le premier tour de la phase 3 en
    comptait dix « aucun en echec » alors que **deux** passaient un `True` litteral : ils
    listaient, ils n'eprouvaient pas. Le compte rendu affirmait pourtant que les dix etaient
    verifies capables d'echouer.

    D'ou les deux constructeurs distincts ci-dessous. `_epreuve` exige un predicat calcule --
    un test de l'AST interdit d'y passer un booleen litteral --, `_releve` dit en toutes
    lettres que le controle **liste** sans juger. Le rapport les compte separement.

    Attributes:
        code: la question instruite -- `Q1`, `R3`, ...
        intitule: ce que le controle cherche a casser, ou a relever.
        statut: `concluant`, `en echec`, ou `releve`.
        preuve: le chiffre ou le fait qui l'etablit. **Jamais « OK ».**
    """

    code: str
    intitule: str
    statut: str
    preuve: str

    def __post_init__(self) -> None:
        if self.statut not in STATUTS:
            raise ValueError(
                f"statut « {self.statut} » inconnu : un controle est {', '.join(STATUTS)}"
            )

    @property
    def eprouve(self) -> bool:
        """Ce controle **peut-il** echouer ? Un releve ne le peut pas."""
        return self.statut != "releve"

    @property
    def passe(self) -> bool:
        """Vrai sauf en echec. **Ne dit pas que le controle a eprouve quoi que ce soit** --
        lire `eprouve` pour ca, et ne jamais compter un releve dans « aucun en echec »."""
        return self.statut != "en echec"


def _epreuve(code: str, intitule: str, passe: bool, preuve: str) -> Controle:
    """Un controle qui **peut** echouer. `passe` doit venir d'un calcul, jamais d'un litteral.

    `tests/mesure/test_phase3_audit.py` lit l'AST de ce module et **refuse** qu'un appel a
    `_epreuve` porte `True` ou `False` en dur : c'est la parade qui empeche le defaut de se
    refaire, la ou une docstring ne l'empechait pas.
    """
    return Controle(
        code=code,
        intitule=intitule,
        statut="concluant" if passe else "en echec",
        preuve=preuve,
    )


def _releve(code: str, intitule: str, preuve: str) -> Controle:
    """Un controle qui **liste sans juger**, et qui le dit.

    Il a sa place -- lister les zeros absolus ou les unites divergentes est utile -- mais il ne
    se compte pas parmi les controles concluants, et le rapport doit le dire.
    """
    return Controle(code=code, intitule=intitule, statut="releve", preuve=preuve)


def controle_niveau_nul(
    donnes: int, depart: int, agent: phase3.Fabrique | None = None
) -> Controle:
    """**Q1.** Le niveau nul du juge est-il ou je crois qu'il est, SUR LES SEEDS DU VERDICT ?

    La pre-inscription calibre l'instrument sur les seeds `20000-21999`. Le verdict est rendu
    sur `30000+`. **Ce n'est pas le meme echantillon**, et un niveau nul verifie ailleurs ne
    dit rien ici : ce controle refait la calibration sur les donnes exactes du verdict, avec
    le greedy a la place de l'agent.

    Si l'IC ne contient pas 0, **c'est l'instrument qui est faux, pas l'agent** -- et aucun
    chiffre du rapport ne vaut.

    Args:
        agent: la politique mise a la place de l'agent. `None` prend le greedy de reference,
            et c'est le seul usage en production. **Le parametre existe pour que le controle
            soit falsifiable** : un test y injecte une politique qui n'est PAS l'egale des deux
            adversaires, et exige que le controle passe au rouge. Sans lui, « ce controle peut
            echouer » restait une phrase de docstring que rien n'exercait -- et c'est un des
            quatre controles que l'audit a trouves non casses.
    """
    campagne = phase3.jouer_composition(
        agent=agent or phase3.greedy_de_reference,
        adversaire=phase3.greedy_de_reference,
        donnes=donnes,
        intitule="1 greedy contre 2 greedys, seeds du verdict",
        depart=depart,
    )
    verdict = phase3.juger(campagne)
    basse, haute = verdict.gain.intervalle
    return _epreuve(
        "Q1",
        "le niveau nul du juge, recalibre sur les seeds du verdict",
        basse <= 0.0 <= haute,
        f"gain moyen {verdict.gain.moyenne:+.4f}, IC 99 % [{basse:+.4f} ; {haute:+.4f}] sur "
        f"{campagne.nb_parties} parties, seeds {depart}-{depart + donnes - 1}",
    )


def controle_somme_nulle(mesure: phase3_mesure.Mesure, campagne: phase3.Campagne) -> Controle:
    """**Q1.** La somme des gains vaut-elle 0 dans CHAQUE partie ?

    C'est l'invariant I5 et le paragraphe 5.2. Il fonde le niveau nul exact du seuil : s'il
    tombait, le seuil n'aurait plus de valeur nulle connue.
    """
    pire = 0.0
    parties = 0
    for groupe in campagne.traces:
        for trace in groupe:
            pire = max(pire, abs(sum(trace.gains)))
            parties += 1
    return _epreuve(
        "Q1",
        "la somme des gains vaut 0 dans chaque partie (I5, paragraphe 5.2)",
        pire < 1e-12,
        f"ecart maximal a zero : {pire:.3e} sur {parties} parties de « {mesure.intitule} »",
    )


def controle_plan_equilibre(campagne: phase3.Campagne) -> Controle:
    """**Q2.** Chaque siege est-il occupe exactement une fois par donne ?

    C'est ce qui rend l'esperance du niveau nul exacte. Un plan desequilibre la deplacerait
    d'un ecart entre sieges -- et le contraste entre sieges extremes vaut **+0,5735** dans
    cette composition, soit plus de dix fois l'effet cherche.
    """
    fautifs = [
        donne
        for donne, sieges in zip(campagne.donnes, campagne.sieges_mesures, strict=True)
        if sorted(sieges) != list(range(phase3.CONFIG.joueurs))
    ]
    return _epreuve(
        "Q2",
        "chaque siege exactement une fois par donne",
        not fautifs,
        f"{len(campagne.donnes)} donnes verifiees, {len(fautifs)} desequilibrees"
        + (f" : {fautifs[:5]}" if fautifs else ""),
    )


def controle_denominateur(mesure: phase3_mesure.Mesure) -> Controle:
    """**R1.** `parties = donnes x sieges`, reconstruit et non recopie."""
    attendu = mesure.nb_donnes * phase3.CONFIG.joueurs
    return _epreuve(
        "R1",
        "le denominateur du verdict est `donnes x sieges`",
        mesure.nb_parties == attendu,
        f"{mesure.nb_donnes} donnes x {phase3.CONFIG.joueurs} sieges = {attendu}, "
        f"rapporte : {mesure.nb_parties}",
    )


def controle_populations_nommees(
    mesures: Sequence[phase3_mesure.Mesure], intitules_hors_pool: Sequence[str] = ()
) -> Controle:
    """**R2.** Chaque mesure nomme-t-elle sa composition, et les noms sont-ils distincts ?

    Deux compositions portant le meme intitule se liraient comme une seule dans le rapport.

    **Il ne s'appliquait qu'a la liste du pool, et c'est ce qui l'a rendu aveugle.** Le rapport
    du tour 1 publiait la composition du garde-fou -- 600 donnes, seeds 40000+, checkpoint
    courant -- sous **exactement** le meme nom qu'une ligne du pool -- 500 donnes, seeds 70000+,
    `final.pt` --, et R2 declarait « 11 compositions, 11 noms distincts ». Le controle cense
    attraper la faute maison du projet la laissait passer parce que son perimetre etait plus
    etroit que celui du rapport.

    Args:
        intitules_hors_pool: les compositions que le rapport publie **ailleurs** que dans le
            pool -- celle du garde-fou, aujourd'hui. Le controle porte desormais sur tout ce
            qui est publie, pas sur ce qui est commode a lui passer.
    """
    intitules = [mesure.intitule for mesure in mesures] + list(intitules_hors_pool)
    sans_composition = [x for x in intitules if "contre" not in x]
    doublons = sorted({x for x in intitules if intitules.count(x) > 1})
    return _epreuve(
        "R2",
        "chaque composition est nommee, et les noms sont distincts",
        not sans_composition and not doublons,
        f"{len(intitules)} compositions, {len(set(intitules))} noms distincts"
        + (f" ; sans composition : {sans_composition}" if sans_composition else "")
        + (f" ; doublons : {doublons}" if doublons else ""),
    )


def controle_grains(comparaisons: Sequence[phase3_mesure.Comparaison]) -> Controle:
    """**R3.** Deux lignes comparees portent-elles le MEME grain, libelle compris ?

    `ecart_de_taux` leve deja si les grains different -- ce controle verifie que la garde a
    bien ete traversee pour **toutes** les lignes, et pas seulement pour celles qu'on a
    regardees. Une ligne exclue n'est pas comparee : elle n'a pas a coincider.
    """
    fautives = [
        c.nom
        for c in comparaisons
        if c.exclu is None and c.agent.grain != c.base.grain
    ]
    comparees = sum(1 for c in comparaisons if c.exclu is None)
    return _epreuve(
        "R3",
        "les lignes comparees sont au meme grain",
        not fautives,
        f"{comparees} lignes comparees sur {len(comparaisons)}, {len(fautives)} a grains "
        f"differents" + (f" : {fautives}" if fautives else ""),
    )


def controle_zeros(comparaisons: Sequence[phase3_mesure.Comparaison]) -> Controle:
    """**R4.** Tout zero ou cent pour cent publie est-il liste pour traitement individuel ?

    Un zero absolu se confronte a un cas construit a la main **avant** d'etre ecrit : le zero de
    la phase 1 etait contredit par un test du meme livrable.

    **Ce controle liste, il ne juge pas** -- c'est un `_releve`, et le rapport le compte comme
    tel. Le premier tour le donnait « concluant » avec un `True` litteral, ce qui laissait
    croire que les zeros avaient ete eprouves.

    **Et il regardait le seul agent.** Les deux zeros absolus que le rapport publie --
    `B4-contre-nature` 0,00 % (0/1967) et `B4-meurtre-couteux` 0,00 % (0/10382) -- sont du cote
    de la **ligne de base**. Il imprimait donc « 0 valeur extreme chez l'agent -- aucune »
    pendant que le rapport en publiait deux, et la regle du paragraphe 0.2 n'etait exercee sur
    aucun des deux. Il scanne desormais **les deux cotes**, et nomme lequel.

    Les deux zeros de la ligne de base sont confrontes a un cas construit a la main par
    `tests/audit_phase3_corrections/test_zeros_de_la_ligne_de_base.py`, qui montre sur un nœud
    fabrique que le greedy **ne peut pas** contredire son propre argmax.
    """
    extremes: list[str] = []
    for comparaison in comparaisons:
        for cote, compte in (("agent", comparaison.agent), ("ligne de base", comparaison.base)):
            if compte.total > 0 and compte.taux() in (0.0, 1.0):
                extremes.append(
                    f"{comparaison.nom} [{cote}] = {compte.succes}/{compte.total}"
                )
    return _releve(
        "R4",
        "les zeros et les cent pour cent, des DEUX cotes, listes pour traitement individuel",
        f"{len(extremes)} valeur(s) extreme(s) sur {len(comparaisons)} lignes"
        + (f" : {', '.join(extremes)}" if extremes else " -- aucune"),
    )


def controle_unite_avant_valeur(
    mesure: phase3_mesure.Mesure, base: dict[str, comp.Compte], nb_parties_base: int
) -> Controle:
    """**R5.** L'unite est-elle reconstruite avant la valeur, et separement ?

    Le controle ne compare aucun taux. Il reconstruit, pour chaque compteur, le nombre
    d'observations **par partie** des deux cotes, et exige qu'ils coincident -- l'unite --
    **sans regarder les numerateurs** -- la valeur. C'est le controle qui manquait a la
    phase 2, ou un facteur trois a survecu a deux verifications parce que la formule de
    controle recevait le meme denominateur errone que le generateur.

    La tolerance est de 5 % relatif : les denominateurs d'action -- poses d'Assassin, nœuds de
    ciblage -- dependent de la politique et ne coincident pas au nœud pres entre deux agents
    differents. Les lignes `-par-partie`, elles, doivent valoir 1,0 exactement des deux cotes,
    et `phase2.observations_par_partie` **leve** sinon.

    **Ce controle liste, il ne juge pas** -- un ecart d'unite n'est pas fautif en soi, un
    denominateur d'action depend de la politique. C'est donc un `_releve` : le premier tour le
    donnait « concluant » avec un `True` litteral, alors qu'aucune entree ne pouvait le faire
    echouer, pas meme un facteur dix. Ce qui **juge** l'unite est
    `phase2.observations_par_partie`, qui leve ; ce controle rend l'ecart lisible avant que
    les taux ne soient compares.
    """
    ecarts = []
    for nom in sorted(set(mesure.comportements) & set(base)):
        a = phase2.observations_par_partie(mesure.comportements[nom], mesure.nb_parties)
        b = phase2.observations_par_partie(base[nom], nb_parties_base)
        if b > 0 and abs(a - b) / b > 0.05:
            ecarts.append(f"{nom} {a:.3f} vs {b:.3f}")
    return _releve(
        "R5",
        "l'unite -- observations par partie -- relevee des deux cotes, numerateurs non regardes",
        f"{len(ecarts)} compteur(s) dont l'unite differe de plus de 5 % : "
        + (", ".join(ecarts) if ecarts else "aucun")
        + ". Un ecart n'est pas fautif en soi -- un denominateur d'action depend de la "
        "politique -- mais il doit etre lu avant de comparer les taux.",
    )


def controle_seeds_disjoints(
    donnes_verdict: int, donnes_pool: int, nb_checkpoints: int, parties_entrainement: int
) -> Controle:
    """**Q3.** Les donnes du verdict sont-elles disjointes de celles de l'entrainement ?

    Juger sur les donnes d'entrainement donnerait a l'agent un avantage qui n'est pas de
    l'habilete, et le chiffre serait juste sur une population que sa phrase ne nomme pas.

    **Ce controle a trouve un vrai defaut avant la mesure.** La premiere version de
    `phase3_mesure` decalait les compositions du pool de `+100 000` et `+200 000` a partir de
    `30 000`, donc a `130 000` et `230 000+` -- **dans la plage d'entrainement**, qui part a
    `100 000` et consomme une donne par partie jouee. Les plages sont desormais toutes sous
    `100 000`.

    Les bornes sont **calculees depuis les comptes reels**, pas declarees a la main : une
    plage declaree plus etroite qu'elle ne l'est laisserait passer exactement le defaut que ce
    controle cherche.
    """
    from agents import campagne, entrainement

    plages: dict[str, tuple[int, int]] = {
        "dimensionnement": (phase3.DEPART_DONNE, phase3.DEPART_DONNE + donnes_verdict),
        "garde-fou": (
            campagne.DEPART_DONNE_GARDE_FOU,
            campagne.DEPART_DONNE_GARDE_FOU + campagne.DONNES_GARDE_FOU,
        ),
        "verdict": (
            phase3_mesure.DEPART_CAMPAGNE_FINALE,
            phase3_mesure.DEPART_CAMPAGNE_FINALE + donnes_verdict,
        ),
        "pool aleatoire": (
            phase3_mesure.DEPART_CAMPAGNE_FINALE + phase3_mesure.DECALAGE_POOL_ALEATOIRE,
            phase3_mesure.DEPART_CAMPAGNE_FINALE
            + phase3_mesure.DECALAGE_POOL_ALEATOIRE
            + donnes_pool,
        ),
        "variante deterministe": (
            phase3_mesure.DEPART_CAMPAGNE_FINALE
            + phase3_mesure.DECALAGE_VARIANTE_DETERMINISTE,
            phase3_mesure.DEPART_CAMPAGNE_FINALE
            + phase3_mesure.DECALAGE_VARIANTE_DETERMINISTE
            + donnes_verdict,
        ),
        "entrainement": (
            entrainement.DEPART_DONNE_ENTRAINEMENT,
            entrainement.DEPART_DONNE_ENTRAINEMENT + parties_entrainement,
        ),
    }
    for indice in range(max(nb_checkpoints, 1)):
        debut = (
            phase3_mesure.DEPART_CAMPAGNE_FINALE
            + phase3_mesure.DECALAGE_POOL_CHECKPOINTS
            + phase3_mesure.PAS_ENTRE_CHECKPOINTS * indice
        )
        plages[f"pool checkpoint {indice + 1}"] = (debut, debut + donnes_pool)

    chevauchements = []
    noms = sorted(plages)
    for i, un in enumerate(noms):
        for autre in noms[i + 1 :]:
            (a0, a1), (b0, b1) = plages[un], plages[autre]
            if a0 < b1 and b0 < a1:
                chevauchements.append(f"{un} [{a0}, {a1}) x {autre} [{b0}, {b1})")
    return _epreuve(
        "Q3",
        "les plages de donnes ne se chevauchent pas",
        not chevauchements,
        "; ".join(f"{nom} [{a}, {b})" for nom, (a, b) in sorted(plages.items()))
        + (f" ; CHEVAUCHEMENTS : {chevauchements}" if chevauchements else " ; disjointes"),
    )


def controle_bootstrap_par_donne(campagne: phase3.Campagne) -> Controle:
    """**Q2.** Le bootstrap rechantillonne-t-il des DONNES et non des parties ?

    Tirer des parties detruirait la structure qu'on mesure -- c'est elle qui porte le `rho`
    negatif, donc le gain de variance de la permutation. Le controle compare l'effet de plan
    rendu par le bootstrap a celui de l'analyse de variance : deux routes independantes qui
    doivent concorder. Si le bootstrap tirait des parties, son effet vaudrait 1,0 par
    construction.
    """
    gains = campagne.gains_par_donne()
    effet_bootstrap = boot.bootstrap_par_donne(
        gains, phase3.RECHANTILLONS, random.Random(phase3.GRAINE_BOOTSTRAP)
    ).effet
    rho = boot.correlation_intra_donne(gains)
    effet_anova = (
        None if rho is None else 1.0 + (campagne.replicats_par_donne - 1) * rho
    )
    # `effet_anova` peut valoir exactement 0 -- `rho = -1/(m-1)`, le cas d'une donne dont les
    # replicats se partagent une somme constante sans aucune variation entre donnes. Diviser
    # par lui leverait un `ZeroDivisionError` au milieu d'un audit, ce qui est la pire facon de
    # tomber : on ne saurait pas si le controle a echoue ou si le code est casse. Trouve en
    # ecrivant le cas qui casse ce controle, au tour 2.
    concordent = (
        effet_anova is not None
        and abs(effet_bootstrap - effet_anova) < 0.10 * max(effet_anova, 1e-9)
    )
    return _epreuve(
        "Q2",
        "le bootstrap tire des donnes -- deux routes vers l'effet de plan concordent",
        concordent,
        f"effet bootstrap {effet_bootstrap:.4f}, effet par analyse de variance "
        + ("non defini" if effet_anova is None else f"{effet_anova:.4f}")
        + " ; un bootstrap qui tirerait des parties rendrait 1,0000",
    )


def auditer(
    mesure: phase3_mesure.Mesure,
    campagne: phase3.Campagne,
    pool: Sequence[phase3_mesure.Mesure],
    comparaisons: Sequence[phase3_mesure.Comparaison],
    base: dict[str, comp.Compte],
    nb_parties_base: int,
    donnes_calibration: int,
    donnes_pool: int,
    nb_checkpoints: int,
    parties_entrainement: int,
    intitules_hors_pool: Sequence[str] = (),
) -> list[Controle]:
    """Joue tous les controles et rend leurs verdicts, dans l'ordre des questions.

    Args:
        intitules_hors_pool: les compositions publiees hors du pool -- le garde-fou. Voir
            `controle_populations_nommees` : c'est l'etroitesse de son perimetre qui l'avait
            rendu aveugle a un doublon de nom.
    """
    return [
        controle_niveau_nul(donnes_calibration, phase3_mesure.DEPART_CAMPAGNE_FINALE),
        controle_somme_nulle(mesure, campagne),
        controle_plan_equilibre(campagne),
        controle_bootstrap_par_donne(campagne),
        controle_seeds_disjoints(
            donnes_verdict=donnes_calibration,
            donnes_pool=donnes_pool,
            nb_checkpoints=nb_checkpoints,
            parties_entrainement=parties_entrainement,
        ),
        controle_denominateur(mesure),
        controle_populations_nommees(pool, intitules_hors_pool),
        controle_grains(comparaisons),
        controle_zeros(comparaisons),
        controle_unite_avant_valeur(mesure, base, nb_parties_base),
    ]


__all__ = ["Controle", "STATUTS", "auditer"]
