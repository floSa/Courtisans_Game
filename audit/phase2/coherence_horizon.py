"""Mon 7,33 %, avec son echantillon nomme -- et la meme mesure sur SA population.

Ce que ce module mesure. A un nœud de ciblage ou **au moins un Assassin reste en attente**,
deux ensembles d'argmax sont compares :

  - **myope** : `agents.greedy.evaluer_actions`, ce que la politique fait reellement -- elle
    evalue le nœud courant seul, `Perception` ne portant pas les Assassins en attente ;
  - **coherent** : pour chaque action, l'ecart atteignable en resolvant ensuite les Assassins
    restants au mieux, par `agents.greedy._meilleur_apres_assassins` -- exactement ce que
    l'evaluation de la POSE avait suppose.

Un desaccord est un nœud ou la pose a promis une valeur que le ciblage ne poursuit pas.

**Pourquoi ce module existe.** Mon verdict du tour 1 a publie `7,33 % sur 2 429 nœuds` sans
nommer son echantillon -- la faute que je reprochais par ailleurs. Son chiffre a lui,
`4,23 % sur 4 063 nœuds`, IC 99 % [3,46 ; 5,11], ne recouvre pas le mien. L'hypothese testee
ici est que **le denominateur est le meme et la population ne l'est pas** : j'avais mesure
trois greedys, sa campagne B fait jouer un greedy contre deux uniformes. Les deux nombres
seraient alors tous les deux justes, et le mien mal etiquete.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass

from agents.greedy import _meilleur_apres_assassins, choisir, evaluer_actions
from agents.perception import percevoir
from audit.phase2.greedy import Aleatoire
from audit.phase2.stats import clopper_pearson
from courtisans.engine import Engine, Phase
from mesure.instance import ENTRAINEMENT_3J as CONFIG

#: Le decalage de graine de sa campagne B, repris pour que ses adversaires soient les miens.
DECALAGE_B = 3_000_000

#: La graine du departage du greedy. **Nommee** : c'est la valeur en dur invisible dans les
#: chiffres qu'elle produit qui a coute deux fautes a l'audit de la phase 1.
GRAINE_DEPARTAGE = 777


@dataclass
class Comptage:
    """Les nœuds examines et ceux ou les deux argmax divergent."""

    population: str
    parties: int
    tours: int
    noeuds_avec_attente: int
    desaccords: int

    def texte(self) -> str:
        """Le taux, son numerateur, son denominateur et son IC 99 %."""
        if self.noeuds_avec_attente == 0:
            return f"{self.population} : aucun nœud a Assassin en attente, taux sans objet"
        bas, haut = clopper_pearson(
            self.desaccords, self.noeuds_avec_attente, 0.01
        )
        taux = 100 * self.desaccords / self.noeuds_avec_attente
        return (
            f"{self.population} : {self.desaccords} / {self.noeuds_avec_attente} nœuds a "
            f"Assassin en attente = {taux:.2f} %, IC99 [{100 * bas:.2f} ; {100 * haut:.2f}] "
            f"-- {self.parties} parties, {self.tours} tours"
        )


def _argmax(valeurs: dict[int, int]) -> set[int]:
    """Les actions atteignant le maximum. Un ensemble : l'ordre du departage n'entre pas."""
    sommet = max(valeurs.values())
    return {action for action, valeur in valeurs.items() if valeur == sommet}


def _argmax_coherent(etat, perception, joueur: int) -> set[int]:
    """L'argmax que donnerait un ciblage coherent avec la valeur promise par la pose."""
    plateau = list(perception.connues)
    attente = list(etat.assassins_en_attente())
    valeurs: dict[int, int] = {}
    for action in perception.actions_legales:
        if action >= len(perception.cibles) or perception.cibles[action].carte is None:
            # Refus, ou meurtre d'un dos : sans effet sur la vue du decideur.
            reste = plateau
            survivants = attente[1:]
        else:
            cible = perception.cibles[action]
            indice = next(
                rang
                for rang, posee in enumerate(plateau)
                if posee.carte == cible.carte and posee.zone == cible.zone
            )
            reste = [p for rang, p in enumerate(plateau) if rang != indice]
            # Un Assassin encore en attente pourrait etre la victime : le retirer, comme le
            # fait `_meilleur_apres_assassins` lui-meme.
            survivants = [
                a
                for a in attente[1:]
                if not (a.carte == cible.carte and a.zone == cible.zone)
            ]
        valeurs[action] = _meilleur_apres_assassins(reste, survivants, joueur, CONFIG)
    return _argmax(valeurs)


def mesurer(population: str, parties: int) -> Comptage:
    """Joue `parties` parties de cette population et compte les desaccords.

    `population` vaut `trois-greedys` -- celle de mon verdict du tour 1 -- ou
    `un-greedy-deux-hasards`, la composition de sa campagne B, chaque donne jouee aux trois
    sieges.
    """
    engine = Engine(CONFIG)
    alea = random.Random(GRAINE_DEPARTAGE)
    resultat = Comptage(population, 0, 0, 0, 0)

    class SonGreedy:
        """Sa politique, graine partagee, pour que la trajectoire soit reproductible."""

        def action(self, etat) -> int:
            """L'action de son greedy sur cet etat."""
            return choisir(percevoir(etat, etat.current_player()), alea)

    greedy = SonGreedy()
    for donne in range(parties):
        sieges = [0] if population == "trois-greedys" else range(CONFIG.joueurs)
        for siege_greedy in sieges:
            if population == "trois-greedys":
                table: list = [greedy] * CONFIG.joueurs
                mesures = set(range(CONFIG.joueurs))
            else:
                table = [
                    Aleatoire(random.Random(DECALAGE_B + 3 * donne + s))
                    for s in range(CONFIG.joueurs)
                ]
                table[siege_greedy] = greedy
                mesures = {siege_greedy}
            etat = engine.reset(donne)
            resultat.parties += 1
            while not etat.is_terminal():
                joueur = etat.current_player()
                if etat.phase() is Phase.POSE:
                    if joueur in mesures:
                        resultat.tours += 1
                    etat.apply(table[joueur].action(etat))
                    continue
                perception = percevoir(etat, joueur)
                if joueur in mesures and len(etat.assassins_en_attente()) >= 2:
                    resultat.noeuds_avec_attente += 1
                    myope = _argmax(evaluer_actions(perception))
                    coherent = _argmax_coherent(etat, perception, joueur)
                    if myope != coherent:
                        resultat.desaccords += 1
                etat.apply(table[joueur].action(etat))
    return resultat


def main() -> int:
    """Mesure les deux populations et publie les deux taux avec leurs intervalles."""
    parties = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    print(f"instance entrainement-3j, donnes 0 a {parties - 1}, ")
    print(f"graine de departage du greedy Random({GRAINE_DEPARTAGE}), partagee")
    print(f"adversaires uniformes Random({DECALAGE_B} + 3 x donne + siege)")
    print("denominateur : nœud de ciblage ou au moins un Assassin reste en attente")
    print()
    for population in ("trois-greedys", "un-greedy-deux-hasards"):
        print(mesurer(population, parties).texte())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
