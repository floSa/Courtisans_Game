# L'algorithme d'entraînement — explication détaillée avec pseudo-code

---

## Vue d'ensemble : 4 briques

```
TRAIN
├── boucle sur N itérations
│   ├── MCTS → jouer une partie → collecter des exemples
│   ├── OPTIMIZER → s'entraîner sur les exemples
│   ├── (tous les 100 iters) ARENA → tester si on a progressé
│   └── (tous les 50 iters) GREEDY BENCHMARK → mesure absolue
```

---

## Brique 1 — MCTS : qu'est-ce qu'une "simulation" ?

### La question de base

À chaque coup pendant une partie, le réseau doit choisir une action.
Il pourrait juste demander au réseau "quel coup jouer ?" et prendre le plus probable.
Mais ce serait pauvre — le réseau est encore très imparfait, surtout au début.

La solution : avant de jouer un coup, **explorer mentalement** des centaines de variantes
pour avoir une bien meilleure estimation. C'est le rôle du MCTS.

### Une simulation = un chemin dans l'arbre

Une simulation ce n'est **pas une partie complète**. C'est un trajet de la racine
jusqu'à une position non encore explorée, en 3 phases :

```
MCTS.search(position_courante) → distribution de probabilités sur les coups

  Répéter 500 fois :
    |
    ├── SÉLECTION
    │     Depuis la racine, descendre dans l'arbre en choisissant à chaque nœud
    │     l'action avec le meilleur score UCB :
    │
    │         UCB(action) = Q(action) + c_puct × P(action) × √(N_parent) / (1 + N(action))
    │
    │         Q(action)  = valeur moyenne observée sur les simulations passées
    │         P(action)  = probabilité que le réseau donne à ce coup (prior)
    │         N(action)  = nb de fois que ce coup a déjà été exploré
    │         c_puct     = constante d'exploration (1.5 ici)
    │
    │     → Les coups peu explorés ont un gros bonus (√N_parent / 1+N)
    │     → Les coups jugés bons par le réseau (P élevé) partent avec un avantage
    │     → On descend jusqu'à un nœud jamais visité (feuille)
    │
    ├── ÉVALUATION
    │     On demande au réseau de neurones d'évaluer cette position inconnue :
    │
    │         (policy, value) = reseau(state_vector)
    │
    │     value est un score entre -1 (mauvais) et +1 (bon) du point de vue
    │     du joueur courant. C'est une ESTIMATION — pas le vrai résultat de partie.
    │
    ├── EXPANSION
    │     On ajoute ce nœud à l'arbre avec ses probabilités initiales P = policy
    │
    └── BACKPROPAGATION
          On remonte le chemin parcouru en mettant à jour les statistiques :
          Pour chaque nœud traversé :
              N(action) += 1
              Q(action) = moyenne des values remontées par ce nœud
          Si le nœud du dessus appartient à l'adversaire, on inverse le signe de value
          (ce qui est bon pour moi est mauvais pour lui)

  Après 500 simulations :
    Compter les visites de chaque action à la racine → N(action)
    Normaliser → π(action) = N(action) / somme(N)
    Retourner π  ← c'est ça, la distribution de politique MCTS
```

### Pourquoi un coup très visité est-il "bon" ?

Parce que l'UCB pousse à explorer les coups peu visités. Si un coup continue quand
même à être très visité malgré ce bonus à l'exploration, c'est que ses Q-values
remontées sont élevées — c'est-à-dire que les positions qui en découlent sont
**systématiquement évaluées comme bonnes** par le réseau.

**La valeur remontée n'est pas un résultat de partie** (on ne joue pas la partie jusqu'au
bout). C'est une estimation du réseau. C'est le principal point faible au début : si le
réseau est nul, ses estimations sont nulles, et les visites ne veulent rien dire. C'est
pourquoi les premières itérations d'entraînement produisent des labels bruités.

### La connexion avec gagner ou perdre

La connexion est indirecte et s'établit sur des dizaines d'itérations :

```
Itération 1 :
  Réseau aléatoire → values aléatoires → visites MCTS presque aléatoires
  → on joue des parties presque aléatoires
  → au bout de la partie on connaît le vrai résultat (score final)
  → on dit au réseau : "dans cette position tu avais dit +0.3 mais en fait tu as perdu,
    ta vraie value était -0.8"

Itération 10 :
  Réseau légèrement meilleur → values un peu moins nulles → visites légèrement orientées
  → etc.
```

