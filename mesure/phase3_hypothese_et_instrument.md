# Phase 3 — Hypothèse et instrument du premier agent

**Écrit et commité AVANT tout entraînement et avant toute mesure d'agent**, règle 1 du §2 de
[05_protocole_experimental.md](../documentations/05_protocole_experimental.md).

Ce document ne contient **aucun chiffre mesuré sur un agent entraîné**. Il contient : ce qui
sera mesuré, comment, avec quel budget, ce qui sera conclu selon le résultat, et ce que le
résultat n'établira pas. Les chiffres qui y figurent sont de deux sortes, et elles sont
distinguées ligne à ligne :

- des **mesures de terrain** faites sur le greedy mis à la place de l'agent — c'est la
  population de l'hypothèse nulle, et c'est elle qui dimensionne un test ;
- des **calculs de plan**, recalculables par la commande du §9.

Instance : **`entrainement-3j`** — `mesure/instance.py`, `ENTRAINEMENT_3J` — `familles=4`,
les 5 rôles, `exemplaires=2`, `joueurs=3`. Elle est close par la phase 1 et n'est pas rouverte.
`4 × 5 × 2 = 40` cartes ; `40 // 9 = 4` tours par joueur ; `36` cartes jouées ; `4` jamais
piochées.

> **Le lien entre l'instance mesurée et sa description indépendante est désormais tenu par un
> test qui le dit** — `tests/mesure/test_instance_ne_derive_pas.py`. C'était la réserve laissée
> ouverte par la phase 1 : le garde-fou existait, mais aucun des 21 cas qui tombaient sous
> dérive ne nommait la cause.

---

## 0. L'hypothèse

**Écrite avant toute mesure, et falsifiable.**

> **H.** Un agent entraîné en self-play avec un pool d'adversaires figés, sur `entrainement-3j`,
> obtient contre **deux greedys**, sièges permutés, un **gain moyen strictement positif**,
> borne basse de son IC 99 % bootstrap par donne comprise.

**Si H est vraie**, la borne basse de l'IC 99 % du gain moyen est `> 0` sur les 6 000 parties du
§2.2, et la part de victoire fractionnée est au-dessus de 33,3333 %.

**Si H est fausse**, deux cas se distinguent et ils ne disent pas la même chose :

- l'IC 99 % **contient 0** — *non conclu au budget*. Ce n'est **pas** « l'agent ne bat pas le
  greedy » : c'est « à 6 000 parties, un écart inférieur à +0,0243 n'est pas séparable de zéro » ;
- la borne **haute** est `< 0` — l'agent est **battu** par le greedy, et c'est un résultat
  établi.

**Ce qui rendrait H invérifiable**, et qui est donc testé d'abord : que l'instrument lui-même
soit mal calibré. Le §3 le vérifie sur un cas dont la réponse est connue, **avant** que le
premier agent ne soit entraîné.

---

## 0 bis. Le seuil, et celui qu'il remplace

Le seuil de cette phase s'énonçait **« > 55 % contre le greedy sur 1 000 parties appariées »**,
avec une bande 45–55 % et un plancher à 45 %, jusqu'au 20/08/2026. **Ces trois nombres sont des
intuitions de jeu à deux joueurs**, et le texte ne nommait ni la composition de la population ni
l'unité du taux. À trois joueurs la part de victoire fractionnée vaut **33,33 %** au neutre : un
agent à 45 % est très au-dessus du hasard, pas en dessous.

**Le seuil en vigueur, et le seul contre lequel cette phase est jouée :**

| | |
|---|---|
| **Composition mesurée** | **un agent contre deux greedys**, sièges permutés systématiquement |
| **Juge** | le **gain moyen**, niveau nul exactement **0,0000** |
| **Seuil** | **borne basse de l'IC 99 % bootstrap par donne strictement positive** |
| **Rapporté à côté** | part de victoire fractionnée, comparée à **33,3333 %** |
| **Jamais un seuil** | la part de victoire **stricte** — son niveau nul vaut `(1 − P(trois ex æquo))/3` et dépend de la fréquence des ex æquo |

**Un agent contre deux aléatoires est mesuré en parallèle, pour le garde-fou seul.** Cette
composition n'est pas un juge : le greedy y est déjà à 86,52 % de part fractionnée.

---

## 1. Pourquoi le niveau nul de ce seuil est exact, et ce qui le détruirait

C'est la propriété qui fait exister le seuil, et ni le protocole ni la phase 2 ne l'écrivent.

**Sous l'hypothèse nulle, l'ESPÉRANCE du gain mesuré vaut exactement 0,0000.** Notons `μ_s`
l'espérance du gain du siège `s` dans cette composition. La somme nulle du §5.2 des règles,
tenue par l'invariant I5, donne `μ_0 + μ_1 + μ_2 = 0` **exactement** — c'est vrai partie par
partie. Sous l'hypothèse nulle, l'agent est la même politique que ses deux adversaires :
l'espérance de **son** gain au siège `s` vaut donc `μ_s`. Le plan lui fait occuper chaque siège
**exactement une fois par donne**, donc l'espérance de la moyenne mesurée vaut
`(μ_0 + μ_1 + μ_2)/3 = 0`.

**Ce qui n'est pas vrai, et qu'une première rédaction de `mesure/phase3.py` affirmait.** La
moyenne *réalisée* sur une donne ne vaut pas 0. Les trois traces d'une donne sont **trois
parties différentes** — même pioche, aléas de politique distincts — et non une partie lue trois
fois : l'invariant I5 s'applique aux trois sièges d'**une** partie, pas aux trois parties d'une
donne. C'est la faute du projet, un énoncé exact sur une population que sa phrase ne nomme pas,
et elle a été écrite ici avant d'être relue. Le contre-exemple est figé par
`test_la_somme_sur_les_trois_parties_d_une_donne_n_est_PAS_nulle`.

**Ce que l'espérance exacte apporte.** Le niveau nul n'est **pas estimé**. Pas de population de
référence à mesurer à côté, pas de second échantillon, pas de soustraction entre deux grains —
la faute bloquante du tour 1 de la phase 2 n'a **pas de prise** sur ce plan.

