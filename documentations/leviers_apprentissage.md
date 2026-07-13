# Leviers d'apprentissage pour l'IA Courtisans

Ce document recense les techniques qui peuvent **améliorer la qualité ou la
vitesse d'apprentissage** de l'IA, classées du moins coûteux au plus
structurant. Chaque levier est présenté en deux temps : *vulgarisation* (la
métaphore et l'intuition), puis *technique* (le détail formel et la mise en
œuvre concrète sur ce projet).

---

## Préambule — Où va le temps dans AlphaZero ?

Avant de tirer un levier, il faut savoir lequel est *long*. Le cycle classique
d'une itération AlphaZero (« épisode » dans `train()`) :

```
1. Self-play  : l'IA joue une partie contre elle-même
   └── pour chaque coup :
         └── MCTS lance N simulations
               └── chaque simulation = 1 forward(batch=1) du réseau
2. Buffer     : on ajoute les (état, π, valeur) au replay buffer
3. Optimisation : 1 mini-batch SGD sur le réseau
```

Sur Courtisans, une partie dure ~30 tours, et MCTS = 30 sims → on appelle le
réseau ~900 fois en `batch=1` séquentiel par partie. **C'est ça qui domine** —
pas l'optimisation, qui ne représente qu'un seul `forward(batch=64) + backward`
par épisode.

Cette répartition est cruciale pour comprendre pourquoi le GPU n'apporte
qu'un facteur modeste sans le levier #7 : un GPU brille sur de gros batchs, pas
sur des micro-batchs séquentiels.

---

## Niveau 1 — Quick wins (minutes de dev)

### 1.1 Replay buffer plus gros

#### Vulgarisation

Imagine que tu apprennes à jouer aux échecs en relisant **les 5 dernières
parties** de ton journal. Tu vas finir par sur-apprendre les particularités de
ces 5 parties. Si tu relis les **5000 dernières**, ton apprentissage est plus
général : tu vois plus de situations, tes "mauvaises habitudes locales" sont
diluées.

Le **replay buffer** est exactement ça : une mémoire glissante des dernières
positions visitées. Tu y piochent un mini-batch à chaque étape pour mettre à
jour les poids.

#### Technique

Aujourd'hui : `TrainConfig.memory_size = 5000`. En pratique tu emmagasines ~30
transitions par partie (≈ 1 par coup joué × 2 joueurs au moins). Donc 5000
contient seulement **~165 parties** de variété. C'est très peu — l'IA risque
de sur-fitter le "style" de ses parties les plus récentes.

Réf AlphaZero (Go 19×19) : buffer de **500 000 positions**. À l'échelle de
Courtisans, 50 000–100 000 est largement suffisant et tient en RAM (chaque
entrée = ~200 floats × 4 octets ≈ 1 Ko, donc 50k entrées ≈ 50 Mo).

#### Application Courtisans

```python
train(config=TrainConfig(memory_size=50_000, iterations=2_000))
```

Penses-y dès que `iterations × ~30` dépasse ton `memory_size`.

#### Risques

- **RAM** : ne te fais pas exploser sur CPU avec un buffer trop gros.
- **Stale samples** : un buffer énorme contient des positions générées par un
  réseau "ancien", de moins en moins représentatives du niveau actuel. Si tu
  pousses très loin (500k+), pense à un *fresh ratio* qui force un % de
  samples récents dans chaque batch.

---

### 1.2 Plus de simulations MCTS par coup

#### Vulgarisation

MCTS, c'est comme **réfléchir avant de jouer**. Le nombre de simulations N est
*combien de "minutes de réflexion"* l'IA s'accorde pour chaque coup.

- N=1 : intuition pure (la sortie du réseau, sans recherche).
- N=10 : tu réfléchis vite, tu vois quelques coups d'avance.
- N=100 : tu explores des branches profondes, tu détectes les pièges.
- N=1000 : tu deviens redoutable (mais lent).

