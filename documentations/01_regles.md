# Règles de Courtisans

**Le document de référence unique. Objectif du jeu, règles complètes, ce que l'IA doit apprendre, et les tests qui vérifient qu'une implémentation est conforme.**

> **Statut : règles validées par l'auteur les 15 et 16/08.** Les quatre questions bloquantes
> sont tranchées (§11). Sept questions de fond restent ouvertes, aucune ne bloque.

Variante conçue par l'auteur, dérivée du jeu de plateau Courtisans dont le mécanisme
d'enchères est volontairement écarté. Il n'existe donc pas de règle officielle à laquelle
confronter ce document : **la validation par l'auteur fait autorité.**

---

## 1. Objectif

**Gagner.** Avoir le plus de points à la fin. Rien d'autre.

Pas maximiser son écart : la marge est un bon **indicateur** de force, un mauvais
**objectif**. Une IA qui maximise sa marge refuse un sacrifice qui donne la victoire d'un
point. Formulation exacte du gain : §5.2.

---

## 2. Ce qui fait le jeu

Cette section n'ajoute aucune règle. Elle explique ce que les règles produisent — et sans
elle, on peut implémenter le jeu correctement tout en entraînant une IA sur le mauvais
objectif.

### 2.1 Le signe des points se décide à la fin

Pendant toute la partie, les cartes s'accumulent. **Rien n'est marqué avant le décompte.**

Une carte posée dans un domaine n'a **pas de valeur propre**. Sa valeur est un signe décidé
ailleurs — au banquet — et plus tard. Le même Noble vaut **+2**, **0** ou **−2** selon ce
que sera devenue sa famille au dernier tour.

### 2.2 Le retournement

**L'influence se compte en VALEUR, pas en nombre de cartes.** Un Noble au banquet pèse **2**,
tous les autres rôles pèsent **1**.

`d = (somme des valeurs en Estime) − (somme des valeurs en Disgrâce)`, sur les cartes
**vivantes**. Statut : **Lumière** si `d ≥ 1`, **Obscurité** si `d ≤ −1`, **Indifférente** si
`d = 0`.

Exemple donné par l'auteur : 2 Nobles en Estime `= 4`, 2 cartes standard en Disgrâce `= 2`,
donc `d = +2` → **Lumière**, alors qu'il y a autant de cartes de chaque côté.

**Une carte fait varier `d` de 1 ou de 2, selon son rôle.** C'est ce qui rend le Noble
dangereux dans les deux sens :

| Situation | Effet d'une carte standard | Effet d'un Noble |
|---|---|---|
| `d = +1` → je pose en Disgrâce | `d = 0` → **Indifférente** | `d = −1` → **Obscurité** |
| `d = +2` → je pose en Disgrâce | `d = +1`, toujours Lumière | `d = 0` → **Indifférente** |

**Un Noble peut donc inverser une famille à lui seul** quand la marge est de 1. Une carte
standard ne peut jamais qu'annuler.

**Deuxième levier : l'Assassin.** Une carte tuée sort du plateau, donc du décompte
d'influence — comme si elle n'avait jamais été posée. Tuer un Noble en Estime fait varier `d`
de **−2** ; tuer une carte standard, de **−1**. Un Assassin qui tue un Noble a donc le même
poids de bascule qu'un Noble posé.

> **Le seuil qui compte est l'Indifférence, pas l'Obscurité.** Une famille à `d = +1` est à
> **une seule action** de ne plus rien rapporter, et à une seule action de rapporter le
> contraire si cette action est un Noble. Raisonner uniquement sur le basculement en
> Obscurité fait croire une position sûre alors qu'elle est fragile.

**Conséquence : une position n'est jamais acquise.** Une avance bâtie sur une famille en
Lumière peut être annulée ou inversée jusqu'au dernier tour.

### 2.3 Un bon coup, c'est la combinaison des trois cartes

Un tour n'est pas trois décisions indépendantes. **Les trois cartes et l'effet de l'Assassin
forment un seul coup**, et c'est leur combinaison qui le rend bon ou mauvais.

Exemple donné par l'auteur : je pose une carte de famille A chez un adversaire. Ça ne vaut
quelque chose que si je sais ce que je vais faire de mon Assassin — parce que si mon Assassin
fait passer A d'Obscurité à Lumière, le cadeau que je viens de faire devient un vrai cadeau
au lieu d'un poison.

