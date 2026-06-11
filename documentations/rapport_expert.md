# Rapport complet — IA Courtisans
## Document destiné à une revue d'expert

**Projet :** Entraînement d'une IA style AlphaZero sur le jeu de cartes Courtisans  
**Période :** 26–28 mai 2026  
**Matériel :** AMD Ryzen 5 9600X · NVIDIA RTX 4060 Ti 16 Go · 65 Go RAM · WSL2 Ubuntu  
**Stack :** Python 3.12 · PyTorch 2.x · uv

---

## 0. Conclusion-chapeau — diagnostic de paradigme (mise à jour 01/06/2026)

> Cette section résume le verdict obtenu après ~1 semaine d'expériences (détails §1–26).
> Elle invalide la prémisse de départ ("entraîner une IA style AlphaZero") et fixe le cadre correct.

**Le problème n'était pas un réglage — c'était la famille d'algorithme, dès le départ.**
AlphaZero (MCTS + policy/value self-play) est conçu pour les jeux à **information parfaite**
(Go, échecs). Courtisans est un jeu à **information imparfaite** (main adverse, espions face
cachée). Ce mismatch explique *tous* les résultats négatifs :

- Le patch PIMC mono-monde souffre de **strategy fusion** (Cowling 2012) : il planifie comme
  s'il allait connaître les cartes cachées, et ne peut pas valoriser le fait de *cacher* de
  l'info — or les espions sont centraux. ISMCTS testé (§16.8 D5) : *pire* que mono-monde (t=−2.56).
- La **value scalaire d'un info-set est structurellement bruitée** (même info-set → outcomes
  différents selon les cartes cachées) → plafond r≈0.4, non cassable par le volume → MCTS empoisonné.
- **Toutes les variantes MCTS < policy brute.** La recherche *dégrade* sur ce jeu.

**Niveau réel mesuré (01/06) :** l'agent le plus fort du projet n'est aucun réseau — c'est un
**greedy à 1 coup qui maximise l'écart de score** (`moi − adversaire`). Il bat tous nos réseaux
~99 % (équitable PIMC comme info-privilégié). Le saut historique 0.396 → 0.00 vient de
l'objectif "écart", pas de la triche (§24–26).

**Le cadre correct (jeu à info imparfaite) :**
- **2 joueurs** : purement compétitif → on optimise l'**écart**, qui est *à somme nulle*. C'est
  exactement ce que fait le greedy corrigé. → Famille **CFR / Deep CFR / ReBeL** (lignée poker),
  convergence vers Nash, **exploitabilité mesurable** (la métrique absolue qui remplace le
  winrate-vs-greedy et tout le combat de bruit de mesure). **Ne pas re-marcher la voie
  ISMCTS→ExIt : empiriquement morte sur ce jeu.**
- **>2 joueurs** : somme non nulle, pas de Nash, alliances/kingmaking, non-transitivité →
  ligue / PSRO, métrique Elo vs pool. Fallback, pas l'objectif premier.

**Recommandation d'outillage :** réimplémenter Courtisans dans **OpenSpiel** (Deep CFR, ISMCTS,
PSRO, exploitabilité natifs). Compo de cartes : **uniforme, 3 exemplaires × 5 rôles × 6 familles**
(confirmé conforme au jeu visé). Scoring en duplicate (donnes appariées, rotation des sièges),
reward shaping dense (credit-assignment sur parties courtes), un seul changement à la fois.

**Acquis durables :** un moteur de jeu correct, une policy brute ~0.42 (vs ancien greedy) comme
baseline, un greedy-écart PIMC fort comme adversaire/benchmark, et un protocole de mesure mûr.

---

## 1. Le jeu : Courtisans

### Règles en bref

