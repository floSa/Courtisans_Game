# Phase 1 — Hypothèse et instrument

**Écrit et commité AVANT toute mesure**, règle 1 du §2 de
[05_protocole_experimental.md](../documentations/05_protocole_experimental.md). Ce document ne
contient aucun chiffre mesuré : uniquement ce qui sera mesuré, comment, et ce qui sera conclu
selon le résultat.

Instance mesurée : **`entrainement-3j`** — `familles=4`, les 5 rôles, `exemplaires=2`,
`joueurs=3`. Elle n'est pas choisie ici : elle est fixée par le §3 de
[03_specification_moteur.md](../documentations/03_specification_moteur.md), la variante à
20 cartes étant refusée à la construction par le plancher `tours >= 3` du §8 des règles.

Arithmétique de l'instance, à vérifier par la mesure et non à supposer :
`4 × 5 × 2 = 40` cartes ; `40 // (3 × 3) = 4` tours par joueur ; `3 × 3 × 4 = 36` cartes
jouées ; `40 − 36 = 4` cartes jamais piochées.

---

## 1. Hypothèse

> **H — L'instance `entrainement-3j` conserve la substance du jeu.**
>
> Sous jeu **uniformément aléatoire sur les actions légales**, par les trois joueurs, sur
> 1 000 parties :
>
> **H1** — les trois joueurs jouent le même nombre de tours, dans **1 000 parties sur 1 000** ;
> **H2** — la distribution des scores finaux n'est **pas dégénérée**, au sens des quatre
> critères chiffrés du §3 ;
> **H3** — **au moins un retournement `R2` survient dans au moins 33,3 %** des parties, `R2`
> étant défini au §2.

**Falsifiable** : chacun des trois énoncés est un chiffre confronté à un seuil fixé
d'avance. H est vraie si les trois tiennent, fausse dès que l'un tombe.

**Ce que j'attends si H est vraie.** H1 exactement 1 000/1 000 (c'est une conséquence du
code, pas un aléa — le tester est un contrôle de non-régression, pas une découverte).
H3 largement au-dessus du seuil : *SUPPOSÉ, avant mesure*, `R2 ≥ 90 %` des parties — 12 poses
au banquet réparties sur 4 familles donnent ~3 cartes de banquet par famille, chacune de
signe quasi équiprobable, et la première carte d'une famille la sort toujours de
l'Indifférence. `R1` (inversion stricte de signe) *SUPPOSÉ ≥ 50 %*, sans engagement.

**Ce que j'attends si H est fausse.** Le cas le plus probable est H3 sous le seuil parce que
les familles n'accumulent pas assez de cartes au banquet pour changer de statut après en
avoir pris un — c'est-à-dire que 4 tours ne suffisent pas. Le cas H2 se manifesterait par
des scores massivement nuls (familles restant Indifférentes) ou par une écrasante majorité
de parties à trois ex æquo.

**Ce qui est interdit quelle que soit l'issue** : modifier l'instance, modifier le moteur,
modifier un seuil après avoir vu le chiffre. Si H est fausse, elle se rapporte fausse.

---

## 2. « Retournement » — la définition, et les trois autres

Aucun document du projet ne donne de définition mesurable du retournement. Le §2.2 des
règles en décrit le **mécanisme** — une famille change de statut au banquet — sans dire ce
qu'on compte. Un seuil « 1 partie sur 3 » n'a aucun sens sans elle.

### 2.1 Le support de la mesure

Pour une famille `f`, on observe la suite de ses statuts
`S_f = [s_0, s_1, …, s_T]`, où `s_0` est le statut initial — **Indifférente** pour toute
famille, le plateau étant vide — et `s_t` le statut après le `t`-ième événement.

Le statut est celui du moteur : `rules.statuts` sur les cartes **vivantes** du banquet, en
**valeur** (Noble = 2, autres = 1), calculé sur la **vue privilégiée**, donc sur le statut
**vrai**, Espions cachés compris.

**Deux grains, tous deux rapportés :**

| Grain | Échantillonnage | Pourquoi |
|---|---|---|
| **fin** | après chaque `apply()` | tout état atteint par le moteur compte |
| **tour** | après chaque tour de joueur complet, c'est-à-dire quand la phase quitte `CIBLAGE` | le §2.3 des règles fait des 3 cartes **et** des Assassins **un seul coup** : un retournement qui n'existe qu'entre la pose et la résolution d'un Assassin du même tour est un transitoire, pas un coup |

Le grain **tour** est le grain de référence pour le go/no-go ; le grain **fin** est rapporté
à côté et l'écart entre les deux est le chiffre qui dit combien de retournements sont des
transitoires intra-tour.

### 2.2 Les quatre définitions

