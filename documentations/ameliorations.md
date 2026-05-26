# Récapitulatif des axes d'amélioration

Audit du projet effectué sur la branche `main`. Le tableau ci-dessous liste les
26 points identifiés, leur sévérité, et indique si un patch est livré dans cette
itération. Les points non patchés sont décrits plus bas avec une piste
d'implémentation.

## Tableau récapitulatif

| #  | Catégorie       | Point                                                                 | Sévérité | Patché ? |
|----|-----------------|-----------------------------------------------------------------------|----------|----------|
| 1  | Dépendances     | `torch` absent de `requirements.txt` / `pyproject.toml`               | 🔴       | ✅ oui   |
| 2  | IA / MCTS       | Backprop `value = -value` cassée à N ≥ 3 joueurs                      | 🔴       | ✅ oui   |
| 3  | IA / MCTS       | Pas de bruit de Dirichlet à la racine                                 | 🟠       | ✅ oui   |
| 4  | IA / MCTS       | Softmax appliqué avant masquage des actions illégales                 | 🟡       | ✅ oui   |
| 5  | Moteur          | Fin de partie déclenchée trop tôt (pioche vide, mains non vides)      | 🔴       | ✅ oui   |
| 6  | Moteur          | Assassins multiples dans un même tour ignorés                         | 🟠       | ✅ oui (documenté + résolution en chaîne pour l'IA) |
| 7  | Moteur          | Espions exclus du scoring par `c.visible`                             | 🔴       | ✅ oui (révélation à la fin de partie) |
| 8  | IA / MCTS       | `clone_determinized` triche (information parfaite)                    | 🟠       | ✅ oui (PIMC : permutation des identités non vues, contrainte espion préservée) |
| 9  | Robustesse      | `except:` nus dans `mcts_network.py` et Streamlit                     | 🟡       | ✅ oui   |
| 10 | Architecture    | `courtisans_app.py` monolithique (613 lignes)                         | 🟠       | ✅ oui   |
| 11 | Qualité         | Aucun test                                                            | 🔴       | ✅ oui (tests pytest pour moteur et mapper) |
| 12 | Architecture    | `ActionMapper` n'a pas d'`encode`                                     | 🟡       | ✅ oui   |
| 13 | Qualité         | Type hints quasi absents                                              | 🟡       | ✅ oui (signatures publiques principales) |
| 14 | Qualité         | `print` partout, pas de `logging`                                     | 🟡       | ✅ oui   |
| 15 | Reproductibilité| Pas de seed sur `random` / `torch`                                    | 🟡       | ✅ oui   |
| 16 | IA              | Memory non persistée + pas de checkpoints intermédiaires              | 🟠       | ✅ oui   |
| 17 | IA              | Pas de réseau "target" / arena d'évaluation                           | 🟠       | ❌ non (gros chantier, voir note) |
| 18 | IA              | BatchNorm + batch=1 fragile en mode train                             | 🟡       | ❌ non (mitigé par `eval()` à l'inférence) |
| 19 | IA              | `num_sims` hard-codé (30 train / 50 inférence)                        | 🟡       | ✅ oui   |
| 20 | Robustesse      | `torch.load` sans `weights_only=True` dans `play_vs_ai`               | 🟡       | ✅ oui   |
| 21 | Doc             | `configuration.md` désynchronisé (3.10 vs 3.12, venv vs uv)           | 🟡       | ✅ oui   |
| 22 | Doc / CLI       | `main.py` ne fait rien                                                | 🟡       | ✅ oui (vrai CLI `train` / `play`) |
| 23 | Repo            | `models/model_2.pth` versionné dans git                               | 🟡       | ❌ non (décision produit, voir note) |
| 24 | DevEx           | Pas de CI ni de pré-commit                                            | 🟠       | ✅ oui (workflow GitHub Actions + ruff) |
| 25 | Doc             | README — chemin de clone (`github.com:` au lieu de `github.com-perso:`) | 🟢     | ✅ oui   |
| 26 | Doc             | Nom du projet incohérent (`Courtisants-Games` vs `courtisans-game`…)  | 🟢       | ✅ oui (uniformisation `courtisans_game`) |

Légende sévérité : 🔴 bug fonctionnel · 🟠 architecture · 🟡 qualité / hygiène · 🟢 cosmétique.

---

## Points non patchés : pistes d'implémentation

### #17 — Arena d'évaluation entre versions du modèle

Aujourd'hui `train()` écrase aveuglément `model_2.pth`. Une régression
silencieuse est possible. À ajouter :
- garder un `best_model` et un `candidate` ;
- jouer N parties candidate vs best (avec un MCTS un peu plus profond et
  température basse) ;
- promouvoir candidate → best si winrate > 55 %.

### #18 — BatchNorm + batch=1

`MCTS._expand` passe un seul état à la fois. En mode `eval()` les running stats
font le job ; en mode `train()` ça crasherait. Aucune incidence aujourd'hui
puisque l'entraînement utilise des mini-batchs de 64. À revoir si on veut faire
de l'expansion par batch (asynchrone).

### #23 — `models/model_2.pth` versionné

Garder un binaire dans git est une dette mais aucune solution n'est neutre :
- **Git LFS** : prix + complexité de setup ;
- **Release GitHub** : ajoute une étape manuelle ;
- **Statu quo** : OK tant que le fichier reste petit (~ qq Mo) et qu'on
  ne le met à jour qu'occasionnellement.

Décision à prendre par le propriétaire du projet. Si la taille augmente,
basculer en release GitHub avec un script `scripts/download_model.py`.
