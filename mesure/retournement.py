"""Les quatre definitions du retournement, sur la suite des statuts d'une famille.

Aucun document du projet ne definit « retournement » de facon mesurable. Le paragraphe 2.2
des regles en decrit le **mecanisme** -- une famille change de statut au banquet -- sans dire
ce qu'on compte. Les quatre definitions ci-dessous sont proposees dans
`hypothese_et_instrument.md`, ecrit avant toute mesure ; **le go/no-go porte sur R2**,
arbitre par l'auteur et deja tranche par l'encadre du paragraphe 2.2 : « le seuil qui compte
est l'Indifference, pas l'Obscurite ».

Elles sont rendues **sans hierarchie supposee**. Les inclusions vraies sont `R1 ⊆ R2`,
`R3 ⊆ R2` et `R2 ⊆ R0` ; en revanche **R1 et R3 ne sont pas ordonnees** -- une famille
Lumiere puis Obscurite puis Lumiere satisfait R1 et pas R3. Les tests les verifient au lieu
de les supposer.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from courtisans.rules import Statut


@dataclass(frozen=True)
class Retournements:
    """Les quatre definitions, evaluees sur une meme suite de statuts.

    Attributes:
        r0: toute transition -- `∃ t : s_t != s_{t-1}`.
        r1: inversion de signe -- dans la suite privee de ses Indifferente, deux valeurs
            consecutives ont des signes opposes.
        r2: perte d'acquis -- `∃ t : s_{t-1} != Indifferente et s_t != s_{t-1}`.
        r3: divergence finale -- le premier statut non-Indifferent existe, et le statut
            final en differe.
    """

    r0: bool
    r1: bool
    r2: bool
    r3: bool

    @classmethod
    def ou(cls, retournements: Iterable[Retournements]) -> Retournements:
        """L'agregation d'une partie : une definition tient des qu'**une** famille la tient.

        Le neutre est faux partout, ce qui est le bon neutre : une partie sans aucune
        famille ne retourne rien.
        """
        agrege = cls(r0=False, r1=False, r2=False, r3=False)
        for retournement in retournements:
            agrege = cls(
                r0=agrege.r0 or retournement.r0,
                r1=agrege.r1 or retournement.r1,
                r2=agrege.r2 or retournement.r2,
                r3=agrege.r3 or retournement.r3,
            )
        return agrege


def analyser_suite(suite: Sequence[Statut]) -> Retournements:
    """Evalue les quatre definitions sur la suite des statuts d'une famille.

    Args:
        suite: les statuts successifs, `suite[0]` etant le statut avant tout evenement --
            Indifferente, le plateau etant vide.

    Raises:
        ValueError: si la suite est vide. Une famille a toujours au moins son statut
            initial ; une suite vide signale un releve qui n'a pas eu lieu, pas une famille
            sans histoire.
    """
    if not suite:
        raise ValueError(
            "une suite de statuts contient au moins un statut, celui du plateau initial"
        )

    transitions = list(zip(suite, suite[1:], strict=False))
    r0 = any(avant is not apres for avant, apres in transitions)
    r2 = any(
        avant is not Statut.INDIFFERENTE and avant is not apres for avant, apres in transitions
    )

    # Prive de ses Indifferente, il ne reste que Lumiere et Obscurite : deux valeurs
    # consecutives differentes y sont necessairement de signes opposes.
    signes = [statut for statut in suite if statut is not Statut.INDIFFERENTE]
    r1 = any(avant is not apres for avant, apres in zip(signes, signes[1:], strict=False))
    r3 = bool(signes) and suite[-1] is not signes[0]

    return Retournements(r0=r0, r1=r1, r2=r2, r3=r3)


def evenements_r2(suite: Sequence[Statut]) -> tuple[int, ...]:
    """Les indices ou une **perte d'acquis** se produit, et pas seulement s'il y en a une.

    `analyser_suite(...).r2` repond « cette famille a-t-elle perdu un acquis », un booleen.
    Cette fonction repond « quand », ce qui est la seule facon de comparer deux vues
    **evenement par evenement** : deux vues peuvent toutes les deux porter un R2 sans que
    ce soit le meme.

    **Ecrite apres l'audit croise, qui a rejete la premiere version de la mesure.** Le
    rapport comparait la vue vraie et les vues par siege apres avoir agrege les quatre
    familles en un booleen de partie, puis agrege les trois sieges par un `any` : la
    conjonction « vrai oui, aucun siege » etait alors quasi impossible par construction, et
    le zero qu'elle affichait ne mesurait pas ce que la phrase annoncait. On ne compare
    plus que des grandeurs non agregees.

    Raises:
        ValueError: si la suite est vide, comme `analyser_suite`.
    """
    if not suite:
        raise ValueError(
            "une suite de statuts contient au moins un statut, celui du plateau initial"
        )
    return tuple(
        indice
        for indice, (avant, apres) in enumerate(zip(suite, suite[1:], strict=False), start=1)
        if avant is not Statut.INDIFFERENTE and avant is not apres
    )