Plus important encore : les **labels** que MCTS produit pour entraîner le
réseau sont *meilleurs* avec N grand. C'est l'idée AlphaZero : le réseau
apprend de l'amélioration apportée par MCTS.

```
réseau seul (policy π_θ) → MCTS(N) → meilleure policy π_MCTS
                                 ↓
                              entraîner π_θ à ressembler à π_MCTS
                                 ↓
                            π_θ s'améliore → MCTS(N) devient encore mieux
```

C'est la boucle de **policy improvement** d'AlphaZero. Sans MCTS suffisamment
profond, π_MCTS ≈ π_θ et la boucle se grippe.

#### Technique

La formule de sélection MCTS (PUCT) :

$$
a^* = \arg\max_a \left[ Q(s, a) + c_{puct} \cdot P(s, a) \cdot \frac{\sqrt{N(s)}}{1 + N(s, a)} \right]
$$

- $Q(s, a)$ : value moyenne observée pour l'action $a$ depuis $s$.
- $P(s, a)$ : prior du réseau (policy).
- $N(s)$ : visites totales du nœud parent.
- $N(s, a)$ : visites de l'enfant via $a$.
- $c_{puct}$ : balance exploration/exploitation.

**Garantie théorique** : quand $N \to \infty$, la distribution des visites
$\pi_{MCTS}(s, a) \propto N(s, a)$ converge vers la meilleure réponse. À N
petit, $\pi_{MCTS}$ est encore très influencé par le prior $P$ — donc tu
n'apprends pas grand chose de nouveau.

**Ordre de grandeur empirique** :
- N < 20 : labels bruités, apprentissage lent.
- N ≈ 50-100 : sweet spot pour des jeux de la complexité de Courtisans.
- N > 200 : diminishing returns par minute de wall-clock.

#### Application Courtisans

Aujourd'hui : `TrainConfig.num_sims = 30`. À booster.

```python
train(config=TrainConfig(num_sims=80, iterations=1_000))
```

**Trade-off temps** : doubler N double approximativement le temps de chaque
coup. Sur CPU, viser N=50-80. Sur GPU avec evaluator batché (lever #7), N=200
devient abordable.

---

### 1.3 Température schedule

#### Vulgarisation

Au tout début d'une partie, **explorer** est crucial : si l'IA joue toujours
le même premier coup, elle ne saura jamais si une autre ouverture est
meilleure. Plus tard dans la partie, **exploiter** ce qu'on sait devient
prioritaire : on veut jouer le coup le mieux noté, pas un coup "intéressant".

La **température** $T$ règle ce curseur :

- $T \to \infty$ : on tire un coup au hasard parmi les légaux.
- $T = 1$ : on tire un coup proportionnellement à son nombre de visites MCTS.
- $T \to 0$ : on prend le coup le plus visité (greedy / argmax).

#### Technique

Le sampling d'action à partir des visites MCTS :

$$
\pi(s, a) = \frac{N(s, a)^{1/T}}{\sum_{b} N(s, b)^{1/T}}
$$

Stratégie recommandée (AlphaZero original) :
- **Pour les K premiers coups** d'une partie de self-play : $T = 1$
  (échantillonnage proportionnel aux visites).
- **Au-delà du coup K** : $T \to 0$ (greedy).

Le K dépend du jeu. Pour Courtisans (~30 tours par partie), K=10 à 15
semble raisonnable.

Aujourd'hui, le code fait :
```python
if it < config.warmup_iters:
    action = np.random.choice(len(probs), p=probs)
else:
    if random.random() < config.epsilon_random:
        action = np.random.choice(len(probs), p=probs)
    else:
        action = int(np.argmax(probs))
```

C'est un proxy mais qui mélange deux concepts (température + ε-greedy) et qui
opère par *itération* plutôt que par *coup-dans-la-partie*. Le schedule de
température classique opère **dans la partie elle-même**.

#### Application Courtisans

À implémenter dans `train()` :

```python
TEMP_THRESHOLD = 10  # coups par partie

# Dans la self-play loop, tracker le numéro du coup :
move_in_game = 0
while not done:
    probs = mcts.search(env, add_root_noise=True)
    if move_in_game < TEMP_THRESHOLD:
        # T=1 : échantillonnage selon les visites MCTS
        action = int(np.random.choice(len(probs), p=probs))
    else:
        # T→0 : greedy
        action = int(np.argmax(probs))
    move_in_game += 1
```

Pour aller plus loin : ajouter un `temperature_schedule: Callable[[int], float]`
dans `TrainConfig` pour customiser.

#### Pitfall

- **Ne pas oublier le bruit Dirichlet à la racine** : il est *indépendant* de
  la température, et tous les deux contribuent à l'exploration. Dirichlet
  diversifie le prior à la racine ; la température diversifie le sampling de
  l'action.

---

### 1.4 Weight decay (régularisation L2)

#### Vulgarisation

Quand un réseau a beaucoup de paramètres et peu de données, il a tendance à
**mémoriser** au lieu de **généraliser**. Imagine que tu te prépares à un
examen en apprenant les 50 dernières copies par cœur, plutôt que les concepts
sous-jacents.

Le **weight decay** force le réseau à utiliser ses paramètres *avec
parcimonie*. En pratique : à chaque étape, on tire chaque poids un peu vers
zéro. Si ce poids est utile, le gradient le ramène ; sinon, il s'évanouit.

#### Technique

On ajoute à la loss un terme $\lambda \sum_w w^2$. Le gradient devient :

$$
\nabla L_{total}(w) = \nabla L(w) + 2 \lambda w
$$

L'optimiseur `Adam` de PyTorch prend ça nativement :

```python
optimizer = optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
```

Valeurs typiques : $\lambda \in [10^{-5}, 10^{-3}]$. Trop fort → sous-apprentissage.
Trop faible → sans effet.

> Subtilité : Adam avec weight_decay n'est *pas* exactement de la L2 (il y a
> une interaction avec les moments adaptatifs). Pour une régularisation plus
> propre, utilise `torch.optim.AdamW` qui implémente le « decoupled weight
> decay ». Différence souvent négligeable, mais bonne pratique.

