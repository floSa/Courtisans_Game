# Stratégie d'entraînement v2 — Analyse critique et feuille de route

Ce document fait suite au premier run complet (1500 itérations, 22h44–02h35, 26–27 mai 2026).
Il rassemble le diagnostic des problèmes observés, ce que dit la littérature scientifique,
et les décisions d'implémentation retenues pour la v2.

---

## 1. Diagnostic du run v1 — ce qui a mal fonctionné

### 1.1 La loss a plateauté à iter ~200

**Observation :** la loss descend rapidement de 5.5 → 3.1 sur les 200 premières itérations,
puis oscille entre 3.0 et 3.4 pendant les 1300 itérations suivantes sans tendance claire.

**Cause technique :** avec 80 simulations MCTS par coup et ~46 coups par partie, chaque
itération produit des labels de politique (distributions de visite) très bruités. Le réseau
de neurones ne peut pas mieux fitter ce qu'il voit, non pas parce qu'il a tout appris, mais
parce que les cibles changent à chaque itération et restent imprécises. Le plateau n'est
pas la convergence — c'est le plafond du signal disponible avec cette config.

**Vulgarisé :** imagine que tu apprends à jouer aux échecs en t'entraînant avec un prof qui
ne joue que 3 coups à l'avance. Même si tu deviens très fort, ton "prof" est trop limité pour
te donner des conseils meilleurs que ceux que tu as déjà intégrés. Il faut un prof qui calcule
plus loin.

### 1.2 Désert d'arena iter 150 → 850 (700 itérations sans promotion)

**Observation :** après 3 promotions rapides (iters 50, 100, 150), le candidat n'arrive plus
à battre le champion pendant 700 itérations. Pire : le winrate chute à 0.05 à iter 400
(1 victoire sur 20 parties).

**Cause technique — deux phénomènes combinés :**

1. **Catastrophic forgetting** : le modèle "désapprend" en suroptimisant sur les nouvelles
   parties. Le replay buffer contient un mélange de parties récentes (mauvaises) et anciennes
   (meilleures), mais le gradient moyen tire le modèle vers les récentes.

2. **Distribution shift circulaire** : le modèle génère des parties → crée ses propres labels
   → s'entraîne dessus → génère des parties légèrement différentes → etc. Si à un moment le
   modèle part dans une mauvaise direction, les labels changent avec lui, et rien ne le
   rappelle à la réalité. C'est ce qu'on appelle un "drifting" en self-play.

**Vulgarisé :** c'est comme apprendre à cuisiner en goûtant uniquement tes propres plats.
Si tu prends une mauvaise habitude (trop de sel), tu vas trouver tes plats normaux, créer des
recettes encore plus salées, et progressivement tout tes plats deviennent immangeable — sans
jamais t'en rendre compte parce que tu n'as plus de référence externe.

### 1.3 L'arena sur 20 parties est statistiquement inutilisable

**Observation :** des winrates très instables (0.05, 0.20, 0.56, 0.74, 0.40...) alternent
sans logique apparente.

**Cause technique :** avec 20 parties, la marge d'erreur statistique (intervalle de confiance
à 95%) sur un winrate de 0.55 est ±22 points de pourcentage. Autrement dit, un modèle "vrai"
à 55% peut observer entre 33% et 77% sur un échantillon de 20 parties. On a promu et rejeté
des modèles sur du bruit pur.

Formule : σ = √(p(1-p)/n) = √(0.55×0.45/20) ≈ 0.111, IC95 = ±1.96×0.111 ≈ ±0.22.

Pour avoir une erreur < 5 points : n = (1.96/0.05)² × 0.25 ≈ **384 parties minimum**.
1000 parties donne une erreur ±3 points — c'est fiable.

**Vulgarisé :** juger un joueur de tennis sur 2 sets alors qu'il peut gagner ou perdre par
chance. Sur 100 matchs, la chance s'efface.

### 1.4 Pas de baseline externe — l'auto-référentialité du self-play

**Observation :** on ne sait pas si l'IA "joue bien" en absolu — on sait seulement qu'elle
bat sa version d'avant.

**Cause technique :** le self-play pur est un système fermé. Il peut converger vers n'importe
quel équilibre de Nash, y compris des équilibres sous-optimaux où les deux joueurs adoptent
des stratégies mutuellement exploitables par un agent externe avec une stratégie différente.

**Vulgarisé :** deux joueurs qui apprennent à jouer ensemble peuvent développer un code
secret (des habitudes partagées) très efficace entre eux, mais complètement inefficace
contre n'importe qui d'autre.

---

## 2. Ce que dit la littérature scientifique

### 2.1 Le compromis itérations / simulations MCTS

**Papier clé :** *"Analysis of Hyper-Parameters for Small Games: Iterations or Epochs in
Self-Play?"* (arXiv:2003.05988, 2020).

