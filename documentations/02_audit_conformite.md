# Audit de conformité et de code

**Ce que le code fait par rapport à ce que les règles disent, et ce qu'on garde du projet existant.**

Audit du 15/08/2026, branche `cfr-pivot`. Toutes les mesures sont reproductibles par les
scripts cités. Référence des règles : [01_regles.md](01_regles.md).
Suite : [05_protocole_experimental.md](05_protocole_experimental.md).

---

## 1. Synthèse — les six écarts

| # | Écart | Gravité | Touche | Corrigé en |
|---|---|---|---|---|
| **N1** | Le meurtre de l'Assassin est **obligatoire** alors qu'il est facultatif | **Bloquante** | instances 2.1c, 2.1e | Phase 0 |
| **N2** | Fin de partie testée **joueur par joueur** : les premiers de l'ordre jouent un tour de plus | **Bloquante** | `app/jeu.py` | Phase 0 |
| **N3** | Tours inégaux : P0 joue 2 tours (6 cartes), P1 un seul (3 cartes) | **Bloquante** | instances 2.1d, 2.1e | Phase 1 |
| **N4** | La métrique d'exploitabilité joue **uniforme** sur les info-sets non couverts | **Bloquante** | mesure | Phase 2 |
| **N5** | `device="cpu"` codé en dur : le GPU n'est jamais utilisé | Moyenne | performance | Phase 2 |
| **N6** | `DCFR_MEM=1e6` contre ~9,5 M échantillons streamés : ~90 % jetés | Moyenne | algorithme | Phase 2 |

**Cause racine de N1 et N3.** Les quatre instances CFR sont des **copies manuelles** les
unes des autres : `courtisans_assassin.py` et `courtisans_combo.py` ont un `_legal_actions`
identique au caractère près. Un défaut introduit une fois se propage à toutes les instances
suivantes sans que rien ne le signale. Aucun test ne vérifie qu'une instance respecte les
règles.

---

## 2. Ce qui est conforme

Vérifié ligne à ligne contre [01_regles.md](01_regles.md) et
contre le moteur `app/jeu.py`.

| Mécanisme | Statut |
|---|---|
| Assassin — cible dans sa zone, ni Garde, ni lui-même | ✅ |
| Assassin — Estime et Disgrâce sont deux zones distinctes | ✅ |
| Assassin tue un espion caché ou un autre assassin | ✅ |
| Assassins multiples — file de résolution séquentielle | ✅ |
| Carte tuée — exclue de l'influence **et** des points, identique à `app/jeu.py` | ✅ |
| Espion — caché pour l'adversaire, identité connue du poseur, compté au décompte | ✅ |
| Décompte — majorité Estime/Disgrâce, crédité au propriétaire du domaine | ✅ |
| Espace d'actions — 6 assignations × 2 positions Reine × (n−1) adversaires | ✅ |
| **Ordre de pose intra-tour** — sans effet | ✅ |
| **Encodage info-set** — injectif | ✅ |

### 2.1 L'ordre de pose : vérifié sans effet

La règle dit qu'un Assassin tue « immédiatement », ce qui laisserait penser que poser
d'abord chez l'adversaire plutôt que chez soi change les cibles disponibles. **Ce n'est pas
le cas** : les trois cartes d'un tour vont toujours dans trois zones-clés distinctes —
Reine (Estime ou Disgrâce), son domaine, le domaine adverse. Vérifié exhaustivement :
**0 cas sur 24** (12 actions × 2 joueurs) où deux cartes du même tour partagent une zone.

Un assassin posé ce tour-ci ne peut donc jamais cibler ses compagnons de tour. `app/jeu.py`
fait le même choix (ligne 296 : les trois cartes sont posées, **puis** les assassins sont
enfilés). La dimension stratégique — quelle carte chez qui — est modélisée comme une
**assignation**, couverte intégralement par les actions de pose.

> **À revérifier à 3 et 4 joueurs** (test C7 de la spec).

### 2.2 L'encodage : injectif