> **Poser une carte chez un adversaire sans avoir décidé ce que fera l'Assassin du même tour
> n'a aucun sens.**

C'est ce qui distingue le jeu d'une suite de coups myopes, et c'est pourquoi l'action de pose
est **atomique** : les trois cartes sont assignées d'un bloc, puis les Assassins résolus
(§3.2). Le joueur choisit une combinaison, pas trois placements successifs.

### 2.4 Qui pose n'est pas qui encaisse

Les points vont au **propriétaire du domaine**, jamais à celui qui a posé la carte (§5).

Or chaque tour oblige à poser une carte chez un adversaire (§3.1). On lui donne donc, à
chaque tour, quelque chose qui vaudra `+valeur`, `0` ou `−valeur` — **et c'est le futur
statut de la famille qui décide lequel.**

| Ce que je pose chez l'adversaire | Lumière | Indifférente | Obscurité |
|---|---|---|---|
| une carte de famille A | **cadeau** : `+valeur` pour lui | **sans effet** : 0 | **poison** : `−valeur` pour lui |

Le même geste est un cadeau, rien, ou un poison. Ce qui tranche, c'est ce qui se passera au
banquet ensuite — et l'issue la plus fréquente n'est pas forcément l'une des deux extrêmes.

### 2.5 Les alliances implicites, famille par famille

C'est le cœur du jeu à 3 joueurs et plus.

Si je pose des cartes de famille A dans ton domaine, **tu as désormais intérêt à ce que A
finisse en Lumière**. Si j'ai moi aussi des A chez moi, nous avons le même intérêt : ni toi
ni moi ne mettrons A en Disgrâce. Nous sommes **alliés objectifs sur A**, sans rien avoir
négocié. Et rien n'empêche d'être **ennemis sur B** en même temps.

> Le jeu consiste à fabriquer, famille par famille, qui a intérêt à quoi.

C'est ce qui sépare structurellement 3 joueurs de 2. À 2 joueurs, ce que je donne à l'autre,
je le lui donne contre moi. À 3, je peux nourrir un joueur sur une famille pour qu'il la
défende, et attaquer le troisième ailleurs.

### 2.6 L'information est majoritairement ouverte

**C'est le point le plus important de cette section, et le plus facile à se représenter de
travers.**

Courtisans **n'est pas** un jeu où l'on joue à l'aveugle. La grande majorité des cartes
posées sont face visible : famille, rôle, zone, propriétaire du domaine, tout est public.
Seuls les Espions sont cachés, et ils ne représentent qu'un cinquième des rôles.

| Ce qu'un joueur connaît exactement | Ce qu'il ignore |
|---|---|
| toutes les cartes face visible du plateau, avec famille, rôle et zone | l'identité des Espions posés par les autres — mais **leur position est connue** |
| sa propre main | les mains adverses |
| l'identité des Espions qu'il a lui-même posés | le contenu et l'ordre de la pioche |
| la composition totale du paquet — 6 × 5 × 3 | |
| le nombre de tours restants | |

**Conséquence : le résidu est calculable.** Le paquet est connu à l'avance. Tout ce qui
n'est ni visible sur le plateau, ni dans sa propre main, ni un Espion qu'on a soi-même posé,
forme un **ensemble résiduel exactement déterminé** — réparti entre la pioche, les mains
adverses et les Espions cachés du plateau. On sait donc, à chaque instant, **quelles cartes
restent en circulation**, même si on ignore où.

### 2.7 Le calcul de marge — la compétence centrale

De là découle ce que fait un bon joueur en permanence : **estimer sa marge**, et décider si
elle vaut la peine d'être défendue.

Exemple, corrigé après audit — et recalculé **en valeur** :

> Famille A : **2 cartes standard en Estime** (`+2`), rien en Disgrâce, plus **un dos en
> Disgrâce**. Il reste **2 tours**.
>
> **Marge visible** : `d = +2`.
> **Marge pire cas** : le dos est un Espion, donc de valeur 1 ; s'il est de famille A →
> `d = +1`. La famille tient, mais à **un cran**.
> **Ce qui suffit alors** : une carte standard A en Disgrâce annule (`d = 0`) ; **un Noble A
> en Disgrâce inverse** (`d = −1`) ; un Assassin qui tue une carte A d'Estime annule.
>
> Conclusion : la marge **n'est pas confortable**. Un seul Noble adverse suffit à faire
> passer A dans le négatif.

