# Architecture technique — Courtisans AI

Ce document détaille l'architecture du projet et la logique d'implémentation
de l'IA. L'audit des limites connues et des axes d'amélioration vit dans
[`ameliorations.md`](ameliorations.md).

## Architecture globale

Séparation stricte des responsabilités :

| Couche       | Module(s)                       | Rôle |
|--------------|---------------------------------|------|
| Moteur       | `app/jeu.py`                    | Règles, état du plateau, aucune IA. |
| Cerveau IA   | `app/mcts_network.py`           | MCTS guidé par un ResNet (`CourtisansNet`). |
| Interface    | `streamlit_app/`                | App Streamlit (sous-modules `ui/`, `state.py`, `ai_runner.py`). |
| CLI          | `main.py`                       | Entrée argparse `train` / `play`. |
| Tests        | `tests/`                        | Pytest (mapper, moteur, assassins). |

---

## 1. Moteur de jeu (`app/jeu.py`)

### Concepts clés

- **État (`GameEnv`)** : plateau (cartes chez la Reine et chez chaque joueur),
  main du joueur courant (3 cartes), pioche restante. Initialisable avec un
  `seed` pour la reproductibilité.
- **Action atomique** : une "action" représente **le tour complet** d'un joueur
  (placer 3 cartes dans 3 zones).
  - 3 cartes en main → $3! = 6$ permutations.
  - 2 positions Reine possibles (`Estime` / `Disgrace`).
  - $N - 1$ cibles adverses possibles.
  - **Taille de l'espace d'action** : $6 \times 2 \times (N - 1)$.
    - 2 joueurs → 12 actions.

### `ActionMapper`

- `decode(idx) → (perm, queen_pos, target_rel)` : O(1).
- `encode(perm, queen_pos, target_rel) → idx` : O(1), bijection vérifiée par
  les tests.

### `GameEnv`

Points notables :

- `is_done()` : fin de partie si pioche vide **et** (toutes mains vides **ou**
  joueur courant incapable de former un tour complet).
- `_reveal_spies()` : les espions sont retournés face visible avant le calcul
  des scores → ils comptent bien dans le décompte final.
- **Multi-assassins par tour** :
  - Joueurs bots : tous les assassins sont auto-résolus séquentiellement
    (cible tirée aléatoirement parmi les cibles valides).
  - Joueur humain : la file `_pending_assassins_queue` est exposée via
    `pending_assassin_context` ; l'UI appelle `resolve_assassin_manual()`
    autant de fois que nécessaire.
- `get_state_vector()` : encodage **information imparfaite** — les cartes
  cachées d'un adversaire (espions retournés) ne figurent pas dans l'entrée
  du réseau.
- `clone_determinized(randomize=True)` : **déterminisation PIMC**. On
  `deepcopy` puis on permute les identités `(famille, role)` des cartes que
  le joueur courant ne peut pas voir (main adverse + espions cachés
  adverses + pioche). Contrainte préservée : un slot face cachée dans le
  domaine d'un adversaire ne reçoit qu'une identité ESPION.
  `randomize=False` permet un clone fidèle (utile pour les tests).

---

## 2. Intelligence artificielle (`app/mcts_network.py`)

### Réseau (`CourtisansNet`)

ResNet 5 blocs résiduels avec **LayerNorm** (et non BatchNorm — robuste au
batch=1 typique des évaluations MCTS), sortie double :

- **Policy** : vecteur de logits de taille `action_dim`.
- **Value** : scalaire dans `[-1, +1]` (`tanh`).

> Note : un checkpoint issu d'une ancienne version BatchNorm n'est plus
> chargeable. `load_model()` détecte la mismatch de clés et logge une
> instruction de ré-entraînement plutôt que de planter.

### MCTS

Recherche AlphaZero classique avec quatre points clés :

1. **Sélection** : score PUCT = $Q + c_{puct} \cdot P \cdot \frac{\sqrt{N_{parent}}}{1 + N_{child}}$.
2. **Expansion + évaluation** : le réseau fournit `(policy, value)`. **Les
   actions illégales sont masquées sur les logits (−∞) avant softmax** pour
   éviter de biaiser la normalisation.
3. **Backpropagation** : `value = -value` à chaque remontée — approximation
   zéro-sum (exacte à 2 joueurs, raisonnable à N joueurs).
