"""Les calculs de plan de la phase 2 : seuils, puissance, taille d'echantillon.

**Aucune partie n'est jouee ici.** Ce module ne mesure rien : il recalcule les chiffres de
`phase2_hypothese_et_instrument.md` paragraphes 2.3, 2.4, 3.4 et 4.4, pour qu'un lecteur
puisse les reconstruire au lieu de les croire (paragraphe 10 des conventions : un chiffre
qui ne peut pas etre reconstruit se decompose ou se retire).

Toutes les formules supposent des parties **independantes**. C'est volontaire, et c'est dit :
les seuils du plan sont calcules ainsi *avant* la mesure, puis recalcules sur la variance
bootstrap par donne dans le compte rendu. L'ecart entre les deux est l'**effet de plan**, et
son signe n'est pas suppose ici -- voir le paragraphe 1.3 du document.

Trois calculs de taille d'echantillon, et pourquoi les trois sont publies
-------------------------------------------------------------------------
Une taille d'echantillon n'a pas de valeur unique : elle depend de la formule. Deux
approximations normales raisonnables divergent ici de 19 parties sur 1 456, et l'exact
s'ecarte des deux. **Les trois sont donc rendus, avec leurs parametres**, et c'est l'exact
qui sert de reference -- lui seul ne depend d'aucun choix d'approximation.

| Methode | Ecart-type au terme de puissance | Resultat a p1 = 38 % |
|---|---|---:|
| `Variance.SOUS_H0` | `sqrt(p0 q0)` -- le meme aux deux termes | 1 456 |
| `Variance.SOUS_H1` | `sqrt(p1 q1)` -- celui de l'alternative | 1 475 |
| exact binomial, franchissement | aucune | 1 501 |
| **exact binomial, stable** | aucune | **1 531** |

`SOUS_H1` est la forme des manuels pour un test de proportion : le terme de puissance decrit
la loi **sous l'alternative**, dont l'ecart-type est `sqrt(p1 q1)`. `SOUS_H0` prend `sqrt(p0
q0)` partout, ce qui **sous-estime** `n` des que `p1` est plus proche de 0,5 que `p0`. Les
deux se lisent dans la litterature ; aucune n'est fausse, elles ne repondent pas tout a fait
a la meme question.

**L'exact departage, et il est plus grand que les deux.** Le test reel porte sur un compte
entier : on rejette si `K >= c`, ou `c` est le plus petit entier dont la queue superieure
sous `p0` ne depasse pas le risque. La discretion du compte rend le test **conservateur** --
la queue atteinte est strictement inferieure au risque nominal -- donc il faut plus de
parties que la normale ne le dit.

**Et la puissance exacte n'est pas monotone en `n`.** Elle avance en dents de scie, parce que
`c` saute d'une unite. A `p1 = 38 %` elle franchit 80 % a `n = 1 501`, puis **redescend** en
dessous a 1 502, 1 503, 1 505... jusqu'a 1 530. Publier le premier franchissement serait
publier une coincidence d'arrondi : `parties_pour_puissance_exacte` rend donc par defaut le
plus petit `n` **a partir duquel la puissance ne redescend plus**, et le premier
franchissement est rendu a cote pour que la dent de scie soit visible et non cachee.

Un seul endroit ecrit le nombre de sieges, le nombre de parties et le risque : les
constantes ci-dessous. Un litteral recopie dans une formule serait exactement la valeur en
dur que le paragraphe 3 des conventions interdit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import NormalDist

from mesure.binomiale import masse_binomiale

#: Plan de la campagne A : 1 667 donnes x 6 replicats de politique. 10 000 n'est pas
#: divisible par 6 ; on depasse la cible plutot que de la manquer.
DONNES_CAMPAGNE_A = 1667
REPLICATS_CAMPAGNE_A = 6

#: Plan de la campagne B : 3 334 donnes x les 3 sieges du greedy.
DONNES_CAMPAGNE_B = 3334
ASSIGNATIONS_CAMPAGNE_B = 3

#: Risque global et puissance cibles, fixes d'avance.
RISQUE = 0.01
PUISSANCE = 0.80

#: Largeur de la fenetre sans creux qui fait declarer la puissance exacte « stable ».
#: 200 valeurs de `n` consecutives : au-dela du dernier creux mesure, les dents de scie
#: sont espacees de 1 a 3 unites, donc une fenetre de cette largeur ne peut pas en manquer.
FENETRE_STABILITE = 200

_NORMALE = NormalDist()


class Variance(Enum):
    """Quel ecart-type entre au terme de puissance d'une formule normale.

    Le nommer est le seul moyen de rendre un `n` reconstructible : deux implementations
    honnetes divergent de 19 parties sur 1 456 selon ce choix, et rien dans le nombre ne
    dit lequel a ete fait.
    """

    #: `sqrt(p0 q0)` aux deux termes. Sous-estime `n` quand `p1` est plus proche de 0,5.
    SOUS_H0 = "sous H0 aux deux termes"
    #: `sqrt(p1 q1)` au terme de puissance -- la forme des manuels.
    SOUS_H1 = "sous H1 au terme de puissance"


def parties(donnes: int, repetitions: int) -> int:
    """Le nombre de parties d'une campagne. Ecrit une fois, pas trois."""
    return donnes * repetitions