Traversée exhaustive des **8 250 001** états de l'instance combo, canonicalisation active :

```
info-sets (strings distinctes) : 475 000   (P0 455 092 + P1 19 908)
tenseurs distincts             : 475 000
2 info-sets → 1 tenseur                       : 0
1 info-set → 2 tenseurs                       : 0
actions légales incohérentes dans un info-set : 0
```

Les deux premiers contrôles confirment `cfr/check_combo.py`. Le troisième est nouveau : il
vérifie que tous les états d'un même info-set exposent le même ensemble d'actions légales —
la condition qui rend CFR bien défini. C'était le vrai risque en phase de ciblage, où la
string ne code que la zone-clé de l'assassin et pas son index. Elle passe.

**L'hypothèse « perte d'information dans l'encodage » est éliminée.**

---

## 3. N1 — Le meurtre obligatoire

**La règle.** L'Assassin n'est pas tenu de tuer : ni s'il ne peut pas, ni s'il ne veut pas.

**Le code des instances CFR** (`courtisans_assassin.py:147`, `courtisans_combo.py:149`) :

```python
def _legal_actions(self, player):
    if self._phase == "target":
        return list(range(len(self._valid_targets(self._pending[0]))))
```

Les actions légales sont exactement les cibles. Le cas « je ne peux pas » est géré
(`_advance` retire les assassins sans cible). Le cas **« je ne veux pas » n'existe pas**.

Le moteur `app/jeu.py` l'autorise pourtant : `resolve_assassin_manual(victim_idx: int | None)`,
`None` = skip. **L'écart est entre le moteur et les instances CFR.** Aucune politique du
dépôt n'utilise ce skip : l'heuristique B1 (`_pick_target_heuristic`) ne renvoie `None` que
si la liste de cibles est vide. L'ère AlphaZero jouait donc déjà la variante contrainte.

**Impact mesuré** — 20 000 playouts, 35 046 résolutions d'assassin :

| Mesure | Valeur |
|---|---|
| Résolutions où refuser serait **strictement meilleur** pour le poseur (évaluation myope) | **20.0 %** |
| Perte moyenne subie dans ces cas | **1.34 point** |
| Perte maximale observée | **3 points** |
| Résolutions où **toutes** les cibles sont dans le domaine du poseur (auto-mutilation forcée) | **38.1 %** |

**Conséquence.** L'oracle à **0.001783** est l'équilibre exact d'un jeu qui n'est pas
Courtisans.

---

## 4. N2 et N3 — Les tours inégaux

### 4.1 Dans les instances CFR

| Instance | Tours P0 | Tours P1 | Cartes posées |
|---|---:|---:|---|
| 2.1d redeal | 2 | 1 | — |
| 2.1e combo | **2** | **1** | **P0 : 6, P1 : 3** |

Séquence codée dans `_advance` : P0 joue → P1 joue → **P0 pioche les 3 restantes et
rejoue** → terminal. P1 ne rejoue jamais.

**Origine.** 9 cartes = 3 + 3 distribuées, 3 en pioche. Trois tours de 3 cartes ne se
partagent pas entre deux joueurs. Ce n'est pas une erreur d'implémentation mais une
**conséquence du choix de 9 cartes**, dont la portée n'a jamais été évaluée.

**Pourquoi c'est bloquant.** Une instance où un joueur pose deux fois plus de cartes que
l'autre n'est pas une miniature de Courtisans. Les conclusions sur « l'horizon long avec
pioche » sont tirées d'un horizon long **pour un seul joueur**.

### 4.2 Dans le moteur complet

`app/jeu.py::is_done`, critère 3 : « si la pioche est vide et le joueur courant ne peut plus
former un tour complet → terminé, cartes résiduelles défaussées ».

Le test est **par joueur**, pas par tour de table. À 4 joueurs : après 7 tours complets,
84 cartes jouées, 6 restantes. Le joueur 0 pioche 3, le joueur 1 pioche 3, le joueur 2 ne
peut plus → fin. **Les joueurs 0 et 1 ont joué 8 tours, les joueurs 2 et 3 en ont joué 7.**