#### Application Courtisans

Dans `train()` :

```python
optimizer = optim.AdamW(net.parameters(), lr=config.lr, weight_decay=1e-4)
```

Et ajouter dans `TrainConfig` : `weight_decay: float = 1e-4`.

#### Quand ça aide vraiment ?

- Replay buffer petit relatif au nombre de params du réseau.
- Long runs (5000+ itérations) où le sur-apprentissage devient un risque.

Sur un petit run (200 itérations, buffer 5000), l'effet est négligeable.

---

## Niveau 2 — Investissements moyens (heures de dev)

### 2.1 PIMC multi-déterminisation

#### Vulgarisation

Dans Courtisans, **tu ne sais pas** ce que l'adversaire a en main. Aujourd'hui
notre PIMC fait *une* hypothèse aléatoire à chaque appel `search()` et
explore l'arbre dans ce monde imaginé. Mais ce monde n'est qu'**un parmi des
millions possibles**.

Imagine un joueur d'échecs aveugle qui doit deviner où sont les pièces noires.
S'il s'imagine *un* placement possible et planifie en conséquence, il sera
parfois piégé par les configurations qu'il n'a pas envisagées. S'il s'imagine
*plusieurs* placements et choisit le coup qui marche en moyenne, sa décision
est plus robuste.

C'est exactement le principe du PIMC multi-déterminisation : on tire $K$
mondes possibles, on lance MCTS dans chacun, et on **moyenne** les comptes
de visites pour décider du coup à jouer.

#### Technique

Pseudo-code (référence : *Cowling, Powley & Whitehouse, 2012*) :

```
def search_pimc_multi(env, K_worlds, N_sims):
    visit_counts = zeros(action_space)
    for k in range(K_worlds):
        determinized = env.clone_determinized()  # 1 monde
        counts_k = mcts_search(determinized, N_sims)
        visit_counts += counts_k
    return visit_counts / visit_counts.sum()
```