Écrites sur la suite `S_f`. Une **partie** satisfait une définition si **au moins une** de ses
4 familles la satisfait.

| # | Nom | Énoncé sur `S_f` |
|---|---|---|
| **R0** | toute transition | `∃ t : s_t ≠ s_{t−1}` |
| **R1** | inversion de signe | dans `S_f` privée de ses `Indifférente`, deux valeurs consécutives ont des signes opposés (Lumière puis Obscurité, ou l'inverse) |
| **R2** | **perte d'acquis** | `∃ t : s_{t−1} ≠ Indifférente et s_t ≠ s_{t−1}` |
| **R3** | divergence finale | le premier statut non-Indifférent `p` de `S_f` existe, et `s_T ≠ p` |

**Le go/no-go porte sur `R2`.** Arbitré par l'auteur le 17/08, et déjà tranché par l'encadré
du §2.2 des règles : « **Le seuil qui compte est l'Indifférence, pas l'Obscurité.** Raisonner
uniquement sur le basculement en Obscurité fait croire une position sûre alors qu'elle est
fragile. » R2 est exactement cet énoncé rendu mesurable : une famille qui rapportait quelque
chose cesse de rapporter ce qu'elle rapportait — qu'elle tombe à zéro ou qu'elle s'inverse.

**Pourquoi les trois autres sont rapportées quand même.** Parce que le chiffre change avec la
définition, et qu'un lecteur doit pouvoir voir de combien.

- **R0 est inutilisable comme critère** et sera rapportée pour le montrer : la première carte
  posée au banquet dans une famille la fait passer d'Indifférente à Lumière ou Obscurité,
  ce qui est une transition. R0 mesure donc « une famille a-t-elle reçu une carte au
  banquet », pas un retournement. *SUPPOSÉ : proche de 100 %.*
- **R1 est la lecture littérale** du mot « retournement » : le signe s'inverse.
- **R3 est la lecture « ce qui reste à la fin »** : seul le statut final rapporte des points
  (§2.1 des règles), donc R3 mesure les retournements qui ont **survécu**.

### 2.3 Ce qu'on ne suppose pas

Les inclusions vraies sont `R1 ⊆ R2`, `R3 ⊆ R2`, `R2 ⊆ R0`. **`R1` et `R3` ne sont pas
ordonnées** : une famille Lumière → Obscurité → Lumière satisfait R1 et pas R3.

Les quatre chiffres sont donc rendus **sans hiérarchie supposée**, et les trois inclusions
ci-dessus sont **vérifiées sur les 1 000 parties**, partie par partie, plutôt que déduites —
une inclusion qui tombe désignerait un défaut du compteur.

### 2.4 Isoler la contribution des Espions cachés

Un Espion posé au banquet compte dans le statut vrai mais **son identité n'est connue que de
son poseur** (§4.2 des règles). Un retournement qu'il provoque n'est visible d'aucun des deux
autres joueurs — donc il ne peut être ni anticipé, ni planifié par eux.

On calcule donc, en parallèle du statut vrai, un **statut public** : la même formule, sur les
seules cartes du banquet **face visible**. Et on rapporte :

- `R2` sur le statut vrai — le chiffre du go/no-go ;
- `R2` sur le statut public — les retournements que **tout le monde** voit ;
- l'écart entre les deux, c'est-à-dire les parties dont le retournement n'existe que dans la
  vue de dieu.

---

## 3. « Distribution non dégénérée » — les quatre seuils

Le protocole exige que la distribution des scores finaux ne soit « pas dégénérée » sans
donner de seuil. Proposition, chiffrée et justifiée. La distribution porte sur les
`1 000 × 3 = 3 000` scores finaux, examinés **par siège**.

| # | Critère | Seuil | Justification |
|---|---|---|---|
| **D1** | écart-type du score final, pour chaque siège | **≥ 1 point** | 1 point est le plus petit quantum marquable — une carte standard dans une famille en Lumière. Une distribution dont la dispersion est inférieure à son propre quantum est constante en pratique. |
| **D2** | nombre de valeurs de score distinctes, pour chaque siège | **≥ 8** | l'amplitude a priori atteignable est de l'ordre de 25 valeurs (un domaine reçoit ~8 cartes de valeur 1 ou 2, de signe ±). Moins d'un tiers de cette amplitude sur 1 000 parties signifie que le jeu ne produit qu'une poignée d'issues. |
| **D3** | part de la valeur modale, pour chaque siège | **< 50 %** | si une seule valeur couvre la moitié des parties, le score est une constante bruitée. |
| **D4** | part des parties à **trois ex æquo** | **< 50 %** | le gain du §5.2 vaut `0, 0, 0` sur une partie à trois ex æquo : au-delà de la moitié, le signal d'apprentissage est nul plus souvent qu'il ne dit quelque chose. |

**Ces quatre seuils sont une proposition de l'agent**, pas une reprise d'un document
existant. Ils sont écrits avant la mesure précisément pour qu'on ne puisse pas les ajuster
après.

---

## 4. Instrument

| Point | Valeur |
|---|---|
| Instance | `GameConfig(familles=4, roles=tuple(Role), exemplaires=2, joueurs=3)` |
| Nombre de parties | **1 000** |
| Donne | `Engine.reset(seed)` avec `seed = 0 … 999` |
| Politique | **uniforme sur `legal_actions()`**, pour les trois joueurs, en phase POSE comme en phase CIBLAGE |
| Aléa de la politique | `random.Random(1_000_000 + seed)`, une instance par partie, **distincte de celle de la donne** |
| Observation | `vue_privilegiee()` après chaque `apply()` |
| Reproductibilité | la commande exacte est donnée dans le compte rendu ; rejouer doit rendre les mêmes chiffres au bit près |

**La politique uniforme n'est pas une IA.** Elle ne lit pas l'état : elle tire un indice dans
la liste des actions légales. Le §4 des conventions et la consigne de phase 1 interdisent
toute heuristique, toute évaluation de position ; il n'y en a aucune.

### 4.1 Les quantités mesurées

| Quantité | Définition opératoire |
|---|---|
| Tours par joueur | nombre de poses effectuées par chaque siège, compté sur la trace |
| Durée machine | temps mural par partie, et total du run |
| Longueur de partie | nœuds de décision : poses (constante attendue 12) et ciblages |
| Score final | `state.scores()` à l'état terminal, par siège |
| Gains | `state.returns()`, contrôle de somme nulle |
| Retournements | R0/R1/R2/R3, par partie et par famille, aux deux grains, statut vrai et statut public |
| Refuser de tuer possible | nœuds de phase CIBLAGE où `len(legal_actions()) ≥ 2`, c'est-à-dire au moins une cible valide en plus du refus |

### 4.2 Le seuil, et à quel nombre de parties il tranche

Le seuil de H3 est `p ≥ 1/3`, `p` = proportion de parties avec au moins un retournement R2.

- À **N = 1 000**, l'intervalle de Clopper-Pearson à 99 % a une demi-largeur d'au plus
  **±3,9 points** autour de 1/3. La mesure **tranche** dès que la proportion observée est
  hors de **[0,295 ; 0,372]**, et le compte rendu donnera l'intervalle exact.
- Elle **tranche bien plus tôt si le résultat est net** : à `p̂ ≥ 0,80`, la borne basse à 99 %
  dépasse 1/3 dès **N = 30**. C'est le cas attendu.
- **Si la proportion observée tombe dans la bande d'indécision**, le résultat rapporté est
  « **indécis** », pas « proche du seuil » : conclure demanderait `N ≈ 40 000` parties pour
  une proportion vraie à 0,35, et cette expérience-là serait à redessiner, pas à rallonger.

### 4.3 Budget

Coût attendu : *SUPPOSÉ* quelques secondes de CPU pour 1 000 parties — 36 poses par partie,
moteur en stdlib pure. Le protocole annonce « quelques minutes ». Si le run dépasse
**5 minutes**, c'est un défaut d'instrumentation, pas un résultat, et il est signalé comme
tel.

---

## 5. Ce que cette mesure n'établira pas

Écrit avant la mesure, pour ne pas être écrit après coup en fonction du résultat.

1. **L'aléatoire n'est pas le jeu.** Une fréquence de retournements sous politique uniforme
   établit que l'instance **rend le mécanisme atteignable**. Elle n'établit pas qu'un agent
   pourra en **planifier** un (comportement B1), ni qu'un agent entraîné en produira autant,
   ni moins — un agent peut très bien les éviter.
2. **Un retournement mesuré n'est pas un retournement décisif.** Rien ici ne relie un
   retournement au vainqueur de la partie.
3. **Un retournement invisible n'est pas planifiable.** La mesure porte sur le statut vrai,
   Espions cachés compris ; la part que les autres joueurs ne peuvent pas voir est isolée
   (§2.4), et cette part-là ne peut, par construction, être anticipée par personne d'autre
   que le poseur.
4. **La mesure ne dit rien de l'instance complète** `complet-3j`. 4 familles et 4 tours ne se
   comparent à 6 familles et 10 tours par aucun chiffre produit ici.
5. **La mesure ne valide pas le moteur.** Elle le suppose conforme — c'est la phase 0 qui
   l'établit, et elle est close.
6. **Les seuils du §3 sont une proposition**, non un fait mesuré. Si l'auteur en retient
   d'autres, les chiffres bruts du compte rendu permettent de recalculer la décision sans
   relancer la mesure.
