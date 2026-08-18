# Phase 2 — Hypothèse et instrument des quatre mesures

**Écrit et commité AVANT toute mesure**, règle 1 du §2 de
[05_protocole_experimental.md](../documentations/05_protocole_experimental.md). Ce document ne
contient **aucun chiffre mesuré en phase 2** : uniquement ce qui sera mesuré, comment, ce qui
sera conclu selon le résultat, et ce que le résultat n'établira pas.

Les chiffres de la phase 1 qui y figurent sont cités comme tels, avec leur source
(`documentations/06_journal_decisions.md`, entrée du 18/08). Les chiffres de dimensionnement
statistique sont des **calculs de plan**, pas des mesures : ils sont recalculables par la
commande donnée au §9.

Instance mesurée : **`entrainement-3j`** — `mesure/instance.py`, `ENTRAINEMENT_3J` —
`familles=4`, les 5 rôles, `exemplaires=2`, `joueurs=3`. Elle n'est pas choisie ici : elle est
close par la phase 1. Arithmétique, à vérifier par la mesure et non à supposer :
`4 × 5 × 2 = 40` cartes ; `40 // (3 × 3) = 4` tours par joueur ; `3 × 3 × 4 = 36` cartes
jouées ; `40 − 36 = 4` cartes jamais piochées ; `12` poses par partie, `4` par siège, donc
`4` cartes au banquet, `4` en domaine propre et `4` en domaine adverse par siège et par
partie.

---

## 0. Ce que la phase 2 mesure, et l'ordre des dépendances

| Mesure | Objet | Campagne |
|---|---|---|
| **M1** | avantage de siège sous jeu uniformément aléatoire | A |
| **M2** | variance du score final, et le nombre de parties qu'elle impose | A |
| **M3** | winrate du greedy contre l'aléatoire | B |
| **M4** | fréquence de B1–B7 chez le greedy — et chez l'aléatoire | A et B |

**M1 et M2 partagent la campagne A**, M3 et M4 la campagne B : ce sont les mêmes parties, lues
par des compteurs différents. Mesurer la variance sur d'autres parties que l'avantage de siège
n'apporterait rien et interdirait de croiser les deux.

**M4 est mesuré sur les deux campagnes.** « Le greedy fait B4 dans 12 % des nœuds » n'est pas
interprétable sans savoir ce que le hasard donne : la ligne de base des comportements a besoin
de **deux** points, le hasard et le greedy, sinon la comparaison de la phase 3 se fera contre
un seul chiffre sans échelle. C'est le même argument que celui qui justifie M3.

---

## 1. « Parties appariées » — la définition, et pourquoi elle est vide sur M1

Le protocole écrit : « la même donne est rejouée avec les agents permutés à chaque position ».
À trois sièges il y a `3! = 6` permutations d'un triplet d'agents étiquetés.

### 1.1 L'appariement est vide quand les trois politiques sont identiques

La campagne A oppose **trois agents uniformément aléatoires**. Permuter trois copies de la même
politique ne produit pas trois parties différentes de la même donne : ça produit trois parties
dont les lois sont identiques. L'appariement du protocole **ne supprime aucune variance** ici,
parce qu'il n'y a aucun effet d'agent à séparer de l'effet de siège.

Pire : c'est l'objet même de M1 qui l'interdit. Un avantage de siège sous politiques identiques
**est** une asymétrie structurelle — ordre de jeu, et quelles cartes d'une pioche fixée
arrivent à quel siège. Neutraliser les sièges par permutation détruirait exactement la quantité
mesurée. On ne neutralise pas ce qu'on mesure.

**Ce que je retiens donc pour la campagne A** : le plan à 6 réplicats de politique par donne,
qui est littéralement le plan à 6 permutations du protocole quand les agents sont
interchangeables, et qui donne un compte divisible par 6.

| | |
|---|---|
| Donnes | **1 667**, `Engine.reset(seed)`, `seed = 0 … 1666` |
| Réplicats par donne | **6**, indices `r = 0 … 5` |
| Parties | **1 667 × 6 = 10 002** |
| Aléa de politique | `random.Random(2_000_000 + 6 × seed + r)`, une instance par partie, distincte de la donne |
| Bloc de contrôle | mêmes règles, `seed = 10 000 … 11 666`, rejoué pour comparer deux blocs disjoints |

`10 000` n'est pas divisible par 6. **10 002 est retenu, et non 9 996**, parce qu'aucun seuil du
protocole ne dépend du sens de l'arrondi et qu'il vaut mieux dépasser la cible que la manquer.

### 1.2 L'appariement est réel sur M3, et c'est là qu'il sert

La campagne B oppose **un greedy à deux aléatoires** (arbitrage validé, §4.2). Le triplet n'est
plus interchangeable : il y a exactement **3 assignations distinctes** du greedy aux sièges, les
deux autres sièges étant occupés par la même politique aléatoire. Rejouer chaque donne avec le
greedy en siège 0, 1 puis 2 **neutralise l'avantage de siège par construction** : la moyenne du
greedy sur les 3 parties d'une donne ne contient plus d'effet de siège, quel que soit cet effet.

| | |
|---|---|
| Donnes | **3 334**, `seed = 0 … 3333` |
| Assignations par donne | **3**, le siège du greedy `g = 0, 1, 2` |
| Parties | **3 334 × 3 = 10 002** |
| Aléa de politique | `random.Random(3_000_000 + 3 × seed + g)`, partagé par les deux sièges aléatoires |
| Aléa de départage du greedy | `random.Random(3_500_000 + 3 × seed + g)`, §5.4 |

C'est ce plan qui est **appliqué inconditionnellement** dans toutes les phases suivantes
(arbitrage validé, §4.3) : on neutralise, on ne teste pas s'il valait la peine de neutraliser.

### 1.3 L'effet de plan, à mesurer et non à annoncer

Les 6 réplicats d'une même donne partagent la pioche : les parties d'une donne ne sont **pas
indépendantes**. La formule iid `SE = √(p(1−p)/n)` n'est donc pas exacte, et **je n'annonce pas
le sens de l'écart** — dans un plan apparié, la corrélation intra-donne réduit la variance d'un
contraste entre sièges autant qu'elle peut gonfler celle d'un taux marginal.

**L'instrument est un bootstrap par donne** : rééchantillonnage avec remise des **1 667
donnes** (et non des 10 002 parties), chaque donne tirée entrant avec ses 6 réplicats,
`B = 10 000` rééchantillons, `random.Random(2_500_000)`. Le même bootstrap est appliqué à
la campagne B sur ses 3 334 donnes.

Ce qui est **publié comme chiffre**, pour chaque statistique et chaque campagne :

| Chiffre | Définition |
|---|---|
| Variance bootstrap | `Var_boot` de la statistique, sur les `B` rééchantillons |
| Variance iid | `Var_iid` de la même statistique sous l'hypothèse d'indépendance des parties |
| **Effet de plan** | `Var_boot / Var_iid` — un rapport, sans signe supposé |
| **Taille d'échantillon effective** | `n_eff = n / (Var_boot / Var_iid)`, `n = 10 002` |

Les seuils du §2 sont calculés sur `Var_iid` **avant** la mesure — c'est ce que permet un plan
écrit d'avance — puis **recalculés sur `Var_boot`** dans le compte rendu. Les deux sont publiés
côte à côte. Si l'effet de plan s'écarte de 1 de plus de 20 %, le compte rendu conclut sur les
seuils bootstrap et le dit explicitement.

---

## 2. M1 — Avantage de siège

### 2.1 Hypothèse

> **H1 — La position de départ n'avantage aucun siège de façon décisive.**
>
> Sous jeu uniformément aléatoire par les trois joueurs, sur 10 002 parties issues de
> 1 667 donnes, la part de victoire de chaque siège ne s'écarte pas de `1/3` au-delà de ce
> que le hasard d'échantillonnage explique.

**Falsifiable** : trois proportions confrontées à un intervalle fixé d'avance.

**Ce que j'attends si H1 est vraie.** Les trois parts dans `33,33 % ± 1,38 pt`, et le gain
moyen `returns()` de chaque siège dans `0,00 ± 0,03`.