**La version fausse de cet exemple, à ne pas refaire.** J'avais initialement conclu « marge
confortable, je ne défends pas », en raisonnant uniquement sur le passage en **Obscurité**
— qui demande deux cartes — et en oubliant l'Assassin. Deux erreurs qui vont dans le même
sens : elles font croire une position sûre. C'est exactement le type de raisonnement qu'une
IA ne doit pas apprendre.

Ce raisonnement combine quatre choses, toutes calculables :

| Grandeur | Formule |
|---|---|
| Marge visible | `d` = somme des **valeurs** visibles en Estime moins celles en Disgrâce |
| Marge pire cas | `d` diminué de 1 par dos adverse du côté favorable — un dos est toujours un Espion, donc de valeur 1 |
| Cartes de la famille encore posables | résidu de la famille, **hors cartes mortes** (la défausse est publique) |
| Poids de bascule disponible | combien de **Nobles** de cette famille restent en circulation — ce sont eux qui font varier `d` de 2 |
| Occasions restantes | poses au banquet encore possibles = tours restants × joueurs |

**Ce n'est pas de l'intuition, c'est une borne.** Un joueur fort sait quand une famille est
hors d'atteinte, quand elle est à un cran de l'annulation, et quand elle est déjà perdue.

> **Exigence pour l'IA.** L'état exposé au réseau doit rendre ce calcul **possible** — sans
> le lui coder en dur. Il faut donc que l'encodage contienne : les comptes visibles par
> famille et par zone, le **nombre de cartes cachées par zone**, le **résidu par type de
> carte** encore en circulation, et le **nombre de tours restants**. Un encodage qui se
> contente de lister les cartes posées une par une, sans ces agrégats, oblige le réseau à
> réapprendre l'arithmétique du décompte au lieu d'apprendre à jouer.
> Détail : [03_specification_moteur.md](03_specification_moteur.md).

**À CONFIRMER : ai-je bien décrit ton raisonnement de marge ?**

---

## 3. Matériel et déroulement

### 3.1 Le paquet

6 familles × 5 rôles (Assassin, Garde, Noble, Espion, Neutre) × **3 exemplaires** =
**90 cartes**.

**On joue toujours avec les 90 cartes. Aucune n'est retirée.**

### 3.2 Le tour de jeu

À son tour, un joueur a **3 cartes en main** et les joue **toutes les trois**, une par zone :

1. une carte au **banquet** (chez la Reine), en **Estime** ou en **Disgrâce** ;
2. une carte dans **son propre domaine** ;
3. une carte dans le domaine d'**un adversaire**.

**Structure fixe, sans exception.** Jamais deux cartes au banquet, jamais deux dans son
propre domaine, jamais deux chez le même adversaire dans un même tour. À 3 et 4 joueurs, la
seule liberté supplémentaire est **lequel** des adversaires reçoit la carte. Un joueur peut
parfaitement viser le même adversaire à chacun de ses tours.

**Séquence d'un tour, sans ambiguïté :**

1. le joueur choisit **une** action de pose, qui place les **trois** cartes simultanément ;
2. puis, s'il a posé un ou plusieurs Assassins, chacun ouvre un nœud de décision de ciblage,
   **résolus dans l'ordre : banquet, puis son propre domaine, puis le domaine adverse** ;
3. le tour passe au joueur suivant.

Le mot « immédiatement » du §4.1 signifie « avant la fin du tour », pas « avant que les deux
autres cartes ne soient posées ».

**L'ordre de pose n'a donc pas d'effet** : les trois cartes vont dans trois zones distinctes
par construction — banquet, domaine propre, domaine d'un adversaire sont deux à deux
disjoints quel que soit le nombre de joueurs. Un Assassin posé ce tour-ci ne peut jamais
cibler ses deux compagnons de tour. C'est une conséquence directe de la structure fixe
ci-dessus, pas une propriété à mesurer ; le test **C8** la vérifie par sécurité.

#### Nombre d'actions de pose

| Décision | Choix | Détail |
|---|---:|---|
| **Assignation** des 3 cartes aux 3 zones | **6** | 3 choix pour le banquet × 2 pour son domaine × 1 = **3! = 6** |
| **Position au banquet** | **2** | Estime ou Disgrâce |
| **Quel adversaire** | **n − 1** | sans objet à 2 joueurs |