La boucle complète : les vraies valeurs de fin de partie corrigent le réseau, le réseau
améliore ses estimations en cours de partie, le MCTS peut donc explorer plus intelligemment,
les coups joués sont meilleurs, les vraies valeurs sont plus informatives...

---

## Brique 2 — `_run_one_game` : une partie self-play complète

```python
_run_one_game(net, config) → (liste d'exemples, scores_finaux)

  Créer un environnement de jeu (plateau vide)
  Créer un MCTS local avec net comme évaluateur

  historique = []

  TANT QUE la partie n'est pas terminée :

    SI assassin en attente (cas spécial) :
      probs = MCTS.search(position_courante)   # distribution sur les cibles possibles
      action = échantillonner(probs)            # selon température (voir ci-dessous)
      env.resolve_assassin(action)
    SINON :
      probs = MCTS.search(position_courante)   # distribution sur les 12 actions
      action = échantillonner(probs)
      env.step(action)

    historique.append( (state_vector, probs, joueur_courant) )

  # Fin de partie : on connaît maintenant les vrais scores
  scores = env.calcul_scores()

  # Construire les exemples d'entraînement
  Pour chaque (state, probs, joueur) dans historique :
    mon_score    = scores[joueur]
    score_moyen_adversaires = moyenne(scores des autres joueurs)
    value = clamp( (mon_score - score_moyen_adversaires) / 20 , -1, +1 )
    #       ↑ normaliser le score brut en [-1, +1]

    exemples.append( (state, probs, value) )
    #                  ↑       ↑      ↑
    #               entrée   cible   cible
    #               réseau   policy  value

  Retourner exemples, scores
```

### La température : explorer ou exploiter

```
SI coup_numéro < temperature_threshold (10 premiers coups) :
    action = ÉCHANTILLONNER selon probs  (exploration — on peut jouer un coup sous-optimal)
SINON :
    action = ARGMAX(probs)               (exploitation — on joue le meilleur coup connu)
```

Pourquoi ? Les premiers coups d'une partie sont souvent symétriques ou peu décisifs.
Introduire de la variété génère des parties diverses → un buffer d'entraînement riche.
En fin de partie, les coups sont critiques → on joue le meilleur.

---

## Brique 3 — `train` : la boucle principale

```python
train(config)

  Charger le champion existant (model_2.pth) ou créer un réseau vierge
  Créer un replay buffer (file FIFO de taille max 100 000 exemples)
  Créer l'optimiseur AdamW

  POUR it DE 0 À 299 (300 itérations) :

    # 1. Choisir l'adversaire (25% du temps : un vieux checkpoint)
    SI random() < 0.25 ET checkpoints_disponibles :
        adversaire = charger checkpoint aléatoire parmi les 10 derniers
    SINON :
        adversaire = None  # self-play pur (champion joue contre lui-même)

    # 2. Calculer le nb de sims effectif (schedule progressif)
    SI it < 100  : sims = min(500, 100)   →  100 sims
    SI it < 250  : sims = min(500, 200)   →  200 sims
    SINON        : sims = 500

    # 3. Jouer une partie avec le CHAMPION (pas le candidat en cours d'entraînement)
    #    → les exemples sont toujours basés sur de "bonnes" parties
    exemples, scores = _run_one_game(champion, config, adversaire, sims)

    # 4. Ajouter au buffer
    POUR chaque exemple :
        buffer.append(exemple)

    # 5. Entraîner le réseau candidat (net) sur un batch tiré du buffer
    SI buffer.taille > 64 :
        batch = tirer_aleatoire(buffer, 64)
        batch = augmenter(batch)        # permuter les familles de cartes (symétrie)

        états, cibles_policy, cibles_value = décomposer(batch)

        policy_pred, value_pred = reseau(états)

        loss_policy = cross_entropy(policy_pred, cibles_policy)
        #             ↑ pénalise si le réseau dit "joue A" alors que MCTS disait "joue B"

        loss_value  = mse(value_pred, cibles_value)
        #             ↑ pénalise si le réseau dit +0.5 et le vrai résultat était -0.8

        loss = loss_policy + loss_value

        loss.backward()    # calculer les gradients
        optimizer.step()   # ajuster les poids du réseau

    # 6. Checkpoint tous les 25 iters
    SI (it+1) % 25 == 0 :
        sauvegarder model_2_ckpt_{it+1}.pth

    # 7. Arena tous les 100 iters
    SI (it+1) % 100 == 0 :
        stats = arena(candidat, champion, 1000 parties)
        SI stats.winrate >= 0.55 :
            champion = candidat
            sauvegarder model_2.pth
        SINON :
            garder l'ancien champion

    # 8. Benchmark greedy tous les 50 iters
    SI (it+1) % 50 == 0 :
        stats = benchmark_vs_greedy(champion, 200 parties)
        logger.info(f"Greedy winrate: {stats.winrate}")

  Sauvegarder model_2_candidate.pth  # dernière version entraînée
```