def part_neutre(sieges: int) -> float:
    """La part de victoire fractionnee attendue par siege sous absence d'avantage.

    Exactement `1 / sieges`, et non une valeur estimee : les parts fractionnees -- `1/k`
    pour chacun des `k` vainqueurs ex aequo -- **somment a 1 sur les sieges a chaque
    partie**, donc leur moyenne somme a 1. Sous echangeabilite des sieges, chacune vaut
    `1 / sieges`.

    C'est la raison pour laquelle la part **stricte** ne peut pas servir de seuil : elle
    vaut `(1 - P(ex aequo)) / sieges`, dont la valeur est inconnue avant mesure.
    """
    if sieges < 2:
        raise ValueError(f"il faut au moins 2 sieges, {sieges} recu(s)")
    return 1 / sieges


def ecart_type_par_partie(proportion: float) -> float:
    """L'ecart-type d'un indicateur de Bernoulli : `sqrt(p (1 - p))`."""
    if not 0 <= proportion <= 1:
        raise ValueError(f"une proportion vaut entre 0 et 1, {proportion} recue")
    return (proportion * (1 - proportion)) ** 0.5


def erreur_type(proportion: float, nb_parties: int) -> float:
    """L'erreur-type d'une proportion sur `nb_parties` parties **independantes**."""
    if nb_parties < 1:
        raise ValueError(f"il faut au moins une partie, {nb_parties} recue(s)")
    return ecart_type_par_partie(proportion) / nb_parties**0.5


def quantile_bilateral(risque: float, comparaisons: int = 1) -> float:
    """Le `z` d'un test bilateral au risque `risque`, corrige de Bonferroni.

    `comparaisons` est le nombre de tests menes en parallele : trois sieges testes au
    risque nominal de 1 % chacun donnent un risque global de ~3 %. La correction ramene le
    risque **global** a `risque`.
    """
    if not 0 < risque < 1:
        raise ValueError(f"un risque vaut strictement entre 0 et 1, {risque} recu")
    if comparaisons < 1:
        raise ValueError(f"il faut au moins une comparaison, {comparaisons} recue(s)")
    return _NORMALE.inv_cdf(1 - risque / comparaisons / 2)


def quantile_de_puissance(puissance: float) -> float:
    """Le `z` unilateral d'une puissance cible. Public parce que le plan de M3 en a besoin.

    Le garder prive obligerait l'appelant a lire `_NORMALE`, et un acces prive depuis un autre
    module est exactement ce que le renommage de `vue_du_joueur` a corrige ailleurs.
    """
    if not 0 < puissance < 1:
        raise ValueError(f"une puissance vaut strictement entre 0 et 1, {puissance} recue")
    return _NORMALE.inv_cdf(puissance)