Jeu de cartes à **2 joueurs** (l'implémentation supporte N joueurs, mais tous les runs
d'entraînement ont été faits à 2). **90 cartes** : 6 familles × 5 rôles × 3 exemplaires.

**Rôles :**
| Rôle | Effet | Points |
|------|-------|--------|
| Assassin | Tue immédiatement une carte dans sa zone (hors Gardes) | 1 |
| Garde | Immunisé contre les Assassins | 1 |
| Noble | Aucun effet spécial | **2** |
| Espion | Posé **face cachée** (information cachée) | 1 |
| Neutre | Aucun effet spécial | 1 |

**Tour de jeu :** chaque joueur reçoit 3 cartes et les joue toutes les trois :
1. Une carte **chez la Reine** en Lumière (Estime) ou Obscurité (Disgrâce)
2. Une carte **dans son propre domaine**
3. Une carte **dans le domaine adverse**

**Fin de partie :** quand la pioche est épuisée et qu'aucun joueur n'a 3 cartes.

**Décompte :**
- Pour chaque famille : si plus de cartes en Estime qu'en Disgrâce → famille en **Lumière**,
  sinon **Obscurité**, sinon **Neutre**.
- Chaque carte dans un domaine rapporte `valeur` pts à son propriétaire si famille en Lumière,
  enlève `valeur` pts si en Obscurité, 0 si Neutre.
- Les Espions (face cachée) sont retournés avant décompte.

**Complexité :** ~46 coups par partie, ~12 actions légales par coup, information partielle
(cartes adverses inconnues, Espions cachés). Le placement chez la Reine crée des dépendances
à long terme entre familles.

---

## 2. Représentation de l'état et des actions

### Vecteur d'état : 158 dimensions (float32)

Le vecteur encode la vue subjective du joueur courant :
- Cartes sur le plateau (Reine, domaines) : position, famille, rôle visible/caché, propriétaire
- Main du joueur courant (les 3 cartes qu'il doit jouer)
- Informations agrégées sur les familles (combien en Lumière/Obscurité/Neutre)
- Score actuel de chaque joueur
- Contexte d'assassin en attente le cas échéant

Les cartes adverses inconnues (main + Espions face cachée) ne sont **pas incluses** — c'est
le problème d'information partielle que le PIMC doit gérer.

### Espace d'actions : 12 actions (coups principaux)

Chaque action encode le placement des 3 cartes de la main :
- Laquelle va chez la Reine (Lumière ou Obscurité)
- Laquelle va dans son domaine
- Laquelle va chez l'adversaire

(Les 3 cartes sont triées par `sort_key = famille × 5 + rôle` pour normaliser l'ordre.)

### Espace d'actions secondaire : 17 actions (ciblage assassin)

Quand un Assassin est joué, un second choix est requis : quelle carte tuer parmi les
cibles valides (max 16) + option "passer". Cette décision est traitée par une tête de
réseau séparée (`policy_head_target`).

---

## 3. Architecture du réseau de neurones

### CourtisansNet — ~3 millions de paramètres

```
Entrée : vecteur d'état (158 floats)
    ↓
fc_start : Linear(158 → 512) + LayerNorm + ReLU
    ↓
5 × ResidualBlock(512) :
    fc1 : Linear(512 → 512) + LayerNorm + ReLU
    fc2 : Linear(512 → 512) + LayerNorm
    + connexion résiduelle + ReLU
    ↓
    ├── policy_head_main   : Linear(512→256) + ReLU + Linear(256→12)   → 12 logits
    ├── policy_head_target : Linear(512→128) + ReLU + Linear(128→17)   → 17 logits
    └── value_head         : Linear(512→128) + ReLU + Linear(128→1) + Tanh → scalaire [-1,1]
```

**Choix LayerNorm vs BatchNorm :** BatchNorm instable avec batch=1 (fréquent en inférence
MCTS séquentielle). LayerNorm est identique en train et eval.

**Deux têtes de policy :** nécessaire car la décision d'assassinat est un sous-jeu
conditionnel avec un espace d'actions différent (cibles dynamiques).

---

## 4. Algorithme d'entraînement (style AlphaZero)

### 4.1 MCTS avec PIMC (Perfect Information Monte Carlo)

Le jeu a de l'information cachée (cartes adverses). On utilise PIMC : à chaque appel
`MCTS.search()`, on **déterminise** le monde en assignant aléatoirement les cartes
inconnues de l'adversaire parmi les cartes non vues, puis on lance MCTS sur ce monde
parfaitement informé.

Une simulation MCTS = un chemin racine → feuille :
1. **Sélection** : UCB (formule PUCT) depuis la racine jusqu'à un nœud non visité
2. **Évaluation** : forward pass du réseau → `(policy_logits, value)`
3. **Expansion** : ajout du nœud avec `P = softmax(policy_logits)` masqué sur actions légales
4. **Backpropagation** : mise à jour de `N(a)` et `Q(a) = moyenne des values remontées`,
   avec inversion de signe entre niveaux (ce qui est bon pour moi est mauvais pour l'adversaire)

**Formule PUCT :**
```
UCB(a) = Q(a) + c_puct × P(a) × √N_parent / (1 + N(a))
c_puct = 1.5
```

**Bruit Dirichlet à la racine** (exploration) :
```
P_noisy(a) = (1 - ε) × P(a) + ε × Dir(α)
ε = 0.25, α = 0.3
```

Après N simulations, la politique MCTS = distribution de visites normalisée :
`π(a) = N(a) / Σ N(a)`

### 4.2 Self-play et constitution du buffer

La boucle d'une partie (`_run_one_game`) :
1. Le **champion** (`best_net`) joue les deux rôles pour générer les données
   (pas le candidat en cours d'entraînement — garantit la qualité des données)
2. Pour chaque coup : MCTS avec N sims → distribution π → action selon température
3. **Température** : les `temperature_threshold=10` premiers coups → sampling selon π (exploration) ;
   ensuite → argmax(π) (exploitation)
4. Labels de valeur (discount temporel) :
   ```
   val_k = clamp((score_joueur - score_moyen_adversaires) / 20, -1, +1) × γ^(T-1-k)
   γ = 0.99
   ```
   Le dernier coup reçoit le poids plein (×1.0), le premier coup ~64% (γ^45 ≈ 0.64)

Chaque partie produit T échantillons `(état, π_MCTS, valeur_discountée)` ajoutés au
**replay buffer** (FIFO, capacité 100 000).

### 4.3 Boucle d'entraînement principale

```
POUR chaque itération :
    1. Sélectionner adversaire :
       - 75% : self-play pur (champion vs champion)
       - 25% : champion vs checkpoint passé aléatoire (anti-catastrophic-forgetting)

    2. Schedule progressif de simulations :
       - iter 0–99  : 100 sims
       - iter 100–249 : 200 sims
       - iter 250+  : 500 sims (= num_sims cible)

    3. Jouer une partie avec le champion → ajouter au buffer

    4. Si buffer > batch_size (64) :
       - Tirer un batch aléatoire de 64 samples
       - Augmentation par symétrie des familles (permutation aléatoire)
       - Forward pass candidat → (policy_main, policy_target, value)
       - loss_pi = cross_entropy(policy_pred, π_MCTS)   [séparé main + target]
       - loss_v  = MSE(value_pred, valeur_discountée)
       - loss    = loss_pi + loss_v
       - Backward + AdamW step
       - Scheduler LR cosine annealing (lr=1e-3 → lr_min=1e-5)

    5. Tous les 25 iters : sauvegarder checkpoint

    6. Tous les 100 iters : ARENA (1000 parties, 30 sims) candidat vs champion
       → si winrate ≥ 0.55 : candidat devient champion, sauvegarder model_2.pth

    7. Tous les 50 iters : BENCHMARK GREEDY (200 parties, 30 sims)
       candidat vs greedy bot
```

### 4.4 Arena

1000 parties, positions alternées (candidat commence 500 fois, champion 500 fois).
Les deux modèles utilisent MCTS avec **30 simulations**.

**Seuil de promotion : 0.55** (winrate hors draws).

Statistique : avec 1000 parties et p=0.55, IC95 = [0.52, 0.58] → fiable à ±3%.

**Note importante :** l'arena utilise 30 sims pour la rapidité (~33 min pour 1000 parties).
Les données d'entraînement sont générées avec 500 sims. Ce **mismatch sims** est une
hypothèse non résolue sur l'absence de promotions (cf. section 7).

### 4.5 Greedy bot

Pour chaque action légale : clone le plateau, joue l'action, et choisit l'action
maximisant l'**écart** de score immédiat (`score_courant − meilleur_score_adverse`).
**Stratégie myope à 1 coup** — ignore les menaces futures, les combos, la gestion des
familles à long terme, mais prend en compte l'effet du coup sur l'adversaire.

Objectif : servir de baseline externe absolue. Une IA fonctionnelle devrait le battre
à >80%.

> ⚠️ **Changement de baseline (31/05/2026).** Jusqu'au 31/05 inclus, le greedy maximisait
> son **score absolu** (`scores[cp]`), pas l'écart. Il ignorait donc totalement l'effet de
> ses coups sur l'adversaire — une faiblesse réelle. Depuis, il maximise l'écart (cf.
> `_score_margin` dans `app/greedy_bot.py`), ce qui en fait un adversaire **plus fort**.
> **Conséquence : tous les winrates greedy des sections 6 à 23 (0.12 random, 0.396 v8_250,
> etc.) ont été mesurés contre l'ANCIEN greedy et ne sont plus directement comparables aux
> mesures futures.** Re-mesurer v8_250 vs le nouveau greedy est la première action du plan post-23.

### 4.6 Warm-start du candidat

**Ajouté en v5c (28/05/2026)** — le candidat est initialisé depuis les poids du champion
(pas depuis un réseau aléatoire). Détail critique : pendant les runs v2–v4, le candidat
démarrait avec des poids aléatoires à chaque run, ce qui explique pourquoi il n'a jamais
atteint 0.55 d'avantage sur le champion en 300 itérations.

---

## 5. Paramètres de la configuration actuelle (v5c)

```python
TrainConfig(
    num_players=2,
    iterations=300,
    num_sims=500,           # sims MCTS self-play (schedule progressif)
    c_puct=1.5,
    lr=1e-3,
    lr_min=1e-5,            # cosine annealing
    weight_decay=1e-4,
    memory_size=100_000,
    batch_size=64,
    temperature_threshold=10,
    dirichlet_alpha=0.3,
    dirichlet_epsilon=0.25,
    num_worlds=1,           # PIMC : 1 seule déterminisation par search()
    family_augmentation=True,
    mcts_batch_size=1,      # séquentiel (batch=8 corrompt les données — cf. bugs)
    arena_games=1000,
    arena_every=100,
    arena_num_sims=30,      # sims en arena (différent des 500 sims self-play)
    arena_win_threshold=0.55,
    past_checkpoint_ratio=0.25,
    progressive_sims=True,
    greedy_benchmark_every=50,
    greedy_benchmark_games=200,
    value_discount=0.99,
    use_fp16=True,          # inférence float16 sur GPU (Tensor Cores)
    train_steps_per_iter=1,
)
```

---

## 6. Historique complet des runs d'entraînement

### Runs v1 (26 mai 2026) — configuration naive

**Problèmes de configuration v1 :**
- Arena sur **20 parties** → IC95 = ±22% → résultats statistiquement inutilisables
- **80 simulations MCTS** → labels bruités, plateau de loss à iter ~200
- Pas de baseline externe (pas de greedy bot)
- Pas d'anti-catastrophic-forgetting

**train_5000.log (~1000 iters, 80 sims, arena 20 parties) :**
```
iter 100  : Arena 0.84 → PROMU  (sur 20 parties : bruit pur)
iter 150  : Arena 0.26 → conservé
iter 200  : Arena 0.20 → conservé
iter 450  : Arena 0.65 → PROMU
iter 650  : Arena 0.61 → PROMU
iter 700  : Arena 0.61 → PROMU
iter 750  : Arena 0.69 → PROMU
iter 800  : Arena 0.90 → PROMU  ← pic aberrant, 20 parties
iter 900  : Arena 0.61 → PROMU
```

**train_final.log (1500 iters, 80 sims, arena 20 parties) :**
```
iter  50  : Arena 0.56 → PROMU
iter 100  : Arena 0.67 → PROMU
iter 150  : Arena 0.67 → PROMU
iter 200–800 : stagnation (0.20–0.45, conservé)
iter 850  : Arena 0.58 → PROMU
iter 900  : Arena 0.65 → PROMU
iter 950  : Arena 0.56 → PROMU
iter 1150 : Arena 0.58 → PROMU
iter 1250 : Arena 0.74 → PROMU
iter 1400 : Arena 0.67 → PROMU  ← dernière promotion, model_2.pth actuel
iter 1500 : Arena 0.53 → conservé (fin de run)
Loss finale : ~3.1
```

**Conclusion v1 :** les promotions sont du bruit statistique (20 parties = ±22%).
Le model_2.pth actuel correspond à la dernière promotion (iter ~1400 de train_final.log).
Il a été entraîné avec 80 sims, sans warm-start, sans anti-forgetting.

---

### Runs v2–v4 (27–28 mai 2026) — améliorations v2 sans warm-start

**Configuration commune v2–v4 :**
- 300 itérations, 500 sims (schedule progressif), arena 1000 parties
- 25% parties contre checkpoint passé (anti-forgetting)
- Greedy benchmark tous les 50 iters
- **BUG : candidat initialisé avec poids aléatoires** (warm-start manquant)
- **BUG : greedy benchmark mesurait `best_net` (champion figé), pas le candidat**

```
Run | Arena@100 | Arena@200 | Arena@300 | Promotions | Greedy@fin | Loss@fin
v2  |   0.45    |   0.33    |   0.49    |     0      |   0.18     |  ~2.63
v3  |   0.48    |   0.51    |   0.48    |     0      |   0.20     |  ~2.69
v4  |   0.46    |   0.40    |   0.45    |     0      |   0.18     |  ~2.67
```

**Interprétation :** le candidat atteint 0.44–0.51 sans jamais dépasser 0.55.
Avec des poids aléatoires au départ, le candidat doit réapprendre toute la politique du
champion EN 300 itérations ET le dépasser de 55%. C'est mécaniquement très difficile.

---

### Run v5 (28 mai 2026) — tentative avec trop de changements simultanés

**Changements introduits simultanément :** warm-start + K=3 steps + mcts-batch-size=8
+ LR cosine + greedy sur candidat. **Violation de la règle : 1 changement à la fois.**

```
Arena@100 = 0.24  → ARRÊTÉ
Greedy@50 = 0.05  (candidat complètement dégradé)
```

**Diagnostic :** K=3 gradient steps par itération sur un buffer de ~2300 samples
(50 parties × 46 coups) = sur-entraînement massif, oubli catastrophique.

---

### Run v5b (28 mai 2026) — K=1 mais mcts-batch-size=8

```
Arena@100 = 0.16  → ARRÊTÉ
Greedy@50 = 0.05
Loss iter 10 = 3.71
```

**Diagnostic :** loss initiale 3.71 (similaire à random init !) alors que warm-start
devrait donner ~2.86. `--mcts-batch-size 8` **corrompt les données d'entraînement** :
la virtual loss dans le MCTS batché dégrade la qualité de la politique générée.

---

### Run v5c (28 mai 2026) — warm-start seul, batch-size=1

**Seul changement vs v2–v4 :** warm-start depuis le champion.

```
Arena@100 = 0.44    | Greedy@50 = 0.17 (candidat)
Arena@200 = 0.47    | Greedy@100 = 0.17
                    | Greedy@150 = 0.19
                    | Greedy@200 = 0.16
Loss iter 10 = 2.86 (vs 3.7 sans warm-start — warm-start fonctionne)
Loss iter 250 = 2.50
LR à iter 250 : 7.63e-05 (annealing presque terminé)
→ ARRÊTÉ à iter 255 (0 promotions confirmées, analyse demandée)
```

**Observation clé :** le warm-start améliore le départ (loss 2.86 vs 3.7), mais
n'améliore pas le résultat arena par rapport aux runs sans warm-start (0.44–0.47 vs 0.45–0.51).

---

## 7. Bugs critiques identifiés et corrigés

### Bug #1 — Candidat initialisé avec poids aléatoires (CRITIQUE)

**Présent dans :** v1, v2, v3, v4  
**Symptôme :** 0 promotions sur 900 itérations cumulées (v2+v3+v4)  
**Cause :** ligne 851 `net = CourtisansNet(...)` crée un réseau aléatoire.
Le champion (`best_net`) est chargé juste après mais les deux ne sont jamais connectés.  
**Fix :**
```python
# Après chargement de best_net :
net.load_state_dict({k: v.clone() for k, v in best_net.state_dict().items()})
```

### Bug #2 — Greedy benchmark sur le mauvais modèle (TROMPEUR)

**Présent dans :** v2, v3, v4  
**Symptôme :** greedy winrate stable à 0.17–0.25 sans progression → semblait stagnant  
**Cause :** `benchmark_vs_greedy(best_net, ...)` → mesure le champion figé, pas le candidat  
**Fix :** `benchmark_vs_greedy(net, ...)` → mesure le candidat en cours d'entraînement

### Bug #3 — mcts-batch-size=8 corrompt les données

**Présent dans :** v5, v5b  
**Symptôme :** loss initiale 3.71 avec warm-start (devrait être ~2.86), arena@100=0.16–0.24  
**Cause supposée :** la virtual loss dans le MCTS batché (implémentée pour diverger les
descentes parallèles) dégrade la qualité des distributions de visites quand batch_size > 1
sur ce jeu. Résultat : données d'entraînement corrompues, gradient nocif.  
**Fix :** revenir à `mcts-batch-size=1` (séquentiel)  
**Note :** la cause exacte du problème de batch>1 n'est pas encore diagnostiquée précisément.

### Bug #4 — K=3 steps avec petit buffer = sur-entraînement

**Présent dans :** v5  
**Symptôme :** greedy@50=0.05 (candidat oublie tout le savoir du champion en 50 iters)  
**Cause :** 50 parties × 46 samples = 2300 samples dans le buffer. K=3 steps × 50 iters
= 150 gradient updates sur un buffer quasi-vide = sur-apprentissage total + oubli catastrophique.  
**Fix :** K=1 par défaut ; K>1 uniquement après que le buffer soit suffisamment rempli.

---

## 8. Hypothèses non résolues pour l'expert

### H1 — Mismatch sims entraînement (500) vs arena (30) [PRIORITAIRE]

Le candidat est entraîné sur des données générées avec 500 sims MCTS. Ses poids apprennent
à approximer une politique 500-sims. L'arena évalue avec 30 sims. À 30 sims, l'avantage
d'un réseau "calibré pour 500 sims" vs un réseau "calibré pour 80 sims" (le champion v1)
pourrait être insuffisant pour créer 55% d'avantage.

**Test proposé :** augmenter `arena_num_sims` de 30 à 100 ou 200, quitte à réduire
`arena_games` à 400 (±5% CI reste acceptable). Si les promotions apparaissent → confirme H1.

### H2 — Value head ne converge pas

La value loss (`loss_v`) reste constamment à **0.04–0.11** sur tous les runs, alors que
la policy loss descend de 3.7 → 2.5. Le réseau apprend à approximer la politique MCTS
mais n'apprend pratiquement pas à estimer la valeur des positions.

Causes possibles :
- Les parties de self-play à 2 joueurs équilibrés produisent des scores proches de 0
  (jeu de somme nulle) → toutes les valeurs cibles sont petites → MSE proche de 0
  même en prédisant toujours 0
- Le discount γ=0.99 atténue les signaux de début de partie : premier coup à 64%
  → signal très petit sur les positions précoces

**Conséquence :** le MCTS utilise les `value` prédites pour remonter l'information à
chaque backpropagation. Si `value ≈ 0` toujours, les simulations MCTS explorent presque
au hasard et la qualité des labels de politique est limitée à ce que le prior (la policy)
guide.

**Test proposé :** vérifier la distribution des valeurs cibles (histogramme des `val`)
et celle des prédictions. Vérifier si `v_pred ≈ 0` partout.

### H3 — Champion trop vieux / entraîné sur une distribution différente

Le champion actuel (`model_2.pth`) est le résultat de la v1 : entraîné avec 80 sims,
arena 20 parties (bruit pur), sans architecture LayerNorm (incompatibilité corrigée au
chargement). Il représente un modèle potentiellement mal entraîné qui sert de baseline
"figée" depuis ~1500 itérations de v1.

**Conséquence :** warm-starting depuis ce champion donne un point de départ qui n'est
peut-être pas dans un bon "bassin" pour un entraînement 500-sims. Les gradients 500-sims
tirent dans une direction orthogonale aux poids v1.

**Test proposé :** supprimer `model_2.pth` et repartir de zéro. Le premier candidat
deviendra automatiquement champion (aucune baseline figée), et les runs suivants
progresseront à partir d'une base cohérente avec la configuration actuelle.

### H4 — 300 itérations insuffisantes pour créer un avantage décisif

Avec warm-start + 300 iters, le candidat stagne à 0.44–0.47 de winrate. Si la "vraie"
valeur du candidat est 0.52 (mieux que le champion mais sous le seuil), 300 iterations
ne sont pas assez pour créer un avantage détectable même avec 1000 parties d'arena.

**Test proposé :** lancer 1000 itérations avec warm-start. Observer si le winrate
continue de croître ou plafonne.

### H5 — Problème de l'information partielle (PIMC single)

Le PIMC actuel utilise **une seule déterminisation** par appel `search()`. La théorie
(Cowling et al. 2012) montre que PIMC single souffre du "strategy fusion problem" :
il ne peut pas apprendre à exploiter l'asymétrie d'information (ex : poser un espion
pour cacher une information stratégique). Les Espions sont centraux dans Courtisans.

**Test proposé :** activer `--num-worlds 3` (PIMC multi-déterminisation) — **mais avec
mcts-batch-size=1 car le batch>1 est problématique** — et observer si la qualité des
parties self-play s'améliore qualitativement.

---

## 9. Métriques observées et objectifs

| Métrique | Meilleur observé | Objectif "IA fonctionnelle" |
|----------|-----------------|------------------------------|
| Arena winrate (1000 parties, 30 sims) | 0.51 (v3, iter 200) | ≥ 0.55 (promotion) |
| Greedy winrate (champion) | 0.25 (v3, iter 250) | > 0.80 |
| Greedy winrate (candidat) | 0.19 (v5c, iter 150) | > 0.80 |
| Loss finale | 2.50 (v5c, iter 240) | < 2.0 (hypothétique) |
| Value loss | ~0.05 (tous runs) | devrait être > 0.1 pour apprendre |
| Promotions arena (1000 parties) | 0 (v2–v5c) | régulières (1 sur 3 arenas) |

---

## 10. Architecture décisionnelle — ce qui a été décidé et pourquoi

### Choix confirmés par l'expérience

| Décision | Justification |
|----------|---------------|
| Arena 1000 parties (vs 20 en v1) | IC95 ±3% vs ±22% |
| 500 sims (vs 80 en v1) | Sortir du plateau de loss précoce |
| 25% parties vs checkpoints passés | Anti-catastrophic-forgetting (arXiv:2604.05476) |
| Seuil arena 0.55 | Statistiquement justifié, ne pas abaisser |
| batch-size=1 pour MCTS | batch>1 corrompt les données (bug non diagnostiqué précisément) |
| K=1 gradient step par iter | K=3 cause sur-entraînement sur petit buffer |

### Choix non testés / hypothèses ouvertes

| Levier | Statut | Risque |
|--------|--------|--------|
| `arena_num_sims=100` (vs 30) | Non testé | Arena 3× plus lente (~1h30) |
| `num_worlds=3` (PIMC multi) | Non testé | Coût 3× en self-play |
| Repartir sans champion (reset) | Non testé | Perd la baseline v1 |
| 1000+ itérations | Non testé | ~15h de compute |
| Value head redesign | Non testé | Risque d'instabilité |

---

## 11. Questions directes pour l'expert

1. **L'absence de promotions sur 900 itérations (v2–v4, sans warm-start) est-elle normale ?**
   Est-ce que le problème warm-start suffit à l'expliquer, ou y a-t-il autre chose ?

2. **La value loss à ~0.05 constante est-elle un signal d'alarme ?** Y a-t-il une façon
   de vérifier si le value head apprend quelque chose d'utile ?

3. **Le mismatch arena_sims=30 vs train_sims=500 est-il un problème réel ?** Dans
   les implementations AlphaZero standard, les sims d'arena sont-ils proches de ceux
   d'entraînement ?

4. **Pour un jeu avec autant d'information partielle (Espions), le PIMC single est-il
   raisonnable ?** Faut-il passer à IS-MCTS (Information Set MCTS) ?

5. **Avec 12 actions légales et ~46 coups par partie, combien d'itérations réalistes
   faut-il pour voir une IA "jouer bien" sur un jeu de cette complexité ?**

6. **Le champion v1 (80 sims, 20-game arena) comme baseline figée est-il un problème
   fondamental ?** Faut-il repartir de zéro ?

---

## 12. Retour d'expert — Diagnostic et plan d'action (28/05/2026)

*Retranscription du diagnostic reçu après soumission de ce document. Suivi de nos réponses
aux 4 questions techniques de l'expert, qui ont permis de verrouiller le diagnostic.*

---

### 12.1 Recadrage principal

> « Le chiffre le plus important de tout ton rapport n'est pas "0 promotions". C'est celui-ci :
> Greedy winrate (champion et candidat) ≈ **0.17–0.25**, objectif > 0.80.
> Ton IA, champion *comme* candidat, **perd 75 à 80 % de ses parties contre un bot myope à
> 1 coup**. Ce n'est pas "une IA légèrement sous le seuil de promotion". C'est une IA qui ne
> joue pas mieux qu'un réflexe glouton. »

**Conséquence directe :** l'arène compare deux réseaux au niveau "bruit". Ils ont tous les
deux ~0.50 de winrate l'un contre l'autre → jamais de promotion, pas parce que le seuil est
trop haut, mais parce que **rien d'utile n'est appris**. Arrêter d'optimiser la machinerie
d'arène tant que cette cause racine n'est pas résolue.

---

### 12.2 Cause racine n°1 — Value head mathématiquement morte

**Mécanisme AlphaZero :** le MCTS ne s'améliore que parce que la value aux feuilles
distingue les bonnes des mauvaises positions. Si `value ≈ 0` partout, les backups remontent
≈ 0 → la recherche se réduit à du PUCT piloté par le prior de politique → **l'opérateur
d'amélioration de politique est cassé** → boucle circulaire sans ancre.

**Pourquoi la value est-elle morte (preuve mathématique) ?**

La cible implémentée :
```python
val_k = clamp((score - avg_opponent) / 20, -1, +1) × γ^(T-1-k)
```

Le terme `γ^(T-1-k)` dépend de `T` (longueur totale de partie) et de `k` (indice du coup).
**Ni T ni k ne sont encodés dans le vecteur d'état (158 dimensions).** Deux positions
quasi identiques issues de parties de longueurs différentes reçoivent des cibles différentes
que le réseau ne peut pas distinguer. Il converge vers la moyenne ≈ 0.

*Vérification dans le code (questions de l'expert, réponse Q4) :*
- `get_state_vector()` encode counts de cartes + compteurs d'espions cachés.
- Zero indicateur de : numéro de coup `k`, longueur totale `T`, cartes restantes en pioche.
- La cible discount est donc **non apprenable par construction**.

**Confirmation via Q1 (composition de la loss) :**

```python
loss_pi_main   = -sum(targets × log_softmax(logits)) / len(main_idx)  # CE mean
loss_pi_target = -sum(targets × log_softmax(logits)) / len(target_idx) # CE mean
loss_pi = loss_pi_main + loss_pi_target   # somme des deux normalized
loss_v  = F.mse_loss(v_pred, values_tensor)  # MSE, λ = 1 (aucune pondération)
loss    = loss_pi + loss_v
```

Avec `loss_pi ≈ 2.50` et `loss_pi ≈ ln(12) = 2.485` (politique **uniforme**), la policy head
apprend à peine au-delà du masquage des coups illégaux. Elle est quasi uniforme.

**Note critique (correction de notre Q1 initial) :** la petitesse de `loss_v ≈ 0.05` n'est
pas due à un gradient trop faible, c'est le résultat *naturel* d'une cible quasi constante
(≈ 0). La MSE d'un prédicteur-moyenne sur des cibles plates est mécaniquement petite.
Augmenter `λ_value` amplifierait un gradient qui pointe vers « prédis 0 plus vite » — cela
n'aide pas. **Ne pas toucher à λ_value avant d'avoir corrigé la cible.**

---

### 12.3 Cause racine n°2 — Budget de parties ~100× trop faible

- 300 itérations × 1 partie/iter = **300 parties** ≈ 14 000 samples
- Buffer capacité 100 000 : ne se remplit jamais
- 300 pas de gradient au total

Ordre de grandeur nécessaire : **10 000–100 000 parties** pour un jeu de cette complexité
(information partielle, ~46 coups, dépendances à long terme). Le runs v1 (1000–1500 parties)
montraient quelques promotions (bruitées) car le volume était ~5× plus grand.

---

### 12.4 Cause racine n°3 — Deadlock du gating

Le champion génère toutes les données. S'il est mauvais (perd contre greedy), le candidat
apprend à imiter le MCTS d'un mauvais joueur. Le candidat ne peut pas être promu sans de
meilleures données, et il ne peut pas générer de meilleures données sans être promu.
**Œuf et poule.**

Le champion actuel (`model_2.pth`) est la dernière promotion d'une arène à 20 parties
(IC95 ±22%) : un réseau promu par bruit statistique, figé depuis ~1500 itérations de v1,
entraîné avec 80 sims sans warm-start. Il fige toute la distribution de données depuis
le début des runs v2–v5.

*AlphaZero (version post-AlphaGo Zero) a supprimé le gating précisément pour cette raison :
le réseau le plus récent s'auto-joue et s'entraîne en continu, sans gate binaire.*

---

### 12.5 Diagnostic du Bug #3 (virtual loss, cause exacte)

> « La cause la plus probable est la **virtual loss mal réinitialisée**. En MCTS batché,
> on ajoute une virtual loss sur les chemins en vol pour forcer les threads à diverger,
> *puis on la retire* au moment du backup réel. Bug classique : la virtual loss n'est
> pas retirée après backup (ou pas dans le bon signe entre niveaux), ce qui laisse des
> `N(a)` gonflés et des `Q(a)` déprimés artificiellement. »

Dans notre implémentation (phase 3 de `_search_single_world_batched`) :
```python
for n in p["path"][1:]:
    n.visit_count -= self.VIRTUAL_LOSS
    n.value_sum += self.VIRTUAL_LOSS
```

La virtual loss est retirée en soustrayant du `visit_count` et ajoutant au `value_sum` —
ce qui inverse le signe par rapport à ce qui avait été ajouté (`visit_count += VL`,
`value_sum -= VL`). L'annulation semble mathématiquement correcte sur le papier, mais des
effets de bord lors des descentes concurrentes (interactions entre batchs successifs sur
le même arbre) restent possibles. Garder `batch_size=1` jusqu'à diagnostic complet.

---

### 12.6 Réponses aux 4 questions de l'expert

**Q1 — Composition de la loss :**
Voir section 12.2. Résumé : `loss = loss_pi + loss_v`, λ=1, value gradient ~50× plus faible
en magnitude absolue mais pas en raison d'une pondération inadéquate — en raison d'une
cible plate. Le vrai problème est la cible, pas λ.

**Q2 — Perspective de la cible de valeur :**
Correcte. `player_id` = joueur courant à chaque step k. Le state vector encode déjà l'état
depuis la perspective du joueur courant (domaines relatifs via `(domaine_id - current_player) % N`).
Les deux sont cohérents. Pas de bug de signe.

**Q3 — PIMC : re-déterminisation par search() ou par simulation ?**
Une seule fois par `search()` (= par coup). Toutes les simulations d'un même appel partagent
le même monde (`randomize=False` dans les boucles de simulation). L'échantillonnage des
cartes cachées est **uniforme** (pas de croyance bayésienne).

**Q4 — Progression de partie encodée dans les 158 dimensions ?**
**Non.** Zéro indicateur de numéro de coup k, longueur totale T, cartes restantes en pioche.
Preuve mathématique directe du problème : `γ^(T-1-k)` est non apprenable depuis le state.

---

### 12.7 Réponses aux 6 questions initiales (verdict expert)

1. **Absence de promotions sur 900 iters — normale ?** Oui, mécaniquement attendue : deux
   réseaux incapables de battre greedy s'affrontent à ~0.50. Le warm-start manquant est
   une partie du problème ; les causes profondes sont value morte + budget minuscule +
   deadlock de gating.

2. **Value loss ~0.05 — alarme ?** Oui, alarme rouge. Cause : discount rend la cible
   non apprenable. Test de validation : corrélation `v_pred` ↔ `v_target` (objectif R² > 0,
   actuellement ≈ 0). Après fix, `loss_v` devrait sauter à ~1.0 puis redescendre.

3. **Mismatch arena 30 vs train 500 — réel ?** Oui, mais amplificateur de symptôme, pas
   maladie. Avec une value fonctionnelle, l'IA battrait greedy à 30 sims comme à 500.
   AlphaZero a supprimé le gate binaire — à terme adopter un Elo glissant.

4. **PIMC single pour jeu à espions ?** Non, insuffisant à terme (strategy fusion problem,
   Cowling et al. 2012). Mais ce n'est pas ce qui fait perdre contre greedy. À traiter
   après causes 1–3. Fix minimal : re-déterminiser par simulation (pas une fois par coup).

5. **Combien d'itérations réalistes ?** Pas en itérations : en **parties**. Ordre de grandeur
   10⁴–10⁵ parties de self-play avec un signal de valeur sain. 300 parties = hors de portée.

6. **Champion v1 comme baseline — problème ?** Double problème : promu par bruit (20 parties)
   ET fige la distribution de données. À supprimer après correction de la value.

---

### 12.8 Plan d'action (par ordre de priorité)

#### Étape 1 — Corriger la cible de valeur (priorité absolue)

**Fix : outcome-based z, sans discount, perspective du joueur au trait.**

```python
# Avant (lignes 826-831 de mcts_network.py) :
val = max(-1.0, min(1.0, (my_score - sum(others) / len(others)) / 20.0))
val = val * (gamma ** (T - 1 - k))

# Après :
margin = my_score - sum(others) / len(others)
val = 1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)
# (plus de discount)
```

Garder `z=0` pour les nuls exacts (la position était réellement neutre). Surveiller si les
nuls sont très fréquents (ce qui re-diluerait la variance).

**À faire en même temps (même commit conceptuel) : reset du champion.**
Supprimer `model_2.pth` avant de lancer → le premier candidat devient champion sans avoir
à franchir le gate, génère immédiatement des données avec la value corrigée, et le deadlock
est brisé.

**Ce que ces deux changements règlent ensemble :**
- Fix cible seul sans reset : la value head se réveille, mais les labels de politique
  (`π_MCTS`) continuent à venir d'un champion à policy quasi uniforme → policy stagne.
- Reset seul sans fix cible : champion reparti de zéro, mais value toujours morte →
  pas de signal utile, boucle toujours cassée.
- Ensemble : signal de valeur sain + données fraîches générées par le réseau qui s'améliore.

#### Étape 2 — Instrumenter pour confirmer l'apprentissage

Ajouter au log (avant de lancer quoi que ce soit de long) :
- Corrélation `v_pred` ↔ `v_target` (viser R² > 0.1 pour confirmer)
- Entropie moyenne de la policy vs `ln(12) = 2.485` (viser entropie qui descend)
- Histogramme des valeurs cibles (vérifier répartition ±1 équilibrée, pas tous à 0)

#### Étape 3 — Augmenter le débit (après confirmation étape 1+2)

Passer à 4–8 parties parallèles (`--parallel-games 8`) pour atteindre 10 000+ parties.
La parallélisation ne change pas CE qui est appris, seulement COMBIEN — donc après validation.

#### Étape 4 — Pour plus tard (ne pas mêler aux étapes 1-3)

- Ajouter progression de partie au state vector (cartes restantes en pioche / numéro de coup)
  → aide intrinsèquement la value même avec le fix, mais changement orthogonal
- Self-play continu (AlphaZero style vs AlphaGo Zero style) : supprimer le gate binaire,
  Elo glissant comme thermomètre
- PIMC multi-monde (`--num-worlds 3`) une fois la boucle débloquée

---

### 12.9 Critères de succès pour valider l'apprentissage

| Métrique | Valeur actuelle | Attendu après fix 1+2 | Signal d'alerte |
|----------|----------------|----------------------|-----------------|
| `loss_v` | ~0.05 | **Saute à ~1.0, puis descend 0.5–0.8** | Reste à 1.0 → value ne capte toujours rien |
| `loss_pi` | ~2.50 ≈ ln(12) | **Passe sous 2.48 → 1.5–2.0** | Reste ≥ 2.48 → policy uniforme |
| Corrélation v_pred/v_target | ≈ 0 | **Devient positive (R² > 0.1)** | Reste ≈ 0 → revoir cible |
| Greedy winrate | 0.17–0.25 | **Dépasse 0.30 puis 0.50** | Stagne à 0.17 → voir correction n°2 |

**Note :** si la `loss_v` monte mais que le greedy winrate stagne avec le champion
reset, c'est exactement la correction n°2 qui se manifeste (policy toujours dégradée par
données du champion figé). Dans ce cas, passer au self-play continu (étape 4).

---

## 13. Runs de validation post-fix (28/05/2026 après-midi)

### 13.1 Run v6 — Reset champion + fix value (18h00–20h00)

**Configuration :** fix value target (z=sign(margin), sans discount) + reset complet du
champion (model_2.pth supprimé → réseau aléatoire comme baseline).

```
Iter 10  | loss_v=1.94  v_corr=-0.12  pi_ent=2.443
Iter 20  | loss_v=2.12  v_corr=+0.21  pi_ent=2.441
Iter 50  | Greedy@50 = 0.01 (1/200)
Iter 60  | loss_v=0.92  v_corr=+0.37  pi_ent=2.467
Iter 80  | loss_v=0.83  v_corr=+0.39  pi_ent=2.474
Arena@100 = 0.31 (candidat pire que le réseau random initial)
Greedy@100 = 0.08
Greedy@150 = 0.10
→ ARRÊTÉ à iter 170
```

**Diagnostic :**
- Fix value confirmé : `loss_v` passe de 0.05 → 2.0, `v_corr` atteint +0.39. La value head est vivante.
- Mais `pi_ent` reste à 2.44–2.47 (quasi-uniforme, inchangé vs avant le fix).
- Arena@100=0.31 : le candidat est **pire** que le réseau random initial après 100 iters.
- Cause : champion = réseau aléatoire → self-play génère des distributions MCTS quasi-uniformes
  → la policy apprend "jouer aléatoire" → deadlock. La value apprend mais la policy n'a aucun
  signal utile. **Le reset total était trop radical.**

### 13.2 Run v7 — Fix value + warm-start model_2 (18h00–20h30)

**Configuration :** fix value target + restauration de model_2.pth comme champion
(warm-start depuis le champion v1, greedy=0.17).

```
Iter 10  | loss_v=1.05  v_corr=+0.23  pi_ent=2.280  ← pi_ent chute immédiatement !
Iter 20  | loss_v=0.94  v_corr=+0.33  pi_ent=2.248
Iter 50  | Greedy@50 = 0.14
Iter 90  | loss_v=0.85  v_corr=+0.27  pi_ent=2.229  ← plus bas de l'entropie
Arena@100 = 0.48
Greedy@100 = 0.06  ← régresse depuis 0.14
Arena@200 = 0.44
Greedy@200 = 0.08
```

**Diagnostic :**

**Signaux positifs (fixes fonctionnent) :**
- `loss_v` : 1.05 → 0.79 sur 200 iters (vs 0.05 avant le fix). Value head vivante et apprenante.
- `v_corr` : stable 0.15–0.42, positif tout au long du run. Corrélation réelle entre prédiction
  et outcome.
- `pi_ent` : **chute de 2.485 (uniforme) à 2.23–2.33**. La policy se spécialise grâce au
  warm-start + value fonctionnelle. Delta significatif vs v6 (2.44–2.47).
- Arena@100=0.48 : légère amélioration vs v5c (0.44).

**Signaux négatifs :**
- Greedy winrate **régresse** : 0.17 (warm-start) → 0.14 → 0.06 → 0.08.
- Arena@200=0.44 : rechute après Arena@100=0.48.
- Le candidat apprend à exploiter les patterns du champion v1 (arena proche de 0.55) mais
  ne généralise pas à de nouveaux adversaires (greedy).

**Cause identifiée — mode collapse sur le champion figé :**

La policy apprend à battre les spécificités du champion v1 (ses patterns en auto-play)
plutôt qu'à jouer "bien" en général. C'est la pathologie classique du self-play avec
un seul adversaire figé et trop peu de données. La policy devient meilleure en auto-play
(arena ↑) mais pire contre out-of-distribution opponents (greedy ↓).

**Ce qui n'a pas encore été résolu :** le volume de données. v7 = 200 parties.
Seuil estimé par l'expert : 10 000–100 000 parties. On est encore **50× en dessous**.

---

## 15. Diagnostics empiriques post-expert (29/05/2026)

### 15.1 Batterie de diagnostics rapides

**Contexte :** avant tout run long, l'expert a prescrit une batterie de tests discriminants.
Tous exécutés sur le candidat v7 (`models/model_2_candidate.pth`, 200 iters, value fix, augmentation active).

#### Baselines (200 parties chacune)

| Test | Winrate | Interprétation |
|------|---------|----------------|
| Random vs Greedy | ~0.12 | Greedy fort (évalue score post-placement Reine incluse) |
| Random vs Champion (30 sims) | ~0.28 | Champion gagne 72% vs random — il a appris quelque chose |

**Scénario confirmé : R (0.12) ≪ A (0.36).** L'IA est dans le scénario "greedy fort" — pas "AI anti-apprend".

#### Policy seule — 0 simulation (100-200 parties)

| Test | Winrate |
|------|---------|
| Champion (0 sim) vs Random | **0.72** |
| Champion (0 sim) vs Greedy | **0.365** |
| Candidat v7 (0 sim) vs Random | **0.73** |
| Candidat v7 (0 sim) vs Greedy | **0.34–0.37** |

**Le réseau a appris une bonne politique** (3.6× mieux que random contre greedy). Tous les benchmarks
greedy historiques (0.06–0.17) étaient biaisés vers le bas car mesurés avec MCTS.

#### Budget de simulations — candidat v7 vs greedy (60–100 parties)

| Sims | Winrate | vs policy-brute (0.365) |
|------|---------|------------------------|
| 0 (policy brute) | **0.365** | référence |
| 30 sims | 0.06–0.09 | **÷ 5** |
| 100 sims | 0.07–0.16 | **÷ 4** |
| 200 sims | 0.04–0.07 | **÷ 7** |
| 500 sims | 0.06–0.07 | **÷ 5** |

**Le MCTS détruit la performance** : 0.365 → 0.03–0.09. Plus de sims ne récupère pas.
*Note : ces chiffres incluent un artefact de mesure corrigé dans §15.5.*

### 15.2 Test keystone v1 — value=0 sur feuilles non-terminales (2 runs × 60–100 parties)

**Objectif :** discriminer "value head est le poison" vs "bug dans le backup/mécanique MCTS".

**Implémentation (v1) :** `MCTSZeroValue` override `_expand` pour retourner 0.0,
mais **`_terminal_value` n'est pas overridé** → les simulations qui atteignent un état terminal
backpropagent de vraies valeurs ±score/20 (via PIMC).

| Test | Run 1 | Run 2 | Moyenne |
|------|-------|-------|---------|
| 100 sims, value **normale** vs greedy | 0.160 | 0.155 | ~0.16 |
| 100 sims, value=**0 forcée (v1)** vs greedy | 0.115 | 0.182 | ~0.15 |
| 30 sims, value=**0 forcée (v1)** vs greedy | 0.260 | 0.237 | **~0.25** |
| 0 sim (policy brute) vs greedy | — | — | **0.365** |

**Conclusion partielle :** value=0 à 30 sims (0.25) se rapproche de la policy-brute (0.365)
→ la value est bien un facteur majeur à faible sim-count.

**Pattern anti-monotone observé :** 0.260 à 30 sims → 0.115 à 100 sims.
*Explication initiale incorrecte : "PUCT distribue les visites uniformément avec Q=0" — voir correction §15.5.*

### 15.3 Test unitaire augment_sample

4 tests, 500+ états réels : **augment_sample est mathématiquement correct** (round-trip,
identité, bijectivité position_map, cohérence state↔action). Ce n'est pas un bug de désync.

**La cause réelle du dégât par augmentation :** l'augmentation force la **value head** à
apprendre la symétrie des 6 familles (720 relabellings) depuis seulement 50 parties.
La policy survit (v7 policy-brute = 0.365 — le classement des coups est préservé) mais la
value head s'effondre (v_corr régresse 0.23 → 0.16 avec aug, vs 0.61 → 0.75 sans aug).

**Note :** augmentation correcte mais nuisible au faible volume. Verdict dépendant du volume,
pas une loi universelle. À 10k+ parties, la symétrie aide l'anti-overfit — la réactiver alors.
Architecture propre à terme : pooling invariant par permutation (DeepSet) plutôt qu'augmentation.

### 15.4 Run comparatif no-augmentation (50 iters)

```
Iter 10  | loss_v=0.94  v_corr=+0.608  pi_ent=1.668   ← chute massive depuis ln(12)=2.485
Iter 20  | loss_v=0.65  v_corr=+0.614  pi_ent=2.050
Iter 30  | loss_v=0.42  v_corr=+0.750  pi_ent=1.950
Greedy@25 = 0.27  ← meilleur résultat de toute l'histoire du projet, à iter 25
Greedy@50 = 0.19
```

Avec augmentation désactivée, la value head converge 3× plus vite (v_corr 0.75 vs 0.30)
et la policy se spécialise immédiatement (pi_ent 1.67 vs 2.28 à iter 10).

*Note : v_corr mesuré **in-sample** (sur le batch d'entraînement). Signal externe fiable = greedy@25=0.27.*

### 15.5 Retour expert n°3 — Corrections théoriques importantes (29/05/2026)

#### Correction 1 : ce n'est pas la policy que l'augmentation tuait, c'est la value

La policy-brute v7 (entraînée **avec** augmentation) atteint 0.365 vs greedy.
Une policy à 36% contre un adversaire fort n'est pas "quasi-uniforme et inutile" — son
entropie était haute (2.28) mais son *classement* des coups était bon. L'augmentation a
**ralenti la spécialisation**, elle ne l'a pas tuée. Le vrai sinistré était la **value head** :
v_corr descend 0.23 → 0.16 avec aug (régression), vs 0.61 → 0.75 sans aug.

#### Correction 2 : théorie PUCT avec Q=0

Avec Q(a)=0 pour tout a, le score PUCT vaut `c × P(a) × √N / (1 + N(a))`. Ce terme force
`N(a) ∝ P(a)` : les visites convergent vers le prior, pas vers l'uniforme. Plus de sims =
meilleure approximation de argmax(prior). La courbe value=0 aurait dû être **monotone
croissante** vers 0.365. L'anti-monotonie (0.260 à 30 sims → 0.115 à 100 sims) est
quasi-impossible sous PUCT propre avec Q vraiment nul.

#### Correction 3 : cause réelle de l'anti-monotonie dans le test keystone v1

`MCTSZeroValue` ne zeroisait que `_expand` (feuilles non-terminales). `_terminal_value`
retournait toujours les vraies valeurs ±score/20. Avec 30 sims, peu/aucune simulation
n'atteint un état terminal → Q ≈ 0 → visits ∝ prior → bon. Avec 100 sims, des chemins
atteignent des terminaux → vraies valeurs PIMC (biaisées vers un seul monde aléatoire) sont
backpropagées → Q ≠ 0 → visites dérivent du prior → anti-monotonie.

Conséquence : une partie du "MCTS détruit la performance" n'est pas de la value mal calibrée
— c'est un artefact de test. Les benchmarks MCTS vs greedy (0.03–0.09) sont aussi
contaminés : le bruit n'est pas le Dirichlet (confirmé définitivement off — `add_root_noise=False`
par défaut dans `search()`), mais les vraies valeurs terminales PIMC du champion v1.

#### Correction 4 : greedy bot plus fort que "myope"

Le greedy évalue le score **après** `step()` complet incluant le placement Reine (Q4 confirmé).
Les bascules de famille sont donc intégrées. Ce n'est pas un "réflexe myope" — c'est un
optimiseur de score réel post-placement. Random vs Greedy = 0.12, ce qui en fait un
adversaire respectueux. Le recadrage "ton IA ne joue pas mieux qu'un réflexe glouton" était
surcalibré. Policy-brute à 0.365 = 3× mieux que random = l'IA joue réellement bien.

### 15.6 Test keystone v2 — value=0 PARTOUT (terminaux inclus) — en cours

**Objectif :** confirmer que la courbe redevient monotone croissante une fois les terminaux
aussi forcés à 0, validant que l'anti-monotonie v1 était un artefact PIMC et non un bug
de backup.

**Implémentation :** `MCTSZeroValue` override `_expand` ET `_terminal_value` → 0.0.
Test à 10 / 30 / 100 / 200 sims vs greedy.

**Hypothèse :** courbe monotone croissante vers ~0.365. Si confirmé → eval harness propre,
mesures MCTS redeviennent fiables pour le run no-aug v8.

*Résultats en attente (test en cours).*

---

## 14. Diagnostic consolidé et état de l'art (29/05/2026)

### Ce qui est confirmé opérationnel

| Composant | Statut | Preuve |
|-----------|--------|--------|
| Fix valeur (z=sign, sans discount) | ✅ Fonctionne | loss_v 0.05→1.05, v_corr positif |
| Warm-start | ✅ Fonctionne | pi_ent 2.48→2.23, loss_pi 4.8→2.7 dès iter 10 |
| Value head apprend (sans aug) | ✅ Confirmé | v_corr 0.61→0.75, loss_v descend rapidement |
| Policy brute est bonne | ✅ Confirmé | 0.365 vs greedy = 3.6× random |
| augment_sample mathématiquement correct | ✅ Testé | 4 tests, 500 états réels, 0 erreur |
| Dirichlet off en évaluation | ✅ Confirmé | add_root_noise=False par défaut |

### Ce qui bloque encore

| Problème | Statut | Prochain levier |
|----------|--------|-----------------|
| **MCTS dégrade la policy** (0.365 → 0.06–0.16) | Cause identifiée : value mal calibrée avec aug | Désactiver aug → v_corr 0.75 → tester si MCTS aide |
| augmentation nuit à la value à faible volume | Confirmé | `--no-family-augmentation` jusqu'à 10k+ parties |
| MCTS terminal PIMC biaisé vers 1 monde | Quantifié (anti-monotonie keystone v1) | Keystone v2 en cours pour mesure propre |
| Volume de données (200 parties vs 10k) | Critique mais pas seul coupable | Parallélisme après validation qualité |

### Tableau de bord greedy — interprétation corrigée

| Métrique | Valeur brute historique | Valeur réelle (policy-only) | Cause du biais |
|----------|------------------------|---------------------------|----------------|
| Greedy winrate (champion v1) | 0.17–0.25 (MCTS 30 sims) | **0.365** | MCTS avec value morte dégrade |
| Greedy winrate (candidat v7) | 0.06–0.14 (MCTS 30 sims) | **0.34–0.37** | MCTS avec value mal calibrée dégrade encore plus |
| Greedy winrate (no-aug iter 25) | 0.27 (MCTS 30 sims) | non mesuré | Meilleur résultat observé avec MCTS |

### Prochaines étapes (ordre strict)

1. **Keystone v2** (terminé) : courbe monotone confirmée → eval propre validée.
2. **Run v8 no-aug** (en cours, iter 250/500) : résultats section 16.
3. **Expert #5** : à consulter après v8 iter 250 — voir section 16 pour les questions.
4. **Plus tard** : self-play continu (supprimer gate), PIMC multi-monde, progression dans state vector.

---

## 16. Run v8 — no-augmentation + parallel-games 4 + held-out (29/05/2026)

### 16.1 Configuration v8

```bash
uv run python -u main.py train \
  --iterations 500 --num-sims 500 \
  --no-family-augmentation \
  --mcts-batch-size 1 --parallel-games 4 \
  --memory-size 200000 \
  --arena-games 1000 --arena-every 100 \
  --greedy-benchmark-every 50 --greedy-benchmark-games 100 \
  --past-checkpoint-ratio 0.25 --train-steps 1 --lr-min 1e-5 \
  --held-out-ratio 0.08
```

**Nouveautés vs v7 :**
- `--no-family-augmentation` : confirmé bénéfique pour la value (v_corr 0.23→0.75 sans aug)
- `--parallel-games 4` : 4× plus de données par itération (2000 parties prévues sur 500 iters)
- `--held-out-ratio 0.08` : 8% des parties vers buffer OOD → `v_corr_ood` mesure honnête
- Three-curve benchmark : `policy_only | mcts_on | mcts_off` à chaque checkpoint greedy
- `--arena-games 1000` : ±3% CI sur le gating (vs ±7% à 200 parties)

### 16.2 Résultats complets iter 0–250

#### Métriques par itération

| Iter | loss | pi_loss | v_loss | v_corr | v_corr_ood | pi_ent |
|------|------|---------|--------|--------|-----------|--------|
| 0    | 4.456 | 2.456 | 2.000 | nan   | nan       | 2.277  |
| 10   | 2.973 | 2.075 | 0.898 | 0.454 | 0.435     | 1.941  |
| 20   | 3.394 | 2.233 | 1.161 | 0.398 | 0.295     | 2.003  |
| 30   | 3.031 | 2.187 | 0.844 | 0.194 | 0.281     | 2.059  |
| 40   | 3.156 | 2.354 | 0.803 | 0.469 | 0.315     | 2.070  |
| 50   | 3.019 | 2.183 | 0.835 | 0.333 | 0.243     | 1.678  |
| 60   | 3.031 | 2.205 | 0.826 | 0.399 | 0.357     | 1.807  |
| 70   | 2.904 | 2.074 | 0.829 | 0.292 | 0.418     | 1.920  |
| 80   | 2.905 | 2.231 | 0.674 | 0.559 | 0.349     | 2.058  |
| 90   | 3.275 | 2.318 | 0.957 | 0.262 | 0.446     | 1.936  |
| 100  | 3.132 | 2.405 | 0.727 | 0.547 | 0.408     | 1.983  |
| 110  | 3.024 | 2.218 | 0.807 | 0.406 | 0.447     | 1.954  |
| 120  | 3.017 | 2.258 | 0.759 | 0.415 | 0.519     | 1.873  |
| 130  | 2.778 | 2.062 | 0.716 | 0.557 | 0.487     | 1.946  |
| 140  | 3.274 | 2.313 | 0.961 | 0.251 | 0.521 ← pic | 1.945  |
| 150  | 3.077 | 2.276 | 0.801 | 0.495 | 0.454     | 2.011  |
| 160  | 3.270 | 2.423 | 0.847 | 0.418 | 0.463     | 2.039  |
| 170  | 2.851 | 2.189 | 0.662 | 0.611 | 0.409     | 1.774  |
| 180  | 2.636 | 2.102 | 0.535 | 0.661 | 0.466     | 1.926  |
| 190  | 2.813 | 2.138 | 0.674 | 0.532 | 0.466     | 1.865  |
| 200  | 2.985 | 2.272 | 0.712 | 0.508 | 0.360     | 1.949  |
| 210  | 3.004 | 2.268 | 0.736 | 0.563 | 0.411     | 1.882  |
| 220  | 2.818 | 2.136 | 0.682 | 0.520 | 0.382     | 1.818  |
| 230  | 2.689 | 2.172 | 0.517 | 0.738 | 0.380     | 2.017  |
| 240  | 2.626 | 1.939 | 0.687 | 0.463 | 0.380     | 1.824  |
| 250  | 2.830 | 2.232 | 0.598 | 0.570 | 0.383     | 2.016  |

#### Three-curve benchmark vs greedy bot

| Iter | policy_only | mcts_on | mcts_off | Écart on/off |
|------|-------------|---------|----------|--------------|
| 50   | **0.453**   | 0.222   | 0.351    | −0.129       |
| 100  | 0.366       | 0.170   | 0.286    | −0.116       |
| 150  | 0.340       | 0.214   | 0.306    | −0.092       |
| 200  | 0.333       | 0.196   | 0.316    | −0.120       |
| 250  | 0.344       | 0.140   | 0.263    | −0.123       |

#### Arenas

| Iter | wins | losses | draws | winrate | Décision |
|------|------|--------|-------|---------|----------|
| 100  | 479  | 442    | 79    | 0.52    | Champion conservé (< 0.55) |
| 200  | 469  | 469    | 62    | 0.50    | Champion conservé (< 0.55) |

### 16.3 Analyse et observations

#### Ce qui fonctionne
- **v_corr_ood non nulle et stable** : la value apprend sur des états jamais vus (~0.38–0.52),
  ce qui valide que le held-out fonctionne et qu'il n'y a pas de mémorisation pure.
- **v_loss descend** : 2.00 → 0.53 (iter 180), confirmant que la value head apprend.
- **Pas d'overfitting value** : écart v_corr / v_corr_ood faible (vs 0.75 in-sample seul en v7).

#### Ce qui ne fonctionne pas
1. **Champion jamais battu** (0.52 puis 0.50) → le self-play tourne indéfiniment sur le même
   champion initial (warm-start model_2.pth). Le candidat imite le champion sans le surpasser.
2. **policy_only régresse** : 0.453 (iter 50) → 0.344 (iter 250). Paradoxal : le modèle est
   entraîné sur les politiques MCTS du champion (qui devraient être meilleures que sa propre
   policy), mais sa policy brute *empire*. Hypothèse : distillation MCTS → candidat crée un
   artefact de distribution shift (le champion explore des états que le candidat ne voit pas
   en évaluation policy-only).
3. **mcts_on reste sous mcts_off** (value nuit toujours) : malgré v_corr_ood ~0.4, la value
   dégrade systématiquement les décisions MCTS. La valeur OOD n'est pas suffisante ou est mal
   calibrée en absolu (bias, non centré sur 0).
4. **mcts_off lui-même décline** : 0.351 → 0.263, ce qui signifie que la *policy* se dégrade
   pour tous les modes. Le prior PUCT lui-même empire.

#### Hypothèse centrale (deadlock du champion)
Le champion n'étant jamais remplacé, les données de self-play sont générées par le **même
modèle figé** depuis iter 0. Le candidat est en train de **sur-apprendre le comportement du
champion** sans avoir de signal de progression. C'est un cercle fermé :
- données = champion joue → targets = champion's MCTS visits
- candidat imite champion → pas assez différent pour gagner 0.55
- champion reste → mêmes données → même cycle

### 16.4 Questions posées à l'expert #5 + Réponses (29/05/2026 soir)

**Q1 — Deadlock du gating :** Le champion n'a jamais été remplacé sur 250 itérations (arena
0.52, 0.50). Avec un seuil 0.55, le candidat qui performe à 50–52% ne passe jamais. Faut-il :
(a) baisser le seuil à 0.51 ou supprimer le gating complètement (toujours mettre à jour),
(b) utiliser un ELO glissant plutôt qu'un gate binaire,
(c) considérer que le champion initial est trop fort pour être battu avec 500 sims vs 500 sims ?

**Q2 — Régression de la policy_only :** La policy brute (0 sim) régresse de 0.453 à 0.344
sur 200 itérations alors que le modèle est entraîné sur des cibles MCTS du champion (qui
ont 500 sims et devraient concentrer la probabilité sur les bons coups). Pourquoi la
distillation MCTS empire-t-elle la policy brute ? Est-ce un signe que le champion joue dans
une distribution d'états que le candidat n'explore pas ?

**Q3 — v_corr_ood ~0.4 insuffisant ?** La value OOD est à ~0.38–0.52 mais MCTS reste
systématiquement sous policy_only et sous mcts_off. Quelle valeur minimale de v_corr_ood
est typiquement nécessaire pour que le backup de valeur aide dans MCTS ? Est-ce un problème
de calibration absolue (bias) plutôt que de corrélation ?

**Q4 — mcts_off décline aussi :** Si mcts_off (value=0, PUCT pur sur prior) régresse de
0.351 à 0.263, c'est que le prior lui-même se dégrade. Or le prior vient du champion
(politique immuable). Cela suggère que le *candidat* apprend une policy progressivement
pire. Quel mécanisme peut expliquer ça ? Régularisation insuffisante ? Distribution shift
entre les états vus en self-play et ceux rencontrés contre le greedy ?

**Q5 — Que suggères-tu pour v9 ?** Compte tenu de : champion figé, policy qui régresse,
value qui apprend mais n'aide pas, 250 iters restantes probablement inutiles — quelle est
la priorité absolue pour le prochain run ?

---

### 16.5 Réponse de l'expert #5 — Diagnostic unifiant

#### Cause racine : l'opérateur d'amélioration de politique tourne à l'envers

En AlphaZero, tout repose sur une propriété : `π_MCTS` est **meilleur** que la policy brute.
Or les trois courbes v8 montrent l'inverse à chaque checkpoint :

```
mcts_on (0.14–0.22)  <  mcts_off (0.26–0.35)  <  policy_only (0.33–0.45)
```

MCTS n'est pas un opérateur d'amélioration — c'est un opérateur de **dégradation**. Les
cibles de self-play sont précisément `π_MCTS` (visites, value ON, 500 sims). Donc :

> value faible → MCTS empoisonné → `π_MCTS` pire que policy brute → distillation de cibles
> dégradées → `policy_only` descend → prior empire → `mcts_off` descend avec lui.

**Une seule mécanique** explique la régression de Q2 (policy) et Q4 (mcts_off). Ce n'est
pas une imitation qui plafonne — c'est une **spirale descendante** : le candidat est tiré
activement *sous* le champion qui l'a initialisé.

#### Q1 — Le gate protège, il ne bloque pas

Ne pas baisser le seuil ni supprimer le gate. Le candidat devient *plus mauvais* (arènes
0.52 → 0.50), le gate rejette donc correctement un candidat qui régresse. Supprimer le gate
avec un opérateur inversé = remplacer le meilleur modèle par un modèle dégradé → effondrement
accéléré. ELO glissant / self-play continu sont les bonnes architectures **une fois seulement
que `mcts > policy_only`**. Avant ça, le gate est le seul frein.

La cause du deadlock n'est pas le seuil 0.55 — c'est l'opérateur inversé.

#### Q2 — Pourquoi distiller 500 sims empire la policy ?

Au keystone, plus de sims = pire avec une mauvaise value. Donc 500 sims produit des cibles
*plus* dégradées que 30 sims. « 500 sims concentre sur les bons coups » est **exactement
faux** en régime value-empoisonnée. Distribution shift = amplificateur de second ordre
seulement.

#### Q3 — v_corr_ood ~0.4 : pourquoi ça ne suffit pas

r = 0.4 → 16% de variance expliquée. MCTS **amplifie** le bruit de value : une feuille
sur-évaluée attire des visites via Q, la recherche s'y concentre. À 500 sims, ce bruit
domine complètement. Cible empirique : **v_corr_ood > 0.6–0.7** avant que la value aide.

Le held-out révèle aussi que la value n'overfitte pas (v_corr ≈ v_corr_ood ≈ 0.4) — elle
est juste **plafonnée à r ≈ 0.4**, et c'est sa vraie qualité. Ce plafond vient probablement
de la variance PIMC mono-monde : le même état d'information reçoit des cibles win/loss
différentes selon les cartes cachées tirées. Volume ne casse pas ce plafond — seul un
changement de cible (moyenner sur K déterminisations) le casse.

Test à faire : régresser `v_pred` sur outcome held-out → vérifier pente ≈ 1 et intercept ≈ 0.
Un biais absolu (pente ≠ 1 ou offset ≠ 0) nuit au backup indépendamment de r, et se corrige
par recalibration (Platt scaling).

#### Q5 — Priorité v9 : donner aux feuilles un signal réel

Le problème fondamental : MCTS n'a **aucun signal de lookahead exploitable**.
- value ON → empoisonne.
- value OFF → Q = 0 partout → visites ∝ prior + bruit → `mcts_off < policy_only`.

La priorité n'est ni le gate ni le volume — c'est **donner aux feuilles un signal réel**,
par ordre de coût croissant :

1. **Value heuristique statique aux feuilles (priorité absolue)** : utiliser la fonction de
   score du greedy bot, normalisée dans [-1, 1], comme évaluation de feuille MCTS à la
   place de la value réseau. O(1), pas de rollout, signal infiniment meilleur que r=0.4.
   → Très probablement `mcts_on(heuristique) > policy_only` immédiatement → la spirale
   s'inverse → le candidat bat enfin le champion → deadlock Q1 se résout seul.

2. **Rollouts tronqués** (si heuristique insuffisante) : rollout greedy ou tronqué à
   profondeur k dans le monde déterminisé. Plus coûteux, non biaisé. Greedy-rollout >
   random-rollout en signal par échantillon.

3. **Value réseau gardée HORS de la recherche** jusqu'à `v_corr_ood > 0.6` ET
   `mcts_on(value) > mcts_off`. Réintroduire progressivement :
   `leaf = λ·v_net + (1-λ)·heuristique`, λ montant avec le held-out v_corr.
   (Approche AlphaGo original, conçue pour value pas encore fiable.)

4. **Casser le plafond r=0.4** : moyenner l'outcome sur K déterminisations par état →
   cible de value moins bruitée → r peut dépasser 0.4.

5. **Volume** (`--parallel-games`) : nécessaire mais pas suffisant seul.

#### Test décisif pour v9 (prévu)

50 itérations avec **value heuristique aux feuilles** (value réseau désactivée dans la
recherche), gate conservé, three-curve à chaque checkpoint.

**Critère de succès** : `mcts_on(heuristique) > policy_only` ET `policy_only` arrête de
régresser (idéalement remonte vers 0.453).

---

### 16.6 Run v9 — value heuristique (score intermédiaire) — 30/05/2026 matin

#### Configuration v9
```bash
uv run python -u main.py train \
  --iterations 50 --num-sims 500 --no-family-augmentation \
  --mcts-batch-size 1 --parallel-games 4 --memory-size 200000 \
  --arena-games 1000 --arena-every 100 \
  --greedy-benchmark-every 25 --greedy-benchmark-games 100 \
  --past-checkpoint-ratio 0.25 --train-steps 1 --lr-min 1e-5 \
  --held-out-ratio 0.08 --heuristic-value
```

**Implémentation** : `MCTSHeuristicValue._expand` appelle `super()._expand()` pour les priors
réseau, puis retourne `tanh(margin / 15)` où `margin = score_moi - moy(autres)` calculé par
`env._calcul_scores()` sur l'état courant (non terminal).

#### Résultats

| Iter | policy_only | mcts_on | mcts_off |
|------|-------------|---------|----------|
| 25   | 0.311       | 0.092   | 0.242    |
| 50   | 0.388       | 0.133   | 0.250    |

**Échec : `mcts_on < mcts_off < policy_only` — même ordering qu'avant.**

#### Post-mortem

`_calcul_scores()` renvoie le score *intermédiaire* en cours de partie, qui est souvent proche
de 0 (top_score moyen = −20 à −30 dans v8). `tanh(−2 / 15) ≈ −0.13` → signal quasi nul →
comportement identique à `MCTSZeroValue`. La hiérarchie rollout greedy > score intermédiaire
est confirmée, mais avant de lancer le rollout, l'expert #5 signale une anomalie plus profonde.

---

### 16.7 Retour expert #5 — Diagnostic révisé : l'anomalie est `mcts_off < policy_only`

#### Observation centrale

`mcts_off` (value=0, PUCT pur) est systématiquement **sous** `policy_only` à chaque checkpoint.
Or `mcts_off` devrait théoriquement égaler `policy_only` (visites ∝ prior → argmax ≈ argmax policy).
L'écart persistant −0.05 à −0.13 indique un problème structurel *avant* la value.

#### Deux hypothèses opposées

**(A) Bruit d'échantillonnage fini** : à sims modérés, `argmax(visites)` est une estimation
bruitée de `argmax(prior)`. L'écart se referme quand les sims montent. Dans ce cas, un signal
de feuille (rollout) aiderait ensuite.

**(B) PIMC strategy fusion** (Cowling et al. 2012) : la recherche déterminise un seul monde
par `search()` et planifie *comme si* elle connaissait les cartes cachées. Elle s'engage dans
des lignes optimales pour ce monde mais mauvaises en espérance. La policy brute, entraînée sur
des données moyennées, encode une stratégie robuste à l'ensemble d'information → elle bat la
recherche mono-monde. **Dans ce cas, aucun signal de feuille ne sauve la recherche**, car le
cadre PIMC mono-monde est lui-même l'opérateur de dégradation.

#### Discriminateur : courbe value=0 à sims croissants (30/100/300/1000)

- **Écart se referme** → (A) → rollout greedy mono-monde suffit.
- **Écart persiste ou s'élargit** → (B) → re-déterminisation par simulation (un monde frais
  par simulation dans un même `search()`), puis éventuellement rollout greedy par-dessus.

**Test terminé** (`scripts/discriminator.py`) — résultats section 16.8.

---

### 16.8 Série de tests diagnostiques post-expert #5 (30/05/2026)

#### Test D1 — sims-sweep value=0 non-apparié

```
policy_only (100g) : wr=0.340
value=0   30 sims  (80g) : wr=0.267  gap=−0.074
value=0  100 sims  (60g) : wr=0.328  gap=−0.013
value=0  300 sims  (40g) : wr=0.514  gap=+0.173  ← n=40, non-significatif
value=0 1000 sims  (20g) : wr=0.316  gap=−0.025  ← n=20, CI ±21%
```
**Verdict :** indécidable. Les seuls points fiables (n=80, 60) montrent gap négatif. Le pic
à 300 sims est non-significatif (CI ±16%). Sous-dimensionné pour trancher (A) vs (B).

#### Test D2 — v9 heuristique (score intermédiaire)

`MCTSHeuristicValue._expand` → `tanh(margin/15)` depuis `_calcul_scores()` courant.

```
Iter 25 : policy_only=0.311 | mcts_on=0.092 | mcts_off=0.242
Iter 50 : policy_only=0.388 | mcts_on=0.133 | mcts_off=0.250
```
**Échec.** `_calcul_scores()` donne le score intermédiaire (~0 en milieu de partie).
`tanh(−2/15) ≈ −0.13` → signal quasi nul → comportement ≈ MCTSZeroValue.

#### Test D3 — apparié multi-monde (architecture incorrecte)

Design : `num_worlds=30, num_sims=10` vs `num_worlds=1, num_sims=300`.
```
[60/150] policy=0.414  arm1=0.167  arm2=0.000
```
**Stoppé.** Architecture incorrecte : 30 arbres indépendants × 10 sims = arbres trop
superficiels. Confondu par la réduction de profondeur. Le 0.000 ne teste pas la strategy
fusion — il mesure l'inutilité d'un arbre à 10 sims.

#### Correction d'architecture (retour expert #5 révisé)

**Architecture 1 (mauvaise)** : W arbres × S sims = coût W×S. Compromis profondeur/diversité.
**Architecture 2 (ISMCTS)** : 1 arbre, monde frais PAR simulation. Coût = N sims (identique
au mono-monde). Pas de compromis. C'est Cowling et al. 2012.

Point clé démontré : avec value=0, ISMCTS ≡ mono-monde (Q=0 partout → priors identiques
→ arbres identiques → diff=0.000 exact). Le test discriminateur nécessite value ON pour que
les Q(a) des deux bras divergent via des signaux de mondes différents.

#### Test D4 — apparié ISMCTS value=0 (confirme l'identité)

```
[100/150] policy=0.421  mono=0.293  ismcts=0.293  (diff=0.000 exact)
```
Stoppé à 100 parties. Résultat attendu : avec Q=0 et priors identiques, les deux bras
sont mathématiquement équivalents. Confirme que le test discriminateur doit utiliser value ON.

#### Test D5 — apparié ISMCTS value ON (terminé)

`MCTS` (mono) vs `MCTSReDeterminize` (ISMCTS), value réseau ON, 300 sims, 150 paires.

**`MCTSReDeterminize`** : 1 arbre partagé, `env.clone_determinized()` frais à chaque sim.
Mismatch de mode (assassin/non-assassin selon monde) → traité par arrêt de descente au
nœud incohérent (approximation ISMCTS standard).

**Résultats complets (150 parties appariées) :**

```
policy_only  wr=0.424  [61W/83L/6D]
mono (arm1)  wr=0.186  [27W/118L/5D]
ismcts(arm2) wr=0.123  [18W/128L/4D]

ismcts − mono   : −0.127 ± 0.605  t=−2.56  ← ISMCTS significativement PIRE
ismcts − policy : −0.587 ± 1.005  t=−7.15
mono   − policy : −0.460 ± 1.008  t=−5.59
```

**ISMCTS est significativement inférieur au mono-monde (t=−2.56).** Ce n'est pas Branch 3
("ISMCTS ≈ mono") — c'est ISMCTS < mono < policy_only. Interprétation :

- (B) strategy fusion est **éliminé** comme cause principale.
- Avec value r=0.4 (bruité), ISMCTS aggrave : moyenner des mauvais signaux de valeur
  sur plusieurs mondes amplifie le bruit au lieu de le réduire. Le mono-monde commet
  certes à un seul monde, mais accumule au moins des Q cohérents dans ce monde.
- Les mismatches de mode (assassin present/absent selon monde) causent aussi des
  arrêts prématurés de descente → simulations moins profondes → pire que mono.

**Verdict D5 :** la recherche n'est pas le bon outil tant que la value est à r=0.4.
Test suivant : rollout greedy en feuille (D6) — signal de feuille non plafonné à r=0.4.

#### Arbre de décision post-D5

| Résultat | Interprétation | Suite |
|----------|----------------|-------|
| ISMCTS ≥ policy_only | (B) confirmé + fix validé | Run volume avec MCTSReDeterminize |
| ISMCTS > mono mais < policy_only | Value trop faible (r=0.4) pour que le moyennage aide | Tester rollout greedy en feuille |
| ISMCTS ≈ mono < policy_only | (B) éliminé | Fork 2 : self-play direct sans MCTS-professeur |

#### Note de l'expert #5 sur la limite de la famille MCTS

> « ISMCTS est le plafond de la famille MCTS pour l'info cachée. Ce n'est même pas la
> solution principielle — celle-ci est CFR (DeepStack, ReBeL), qui raisonne sur les croyances.
> Ton meilleur joueur, c'est ta policy, pas ta recherche. »

**Fork 2 confirmé par D6 (voir ci-dessous).**

---

#### Test D6 — rollout greedy en feuille (ultime tiebreak, 31/05/2026)

`MCTSGreedyRollout._expand` : priors réseau + rollout greedy complet jusqu'au terminal.
Signal réel (±1), non plafonné à r=0.4. 100 sims, 100 parties appariées.

```
  [ 60/100]  policy=0.414  zero=0.300  rollout=0.083
```
Stoppé à 60 parties — le verdict est sans appel.

```
policy_only    wr=0.414
mcts zero      wr=0.300  (MCTSZeroValue)
mcts rollout   wr=0.083  (MCTSGreedyRollout)  ← 5× pire que policy_only
```

**Le rollout greedy est la pire variante testée.** Pourquoi : le rollout greedy dans le
monde déterminisé simule "ce que ferait un greedy dans CE monde précis" — et comme le
monde est aléatoire (cartes cachées), ces outcomes bruités sont backpropagés dans l'arbre,
créant des Q(a) encore plus biaisés que la value réseau. Le rollout greedy est non-biaisé
*en espérance sur les mondes* seulement si on moyennait sur beaucoup de mondes. Dans le
PIMC mono-monde, il est biaisé vers un seul tirage → pire que value=0.

---

## 17. Verdict final et pivot Fork 2 (31/05/2026)

### Tableau récapitulatif de tous les modes MCTS testés

| Mode | winrate vs greedy | vs policy_only |
|------|-------------------|----------------|
| **policy_only (0 sim)** | **0.42–0.45** | — baseline |
| mcts_off MCTSZeroValue | 0.26–0.35 | −0.10 à −0.15 |
| mcts_on value réseau | 0.12–0.22 | −0.20 à −0.25 |
| ISMCTS value ON | 0.12 | −0.30 |
| heuristique score intermédiaire | 0.09–0.13 | −0.30 |
| rollout greedy | 0.08 | −0.33 |

**Conclusion : aucune variante MCTS ne bat la policy brute sur ce jeu.**

### Pourquoi la recherche échoue systématiquement

1. **Information cachée profonde** : les cartes adverses (Espions face cachée, mains) sont
   invisibles. La déterminisation PIMC tire UN monde parmi des centaines possibles → les
   Q(a) optimisent pour ce monde, pas pour l'ensemble d'information réel. La policy, elle,
   a été entraînée sur des données moyennées → encode une stratégie robuste à tous les mondes.

2. **MCTS comme professeur est auto-destructeur** : si `π_MCTS` < `policy_only`, distiller
   `π_MCTS` dégrade la policy → spirale descendante (v8 : 0.453 → 0.344 en 250 iters).

3. **Value plafonnée à r=0.4** : PIMC mono-monde génère un même état d'information avec des
   outcomes différents selon les cartes tirées → prédictibilité intrinsèque limitée.
   Le volume ne casse pas ce plafond.

### Fork 2 — Paradigme de remplacement

**Principe :** améliorer la policy directement par self-play sur outcomes réels, sans MCTS.

**Architecture :**
- Parties contre un pool d'adversaires : greedy bot + anciens checkpoints (past_checkpoint_ratio)
- Cible policy = **l'action jouée** (one-hot sur le coup réel, pas πMCTS)
- Cible value = z=sign(margin) comme maintenant (inchangé)
- Exploration = température de softmax (température haute en début de partie, argmax après)
- Pas de MCTS pendant l'entraînement

**Pourquoi ça marche mieux ici :**
- L'agent apprend directement depuis les outcomes de parties complètes
- Pas de signal corrompu par la déterminisation
- La policy guide l'action, pas une recherche biaisée
- Analogie : DeepStack / Libratus (poker) n'utilisent pas MCTS — ils entraînent des policies
  directement sur des outcomes d'information imparfaite

**Point de départ :** policy brute à ~0.42 vs greedy = base saine.

---

## 17.1 Correction du plan Fork 2 — retour expert #5 (31/05/2026)

### Défaut du plan initial : « cible = action jouée » = imitation pure

Si la policy échantillonne ses propres actions et s'entraîne à les reproduire sans pondération
par l'outcome, elle renforce sa distribution courante **y compris ses coups perdants**. Pas de
signal d'amélioration. Au mieux no-op, au pire dérive.

### La mise à jour policy doit être couplée à l'outcome

**Option A — Self-imitation filtré (recommandé pour le premier run)** :
- Garder uniquement les trajectoires gagnantes (`z > 0`) OU pondérer par `z`
- Cible policy = one-hot sur l'action jouée dans les parties gagnantes
- Signal : le réseau imite son *bon* jeu passé, pas tout son jeu
- Stable, difficile à déstabiliser. Expert Iteration où l'expert = parties gagnantes.

**Option B — REINFORCE avec baseline** :
- `loss_pi = −(z − V(s)) · log π(a|s)`
- La value head (r≈0.4) devient enfin utile comme baseline de réduction de variance
- Plus efficace que A, plus de variance

**Option C — AWR (Advantage Weighted Regression)** :
- `loss_pi = −exp((z − V(s))/β) · log π(a|s)`
- Robuste aux données off-policy d'un buffer. Bon compromis.

**Recommandation : Option A d'abord, puis B/C quand policy vs greedy monte stablement.**

### Deux ajouts indispensables

**1. Pool d'adversaires (déjà prévu — bien)** : self-play naïf tourne en rond (dynamique
pierre-feuille-ciseaux) sur les équilibres mixtes. Le pool avec anciens checkpoints + greedy
est une approximation de *fictitious play* qui casse ces cycles.

**2. Régularisation d'entropie (nouveau)** : bonus `+coef · H(π)` dans la loss policy pour
maintenir la stochasticité. Une policy qui collapse vers le déterministe devient exploitable
(l'équilibre optimal est mixte). Non négociable.

### Mesures

- **Métrique unique** : `policy_only vs greedy` apparié (common random numbers)
- **Proxy d'exploitabilité** : winrate vs pool dans le temps — si ça oscille, c'est du cycling,
  pas un bug. Réponse : renforcer pool et entropie.
- Critère de succès : `policy_only > 0.50 vs greedy`

### Plan d'implémentation Fork 2

1. Remplacer `mcts.search(env)` par échantillonnage température depuis les logits policy
2. Cible policy = **one-hot sur l'action jouée** (au lieu des visites MCTS)
3. Loss policy = **pondérée par z** (Option A : `max(z, 0)`) + **bonus entropie**
4. Garder `past_checkpoint_ratio` pour le pool
5. Supprimer les trois courbes du benchmark, garder uniquement `policy_only vs greedy`
6. Flags CLI : `--no-mcts`, `--entropy-coef 0.01`, `--policy-temperature 1.0`

---

## 18. Runs Fork 2 (31/05/2026)

### 18.1 Fork 2a — test initial (50 iters, entropy_coef=0.01)

```bash
uv run python -u main.py train --no-mcts --iterations 50 \
  --no-family-augmentation --parallel-games 4 --entropy-coef 0.01 \
  --policy-temperature 1.0 --past-checkpoint-ratio 0.25 \
  --greedy-benchmark-every 25 --greedy-benchmark-games 100 \
  --arena-every 0 --no-progressive-sims
```

**Durée : ~13 minutes** (vs ~2h pour MCTS 50-iter). Dramatiquement plus rapide.

| Iter | pi_ent | policy_only | mcts_on | mcts_off |
|------|--------|-------------|---------|----------|
| 0    | 2.275  | —           | —       | —        |
| 10   | 0.701  | —           | —       | —        |
| 20   | 0.533  | —           | —       | —        |
| 25   | —      | **0.316**   | **0.398** | 0.287  |
| 30   | 1.144  | —           | —       | —        |
| 40   | 1.094  | —           | —       | —        |
| 50   | —      | **0.406**   | 0.366   | 0.362    |

**Observations :**
1. **Collapse d'entropie initial** : pi_ent 2.275 → 0.533 en 20 iters (entropy_coef=0.01 insuffisant
   face au LR élevé). La policy s'est d'abord effondrée (policy_only=0.316 à iter 25).
2. **Récupération spontanée** : quand le LR cosine a baissé, pi_ent est remonté à ~1.1 et
   policy_only a récupéré à **0.406** — quasiment au niveau du champion (0.424) en 50 iters.
3. **iter 25 : `mcts_on=0.398 > policy_only=0.316` — première fois que MCTS aide**. Signal
   de self-imitation donne à la value head un signal suffisant pour que MCTS soit positif.
4. **iter 50** : policy_only=0.406 > mcts_on=0.366 ≈ mcts_off=0.362. L'opérateur MCTS n'aide
   plus au niveau final, mais la policy seule est forte.

**Action corrective** : `--entropy-coef 0.05` + `--policy-temperature 1.2` pour Fork 2b.

### 18.2 Fork 2b — entropy renforcée (200 iters, en cours)

```bash
uv run python -u main.py train --no-mcts --iterations 200 \
  --no-family-augmentation --parallel-games 4 --entropy-coef 0.05 \
  --policy-temperature 1.2 --past-checkpoint-ratio 0.25 \
  --greedy-benchmark-every 25 --greedy-benchmark-games 100 \
  --arena-every 0 --no-progressive-sims
```

**Durée : ~48 minutes** pour 200 iters (vs ~8h pour MCTS 200 iters — 10× plus rapide).

| Iter | pi_ent | v_corr | policy_only | mcts_on | mcts_off |
|------|--------|--------|-------------|---------|----------|
| 0    | 2.282  | —      | —           | —       | —        |
| 10   | 1.691  | 0.327  | —           | —       | —        |
| 20   | 1.386  | 0.303  | —           | —       | —        |
| 25   | —      | —      | 0.277       | 0.319   | 0.316    |
| 30   | 1.596  | 0.168  | —           | —       | —        |
| 50   | 0.832  | 0.425  | **0.441**   | 0.319   | 0.423    |
| **75** | — | 0.534  | **0.457 ← pic** | **0.440** | **0.438** |
| 100  | 1.152  | 0.482  | 0.240       | 0.312   | 0.355    |
| 125  | —      | —      | 0.271       | 0.402   | 0.421    |
| 150  | 1.078  | 0.427  | 0.389       | 0.309   | 0.383    |
| 175  | —      | —      | 0.337       | 0.274   | 0.351    |
| 200  | —      | —      | 0.396       | 0.295   | 0.363    |

**Analyse :**

1. **Pic iter 75 : policy_only=0.457 > champion (0.424)** — première amélioration réelle.
   À iter 75, les trois courbes convergent (0.457 / 0.440 / 0.438) — la policy ET le MCTS
   sont au-dessus du champion.

2. **Cycling confirmé** : après iter 75, policy_only oscille entre 0.240 et 0.457. C'est
   exactement la dynamique "pierre-feuille-ciseaux" prédite par l'expert. Le modèle apprend
   à exploiter le pool, puis les nouveaux checkpoints du pool l'exploitent en retour.

3. **v_corr record : 0.534** à iter 70 — la value head apprend mieux sans la distorsion MCTS.

4. **mcts_on > policy_only à plusieurs checkpoints** (iter 25, 50, 75, 125) — pour la première
   fois, MCTS aide de façon répétée. Le signal de self-imitation pondéré par z améliore la
   value head suffisamment pour que MCTS soit parfois positif.

5. **pi_ent oscille entre 0.75 et 1.70** — le coefficient 0.05 évite le collapse total de
   Fork 2a (0.533) mais n'est pas assez fort pour maintenir l'entropie haute.

**Meilleur checkpoint : `models/model_2_ckpt_75.pth`** (policy_only=0.457).

**Diagnostic du cycling :** la variance de mesure (benchmark non-apparié, 100 parties) masque
partiellement le signal. Les swings de ±0.15-0.20 contiennent à la fois du vrai cycling et
du bruit de mesure. Un benchmark apparié (common random numbers) serait nécessaire pour
distinguer les deux.

**Prochaine étape recommandée :**
- `--entropy-coef 0.10-0.15` pour maintenir la stochasticité et réduire le cycling
- Benchmark apparié pour mesurer le vrai progrès
- Éventuellement : pool plus diversifié (greedy + tous les checkpoints passés)

### 18.3 Fork 2c — entropy=0.10 (200 iters)

```bash
uv run python -u main.py train --no-mcts --iterations 200 \
  --no-family-augmentation --parallel-games 4 --entropy-coef 0.10 \
  --policy-temperature 1.2 --past-checkpoint-ratio 0.25
```

| Iter | pi_ent | v_corr | policy_only | mcts_on | mcts_off |
|------|--------|--------|-------------|---------|----------|
| 25   | —      | —      | 0.344       | 0.305   | 0.326    |
| 50   | 0.434  | 0.346  | 0.413       | 0.340   | 0.340    |
| 75   | —      | —      | 0.306       | 0.226   | 0.208    |
| 100  | 0.568  | 0.362  | 0.330       | 0.319   | 0.380    |
| 125  | —      | —      | **0.423**   | 0.359   | 0.320    |
| 150  | 0.857  | 0.314  | 0.371       | 0.364   | 0.330    |
| 175  | —      | —      | 0.383       | 0.319   | 0.309    |
| 200  | 1.458  | 0.299  | 0.295       | 0.323   | **0.434** |

**Observations :**
- v_corr record : **0.592** à iter 130 — la value continue de progresser
- Cycling identique à Fork 2b, peak légèrement plus bas (0.423 vs 0.457)
- `entropy_coef=0.10` n'apporte pas d'amélioration significative vs 0.05
- mcts_off=0.434 à iter 200 avec pi_ent=1.458 — quand la policy est diffuse (haute entropie),
  MCTS pur sur prior peut atteindre 0.43 (proche du champion)

**Cause du cycling identifiée :** les checkpoints passés du candidat entrent dans le pool
(`past_checkpoint_ratio=0.25`). Quand un checkpoint bat le champion, ses samples z=+1
entrent dans le buffer — le candidat apprend la stratégie du checkpoint (contre-stratégie
du champion), cassant sa propre stratégie gagnante.

**Tableau comparatif Fork 2 :**

| Run | entropy | Pic policy_only | Iter du pic |
|-----|---------|-----------------|-------------|
| Fork 2a | 0.01 | 0.406 | 50  |
| Fork 2b | 0.05 | **0.457** | 75 |
| Fork 2c | 0.10 | 0.423 | 125 |

**Meilleur checkpoint absolu : `models/model_2_ckpt_75.pth` (Fork 2b, policy=0.457)**

### 18.4 Fork 2d — warmstart depuis le meilleur ckpt, past_checkpoint_ratio=0 (en cours)

Hypothèse : supprimer le pool de checkpoints adversaires (`past_checkpoint_ratio=0`) élimine
le mécanisme de cycling. Champion figé = champion joue toujours contre lui-même → données
stables → policy apprend sans être perturbée par des contre-stratégies.

Point de départ : `model_2_ckpt_75.pth` (policy=0.457, meilleur vu).

```bash
cp models/model_2_ckpt_75.pth models/model_2.pth  # new champion
uv run python -u main.py train --no-mcts --iterations 200 \
  --no-family-augmentation --parallel-games 4 --entropy-coef 0.05 \
  --policy-temperature 1.2 --past-checkpoint-ratio 0.0 \
  --greedy-benchmark-every 25 --greedy-benchmark-games 100 \
  --arena-every 0 --no-progressive-sims
```

**Durée : ~46 min.** Champion = Fork 2b iter 75 (policy_only=0.457).

| Iter | pi_ent | v_corr | policy_only | mcts_on | mcts_off |
|------|--------|--------|-------------|---------|----------|
| 25   | —      | —      | 0.389       | **0.409** | 0.323    |
| 50   | 0.835  | 0.260  | 0.298       | 0.277   | 0.240    |
| 75   | —      | —      | 0.224       | 0.273   | 0.219    |
| 100  | 0.875  | 0.473  | 0.287       | 0.313   | 0.266    |
| 125  | —      | —      | 0.283       | **0.389** | 0.330    |
| 150  | 1.095  | 0.410  | 0.237       | 0.274   | 0.281    |
| 175  | —      | —      | 0.281       | 0.309   | 0.312    |
| 200  | —      | —      | 0.296       | 0.280   | 0.292    |

**Conclusion Fork 2d :** sans pool (`past_checkpoint_ratio=0`), la policy régresse
systématiquement depuis le point de départ (0.457 → 0.22-0.30). Le modèle oublie ses
stratégies gagnantes (catastrophic forgetting). Le pool de checkpoints est **nécessaire**
pour maintenir la diversité et prévenir l'oubli — même s'il génère du cycling.

**Champion restauré :** `models/model_2.pth` = Fork 2b iter 75 (policy_only=0.457).

---

## 19. Synthèse Fork 2 — bilan complet (31/05/2026)

### Tableau comparatif des 4 runs Fork 2

| Run | entropy_coef | pool | Pic policy_only | Iter pic | Moyenne approx. |
|-----|-------------|------|-----------------|----------|-----------------|
| 2a  | 0.01 | 0.25 | 0.406 | 50  | ~0.35 |
| **2b**  | **0.05** | **0.25** | **0.457** | **75**  | **~0.37** |
| 2c  | 0.10 | 0.25 | 0.423 | 125 | ~0.35 |
| 2d  | 0.05 | 0.00 | 0.389 | 25  | ~0.28 |

**Meilleure config : Fork 2b (entropy=0.05, pool=0.25).**

### Fork 2e — mémoire et LR réduit (300 iters, lr=5e-4, memory=100k, train_steps=2)

Démarré depuis Fork 2b "iter75" (faux bon checkpoint : vrai paired wr=0.260). Meilleur v_corr
observé : **0.694** (iter 230). Policy_only oscille 0.274-0.379 (bruit non-apparié). Confirmé
que le point de départ était mauvais.

---

## 20. Benchmark apparié — mesure réelle des checkpoints (31/05/2026)

### Problème découvert : les 0.457 étaient du bruit

Le benchmark d'entraînement (100 parties, donnes aléatoires, ±10% CI) produisait des
swings de ±0.20 pour le même modèle. Les «améliorations» visibles pendant Fork 2b/2c
(policy_only jusqu'à 0.457) étaient **statistiquement non significatives**.

### Résultats appariés (300 parties seedées, CI ±5% worst-case)

```
model_2_ckpt_250.pth (v8 MCTS iter 250)   : wr = 0.396 ±0.056  ← MEILLEUR
model_2.pth          (Fork 2b "iter75")    : wr = 0.260 ±0.051
model_2_ckpt_50.pth  (Fork 2d iter 50)     : wr = 0.267 ±0.051
model_2_ckpt_75.pth  (Fork 2d iter 75)     : wr = 0.254 ±0.051
```

**Le meilleur checkpoint connu est `model_2_ckpt_250.pth` (issu de v8, entraîné avec MCTS)**
avec wr=0.396 ±0.056 en mesure appariée. Fork 2 n'a pas encore battu ce niveau en mesure
propre. Nouveau champion = `model_2_ckpt_250.pth`.

---

## 21. Fork 2f — départ depuis le vrai meilleur checkpoint (31/05/2026)

```bash
# Champion remplacé par model_2_ckpt_250.pth (wr_paired=0.396)
uv run python -u main.py train --no-mcts --iterations 200 \
  --no-family-augmentation --parallel-games 4 --entropy-coef 0.05 \
  --policy-temperature 1.2 --past-checkpoint-ratio 0.25 \
  --train-steps 2 --memory-size 100000 --lr 5e-4 \
  --greedy-benchmark-every 25 --greedy-benchmark-games 100 \
  --arena-every 0 --no-progressive-sims
```

**Durée : ~46 min.** Départ : v_corr=0.676 (hérité de v8, le meilleur point de départ vu).

| Iter | pi_ent | v_corr | policy_only | mcts_on | mcts_off | mcts_on > policy ? |
|------|--------|--------|-------------|---------|----------|--------------------|
| 0    | 0.961  | 0.676  | —           | —       | —        | —                  |
| 25   | —      | —      | 0.326       | 0.370   | 0.412    | ✓                  |
| 50   | 0.996  | 0.467  | 0.351       | **0.413** | 0.333  | ✓                  |
| 75   | —      | —      | 0.213       | 0.357   | 0.283    | ✓                  |
| 100  | 0.845  | 0.485  | 0.216       | 0.381   | 0.352    | ✓                  |
| 125  | —      | —      | 0.375       | 0.354   | 0.389    | ✗ (−0.021)         |
| 150  | 0.745  | 0.594  | 0.370       | 0.253   | 0.392    | ✗                  |
| 175  | —      | —      | 0.326       | 0.389   | 0.323    | ✓                  |
| 200  | —      | —      | 0.396       | 0.326   | 0.280    | ✗                  |

**Observations clés :**

1. **mcts_on > policy_only à 5/8 checkpoints** — cohérence inédite. Quand le modèle démarre
   avec une bonne value (v_corr=0.676), MCTS aide régulièrement.
2. **mcts_on peak 0.413** (iter 50) — potentiellement au-dessus du baseline paired (0.396)
   mais non vérifié en paired (mesure non-appariée = bruit ±10%).
3. **v_corr 0.594-0.676** — le meilleur de tous les runs. La value head bénéficie du warmstart
   v8 (MCTS distillait tout de même un signal de value utile).
4. **Cycling identique** : policy_only oscille 0.213–0.396. La moyenne est ~0.33.
5. **iter 200 : policy_only=0.396** = exactement le baseline paired de départ. Fork 2f
   n'a pas progressé net après 200 iters sur ce checkpoint.

---

## 22. Synthèse globale — état de l'art au 31/05/2026

### Tableau de tous les runs (mesures non-appariées sauf *)

| Run | Méthode | Départ | Best policy_only | Paired wr* | Notes |
|-----|---------|--------|-----------------|------------|-------|
| v8 (250 iters) | MCTS | warm-start | 0.453 | 0.396* | Champion actuel |
| Fork 2a | Self-imit, ent=0.01 | v8 warm | 0.406 | — | Collapse entropie |
| Fork 2b | Self-imit, ent=0.05 | v8 warm | 0.457 | 0.260* | Bruit 100-parties |
| Fork 2c | Self-imit, ent=0.10 | v8 warm | 0.423 | — | — |
| Fork 2d | Self-imit, pool=0 | Fork2b ckpt75 | 0.389 | — | Forgetting |
| Fork 2e | Self-imit, lr=5e-4 | Fork2b ckpt75 | 0.379 | — | — |
| **Fork 2f** | Self-imit, ent=0.05 | **v8_ckpt250** | 0.396 | **?** | Meilleur départ |

*Paired = 300 parties seedées, CI ±5%.

### Ce qui est prouvé

1. **MCTS ne convient pas à ce jeu** : 5 variantes testées (value, ISMCTS, rollout greedy,
   heuristique, value=0), toutes < policy_only. Résultat négatif propre et bien gainé.
2. **Fork 2 fonctionne** : 10× plus rapide, MCTS aide quand la value est bonne (v_corr>0.6),
   le self-imitation extrait un signal réel de l'outcome.
3. **Le pool est essentiel** : sans checkpoints adverses, forgetting immédiat (Fork 2d).
4. **La mesure appariée est indispensable** : ±10% sur 100 parties non-appariées masque tout
   signal réel. Les benchmarks d'entraînement sont indicatifs seulement.
5. **Meilleur modèle prouvé** : v8_ckpt_250 à 0.396 ±0.056 (300 parties appariées).

### Ce qui est ouvert

1. **Le cycling** : policy oscille ±0.15-0.20 autour de ~0.33-0.36 dans tous les runs Fork 2.
   Est-ce fondamental (équilibre mixte zéro-somme) ou corrigible (meilleur pool/régularisation) ?
2. **Fork 2f iter 50 (mcts_on=0.413)** : checkpoint potentiellement meilleur que 0.396 mais
   non mesuré en appairé. À benchmarker.
3. **v_corr=0.676 → aide MCTS** : avec un bon point de départ, MCTS aide à 5/8 checkpoints.
   Si le cycling pouvait être réduit, on pourrait rester dans la zone "mcts_on > policy_only"
   durablement et lancer un run MCTS (ou ISMCTS) à volume.
4. **Ce n'est pas du cycling — c'est de la régression.** La matrice est quasi-triangulaire
   (transitif). L'opérateur `max(z,0)` renforce du bruit après ~75 iters → dégradation
   progressive. Fix : AWR.

---

## 23. Retour expert #5 — Recadrage mesure et séquençage (31/05/2026)

### Fil rouge : le bruit de mesure est l'ennemi principal

Le mirage Fork 2b (0.457 → 0.260 en apparié) était du même type que le mirage v7
(v_corr=0.75 in-sample → 0.40 OOD). La règle désormais : **aucun chiffre non-apparié ne
déclenche une décision**. Le benchmark apparié (common random numbers) est le standard minimum.

### Q3 — Prérequis absolu : mesurer Fork 2f iter 50 en apparié

Trois nombres requis (300 parties seedées) :
1. `policy_only vs greedy` — Fork 2 a-t-il amélioré la policy brute au-delà de 0.396 ?
2. `mcts_on vs greedy` — MCTS aide-t-il depuis ce point ?
3. `mcts_on − policy_only` apparié — bénéfice net de la recherche.

**Résultats Q3** (`model_2_ckpt_50.pth`, 300 parties seedées, MCTS sims=30) :

```
policy_only  wr=0.398 ±0.056  [115W/174L/11D]
mcts_on      wr=0.378 ±0.056  [108W/178L/14D]
Diff mcts_on−policy : −0.037 ±0.811  t=−0.78  (non significatif)
```

Conclusion Q3 :
- policy_only=0.398 ≈ baseline 0.396 — Fork 2f n'améliore pas la policy vs greedy de façon mesurable
- MCTS légèrement négatif mais non-significatif (t=−0.78 < 1.65)
- Le chiffre 0.413 non-apparié de l'entraînement était du bruit comme 0.457

### Clarification sur v_corr=0.676 (Fork 2f iter 0)

Fork 2f lancé avec `--held-out-ratio 0.0` → pas de buffer held-out → v_corr_ood=nan.
Le 0.676 est **in-sample** (mesure sur le batch d'entraînement, même modèle qui génère les
données). **La prémisse de Q2 s'effondre** — même scénario que le 0.75 de v7. On n'ouvre
pas MCTS sur ce chiffre.

### Q1 — Ce n'est probablement pas du cycling

Distinction cruciale (expert) : osciller face à un adversaire FIXE (greedy) ≠ cycling.
Le cycling est une non-transitivité dans le self-play (A bat B bat C bat A), observable
via table croisée des checkpoints. Le ±0.20 face au greedy est probablement la signature
d'un **opérateur d'apprentissage trop faible** (self-imitation max(z,0)) : credit
assignment épouvantable (z binaire sur 46 coups), parties perdues ignorées (poids=0).

**Diagnostic réel** : table croisée des checkpoints Fork 2f. Si triangulaire (tardifs >
précoces) → progrès transitif mais lent. Si cycles → non-transitivité réelle.
**Test en cours** (`scripts/cross_table.py`).

### Q2 — Pas encore ouvert (dépend de Q3 et du held-out)

La seule façon de trancher : le nombre 2 de Q3 en apparié. Si mcts_on>policy_only>0.396
significatif ET v_corr_ood>0.5 sur les mêmes données → porte entrouverte. Sinon fermée.

### Upgrade algorithme recommandé : AWR (Option C) après les mesures

Self-imitation Option A (`max(z,0)`) est l'opérateur le plus faible possible. Option B
(REINFORCE avec baseline) est on-policy mais le buffer FIFO est off-policy → biais.
**AWR** : `loss = −exp((z − V(s))/β) · log π(a)` — avantage continu, baseline, utilise
les parties perdues, off-policy-safe. Adapté au buffer actuel. À implémenter APRÈS Q3.

### Implémentation AWR (réalisée)

`TrainConfig` : `awr_beta=1.0`, `awr_weight_clip=20.0`. Baseline = moyenne de z par batch.
Avantage continu, parties perdues incluses (poids <1 → pousse l'action vers le bas).
Flags CLI : `--awr-beta 1.0 --awr-weight-clip 20.0`.

### Run AWR en cours (150 iters, v8_ckpt_250, held-out=0.08)

**Durée : ~34 min.** Départ : v8_ckpt_250.

| Iter | v_corr | v_corr_ood | pi_ent | policy_only | mcts_on | mcts_off |
|------|--------|-----------|--------|-------------|---------|----------|
| 0    | 0.761  | nan        | 0.761  | —           | —       | —        |
| 10   | 0.389  | **0.420**  | 0.666  | —           | —       | —        |
| 20   | 0.650  | **0.487**  | 0.578  | —           | —       | —        |
| 25   | —      | —          | —      | 0.362       | 0.293   | 0.354    |
| 30   | 0.538  | **0.495**  | 0.833  | —           | —       | —        |
| 40   | 0.566  | 0.444      | 1.007  | —           | —       | —        |
| 50   | 0.478  | 0.425      | 0.519  | 0.281       | **0.436** | 0.245    |
| 70   | 0.588  | **0.523**  | 0.897  | —           | —       | —        |
| 75   | —      | —          | —      | 0.394       | 0.287   | 0.364    |
| 90   | 0.498  | **0.547** ← | 0.668 | —          | —       | —        |
| 100  | 0.467  | 0.474      | 0.782  | 0.354       | 0.380   | 0.385    |
| 125  | —      | —          | —      | 0.347       | 0.312   | 0.309    |
| 150  | —      | —          | —      | 0.231       | 0.354   | 0.400    |

**Observations clés :**

1. **v_corr_ood enfin mesuré honnêtement** (held-out=0.08). Plage : 0.40–0.55. In-sample ≈ OOD
   → pas de mirage in-sample. Moyenne OOD ≈ 0.47.

2. **v_corr_ood dépasse 0.5 à iter 70 (0.523) et iter 90 (0.547)** — seuil indicatif de
   l'expert pour rouvrir la question MCTS. Mais non-accompagné d'un benchmark MCTS aparié.

3. **mcts_on=0.436 à iter 50** (non-aparié, 100 jeux) > policy_only=0.281. Mais le benchmark
   à 100 jeux a CI ±10% — à vérifier en aparié.

4. **AWR ne résout pas l'oscillation** du benchmark non-aparié : policy_only oscille
   0.231–0.394 comme avec Option A.

5. **pi_ent plus stable** qu'Option A : plage 0.52–1.01 vs 0.53–1.69. L'AWR semble
   mieux préserver la diversité.

### Table croisée AWR + v8_250 (7 checkpoints × 80 parties)

```
Classement : awr50=0.549 > awr25=0.542 > awr100=0.522 > awr75=0.487
             > awr125=0.483 > v8_250=0.460 > awr150=0.456

vs v8_250 (80 parties) :
  awr25 : wr=0.613 ±0.110  t=+2.02  ← "significatif"
  awr50 : wr=0.581 ±0.112  t=+1.41
  awr100: wr=0.568 ±0.113  t=+1.17
  awr150: wr=0.417          t=−1.43  ← régression
```

**Mais** le résultat t=+2.02 pour awr25 à 80 parties était une fluctuation.

### Confirmation awr25 vs v8_250 (300 parties appariées)

```
131W/150L/19D  wr=0.466 ±0.058  t=−1.14
→ pas de différence significative
```

**v8_250 reste le seul champion prouvé.** awr25 est neutre (0.466, non-sig), ce qui est
mieux que Fork 2f ckpt75 (0.433, t=−2.24, significativement pire). **AWR arrête la régression
mais n'améliore pas encore le modèle en mesure à 300 parties.**

La limite critique : pour détecter un avantage réel de ΔWR=0.05 avec puissance 80%, il
faut n > 780 parties. Toutes les "confirmations" à 80-100 parties produisent des faux
positifs. La barre est : **300 parties minimum, idéalement 500+**.

---

## 24. Retour expert #5 — Bilan et choix décisif (31/05/2026)

### Vérité difficile

v8_250 est toujours champion — aucune méthode ne l'a battu à puissance adéquate. Le
"gain" Fork 2f ckpt75 à 60 parties (t=+2.02) était un faux positif : 300 parties montraient
t=−2.24. AWR awr25 est neutre (t=−1.14), non significativement différent d'Option A (Δ=0.033,
Z≈0.8). AWR a arrêté l'hémorragie ; il n'a pas amélioré.

### Q1 — Protocole de mesure correct : SPRT pentanomial sur parties appariées (Stockfish)

**Duplicate (CRN + swap de sièges) :** joue chaque donne deux fois, sièges inversés. Annule
la chance de donne ET l'avantage du premier coup. n≈780 non-apparié → 200-400 paires.

**SPRT (Sequential Probability Ratio Test) :** pas de n fixé. Définis H0: Δ≤0 vs H1: Δ≥seuil
(2-3%), α=β=0.05. Accumule le log-likelihood-ratio donne par donne ; arrête quand une borne
est franchie. Coût minimal sur les cas clairs.

**SPRT pentanomial sur parties appariées = protocole Fishtest (Stockfish).** Adopter ce
standard : c'est exactement le problème.

### Q2 — Le cycle "neutre → adopter" est une marche aléatoire

N'adopter que sur H1 validée (SPRT). « Si neutre → nouveau champion » injecte du bruit, dérive
mais ne monte pas. Le vrai plafond n'est pas établi : **volume non épuisé** (150 iters ≈ 50×
sous le seuil 10k+ parties). La dégradation après iter 50 est cohérente avec dérive à faible
volume (collapse entropie, buffer FIFO périmé), pas un plafond prouvé.

**La bonne baseline pour AWR :** moyenne de `z` par batch, pas la value head (r_ood=0.47 dans
l'exponentielle = mirage in-sample risqué). La value head n'est à réintroduire que si r_ood
franchit ~0.65 de façon soutenue.

### Q3 — 0.547 insuffisant, surveiller la trajectoire

Théoriquement, la value info-state n'est pas biaisée par la déterminisation (≠ rollout de D6).
Mais seuil utile ≈ 0.7-0.9. À 0.47-0.55, porte fermée.

Critère décisif : la **trajectoire** de r_ood monte-t-elle ou plafonne-t-elle ? Le plateau
~0.5 observé est cohérent avec un plafond intrinsèque du jeu (l'outcome dépend de cartes
non vues). Re-tester MCTS uniquement si r_ood franchit proprement 0.65 après run à volume.

### L'expérience décisive recommandée

**Un run AWR à volume réel** (visant 10k+ parties) :
- Baseline simple (`z − z̄`, pas la value head)
- Entropie forte (0.15-0.20, contre le collapse)
- Pool ancré en dur : v8_250 + bons anciens checkpoints toujours présents (fictitious play)
- `parallel-games` pour volume
- **Keep-best par SPRT pentanomial** : banque les gains, ne les perd pas dans la dérive

Issue 1 : ça monte → le volume était la pièce manquante → continuer.
Issue 2 : plafonne/dégrade même à volume → plafond réel → pivot vers **famille CFR**
(regret counterfactuel — lignée poker : DeepStack, Libratus, ReBeL). CFR ne dépend ni
d'une value scalaire d'info-set ni de "search améliore la policy". C'est le bon outil pour
les jeux à information cachée si le plafond AWR est confirmé.

### Question fondamentale (pour décider la prochaine action)

> « C'est quoi l'objectif réel ? »
> - **Shipper un jeu jouable** → v8_250 suffit (3.6× le hasard, ~0.40 vs greedy fort).
>   Rendements décroissants : arrêter là est légitime.
> - **Repousser le plafond / recherche** → run à volume (tranche entre "volume suffit" et
>   "il faut CFR").

### Table croisée des checkpoints Fork 2f — révélation majeure

9 checkpoints × 60 parties appariées par matchup. Résultats du classement :

```
1. ckpt75  (Fork 2f iter 75)  score=0.559  ← meilleur
2. ckpt50                     score=0.527
3. ckpt25                     score=0.523
4. ckpt100                    score=0.521
5. ckpt125                    score=0.496
6. ckpt175                    score=0.474
7. v8_250  (champion actuel)  score=0.470  ← 7ème sur 9
8. ckpt150                    score=0.468
9. ckpt200                    score=0.462
```

**Fork 2 a bien amélioré le modèle en tête-à-tête.** Les checkpoints Fork 2f 25-100
battent tous v8_250 en head-to-head (wr ~0.55-0.60 contre lui). Le benchmark greedy masquait
cette amélioration car les deux modèles jouent à ~0.40 vs greedy — un adversaire trop faible
pour discriminer.

**Le pattern n'est pas du cycling — c'est de la régression progressive.** Après iter 75,
les checkpoints deviennent progressivement plus faibles (ckpt75=0.559 > ckpt200=0.462).
C'est du forgetting/dégradation, pas une non-transitivité pierre-feuille-ciseaux. La
matrice est quasi-triangulaire sur les early checkpoints.

**Classement croisé** (agrégé sur 8 adversaires) : ckpt75 domine les autres checkpoints Fork 2f.
**MAIS** la cellule individuelle ckpt75 vs v8_250 à 60 parties (wr=0.56) était une fluctuation —
confirmée à 300 parties : wr=0.433 ±0.058, t=−2.24 → **ckpt75 PERD contre v8_250**.

```
Confirmation ckpt75 vs v8_250 (300 parties appariées) :
  120W / 157L / 23D  wr=0.433 ±0.058  t=−2.24
  → v8_ckpt_250 reste le champion
```

**v8_ckpt_250 reste le seul champion prouvé.** Le ranking croisé montrait la dominance de
Fork 2f sur lui-même, pas sur le baseline. Le greedy benchmark ET la table croisée à 60
parties étaient tous les deux insuffisants pour confirmer un nouveau champion.

**Conséquence pour la mesure** : le benchmark greedy (policy_only vs greedy fixe) est un
mauvais thermomètre pour comparer des modèles proches. La table croisée head-to-head est
le seul outil fiable pour ranger les checkpoints entre eux.

---

## 24. Correction du greedy + re-mesure du sol (31/05/2026 soir)

### 24.1 Le greedy maximisait le mauvais objectif

Découverte en relisant `app/greedy_bot.py` : le greedy maximisait son **score absolu**
`scores[cp]`, pas l'**écart** avec l'adversaire. Il ignorait donc totalement l'effet de
ses coups sur l'autre joueur (poser chez l'adverse, basculer une famille où l'adverse est
exposé). C'était un *maximiseur égoïste myope*, pas un vrai joueur à 1 coup.

**Fix** : `greedy_action_main` / `greedy_action_target` maximisent désormais
`_score_margin = scores[cp] − max(scores des autres)`, cohérent avec la condition de victoire.

### 24.2 Le nouveau greedy est BEAUCOUP plus fort (sanity checks, 40 parties)

| Match | Résultat | Lecture |
|-------|----------|---------|
| nouveau greedy vs **ancien** greedy | 33–6–1 | le nouveau gagne **85%** |
| **random** vs nouveau greedy | 0–40 | écrase random **100%** (ancien : 88%) |
| nouveau vs nouveau (miroir) | 6–12–2 | équilibré, léger avantage 2e joueur |

Scores sains (34-30, 24-19, 22-7) → ce n'est pas un bug, c'est un adversaire réellement fort.

### 24.3 Re-mesure du sol — le résultat qui recadre tout le projet

`policy_only vs NOUVEAU greedy`, apparié, N=300 :

```
v8_ckpt_250 (best prouvé)   wr = 0.000  [0W/300L/0D]
champion actuel (model_2)   wr = 0.000  [0W/300L/0D]
```

**Le meilleur modèle du projet perd 300 parties sur 300 contre un greedy à 1 coup correct.**

Tous les "0.396", "0.45", "3.6× le hasard" du rapport étaient mesurés contre un greedy
**défectueux et faible**. Contre un greedy qui joue aussi à étouffer l'adversaire, la policy
entraînée est **totalement dominée**. Le recadrage de l'expert ("tu as déjà une IA correcte")
reposait sur cette baseline biaisée et **tombe**.

### 24.4 Conséquences stratégiques

1. **Le sol réel est 0.00, pas 0.40.** Énorme marge de progression, et un gradient honnête
   à remonter. Le projet n'est pas "fini" — il commençait à peine à être mesuré correctement.
2. **Le nouveau greedy est un adversaire d'entraînement idéal** : fort, déterministe, O(1),
   et le réseau a tout à apprendre de lui. Il devrait devenir un **opérateur de curriculum /
   membre du pool**, pas seulement un benchmark.
3. **La métrique winrate sature à 0.00 près du sol** (déterministe vs déterministe → 0/300).
   Pour voir une trajectoire, il faut une métrique continue : **écart de score moyen**
   (`scores[net] − scores[greedy]`), qui distingue "perd 34-30" de "perd 40-5".

### 24.5 Infrastructure ajoutée

- `app/greedy_bot.py` : `_score_margin`, greedy corrigé.
- `app/mcts_network.py` : **pool ancré** (`anchor_checkpoints`, `anchor_ratio`) — checkpoints
  toujours présents comme adversaires (fictitious play anti-dérive). CLI : `--anchor-checkpoints`,
  `--anchor-ratio`.
- `scripts/remeasure_greedy.py`, `scripts/trajectory_greedy.py` : mesure appariée vs nouveau greedy.

---

## 25. Diagnostic clonage (BC) — capacité vs signal (31/05/2026 nuit)

### 25.1 Protocole
`scripts/bc_greedy.py` : 600 parties greedy-vs-greedy → 18k états (main) + 9.7k (target).
Réseau **frais** (init aléatoire) entraîné en supervisé pur à imiter le greedy. Mesure :
train-accuracy (fit in-sample), policy_only winrate, et **écart de score moyen**.

### 25.2 Résultats

| epoch | train_acc | policy_only wr | écart score |
|-------|-----------|----------------|-------------|
| 0     | —         | 0.000          | −32.2       |
| 4     | 0.259     | 0.010          | −24.3       |
| 8     | 0.459     | 0.010          | −20.6       |
| 12    | **0.674** | 0.000          | −18.6       |

### 25.3 Verdict — double conclusion actionnable

1. **Ce n'est PAS un mur de représentation.** train_acc grimpe 0.20→0.67 sans plateau →
   le réseau *peut* représenter la majorité des décisions du greedy. La capacité existe.
2. **Le clonage pur ne gagne jamais** (0/100 à 67% de fit). Pathologie classique du
   behavioural cloning : **compounding errors / distribution shift**. Le réseau imite bien
   sur les états du greedy, mais en jouant lui-même il dérive hors-distribution.
3. **L'écart de score est la bonne métrique** près du sol : bouge proprement (−32→−18.6)
   là où le winrate reste à 0.

### 25.4 Cause racine reformulée
**Aucune méthode essayée (self-play MCTS, self-play AWR) n'a jamais entraîné le réseau
contre un adversaire fort.** Il n'a vu que lui-même ou ses vieux checkpoints (faibles) →
il plafonne à son propre niveau. Le greedy est le premier prof fort, stable, externe — et
la BC prouve que la capacité de monter existe.

### 25.5 Prochaine expérience décisive : DAgger
Le greedy est un **oracle interrogeable** (O(1)). DAgger (Ross et al. 2011) corrige
exactement le distribution shift : le réseau joue (visite ses propres états), le greedy
étiquette ces états, on agrège, on ré-entraîne, on répète. `scripts/dagger_greedy.py`.
**Critère** : l'écart de score remonte vers 0 et le winrate décolle au-dessus de 0 →
chemin viable. Sinon → le plafond de fit à ~0.67 mord (représentation insuffisante en
généralisation) → corriger le state vector (progression de partie).

---

## 26. DAgger + greedy équitable — la vérité sur le niveau réel (01/06/2026)

### 26.1 DAgger depuis l'oracle greedy (`scripts/dagger_greedy.py`)
Réseau frais, 8 rounds, 250 parties net-vs-greedy/round étiquetées par le greedy.

| round | train_acc | wr | écart |
|-------|-----------|-----|-------|
| 0 (BC) | 0.347 | 0.000 | −21.75 |
| 3      | 0.912 | 0.037 | −15.01 |
| 7      | 0.955 | 0.037 | −14.15 |

DAgger **casse le plancher 0.00** : écart −32 (random) → −21.75 (BC) → **−14**, winrate
0 → ~0.03. Mais **plateau** : train_acc plafonne à 0.955 et l'écart à ~−14.

### 26.2 Le greedy est info-privilégié — mais ce n'est PAS le levier
`_calcul_scores()` lit la vraie identité de toutes les cartes (espions cachés inclus). Le
greedy (`clone_determinized(randomize=False)`) voyait donc à travers les espions adverses.
Greedy ÉQUITABLE ajouté : `num_worlds≥1` → moyenne sur K déterminisations PIMC (`randomize=True`),
n'utilise que l'info légale.

**Mesure vs greedy équitable (PIMC K=8, apparié N=150) :**
```
random            wr=0.000  ecart=-27.95
v8_ckpt_250       wr=0.007  ecart=-22.54
champion model_2  wr=0.007  ecart=-23.25
AWR candidate     wr=0.000  ecart=-24.03
```

### 26.3 Conclusion qui recadre TOUT le projet
| greedy | v8_250 wr | ce qui change |
|--------|-----------|---------------|
| score absolu (triche)  | 0.396 | baseline historique |
| écart (triche)         | 0.000 | **−0.40 : l'objectif "écart"** |
| écart équitable (PIMC) | 0.007 | +0.007 : la triche ne compte presque pas |

**Le saut 0.396 → 0.00 vient de l'objectif "écart", pas de la triche.** Un greedy à 1 coup
qui joue l'écart est *genuinely fort*, et tous nos réseaux entraînés sont à peine meilleurs
que random contre lui (v8_250 ecart −22.5 vs random −28).

**Vérité du niveau réel : l'agent le plus fort du projet n'est aucun réseau — c'est le
greedy à 1 coup lui-même.** Tout l'effort AlphaZero/self-play a plafonné *sous* une heuristique
à 1 coup. DAgger (imitation du greedy) s'en rapproche (ecart −14) mais plafonne sous la parité.

### 26.4 Pourquoi le 0-ply n'atteint pas le 1-ply
Le greedy fait une recherche à 1 coup (il simule chaque coup). La policy_only fait du 0-ply
(elle choisit sans simuler). Une policy 0-ply qui imite un chercheur 1-ply traîne toujours :
elle doit *mémoriser* des conséquences que l'autre *calcule*. À 95.5% d'imitation, les 4.5%
d'erreurs (souvent sur des coups qui font basculer une famille = gros points) coûtent ~14 pts.

---

## 27. Feuille de route — bascule CFR (consensus expert, 01/06/2026)

**Verdict partagé : abandonner non pas "la recherche", mais "la recherche à value scalaire
par monde", structurellement non fondée ici. Le plafond r≈0.4 et l'échec d'ExIt sont le même
fait : la valeur d'un info-set dépend du reach (politique adverse), absent de l'entrée → cible
mal posée, erreur à plancher irréductible. Tout opérateur qui bootstrappe cette feuille hérite
du biais.**

### Trajectoire 2 joueurs (somme nulle sur l'écart)
1. **Deep CFR d'abord.** External-sampling MCCFR descend aux terminaux (gains réels, **pas de
   feuille bootstrappée**) → contourne la cause racine. Taille du jeu (branching ~12 + sous-jeu
   assassin ~17, horizon ~46, pioche) dans le domaine cible. **Vrai risque = variance**
   (horizon long × pioche) → VR-MCCFR / baselines, comparer external vs outcome sampling.
2. **Exploitabilité (NashConv)** comme métrique absolue, via best-response exact OpenSpiel.
   Remplace le winrate-vs-greedy et tout le combat de bruit de mesure.
3. **ReBeL en escalade conditionnelle** : si l'exploitabilité de Deep CFR plafonne, ou si on
   veut de la recherche au test. Sa value sur **public belief state** est une cible *bien posée*
   (la valeur EST fonction de la croyance) → le réseau apprend là où le scalaire plafonnait.
   Facilité Courtisans : un espion posé est inconnu de tous (variable commune-inconnue) → PBS
   plus simple qu'au poker. Coût : ingénierie PBS + subgame solving.

### Validation — instance réduite résoluble exactement
Construire une **mini-instance** (deck tronqué, 1 famille de moins, horizon court) où **CFR+
tabulaire** calcule Nash + exploitabilité *exacts*. Sert d'**oracle** : le Deep CFR doit y
converger. Sans cet oracle, impossible de distinguer exploitabilité résiduelle = algo /
abstraction / bug.

### Abstractions sûres (lossless)
- **Symétrie des 6 familles = automorphisme du jeu** → canonicaliser les labels (tri sur l'état
  public) = quotient *lossless*, ÷ jusqu'à 6! les info-sets, **ne déplace pas l'exploitabilité**
  (équilibre symétrique existe). À préférer à l'augmentation actuelle.
- Encodage par **comptes (famille, rôle) vus/restants** : l'ordre de pose/pioche est sans effet
  sur les gains → ~lossless. Tout bucketing au-delà = à valider contre l'exploitabilité relevée.
- **Vérifié (01/06)** : l'info privée (mes espions posés) est déjà préservée dans le state vector
  (`_knows_identity` via `proprietaire_idx == current_player`). Pas de fuite à corriger.

### Choix de payoff (à trancher consciemment — induit des équilibres différents)
- **Écart de score** `s_moi − s_adv` : récompense l'écrasement. C'est ce que fait le greedy.
- **Indicateur** `{+1, 0, −1}` (victoire/nul/défaite) : récompense le simple fait de gagner.
  *Souvent plus pertinent pour un adversaire de jeu desktop.*

### Rôle résiduel du greedy PIMC
- **LBR (local best response)** = borne inférieure cheap de NashConv (le greedy 1-coup *est*
  ~une LBR). Ancre de benchmark (il bat 99% des nets → barre à franchir).
- PAS de warm-start de stratégie (incompatible regret-matching). Éventuellement distribution
  d'échantillonnage MCCFR (avec correction d'importance).