Le correctif ne touche pas au paquet : tester `len(pioche) < 3 × nb_joueurs` **avant
d'entamer un tour de table**. Voir [01_regles.md](01_regles.md) §3.3.

---

## 5. N4 — La métrique d'exploitabilité

Le chiffre **0.190** n'est pas l'exploitabilité d'un réseau. `DCFR_MEASURE_NET` vaut 0 par
défaut : la métrique loggée est `buffer_exploitability`, une moyenne tabulaire reconstruite
depuis le strategy buffer, qui **retourne la politique uniforme** pour tout info-set absent
du buffer (`deep_cfr_mini.py::buffer_exact_fn`).

Simulation de la collecte de strategy-memories au budget exact du run qui plafonne
(20 itérations × 2000 traversées), sous politique uniforme — donc **borne supérieure** de
couverture, puisqu'une politique convergée concentre le reach et couvre moins :

| traversées p=1 | memories P0 | info-sets P0 distincts | % de 455 092 |
|---:|---:|---:|---:|
| 4 000 | 96 521 | 66 372 | 14.6 % |
| 16 000 | 385 690 | 175 107 | 38.5 % |
| **40 000** (= it.20) | **954 332** | **295 176** | **64.9 %** |

Au moins **35 %** des info-sets jouent uniforme dans la stratégie notée 0.190.

**Pourquoi ça n'avait jamais mordu avant.** Aux briques 1 à 2.1d la couverture était totale
(236/236, puis 12 484/12 484) : la métrique était honnête et les comparaisons valides. À
455 092 info-sets elle ne l'est plus.

**Conséquence.** La conclusion « mur de variance, donc ESCHER/DREAM » du `rapport_expert.md`
§34 repose sur un chiffre non comparable à ceux des briques précédentes. Elle est
**suspendue** jusqu'au diagnostic de la phase 3.

---

## 6. Performance : où est le goulot

| Mesure | Valeur | Machine |
|---|---:|---|
| Traversée exhaustive avec encodage | **10 500** états/s | 2 vCPU |
| Playout avec encodage | 14 500 états/s | 2 vCPU |
| Traversées Deep CFR | ~830 /s (48 nœuds chacune) | 2 vCPU |
| Itération oracle CFR+ (8,25 M états) | ~7,4 min | machine de dev |

**Goulot : CPU pur, mono-thread, Python. Zéro I/O, zéro GPU.** Points chauds :
`_canon_perm` (brute-force sur 6 permutations, chacune reconstruisant une string `_repr`
complète) et le clonage d'état pyspiel.

**Pour Deep CFR, l'arbre n'est pas le goulot** : ~15 s par itération sur les ~9 min
observées. Le reste est l'entraînement réseau (1500 pas × 512 × 2 joueurs) que
`device="cpu"` force sur le processeur (N5). Une fois le GPU actif, l'itération devrait
tomber à ~1 min et redevenir dominée par la traversée — d'où la parallélisation des
traversées en réserve.

**Conséquence sur le choix de machine.** Aucune expérience n'est gourmande en VRAM : le plus
gros modèle envisagé (1024², tenseur 190-dim) tient sous 1 Go. **Le critère est le nombre de
cœurs CPU, pas la carte graphique.**

---

## 7. Verdict de code — garder, jeter, refaire

Inventaire complet : **9 299 lignes de Python**.

### 7.1 Garder — le socle (≈ 2 900 lignes)