**Ce que j'attends si H1 est fausse.** Le siège 0 favorisé : il joue le premier, donc il pose
la première carte de chaque famille au banquet — celle qui sort une famille de l'Indifférence
— et il pioche en premier dans une pioche non épuisée. *SUPPOSÉ, avant mesure*, un écart
inférieur à 2 points ; je n'ai aucun argument pour en prédire le signe avec confiance, et je ne
prétends pas en avoir un.

**Interdit quelle que soit l'issue** : modifier l'instance, modifier le moteur, modifier un
seuil après avoir vu le chiffre.

### 2.2 Deux statistiques, deux niveaux neutres — et ils ne sont pas les mêmes

C'est le point sur lequel un lecteur se trompera s'il n'est pas écrit ici.

| Statistique | Définition | **Niveau neutre** |
|---|---|---|
| **Gain moyen** | moyenne de `returns()[siège]` sur les parties | **0,00** exactement, par la somme nulle du §5.2 des règles, tenue par l'invariant I5 |
| **Part de victoire fractionnée** | `1/k` pour chacun des `k` vainqueurs ex æquo d'une partie, `0` sinon, moyenné sur les parties | **33,33 %** exactement : les parts somment à 1 sur les trois sièges, à chaque partie |
| Part de victoire stricte | `1` si vainqueur unique, `0` sinon | **strictement inférieur à 33,33 %**, et inconnu d'avance : il vaut `(1 − P(ex æquo))/3` |

**Un greedy à `+0,05` de gain moyen n'est pas un greedy médiocre** : c'est un greedy qui gagne
5 % de l'écart maximal à somme nulle. Un greedy à `0,05` de part de victoire, lui, serait
catastrophique. Les deux chiffres ne se lisent pas sur la même échelle et le compte rendu les
étiquette systématiquement.

**La part de victoire fractionnée est la statistique du seuil de M1**, parce que le seuil du
protocole — « si un siège gagne plus de 38 % des parties » — est écrit dans ces unités-là, et
qu'on répond à un seuil dans ses propres unités. La part stricte est rapportée à côté ; elle ne
peut pas servir de seuil, son niveau neutre n'étant pas `1/3`. Le gain moyen est rapporté comme
statistique primaire de siège, parce que son niveau neutre est exact et non estimé.

### 2.3 Les trois seuils, et ce que chacun discrimine