Ce papier étudie 12 hyper-paramètres d'un système AlphaZero-like sur des petits jeux.
Conclusion principale (résumée) :

> **La boucle externe (nombre d'itérations de self-play) est le paramètre le plus important.
> Les paramètres de la boucle interne (simulations MCTS, épisodes par itération, epochs
> d'entraînement) devraient être gardés bas, en faveur de plus d'itérations.**

Interprétation : un budget fixe de calcul est mieux utilisé en jouant plus de parties (même
avec un MCTS moins précis) qu'en jouant peu de parties avec un MCTS très précis.

**Mais attention — la nuance critique :**
Ce résultat vaut pour les *petits* jeux où 50–100 simulations suffisent à produire un signal
utile. Pour les jeux complexes (Go, Chess), AlphaZero utilise **1600 simulations** par coup
parce qu'en dessous d'un certain seuil, le MCTS ne "voit" pas assez loin pour produire un
label de politique meilleur que le réseau seul. Il existe un **seuil minimal de simulations**
en dessous duquel les labels sont du bruit.

**Application à Courtisans :** le jeu a ~46 coups par partie et ~12 actions légales par coup.
L'arbre MCTS est moins profond que Go, mais la dimension cachée (cartes inconnues) augmente
la variance. Empiriquement, 80 simulations montrent un plateau de loss rapide — suggérant
qu'on est sous le seuil de qualité. **200–500 simulations** sont justifiées pour améliorer
la qualité des labels avant d'augmenter le nombre d'itérations.

**Compromis retenu pour la v2 :**
- 500 simulations × 300 itérations en session de test (3h)
- Comparer la qualité des labels (variance de la loss, fréquence des promotions)
- Si les promotions sont plus régulières → augmenter les itérations en session suivante

### 2.2 Catastrophic forgetting et replay buffer

**Papier clé :** *"Reproducing AlphaZero on Tablut: Self-Play RL for an Asymmetric Board
Game"* (arXiv:2604.05476, 2025).

Ce papier reproduit AlphaZero sur un jeu de plateau asymétrique (similaire à notre cas
avec les familles asymétriques dans Courtisans). Conclusions sur le catastrophic forgetting :

> *"During training, performance against earlier checkpoints degraded — a phenomenon known
> as catastrophic forgetting in self-play."*

Solutions validées par les auteurs :
1. **Augmenter la taille du replay buffer** (de 8 à 16 itérations de self-play stockées) →
   stabilité substantiellement améliorée.
2. **25% des parties d'entraînement jouées contre des checkpoints passés** (tirés
   aléatoirement parmi les 10 derniers) → stabilisation supplémentaire.

**Application à Courtisans :** on implémente les deux. Le replay buffer actuel (100k samples)
stocke ~2 runs de parties — c'est déjà correct. On ajoute le mécanisme de 25% contre
checkpoints passés.

### 2.3 League training et diversité des adversaires

**Papier clé :** *"Grandmaster level in StarCraft II using multi-agent reinforcement learning"
— AlphaStar* (DeepMind, Nature 2019).

AlphaStar introduit le **League Training** pour résoudre le problème du self-play cyclique
(le modèle apprend à battre sa dernière version, mais devient vulnérable à des versions
encore plus anciennes).

Structure de la ligue :
- **Main agents** : s'entraînent contre toute la ligue (passé + présent)
- **Main exploiters** : cherchent à exploiter les failles du main agent courant
- **League exploiters** : cherchent les failles de toute la ligue

**Application à Courtisans (version simplifiée) :** on ne peut pas implémenter une ligue
complète, mais on peut introduire :
1. Un pool de checkpoints passés comme adversaires (anti-forgetting)
2. Un **heuristic bot** (greedy) comme adversaire fixe externe

### 2.4 Heuristique greedy et curriculum

**Concept :** ε-greedy curriculum — l'adversaire joue le coup optimal avec probabilité
(1-ε) et un coup aléatoire avec probabilité ε. En faisant décroître ε de 1.0 (totalement
aléatoire) à 0.0 (totalement greedy) au cours de l'entraînement, on crée une progression
naturelle de difficulté.

**Référence :** *"Curriculum Learning"* (Bengio et al., ICML 2009) — principe général :
présenter des exemples du plus simple au plus difficile accélère la convergence et améliore
la qualité finale du modèle.

**Définition de "coup greedy" pour Courtisans :** pour chaque action légale, simuler
l'état résultant et choisir l'action qui maximise le score *immédiat* du joueur (somme des
cartes sur le plateau après le coup). C'est rapide (12 clones max) et représente un joueur
"raisonnable mais myope" : il ne calcule pas les conséquences futures.

**Limite connue de ce greedy :** il ignore les menaces d'assassin, les combos multi-coups,
et le contrôle de plateau. L'IA devrait le battre facilement après quelques centaines
d'itérations — c'est voulu : le greedy est un plancher, pas un plafond.

**Application à Courtisans :**
- Au début de l'entraînement : ε = 1.0 (adversaire aléatoire → facile à battre → labels
  peu bruités car les parties sont courtes et lisibles)