| Fichier | Lignes | Pourquoi |
|---|---:|---|
| `app/jeu.py` | 719 | **L'actif principal.** Conforme sur tout ce qui a été audité sauf N2. Supporte déjà N joueurs. |
| `app/greedy_bot.py` | 281 | Le greedy PIMC : **l'agent le plus fort jamais mesuré**, bat l'ancien réseau AlphaZero à ~99 %. Baseline indispensable et **seul juge disponible à 3 joueurs**. |
| `streamlit_app/` | 703 | L'interface. C'est le produit livrable. |
| `cfr/solve_mini.py` | 97 | Oracle CFR+ avec checkpoint/reprise vérifié exact. |
| `cfr/deep_cfr_mini.py` | 204 | Runner Deep CFR. À corriger (N4, N5, N6), pas à jeter. |
| `cfr/diag_strategy_buffer.py`, `plot_*.py`, `run_combo_chain.sh` | 247 | Diagnostic, graphes, orchestration. |
| `tests/` moteur : `test_action_mapper`, `test_assassin`, `test_card_ownership`, `test_game_engine` | 466 | Tests de règles valides, à étendre. |
| `documentations/` | 5 380 | **Intégralement.** Résultat négatif AlphaZero documenté, preuve que la canonicalisation est lossless, pièges OpenSpiel, correctifs WSL. Ce qui coûterait le plus cher à réapprendre. |

### 7.2 Jeter — l'appareil AlphaZero (≈ 4 800 lignes)

| Fichier | Lignes | Pourquoi |
|---|---:|---|
| `app/mcts_network.py` | **1 556** | Le plus gros fichier du dépôt. Abandonné sur résultat négatif documenté. |
| `app/augmentation.py` | 186 | Augmentation de données pour AlphaZero. |
| `scripts/` (19 fichiers) | **2 228** | Benchmark, DAgger, discriminateurs, cross-tables, BC greedy. Leurs conclusions sont dans `rapport_expert.md` ; le code ne resservira pas. |
| `tests/` AlphaZero : `test_batched_mcts`, `test_pimc`, `test_target_mcts`, `test_augmentation`, `test_arena`, `test_assassin_heuristic` | 856 | Testent du code supprimé. |

> **Poser un tag `alphazero-final`** sur le dernier commit contenant ce code avant de le
> retirer. Le résultat négatif reste consultable, le dépôt de travail redevient lisible.

### 7.3 Refaire — les instances CFR (≈ 1 555 lignes)

| Fichier | Lignes | Pourquoi |
|---|---:|---|
| `cfr/courtisans_{mini,assassin,redeal,combo}.py` | **1 254** | Quatre copies manuelles. À remplacer par **un générateur paramétré**. |
| `cfr/check_*.py`, `count_infosets.py` | 301 | Scripts ponctuels lancés à la main, jamais rejoués. À transformer en **suite de tests automatique**. |

---

## 8. Décision : on repart du projet, pas de zéro

**Problème.** Les instances CFR sont non conformes aux règles. Faut-il repartir d'un dépôt
vierge ?

**Options.** (a) dépôt neuf, tout réécrire ; (b) garder le dépôt, purger le code mort,
réécrire la couche instances.

**Choix : (b).**

**Justification contrastive.** Ce qui a de la valeur ici n'est pas le code mais `app/jeu.py`,
le greedy, et les **5 380 lignes de documentation** — dont un résultat négatif complet qui a
coûté deux mois. Un dépôt neuf oblige à réécrire un moteur qui est correct et à réapprendre
des pièges déjà payés. Les défauts constatés sont **localisés dans une seule couche** : les
1 254 lignes d'instances copiées à la main. Réécrire cette couche coûte quelques jours ;
réécrire le projet coûte des semaines pour un gain nul.

**Limite.** Garder le dépôt impose la discipline de la phase 0 — purge du code mort et suite
de tests de conformité — sans quoi on garde aussi les habitudes qui ont produit N1 et N3.

---

## 9. Reproduire cet audit

| Mesure | Script | Durée |
|---|---|---:|
| Injectivité de l'encodage | `audit_injectivity.py` (exhaustif) ou `audit_injectivity_sharded.py` (par lots) | ~15 min |
| Couverture du strategy buffer | `measure_buffer_coverage.py` | ~3 min |
| Impact du meurtre obligatoire | `pass_impact.py` | ~2 min |
| Inventaire de code | `find . -name "*.py" \| xargs wc -l` | — |

Ces scripts sont à intégrer à la suite de tests en phase 0 : un audit qui ne se rejoue pas
automatiquement se périme.
