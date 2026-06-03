# Analyse critique du run d'entraînement v1 — Stratégie d'amélioration

> Run de référence : 1500 itérations, 80 sims, batch=1, worlds=1, arena=20 parties  
> Matériel : RTX 4060 Ti 16 Go, Ryzen 5 9600X, WSL2 — durée réelle : ~3h35

---

## 1. Diagnostic — ce qu'on a observé

### 1.1 Courbe de loss

| Phase | Itérations | Loss | Interprétation |
|---|---|---|---|
| Chute rapide | 0 → 150 | 5.55 → 3.08 | Le réseau absorbe les patterns de base |
| Plateau bruité | 150 → 1500 | 3.08 → 3.01 | Oscillations ±0.3, pas de tendance claire |

**Signal d'alarme** : 90 % du run n'a produit aucune amélioration mesurable de la loss. La chute significative s'arrête à l'itération ~150.

### 1.2 Résultats d'arena

Sur 30 évaluations arena (toutes les 50 itérations) :
- **8 promotions** (winrate ≥ 0.55)
- **22 "champion conservé"** (winrate < 0.55)
- Winrate minimal observé : **0.05** à l'itération 400 (1 victoire sur 20)
- Meilleur winrate : **0.74** à l'itération 1250

**Problème structurel** : avec 20 parties d'arena, l'intervalle de confiance à 95 % sur un winrate de 0.55 est **±22 %** (test binomial). Statistiquement, on ne peut rien conclure d'un résultat entre 0.33 et 0.77. Plusieurs promotions ont été accordées sur du bruit pur.

### 1.3 Désert d'arena 150 → 850

700 itérations consécutives sans une seule promotion. Les winrates descendent jusqu'à 0.05–0.20, ce qui indique que **le candidat régressait activement** par rapport au champion. Ce n'est pas une stagnation, c'est une dégradation.

### 1.4 Instabilité bimodale

Les winrates sont très polarisés : soit crushing (0.65–0.74), soit catastrophiques (0.05–0.25). Un entraînement stable devrait converger progressivement vers 0.55–0.65 de façon monotone. Le comportement observé est caractéristique d'une **politique instable** : le modèle apprend et désapprend selon le contenu du replay buffer.

### 1.5 Absence de baseline externe

Toute l'évaluation est auto-référentielle : "est-ce que le candidat bat la version d'hier ?". Le modèle peut avoir convergé vers un équilibre de Nash local — une stratégie cohérente mais sous-optimale — sans qu'on le détecte. Il n'existe aucune mesure de qualité absolue.

---

## 2. Ce que dit la littérature

### 2.1 Simulations MCTS vs itérations de self-play — le tradeoff fondamental

**Papier de référence** : *"Analysis of Hyper-Parameters for Small Games: Iterations or Epochs in Self-Play?"* (Świechowski et al., 2020 — arXiv:2003.05988)

Ce papier analyse 12 hyper-paramètres d'un algorithme AlphaZero-like. Conclusion principale :

> **La boucle externe (nombre d'itérations de self-play) domine la boucle interne (simulations MCTS par coup, épisodes, epochs d'entraînement).** Les hyper-paramètres de la boucle interne doivent être maintenus à des valeurs modérées pour favoriser la diversité des parties générées.

En d'autres termes : **plus de parties variées > moins de parties mieux jouées**, du moins jusqu'à un certain seuil de qualité de simulation.

**Nuance critique** : ce résultat s'applique quand les simulations sont déjà "suffisantes" pour produire des labels non-aléatoires. En dessous d'un seuil minimum (~50–100 sims pour des jeux de complexité moyenne), les labels MCTS sont si bruités que la loss ne peut pas converger. Au-dessus du seuil, l'effet marginal d'une simulation supplémentaire est décroissant.