**Et ce qui la détruirait : le déséquilibre des sièges.** Un plan qui donnerait un siège deux
fois et un autre zéro fois déplacerait le niveau nul d'un écart entre sièges — et cet écart est
**énorme** dans cette composition. La permutation systématique n'est donc pas une précaution de
forme : elle est ce qui fait exister le seuil.

> **Le chiffre à citer ici est celui de MA composition, et ce n'est pas le +0,1890 du protocole.**
> Le contraste de **+0,1890** entre sièges extrêmes, cité par l'erratum de la phase 2 et par le
> prompt de cette phase, est mesuré sur **un greedy contre deux aléatoires**. Ma composition en
> compte trois. **MESURÉ au §2.2 : l'étendue vaut 0,5735**, soit **trois fois** plus. Une
> première rédaction de ce paragraphe citait 0,189 — un chiffre exact sur une population que sa
> phrase ne nommait pas, écrit avant que la mesure ne soit faite, et corrigé après elle.

---

## 2. Le budget ne s'emprunte pas, et la formule de la phase 2 n'est pas la mienne

Le protocole fixe « 1 000 parties appariées ». Le seul écart de gain détectable publié,
**+0,1013 à 1 000 parties**, l'a été **sous jeu uniformément aléatoire**, avec
`σ(gain) = 0,6652` et `ρ = +0,0066` moyenné sur trois sièges. **Le dépôt ne contient aucune
mesure de `σ` ni de `ρ` sur une population de greedys** — vérifié.

### 2.1 Les deux formules ne dimensionnent pas le même estimand

**C'est le point le plus important de ce paragraphe, et il n'était écrit nulle part.**

| | Phase 2 | Phase 3 |
|---|---|---|
| Estimand | contraste **apparié entre deux agents** | moyenne d'**un échantillon** contre un nul exact |
| Variance | `Var(X_A − X_B) = 2σ²(1 − ρ)` | `Var(moyenne) = σ²(1 + (m−1)ρ)/N` |
| Écart détectable | `z σ √(2(1−ρ)) / √n` | `z σ / √(n/effet)` |
| Rôle de `ρ` | la corrélation est entre les deux termes qu'on **soustrait** | elle est entre les réplicats qu'on **moyenne** |
| **Sens de `ρ`** | `ρ` élevé **réduit** le budget | `ρ` élevé **augmente** le budget |

**Deux conséquences, et la seconde est contre-intuitive.**

1. À `ρ = 0` **et à `σ` identique**, mon écart détectable vaut celui de la phase 2 **divisé
   par exactement `√2`** — le facteur 2 de la variance d'une différence, soit un facteur 2 en
   parties. C'est une **identité algébrique**, pas une mesure : le facteur réel dépend de mon
   `σ` et de mon `ρ`, tous deux mesurés au §2.2, et **il vaut 2,89**.
2. **`ρ` joue en sens inverse dans les deux formules.** Lire « ρ = 0,0066, donc l'appariement
   ne rapporte rien » et en conclure que `ρ` est sans conséquence pour la phase 3 serait faux
   dans le sens le plus coûteux : un `ρ` positif fort me **coûterait** des parties là où il en
   économisait à la phase 2.

Les deux relations sont tenues par
`test_ma_formule_n_est_PAS_celle_de_la_phase_2_et_le_rapport_vaut_racine_de_deux`, qui vérifie
d'abord que ma réimplémentation de **leur** formule rend **leur** chiffre — sans quoi le rapport
de `√2` ne dirait rien.

### 2.2 `σ` et `ρ`, mesurés sur ma composition

**Échantillon : le greedy mis à la place de l'agent** — trois greedys, un seul siège compté,
celui qui tourne. C'est la population de l'hypothèse nulle, donc celle qui dimensionne un test.

**MESURÉ le 20/08/2026**, `uv run python -m mesure.phase3 --donnes 2000` — 2 000 donnes,
seeds `20000` à `21999`, **6 000 parties**, 3 par donne. Aucun agent entraîné n'y figure.

| Grandeur | Valeur | Comparaison |
|---|---:|---|
| `σ(gain)`, siège mesuré | **0,6494** | 0,6652 sous jeu uniformément aléatoire (phase 2, campagne A) |
| `ρ` intra-donne du gain | **−0,1400** | +0,0066 en phase 2 — **et de signe opposé** |
| effet de plan `1 + (m−1)ρ`, `m = 3` | **0,7200** | par décomposition de variance à un facteur |
| effet de plan par **bootstrap** | **0,7223** | route indépendante, écart **0,3 %** |
| `n` effectif à 6 000 parties | **8 307** | plus grand que `n` : le plan **gagne** des parties |

**`ρ` est négatif, et c'est structurel.** Ce n'est pas le même `ρ` que celui de la phase 2, et
il ne mesure pas la même chose : le sien est la corrélation entre **réplicats de politique** sur
une même donne, le mien entre **assignations de siège** sur une même donne. Dans une partie, la
somme des trois sièges vaut 0 ; si une pioche favorise le siège 0, l'agent y gagne quand il
l'occupe et y perd quand il occupe les deux autres. **La permutation des sièges ne fait donc pas
qu'exactifier le niveau nul : elle réduit la variance**, d'un facteur de plan de 0,72.

**Les deux routes vers l'effet de plan concordent** — 0,7200 par l'analyse de variance,
0,7223 par le bootstrap — et elles sont calculées différemment : l'une décompose la variance
inter et intra donne, l'autre rééchantillonne les donnes. C'est le contrôle qui manquait à la
phase 2, où un facteur trois indu avait survécu à deux vérifications qui partageaient le même
dénominateur.

### Le budget qui en découle

| Budget | Écart de gain détectable, 99 % bilatéral, 80 % de puissance |
|---:|---:|
| 500 parties | +0,0842 |
| **1 000 parties** (le nominal du protocole) | **+0,0596** |
| 3 000 parties | +0,0344 |
| **6 000 parties** (mon budget) | **+0,0243** |