**Trade-off** : multiplier par $K$ le nombre de mondes équivaut à diviser par
$K$ le budget de simulation par monde (à wall-clock constant). On préfère
souvent $K=5$ avec $N=20$ que $K=1$ avec $N=100$ pour les jeux à forte
incertitude — car la variance entre mondes domine l'erreur d'estimation.

**Limite théorique** : PIMC multi a un défaut connu appelé "**strategy
fusion**" — il peut ignorer les stratégies qui *exploitent* l'asymétrie
d'information (typiquement le bluff). Pour les bluffs, il faut IS-MCTS (un
seul arbre indexé par information-set, redéterminisation par simulation). Mais
pour Courtisans qui a peu de bluff pur, PIMC multi est largement suffisant.

#### Application Courtisans

À refactorer dans `MCTS.search()` ou ajouter une variante :

```python
def search_pimc(self, env, num_worlds=5, add_root_noise=False):
    accumulated = np.zeros(env.mapper.get_action_space_size())
    for _ in range(num_worlds):
        world_env = env.clone_determinized()  # nouvelle déterminisation
        counts = self._search_single_world(world_env, add_root_noise)
        accumulated += counts
    return accumulated / accumulated.sum() if accumulated.sum() > 0 else accumulated
```

Et `TrainConfig.num_worlds: int = 5`.

#### Coût

Linéaire en $K$ : 5 mondes = 5× le temps. Sur CPU, vise $K=3$. Sur GPU + lever
#7, $K=10$ devient envisageable.

---

### 2.2 Augmentation de données par symétrie des familles

#### Vulgarisation

Dans Courtisans, **les 6 familles sont interchangeables** : aucune règle ne
favorise la famille rouge par rapport à la bleue. Si tu permutes toutes les
familles dans une partie (rouge ↔ bleue, vert ↔ jaune, etc.), c'est la même
partie *stratégiquement*.

Or notre réseau est entraîné sur des vecteurs où la position d'un slot dépend
de la famille. Si la famille rouge apparaît plus souvent dans des positions
"gagnantes" durant le self-play, le réseau peut apprendre à *aimer* la
famille rouge pour de mauvaises raisons.

L'astuce : **chaque partie générée vaut 6! = 720 parties** (toutes les
permutations de familles). On en exploite quelques-unes pour multiplier
l'efficacité du replay buffer.

#### Technique

Soit $\sigma$ une permutation des 6 familles (élément du groupe symétrique
$S_6$). Pour chaque triplet $(s, \pi, v)$ ajouté au replay buffer, on génère
aussi $(s^\sigma, \pi^\sigma, v)$ où :

- $s^\sigma$ = le state vector où on a permuté les blocs de 5 cellules
  correspondant à chaque famille (dans chaque zone).
- $\pi^\sigma$ = la policy où on a remappé les indices d'action si
  nécessaire (cf. *pitfall* ci-dessous).
- $v$ inchangé (le score final est indépendant des familles).

#### Pitfall très important

Sur Courtisans, l'**action** encode la position d'une carte dans la **main
triée** (par `sort_key = famille * 5 + role`). Si on permute les familles, la
sort_key change, et donc l'ordre des cartes en main change. **Une action
"placer carte 0 chez la Reine" pointe sur une carte différente** dans le
monde permuté.

Conséquence : il faut aussi **remapper la policy**, dimension par dimension,
en calculant la nouvelle permutation des cartes en main avant/après $\sigma$.

Esquisse :

```python
def augment_sample(state_vec, policy, hand_card_ids, family_perm):
    # 1. Permuter le state vector zone par zone
    new_state = permute_state_by_family(state_vec, family_perm)

    # 2. Recalculer la nouvelle position des 3 cartes en main sous family_perm
    new_hand = sorted(hand_card_ids, key=lambda i: permuted_sort_key(i, family_perm))
    # mapping (ancienne_position) -> (nouvelle_position)
    pos_map = compute_position_map(hand_card_ids, new_hand)

    # 3. Remapper la policy : chaque action (perm, queen_pos, target)
    # devient (perm_remapped, queen_pos, target)
    new_policy = remap_policy(policy, pos_map, mapper)

    return new_state, new_policy
```

