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
| 17 | IA              | Pas de réseau "target" / arena d'évaluation                           | 🟠       | ✅ oui (fonction `arena()` + intégration `train()`, promotion candidate→best si winrate ≥ 55 %) |
| 18 | IA              | BatchNorm + batch=1 fragile en mode train                             | 🟡       | ✅ oui (bascule en `LayerNorm`) |
| 19 | IA              | `num_sims` hard-codé (30 train / 50 inférence)                        | 🟡       | ✅ oui   |
| 20 | Robustesse      | `torch.load` sans `weights_only=True` dans `play_vs_ai`               | 🟡       | ✅ oui   |
| 21 | Doc             | `configuration.md` désynchronisé (3.10 vs 3.12, venv vs uv)           | 🟡       | ✅ oui   |
| 22 | Doc / CLI       | `main.py` ne fait rien                                                | 🟡       | ✅ oui (vrai CLI `train` / `play`) |
| 23 | Repo            | `models/model_2.pth` versionné dans git                               | 🟡       | ✅ oui (`models/*.pth` gitignoré + `.gitattributes` prêt pour LFS + `scripts/bootstrap_model.py`) |
| 24 | DevEx           | Pas de CI ni de pré-commit                                            | 🟠       | ✅ oui (workflow GitHub Actions + ruff) |
| 25 | Doc             | README — chemin de clone (`github.com:` au lieu de `github.com-perso:`) | 🟢     | ✅ oui   |
| 26 | Doc             | Nom du projet incohérent (`Courtisants-Games` vs `courtisans-game`…)  | 🟢       | ✅ oui (uniformisation `courtisans_game`) |

Légende sévérité : 🔴 bug fonctionnel · 🟠 architecture · 🟡 qualité / hygiène · 🟢 cosmétique.

---

## Note : tous les axes sont adressés

Pour mémoire, les chantiers les plus structurants traités dans la dernière
itération :

- **#8 — PIMC** : `GameEnv.clone_determinized()` permute désormais les
  identités des cartes non vues du joueur courant, avec préservation de la
  contrainte « face cachée chez adversaire ⇒ rôle ESPION ».
- **#17 — Arena** : `arena()` confronte candidat et champion sur N parties à
  positions alternées ; `train()` promeut le candidat au statut de
  champion si winrate ≥ 55 %. Convention de fichiers : `models/model_{N}.pth`
  = best, `models/model_{N}_candidate.pth` = dernier candidat.
- **#18 — LayerNorm** : `BatchNorm1d` remplacé par `LayerNorm` partout dans
  `CourtisansNet`. Plus de dépendance aux statistiques de batch, identique en
  train/eval. L'ancien `model_2.pth` BatchNorm est incompatible — `load_model`
  détecte la mismatch de clés et logge une instruction de ré-entraînement.
- **#23 — Versionnage `.pth`** : `models/*.pth` est gitignoré (l'utilisateur
  peut forcer avec `git add -f`). `.gitattributes` est pré-configuré pour
  Git LFS (avec commande de migration en commentaire) si la taille devient un
  problème. `scripts/bootstrap_model.py` génère un modèle initial sans
  entraînement complet (utile pour démarrer Streamlit out-of-the-box).