- À mi-entraînement : ε = 0.5 (adversaire semi-greedy)
- Fin d'entraînement : ε = 0.0 (adversaire purement greedy → test de solidité)

---

## 3. Décisions d'implémentation v2

### 3.1 Arena : 1000 parties

| | v1 | v2 |
|---|---|---|
| Parties d'arena | 20 | **1000** |
| Erreur IC95 | ±22% | **±3%** |
| Temps par arena | ~1 min | ~10 min |
| Fréquence | tous les 50 iters | tous les 100 iters |

L'augmentation du coût (~10 min par arena × 3 arenas sur 300 iters = 30 min) est
absorbée en réduisant la fréquence. Le signal est incomparablement plus fiable.

### 3.2 Simulations MCTS : 500 (vs 80 en v1)

Objectif : sortir du plateau de loss rapide observé en v1. 500 simulations par coup
permettent à l'MCTS d'explorer l'arbre assez profondément pour produire des distributions
de visite significatives, même sous information partielle (cartes cachées).

Coût : ~6× plus lent par partie. Sur 300 itérations (vs 1500) le budget temps reste ~3h.

### 3.3 Anti-catastrophic-forgetting : 25% contre checkpoints passés

À chaque itération, au lieu de jouer uniquement contre `model_2.pth` (le champion actuel),
25% des parties sont jouées contre un checkpoint tiré aléatoirement parmi les 10 derniers
sauvegardés. Cela force le modèle à maintenir sa performance contre toutes les versions
récentes, pas seulement la dernière.

### 3.4 Heuristic bot greedy comme baseline externe

Un bot `GreedyBot` est implémenté et utilisé de deux façons :

1. **Validation** : toutes les 100 itérations, jouer 200 parties contre le GreedyBot.
   Un modèle "sérieux" doit le battre à >80%. C'est le signal absolu qui manquait en v1.

2. **Curriculum** (optionnel, phase suivante) : utiliser le GreedyBot comme adversaire
   d'entraînement avec ε décroissant selon un schedule linéaire.

### 3.5 Résumé de la config v2

```bash
python -u main.py train \
  --iterations 300 \
  --num-sims 500 \
  --mcts-batch-size 1 \
  --num-worlds 1 \
  --memory-size 100000 \
  --arena-games 1000 \
  --arena-every 100 \
  --past-checkpoint-ratio 0.25 \
  2>&1 | tee train_v2.log
```

---

## 4. Ce qu'on n'implémente PAS (et pourquoi)

### 4.1 League training complet (AlphaStar)

Trop complexe pour le gain attendu sur un jeu à 2 joueurs relativement simple. Le mécanisme
de 25% contre checkpoints passés donne 80% du bénéfice pour 20% du coût d'implémentation.

### 4.2 Prioritized Experience Replay (PER)

Mécanisme qui sample les transitions "surprenantes" (erreur TD élevée) plus souvent.
Efficace sur des environnements stationnaires. Ici, la distribution change à chaque
itération → le calcul des priorités devient rapidement périmé. Non pertinent.

### 4.3 torch.multiprocessing pour parallélisation vraie

Implémentation complexe (processes séparés, queue partagée). Documenté dans
`entrainement.md` comme piste future. Pas prioritaire avant d'avoir validé la qualité
des labels avec 500 sims.

---

## 5. Métriques de succès v2

| Métrique | Résultat v1 | Objectif v2 |
|---|---|---|
| Loss finale | 3.01 | < 2.5 |
| Loss plateau atteint à | iter 200 | iter 400+ |
| Promotions arena | 8/30 (27%) | > 40% |
| Winrate vs GreedyBot | non mesuré | > 80% |
| Winrate arena biaisé (0.05 vu) | oui | non |

---

## Références

- Silver et al. (2018). *A general reinforcement learning algorithm that masters chess,
  shogi, and Go through self-play.* Science. — AlphaZero
- Vinyals et al. (2019). *Grandmaster level in StarCraft II using multi-agent reinforcement
  learning.* Nature. — AlphaStar / League Training
- Auer et al. (2020). *Analysis of Hyper-Parameters for Small Games: Iterations or Epochs
  in Self-Play?* arXiv:2003.05988
- Bengio et al. (2009). *Curriculum Learning.* ICML 2009.
- Saffidine et al. (2025). *Reproducing AlphaZero on Tablut.* arXiv:2604.05476