| Écart à établir | Parties | Donnes × 3 |
|---:|---:|---|
| +0,02 | 8 867 | 2 956 |
| +0,05 | 1 419 | 473 |
| +0,10 | 355 | 119 |
| +0,20 | 89 | 30 |

**À quel nombre de parties le seuil devient décisif** — c'est l'étape 4 de la boucle du §2 :

- pour un agent à **+0,10** de gain moyen, le seuil est décisif dès **355 parties** ;
- pour un agent à **+0,05**, dès **1 419 parties** ;
- pour un agent à **+0,02**, il faudrait **8 867 parties**, et je ne les budgète pas : un tel
  écart n'est pas ce que la phase 3 cherche.

**Budget pré-inscrit : 2 000 donnes × 3 sièges = 6 000 parties**, écart détectable **+0,0243**.
Soit **six fois** le nominal du protocole en parties. Comparé au **+0,1013** que le protocole
citait pour ce nominal, mon écart détectable est **4,17 fois plus fin**, et ce facteur se
décompose en deux causes distinctes qu'il ne faut pas confondre :

`4,17 = 1,70 × 2,45`

— **1,70** vient de la **formule et de la composition** (un échantillon contre un nul exact,
`σ = 0,6494`, `ρ = −0,1400`), à budget égal de 1 000 parties ; **2,45 = √6** vient du **budget**
seul, 6 000 parties au lieu de 1 000. La première moitié est gratuite, la seconde est payée en
parties.

*Aucune durée n'est citée ici : le §0.2 exige trois passes avec leur étendue, et ce budget n'a
été chronométré qu'une fois.*

**Les seeds de la campagne finale sont `30000+`, disjoints des `20000–21999` de ce
dimensionnement.** Dimensionner et mesurer sur le même échantillon le réutiliserait deux fois.

### Ce que l'emprunt aurait coûté, chiffré

| | |
|---|---:|
| écart détectable à 1 000 parties, formule de la phase 2 | +0,1013 |
| écart détectable à 1 000 parties, **ma composition et ma formule** | **+0,0596** |
| rapport, en taille d'effet | **1,70** |
| rapport, **en parties** | **2,89** |

Décomposition, pour que le lecteur la reconstruise :
`(0,6652 / 0,6494) × √(2 × (1 − 0,0066) / 0,7200) = 1,0243 × 1,6612 = 1,7016`, et
`1,7016² = 2,8954`.

**Emprunter le +0,1013 aurait donc surestimé mon budget d'un facteur 2,89 en parties.** Le
facteur `√2` du §2.1 est celui d'un `ρ` nul et d'un `σ` identique ; le facteur 2,89 est celui
qui est **mesuré**. Les deux sont vrais, sur deux choses différentes, et le second est le seul
qui vaille pour cette phase.

### Un chiffre qui n'était pas attendu : l'avantage de siège est TROIS FOIS celui qu'on cite

| Siège occupé | Gain moyen du greedy, contre deux greedys |
|---|---:|
| siège 0 | **−0,2541** |
| siège 1 | **−0,0703** |
| siège 2 | **+0,3194** |

Somme : **−0,0050**, soit zéro à la précision d'échantillonnage — ce qui vérifie
`μ_0 + μ_1 + μ_2 = 0` sur 6 000 parties.

**Contraste entre sièges extrêmes, apparié par donne : +0,5735, IC 99 % bootstrap
[+0,5218 ; +0,6240]** — **établi**. Chaque donne fournit les trois sièges, donc la différence ne
contient plus la variance de distribution. C'est la même méthode et la même écriture que le
contraste de la phase 2, pour que les deux se lisent l'un contre l'autre.

Le prompt de cette phase et l'erratum de la phase 2 citent **+0,1890**, qui
est le contraste entre sièges extrêmes de la composition **un greedy contre deux aléatoires**.
Dans **ma** composition, l'étendue est **trois fois plus grande** — et proche des **0,5717** que
la phase 2 mesure sur « deux greedys contre un aléatoire ». Plus il y a de greedys, plus le
siège pèse.

**Conséquence directe, et elle renforce le §1 :** l'étendue de siège vaut **0,5735** quand
l'effet cherché est de l'ordre de **0,05**. Le siège pèse plus de **dix fois** l'effet mesuré.
Un plan qui ne donnerait pas chaque siège exactement une fois ne mesurerait pas l'agent.


**Ce que `σ` mesuré ici ne dit pas.** Il est mesuré **sous l'hypothèse nulle**. Un agent
réellement meilleur a une distribution de gain différente, donc un `σ` différent. C'est
**SUPPOSÉ**, ce n'est pas mesuré, et c'est remesuré sur la campagne finale : `mesurer` rend `σ`
à chaque composition, pour que l'écart entre le supposé et le mesuré soit un chiffre et non un
oubli.

### 2.3 La structure du plan, en donnes × sièges

« 1 000 parties appariées » est ambigu : 1 000 parties, ou 1 000 donnes × 3 permutations ? Le
protocole confirme que ce nombre ne me lie pas — mon `n` vient de ma mesure. **Ma structure est
donc écrite explicitement :**

- l'unité de tirage est la **donne**. Trois plages **disjointes**, et elles ne servent pas à
  la même chose : `20000–21999` pour le **dimensionnement et la calibration** du §2.2 et du §3,
  `30000+` pour la **campagne finale** qui juge l'agent, et les seeds `0–3333` et `10000–11666`
  restent ceux de la phase 2. Dimensionner et juger sur le même échantillon le réutiliserait
  deux fois ;
- chaque donne est jouée **3 fois**, l'agent au siège 0, puis 1, puis 2, sur la **même pioche** ;
- `parties = donnes × 3` ;
- le bootstrap rééchantillonne les **donnes**, jamais les parties : tirer des parties
  détruirait la structure qu'on mesure ;
- le plan est **équilibré**, et `mesure.phase3.Campagne` **lève** s'il ne l'est pas — le rapport
  intraclasse et le bootstrap par donne le supposent tous deux.

---

## 3. La calibration de l'instrument, avant de mesurer l'agent

**Un instrument se vérifie sur un cas dont on connaît la réponse.**