**Total : 6 × 2 × (n − 1)** — soit **12** à 2 joueurs, **24** à 3, **36** à 4.

Le facteur 2 est bien Estime/Disgrâce, pas l'Assassin : deux actions qui n'en diffèrent que
posent les mêmes cartes aux mêmes endroits, avec un effet **opposé** sur l'influence.

Le **ciblage d'Assassin est une phase de décision séparée**, pas un multiplicateur. Après la
pose, chaque Assassin posé ouvre un nœud de décision de **`nombre de cibles valides + 1`**
actions, le « +1 » étant le refus de tuer (§4.1).

### 3.3 Ordre et pioche

Les joueurs jouent à tour de rôle dans un ordre fixe. En début de tour, le joueur complète sa
main à 3 cartes depuis la pioche.

### 3.4 Fin de partie

**Tous les joueurs jouent exactement le même nombre de tours.**

La partie se termine **à la fin du dernier tour de table complet** : dès qu'il ne reste plus
assez de cartes pour que **tous** les joueurs jouent encore 3 cartes. Les cartes restantes ne
sont jamais piochées et leur identité n'est jamais révélée.

**Formellement** : avant d'entamer un tour de table, si `len(pioche) < 3 × nb_joueurs`, la
partie est finie.

```
tours par joueur    = floor(90 / (3n))
cartes jouées       = 3n × tours
cartes non piochées = 90 − cartes jouées
```

| Joueurs | Cartes par tour de table | Tours par joueur | Cartes jouées | Restant en pioche |
|---:|---:|---:|---:|---:|
| 2 | 6 | **15** | 90 | 0 |
| **3** | **9** | **10** | **90** | **0** |
| 4 | 12 | **7** | 84 | 6 |
| 5 | 15 | **6** | 90 | 0 |

Le nombre de tours **décroît** quand le nombre de joueurs augmente — 15, 10, 7, 6. Toute
table qui ne respecte pas cette monotonie contient une erreur.

Tester la fin de partie **joueur par joueur** — « le joueur courant a-t-il encore 3 cartes ? »
— est **non conforme** : les premiers de l'ordre jouent alors un tour de plus.

---

## 4. Rôles et effets

| Rôle | Valeur | Face | Effet |
|---|---:|---|---|
| Noble | **2** | visible | aucun |
| Garde | 1 | visible | **immunisé** contre les Assassins |
| Espion | 1 | **cachée** | identité connue du seul poseur |
| Neutre | 1 | visible | aucun |
| Assassin | 1 | visible | peut tuer une carte de sa zone |

### 4.1 Assassin

Quand un Assassin est posé, il **peut** tuer une carte, immédiatement.

**Cibles valides** : toute carte de la **même zone** — même position Estime ou Disgrâce au
banquet, même domaine sinon — qui n'est **pas un Garde** et qui n'est **pas l'Assassin
lui-même**. Il peut donc tuer un autre Assassin, un Neutre, un Noble, et un Espion visible
ou caché.

**Le meurtre est facultatif.** L'Assassin ne tue pas s'il ne peut pas (aucune cible valide),
**et il n'est pas tenu de tuer s'il ne veut pas**, même lorsque des cibles existent.
« Ne pas tuer » est une **action à part entière**, pas un cas dégénéré.

Plusieurs Assassins posés au même tour se résolvent **séquentiellement**, chacun avec son
propre choix — y compris celui de s'abstenir.

**Une carte tuée est révélée et va à la défausse.** La défausse est **publique** — c'est sa
seule utilité dans ce jeu. Une carte tuée ne compte ni pour l'influence des familles, ni pour
les points, et ne peut plus jamais réapparaître.

**Conséquence : un Espion tué révèle sa famille à tout le monde.** Assassiner un Espion est
donc aussi un **outil d'information** : on retire une carte du jeu et on apprend, avec tous
les autres joueurs, ce qu'elle était.

**Conséquence pour le calcul de marge (§2.6) : le résidu est exactement calculable.** Tout
joueur peut retrancher la défausse de ce qui reste en circulation. Il n'y a aucune incertitude
résiduelle sur les cartes mortes.

### 4.2 Espion

Posé face cachée dans toutes les zones, y compris au banquet. Le poseur connaît son
identité ; les autres ne voient qu'un dos. Tous les Espions sont retournés face visible
avant le décompte et comptent normalement.

### 4.3 Garde