**AlphaZero original** (Silver et al., 2018) utilisait **1 600 simulations par coup** pour le Go. Pour des jeux plus simples, la pratique courante est de faire progresser le budget de simulations avec l'entraînement :
- Générations 1–4 : 100 sims
- Générations 5–11 : 200 sims
- Générations 12+ : 400 sims

L'idée : au début le réseau est mauvais, plus de sims ne produit pas de meilleurs labels. En fin de training, le réseau est bon, plus de sims exploite réellement sa connaissance.

**Application à notre cas** : 80 sims fixes sur 1500 itérations est probablement sous-optimal dans les deux sens — trop pour les premières itérations (gaspillage), insuffisant pour les dernières (labels encore bruités). Un budget de 300 sims sur 500 itérations donne un meilleur compromis qualité/quantité pour notre contrainte temps de 3h.

### 2.2 Catastrophic forgetting et design du replay buffer

**Papier de référence** : *"Reproducing AlphaZero on Tablut: Self-Play RL for an Asymmetric Board Game"* (arXiv:2604.05476, 2026)

Ce papier, le plus récent et le plus pertinent pour des jeux à asymétrie modérée comme Courtisans, identifie le catastrophic forgetting comme **le défi principal** du passage à l'échelle vers le bas d'AlphaZero (downscaling depuis les ressources de DeepMind).

Deux solutions validées expérimentalement :
1. **Augmentation du replay buffer** (×2 de la taille standard) → "substantially improved stability"
2. **25 % des parties jouées contre des checkpoints passés aléatoires** → stabilise l'entraînement sans compromettre la progression

Le papier original d'AlphaZero ne couvre pas ces problèmes car il était entraîné avec des centaines de TPU, ce qui noie les instabilités dans le volume.

**Lien avec notre observation** : le désert 150→850 et le winrate à 0.05 de l'iter 400 sont des signatures classiques de catastrophic forgetting. Le buffer s'est rempli de parties générées par un modèle en dégradation, créant un cercle vicieux : mauvaises parties → mauvais labels → modèle dégradé → encore plus mauvaises parties.

### 2.3 League training et baseline externe

**Papier de référence** : *"Grandmaster level in StarCraft II using multi-agent reinforcement learning"* (Vinyals et al., DeepMind, 2019)

AlphaStar a démontré que le self-play pur convergait vers des stratégies cyclic (A bat B, B bat C, C bat A) sans amélioration globale. Solution : **League Training** — maintenir un pool d'adversaires hétérogènes :
- **Main agents** : jouent contre tous (self, exploiters, past players)
- **Main exploiters** : jouent uniquement contre les main agents pour trouver leurs failles
- **League exploiters** : jouent contre tous les players passés