def seuil_de_detection(
    proportion: float, nb_parties: int, risque: float, comparaisons: int = 1
) -> float:
    """La proportion au-dela de laquelle un ecart est statistiquement etabli.

    C'est la borne haute de l'intervalle bilateral autour de `proportion`. Un seuil
    **au-dessus** de cette valeur laisse passer des ecarts certains ; c'est le defaut du
    seuil de 38 % du protocole, et `ecarts_types` le chiffre.
    """
    return proportion + quantile_bilateral(risque, comparaisons) * erreur_type(
        proportion, nb_parties
    )


def ecarts_types(
    observee: float, attendue: float, nb_parties: int
) -> float:
    """De combien d'erreurs-type `observee` s'ecarte de `attendue`.

    Sert a dire ce qu'un seuil discrimine : un seuil a 9,9 erreurs-type de l'attendu ne
    signale rien de ce qui est deja certain a 3,5.
    """
    return (observee - attendue) / erreur_type(attendue, nb_parties)


def parties_pour_puissance(
    ecart: float,
    ecart_type_partie: float,
    risque: float,
    puissance: float,
    comparaisons: int = 1,
) -> int:
    """Taille normale a un seul ecart-type, employe aux deux termes. Arrondi au superieur.

    `n >= ((z_risque + z_puissance) * sigma / ecart)^2`.

    **C'est `Variance.SOUS_H0` quand on l'appelle avec `sigma = sqrt(p0 q0)`**, donc la forme
    qui sous-estime `n`. Elle est conservee parce que le tableau de M3 porte sur des gains
    `returns()`, dont l'ecart-type ne depend pas d'une proportion et pour lesquels un seul
    `sigma` est la bonne reponse. Pour une proportion, passer par
    `parties_pour_puissance_proportion`, qui exige de nommer la variance.
    """
    if ecart <= 0:
        raise ValueError(f"un ecart a etablir est strictement positif, {ecart} recu")
    if not 0 < puissance < 1:
        raise ValueError(f"une puissance vaut strictement entre 0 et 1, {puissance} recue")
    z_risque = quantile_bilateral(risque, comparaisons)
    z_puissance = _NORMALE.inv_cdf(puissance)
    exact = ((z_risque + z_puissance) * ecart_type_partie / ecart) ** 2
    return int(-(-exact // 1))


def parties_pour_puissance_proportion(
    attendue: float,
    alternative: float,
    risque: float,
    puissance: float,
    comparaisons: int = 1,
    variance: Variance = Variance.SOUS_H1,
) -> int:
    """Taille normale pour un test de proportion, la variance etant **nommee**.

    `n >= (z_risque * sqrt(p0 q0) + z_puissance * sigma_puissance)^2 / (p1 - p0)^2`, ou
    `sigma_puissance` vaut `sqrt(p0 q0)` sous `Variance.SOUS_H0` et `sqrt(p1 q1)` sous
    `Variance.SOUS_H1`.

    Le defaut est `SOUS_H1`, la forme des manuels : le terme de puissance decrit la loi sous
    l'alternative. `SOUS_H0` est offerte pour que l'ecart entre les deux soit un chiffre
    reproductible et non un desaccord entre deux implementations.

    Raises:
        ValueError: si les deux proportions sont egales -- aucun nombre de parties n'etablit
            un ecart nul, et le dire vaut mieux que de diviser par zero.
    """
    if attendue == alternative:
        raise ValueError(
            f"un ecart nul ne s'etablit sur aucun nombre de parties : p0 = p1 = {attendue}"
        )
    if not 0 < puissance < 1:
        raise ValueError(f"une puissance vaut strictement entre 0 et 1, {puissance} recue")
    sigma_h0 = ecart_type_par_partie(attendue)
    sigma_puissance = (
        sigma_h0 if variance is Variance.SOUS_H0 else ecart_type_par_partie(alternative)
    )
    z_risque = quantile_bilateral(risque, comparaisons)
    z_puissance = _NORMALE.inv_cdf(puissance)
    numerateur = (z_risque * sigma_h0 + z_puissance * sigma_puissance) ** 2
    exact = numerateur / (alternative - attendue) ** 2
    return int(-(-exact // 1))


def valeur_critique(
    nb_parties: int, attendue: float, risque: float, comparaisons: int = 1
) -> int:
    """Le plus petit compte `c` dont la queue superieure sous `attendue` tient le risque.

    On rejette H0 si `K >= c`. Le risque est bilateral, donc la queue superieure en recoit la
    moitie, puis Bonferroni la divise par le nombre de comparaisons.

    **La queue atteinte est strictement inferieure au risque nominal** : un compte est entier,
    il n'existe pas de `c` qui l'egale. C'est ce qui rend le test exact conservateur, donc
    plus couteux en parties que la normale ne l'annonce.
    """
    if nb_parties < 1:
        raise ValueError(f"il faut au moins une partie, {nb_parties} recue(s)")
    plafond = risque / comparaisons / 2
    masse = masse_binomiale(nb_parties, attendue)
    cumul = 0.0
    for compte in range(nb_parties, -1, -1):
        cumul += masse[compte]
        if cumul > plafond:
            return compte + 1
    return 0


def puissance_exacte(
    nb_parties: int,
    attendue: float,
    alternative: float,
    risque: float,
    comparaisons: int = 1,
) -> float:
    """`P(K >= c | alternative)`, `c` etant la valeur critique exacte. Aucune normalite.

    **Non monotone en `nb_parties`** : `c` saute d'une unite, donc la puissance avance en
    dents de scie. C'est la raison d'etre du mode stable de
    `parties_pour_puissance_exacte`.
    """
    critique = valeur_critique(nb_parties, attendue, risque, comparaisons)
    return sum(masse_binomiale(nb_parties, alternative)[critique:])


@dataclass(frozen=True)
class TailleExacte:
    """Le resultat d'un calcul de taille exact, dents de scie comprises.

    Attributes:
        franchissement: le plus petit `n` dont la puissance atteint la cible. C'est une
            coincidence d'arrondi : la puissance y redescend souvent des `n + 1`.
        stable: le plus petit `n` a partir duquel la puissance ne redescend plus, sur une
            fenetre de `FENETRE_STABILITE`. **C'est le chiffre publie.**
        dernier_creux: le dernier `n` dont la puissance passe sous la cible. `stable` vaut
            `dernier_creux + 1` ; le publier montre l'ampleur de la dent de scie.
        puissance_stable: la puissance atteinte en `stable`.
    """

    franchissement: int
    stable: int
    dernier_creux: int
    puissance_stable: float


def parties_pour_puissance_exacte(
    attendue: float,
    alternative: float,
    risque: float,
    puissance: float,
    comparaisons: int = 1,
    depart: int | None = None,
) -> TailleExacte:
    """La taille exacte, par balayage : franchissement, dernier creux, et taille stable.

    Le balayage part de `depart` -- par defaut la taille normale a un seul ecart-type, qui
    minore les trois -- et monte jusqu'a ce que `FENETRE_STABILITE` valeurs consecutives de
    `n` tiennent la cible.

    Raises:
        ValueError: si `alternative` n'est pas strictement au-dessus de `attendue`. Le
            balayage est ecrit pour une alternative superieure ; l'appeler autrement rendrait
            un nombre sans le signaler.
    """
    if alternative <= attendue:
        raise ValueError(
            f"le balayage exact demande une alternative superieure a l'attendu : "
            f"{alternative} <= {attendue}"
        )
    sigma = ecart_type_par_partie(attendue)
    if depart is None:
        depart = parties_pour_puissance(
            alternative - attendue, sigma, risque, puissance, comparaisons
        )
    franchissement: int | None = None
    dernier_creux = max(0, depart - 1)
    nb_parties = max(1, depart)
    while nb_parties <= dernier_creux + FENETRE_STABILITE:
        atteinte = puissance_exacte(nb_parties, attendue, alternative, risque, comparaisons)
        if atteinte >= puissance:
            if franchissement is None:
                franchissement = nb_parties
        else:
            dernier_creux = nb_parties
        nb_parties += 1
    if franchissement is None:  # pragma: no cover - la fenetre est sans creux par sortie
        raise RuntimeError("la fenetre de stabilite ne contient aucun franchissement")
    stable = dernier_creux + 1
    return TailleExacte(
        franchissement=franchissement,
        stable=stable,
        dernier_creux=dernier_creux,
        puissance_stable=puissance_exacte(
            stable, attendue, alternative, risque, comparaisons
        ),
    )


def puissance_atteinte(
    ecart: float,
    ecart_type_partie: float,
    nb_parties: int,
    risque: float,
    comparaisons: int = 1,
) -> float:
    """La probabilite de detecter un ecart vrai de `ecart` avec `nb_parties` parties.

    L'ecrire est ce qui empeche de lire une absence de detection comme une absence
    d'effet : a 10 002 parties, un siege a 35 % n'est detecte que trois fois sur quatre.
    """
    if nb_parties < 1:
        raise ValueError(f"il faut au moins une partie, {nb_parties} recue(s)")
    z_risque = quantile_bilateral(risque, comparaisons)
    return _NORMALE.cdf(ecart * nb_parties**0.5 / ecart_type_partie - z_risque)


def erreur_relative_ecart_type(nb_parties: int) -> float:
    """L'erreur relative d'un ecart-type estime sur `nb_parties` : `1 / sqrt(2 n)`.

    C'est ce qui rend M2 decide bien avant la fin de la campagne, et donc ce qui deplace
    son contenu reel vers la correlation intra-donne et le tableau de dimensionnement.
    """
    if nb_parties < 1:
        raise ValueError(f"il faut au moins une partie, {nb_parties} recue(s)")
    return 1 / (2 * nb_parties) ** 0.5


def parties_pour_erreur_relative(cible: float) -> int:
    """L'inverse : combien de parties pour connaitre un ecart-type a `cible` pres."""
    if not 0 < cible < 1:
        raise ValueError(f"une erreur relative cible vaut entre 0 et 1, {cible} recue")
    return int(-(-(1 / (2 * cible**2)) // 1))


def parties_pour_contraste_apparie(
    ecart: float,
    ecart_type_partie: float,
    correlation: float,
    risque: float,
    puissance: float,
    comparaisons: int = 1,
) -> int:
    """Parties pour etablir un ecart de moyennes entre deux politiques, en plan apparie.

    La variance d'un contraste apparie vaut `2 sigma^2 (1 - rho)` contre `2 sigma^2` sans
    appariement : le gain de parties est un facteur `1 / (1 - rho)`. `correlation = 0`
    rend donc le cas non apparie, et c'est ce qui permet de publier les deux colonnes du
    tableau du paragraphe 3.3 avec une seule fonction.

    Raises:
        ValueError: si `correlation` n'est pas dans `[0, 1)`. A `rho = 1` les deux
            politiques sont indistinguables sur une meme donne et aucun nombre de parties
            ne conclut.
    """
    if not 0 <= correlation < 1:
        raise ValueError(f"une correlation d'appariement vaut dans [0, 1), {correlation} recue")
    variance_contraste = 2 * ecart_type_partie**2 * (1 - correlation)
    return parties_pour_puissance(
        ecart, variance_contraste**0.5, risque, puissance, comparaisons
    )


@dataclass(frozen=True)
class PlanM1:
    """Le plan de M1, calcule et non recopie.

    Attributes:
        sieges: nombre de sieges testes, donc de comparaisons.
        nb_parties: parties de la campagne A.
        neutre: part de victoire fractionnee attendue par siege.
        ecart_type_partie: ecart-type de l'indicateur, par partie.
        erreur_type: erreur-type de la part, iid.
        seuil_protocole: le seuil ecrit au paragraphe 3 du protocole.
        seuil_non_corrige: detection bilaterale au risque nominal.
        seuil_bonferroni: detection bilaterale au risque global, corrigee.
        ecarts_types_du_protocole: a combien d'erreurs-type le seuil du protocole se situe.
    """

    sieges: int
    nb_parties: int
    neutre: float
    ecart_type_partie: float
    erreur_type: float
    seuil_protocole: float
    seuil_non_corrige: float
    seuil_bonferroni: float
    ecarts_types_du_protocole: float


def plan_m1(sieges: int = 3, seuil_protocole: float = 0.38) -> PlanM1:
    """Le plan complet de M1 pour la campagne A."""
    nb_parties = parties(DONNES_CAMPAGNE_A, REPLICATS_CAMPAGNE_A)
    neutre = part_neutre(sieges)
    return PlanM1(
        sieges=sieges,
        nb_parties=nb_parties,
        neutre=neutre,
        ecart_type_partie=ecart_type_par_partie(neutre),
        erreur_type=erreur_type(neutre, nb_parties),
        seuil_protocole=seuil_protocole,
        seuil_non_corrige=seuil_de_detection(neutre, nb_parties, RISQUE),
        seuil_bonferroni=seuil_de_detection(neutre, nb_parties, RISQUE, sieges),
        ecarts_types_du_protocole=ecarts_types(seuil_protocole, neutre, nb_parties),
    )


def _pourcent(valeur: float) -> str:
    return f"{100 * valeur:.4f} %"


def rapport_de_plan(sieges: int = 3, alternatives: tuple[float, ...] = (0.38, 0.35)) -> str:
    """Le texte des chiffres de plan, **chaque resultat suivi de ses parametres**.

    Un `n` sans sa formule n'est pas reconstructible : deux implementations honnetes
    divergent de 19 parties sur 1 456 selon l'ecart-type retenu au terme de puissance. Ce
    rapport rend donc les trois calculs, leurs `z`, leurs ecarts-type, la valeur critique du
    test exact, et l'ampleur de la dent de scie.
    """
    plan = plan_m1(sieges)
    neutre = plan.neutre
    sigma = plan.ecart_type_partie
    z_risque = quantile_bilateral(RISQUE, sieges)
    z_puissance = _NORMALE.inv_cdf(PUISSANCE)
    lignes = [
        "# Chiffres de plan de la phase 2",
        "",
        "Aucune partie jouee. Recalcul de `phase2_hypothese_et_instrument.md`.",
        "",
        "## Campagnes",
        f"- A : {DONNES_CAMPAGNE_A} donnes x {REPLICATS_CAMPAGNE_A} replicats = "
        f"{parties(DONNES_CAMPAGNE_A, REPLICATS_CAMPAGNE_A)} parties",
        f"- B : {DONNES_CAMPAGNE_B} donnes x {ASSIGNATIONS_CAMPAGNE_B} assignations = "
        f"{parties(DONNES_CAMPAGNE_B, ASSIGNATIONS_CAMPAGNE_B)} parties",
        "",
        "## Parametres communs",
        f"- risque global bilateral : {RISQUE} ; comparaisons (sieges) : {sieges} ; "
        f"donc {RISQUE / sieges / 2:.6g} par queue",
        f"- z_risque = {z_risque:.6f} ; z_puissance = {z_puissance:.6f} "
        f"(puissance cible {PUISSANCE})",
        f"- p0 = {neutre:.10f} ; sqrt(p0 q0) = {sigma:.6f}",
        "",
        "## M1 -- avantage de siege",
        f"- niveau neutre de la part fractionnee : {_pourcent(neutre)} (exact, pas estime)",
        f"- ecart-type par partie : {_pourcent(sigma)}",
        f"- erreur-type a n = {plan.nb_parties} : {_pourcent(plan.erreur_type)} (iid)",
        f"- seuil du protocole : {_pourcent(plan.seuil_protocole)} "
        f"= {plan.ecarts_types_du_protocole:.2f} erreurs-type de l'attendu",
        f"- detection a {int(100 * (1 - RISQUE))} % non corrigee : "
        f"{_pourcent(plan.seuil_non_corrige)}",
        f"- detection a {int(100 * (1 - RISQUE))} % Bonferroni sur {sieges} sieges : "
        f"{_pourcent(plan.seuil_bonferroni)}",
        "",
        "## M1 -- a quel nombre de parties la mesure tranche",
        "",
        "Trois calculs, parce qu'un `n` depend de sa formule. La reference est l'exact",
        "stable : lui seul ne suppose aucune normalite et aucune chance d'arrondi.",
    ]
    for cible in alternatives:
        ecart = cible - neutre
        sigma_h1 = ecart_type_par_partie(cible)
        sous_h0 = parties_pour_puissance_proportion(
            neutre, cible, RISQUE, PUISSANCE, sieges, Variance.SOUS_H0
        )
        sous_h1 = parties_pour_puissance_proportion(
            neutre, cible, RISQUE, PUISSANCE, sieges, Variance.SOUS_H1
        )
        exacte = parties_pour_puissance_exacte(neutre, cible, RISQUE, PUISSANCE, sieges)
        critique = valeur_critique(exacte.stable, neutre, RISQUE, sieges)
        normale = puissance_atteinte(ecart, sigma, plan.nb_parties, RISQUE, sieges)
        exact = puissance_exacte(plan.nb_parties, neutre, cible, RISQUE, sieges)
        lignes += [
            "",
            f"### Un siege a {_pourcent(cible)} -- ecart vrai de {_pourcent(ecart)}",
            f"- sqrt(p1 q1) = {sigma_h1:.6f}",
            f"- normale, {Variance.SOUS_H0.value} : **{sous_h0}** parties",
            "  `n = ((z_risque + z_puissance) sqrt(p0 q0) / ecart)^2`",
            f"- normale, {Variance.SOUS_H1.value} : **{sous_h1}** parties",
            "  `n = (z_risque sqrt(p0 q0) + z_puissance sqrt(p1 q1))^2 / ecart^2`",
            f"- exact binomial, premier franchissement : {exacte.franchissement} parties "
            f"-- coincidence d'arrondi, la puissance redescend ensuite",
            f"- exact binomial, dernier creux : {exacte.dernier_creux} parties "
            f"(dent de scie de {exacte.dernier_creux - exacte.franchissement + 1} unites)",
            f"- **exact binomial, stable : {exacte.stable} parties** -- puissance "
            f"{100 * exacte.puissance_stable:.3f} %, rejet si K >= {critique}",
            f"- puissance a n = {plan.nb_parties} : normale {100 * normale:.1f} %, "
            f"**exacte {100 * exact:.1f} %**",
        ]
    lignes += [
        "",
        "## M2 -- precision de l'ecart-type",
        f"- erreur relative a n = {plan.nb_parties} : "
        f"{100 * erreur_relative_ecart_type(plan.nb_parties):.3f} %",
        f"- parties pour 5 % relatif : {parties_pour_erreur_relative(0.05)}",
        "",
        "## M3 -- contraste de gain moyen, formule",
        "- `n >= ((z_risque + z_puissance) * sigma * sqrt(2 (1 - rho)) / ecart)^2`",
        "- un gain `returns()` n'est pas une proportion : son ecart-type ne depend pas de la",
        "  valeur testee, donc un seul sigma est ici la bonne reponse et la question",
        "  SOUS_H0 / SOUS_H1 ne se pose pas.",
        "- sigma et rho sont **mesures** en M2 ; les remplir ici avec un sigma suppose",
        "  produirait un chiffre qui a l'air d'un fait.",
    ]
    return "\n".join(lignes)


def main() -> int:
    """Ecrit les chiffres de plan sur la sortie standard."""
    print(rapport_de_plan())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