Appliqué au greedy mis à la place de l'agent, l'instrument doit produire un IC 99 % qui
**contient 0,0000**. S'il ne le contient pas, **c'est l'instrument qui est faux, pas l'agent**,
et la phase s'arrête là — un seuil dont le niveau nul est mal placé déclarerait vainqueur un
agent qui ne l'est pas.

Ce contrôle est **falsifiable et il peut échouer** : il n'est pas garanti par construction,
puisque seule l'espérance vaut 0 et que l'échantillon est fini. À 99 %, il échoue à tort une
fois sur cent.

**MESURÉ**, même campagne, 2 000 donnes, 6 000 parties :

| | |
|---|---:|
| gain moyen du greedy à la place de l'agent | **−0,0017** |
| IC 99 % bootstrap par donne | **[−0,0195 ; +0,0170]** |
| **contient 0,0000 ?** | **OUI** |
| part de victoire fractionnée | **33,2222 %** (neutre exact **33,3333 %**) |
| part de victoire stricte | 26,6167 % — rapportée, jamais un seuil |

**L'instrument est calibré.** La borne basse vaut −0,0195, donc l'instrument appliqué à un agent
qui ne vaut pas mieux que le greedy **ne le déclare pas vainqueur**.

Et il donne la sensibilité réelle du seuil : la demi-largeur de l'IC vaut **0,0183** à
6 000 parties — `(0,0170 − (−0,0195)) / 2` — donc un agent devra dépasser de l'ordre de
**+0,018** de gain moyen pour que sa borne basse soit strictement positive.

> **Ce +0,018 est un SUPPOSÉ, pas un MESURÉ.** Il transporte la demi-largeur mesurée **sous
> l'hypothèse nulle** vers une campagne où l'agent sera différent, donc où `σ` le sera aussi.
> La demi-largeur réelle sera **remesurée** sur la campagne finale et publiée à côté de
> celle-ci ; si elle en diffère de plus de 10 %, c'est que `σ` a bougé et il faudra le dire.

---

## 4. Le contrôle de collision de tenseurs

**Le réseau est unique et partagé par les trois sièges**, et ce n'est pas une économie : c'est
la symétrie correcte du problème. L'observation est déjà **relative à l'observateur** —
`infoset._relatif`, « 0 c'est moi, 1 le suivant, 2 celui d'après ».

**Mais cette même relativité fait naître un risque.** Si deux nœuds à des positions différentes
dans l'ordre du tour partageaient un tenseur, le réseau partagé serait **plafonné par
construction et rien ne le dirait** — d'autant que l'avantage de siège est massif sous jeu
greedy.

`chaine` est la sérialisation **sans perte** des mêmes blocs que `tenseur` : deux nœuds de même
tenseur et de chaînes différentes sont une collision réelle de l'encodage numérique.

> **C'est un ÉCHANTILLON, pas une preuve.** La preuve exhaustive d'injectivité existe pour
> l'ancienne instance combo, **pas** pour `entrainement-3j`. Le contrôle du pilote le
> 20/08/2026 — 300 donnes, **trois joueurs uniformément aléatoires**, `Random(9000000 + seed)`,
> 5 766 observations, 5 731 tenseurs distincts, 0 collision — est un échantillon lui aussi, et
> sur une population **différente** de la mienne : jeu uniforme chez lui, **trois greedys** chez
> moi. Les deux se rapportent séparément et **ne se cumulent pas**.
>
> *Une première rédaction de cet encadré décrivait sa population comme « politique uniforme
> contre trois greedys » — un énoncé qui ne désigne aucune composition possible, puisqu'à trois
> sièges on est soit l'un soit l'autre. Corrigé à la relecture.*

**MESURÉ**, même campagne — 2 000 donnes, 6 000 parties, **les trois sièges** :

| | |
|---|---:|
| nœuds observés | **115 299** |
| tenseurs distincts | **106 590** |
| **collisions tenseur → chaîne** | **0** |

Les 8 709 tenseurs répétés portent tous une chaîne **identique** : ce sont de vraies
répétitions d'info-set, pas des collisions.

L'échantillon est **20,0 fois** celui du pilote — `115 299 / 5 766 = 20,00` — et il porte une
**autre population** : trois greedys sur les trois sièges, là où le sien est en jeu uniforme.

> **Ce que l'écart de taille de l'échantillon permet, et ce qu'il ne permet pas de conclure.**
> Un échantillon vingt fois plus grand offre vingt fois plus d'occasions de collision, donc
> `0 collision` y est un résultat **plus fort** que le sien. En revanche il ne dit **rien** sur
> laquelle des deux politiques est la plus exigeante : mes tenseurs se répètent bien plus que
> les siens — `115 299 → 106 590`, soit 7,6 % de répétitions, contre `5 766 → 5 731`, soit
> 0,6 % — mais un taux de répétition croît **mécaniquement** avec la taille de l'échantillon,
> et les deux tailles diffèrent d'un facteur 20. **Les deux effets sont confondus**, et il
> faudrait un échantillon de même taille sous les deux politiques pour les séparer. Ce n'est
> pas fait, et ce serait la seule façon de l'écrire.

---

## 5. L'algorithme, et ce que les autres options auraient donné

**Arbitré le 20/08/2026. Le protocole tranche « self-play avec pool figé » et écarte CFR ; il
ne dit pas lequel.**

**Retenu : PPO à masque d'actions, réseau unique partagé par les trois sièges, tête de valeur,
`γ = 1`.**

`γ = 1` parce que l'horizon est **fixe** — 4 tours par joueur — et que le gain n'arrive qu'au
terminal : actualiser fausserait le jeu en préférant un point tôt à un point tard, alors que
seul le décompte final paie.

**Justification contrastive.**

| Option | Ce qu'elle aurait donné |
|---|---|
| **IS-MCTS / AlphaZero** | plus fort par décision, mais exige une **déterminisation** de l'information cachée — c'est-à-dire exactement le PIMC du greedy et sa fusion de stratégies. Plus de surface à auditer pour un gain non garanti à 3 joueurs. |
| **NFSP** | double la machinerie — un DQN de meilleure réponse **plus** un réseau de politique moyenne — pour une garantie qui, comme celle de CFR, **ne tient qu'à deux joueurs**. |
| **Deep CFR** | écarté au protocole, avec sa justification : aucune garantie au-delà de deux joueurs, et c'est la trajectoire qui a coûté trois mois. |