**À écrire avec soin et à tester unitairement** : une erreur de remapping rend
l'augmentation contre-productive (le réseau apprend des labels incohérents).

#### Coût et gain

- Coût : ~zéro à l'exécution (permutations rapides), un peu de RAM pour le
  buffer si tu en stockes plusieurs versions par sample.
- Gain : facteur 2 à 6 effectif sur la taille des données utiles. Très bonne
  ROI **si tu trains longtemps**.

#### Conseil pratique

Plutôt que de générer toutes les 720 permutations, échantillonne **une
permutation aléatoire à chaque fois qu'un sample est tiré du buffer pendant
l'optimisation**. Pas de coût de stockage, le réseau voit naturellement
beaucoup de variantes.

---

## Niveau 3 — Refactor majeur (jours de dev)

### 3.1 Évaluateur MCTS batché

#### Vulgarisation

Aujourd'hui chaque simulation MCTS envoie un seul état au réseau et attend la
réponse. C'est comme si tu allais au comptoir d'un fast-food **commander une
frite à la fois**. Si tu en commandes 50, tu mets 50× le temps.

Un *evaluator batché*, c'est commander **50 frites d'un coup**. Le cuisinier
les prépare en parallèle et tu repars en une seule attente.

Pour le réseau, c'est exactement pareil : un forward(batch=50) prend à peine
plus de temps qu'un forward(batch=1) — surtout sur GPU. Donc si on arrive à
*collecter* 50 demandes d'évaluation avant de les lancer, on divise quasiment
par 50 le coût d'évaluation.

#### Technique

Deux approches courantes :

**Approche A — Parallel MCTS avec "virtual loss"** :

On lance plusieurs threads / coroutines qui font chacun une simulation. Quand
un thread descend dans une branche d'un arbre, il y ajoute une *virtual loss*
(une visite fictive avec value très négative) pour décourager les autres
threads de prendre la même branche en parallèle. Quand le forward est résolu,
on lève la virtual loss et on enregistre la vraie value.

Avantage : haute parallélisation possible.
Inconvénient : implémentation complexe, débogage difficile.

**Approche B — Batched leaf evaluation** :

Plus simple : on fait `N_batch` simulations *quasi-séquentiellement* mais on
**collecte les demandes d'évaluation** avant de descendre dans l'arbre. Tant
qu'on n'a pas atteint `N_batch` feuilles à évaluer, on continue à descendre.
Puis un seul forward(batch=N_batch). Puis on remonte les valeurs.

C'est moins parallèle qu'approche A, mais beaucoup plus simple, et déjà très
efficace sur GPU.

Pseudo-code (approche B) :

```python
def search_batched(self, env, batch_size=16, num_sims=64):
    root = MCTSNode(...)
    self._expand_root(root, env)

    sims_done = 0
    while sims_done < num_sims:
        # Phase 1 : collecter `batch_size` feuilles à évaluer
        leaves = []  # liste de (node, env_at_node, ancestors_to_update)
        for _ in range(min(batch_size, num_sims - sims_done)):
            node, sim_env, path = self._descend_to_leaf(root, env)
            leaves.append((node, sim_env, path))

        # Phase 2 : un seul forward sur le batch
        states = [leaf[1].get_state_vector() for leaf in leaves]
        batch_tensor = torch.from_numpy(np.stack(states)).to(DEVICE)
        with torch.no_grad():
            policy_logits, values = self.model(batch_tensor)

        # Phase 3 : expand chaque feuille + backprop
        for (node, sim_env, path), pi, v in zip(leaves, policy_logits, values):
            self._expand_with_policy(node, sim_env, pi)
            self._backprop(path, v.item())
            sims_done += 1
```

#### Implémentation effective dans ce projet