4. **Bruit de Dirichlet** : injecté sur les priors de la racine en self-play
   (`add_root_noise=True`) pour garantir l'exploration. Paramètres : `α`,
   `ε` configurables dans `TrainConfig`.

### `TrainConfig`

Dataclass centralisant les hyper-paramètres :

```python
TrainConfig(
    num_players=2, iterations=100, num_sims=50, c_puct=1.5,
    lr=1e-3, weight_decay=1e-4,
    memory_size=50_000, batch_size=64,
    temperature_threshold=10,
    dirichlet_alpha=0.3, dirichlet_epsilon=0.25,
    num_worlds=1, family_augmentation=True,
    mcts_batch_size=1,  # bump to 8-16 (CPU) ou 32-64 (GPU) pour le batched eval
    checkpoint_every=25, model_dir="models", seed=None,
    arena_every=50, arena_games=20, arena_num_sims=30, arena_win_threshold=0.55,
)
```

Voir [`leviers_apprentissage.md`](leviers_apprentissage.md) pour la théorie
et les recommandations de tuning de chaque hyper-paramètre.

### Arena (champion vs candidat)

- `arena(challenger, champion, num_games, num_sims, num_players)` joue
  `num_games` parties à positions alternées (équilibrage de l'avantage du
  premier joueur), renvoie `{wins, losses, draws, winrate}`.
- Convention de fichiers :
  - `models/model_{N}.pth` → **best**, chargé par Streamlit / `play_vs_ai`.
  - `models/model_{N}_candidate.pth` → dernier candidat entraîné.
- Promotion : tous les `arena_every` épisodes, si `winrate ≥ arena_win_threshold`,
  le candidat remplace le best sur disque (et en mémoire).

### Boucle d'entraînement (`train`)

1. Self-play avec bruit Dirichlet à la racine, échantillonnage des actions
   pendant le warmup puis politique gloutonne + ε-aléa.
2. Reward final : pour chaque état rencontré, on attribue
   `(score_joueur − moyenne_autres) / 20` clippé à `[-1, +1]`.
3. Mini-batch SGD (Adam) : loss = cross-entropy(policy) + MSE(value).
4. Checkpoint intermédiaire tous les `checkpoint_every` épisodes
   → `models/model_{N}_ckpt_{iter}.pth`.
5. Évaluation arena tous les `arena_every` épisodes ; promotion candidat → best
   si winrate ≥ `arena_win_threshold`.
6. Sauvegarde finale : `models/model_{N}_candidate.pth` (dernier candidat) et
   `models/model_{N}.pth` (best — peut rester le best initial si aucune
   promotion n'a eu lieu).

### Chargement (`load_model`)

`torch.load(..., weights_only=True)` partout (best practice depuis Torch 2.4).
Échecs (fichier absent, état corrompu) loggés et retournent `None`.

---

## 3. Interface Streamlit

Voir [`streamlit_app_spec.md`](streamlit_app_spec.md) pour le détail des
modules et du flux d'interaction.

---

## 4. Tests

`tests/` contient 64 tests pytest :

- `test_action_mapper.py` : bijection `encode/decode`, espace d'action, erreurs.
- `test_game_engine.py` : invariants de `GameEnv` (deck, main triée,
  terminaison, révélation espions, reproductibilité par seed, clone
  indépendant).
- `test_assassin.py` : ciblage par zone Reine, par domaine, exclusions
  Garde / Assassin.
- `test_pimc.py` : déterminisation — préservation de l'inventaire global,
  de la main du joueur courant, des cartes visibles ; contrainte espion
  pour les slots face cachée adverses ; randomisation effective ; N joueurs.
- `test_arena.py` : statistiques `arena()` (wins/losses/draws/winrate),
  alternance des positions de départ, multi-mondes MCTS.
- `test_augmentation.py` : symétrie famille — permutation d'état, mapping
  des positions, conservation de la mass policy, **équivalence physique**
  de l'action préférée sous σ.
- `test_batched_mcts.py` : évaluateur MCTS batché — dispatch
  séquentiel/batché, distribution valide, compatibilité avec Dirichlet et
  PIMC multi, **annulation correcte de la virtual loss** (somme des
  visites racine = `num_sims` exactement).

CI : `.github/workflows/ci.yml` lance `ruff check .` puis `pytest` à chaque
push et PR sur `main`.