Immunisé contre les Assassins. **À CONFIRMER : quel est son rôle réel dans ta façon de
jouer ?**

### 4.4 Neutre

Aucun effet, vaut 1 point. **À CONFIRMER : quel intérêt a-t-il ?**

---

## 5. Décompte

1. **Statut de chaque famille**, calculé sur ses cartes **vivantes** au banquet :

   `d = (somme des valeurs en Estime) − (somme des valeurs en Disgrâce)`

   - `d ≥ 1` → **Lumière**
   - `d ≤ −1` → **Obscurité**
   - `d = 0` → **Indifférente**, la famille ne rapporte rien

   **Tout se compte en valeur, jamais en nombre de cartes.** Un Noble pèse **2**, tous les
   autres rôles pèsent **1** — au banquet comme dans les domaines. Une famille peut donc avoir
   autant de cartes de chaque côté et n'être pas Indifférente : 2 Nobles en Estime contre
   2 cartes standard en Disgrâce donne `d = 4 − 2 = +2`, soit **Lumière**.

   Une famille dont aucune carte vivante n'est au banquet — jamais posée, ou toutes tuées —
   est **Indifférente** (`d = 0`).

   > *Note de vocabulaire.* Le statut s'appelle **Indifférente** et non « Neutre », pour
   > éviter la collision avec le **rôle** Neutre. « Une carte Neutre de famille Neutre »
   > était une phrase légale et incompréhensible.
2. **Points** : pour chaque carte posée dans un domaine, si sa famille est en Lumière le
   **propriétaire du domaine** gagne la valeur de la carte ; en Obscurité il la perd ; en
   Neutre, rien.
3. Le **propriétaire du domaine** est crédité, **pas** celui qui a posé la carte.
4. Les cartes tuées ne comptent nulle part.
5. Les cartes au banquet ne rapportent aucun point : elles ne servent qu'à déterminer le
   statut des familles.

### 5.1 Égalités

Le joueur avec le plus de points gagne. **Les égalités sont possibles et conservées** : si
plusieurs joueurs terminent au score maximum, ils gagnent ex æquo. Aucun départage
artificiel, ni par ordre de jeu ni autrement.

### 5.2 Formulation du gain pour l'IA

| Situation | Gain |
|---|---|
| Vainqueur unique (n joueurs) | **+1** pour lui, **−1/(n−1)** pour chacun des autres |
| k vainqueurs ex æquo | **+(n−k)/(k(n−1))** pour chacun d'eux, **−1/(n−1)** pour les perdants |

À 3 joueurs : vainqueur unique → **+1, −0,5, −0,5**. Deux ex æquo → **+0,25, +0,25, −0,5**.
Trois ex æquo → **0, 0, 0**. Somme nulle dans tous les cas.

*Limite assumée* : un signal binaire est plus pauvre qu'un écart continu, donc potentiellement
plus lent à apprendre. Si l'entraînement stagne pour cette raison, la piste est un signal
auxiliaire **pendant** l'apprentissage — jamais dans la fonction de gain évaluée.

---

## 6. Ce qui change avec le nombre de joueurs

| Aspect | 2 joueurs | **3 joueurs** | 4 joueurs |
|---|---|---|---|
| Tours par joueur | 15 | **10** | 7 |
| Cartes jouées | 90 | **90** | 84 |
| Actions de pose par tour | 12 | **24** | 36 |
| Choix de l'adversaire ciblé | non | **oui** | oui |
| Zones de ciblage d'Assassin | 4 | **5** | 6 |
| Alliances implicites possibles | non | **oui** | oui |

---

## 7. Ce que l'IA doit apprendre

### 7.1 Ce que fait le greedy, et ce qu'il ne voit pas

Le greedy PIMC est aujourd'hui l'agent le plus fort mesuré du projet. Sa règle : **maximiser
l'écart de score obtenu sur le tour en cours**, comme si la partie s'arrêtait là. Ce n'est
pas une mauvaise heuristique — elle gagne des parties. Ce n'est pas une stratégie.

| Ce qu'il ne fait pas | Pourquoi c'est décisif |
|---|---|
| Anticiper les **retournements** | il évalue les signes actuels comme définitifs (§2.2) |
| **Calculer sa marge** | il ne borne pas le nombre de cartes pouvant encore basculer une famille, donc il défend ce qui est déjà sûr et néglige ce qui est en jeu (§2.6) |
| Raisonner sur les **Espions adverses** | il traite une carte cachée comme neutre, au lieu de raisonner sur le pire cas |
| Tenir compte du **résidu** en circulation | il ignore combien de cartes d'une famille peuvent encore apparaître |
| Construire une **alliance** | il ne modélise pas l'intérêt qu'il crée chez l'autre en lui donnant une carte (§2.4) |
| Planifier sur **plusieurs tours** | son horizon est d'un tour, par construction |