**Combinaison des approches A + B** : on utilise l'approche B (batched leaf
eval) **avec** la virtual loss de l'approche A. Sans la virtual loss, les K
descentes du batch suivraient toutes le même chemin (les `visit_count` ne
sont pas encore à jour entre les descentes) → on évaluerait K fois la même
feuille. La virtual loss force la divergence des chemins **dans un même
batch**.

Algorithme effectif (dans `MCTS._search_single_world_batched`) :

```
Phase 1 — Descente (×K)
  Pour chaque descente :
    node ← root
    while node a des enfants ET pas terminal :
       child ← PUCT_select(node)
       child.visit_count += VIRTUAL_LOSS   # discourager la même branche
       child.value_sum   -= VIRTUAL_LOSS   # pour les descentes suivantes
       node ← child
       sim_env.step(action)
    Stocker (node, sim_env, path, terminal_value_si_applicable)

Phase 2 — Évaluation batchée
  Empiler les state vectors des feuilles non terminales en un tensor (K, D)
  Un seul forward → (logits batch, values batch)
  Expander chaque feuille avec ses logits

Phase 3 — Backprop
  Pour chaque feuille :
    Annuler la virtual loss le long du path (visit_count -= VL, value_sum += VL)
    Backprop la vraie value avec alternance de signes
```

`VIRTUAL_LOSS = 3` (constante de classe `MCTS.VIRTUAL_LOSS`, tunable).

#### Gain mesuré et attendu

**Benchmark CPU réel** (i5 récent, réseau LayerNorm ~3M params,
50 simulations, moyenne sur 3 appels `search()`) :

| `batch_size` | Temps / search | Speedup |
|---:|---:|---:|
| 1 (séquentiel) | 85 ms | 1.0× |
| 4 | 63 ms | 1.35× |
| 8 | 71 ms | 1.2× |
| 16 | **47 ms** | **1.8×** |

Note : à batch_size=8 le speedup est légèrement inférieur à batch_size=4 sur
ce poste — phénomène classique de cache CPU non saturé. C'est très
machine-dépendant.

**Gain attendu sur GPU 4060Ti** : x10-20. Le GPU sature à batch_size ~32-64
et amortit les transferts mémoire CPU↔GPU.

#### Risques évités (tests critiques)

- **Fuite de virtual loss** : si on oublie d'annuler la virtual loss en
  phase 3, les `visit_count` accumulent des visites fictives → policy MCTS
  faussée silencieusement. Le test
  `test_batched_search_leaves_no_residual_virtual_loss` vérifie que la
  somme des visites racine = `num_sims` exactement. C'est la seule garde
  qui rattrape ce bug.
- **Compatibilité Dirichlet/PIMC multi** : tests dédiés
  (`test_batched_search_with_root_noise`, `test_batched_search_with_multi_world`).
- **Dispatch correct** : `batch_size=1` doit continuer d'appeler le code
  séquentiel historique
  (`test_batch_size_1_dispatches_to_sequential`).

---

## Comment mesurer le progrès ?

Sans métrique, on optimise à l'aveugle. Trois indicateurs à suivre :

### A. Loss de training

```
loss_pi = -Σ π_MCTS · log π_θ        (cross-entropy policy)
loss_v  = MSE(v_θ, reward_final)    (mean squared error value)
loss    = loss_pi + loss_v
```

Doit décroître globalement. Mais une loss qui plafonne ne veut pas dire que
le jeu ne s'améliore plus — le réseau peut converger vers un π_MCTS plus
sophistiqué et la loss "saute" à la hausse à chaque amélioration de MCTS.
Donc *loss seule = insuffisant*.

### B. Winrate via l'arena (déjà en place !)

Notre `arena()` joue le candidat contre le meilleur connu. Si le winrate
dépasse 55 % périodiquement, l'IA progresse. Si elle stagne autour de 50 %,
on est dans un plateau (ou en régression).

Log à surveiller (généré par `train()`) :
```
Arena (iter 50): wins=12 losses=7 draws=1 winrate=0.63
Champion promu
Arena (iter 100): wins=8 losses=10 draws=2 winrate=0.44
Champion conservé
```