PPO est le plus court chemin vers un agent mesurable, et il devient une méthode de population
en élargissant le pool — ce qui est la phase 4, pas celle-ci.

---

## 6. Le pool d'entraînement, et l'écart avec la population d'évaluation

**Le protocole dit self-play avec pool figé ; la mesure dit un agent contre deux greedys. Ce ne
sont pas la même population**, et le protocole ne traite pas l'écart.

**Arbitré le 20/08/2026 : ni le greedy ni l'aléatoire n'entrent dans le pool d'entraînement.**

- **Le greedy n'y entre pas** : s'entraîner contre lui transformerait « bat le greedy » en test
  **dans** la distribution, et aucun greedy de rétention n'existe puisque c'est une politique
  unique et fixe.
- **L'aléatoire n'y entre pas** non plus, pour la même raison : le garde-fou le mesure, et **ce
  qui mesure n'entraîne pas**.

**La contrepartie, et il faut l'écrire.** En sortant le greedy du pool, le risque n'est pas
supprimé, il est **déplacé** : le mode de défaut devient l'**effondrement de convention** en
self-play, que le protocole nomme explicitement — trois copies du même agent s'accordent sur une
convention stable qui s'effondre contre un adversaire différent. Les checkpoints figés sont le
garde-fou de ce risque-là. Donc :

- **les mesures contre les checkpoints figés sont rapportées**, chacune avec sa composition
  nommée ;
- **un agent qui écrase ses propres checkpoints mais ne bat pas le greedy est le symptôme exact
  de l'effondrement de convention** — c'est un résultat publiable, pas un échec à cacher.

### 6.1 La proportion, pré-inscrite

À chaque épisode, l'agent courant occupe un siège tiré uniformément ; les **deux autres sièges**
sont tirés selon :

| Adversaire | Proportion | Pourquoi |
|---|---:|---|
| copie courante de l'agent (self-play) | **60 %** | le signal d'apprentissage principal ; c'est la population contre laquelle la politique s'améliore |
| checkpoint figé, tiré uniformément dans le pool | **40 %** | le garde-fou d'effondrement de convention. Une proportion trop faible ne le retient pas ; trop forte, elle ralentit l'amélioration en faisant jouer contre des versions périmées |

Les deux sièges adverses sont tirés **indépendamment** : une partie peut donc opposer l'agent à
une copie de lui-même **et** à un checkpoint. C'est délibéré — une population où l'agent ne
rencontre jamais deux espèces à la fois ne ressemble à aucune des deux compositions mesurées.

**Le pool** : un checkpoint tous les quarts d'heure, plafonné aux **8** plus récents. Le
plafond existe pour que le pool ne se remplisse pas de versions très faibles qui diluent le
signal ; 8 checkpoints à 15 minutes couvrent les 2 h du run.

**Ces trois nombres — 60/40, 15 minutes, 8 — sont pré-inscrits et non mesurés.** Ils ne sont
pas justifiés par une mesure de ce dépôt : ce sont des choix de plan, et les changer est un
levier de la **phase 4**, une variable à la fois.

---

## 7. Le signal d'apprentissage

Le gain du §5.2 est **catégoriel** et n'arrive qu'au décompte : c'est un crédit temporel long
sur un signal pauvre. Le §5.2 des règles autorise explicitement un signal auxiliaire **pendant**
l'apprentissage, jamais dans la fonction de gain évaluée.

**Arbitré le 20/08/2026 : pas de signal auxiliaire en phase 3.** La question de cette phase est
« un agent apprend-il, et bat-il le greedy ». Avec la tête auxiliaire dès le départ, s'il
apprend on ne sait pas grâce à quoi, et s'il n'apprend pas il y a deux suspects. C'est la règle
d'or du protocole — **une variable à la fois**.

### 7.1 La réponse prévue si le garde-fou tombe, écrite d'avance

**Écrite ici pour qu'elle ne soit pas un ajustement d'après-coup.**

Si le garde-fou du §8 tombe, la première réponse est une **tête auxiliaire de régression sur
l'écart de score final** :

- une **tête de sortie supplémentaire** sur le tronc partagé, prédisant
  `score(moi) − max(score(autres))` au terminal ;
- entraînée par une **perte séparée**, pondérée, ajoutée à la perte totale ;
- **jamais dans le retour, jamais dans l'avantage** : la fonction de gain évaluée reste
  strictement le §5.2. La tête auxiliaire ne façonne pas la récompense, elle contraint la
  représentation.

Ce n'est pas un façonnage de récompense — celui-là est le **levier 5 de la phase 4** et il
déplacerait l'objectif.

---

## 8. Le garde-fou, et la correction de sa date

Le protocole écrivait : « **si après 2 h d'entraînement** l'agent, mis à la place du greedy dans
la composition un contre deux aléatoires, n'a pas dépassé **86,52 %** de part de victoire
fractionnée, on arrête ».

> **Ce garde-fou ne pouvait rien arrêter, et le défaut est corrigé au protocole depuis le
> 20/08/2026.** Le plafond d'exécution de cette phase est **lui aussi de 2 h** : le garde-fou se
> déclenchait exactement quand le run était fini.

**La forme en vigueur, reprise telle quelle :** évaluation **à chaque checkpoint de
15 minutes**, contre deux aléatoires, **agrégée sur les trois sièges** comme le 86,52 % l'est.

> **Ce 86,52 % est une moyenne sur les trois sièges**, agrégée sur les 10 002 parties de la
> campagne B de la phase 2, et **il ne se compare qu'à une mesure agrégée de la même façon**.
> Confronter un chiffre d'un seul siège à cette moyenne serait mot pour mot le défaut bloquant
> du tour 1 de la phase 2 — une comparaison entre deux grains. L'avantage de siège est massif
> sous jeu greedy.