**Battre le greedy est un plancher, pas un objectif.** Une IA qui le bat de peu peut n'être
qu'un greedy légèrement meilleur.

### 7.2 Critères de réussite observables

| # | Comportement attendu | Comment le constater |
|---|---|---|
| **B1** | **Planifier un retournement** : nourrir une famille chez un adversaire, puis la basculer en Obscurité en fin de partie | tracer les parties où l'IA pose une famille chez un adversaire puis la met en Disgrâce plus tard |
| **B2** | **Placer l'Assassin là où il pourra servir** — au banquet sur une famille contestée plutôt que dans un domaine sans enjeu | distribution des zones où l'IA place ses Assassins, comparée au greedy |
| **B3** | **Fabriquer une alliance** : nourrir un joueur sur une famille où l'IA est elle-même exposée | corrélation entre les familles données à un joueur et celles que l'IA détient |
| **B4** | **Refuser de tuer** quand le meurtre lui coûterait | fréquence du refus, et vérification qu'il survient dans les cas défavorables |
| **B5** | **Se méfier des Espions** : ne pas traiter une majorité serrée comme acquise s'il reste des cartes cachées | comportement face aux majorités à une carte d'écart |
| **B6** | **Exploiter la pioche connue** : jouer différemment en fin de partie, quand l'incertitude tombe | comparaison du style entre début et fin de partie |
| **B7** | **Ne pas défendre ce qui est déjà sûr** : sur une famille dont la marge est hors d'atteinte compte tenu du résidu et des tours restants, jouer ailleurs (§2.6) | mesurer la fréquence des cartes « gaspillées » à renforcer une majorité déjà imprenable, comparée au greedy |

**B1 et B3 définissent le jeu.** Une IA qui ne les manifeste jamais joue à autre chose, quel
que soit son score.

> **Note.** Un critère « garder un Assassin en main pour la fin » a été retiré après audit :
> il est **impossible** sous ces règles. La main est vidée à chaque tour (§3.2) et
> recomplétée au suivant (§3.3), donc le tour où un Assassin est joué est entièrement
> déterminé par le mélange, jamais par une décision. B2 mesure désormais **où** l'Assassin
> est placé, ce qui est bien une décision.

**À CONFIRMER : en manque-t-il un qui, pour toi, sépare un bon joueur d'un joueur correct ?**

---

## 8. Écarts autorisés pour une instance réduite

Une instance d'entraînement peut réduire **la composition du paquet**, et rien d'autre.

| Dimension | Réduction autorisée | Interdit |
|---|---|---|
| Familles | 6 → moins, mais **strictement plus que le nombre de joueurs** | familles ≤ joueurs ; familles non interchangeables |
| Rôles | retirer des rôles entiers | modifier l'effet d'un rôle conservé |
| Exemplaires | 3 → 1 ou 2 | déséquilibrer entre types de cartes |
| Joueurs | 2, 3 ou 4 | — |
| **Durée de la partie** | **jamais** | tronquer la partie, arrêter avant épuisement de la pioche |
| **Tours par joueur** | **jamais directement** | tours inégaux entre joueurs |
| **Meurtre facultatif** | **jamais** | forcer le meurtre |

**La durée n'est jamais un paramètre de réduction.** Un paquet plus petit donne mécaniquement
une partie plus courte — elle se termine parce que la pioche est épuisée, jamais parce qu'on
l'interrompt. Tronquer une partie détruit le jeu : la stratégie *est* dans la durée, puisque
le signe des points ne se décide qu'à la fin (§2.1). On ne raccourcit pas une partie d'échecs
à deux coups pour regarder qui mène.

**Deux planchers, sans lesquels la réduction devient une troncature déguisée :**

