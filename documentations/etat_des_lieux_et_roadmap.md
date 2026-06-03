# État des lieux & feuille de route — IA Courtisans

> Document de passation (01/06/2026). À lire en premier pour reprendre le projet.
> Détails complets et historique : `documentations/rapport_expert.md` (§0 conclusion-chapeau,
> puis §24–28 pour la dernière phase).

---

## 1. TL;DR — le pivot

Après ~1 semaine d'expériences style **AlphaZero (MCTS + self-play)**, verdict : **mauvais
paradigme**. Courtisans est un jeu à **information imparfaite** (mains, espions face cachée) ;
AlphaZero est fait pour l'information *parfaite*. Tous les échecs en découlent.

**On bascule sur la famille CFR** (lignée poker : CFR+, Deep CFR, ReBeL), via **OpenSpiel**,
avec l'**exploitabilité** comme métrique absolue. Premier jalon atteint : un **oracle**
(Courtisans réduit résolu exactement) fonctionne.

---

## 2. Ce qui a été prouvé (et enterré)

- **Toutes les variantes MCTS < policy brute** (value réseau, value=0, ISMCTS, rollout greedy,
  heuristique). La recherche *dégrade* sur ce jeu. ISMCTS *pire* que mono-monde (t=−2.56).
- **Value scalaire plafonnée à r≈0.4** (held-out), insensible au volume. Cause : la valeur d'un
  info-set dépend du *reach* adverse, absent de l'entrée → cible mal posée, plancher d'erreur
  irréductible. Ce n'est PAS un bug d'encodage (vérifié : l'info privée — mes espions posés —
  est bien dans le state vector via `proprietaire_idx == current_player`).
- **Le meilleur réseau (v8_250) perd ~99 %** contre un **greedy 1-coup qui maximise l'écart**
  `s_moi − s_adv` (équitable PIMC comme info-privilégié). Le saut historique 0.396 → 0.00 vient
  de l'objectif "écart" (correction du greedy), pas de la triche.
- **BC du greedy** : capacité OK (fit 67 %+) mais plafonne (distribution shift).
- **DAgger** : casse le sol (écart −32 → −14, wr 0 → 0.03) mais plafonne à 95,5 % d'imitation —
  on n'imite qu'un greedy lui-même sous-optimal.

→ Conclusion : abandonner non pas "la recherche", mais **"la recherche à value scalaire par
monde"**, structurellement non fondée ici. Ces résultats restent valides comme *résultat négatif
propre*, pas comme voie à poursuivre.

---

## 3. Le cadre correct (consensus expert)

**2 joueurs = compétitif pur → on optimise l'écart, qui est à somme nulle.** Donc :
- Famille **CFR / Deep CFR / ReBeL** : convergence vers Nash, **exploitabilité (NashConv)
  mesurable** = métrique absolue (remplace le winrate-vs-greedy et tout le bruit de mesure).
- **Deep CFR d'abord** : MCCFR descend aux terminaux (gains réels, **pas de feuille
  bootstrappée**) → contourne la cause racine (value plafonnée). Vrai risque = **variance**
  (horizon ~46 × pioche) → VR-MCCFR / baselines.
- **ReBeL en escalade conditionnelle** : si l'exploitabilité Deep CFR plafonne, ou si on veut de
  la recherche au test. Sa value sur *public belief state* est une cible *bien posée*.

**>2 joueurs** (plus tard) : somme non nulle, pas de Nash, alliances/kingmaking → ligue / PSRO,
métrique Elo vs pool. Fallback, pas l'objectif premier.

---

## 4. État du code

| Fichier | Rôle | Statut |
|---|---|---|
| `app/jeu.py` | Moteur Courtisans (règles, state vector, scoring) | OK, sert de simulateur rapide |
| `app/mcts_network.py` | Réseau + MCTS + boucle d'entraînement AlphaZero/Fork2 | **Voie abandonnée** (historique) |
| `app/greedy_bot.py` | Greedy 1-coup. `num_worlds=0` triche / `≥1` équitable PIMC | OK — sert de baseline/LBR |
| `cfr/courtisans_mini.py` | **Courtisans réduit en jeu OpenSpiel** (+ `information_state_tensor` lossless 53-dim) | ✅ Marche |
| `cfr/solve_mini.py` | Résolution exacte CFR+ + exploitabilité (oracle) | ✅ Marche |
| `cfr/deep_cfr_mini.py` | Deep CFR (PyTorch) vs oracle + courbe d'exploitabilité | ✅ Converge (§29) |
| `cfr/diag_strategy_buffer.py` | Diagnostic : policy MCCFR exacte (buffer) vs réseau | ✅ Marche |
| `cfr/plot_deep_cfr_mini.py` | Graphe Deep CFR vs CFR+ depuis le log | ✅ Marche |
| `scripts/remeasure_fair.py` | Mesure appariée vs greedy équitable PIMC | OK |
| `scripts/dagger_greedy.py`, `bc_greedy.py` | Diagnostics BC/DAgger | Historique |