Sous H1, chaque part de victoire fractionnée a un écart-type par partie de
`√(1/3 × 2/3) = 47,14 pt`, donc `SE = 0,4714 pt` à `n = 10 002` (calcul iid, à corriger par
l'effet de plan du §1.3).

| Seuil | Origine | En erreurs-type | Ce qu'il laisse passer |
|---|---:|---:|---|
| **38,00 %** | §3 du protocole, phase 2 | **9,90** | un siège à 35 %, statistiquement certain à 3,54 erreurs-type, **passe sans être signalé** |
| **34,55 %** | détection bilatérale à 99 %, non corrigée | 2,576 | rien au-delà de 1,21 pt, mais gonfle le risque de faux positif : trois sièges testés |
| **34,72 %** | détection bilatérale à 99 %, **Bonferroni sur 3 sièges** | 2,935 | rien au-delà de 1,38 pt, au risque global de 1 % |

**Le seuil retenu pour conclure est 34,72 %**, et les trois sont rapportés. Le seuil du
protocole est rapporté tel quel, avec son nombre d'erreurs-type : il ne s'agit pas de le
remplacer de ma seule autorité mais de publier ce qu'il discrimine.

**Ce seuil constate un fait, il ne décide plus rien.** La permutation systématique des sièges
est appliquée inconditionnellement à partir de la campagne B (§1.2), donc l'issue de M1 ne
conditionne aucune décision de la phase 3. M1 reste à établir parce que c'est un **fait du jeu**
— combien vaut le siège 0 — pas parce qu'il faut décider s'il vaut la peine de neutraliser.

### 2.4 À quel nombre de parties la mesure devient décisive

**Une taille d'échantillon n'a pas de valeur unique : elle dépend de la formule.** Ce point
a été trouvé par un désaccord entre deux implémentations — 19 parties sur 1 456 — et il est
écrit ici parce qu'un `n` publié sans sa formule n'est pas reconstructible. Les trois calculs
sont donc rendus, avec leurs paramètres, par `python -m mesure.dimensionnement`.

Paramètres communs : risque global bilatéral 1 %, Bonferroni sur 3 sièges — donc
`0,00166667` par queue —, `z_risque = 2,935199`, `z_puissance = 0,841621`,
`p₀ = 1/3`, `√(p₀q₀) = 0,471405`.

| Méthode | Écart-type au terme de puissance | siège à 38 % | siège à 35 % |
|---|---|---:|---:|
| normale, σ **sous H₀** aux deux termes | `√(p₀q₀)` | 1 456 | 11 412 |
| normale, σ **sous H₁** au terme de puissance | `√(p₁q₁)` | 1 475 | 11 472 |
| exact binomial, premier franchissement | aucune | 1 501 | 11 539 |
| **exact binomial, stable — la référence** | aucune | **1 531** | **11 629** |

`√(p₁q₁)` vaut `0,485386` à 38 % et `0,476970` à 35 % : les deux dépassent `√(p₀q₀)`, parce
que 0,38 et 0,35 sont plus proches de 0,5 que ne l'est 1/3. **La forme à σ sous H₀
sous-estime donc `n`**, et c'est elle que j'avais employée sans la nommer. Les deux formes se
lisent dans la littérature ; celle sous H₁ est la forme des manuels pour un test de
proportion, le terme de puissance décrivant la loi sous l'alternative.

**L'exact départage, et il est plus grand que les deux.** Le test réel porte sur un compte
entier : on rejette si `K ≥ c`, où `c` est le plus petit entier dont la queue supérieure sous
`p₀` ne dépasse pas le risque. Aucun `c` n'égale le risque nominal, donc la queue atteinte
est strictement en dessous : le test est **conservateur**, et il coûte plus de parties que la
normale ne l'annonce. À `n = 10 002` la valeur critique vaut **`K ≥ 3 474`**, soit 34,73 % —
qui recoupe le seuil normal de 34,72 % du §2.3 au compte près, et c'est le contrôle croisé
qui lie les deux paragraphes : ils décrivent le même test.

**La puissance exacte n'est pas monotone en `n`.** Elle avance en dents de scie, parce que
`c` saute d'une unité. À 38 % elle franchit 80 % dès `n = 1 501`, puis **redescend** en
dessous à 1 502, 1 503, 1 505… jusqu'à 1 530 ; à 35 %, la dent de scie court sur 90 unités,
de 11 539 à 11 628. **Le chiffre publié est donc le plus petit `n` à partir duquel la
puissance ne redescend plus** — 1 531 et 11 629 —, parce qu'un `n` publié doit tenir pour
lui-même *et* pour tout ce qui le suit. Le premier franchissement est publié à côté pour que
la dent de scie soit visible plutôt que cachée.

**Lecture.** L'effet que le seuil du protocole désigne — un siège à 38 % — est établi dès
**1 531 parties**, donc 10 002 parties en sont plus de six fois le nécessaire, et c'est ce
surplus que le seuil de 38 % gaspille : MESURÉ, la puissance exacte contre un siège à 38 % à
`n = 10 002` vaut **100,0 %**. Le seuil est mal placé non parce que l'échantillon est petit,
mais parce qu'il ne signale que ce qui est déjà hors de doute. À l'inverse, **aucun des trois
calculs n'est atteint par 10 002 parties pour un effet de 1,67 pt** : la puissance exacte
contre un siège à 35 % y vaut **71,5 %** — la normale annonçait 72,6 %, elle est
anti-conservatrice ici aussi. Un siège à 35 % sera donc détecté un peu moins de trois fois
sur quatre, et le compte rendu écrira cette puissance à côté du résultat plutôt que de
conclure « aucun avantage détecté » comme si l'absence de détection valait absence d'effet.

Ces chiffres supposent des parties indépendantes ; ils sont recalculés sur `Var_boot`
(§1.3) dans le compte rendu.

---

## 3. M2 — Variance du score final

### 3.1 Hypothèse

M2 n'est pas une hypothèse à falsifier : c'est un **dimensionnement**. L'énoncé pré-inscrit est
donc ce que la mesure doit produire, et le seuil porte sur sa **précision**, pas sur sa valeur.

> **H2 — La variance du score final est assez grande pour que le nombre de parties, et non le
> soin de l'instrument, soit le facteur limitant de toute conclusion ultérieure.**

*Attendu, SUPPOSÉ depuis la phase 1* : écart-type du score final ≈ **4,4 points par siège**
(chiffre de la phase 1, entrée du 18/08 du journal, sous la même politique et la même
instance, sur 1 000 parties). M2 le remesure sur 10 002 parties et lui donne un intervalle.

### 3.2 Ce qui est mesuré

| Quantité | Définition opératoire | Support |
|---|---|---|
| Variance du score | `state.scores()` à l'état terminal, par siège et toutes places confondues | 10 002 parties × 3 sièges |
| Variance du gain | `state.returns()`, idem | idem |
| **Corrélation intra-donne** `ρ` | corrélation des scores d'un même siège entre deux réplicats d'une même donne | 1 667 donnes |
| Étendue, mode, valeurs distinctes | comme les critères D1–D4 de la phase 1, pour comparabilité | par siège |
| Contrôle de somme nulle | `sum(returns()) == 0` sur chaque partie | 10 002 parties |

`ρ` est la quantité utile : c'est elle qui dit de combien un plan apparié réduit le nombre de
parties nécessaires. La variance d'un contraste apparié vaut `2σ²(1 − ρ)` contre `2σ²` sans
appariement, donc le gain de parties est un facteur `1/(1 − ρ)`. Le protocole affirme au §1 que
l'appariement « divise par cinq à dix le nombre de parties nécessaires », ce qui correspond à
`ρ ∈ [0,8 ; 0,9]` — **cette affirmation n'est appuyée par aucune mesure du dépôt**, et M2 est
l'occasion de la vérifier. Si `ρ` mesuré est loin de cet intervalle, c'est le §1 du protocole
qu'il faut corriger, et le compte rendu le signalera.

### 3.3 Le produit livré : le tableau de dimensionnement

Le livrable de M2 n'est pas un écart-type, c'est un **tableau utilisable par les phases
suivantes** : pour chaque écart `Δ` de gain moyen qu'on voudrait établir, le nombre de parties
nécessaire, apparié et non apparié, à 99 % bilatéral et 80 % de puissance.

`Δ ∈ {0,02 ; 0,05 ; 0,10 ; 0,20 ; 0,30}`, avec `σ` et `ρ` mesurés. Le tableau porte aussi la
ligne inverse : **à 1 000 parties appariées, quel `Δ` est détectable** — parce que c'est
exactement le budget que le §3 du protocole fixe à la phase 3, et qu'il faut savoir si son
seuil de « > 55 % contre le greedy » y est atteignable.

### 3.4 À quel nombre de parties la mesure devient décisive

L'erreur relative sur un écart-type vaut `1/√(2n)`. À `n = 10 002`, elle vaut **0,707 %** :
l'écart-type est connu à sept millièmes près en relatif. Il l'est déjà à **5 % relatif dès
`n = 200`**. M2 est donc **décidé très largement avant la fin de la campagne** — et c'est
pourquoi son contenu réel est le tableau du §3.3 et la corrélation `ρ`, pas la variance
elle-même. `ρ` est le chiffre qui a besoin des 1 667 donnes ; son intervalle vient du bootstrap
du §1.3.

---

## 4. M3 — Winrate du greedy contre l'aléatoire

### 4.1 Hypothèse

> **H3 — Le greedy bat l'aléatoire.**
>
> Sur 10 002 parties appariées, un greedy opposé à deux aléatoires obtient un gain moyen
> `returns()` **strictement supérieur à 0,00** et une part de victoire fractionnée
> **strictement supérieure à 33,33 %**, les deux intervalles à 99 % excluant leur niveau
> neutre.

**Ce que j'attends si H3 est vraie.** *SUPPOSÉ*, gain moyen dans `[0,2 ; 0,6]`, part de
victoire fractionnée dans `[45 % ; 70 %]`. Je n'ai aucune mesure de ce dépôt sur laquelle
appuyer ces bornes : le greedy de l'ancienne lignée était mesuré sur un moteur non conforme, et
son chiffre n'est comparable à rien ici. C'est un SUPPOSÉ, écrit pour être démenti.

**Ce que j'attends si H3 est fausse.** Un greedy au niveau neutre signalerait soit un défaut de
son évaluation, soit — et c'est le cas intéressant — que maximiser l'écart sur un tour ne
corrèle pas au score final dans cette instance, le signe des points ne se décidant qu'à la fin
(§2.1 des règles). Un greedy **sous** le niveau neutre signalerait un défaut, et le compte
rendu le traiterait comme un bug à diagnostiquer, pas comme un résultat.

### 4.2 Composition, et le second chiffre

**Référence : 1 greedy contre 2 aléatoires** (arbitrage validé). C'est la lecture naturelle
d'« un agent parmi des adversaires aléatoires », et c'est la composition que la phase 3
utilisera pour son propre plancher.

**Rapportée à côté : 2 greedys contre 1 aléatoire.** 3 334 donnes × les 3 sièges de
l'aléatoire = 10 002 parties, `random.Random(5_000_000 + 3 × seed + siège_aléatoire)`. Ce
chiffre-là n'est pas décoratif : à trois joueurs, deux agents identiques peuvent se nuire
mutuellement ou se renforcer sans le savoir (§2.4 des règles, alliances implicites), et l'écart
entre les deux compositions est la seule mesure qui le dise.

### 4.3 Niveaux neutres — les deux, à nouveau

Rappel explicite, parce que c'est ici que la confusion coûte le plus cher :
**`0,00` pour le gain moyen `returns()`** (somme nulle, invariant I5), et **`33,33 %` pour la
part de victoire fractionnée**. Le chiffre de référence du protocole — « si le greedy est à
60 %, un agent à 65 % n'est pas impressionnant » — est une part de victoire, et son point de
comparaison est **33,33 %, pas 50 %** : à trois joueurs, 50 % est déjà une domination.

### 4.4 À quel nombre de parties la mesure devient décisive

`σ` du gain par partie sera mesuré en M2 ; borne a priori `|returns()| ≤ 1` donc `σ ≤ 1`, et
*SUPPOSÉ* `σ ≈ 0,7` au vu du support `{+1 ; +0,25 ; 0 ; −0,5}`. Sous ces valeurs, en plan
apparié avec `ρ` mesuré, à 99 % bilatéral et 80 % de puissance :

| Écart de gain moyen à établir | N, formule |
|---|---|
| `Δ` | `n ≥ ((2,576 + 0,842) σ √(2(1−ρ)) / Δ)²` pour un contraste apparié |

Les nombres sont remplis dans le compte rendu avec `σ` et `ρ` mesurés — les écrire ici avec un
`σ` supposé produirait un chiffre qui a l'air d'un fait. *SUPPOSÉ, ordre de grandeur* : à
`σ = 0,7` et sans appariement, un `Δ = 0,10` demande ~570 parties, donc **10 002 parties
tranchent très largement**, et le surplus sert M4, dont les dénominateurs sont plus fins.

---

## 5. Le greedy — sa règle, son architecture, et la preuve qu'il ne triche pas

### 5.1 Il n'existe pas dans ce dépôt, et il n'est pas porté

`git show origin/cfr-pivot:app/greedy_bot.py` — 281 lignes — importe `app.jeu.GameEnv`, le
moteur non conforme que ce projet a réécrit, plus `torch` et le réseau AlphaZero abandonné. Il
est **lu pour comprendre la règle, jamais porté** : son `_pick_target_heuristic` ne rendait
`None` que si la liste de cibles était vide, si bien qu'**aucune politique de ce projet n'a
jamais refusé de tuer** (§4 des conventions). Un greedy qui ne sait pas refuser rend **B4
inmesurable**.

Il est réécrit dans un paquet à lui, **`agents/`**, jamais dans `courtisans/`, que le §4 des
conventions interdit à toute heuristique.

### 5.2 La règle, énoncée au §7.1 des règles

> Maximiser l'**écart de score obtenu sur le tour en cours**, comme si la partie s'arrêtait là.

Rendue opératoire. Soit `C_i` l'ensemble des cartes posées vivantes dont le joueur `i`
**connaît l'identité** — faces visibles, plus ses propres Espions. L'évaluation d'une position
par `i` est :

```
evaluer(C, i) = points(C, statuts(C), n)[i] − max_{j ≠ i} points(C, statuts(C), n)[j]
```

calculée par `courtisans.rules.statuts` et `courtisans.rules.points`, **sur `C_i` et non sur le
plateau réel** : les Espions adverses n'y figurent pas, donc valent zéro. C'est exactement le
défaut que le §7.1 des règles attribue au greedy — « il traite une carte cachée comme neutre ».
Ce n'est pas une approximation d'implémentation, c'est la définition de l'agent.

Réutiliser `rules.statuts` et `rules.points` plutôt que de recoder le décompte est imposé par
le §2 des conventions : une seule source de vérité. Le greedy n'a **aucune** logique de règle à
lui.

### 5.3 Un arbitrage que je tranche, et je dis pourquoi

Le « tour en cours » inclut-il la résolution des Assassins que le greedy vient de poser ?

| Variante | Choix de pose | Ce qu'elle suppose |
|---|---|---|
| **G-combiné** — *retenue* | argmax sur les poses de `evaluer` **après résolution optimale de ses propres Assassins**, à horizon un tour | le tour est un coup, §2.3 et §3.2 des règles |
| G-naïf — *rapportée* | argmax sur les poses de `evaluer` après les 3 cartes seulement, puis chaque cible choisie gloutonnement ensuite | la pose et le ciblage sont deux décisions |

**Je retiens G-combiné.** Le §2.3 des règles est explicite : « poser une carte chez un
adversaire sans avoir décidé ce que fera l'Assassin du même tour n'a aucun sens », et les trois
cartes plus les effets d'Assassin « forment un seul coup ». Surtout, le §7.1 énumère ce que le
greedy **ne fait pas** — anticiper les retournements, calculer sa marge, raisonner sur les
Espions adverses, tenir compte du résidu, construire une alliance, planifier sur plusieurs
tours — et *combiner à l'intérieur d'un tour n'y figure pas*. G-naïf serait un greedy plus
faible que celui que les règles décrivent, et M3 sous-estimerait alors l'échelle, ce qui est
l'erreur exactement inverse de celle que la phase 2 doit éviter.

`M3(G-naïf)` est rapporté à côté, sur les mêmes donnes, pour que l'écart entre les deux
lectures soit un chiffre et non un débat.

### 5.4 Le départage EST un élément de l'instrument

Plusieurs actions atteignent souvent le même argmax. **La règle qui les sépare n'est pas un
détail d'implémentation : elle produit directement un des chiffres de M4**, et elle est donc
pré-inscrite ici et non pas seulement écrite dans le code.

Prendre le plus petit indice d'action serait déterministe **et biaisé** : l'indice d'une action
de pose encode l'assignation, la position au banquet et l'adversaire visé
(`rules.decoder_action_pose`, numération à base mixte, l'adversaire variant le plus vite).
Choisir systématiquement le plus petit indice fabriquerait une préférence stable pour une
position et un adversaire — donc **un artefact directement dans B2, B3 et B6**.

| | |
|---|---|
| Départage de référence | **tirage uniforme** dans l'ensemble des argmax, `random.Random` dédié (§1.2) |
| Variante de robustesse | plus petit indice, rapportée sur M3 seulement |

#### 5.4.1 La conséquence sur B4, et elle est lourde

Tuer un dos adverse **ne change pas** `evaluer` : un dos ne figure pas dans `C_i`, donc son
retrait est sans effet. Refus et meurtre-d'un-dos sont donc **exactement à égalité**. Ce n'est
pas une approximation : c'est structurel.

**Donc quand toutes les cibles d'un nœud sont des dos, TOUTES les actions du nœud sont à
égalité, refus compris. Ce n'est plus le greedy qui décide, c'est le départage.** Avec un
tirage uniforme sur `k` dos plus le refus, le greedy refuse avec probabilité exactement
`1/(k+1)` — et ce nombre est une propriété **de la règle de départage**, pas du jeu ni de
l'heuristique.

Or c'est ce nombre-là qui sortirait comme ligne de base de B4. Un lecteur lirait « le greedy
refuse de tuer dans X % des cas » là où le calcul dit « mon départage a tiré au sort X % du
temps ». **C'est mot pour mot la faute de la phase 1** : la phrase et le calcul n'ont pas le
même sujet grammatical.

Trois conséquences, pré-inscrites :

1. **B4 se décompose en trois nombres**, pas deux (§6.4) ;
2. **la part des nœuds de ciblage où toutes les cibles sont des dos est mesurée et publiée.**
   Si elle est élevée, B4 mesure surtout le départage, et le rapport le dit à cet endroit-là ;
3. le même découpage s'appliquera à l'agent de la phase 3, sinon sa comparaison à cette ligne
   de base n'aurait pas de sens.

### 5.5 Il ne lit pas la vue de dieu — par construction, puis par test

**Architecture.** Le greedy ne reçoit **jamais** un `State`.

```
courtisans.engine.State  →  agents/perception.py  →  Perception  →  agents/greedy.py
        (vue de dieu)          l'unique module            (données)      (décision)
                               qui touche State
```

`Perception` contient **exactement** :

| Champ | Justification de sa légitimité |
|---|---|
| les cartes posées vivantes que le décideur connaît — visibles + ses propres Espions | c'est `infoset._vue_du_joueur`, le support de `information_state_string`, tenu par l'invariant I7 |
| le nombre de dos adverses par zone et par poseur | bloc `dos_adverses_*` du tenseur d'observation |
| sa main | bloc `main` du tenseur |
| le résidu par `(famille, rôle)`, morts exclus | bloc `residu` du tenseur |
| les cartes mortes | la défausse est **publique**, §4.1 des règles |
| tours restants par siège, taille de pioche, phase | blocs `tours_restants`, `pioche`, `phase` |
| ses actions légales | savoir commun, contrôle C17 |
| en ciblage : pour chaque indice de cible, son **apparence publique** — `(famille, rôle)` ou `None` pour un dos —, sa zone, son rang public, et un drapeau « c'est mon propre Espion, je sais ce que c'est » | arbitrage du 17/08 : un dos n'est jamais nommé, il est situé et numéroté par `rules.rang_public_dans_zone`, dont la docstring démontre que le rang ne dépend d'aucune information cachée |

**Ce que `Perception` ne contient pas** : la pioche, les mains adverses, l'identité des Espions
adverses, `scores()`, `returns()`, et le résultat brut de `cibles_courantes()` — qui rend de
vrais `CartePosee`, identité des dos comprise, et qui est **rédigé** par l'adaptateur avant
d'atteindre le greedy.

Le greedy ne peut donc pas non plus simuler par `clone()` + `apply()` : il n'a pas d'état à
cloner. Il simule ses candidats **dans son propre modèle de vue**, avec
`rules.decoder_action_pose`, `rules.cibles_valides`, `rules.statuts`, `rules.points` — des
fonctions de règles, publiques pour tous les joueurs.

**Trois preuves, toutes exécutables** (écrites à l'étape 2, avant la mesure) :

| # | Preuve | Ce qui la rend rouge |
|---|---|---|
| **P1 — structurelle** | la signature de `greedy.choisir` prend une `Perception`, jamais un `State` ; un test relit le module de décision et échoue s'il mentionne `vue_privilegiee`, `_pioche`, `_mains`, `scores`, `returns` ou `cibles_courantes` | une régression qui rebrancherait le greedy sur l'état |
| **P2 — runtime** | pendant l'appel à `greedy.choisir`, `State.vue_privilegiee` est remplacée par une fonction qui **lève** ; la partie doit se jouer entière | tout accès à la vue de dieu au moment de décider |
| **P3 — invariance** | sur une donne fixée, on permute (a) l'identité des Espions adverses déjà posés, (b) l'ordre des cartes jamais piochées, (c) les mains adverses — et l'action choisie doit être **identique** | toute dépendance à une information que le greedy n'a pas |

P3 est la preuve forte : P1 et P2 disent qu'il ne *lit* pas la vue de dieu, P3 dit que sa
décision n'en *dépend* pas, ce qui couvre aussi une fuite indirecte.

### 5.6 Il sait refuser de tuer — deux cas construits à la main

Le §4.1 des règles fait du refus une action à part entière. Deux positions où la règle du
greedy **détermine** son coup, calculées de tête et assertées :

| # | Position | Coup imposé par la règle |
|---|---|---|
| **R-refus** | l'Assassin du greedy est dans **son propre domaine**, dont la seule cible valide est **son propre Noble** d'une famille en Lumière | **refuser** : tout meurtre retire `+2` de son propre score, donc baisse strictement l'écart. Refus **strict**, pas par départage |
| **R-meurtre** | l'Assassin du greedy est dans **son propre domaine**, dont la seule cible valide est un Noble d'une famille en **Obscurité**, posé chez lui par un adversaire | **tuer** : le meurtre retire `−2` de son score, donc augmente strictement l'écart |

Les deux cas sont construits par `Engine.reset_depuis_pioche`, pas par un seed cherché — un
seed qui produit le cas serait une coïncidence non reproductible sous un changement de moteur.

---

## 6. M4 — B1 à B7, sept définitions opérationnelles

### 6.0 Le support de chaque compteur, tranché avant de compter

C'est ici que la phase 1 s'est fait prendre : un chiffre juste dont la phrase ne décrivait pas
le calcul. Chaque compteur porte donc, écrit d'avance, **sur quelle vue il est défini**, en
réutilisant `mesure.partie.Vue` — dont la docstring établit déjà que **« la vue publique n'est
la vue de personne »** : un joueur connaît en plus l'identité des Espions qu'il a lui-même
posés.

| Vue | Ce qu'elle est | `mesure.partie` |
|---|---|---|
| **Décideur** | ce que sait le joueur qui choisit : visibles + ses propres Espions | `Vue.du_joueur(i)` |
| **Savoir commun** | ce que les trois joueurs voient à la fois : visibles seulement | `Vue.PUBLIQUE` |
| **Vraie** | la vue de dieu, Espions cachés compris | `Vue.VRAIE` |

**Règle d'arbitrage, appliquée aux sept :** un comportement est une **décision**, et une
décision se prend sur ce que le décideur sait. **La vue du décideur est donc primaire partout
où le compteur qualifie un choix.** Le savoir commun est rapporté à côté chaque fois qu'il
diffère, parce qu'il répond à une autre question — *le coup était-il contesté aux yeux d'un
observateur ?* — et que les deux sont défendables. La vue vraie est rapportée là où elle borne
le possible.

**Une exception, et elle est de règle, pas de goût :** ce qui **paie** se calcule sur la vue
vraie, puisque tous les Espions sont retournés avant le décompte (§4.2 et §5 des règles). Un
compteur dont l'énoncé contient « à la fin, la famille ne rapporte plus » est donc sur la vue
vraie pour cette clause-là, et sur la vue du décideur pour ses clauses de décision. B1 et B7
sont dans ce cas, et leur définition dit lequel de leurs morceaux est sur quelle vue.

### 6.1 B1 — Planifier un retournement

> **Règles §7.2 :** nourrir une famille chez un adversaire, puis la basculer en Obscurité en
> fin de partie.

**Définition retenue — B1-motif.** Un **couple ordonné d'actions du même joueur `i`** sur une
même famille `f` et un même adversaire `j` :

1. à `t₁`, `i` pose une carte de famille `f` dans le domaine de `j`, alors que `f` est en
   **Lumière ou Indifférente** dans la **vue de `i`** — nourrir n'a de sens que si ce n'est pas
   déjà un poison ;
2. à `t₂ > t₁`, `i` exécute une action qui **fait baisser** l'influence de `f` : poser une
   carte de `f` en **Disgrâce** au banquet, ou faire tuer par un de ses Assassins une carte de
   `f` en **Estime** ;
3. au décompte, `f` est **Indifférente ou en Obscurité** dans la **vue vraie** — c'est le
   statut qui paie ;
4. au décompte, `j` détient encore au moins une carte de `f` **vivante** dans son domaine —
   sinon le poison n'a atteint personne.

| | |
|---|---|
| Dénominateur primaire | **parties** — « dans quelle part des parties le motif apparaît » |
| Dénominateur secondaire | **couples (joueur, famille)** : `3 × 4 = 12` par partie |
| Vue | clauses 1 et 2 sur `Vue.du_joueur(i)` ; clauses 3 et 4 sur `Vue.VRAIE` |
| Grain | `Grain.TOUR` primaire, `Grain.FIN` rapporté — comme la phase 1 |

**Définitions concurrentes, dont le chiffre sera publié à côté :**

| Variante | Ce qu'elle change | Sens de l'écart attendu |
|---|---|---|
| **B1-tentative** | supprime les clauses 3 et 4 : le motif compte même s'il rate | **plus grand** — compte les tentatives échouées |
| **B1-strict** | clause 3 exige **Obscurité**, pas Indifférente | **plus petit** — l'encadré du §2.2 des règles dit pourtant que le seuil qui compte est l'Indifférence |
| **B1-collectif** | `t₁` et `t₂` peuvent être de joueurs **différents** | **beaucoup plus grand** — et ne mesure plus une intention |
| **B1-savoir-commun** | clause 1 sur `Vue.PUBLIQUE` | inconnu, à mesurer |

### 6.2 B2 — Placer l'Assassin là où il pourra servir

> **Règles §7.2 :** au banquet sur une famille contestée plutôt que dans un domaine sans
> enjeu ; distribution des zones, comparée au greedy.

**Définition retenue — B2-contestée.** Parmi les poses qui placent un Assassin, la part de
celles dont la **zone de destination** contient, au moment de la pose, au moins une cible
valide (non-Garde, vivante) appartenant à une famille dont l'influence `|d|` est **≤ 1** dans
la **vue du poseur**. `|d| ≤ 1` est la fragilité définie par le §2.2 des règles : à `d = ±1`,
une carte standard annule et un Noble inverse.

| | |
|---|---|
| Dénominateur | **poses d'Assassin**, pas parties. Un Assassin par pose au maximum sur cette zone, jusqu'à 3 par tour |
| Vue | **`Vue.du_joueur(poseur)`** primaire ; `Vue.PUBLIQUE` et `Vue.VRAIE` rapportées |
| Rapporté aussi | la **distribution complète** des 4 destinations — banquet-Estime, banquet-Disgrâce, domaine propre, domaine adverse — que le §7.2 demande explicitement |

**Pourquoi la vue du poseur et pas le savoir commun.** Un joueur qui a lui-même posé un Espion
au banquet dans la famille `f` voit une zone plus — ou moins — contestée que le savoir commun.
Compter au savoir commun répondrait à « le coup était-il contesté aux yeux d'un observateur »,
et non à « le décideur croyait-il placer son Assassin là où il servirait ». Le comportement B2
est une décision : c'est la vue du décideur qui la qualifie. Les deux chiffres sont publiés, et
leur écart est lui-même un résultat — il mesure de combien le savoir privé déplace le jugement.

**Définitions concurrentes :** **B2-banquet**, la seule part des Assassins posés au banquet
— beaucoup plus grande, et elle ne dit rien de l'enjeu ; **B2-fragile-2**, seuil `|d| ≤ 2`
— plus grande ; **B2-cibles**, la part des Assassins posés dans une zone ayant au moins une
cible valide, sans condition d'enjeu — plus grande encore, c'est la borne haute.

### 6.3 B3 — Fabriquer une alliance

> **Règles §7.2 :** nourrir un joueur sur une famille où l'IA est elle-même exposée ;
> corrélation entre les familles données et celles que l'IA détient.

**Définition retenue — B3-exposé.** Une pose par `i` d'une carte de famille `f` dans le domaine
de `j`, alors que le domaine de `i` contient déjà au moins une carte de `f` **vivante** connue
de `i`. `i` est alors **objectivement allié de `j` sur `f`** au sens du §2.4 des règles : les
deux ont intérêt à ce que `f` finisse en Lumière.

| | |
|---|---|
| Dénominateur | **poses en domaine adverse** : `4` par siège et par partie, `12` par partie |
| Vue | **`Vue.du_joueur(i)`** — l'exposition de `i` est ce que `i` en sait ; les Espions adverses posés chez lui ne lui sont pas identifiables. `Vue.VRAIE` rapportée |
| Niveau de hasard | à mesurer sur la campagne A : c'est **le** chiffre sans lequel B3 n'est pas interprétable, une politique aléatoire produisant le motif par coïncidence |

**Définitions concurrentes :** **B3-corrélation**, la lecture littérale du §7.2 — corrélation,
sur toute la partie, entre le multi-ensemble de familles donné à `j` et celui que `i` détient,
mesurée par un indice de recouvrement ; elle donne **un nombre par partie et par couple**, pas
un taux d'action, et ne distingue pas une alliance construite d'une coïncidence de pioche.
**B3-simultané**, qui exige que `f` soit en Lumière dans la vue de `i` au moment de la pose —
plus petite, plus proche d'une intention.

### 6.4 B4 — Refuser de tuer quand le meurtre coûterait

**Le dénominateur, d'abord — c'est là que la lecture littérale est vide.** Refuser est
**toujours** légal (§4.1, arbitrage R2), donc « fréquence des situations où refuser est
possible » vaut 100 % par construction. Le dénominateur est donc les **nœuds de ciblage
offrant au moins une cible**, où refuser est un **choix** et non un constat. La phase 1 a
mesuré que ces nœuds sont **82,53 % des 7 206 nœuds de ciblage** de 1 000 parties aléatoires :
prendre tous les nœuds gonflerait mécaniquement le taux de refus d'un facteur `1/0,8253`.

**Trois nombres, et le partage entre les deux premiers est ce qui distingue un comportement
d'un tirage au sort** (§5.4.1) :

| # | Chiffre | Ce qu'il est | Dénominateur |
|---|---|---|---|
| **B4-strict** | refus où **tout** meurtre disponible baisse **strictement** l'écart évalué | **un comportement** | refus |
| **B4-départage** | refus où refuser était **à égalité** avec au moins un meurtre | **un tirage au sort** | refus |
| **B4-contre-nature** | refus où au moins un meurtre était **strictement meilleur** | **un défaut** | refus |

Les trois somment à 100 % des refus par construction, et le compte rendu **vérifie cette
identité** — c'est un contrôle, pas une déduction.

**B4-contre-nature doit valoir exactement 0 chez le greedy**, puisque `choisir` prend un
argmax : un refus strictement dominé est impossible. **Il est publié quand même**, comme
contrôle — un zéro qu'on n'imprime pas n'est pas un zéro vérifié, et l'enseignement de la
phase 1 est qu'un zéro absolu se confronte à un cas construit à la main avant d'être écrit
(cas `R-refus`, §5.6). Pour un agent entraîné en phase 3, ce même nombre cesse d'être
trivialement nul et devient un diagnostic.

**Deux chiffres de contexte, sans lesquels les trois précédents ne s'interprètent pas :**

| Chiffre | Dénominateur | Pourquoi |
|---|---|---|
| **part des nœuds tout-dos** — nœuds dont **toutes** les cibles sont des dos | nœuds de ciblage à ≥ 1 cible | c'est la part de B4 que le **départage** produit, et non l'heuristique. Si elle est élevée, le rapport le dit à cet endroit |
| **taux de refus brut** | nœuds à ≥ 1 cible | la grandeur que le §7.2 des règles demande littéralement, publiée **avec** sa décomposition en trois |

**Symétrique, rapporté aussi : B4-meurtre-coûteux**, la part des meurtres exécutés alors que
tout meurtre baissait strictement l'écart évalué. Chez le greedy elle doit valoir **0 par
construction**, pour la même raison que B4-contre-nature.

**Sur quelle évaluation « coûterait » est-il jugé.** Sur `agents.greedy.evaluer_actions`, donc
sur l'écart d'un tour dans la vue du décideur — **y compris pour l'agent de la phase 3**, dont
la fonction de valeur propre ne servira PAS d'étalon ici. C'est un choix, et il est fait pour
la comparabilité : deux agents jugés par deux étalons différents ne se comparent pas. Le prix
est qu'un agent qui refuse par anticipation d'un retournement — donc pour une bonne raison à
horizon long — comptera dans **B4-contre-nature**, et ce cas-là devra être lu comme un signe
de planification, pas comme un défaut. Écrit ici, avant de mesurer, pour ne pas être découvert
au moment où le chiffre dérangera.

### 6.5 B5 — Se méfier des Espions

> **Règles §7.2 :** ne pas traiter une majorité serrée comme acquise s'il reste des cartes
> cachées ; comportement face aux majorités à une carte d'écart.

**Définition retenue — B5-renfort.** Parmi les nœuds de pose où **toutes** les conditions
suivantes tiennent :

- une famille `f` a une influence `|d| = 1` au banquet dans la **vue du décideur** ;
- il y a au moins **un dos** au banquet que le décideur ne peut pas identifier, donc la vraie
  influence de `f` peut déjà différer de ce qu'il voit ;
- le décideur a en main au moins une carte de famille `f` ;

la part des nœuds où il **renforce le côté déjà favorable** — pose une carte de `f` du côté du
signe de `d` — plutôt que de consolider ou de jouer ailleurs.

| | |
|---|---|
| Dénominateur | **nœuds de pose satisfaisant les trois conditions**, compté et publié : c'est un sous-ensemble étroit, et son effectif conditionne la précision |
| Vue | `Vue.du_joueur(i)` pour `|d| = 1` — un joueur qui a posé l'un des dos en sait plus ; `Vue.PUBLIQUE` rapportée |

**Ce que la ligne de base du greedy vaudra, et pourquoi il faut la publier quand même.** Le
greedy traite un dos comme absent (§5.2) : la présence d'un dos **n'entre pas** dans sa
décision. Sa méfiance est donc **nulle par construction**, et B5-renfort chez lui mesure
seulement à quelle fréquence son évaluation myope l'amène à renforcer. Ce n'est pas un défaut
de mesure : c'est le point de comparaison dont la phase 3 a besoin, et il doit être écrit comme
tel plutôt que déduit.

**Définition concurrente : B5-pire-cas**, où `|d|` est remplacé par la marge pire cas du §2.6
des règles — `d` diminué de 1 par dos du côté favorable, un dos étant toujours un Espion donc
de valeur 1. Elle sélectionne d'autres nœuds, et son chiffre est publié à côté.

### 6.6 B6 — Exploiter la pioche connue

> **Règles §7.2 :** jouer différemment en fin de partie, quand l'incertitude tombe ;
> comparaison du style entre début et fin de partie.

**Définition retenue — B6-distance.** Sur un ensemble fixé de catégories d'action, la
**distance de variation totale** entre la distribution observée au **tour 1** et celle du
**tour 4** — le dernier — pour un même agent. Les catégories, fixées avant de mesurer :

| Groupe | Catégories |
|---|---|
| Banquet | Estime / Disgrâce |
| Domaine adverse | cadeau (famille en Lumière dans la vue du poseur) / neutre / poison (Obscurité) |
| Ciblage | refus / meurtre |

| | |
|---|---|
| Dénominateur | **poses du tour 1** et **poses du tour 4**, `4 × 10 002` chacune pour le siège greedy... rapporté par groupe et par tour, jamais agrégé |
| Vue | `Vue.du_joueur(i)` pour la catégorisation cadeau/poison |
| Contrôle | les tours 2 et 3 sont rapportés aussi, pour qu'on voie si l'écart est monotone ou un saut |

**Elle n'est pas nulle chez le greedy, et ce n'est pas une preuve de compréhension.** L'état du
plateau change avec le tour : au tour 4, plus de cartes sont posées, plus de familles ont un
statut tranché, donc un agent à horizon un tour joue **mécaniquement** différemment sans rien
savoir de la pioche. **C'est exactement pourquoi la ligne de base est nécessaire** : la phase 3
ne pourra conclure que sur l'**écart** entre la distance de son agent et celle du greedy, jamais
sur la distance seule.

**Définition concurrente : B6-dernier-contre-reste**, tour 4 contre les tours 1–3 agrégés —
plus stable statistiquement, mais elle mélange trois états de jeu différents dans son terme de
comparaison.

### 6.7 B7 — Ne pas défendre ce qui est déjà sûr

> **Règles §7.2 :** sur une famille dont la marge est hors d'atteinte compte tenu du résidu et
> des tours restants, jouer ailleurs ; fréquence des cartes « gaspillées ».

**« Hors d'atteinte », rendu mesurable.** Pour une famille `f`, dans la vue du décideur `i`, à
un instant donné, le **poids de bascule encore mobilisable contre `f`** est le minimum de deux
bornes :

- **borne de matériel** : somme des valeurs des cartes de `f` encore en circulation d'après le
  bloc `residu` — morts exclus, §4.1 des règles — plus `2` par carte de `f` vivante du côté
  favorable qu'un Assassin encore en circulation pourrait tuer ;
- **borne d'occasions** : `tours_restants × joueurs` poses au banquet encore possibles, chacune
  faisant varier `d` d'au plus `2` (un Noble).

`f` est **hors d'atteinte** si `|d| >` ce minimum : aucune suite de coups légaux ne peut plus
changer son statut.

**Définition retenue — B7-gaspillage.** Part des poses au banquet qui placent une carte de
famille `f` **du côté déjà favorable** d'une `f` **hors d'atteinte**.

| | |
|---|---|
| Dénominateur | **poses au banquet** : `4` par siège et par partie |
| Vue | `Vue.du_joueur(i)` — le résidu est ce que le décideur peut calculer ; `Vue.VRAIE` rapportée comme borne |
| Rapporté aussi | la **fréquence des occasions** : part des poses au banquet où au moins une famille est hors d'atteinte. Sans elle, un B7 bas peut vouloir dire « il ne gaspille pas » ou « l'occasion ne s'est pas présentée » |

**Définition concurrente : B7-lumière**, toute pose renforçant une famille déjà en Lumière,
sans condition de portée — **nettement plus grande**, et c'est la définition qu'on obtient en
oubliant la borne, donc celle qui ferait croire à un gaspillage massif. Publier les deux est le
seul moyen de montrer ce que la borne retire.

### 6.8 Dénominateurs attendus, et précision

*DÉDUIT de l'arithmétique de l'instance et des chiffres de la phase 1 — à confirmer par la
mesure, jamais à supposer confirmé.*

| Compteur | Dénominateur | Effectif attendu, siège greedy, 10 002 parties |
|---|---|---:|
| B1 | parties | 10 002 |
| B2 | poses d'Assassin | *à mesurer* — l'Assassin est 1 rôle sur 5 |
| B3 | poses en domaine adverse | 40 008 |
| B4-strict / -départage / -contre-nature | refus | *à mesurer* — dépend du taux de refus |
| B4 brut, part tout-dos | nœuds de ciblage à ≥ 1 cible | ~20 000 *(déduit de 82,53 % × ~2,4 nœuds/siège/partie)* |
| B5 | nœuds de pose à `\|d\| = 1` + dos + carte en main | *à mesurer* — le plus étroit des sept |
| B6 | poses du tour 1, poses du tour 4 | 40 008 chacun, par groupe |
| B7 | poses au banquet | 40 008 |

**Objectif de précision, fixé d'avance** : demi-largeur de l'intervalle de Clopper-Pearson à
99 % **≤ 2 points** pour tout compteur dont le dénominateur dépasse 3 000. Un compteur dont le
dénominateur tombe sous 3 000 est publié **avec son intervalle et un avertissement**, et non
arrondi comme les autres — le cas attendu est B5.

---

## 7. Ce que ces mesures n'établiront PAS

Écrit avant la mesure, pour ne pas l'être après coup en fonction du résultat.

1. **Le greedy ne planifie rien, et B1 chez lui ne mesure pas une planification.** Son horizon
   est d'**un tour, par construction** (§7.1 des règles, et §5.2 ci-dessus : son évaluation ne
   regarde que l'écart obtenu maintenant). Le motif B1 — nourrir puis basculer — apparaîtra
   chez lui **par coïncidence** : deux actions séparées, chacune localement optimale, qui
   forment après coup la figure d'un plan. La ligne de base est bonne pour ça, c'est
   précisément la fréquence du hasard structuré qu'il faut connaître. Mais **« le greedy
   planifie des retournements dans X % des parties » serait faux**, et c'est cette phrase-là
   qu'il faut empêcher d'être écrite plus tard. Le chiffre s'intitule *fréquence du motif B1*,
   jamais *fréquence de planification*.
2. **Le même avertissement vaut mot pour mot pour B3.** Le greedy ne modélise pas l'intérêt
   qu'il crée chez l'autre en lui donnant une carte (§7.1). Un B3 non nul chez lui mesure la
   coïncidence entre ce qu'il détient et ce qu'il donne, produite par sa main et par son
   évaluation myope — **pas une alliance fabriquée**.
3. **B1 a un plafond que rien ne franchira.** La phase 1 a mesuré que **7,40 % des parties**
   (74/1 000, seeds 0–999, grain tour) portent une perte d'acquis qu'**aucun des trois sièges**
   ne pouvait voir : deux Espions de même famille posés par deux joueurs différents suffisent,
   et alors même le poseur d'un des deux n'a pas la vue complète. Ces retournements sont
   **invulnérables à toute planification, par n'importe quel agent**. Une ligne de base B1
   basse doit se lire en le sachant : c'est un **plafond du mesurable**, pas un défaut d'agent.
   Le compte rendu remesure ce taux sur les seeds de la campagne A, pour que le plafond soit
   établi sur les mêmes parties que la ligne de base.
4. **Une part de B4 mesure le départage, pas le jeu.** Sur un nœud dont toutes les cibles
   sont des dos, l'évaluation du greedy est plate : c'est la règle de départage du §5.4 qui
   choisit, et elle refuse avec probabilité `1/(k+1)` sur `k` dos. Le taux de refus brut n'est
   donc **pas** entièrement un comportement, et c'est pourquoi il ne se publie jamais seul.
5. **M3 ne dit pas que le greedy est fort.** Il dit qu'il bat le hasard. « Battre le greedy est
   un plancher, pas un objectif » (§7.1 des règles), et aucun chiffre de la phase 2 ne borne la
   distance entre le greedy et un bon joueur.
6. **M1 ne dit rien de l'avantage de siège sous d'autres politiques.** Un avantage mesuré sous
   jeu uniformément aléatoire est une propriété de la structure **plus** de cette politique. Un
   agent entraîné peut avoir un avantage de siège différent, ou l'inverse. La permutation
   systématique (§1.2) rend la question sans conséquence pratique — elle ne la résout pas.
7. **M2 ne dimensionne que des comparaisons de gain moyen.** Les fréquences de comportement de
   M4 ont leurs propres dénominateurs et leurs propres intervalles (§6.8) ; le tableau du §3.3
   ne s'y applique pas.
8. **Aucune de ces mesures ne dit quoi que ce soit de `complet-3j`** — 6 familles, 3
   exemplaires, 10 tours. Rien ici ne se transporte par un facteur.
9. **La phase 2 ne valide pas le moteur.** Elle le suppose conforme ; c'est la phase 0 qui
   l'établit, et elle est close.
10. **Les seuils et les définitions de ce document sont des propositions.** Les chiffres bruts
   du compte rendu permettront de recalculer toute décision sous d'autres définitions sans
   relancer une mesure. C'est la raison pour laquelle chaque définition concurrente est publiée
   avec son chiffre, et non seulement nommée.

---

## 8. Budget, et garde-fou de la règle 2

| Campagne | Parties | Coût attendu | Plafond |
|---|---:|---|---|
| A — aléatoire | 10 002 | *SUPPOSÉ* ~16 s, par extrapolation du 1,6 ms/partie mesuré en phase 1 | 5 min |
| A — bloc de contrôle | 10 002 | idem | 5 min |
| B — greedy, référence | 10 002 | **MESURÉ 2,4 min** — 14,64 ms par partie sur 200 parties. *SUPPOSÉ* avant l'étape 2a : 8 à 35 min, soit un ordre de grandeur de trop | **2 h** |
| B — G-naïf, 2-greedys | 2 × 10 002 | idem | 2 h chacune |

**Mon estimation était fausse d'un ordre de grandeur, dans le sens sûr.** 2,4 min mesurées
contre 8 à 35 min supposées. Un SUPPOSÉ démenti par le bas est une bonne nouvelle, mais c'en
est un quand même, et la phase 3 s'appuiera sur ces estimations : le compte rendu final le
consigne comme un écart d'estimation, pas comme un succès.

Le protocole annonce « environ une heure » pour la phase 2. **Un dépassement du plafond est un
défaut d'instrumentation, pas un résultat**, et il est signalé comme tel — c'est le garde-fou
de la règle 2 du §2 du protocole. Checkpoint toutes les 1 000 donnes, avec le compte partiel
écrit sur disque, de sorte qu'une campagne interrompue soit exploitable et reprenable.

---

## 9. Reproductibilité

Toute la phase 2 est reproductible depuis les seeds de ce document. Aucun chiffre du compte
rendu n'aura d'autre origine.

| Élément | Valeur |
|---|---|
| Instance | `mesure.instance.ENTRAINEMENT_3J` |
| Campagne A, donnes | `seed = 0 … 1666` ; contrôle `10 000 … 11 666` |
| Campagne A, politique | `random.Random(2_000_000 + 6 × seed + r)`, `r = 0 … 5` |
| Campagne B, donnes | `seed = 0 … 3333` |
| Campagne B, aléatoires | `random.Random(3_000_000 + 3 × seed + g)`, `g` = siège du greedy |
| Campagne B, départage greedy | `random.Random(3_500_000 + 3 × seed + g)` |
| Composition 2-greedys | `random.Random(5_000_000 + 3 × seed + siège_aléatoire)` |
| Bootstrap | `B = 10 000`, `random.Random(2_500_000)`, rééchantillonnage **par donne** |
| Calculs de plan du §2.4 | `python -m mesure.dimensionnement`, écrit à l'étape 1 |
| Loi binomiale exacte | `mesure/binomiale.py`, extrait de `rapport.py` — deux implémentations et un contrôle qui exige leur accord à 1e-12 |

Les plages de seeds de politique sont disjointes par construction :
`2_000_000 … 2_010_001` pour la campagne A principale, `2_060_000 … 2_070_001` pour son
contrôle, `3_000_000 … 3_010_001` pour la campagne B. Aucune partie ne partage son aléa de
politique avec une autre.

---

## 10. Deux réserves de la phase 1, et trois trous du protocole — hors phase 2

Signalés séparément parce que **ce n'est pas cette phase**, et traités sans être mélangés à ses
résultats.

**Réserves de la phase 1, dans `mesure/` que la phase 2 rouvre :**

1. rien ne relie la définition unique de l'instance dans `mesure/instance.py` à la description
   indépendante de `tests/outils.py` — l'indépendance de l'oracle est justifiée, l'absence de
   garde-fou contre la dérive ne l'est pas ;
2. la section 6 du rapport de la phase 1 ne répète pas le **grain** sur ses deux blocs de
   comptage.

Je proposerai un traitement des deux, **annoncé comme tel dans une section distincte du compte
rendu**, sans qu'aucun chiffre de la phase 2 n'en dépende.

**Trous du protocole, à remonter au journal — cinq, à corriger par l'auteur seul** (je ne
modifie aucun document de `documentations/` sans accord ; ce sont des propositions, pas des
écritures).

| # | Trou dans `05_protocole_experimental.md` | Statut |
|---|---|---|
| 1 | « **retournement** » n'est défini nulle part, et le go/no-go de la phase 1 le chiffre | phase 1 ; définition R2 pré-inscrite, deux tours d'audit |
| 2 | « **distribution non dégénérée** » idem | phase 1 ; quatre critères D1–D4 pré-inscrits |
| 3 | « **situations où refuser de tuer est possible** » idem, et sa lecture littérale est **vide** — refuser est toujours légal, donc la fréquence vaut 100 % par construction | phase 1 ; dénominateur corrigé, repris ici en §6.4 |
| 4 | « **parties appariées** » n'est défini nulle part, et il est **vide** quand les politiques comparées sont identiques | phase 2, §1.1 ci-dessus |
| 5 | « l'appariement **divise par cinq à dix** le nombre de parties nécessaires » (§1) implique `ρ ∈ [0,8 ; 0,9]` et **n'est appuyé par aucune mesure du dépôt** | phase 2, §3.2 ci-dessus |

**Le cinquième est le seul qui soit un chiffre**, et c'est ce qui le distingue des quatre
autres : les quatre premiers sont des termes non définis, celui-ci est une affirmation
quantitative publiée sans mesure. M2 la vérifie — et si `ρ` tombe loin de `[0,8 ; 0,9]`, c'est
le §1 du protocole qu'il faut corriger, pas la mesure.

Le §3 du protocole présente en outre « 20 cartes ou 40 cartes » comme un arbitrage à trancher
en phase 1 : il n'en est pas un, la variante à 20 cartes étant refusée à la construction par
le plancher `tours ≥ 3` du §8 des règles. Signalé par la phase 1, non encore corrigé.

---

## 11. Trois enseignements de méthode, à remonter au journal

Écrits ici, avant la mesure, parce qu'ils sont nés d'une faute commise **sur ce document** et
corrigée avant qu'une seule partie soit jouée. Ils valent pour toutes les phases suivantes.

### 11.1 Un seuil de puissance se publie sur son premier `n` STABLE

« Le plus petit `n` dont la puissance dépasse 80 % » est une **coïncidence d'arrondi sur la
valeur critique entière**. La puissance exacte d'un test de proportion n'est pas monotone en
`n` : elle avance en dents de scie, parce que `c` saute d'une unité. MESURÉ, contre un siège à
38 % : elle franchit 80 % à `n = 1 501`, retombe à 79,12 % à 1 502, et ne cesse de redescendre
qu'à partir de **1 531** — douze creux après le franchissement. Contre un siège à 35 %,
quarante-cinq creux, le dernier à +90.

**Un `n` publié doit tenir pour lui-même et pour tout ce qui le suit.** Le premier `n` stable
est donc la bonne réponse, et publier le franchissement à côté est mieux encore : ça rend la
dent de scie visible au lieu de la cacher.

**Cette distinction n'est nulle part dans le protocole**, et tout seuil de puissance des
phases 3 à 6 y est exposé — en particulier le « décisif dès 300 parties si l'écart dépasse
10 points » du §3, phase 3, qui n'a été calculé par aucune formule nommée.

### 11.2 Un contrôle croisé vaut mieux que deux chiffres

La valeur critique exacte à `n = 10 002` vaut `K ≥ 3 474`, soit **34,73 %**, qui recoupe au
compte près le seuil normal Bonferroni de **34,72 %** du §2.3. Rien ne le vérifiait avant. Ce
genre de contrôle établit que **deux paragraphes décrivent le même test** — ce qu'aucune
vérification des deux chiffres pris séparément ne peut montrer. À faire systématiquement quand
deux sections d'un même document produisent un nombre qui devrait coïncider.

### 11.3 « Un chiffre porte son échantillon » s'applique aussi à une formule

L'enseignement de la phase 1 était écrit pour des seeds, une politique et un grain. Il vaut à
l'identique pour une **formule** : mes 1 456 parties n'étaient pas un nombre faux, c'était un
nombre **sous-spécifié** — rien en lui ne disait quel écart-type entrait au terme de
puissance, et deux implémentations honnêtes divergeaient de 19 parties sans que rien ne le
signale.

La parade n'est pas la vigilance, c'est le type : `Variance` est un enum, et
`parties_pour_puissance_proportion` **ne peut pas être appelée sans nommer** l'écart-type
retenu. Rendre obligatoire ce qui manquait ferme la classe entière de fautes, au lieu du seul
cas trouvé.