| Plancher | Valeur | Raison |
|---|---|---|
| **Familles** | **strictement > nombre de joueurs** | Avec autant de familles que de joueurs, **chacun se replie sur sa propre famille** pour ne pas perdre de points, personne ne prend le risque d'en attaquer une autre, et **aucune stratégie d'alliance n'émerge** (§2.4). Le jeu dégénère en trois monologues parallèles. Le jeu complet respecte cette contrainte avec de la marge : 6 familles pour 4 joueurs au maximum. |
| Tours par joueur | **≥ 3** | un retournement demande au moins deux poses au banquet sur la même famille (§2.2) ; en dessous de 3 tours, le mécanisme central du jeu n'est pas réalisable |

Toute instance doit satisfaire : `tours = floor(nb_cartes / (3 × nb_joueurs)) ≥ 3`, identique
pour tous les joueurs, et `familles > joueurs`. Une configuration qui viole un plancher doit
être **refusée à la construction**, pas seulement déconseillée.

---

## 9. Tests de conformité

Leur absence a été le manque le plus coûteux du projet : elle a laissé passer le meurtre
obligatoire et les tours inégaux pendant cinq briques d'entraînement. Chaque test s'applique
au moteur complet **et** à toute instance réduite.

> **État au 16/08 : les 18 tests sont écrits, dans `tests/conformite/`, et tous rouges** —
> le moteur n'existe pas encore. C'est l'étape 1 du prompt de construction. Ils sont
> paramétrés sur sept configurations couvrant `joueurs ∈ {2, 3, 4}`.

| # | Test | Vérifie |
|---|---|---|
| C1 | Le paquet compte `familles × rôles × exemplaires` cartes ; aucune n'est retirée avant le mélange | §3.1 |
| C2 | Tous les joueurs jouent le même nombre de tours, sur 1000 parties, pour n ∈ {2, 3, 4} | §3.4 |
| C3 | Aucun tour partiel : tout tour joué comporte exactement 3 cartes | §3.4 |
| C4 | Le nombre de cartes restées en pioche vaut `nb_cartes mod 3n` | §3.4 |
| C5 | En résolution d'Assassin avec ≥ 1 cible, « ne pas tuer » est une action légale | §4.1 |
| C6 | Les cibles valides excluent les Gardes et l'Assassin lui-même, et sont toutes dans sa zone | §4.1 |
| C7 | Un Assassin peut cibler un Espion caché et un autre Assassin | §4.1 |
| C8 | Les 3 cartes d'un tour vont dans 3 zones distinctes, pour **tout** nombre de joueurs | §3.2 |
| C9 | Une carte tuée ne compte ni dans l'influence, ni dans les points | §4.1 |
| C10 | Un Espion est invisible pour tous sauf son poseur, et compté au décompte | §4.2 |
| C11 | Les points vont au propriétaire du domaine, pas au poseur | §5 |
| C12 | Les cartes au banquet ne rapportent aucun point | §5 |
| C13 | La somme des gains est nulle, y compris avec des ex æquo | §5.2 |
| C14 | L'espace d'actions de pose vaut `6 × 2 × (n − 1)`, chaque action décodant vers une assignation distincte | §3.2 |
| C15 | En phase de ciblage, le nombre d'actions légales vaut `nb_cibles + 1` | §4.1 |
| C16 | Encodage info-set injectif : deux info-sets distincts ne partagent jamais un tenseur | prérequis IA |
| C17 | Tous les états d'un même info-set exposent le même ensemble d'actions légales | prérequis IA |
| C18 | Familles strictement interchangeables : permuter les familles laisse les gains invariants | prérequis à la canonicalisation |

---

## 10. Arbitrages tranchés

| # | Question | Décision |
|---|---|---|
| **R1** | Structure du tour à 3-4 joueurs | **1 banquet / 1 chez soi / 1 chez un adversaire, sans exception.** Seul le choix de l'adversaire s'ajoute. |
| **R2** | Le meurtre de l'Assassin | **Facultatif.** « Ne pas tuer » est une action légale. |
| **R3** | Nombre de tours | **Identique pour tous.** La partie s'arrête au dernier tour de table complet. |
| **R4** | Retrait de cartes selon le nombre de joueurs | **Aucun.** Les cartes en trop restent dans la pioche, non piochées. |
| **R5** | Égalité de score | **Ex æquo conservés**, aucun départage. |
| **R6** | Gagner ou maximiser l'écart | **Gagner.** Gain **catégoriel** — victoire / ex æquo / défaite — réparti à somme nulle. Pas binaire : la formule du §5.2 est graduée selon le nombre d'ex æquo. |
| **R7** | Règle officielle du jeu de plateau | **Sans objet** : variante de l'auteur, dont la validation fait autorité. |
| **R8** | Réduction d'une instance | **Composition du paquet uniquement.** Jamais la durée. Familles > joueurs. |

