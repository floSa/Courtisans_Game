"""Les agents de la phase 2. **Hors de `courtisans/`, et ce n'est pas un detail.**

Le paragraphe 4 des conventions interdit toute heuristique, toute evaluation et tout score de
position dans le module de regles. La raison est ecrite : l'ancien `app/jeu.py` contenait
`_pick_target_heuristic`, une heuristique d'IA au milieu des regles, qui ne rendait `None` que
si la liste de cibles etait vide. Consequence -- **aucune politique du projet n'a jamais refuse
de tuer**, alors que le moteur le permettait. Une regle du jeu a ete perdue parce qu'une IA
vivait dans le fichier des regles.

Trois modules, et la frontiere entre eux est la garantie principale du paquet :

| Module | Voit un `State` | Role |
|---|---|---|
| `perception` | **oui** | traduit un etat en `Perception` : ce que le decideur sait |
| `greedy` | **jamais** | decide, a partir d'une `Perception` seule |
| `politique` | **oui** | colle les deux, pour donner une `Politique` a `mesure.partie.observer` |

`greedy` ne peut donc pas tricher, faute d'avoir quoi que ce soit a lire : c'est structurel,
pas disciplinaire. Trois preuves executables l'etablissent quand meme, dans
`tests/agents/test_aveuglement.py`.
"""