**`courtisans_mini` (v0)** : 2 familles × 3 rôles {Noble(2), Espion caché(1), Simple(1)},
6 cartes, 2 joueurs, main 3, 1 manche, 12 actions composites, payoff {+1,0,−1}.
Résolu : 3141 états, info-sets P0=20 / P1=216, **exploitabilité 0.000027** à 600 iters CFR+,
équilibre **mixte**.

---

## 5. Décisions verrouillées

1. **Payoff = indicateur de victoire `{+1, 0, −1}`** (le vrai objectif : la marge ne rapporte
   rien en plus dans Courtisans). Pas l'écart de score (qui induit un autre équilibre).
2. **Compo de cartes = uniforme** : 3 exemplaires × 5 rôles × 6 familles (jeu plein).
3. **Outillage = OpenSpiel** (Deep CFR + exploitabilité validés), moteur maison = simulateur
   rapide + croisé-validation.
4. **Symétrie des 6 familles = quotient lossless** (canonicaliser les labels, PAS augmenter) →
   ÷ jusqu'à 6! les info-sets sans bouger l'exploitabilité.
5. **Métrique de pilotage = exploitabilité absolue** ; greedy PIMC = borne inf (LBR) + ancre de
   benchmark (mais lui-même exploitable).

---

## 6. Feuille de route (prochaines briques, dans l'ordre)

1. **[FAIT 03/06] Deep CFR vs l'oracle.** Pipeline neuronal validé : Deep CFR (PyTorch
   OpenSpiel) converge vers l'exploitabilité tabulaire (0.0037 à 200 iters vs oracle 0.00014,
   monotone, sans plateau). Détails + courbe : `rapport_expert.md` §29. Code `cfr/deep_cfr_mini.py`,
   `cfr/diag_strategy_buffer.py`, `cfr/plot_deep_cfr_mini.py`. Piège levé : le « plateau » à
   ~0.08 était le sous-apprentissage de la tête policy, pas le MCCFR (métrique de validation =
   policy buffer-exacte).
2. **[PROCHAIN] Agrandir l'instance** progressivement (plus de familles, 2+ manches avec pioche/draw,
   puis assassins + gardes) jusqu'à la limite du tabulaire — chaque palier validé par
   l'exploitabilité tabulaire tant qu'elle reste calculable.
3. **Deep CFR sur l'instance pleine** (compo uniforme 6×5×3), exploitabilité mesurée.
   Appliquer la canonicalisation par symétrie de familles.
4. **ReBeL** seulement si (a) l'exploitabilité plafonne trop haut, ou (b) besoin de recherche
   au test. Implique public belief state + subgame solving.
5. **Généralisation N>2** via PSRO/ligue (objectif secondaire).

**Garde-fous** : un seul changement à la fois ; toute abstraction au-delà du lossless-par-
symétrie = validée empiriquement contre l'exploitabilité *relevée dans le jeu complet* ;
duplicate scoring pour toute comparaison de force.

---

## 7. Comment lancer (commandes + pièges environnement)

```bash
# Résoudre l'oracle (mini-instance) :
uv run python cfr/solve_mini.py 600

# Deep CFR vs oracle (hyperparams via env DCFR_*) + graphe :
DCFR_TRAVERSALS=500 DCFR_ITERS=200 uv run python cfr/deep_cfr_mini.py
uv run python cfr/plot_deep_cfr_mini.py cfr/deep_cfr_mini_final.log cfr/deep_cfr_mini.png

# Mesurer un modèle vs greedy équitable :
uv run python scripts/remeasure_fair.py
```

**Pièges connus de l'environnement :**
- Toujours `uv run python ...` (le `python` système n'a pas numpy/torch).
- **Ne PAS préfixer les commandes par `OMP_NUM_THREADS=...`** : ça casse le stream de
  permission dans cet environnement. Mettre `os.environ` dans le script si besoin.
- Exploitabilité OpenSpiel sur un jeu Python : utiliser
  `exploitability.nash_conv(game, policy, use_cpp_br=False)` (le best-response C++ exige
  `make_py_observer`, absent du jeu Python).
- Runs longs : lancer en arrière-plan (`run_in_background`) et suivre le `.log`.

---

## 8. Pourquoi on est confiants dans cette direction

- L'exploitabilité est une **vérité-terrain absolue** : fini les faux positifs / le bruit de
  mesure qui a pollué toute la phase AlphaZero.
- Deep CFR **n'a pas de feuille bootstrappée** → la cause racine (value plafonnée à r≈0.4)
  ne s'applique pas.
- L'oracle tabulaire **détecte tout bug/abstraction défaillante** : si Deep CFR ne converge pas
  vers lui, on sait que le problème est dans notre pipeline, pas dans le jeu.