- **Rappel** : que PIMC écrase les nets ne prouve pas qu'il est bon — il reste *exploitable*
  (suppose l'info parfaite dans les rollouts → ne bluffe pas). Sa qualité = SON exploitabilité.

### Outillage : OpenSpiel
Réimplémenter Courtisans en jeu OpenSpiel → Deep CFR, MCCFR, CFR+, **best-response/exploitabilité
natifs** (validés). Garder le moteur maison comme **simulateur rapide** et croiser-valider.
Réserve : Deep CFR OpenSpiel = implé de référence (analyse + 1er run), pas la plus perfo.

### Statut des docs
Les recommandations MCTS/ISMCTS→ExIt (recherche §16, trajectoires) sont **périmées pour le 2p**.
Conservées comme historique du résultat négatif. La voie 2p est désormais Deep CFR → exploitabilité → ReBeL conditionnel.

---

## 28. Bascule CFR — premier jalon : l'oracle fonctionne (01/06/2026)

**OpenSpiel installable** (wheel `open-spiel==1.6.15`, pas de build C++). CFR+/best-response/
exploitabilité validés (Kuhn → expl 0.003 en 50 iters).

**`cfr/courtisans_mini.py`** : Courtisans réduit comme jeu OpenSpiel (2 familles × 3 rôles
{Noble(2), Espion caché(1), Simple(1)}, 6 cartes, 2 joueurs, main 3, 1 manche, 12 actions
composites, payoff indicateur {+1,0,−1}). Info cachée réelle via espions face cachée.

**`cfr/solve_mini.py`** — résolution exacte (oracle) :
```
États 3141 | terminaux 2880 | info-sets P0=20  P1=216  (216 ≫ 20 = signature info cachée)
CFR+ iter   1 : exploitabilité 0.667
CFR+ iter  50 : 0.00144
CFR+ iter 600 : 0.000027   ← Nash quasi-exact
Équilibre P0 : MIXTE (4 actions à 0.25) → profondeur stratégique réelle
```

**Ce que ça débloque** : un Nash + une exploitabilité *exacts* sur une instance réelle de
Courtisans. C'est l'oracle de validation prescrit par l'expert : tout Deep CFR devra y converger.
La métrique de pilotage est désormais l'**exploitabilité absolue**, pas un winrate bruité.

**Prochaines briques** : (1) Deep CFR sur cette mini-instance, vérifier convergence vers
l'exploitabilité tabulaire ; (2) agrandir l'instance (familles, manches, assassins/gardes)
jusqu'à la limite du tabulaire ; (3) Deep CFR sur l'instance pleine ; (4) ReBeL si plafond.

---

## 29. Brique 1 — Deep CFR converge vers l'oracle (03/06/2026)

**Verdict : le pipeline neuronal est validé.** Deep CFR (External-Sampling MCCFR, implé
PyTorch d'OpenSpiel) converge vers l'exploitabilité tabulaire de l'oracle sur
`courtisans_mini`, sans plateau.

### Mise en place (pièges levés)
- `deep_cfr` est dans `open_spiel.python.pytorch` (PAS `.algorithms` comme l'indiquait la
  roadmap). Route pytorch retenue (torch déjà là) ; ajout de la dépendance **`dm-tree`**.
- Deep CFR exige un `information_state_tensor` : ajouté à `courtisans_mini.py`, encodage
  **lossless 53-dim** (perspective 2 + main multi-hot 6 + 3 slots board × 15). Vérifié
  injectif : **236 strings ↔ 236 tensors**, structure 20/216 identique à l'oracle.
- `solver.action_probabilities()` ne renormalise PAS sur les actions légales (réseau =
  `num_distinct_actions=20` logits, 12 légales aux décisions) → renormalisation obligatoire
  avant `nash_conv(..., use_cpp_br=False)`.

### Diagnostic décisif — le « plateau » était la tête policy, pas le process
Premiers runs : l'exploitabilité de la **tête policy** plafonne ~0.08–0.10 dès l'iter 20 et
reste **insensible aux traversals** (×5 → 0.097→0.080). Ce n'est donc PAS de la variance
d'échantillonnage. En reconstruisant la **policy moyenne MCCFR exacte** depuis le strategy
buffer (moyenne pondérée-par-itération par info-set, sans le réseau de policy ;
`cfr/diag_strategy_buffer.py`), l'exploitabilité tombe ~10× → **0.0087** (couverture 236/236).
→ Le plancher venait du **sous-apprentissage de la régression policy** (réseau réinitialisé +
ré-entraîné from scratch sur ~520k échantillons en trop peu de pas), pas du MCCFR.

### Courbe de convergence (métrique = policy MCCFR exacte ; 500 traversals/iter)
```
 iter |   CFR+ (oracle) |  Deep CFR
    5 |       0.109941  |  0.163596
   10 |       0.029967  |  0.059461
   20 |       0.008414  |  0.023227
   40 |       0.002167  |  0.014144
   80 |       0.000628  |  0.008690
  160 |       0.000218  |  0.005139
  200 |       0.000137  |  0.003742   ← CONVERGE
```
Deux droites parallèles en log-log (graphe `cfr/deep_cfr_mini.png`), Deep CFR ~½ décade
au-dessus de CFR+ mais **monotone décroissant vers 0** — la signature attendue (coût du
sampling + approximation), pas un plafond.

### Implication pour le scaling
À grande échelle, on ne peut pas matérialiser la policy buffer-exacte (ça annule l'intérêt de
Deep CFR) : **la tête policy est le livrable**, et son sous-apprentissage sera une source
d'exploitabilité résiduelle DISTINCTE de la qualité MCCFR. À soigner (réseau plus gros, bien
plus de pas, pas de réinit, batch plus grand) et à mesurer séparément.

### Fichiers
`cfr/deep_cfr_mini.py` (runner, hyperparams via env `DCFR_*`, métrique buffer-exacte par
défaut, `DCFR_MEASURE_NET=1` pour aussi mesurer le réseau), `cfr/diag_strategy_buffer.py`
(diagnostic buffer vs réseau), `cfr/plot_deep_cfr_mini.py` (graphe), logs `cfr/*.log`.

**Prochaine brique : agrandir l'instance** (plus de familles, 2+ manches avec pioche, puis
assassins/gardes) jusqu'à la limite du tabulaire, chaque palier validé par l'exploitabilité
tabulaire tant qu'elle reste calculable.