**Ce que le garde-fou n'est pas.** Ce n'est pas un juge : dépasser 86,52 % ne dit **rien** sur
le fait de battre le greedy. C'est un détecteur d'agent qui n'apprend pas.

### 8.1 Le budget du garde-fou — l'étape 4 de la boucle s'applique à lui aussi

**Un garde-fou mesuré sur trop peu de parties ne garde rien**, et c'est le défaut que le
protocole a commis trois fois : un critère qui constate au lieu de tester. Le seuil de 38 % de
M1, les quatre critères D1–D4 de la phase 1 et B7 sont les trois précédents.

**Calcul de plan**, à `p = 86,52 %` donc `σ_partie = √(0,8652 × 0,1348) = 0,3415`, 99 %
bilatéral et 80 % de puissance :

| Budget | Écart détectable en part fractionnée |
|---:|---:|
| 900 parties (300 donnes × 3) | 3,89 pt |
| **1 800 parties (600 donnes × 3)** | **2,75 pt** |
| 3 000 parties (1 000 donnes × 3) | 2,13 pt |

**Budget pré-inscrit du garde-fou : 600 donnes × 3 = 1 800 parties par checkpoint**, seeds
`40000+` — une quatrième plage, disjointe des trois autres, et **la même à chaque checkpoint**
pour que deux checkpoints se comparent sur les mêmes donnes.

**Deux réserves, écrites d'avance.**

1. **L'effet de plan de la part fractionnée n'est pas mesuré.** J'ai mesuré `ρ` sur le **gain**,
   pas sur la part fractionnée, et rien ne dit qu'ils coïncident. Le calcul ci-dessus est donc
   **iid**, et le bootstrap de la campagne rendra l'effet réel : il sera publié à côté. Si
   l'effet est inférieur à 1 — ce qui est probable, la permutation des sièges jouant dans le
   même sens que pour le gain —, l'écart détectable réel est **meilleur** que 2,75 pt.
2. **Le garde-fou est évalué 8 fois** — un checkpoint tous les quarts d'heure sur 2 h — et huit
   regards multiplient les occasions de **faux arrêt**. La correction naïve serait de n'évaluer
   qu'à la fin.

   > **Et cette correction naïve est exactement le défaut qu'on vient de corriger.** Une
   > première rédaction de cette réserve écrivait « on arrête si le garde-fou n'est pas franchi
   > au DERNIER checkpoint des 2 h » — c'est-à-dire un garde-fou qui se déclenche quand le run
   > est fini et n'arrête jamais rien, mot pour mot le défaut du protocole corrigé trois
   > paragraphes plus haut. **La correction est le lieu du défaut suivant**, y compris dans le
   > texte qui consigne la leçon.

   **La règle pré-inscrite préserve donc l'arrêt anticipé, et corrige les regards multiples
   plutôt que de les supprimer.** L'IC est corrigé de **Bonferroni pour 8 regards** :
   `z = 3,2272` au lieu de 2,5758, soit une demi-largeur de **2,60 pt** à 1 800 parties contre
   2,07 pt sans correction. Le prix est payé du bon côté — un arrêt tardif coûte des minutes de
   machine, un faux arrêt coûte un run entier et une conclusion fausse.

> **Amendé le 20/08/2026, AVANT le premier entraînement et avant toute mesure d'agent. La règle
> ci-dessus, telle que je l'avais écrite, tuait un agent qui apprend.**
>
> Ma rédaction initiale déclenchait dès le 3ᵉ checkpoint « quand la borne haute est encore sous
> 86,52 % ». **C'est un seuil TERMINAL appliqué à un instant INTERMÉDIAIRE.** Le protocole écrit
> « si **après 2 h** d'entraînement l'agent n'a pas dépassé 86,52 % » : c'est le critère de fin
> de budget, et 86,52 % est le niveau du greedy. L'appliquer à 45 minutes confond deux choses
> qui n'ont rien à voir — **« l'agent n'a pas encore atteint la barre »** et **« l'agent
> n'apprend pas »**.
>
> **MESURÉ sur un run d'essai de 2 minutes**, 25 088 parties, 3 checkpoints, garde-fou réduit à
> 60 donnes : l'entropie de la politique tombe de **2,089 à 1,646** — l'agent apprend,
> visiblement — et ma règle l'arrêtait quand même. Une règle qui tue un apprenant sain n'est pas
> un garde-fou, c'est une panne.
>
> **La règle en vigueur sépare les deux critères :**
>
> - **arrêt anticipé**, possible dès le 3ᵉ checkpoint, et il exige **deux conditions à la
>   fois** — que la part fractionnée **stagne**, `part(k) ≤ part(k−2)`, donc aucun progrès sur
>   une demi-heure, **et** que l'agent soit **loin**, borne haute encore sous 86,52 %. *Stagner
>   loin de la barre* est le symptôme d'un agent qui n'apprend pas ; *être loin en progressant*
>   ne l'est pas ;
> - **critère terminal**, inchangé et celui du protocole : à la fin des 2 h, la part fractionnée
>   a-t-elle dépassé **86,52 %** ? C'est ce qui se rapporte, quel que soit le chemin ;
> - les deux premiers checkpoints sont **rapportés mais ne déclenchent jamais** : `part(k−2)`
>   n'existe pas avant le troisième.
>
> **Ce garde-fou est testé par ses DEUX erreurs**, pas par une seule —
> `tests/agents/test_campagne.py` : un agent qui progresse loin de la barre n'est pas arrêté
> (le faux positif que ma première version commettait), un agent qui stagne loin l'est, et un
> agent qui stagne **au-dessus** de la barre ne l'est pas.
>
> C'est la troisième fois que ce garde-fou porte un défaut : le protocole le déclenchait quand
> le run était fini, ma correction le déclenchait trop tôt. **La correction est le lieu du
> défaut suivant**, et celui-ci a été trouvé avant d'avoir coûté un run.

---

## 9. Ce qui sera rapporté, et comment

### 9.1 Les compositions, chacune nommée

