"""Les calculs de plan de la phase 2 : seuils, puissance, taille d'echantillon.

**Aucune partie n'est jouee ici.** Ce module ne mesure rien : il recalcule les chiffres de
`phase2_hypothese_et_instrument.md` paragraphes 2.3, 2.4, 3.4 et 4.4, pour qu'un lecteur
puisse les reconstruire au lieu de les croire (paragraphe 10 des conventions : un chiffre
qui ne peut pas etre reconstruit se decompose ou se retire).

Les formules sont normales-approchees et supposent des parties **independantes**. C'est
volontaire, et c'est dit : les seuils du plan sont calcules ainsi *avant* la mesure, puis
recalcules sur la variance bootstrap par donne dans le compte rendu. L'ecart entre les deux
est l'**effet de plan**, et son signe n'est pas suppose ici -- voir le paragraphe 1.3 du
document.

Un seul endroit ecrit le nombre de sieges, le nombre de parties et le risque : les
constantes ci-dessous. Un litteral recopie dans une formule serait exactement la valeur en
dur que le paragraphe 3 des conventions interdit.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

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

_NORMALE = NormalDist()


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
    """Le nombre de parties pour etablir un ecart vrai de `ecart`, arrondi au superieur.

    Formule normale a deux quantiles : `n >= ((z_risque + z_puissance) * sigma / ecart)^2`.
    """
    if ecart <= 0:
        raise ValueError(f"un ecart a etablir est strictement positif, {ecart} recu")
    if not 0 < puissance < 1:
        raise ValueError(f"une puissance vaut strictement entre 0 et 1, {puissance} recue")
    z_risque = quantile_bilateral(risque, comparaisons)
    z_puissance = _NORMALE.inv_cdf(puissance)
    exact = ((z_risque + z_puissance) * ecart_type_partie / ecart) ** 2
    return int(-(-exact // 1))


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


def rapport_de_plan(sieges: int = 3) -> str:
    """Le texte des chiffres de plan, tel que le compte rendu les cite."""
    plan = plan_m1(sieges)
    neutre = plan.neutre
    sigma = plan.ecart_type_partie
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
        "## M1 -- avantage de siege",
        f"- niveau neutre de la part fractionnee : {_pourcent(neutre)} (exact, pas estime)",
        f"- ecart-type par partie : {_pourcent(sigma)}",
        f"- erreur-type a n = {plan.nb_parties} : {_pourcent(plan.erreur_type)}",
        f"- seuil du protocole : {_pourcent(plan.seuil_protocole)} "
        f"= {plan.ecarts_types_du_protocole:.2f} erreurs-type de l'attendu",
        f"- detection a {int(100 * (1 - RISQUE))} % non corrigee : "
        f"{_pourcent(plan.seuil_non_corrige)}",
        f"- detection a {int(100 * (1 - RISQUE))} % Bonferroni sur {sieges} sieges : "
        f"{_pourcent(plan.seuil_bonferroni)}",
        "",
        "## M1 -- a quel nombre de parties la mesure tranche",
    ]
    for cible in (plan.seuil_protocole, 0.35):
        ecart = cible - neutre
        lignes.append(
            f"- ecart vrai de {_pourcent(ecart)} (un siege a {_pourcent(cible)}) : "
            f"{parties_pour_puissance(ecart, sigma, RISQUE, PUISSANCE, sieges)} parties "
            f"pour {int(100 * PUISSANCE)} % de puissance ; "
            f"puissance a n = {plan.nb_parties} : "
            f"{100 * puissance_atteinte(ecart, sigma, plan.nb_parties, RISQUE, sieges):.1f} %"
        )
    lignes += [
        "",
        "## M2 -- precision de l'ecart-type",
        f"- erreur relative a n = {plan.nb_parties} : "
        f"{100 * erreur_relative_ecart_type(plan.nb_parties):.3f} %",
        f"- parties pour 5 % relatif : {parties_pour_erreur_relative(0.05)}",
        "",
        "## M3 -- contraste de gain moyen, formule",
        "- `n >= ((z_risque + z_puissance) * sigma * sqrt(2 (1 - rho)) / ecart)^2`",
        "- sigma et rho sont **mesures** en M2 ; les remplir ici avec un sigma suppose "
        "produirait un chiffre qui a l'air d'un fait.",
    ]
    return "\n".join(lignes)


def main() -> int:
    """Ecrit les chiffres de plan sur la sortie standard."""
    print(rapport_de_plan())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