---

## 30. Brique 2.1a — passage à 3 familles (03/06/2026)

**Un seul changement** (garde-fou §6) : `courtisans_mini.py` généralisé sur `NUM_FAMILIES`
(2 → 3). Donne = couple (main P0, main P1), cartes restantes hors-jeu face cachée →
**rétrocompatible** (à 2 familles : C(6,3)×C(3,3)=20, reste 0 = v0). Astuce : on garde
`num_distinct_actions = len(_COMBOS) = 12` (actions joueur) avec `max_chance_outcomes=1680`
(donnes) — OpenSpiel l'accepte, donc la **sortie réseau reste à 12** (pas d'inflation par les
donnes-chance, qui aggraverait le goulot tête-policy).

### Instance 3 familles (9 cartes)
- États **263 761** | terminaux 241 920 | info-sets **P0=84, P1=12 400** | tenseur 65-dim.
- **Lossless** vérifié : 12 484 strings ↔ 12 484 tensors, sans collision.
- **Oracle CFR+** : exploitabilité **0.000089** à 300 iters, équilibre MIXTE (4 actions ~0.25)
  → l'instance agrandie reste résoluble exactement (oracle vivant).

### Deep CFR — la variance devient le levier contraignant
| traversals/iter | exploitabilité finale (buffer-exacte, couverture 12 484/12 484) |
|---|---|
| 500  (iter 200) | 0.060  — **plateau dès l'iter 40** |
| 2000 (iter 120) | **0.0137** — monotone, encore décroissant |