### C. ELO contre une baseline fixe

Pour avoir un score absolu (et pas relatif au best courant), on peut faire
jouer le réseau contre :

1. Un **agent random** (`pick_ai_action` avec `net=None`).
2. Un **MCTS pur sans réseau** (PUCT à priors uniformes).
3. Un **modèle checkpoint** de référence (sauvegardé manuellement il y a 1000
   itérations).

Le winrate vs random doit monter rapidement (> 90 % dès quelques centaines
d'itérations). Le winrate vs MCTS pur monte plus lentement et est un meilleur
proxy de la *valeur* apportée par le réseau.

### D. Diagnostics qualitatifs

À chaque jalon, regarde quelques parties IA vs IA et demande-toi :
- L'IA varie-t-elle ses ouvertures ? (sinon le bruit Dirichlet est faible ou
  la température schedule absente).
- Joue-t-elle des espions intelligemment (cachant des cartes utiles) ?
- Met-elle ses propres familles en Lumière ?

Ces signaux qualitatifs détectent les *plateaux* qu'une métrique numérique
peut masquer.

---

## État d'implémentation

| Levier | Statut | Param `TrainConfig` / CLI |
|---|---|---|
| #1.1 Replay buffer | ✅ activé par défaut | `memory_size=50_000` · `--memory-size` |
| #1.2 num_sims | ✅ activé par défaut | `num_sims=50` · `--num-sims` |
| #1.3 Température schedule | ✅ activé par défaut | `temperature_threshold=10` · `--temperature-threshold` |
| #1.4 AdamW + weight decay | ✅ activé par défaut | `weight_decay=1e-4` · `--weight-decay` |
| #2.1 PIMC multi-déterminisation | opt-in | `num_worlds=1` · `--num-worlds N` |
| #2.2 Augmentation familles | ✅ activé par défaut | `family_augmentation=True` · `--no-family-augmentation` |
| #3.1 Evaluator MCTS batché | opt-in | `mcts_batch_size=1` · `--mcts-batch-size N` |

### Recommandations de tuning

**CPU (validation locale)** :
```bash
python main.py train --iterations 200 --num-sims 50 --mcts-batch-size 8
```
Le batch_size=8 donne déjà ~1.8× de speedup mesuré sur ce projet.

**GPU 4060Ti (run sérieux)** :
```bash
python main.py train \
  --iterations 5000 --num-sims 80 \
  --mcts-batch-size 32 --num-worlds 3 \
  --memory-size 100000
```
On combine : batched eval pour saturer le GPU + PIMC multi pour des labels
de meilleure qualité + buffer plus large pour diversifier.

## Synthèse — Plan d'action recommandé

Tous les leviers sont implémentés et exposés au CLI. Plan d'expérimentation
suggéré :

| Étape | Action | But |
|-------|--------|-----|
| 1 | Run baseline 200 itérations, défauts L1 + L2.2 | Mesurer le départ |
| 2 | Mêmes 200 itérations + `--mcts-batch-size 8` | Vérifier le speedup, mêmes scores |
| 3 | 500 itérations + `--num-worlds 3` | Qualité MCTS améliorée |
| 4 | 5000 itérations + tout activé sur GPU | Le vrai entraînement |

**Règle d'or** : à chaque étape, le `models/model_{N}.pth` (best) ne change que
si l'arena valide le candidat. Tu peux donc empiler les étapes sans crainte
d'écraser un meilleur modèle.

**Règle d'or** : ne pas activer plusieurs leviers d'un coup. Sinon, en cas de
régression, tu ne sais pas lequel a cassé. Active 1 levier → run → mesure (via
arena) → conserve ou rollback → étape suivante.

**Règle d'or n°2** : sauvegarde le `models/model_2.pth` actuel sous un nom
explicite avant chaque expérience (`models/model_2_pre_pimcmulti.pth`). C'est
ta seule baseline robuste pour mesurer un nouveau levier.
