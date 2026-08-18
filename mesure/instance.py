"""L'instance mesuree en phase 1, **definie une seule fois**.

Elle etait ecrite deux fois -- dans `rapport.py` et dans les tests de mesure -- ce que le
paragraphe 2 des conventions interdit : deux definitions finissent par ne plus etre
d'accord, et c'est la mesure qui aurait tort sans que rien ne le signale.

`tests/outils.py` en garde une troisieme description, `ENTRAINEMENT_3J`, et **c'est
volontaire** : celle-la est un `Instance`, une description cote test qui recalcule
l'arithmetique des regles **sans importer le moteur**, pour servir d'attendu. Elle ne doit
justement pas etre la meme objet que celui qu'elle verifie.
"""

from __future__ import annotations

from courtisans.cards import Role
from courtisans.config import GameConfig

#: `entrainement-3j`, paragraphe 3 de `03_specification_moteur.md`. Elle n'est pas choisie
#: ici, elle est fixee : la variante a 20 cartes est refusee a la construction par le
#: plancher `tours >= 3` du paragraphe 8 des regles.
ENTRAINEMENT_3J = GameConfig(familles=4, roles=tuple(Role), exemplaires=2, joueurs=3)