À 2 familles la policy MCCFR exacte atteignait 0.0037 ; à 3 familles avec 500 traversals elle
**plafonne à 0.060** — et cette fois le plateau est dans la **policy MCCFR exacte elle-même**
(tête policy exclue), donc dans la **qualité des regrets / la variance d'échantillonnage** sur
12 400 info-sets, PAS dans la régression policy. ×4 traversals (+ advantage-net 256×256)
casse le plateau (0.060 → 0.0137) → **confirmation empirique du risque variance anticipé par
l'expert** : il scale avec le nombre d'info-sets et devient le facteur limitant.

**Conséquences** : (1) la **canonicalisation par symétrie de familles** (brique 2.1b) divise
les info-sets par jusqu'à 3! = 6 → attaque directement ce goulot variance ; (2) au-delà, il
faudra une variante à **variance réduite** (ESCHER/DREAM dispo dans OpenSpiel-pytorch) ou de
gros budgets de traversals. Hyperparams réseau désormais via env `DCFR_ADV_NET`/`DCFR_POL_NET`,
`DCFR_SKIP_CFR=1` saute le recalcul de l'oracle.

**Sous-brique suivante : 2.1b — canonicalisation lossless par symétrie des familles** (faite, §31).

---

## 31. Brique 2.1b — canonicalisation lossless par symétrie des familles (03/06/2026)