| Composition | Rôle | Sièges |
|---|---|---|
| 1 agent contre 2 greedys | **le juge** | permutés, les 3 |
| 1 agent contre 2 aléatoires | garde-fou seul | permutés, les 3 |
| 1 agent contre 2 checkpoints figés, par checkpoint | effondrement de convention | permutés, les 3 |
| 1 greedy contre 2 greedys | **calibration et dimensionnement** | permutés, les 3 |

### 9.2 Les comportements B1 à B7

Comparés à la ligne de base de la phase 2 **au même grain**. `ecart_de_taux` et `cumuler`
**lèvent** si les grains diffèrent : ils sont utilisés plutôt que des cellules relues.

**Les exclusions se RECALCULENT à mon budget, elles ne se recopient pas.**

Le rapport de phase 2 marque **19 lignes sur 34 « hors budget »** et **2 « aveugles par le
bas »**. Ces deux marqueurs sont **calculés sur les 1 000 parties** que le protocole donnait
alors à la phase 3 — le rapport le dit : « Marqueur `(hors budget)` calculé sur les 1000 parties
de la phase 3 ». **Mon budget en compte 6 000.** Recopier les marqueurs serait exactement la
faute que ce projet paie : un chiffre exact sur une population — ici un budget — que la phrase
ne nomme pas.

> **L'ORDRE DANS LEQUEL C'EST ARRIVÉ, parce qu'un lecteur va me soupçonner et il aura raison
> de le faire.** Un périmètre qui s'élargit juste assez pour qu'une ligne devienne mesurable
> est exactement la liberté que la pré-inscription existe pour supprimer. Voici la
> chronologie, et elle est vérifiable dans l'historique git :
>
> 1. `σ = 0,6494` et `ρ = −0,1400` sont mesurés sur la composition de l'hypothèse nulle,
>    **pour l'estimand du GAIN** — pas pour un compteur de comportement ;
> 2. le budget de **6 000 parties** en est déduit, par la formule du §2.1, et **pré-inscrit** ;
> 3. **seulement ensuite** les marqueurs de M4 sont recalculés à ce budget, parce qu'un
>    marqueur qui dépend du budget doit suivre le budget.
>
> **Que `B7` devienne séparable est une CONSÉQUENCE du budget, jamais un motif de l'avoir
> choisi.** Aucun chiffre de comportement n'est entré dans le choix du budget, et aucun
> n'aurait pu : le budget est fixé par `σ(gain)` et `ρ(gain)`, qui ne dépendent d'aucun
> compteur B1–B7.

**MESURÉ le 20/08/2026**, en repassant les 34 compteurs du rapport livré par
`phase2.budget_d_un_compteur`, la fonction unique que l'audit du tour 2 a imposée :

| | à 1 000 parties | **à 6 000 parties** |
|---|---:|---:|
| lignes **hors budget** | 19 | **8** |
| lignes **aveugles par le bas** | 2 | **0** |

> Le contrôle qui rend ce recalcul crédible : **à 1 000 parties, ma reconstruction retrouve
> exactement 19 et 2**, les deux chiffres publiés. L'unité est donc reconstruite avant la
> valeur, et sur la même fonction.

**Onze lignes entrent dans le budget** qui en étaient sorties — `B1-tentative` (1 331 parties
requises), `B1-collectif` (5 868), `B2-contestee` (1 806), `B2-contestee-publique` (1 359),
`B2-fragile-2` (1 250), `B2-cibles` (2 956), `B2-destination/banquet-Estime` (3 432),
`B2-destination/domaine propre` (2 532), `B4-tout-dos` (3 360), `B5-pire-cas` (3 846),
`B7-lumiere` (2 255). Les noms sont écrits, pas comptés.

**Deux lignes cessent d'être aveugles par le bas, et ce sont** `B7-gaspillage` — écart
détectable de 0,30 % → **0,12 %** pour un taux de 0,15 % (61/40008) — **et**
`B7-gaspillage-vraie` — 0,35 % → **0,14 %** pour 0,20 % (82/40008). **À 6 000 parties, un agent
à zéro exact en EST séparable.**

> **SÉPARABLE NE VEUT PAS DIRE INTERPRÉTABLE, et la marge est mince.** Un écart détectable de
> 0,12 % pour un taux de 0,15 % laisse **0,03 point** de marge : la ligne sort de l'aveuglement,
> elle n'en sort pas confortablement. **Tout écart publié sur B7 vient donc avec son IC**, et
> avec ce qu'il ne dit pas :
>
> - `B7-occasions` vaut **1,22 %** des poses au banquet (488/40008) : sur cette instance à
>   4 tours, une famille devient rarement hors d'atteinte avant la fin. **B7 n'a presque pas
>   l'occasion de se manifester**, et un taux bas se lit sur ce fond-là ;
> - l'écart greedy–hasard observé vaut **−0,02 pt** et demanderait **320 163 parties** :
>   `B7-gaspillage` reste **hors budget** pour cet écart-là à 6 000 parties. Les deux critères
>   sont indépendants — une ligne peut être séparable par le bas et hors budget pour l'écart
>   qu'elle montre ;
> - `_poids_de_bascule_disponible` est une **proposition**, jamais démontrée minimale
>   (réserve 1 de la phase 2), donc `B7-gaspillage` est un **plancher** du gaspillage, pas le
>   gaspillage.

> **C'est un écart avec l'instruction reçue, et il est remonté au pilote plutôt qu'appliqué en
> silence.** Le prompt de cette phase dit « n'annonce aucune différence sur ces lignes », et
> c'est juste **au budget de 1 000 parties**. Le critère est **calculé** ligne à ligne, comme le
> rapport de phase 2 l'exige — « une prose se corrige une fois, un critère n'oublie pas la ligne
> suivante » — donc il change avec le budget. J'applique le critère recalculé et je publie les
> deux colonnes.
>
> **Ce qui ne change pas pour B7 :** son occasion reste rare — `B7-occasions` vaut **1,22 %**
> des poses au banquet (488/40008), et il faudrait **320 163 parties** pour établir l'écart
> greedy–hasard observé de −0,02 pt. B7 devient séparable **par le bas**, il ne devient pas
> informatif sur le jeu.

**Deux exclusions demeurent, et elles ne dépendent pas du budget :**