---

## Brique 4 — `arena` : est-ce qu'on a vraiment progressé ?

```python
arena(candidat, champion, num_games=1000, sims=30)

  wins = losses = draws = 0

  POUR g DE 0 À 999 :
    # Alterner qui commence pour neutraliser l'avantage premier joueur
    SI g % 2 == 0 : candidat = joueur 0, champion = joueur 1
    SINON         : champion = joueur 0, candidat = joueur 1

    # Jouer la partie (les deux utilisent MCTS avec 30 sims — rapide)
    résultat = _play_one_arena_game(candidat, champion)

    SI résultat == candidat  : wins  += 1
    SI résultat == champion  : losses += 1
    SINON                    : draws  += 1

  winrate = wins / (wins + losses)   # les draws ne comptent pas
  Retourner {wins, losses, draws, winrate}
```

### Pourquoi 30 sims en arena et pas 500 ?

L'arena joue 1000 parties. Avec 500 sims × 46 coups × 1000 parties ≈ 23 millions de
forward passes réseau → plusieurs heures. Avec 30 sims, l'arena prend ~35 minutes.
Les deux modèles jouent avec les mêmes 30 sims → la comparaison reste juste.

---

## Brique 5 — `greedy_benchmark` : la mesure absolue

```python
benchmark_vs_greedy(net, num_games=200, sims=30)

  POUR g DE 0 À 199 :
    SI g % 2 == 0 : net = joueur 0, greedy = joueur 1
    SINON         : greedy = joueur 0, net = joueur 1

    TANT QUE partie non terminée :
      SI joueur courant == net :
          probs = MCTS(net, sims=30).search(position)
          action = argmax(probs)
      SINON :
          # Greedy bot : évaluer chaque action légale et prendre la meilleure
          POUR chaque action légale :
              sim = cloner_plateau()
              sim.jouer(action)
              score = sim.score_du_joueur_courant()
          action = argmax(scores immédiats)

      jouer(action)
```

**Ce que mesure ce benchmark :** est-ce que l'IA peut battre un joueur qui ne réfléchit
qu'à un coup à l'avance ? Si non, l'IA ne planifie pas encore.

**Résultat actuel :** 17–24% de victoires. L'IA perd 4× sur 5 contre ce bot myope.
Objectif pour considérer l'IA "fonctionnelle" : > 80%.

---

## Pourquoi la loss ne suffit pas comme mesure

La loss mesure l'écart entre ce que le réseau prédit et ce que le MCTS a calculé.
Mais le MCTS lui-même dépend du réseau pour ses estimations. Si le réseau est mauvais,
le MCTS est mauvais, les labels sont mauvais, et la loss peut descendre tout en
restant "mauvaise" en absolu.

C'est pourquoi on a besoin des trois mesures en parallèle :

| Mesure | Ce qu'elle dit | Limite |
|---|---|---|
| Loss | Le réseau apprend-il quelque chose ? | Auto-référentiel |
| Arena | A-t-on progressé par rapport à avant ? | Auto-référentiel |
| Greedy benchmark | L'IA joue-t-elle bien en absolu ? | Plancher bas |

---

## Résumé en une phrase par brique

- **MCTS** : avant chaque coup, simuler 500 chemins dans l'arbre de jeu en utilisant le réseau comme oracle, et jouer le coup le plus visité.
- **self-play** : jouer une partie entière, puis utiliser les vrais scores finaux pour labelliser chaque position.
- **train loop** : répéter 300× — jouer une partie, stocker, s'entraîner sur 64 exemples passés.
- **arena** : tous les 100 iters, 1000 parties officielles pour décider si le candidat remplace le champion.
- **greedy bench** : tous les 50 iters, 200 parties contre un bot stupide pour mesurer le niveau absolu.