Les NUM_FAMILIES familles sont interchangeables (automorphisme du jeu) → on quotiente les
info-sets en relabellant les familles dans l'ordre canonique. Toggle `COURTISANS_CANON`
(défaut on) pour comparer.

### Le point délicat : relabeler la string NE SUFFIT PAS
Canonicaliser `information_state_string` seule est **incorrect** : les 12 actions composites
indexent des positions dans la main triée ; sous un relabel de familles, « action a » désigne
une carte différente → fusionner deux nœuds symétriques en un info-set forcerait la même
stratégie sur des actions non-équivalentes (CFR faux, exploitabilité déplacée). **Il faut aussi
réinterpréter les actions dans l'ordre canonique de la main** (tri sur l'id relabelé). Preuve
de cohérence : pour deux nœuds d'un même orbite, la main relabelée-triée est identique → action
a désigne la même carte canonique → quotient correct. La perm canonique ne dépend que de la
**vue du joueur** (public + sa main) donc reste cohérente le long de l'arbre.

### Résultat — lossless confirmé
| | non-canon | canon |
|---|---|---|
| info-sets P0 / P1 | 84 / 12 400 | **20 / 2 108** (÷5.9, ≈ ÷3!=6) |
| états / terminaux / returns | — | **inchangés** (tree isomorphe) |
| oracle CFR+ (300 it.) | 0.000089 | 0.000122 |
| équilibre P0 | {4,7,8,11} ~0.25 | **{4,7,8,11} ~0.25 (identique)** |