1. **`B4-tout-dos` (3,89 %) et `B5-renfort` (20,41 %) ne sont pas comparés entre compositions
   différentes.** Leurs taux bougeront sous d'autres agents pour une raison qui n'est pas
   l'habileté. Le critère se décide **sur le texte de la définition** : nomme-t-elle un autre
   joueur ? `B1-collectif` oui, ces deux-là non. *`B4-tout-dos` entre dans le budget à
   6 000 parties — ça ne le rend pas comparable pour autant : les deux critères sont
   indépendants, et celui-ci est textuel.*
2. **Les 8 lignes qui restent hors budget à 6 000 parties** ne sont pas comparées. **Leurs
   noms**, parce qu'un compte n'est pas une liste : `B2-banquet`,
   `B2-destination/banquet-Disgrace`, `B2-destination/domaine adverse`, `B4-departage`,
   `B5-renfort`, `B7-gaspillage`, `B7-gaspillage-vraie`, `B7-occasions`.

Le recalcul est un module, pas un script : `mesure/phase3_budget_des_comportements.py`, tenu par
`tests/mesure/test_phase3_budget_des_comportements.py`, et sa garde
`verifier_contre_la_phase_2` **lève** si la reconstruction cesse de retrouver 19 et 2.

```
UV_LINK_MODE=copy uv run python -m mesure.phase3_budget_des_comportements
```

**`phase2.BUDGET_PHASE_3` reste à 1 000** : la phase 3 passe son budget **en argument** et ne
déplace pas l'étalon d'un livrable audité. Un test le tient.

**La ligne de base de `B1-collectif` est celle des trois greedys**, pas celle d'un greedy contre
deux hasards — son numérateur peut être produit entièrement par les adversaires.

> **Et elle doit être régénérée à UN seul siège mesuré.** La phase 2 la publie sur **trois**
> sièges mesurés — « parties (au moins un des 3 sièges mesurés) » — alors que mon agent n'occupe
> qu'**un** siège par partie. Au grain `(partie, siège)` la comparaison existe ; au grain
> `-par-partie`, non. **Mêmes seeds, même composition, même décalage de graine** : seuls les
> sièges **comptés** changent. `comportements.verifier_inclusion_b1` est rejouée sur la
> population régénérée, **aux deux grains**.

### 9.3 La preuve que l'agent ne lit pas la vue de dieu

**À trois niveaux, comme le greedy, et chacun assorti d'un test que le piège MORD.**

1. **statique** — l'agent ne reçoit qu'une `Perception` ; `agents/perception.py` est la
   frontière, et l'aveuglement est une conséquence de la signature, pas une discipline ;
2. **`vue_privilegiee` piégée** pour lever pendant toute la décision ;
3. **brouillage différentiel** — permuter l'identité des dos adverses, la pioche et les mains
   ne doit pas changer la décision, et un test doit établir que **le brouilleur change vraiment
   la vérité**.

### 9.4 Les durées

**Aucune durée n'est publiée sur un seul chronométrage.** Sur cette machine, cinq passes du même
code donnent un rapport max/min de **2,93 à 3,00** par campagne, de façon non monotone. Toute
durée citée l'est sur **au moins trois passes, avec son étendue**.

### 9.5 Reproduire

```
UV_LINK_MODE=copy uv run python -m mesure.phase3 --donnes 2000
UV_LINK_MODE=copy uv run python -m mesure.phase3_budget_des_comportements
UV_LINK_MODE=copy uv run pytest -q
UV_LINK_MODE=copy uv run python outillage/mutation.py
```

---

## 10. Ce que cette phase n'établira PAS

**Écrit avant la mesure, pour qu'aucune de ces limites ne soit découverte après coup.**

1. **B1 et B3 mesurent la fréquence à laquelle un MOTIF apparaît, jamais une planification.**
   L'avertissement de la phase 2 vaut mot pour mot pour un agent entraîné : un motif observé est
   une figure, pas un plan. Écrire « l'agent planifie des retournements dans X % des parties »
   serait faux quel que soit X.
2. **B1 est plafonné par les 7,40 % de parties portant une perte d'acquis qu'aucun siège ne
   pouvait voir**, mesurés en phase 1. Ces retournements sont **invulnérables à toute
   planification, par n'importe quel agent**. C'est un plafond du mesurable, pas un défaut
   d'agent.
3. **Battre le greedy ne dit pas que l'agent est fort.** Le greedy a un horizon d'un tour, et
   son gain publié est un **plancher** de lui-même — son ciblage est plus myope que sa
   spécification. Aucun chiffre de cette phase ne borne la distance entre l'agent et un bon
   joueur.
4. **Rien ici ne se transporte à `complet-3j`** — 6 familles, 90 cartes, 10 tours. Aucune ligne
   de base de la phase 2 ne s'y transporte non plus, et la phase 5 les remesure.
5. **Le contrôle de collision de tenseurs est un échantillon, pas une preuve d'injectivité.**
6. **`σ` est mesuré sous l'hypothèse nulle** et SUPPOSÉ valoir sous l'agent.
7. **Aucun résultat de cette phase ne valide le moteur.** Elle le suppose conforme ; c'est la
   phase 0 qui l'établit, et elle est close.

---

## 11. Go / no-go

| Résultat, en gain moyen contre **deux greedys** | Conclusion | Suite |
|---|---|---|
| borne basse de l'IC 99 % **> 0** | l'agent bat le greedy | phase 4 |
| IC 99 % **contenant 0** | **non conclu au budget** — ce n'est pas « l'agent ne bat pas le greedy » | dimensionner davantage, ou diagnostiquer |
| borne haute de l'IC 99 % **< 0** | l'agent est battu par le greedy | diagnostiquer avant d'insister |
| part fractionnée **< 33,33 %** contre **deux aléatoires**, IC 99 % excluant 33,33 % | bug | retour phase 0 |

**Aucun seuil ne sera modifié pour faire passer une mesure.** Si l'agent ne bat pas le greedy,
c'est un résultat et il se rapporte tel quel. Un levier écarté est un résultat, pas un échec.