Pour notre cas, une version simplifiée suffit : mixer le self-play avec un **adversaire heuristique déterministe** (greedy bot) qui joue à 100 % optimal sur les récompenses immédiates. Avantages :
- Baseline externe et reproductible (pas de variance d'arena)
- Immunité aux cycles stratégiques du self-play pur
- Facile à implémenter (pas de réseau, juste un `argmax` sur les rewards immédiats)

**Papier complémentaire** : *"Curriculum Learning"* (Bengio et al., 2009) — principe validé : commencer contre des adversaires progressivement plus difficiles accélère l'apprentissage initial et améliore la robustesse finale. L'**ε-greedy curriculum** (jouer le coup optimal avec probabilité ε, aléatoire sinon) en est une implémentation directe. ε croît de 0.1 à 1.0 au fil des itérations.

### 2.4 Taille d'arena — statistiques

Avec un test binomial exact (H₀ : winrate = 0.5) :

| Parties | Marge d'erreur (±) | Ce que ça veut dire sur un winrate observé de 0.55 |
|---|---|---|
| 20 | **±22 %** | La vraie valeur est entre 0.33 et 0.77 → **on ne sait rien** |
| 50 | ±14 % | Entre 0.41 et 0.69 → encore très incertain |
| 100 | ±10 % | Entre 0.45 et 0.65 → limite acceptable |
| 200 | ±7 % | Entre 0.48 et 0.62 → signal faible mais réel |
| 1000 | **±3 %** | Entre 0.52 et 0.58 → **signal fiable, décision valide** |

La marge d'erreur n'est pas "l'amélioration entre les configs" — c'est **l'incertitude sur chaque estimation**. Passer de 20 à 1000 parties, c'est passer d'une incertitude de ±22 points à ±3 points, soit **7× plus précis**.

Conséquence directe sur notre run v1 : notre winrate de 0.67 à iter 100 avait une marge réelle de ±22 %, ce qui signifie que la vraie performance était quelque part entre 0.45 et 0.89. On a peut-être promu un modèle moins bon que le champion. Avec 1000 parties, un winrate de 0.67 (±3 %) signifie que le modèle est **réellement** entre 0.64 et 0.70 — sans ambiguïté.

---

## 3. Stratégie d'amélioration — propositions validées

### 3.1 Simulations et itérations

**Config proposée** : `--iterations 300 --num-sims 500`

Justification :
- 500 sims produit des distributions MCTS nettement plus concentrées → labels policy plus fiables → loss converge plus bas
- 300 itérations × 500 sims ≈ même budget de simulations totales que 1500 × 80 (150k vs 120k), mais avec beaucoup moins de parties → chaque partie "vaut" plus dans le buffer
- Durée estimée : 300 × (500/80 × 8.5s) ≈ ~5.3h. À ajuster selon la tolérance temps.

**Alternative progressive** (inspirée de la pratique AlphaZero) :
- Itérations 0–100 : 100 sims (réseau trop mauvais pour que plus de sims aide)
- Itérations 100–250 : 200 sims
- Itérations 250+ : 500 sims

### 3.2 Arena : 1000 parties

`arena_games=1000` au lieu de 20.

Coût : ~1000 × 0.61ms × 2 joueurs × overhead réseau ≈ **~2–3 min par arena**. Avec une arena tous les 50 iters sur 300 iters = 6 arenas = ~15 min supplémentaires sur un run de 3h. Coût négligeable, gain statistique massif.

### 3.3 Replay buffer — uniquement les parties du champion

**Changement** : le buffer ne reçoit des parties que lorsque le candidat a été promu (ou lors du tout premier run). Entre deux arenas, si le champion est conservé, les parties du candidat ne sont **pas** ajoutées au buffer.

Justification littérature (Tablut, 2026) : les parties d'un modèle en dégradation empoisonnent le buffer avec des labels incorrects → cercle vicieux. AlphaZero original génère les parties de training avec le meilleur modèle connu, pas le modèle en cours d'optimisation.

Coût : moins de diversité dans le buffer en phase de stagnation. Mitigation : mixer avec 25 % de parties contre des checkpoints passés aléatoires (recommandation directe du papier Tablut).

### 3.4 Greedy bot — baseline externe

**Définition** : à chaque tour, évaluer toutes les actions légales, simuler le `step()` pour chacune, retenir celle qui maximise `reward` immédiat (score du joueur après le coup).

**Complexité** : 12 actions max × 0.05ms/step = < 1ms/coup → négligeable.

**Utilisation** :
1. **Benchmark externe** : toutes les 50 itérations, faire jouer le champion contre 100 parties de greedy bot. Objectif minimum avant de qualifier le modèle : winrate ≥ 0.80 contre greedy.
2. **Curriculum d'entraînement** : en option, remplacer l'adversaire self-play par un mélange (greedy avec probabilité ε, self-play sinon). ε croît de 0 à 0.5 au cours du training.

**Limitation du greedy** : le bot ignore les effets assassin différés, les combinaisons multi-tour, et le bluff. Il sera battu par un MCTS même peu entraîné dès ~iter 100. C'est précisément son intérêt comme baseline : franchissable rapidement, ce qui donne un signal positif en début de run.

### 3.5 Checkpoints passés comme adversaires (25 %)

Implémenter : lors de la génération de parties self-play, avec probabilité 25 %, charger un checkpoint passé aléatoire comme adversaire (au lieu de net vs net identiques). Liste de checkpoints : `model_2_ckpt_*.pth`.

Bénéfice : le modèle courant est forcé de rester robuste face à des stratégies "oubliées", ce qui ralentit le catastrophic forgetting sans nécessiter un replay buffer illimité.

---

## 4. Résumé vulgarisé

**Pourquoi l'IA a stagné après 150 itérations ?**

Imagine que tu apprends à jouer aux échecs en regardant tes propres parties. Au début tu progresses vite. Mais après un moment, tes parties deviennent trop prévisibles — tu joues toujours les mêmes coups, tu apprends toujours les mêmes leçons. C'est le plateau.

**Pourquoi le désert 150→850 ?**

L'IA a "oublié" des bonnes stratégies qu'elle avait apprises. Comme si tu avais rempli ton cahier de notes de mauvais conseils jusqu'à ne plus retrouver les bons. Quand elle rejouait contre sa version de la semaine dernière (le champion), elle perdait 95 % du temps.

**Pourquoi 20 parties d'arena c'est insuffisant ?**

C'est comme juger si une pièce est biaisée en la lançant 20 fois. Si tu obtiens 11 faces sur 20, tu ne peux pas conclure grand chose. Il faut 1000 lancers pour être sûr que la pièce est effectivement pipée.

**Pourquoi plus de simulations MCTS ?**

Les "simulations" c'est le nombre de coups que l'IA imagine avant de jouer. Avec 80 imaginations, elle joue un peu au hasard. Avec 500, elle voit vraiment ce qui est bon et ce qui est mauvais — et quand elle s'entraîne sur ses propres parties, les leçons sont beaucoup plus claires.

**Pourquoi un robot heuristique ?**

Pour l'instant on sait juste si l'IA d'aujourd'hui bat l'IA d'hier. Mais si les deux sont nulles, le résultat ne veut rien dire. Un robot qui joue toujours le meilleur coup immédiat (sans réfléchir à l'avenir) est une mesure absolue : si l'IA ne bat pas ce robot, elle ne vaut rien.

---

## 5. Plan d'implémentation

| Priorité | Changement | Fichier | Complexité |
|---|---|---|---|
| 1 | Arena 1000 parties | `mcts_network.py` | trivial (changer constante) |
| 2 | Greedy bot externe | nouveau `app/greedy_bot.py` | ~50 lignes |
| 3 | Benchmark greedy en training | `mcts_network.py` | ~20 lignes |
| 4 | Buffer : uniquement parties du champion | `mcts_network.py` | modéré |
| 5 | 25 % parties contre checkpoints passés | `mcts_network.py` | modéré |
| 6 | Simulations progressives | `mcts_network.py` | ~10 lignes |

---

## Sources

- Silver et al. (2018). *A general reinforcement learning algorithm that masters chess, shogi, and Go through self-play.* Science. — AlphaZero original
- Świechowski et al. (2020). [*Analysis of Hyper-Parameters for Small Games: Iterations or Epochs in Self-Play?*](https://arxiv.org/abs/2003.05988) arXiv:2003.05988
- Vinyals et al. (2019). [*Grandmaster level in StarCraft II using multi-agent reinforcement learning.*](https://storage.googleapis.com/deepmind-media/research/alphastar/AlphaStar_unformatted.pdf) Nature 575.
- Bengio et al. (2009). *Curriculum Learning.* ICML 2009.
- Zanetti & Gambardella (2026). [*Reproducing AlphaZero on Tablut: Self-Play RL for an Asymmetric Board Game.*](https://arxiv.org/abs/2604.05476) arXiv:2604.05476