L'oracle canon **suit** la trajectoire non-canon vers 0 (iter 1 identique à 1e-6 près ;
10/50/100 : 0.035/0.0025/0.00067 vs 0.032/0.0020/0.00057) **sans plancher d'abstraction**, et
retrouve le **même équilibre mixte** → quotient **lossless** prouvé.

### Bénéfice variance (le but)
À budget de traversals **égal** (500), Deep CFR sur le jeu canonicalisé écrase le non-canon :
| iter | non-canon @500 | canon @500 |
|---|---|---|
| 40 | 0.074 | 0.027 |
| 80 | 0.064 | 0.021 |
| 200 | 0.060 (plateau) | **0.019** |
~3× meilleur — canon@500 (0.019) approche le non-canon@2000 (0.0137) pour **¼ du budget**. Le
quotient ÷5.9 réduit directement la variance par info-set, comme prévu.

### Implémentation
Brute-force `min` sur les permutations de familles, **mémoïsé** (cache module-level indexé par
une signature immuable de la vue → fonction pure, jamais périmé même au clone d'état). Indispensable
car O(720) à 6 familles. **Limite connue** : à 6 familles le brute-force sur 720 perms, même caché,
sera lourd → prévoir une canonicalisation directe (tri) plutôt qu'énumérative pour le jeu plein.

**Prochaine sous-brique** : 2+ manches avec pioche/draw (introduit l'horizon long → c'est là que
les variantes à variance réduite type ESCHER/DREAM deviendront pertinentes).

---

## 32. Brique 2.1c — assassins + gardes : le plateau était l'advantage-net sous-entraîné (10/06/2026)

**Un seul changement** : ajout du sous-jeu de ciblage. `cfr/courtisans_assassin.py` = 2 familles
× 4 rôles {Noble(2), Espion(caché,1), Garde(1), Assassin(1)} = 10 cartes (le Neutre, redondant,
est retiré pour garder l'oracle vivant). Un assassin posé tue immédiatement une carte de sa zone
(hors Gardes, hors lui-même) → **2ᵉ phase de décision** (`phase="target"`), actions de ciblage
réutilisant les ids 0..k-1 < 12, assassins multiples résolus séquentiellement.

### Instance
- États **123 921** | terminaux 80 640 | info-sets **P0=56, P1=33 240** | tenseur 138-dim
  (blocs board étendus : flag `dead` + zone-clé de l'assassin en résolution).
- **Oracle CFR+** : exploitabilité **0.000093** à 300 iters — le sous-jeu de ciblage reste
  résoluble exactement. Équilibre MIXTE (6 actions, {8,11}≈0.19, {1,2}≈0.17).

### Le plateau à 0.031 — et le diagnostic
Deep CFR (policy MCCFR buffer-exacte) **plafonnait à ~0.031-0.034** insensible aux leviers déjà
connus : traversals ×3 (1000→3000 : 0.0315→0.0315), policy-net/steps ×2 (sans objet — la
métrique buffer-exacte exclut la tête policy). Nouveau symptôme : la **couverture du strategy
buffer décroissait** (21.3k → 15.8k info-sets), suggérant l'éviction reservoir (~18.6k
échantillons/iter → 3.7M sur 200 iters dans un buffer de 1e6, ~73 % jetés).

Grille à un changement par run (traversals=1000 ; les runs ont été interrompus à l'iter 80
par une mise en veille du PC — suffisant, le verdict est sans ambiguïté à l'iter 80) :

| run | changement | expl. @ 80 |
|---|---|---|
| baseline (@200 : 0.0314) | — | 0.0337 |
| E1 | memory 1e6 → 3e6 | 0.0338 |
| E2 | advantage-net 128² → 256² | 0.0219 |
| E3 | **advantage steps 500 → 1500** | **0.0112** |

→ **L'éviction n'était PAS le goulot** (E1 = baseline au point près : la politique moyenne
pondérée-par-itération est robuste au sous-échantillonnage uniforme du stream). Le goulot était
le **réseau d'avantage sous-entraîné** : 500 steps ne suffisent plus à régresser les regrets de
33k info-sets, or c'est lui qui pilote le regret-matching des traversals — les stratégies
échantillonnées elles-mêmes étaient mauvaises, d'où un plateau que ni les traversals ni la tête
policy ne pouvaient casser. (Même famille de piège que le « plateau » de la brique 1 — qui était
la tête policy sous-entraînée : à chaque agrandissement d'instance, re-questionner le budget
d'entraînement des DEUX réseaux.)

### Confirmation — brique validée
| run | expl. @ 80 | expl. @ 160 |
|---|---|---|
| **combo** 1500 steps + 256² (s42) | 0.0075 | **0.0063** |
| 1500 steps, 128² (seed 123) | 0.0111 | 0.0096 |

Le gain est **robuste à la seed** (0.0112 s42 ≈ 0.0111 s123 @ 80) et les deux leviers
advantage **se cumulent** (combo 0.0063, ~5× sous le plateau, courbe encore décroissante,
largement sous le seuil 0.02). Courbes : `cfr/deep_cfr_assassin_compare.png`.
**Brique 2.1c validée** : Deep CFR converge vers l'oracle sur l'instance à sous-jeu de
ciblage (oracle 0.000093, Deep CFR 0.0063 — même ordre de qualité que les briques 1/2.1a-b
rapporté au nombre d'info-sets).

### Leçon générique pour le scaling
Le levier variance (traversals, canon §31) et le levier **fit de l'advantage-net** (steps,
capacité) sont **indépendants et tous deux bloquants** ; le second ne se voit PAS dans la
couverture du buffer mais dans un plateau précoce de la courbe buffer-exacte. Diagnostic ajouté
au script : `échantillons gardés/stream` à chaque checkpoint (`deep_cfr_mini.py`), grille via
env `DCFR_ADV_STEPS`, `DCFR_ADV_NET`, `DCFR_MEM`, `DCFR_SEED`, `DCFR_GAME`.