---

## 10bis. Défauts corrigés après audit croisé — 16/08

Deux auditeurs indépendants ont relu ce document et le vecteur d'état sans voir le
raisonnement qui les avait produits. Ce qu'ils ont trouvé, et qui est corrigé ci-dessus :

| # | Défaut | Correction |
|---|---|---|
| 1 | « Une seule carte peut inverser une famille » — **faux**, une carte fait varier `d` de ±1, il en faut deux | §2.2 réécrit avec la preuve |
| 2 | L'exemple de calcul de marge du §2.6 concluait « marge confortable » en oubliant le seuil **Indifférente** et le levier **Assassin** | §2.6 réécrit, avec l'erreur conservée comme contre-exemple |
| 3 | « Immédiatement » (§4.1) contredisait l'action de pose atomique (§3.2) | séquence du tour écrite explicitement en §3.2 |
| 4 | Le statut « Neutre » entrait en collision avec le rôle Neutre | statut renommé **Indifférente** |
| 5 | Le critère B2 « garder un Assassin » est impossible : la main est vidée chaque tour | B2 reformulé sur le **placement** |
| 6 | Famille sans carte au banquet : statut non défini | écrit en §5 |
| 7 | Ordre de résolution de plusieurs Assassins non spécifié | fixé en §3.2 : banquet, domaine propre, domaine adverse |
| 8 | §8 interdisait la troncature mais autorisait des instances d'un seul tour | planchers `tours ≥ 3` et `familles > joueurs` ajoutés |
| 9 | §2.3 omettait le cas Indifférente | colonne ajoutée |
| 10 | R6 disait « binaire » alors que la formule est graduée | corrigé dans le tableau §10 |
| 11 | Mauvais numéro de test cité au §3.2 (C7 au lieu de C8) | corrigé |

**Ce que l'audit a confirmé comme solide** : l'arithmétique du §3.4 et du §6 (tours, cartes
jouées, restes) est exacte dans tous les cas ; la formule de gain du §5.2 est à somme nulle
pour tout `n ≥ 2` et tout nombre d'ex æquo, démonstration algébrique à l'appui ; et il
n'existe **aucun état de blocage légal** — un joueur a toujours un coup jouable, quel que
soit le nombre de joueurs.

---

## 11. À confirmer par l'auteur

**Tranché par l'auteur les 15 et 16/08 — toutes les questions bloquantes sont fermées :**

| # | Question | Réponse |
|---|---|---|
| Q1 | Influence en cartes ou en valeur ? | **En valeur.** Noble = 2, autres = 1, partout. |
| Q2 | Une carte tuée est-elle révélée ? | **Oui**, elle va à la défausse, qui est **publique**. |

| Q3 | Le poseur d'une carte **visible** est-il tracé ? | **Non.** Sans intérêt : l'intérêt d'un joueur pour une famille se lit dans le contenu de son domaine, pas dans qui l'y a mis. On ne trace le poseur **que pour les cartes cachées**, où c'est le seul indice disponible. |
| Q4 | Pourquoi plus de familles que de joueurs ? | **Pour empêcher le repli.** À familles = joueurs, chacun joue sa propre famille pour ne pas perdre de points et aucune alliance n'émerge. Voir §8. |

**Plus aucune question ne bloque l'écriture du moteur.**

Questions de fond, non bloquantes :

5. **Le calcul de marge (§2.6)** — la version corrigée décrit-elle bien ton raisonnement ?
6. **L'Espion** — un levier de retournement caché, ou t'en sers-tu autrement : bluff,
   protection d'une carte de valeur ?
7. **Le Garde** — il verrouille une valeur d'influence qu'aucun Assassin ne peut retirer :
   est-ce bien comme ça que tu l'utilises ?
8. **Le Neutre** — quel intérêt, s'il n'a aucun effet et vaut 1 point ?
9. **Ai-je raté un mécanisme de retournement** autre que la pose au banquet et l'Assassin ?
10. **§7.2** — les sept comportements B1 à B7 sont-ils les bons critères de réussite ?
11. **Avantage de position** — y a-t-il un avantage à jouer premier ou dernier ? Non mesuré ;
    à établir dès que le moteur est conforme.
