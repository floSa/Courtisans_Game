# Phase 2 — les sept définitions de B1 à B7, et ce que chaque concurrente donne

Le §7.2 des règles décrit sept comportements **en prose**. Le §6 de
[phase2_hypothese_et_instrument.md](phase2_hypothese_et_instrument.md) en a fixé, **avant toute
mesure**, une définition opérationnelle et — pour chacune — une ou plusieurs définitions
**concurrentes**, avec le sens de l'écart attendu.

Ce document met les deux côte à côte : la définition retenue, sa concurrente, le **chiffre** de
chacune, et le verdict sur le sens annoncé d'avance.

**L'audit croisé a rendu REJETÉ, et ce document a été corrigé en conséquence.** Les quatre
défauts, leurs corrections et les tests qui les tiennent sont dans
[phase2_corrections_audit.md](phase2_corrections_audit.md). Trois d'entre eux touchent ce qui est
écrit ici : le grain des lignes `-par-partie` (§1), la lecture des trois compteurs de B4 (§4), et
le nombre de compteurs aveugles par le bas (§7).

**Ce qui est autoritatif.** Les comptes viennent de [resultats/phase2.md](resultats/phase2.md),
généré par `UV_LINK_MODE=copy uv run python -m mesure.phase2`. Ce document ne recalcule rien : il
recopie des couples `numérateur/dénominateur` et en tire des écarts. En cas de divergence, le
rapport généré a raison et celui-ci a tort.

**Deux colonnes, pas une.** « Le greedy fait B4 dans X % des cas » n'est pas interprétable sans
savoir ce que le hasard donne. Colonne **greedy** : campagne B, 10 002 parties, siège du greedy
seul, seeds 0 à 3333. Colonne **hasard** : campagne A, 10 002 parties, les trois sièges, seeds 0 à
1666. Les dénominateurs de la colonne hasard sont donc environ trois fois ceux de la colonne
greedy, et c'est voulu.

---

## 0. Les douze sens annoncés d'avance, et leur verdict

Une définition concurrente sans direction attendue n'est pas falsifiable. La pré-inscription en a
donc annoncé douze. **Onze tiennent, une est infirmée.**

| # | Concurrente | Sens annoncé | Mesuré | Verdict |
|---|---|---|---|---|
| 1 | `B1-tentative` | plus grand | 55,63 % contre 47,93 % | ✅ |
| 2 | `B1-strict` | plus petit | 38,66 % contre 47,93 % | ✅ |
| 3 | `B1-collectif` | beaucoup plus grand | 70,07 % contre 47,93 % | ✅ |
| 4 | `B2-banquet` | **beaucoup plus grande** | **34,89 % contre 68,32 %** | ❌ **infirmée** |
| 5 | `B2-fragile-2` | plus grande | 78,83 % contre 68,32 % | ✅ |
| 6 | `B2-cibles` | plus grande encore, borne haute | 80,84 %, la plus grande des trois | ✅ |
| 7 | `B3-simultané` | plus petite | 9,84 % contre 33,27 % | ✅ |
| 8 | `B4-contre-nature` | **exactement 0** chez le greedy | 0/4773 | ✅ |
| 9 | `B4-meurtre-coûteux` | **exactement 0** chez le greedy | 0/15406 | ✅ |
| 10 | `B5-pire-cas` | sélectionne **d'autres** nœuds | dénominateur 13 956 contre 18 671, −25,3 % | ✅ |
| 11 | `B6-dernier-contre-reste` | plus stable, mais mélange trois états | dilue d'un facteur **1,9 à 2,8** selon le groupe | ✅ |
| 12 | `B7-lumière` | nettement plus grande | 11,81 % contre 0,15 %, soit **×77,4** | ✅ |

Une seule concurrente était annoncée **sans** direction — `B1-savoir-commun`, « inconnu, à
mesurer » — et son chiffre est au §1.

**Le sens infirmé, et pourquoi il était faux d'avance.** J'annonçais `B2-banquet` « beaucoup plus
grande » que `B2-contestée`, en raisonnant comme si la zone à enjeu était toujours le banquet. Une
pose place **trois** cartes — banquet, domaine propre, domaine adverse (§3.2) —, donc la part des
Assassins qui atterrissent au banquet est bornée par la mécanique du coup, autour d'un tiers :
**34,89 %**, dont 18,82 % en Estime et 16,07 % en Disgrâce. `B2-contestée`, elle, compte l'enjeu
**dans n'importe laquelle des trois zones**. Les deux ensembles ne s'emboîtent pas ; ce sont des
questions différentes, et je les avais lues comme emboîtées.

---

## 1. B1 — Planifier un retournement

> **Règles §7.2** : nourrir une famille chez un adversaire, puis la basculer en Obscurité en fin
> de partie.

**Retenue — `B1-motif`**, quatre clauses. À `t₁`, `i` donne une carte de famille `f` à `j` alors
que `f` est **Lumière ou Indifférente dans la vue de `i`** ; à `t₂ > t₁`, `i` fait baisser
l'influence de `f` ; au décompte `f` est **Indifférente ou en Obscurité dans la vue vraie** ; et
`j` détient encore une carte de `f` **vivante**.

| | |
|---|---|
| Dénominateur | couples **(partie, siège mesuré)** |
| Vue | clauses 1–2 sur la vue du décideur, clauses 3–4 sur la **vue vraie** — c'est le statut qui **paie** |

| Définition | Greedy | Hasard | Écart au retenu (greedy) |
|---|---|---|---:|
| **`B1-motif`** (retenue) | **47,93 %** (4794/10002) | **36,11 %** (10836/30006) | — |
| `B1-tentative` — sans les clauses 3 et 4 | 55,63 % (5564/10002) | 49,05 % (14717/30006) | +7,70 pt |
| `B1-strict` — clause 3 exige l'Obscurité | 38,66 % (3867/10002) | 26,53 % (7962/30006) | −9,27 pt |
| `B1-collectif` — `t₁` et `t₂` de joueurs différents | 70,07 % (7008/10002) | 67,18 % (20157/30006) | +22,14 pt |
| `B1-savoir-commun` — clause 1 sur la vue **publique** | 48,27 % (4828/10002) | 36,21 % (10865/30006) | +0,34 pt |

**Ce que chaque concurrente change.**

- **`B1-tentative`** compte les tentatives ratées : **7,70 points** des motifs amorcés par le
  greedy n'aboutissent pas. Chez le hasard, **12,94 points**. La retenue est plus exigeante, et
  c'est ce qu'on veut d'un compteur qui prétend parler de retournement.
- **`B1-strict`** applique le seuil de l'Obscurité au lieu de l'Indifférence. Le §2.2 des règles
  dit que le seuil qui compte est **l'Indifférence** : une famille indifférente ne rapporte plus
  rien. `B1-strict` est donc plus petite pour une raison de règle, pas de statistique.
- **`B1-collectif`** est **la** concurrente à ne pas confondre avec la retenue : +22,14 points, et
  elle ne mesure **plus une intention**. Une bascule par un adversaire suffit. Elle majore
  `B1-motif` par construction, et cette inclusion est **vérifiée** dans le rapport, pas déduite —
  elle est tombée une fois.

  **Et c'est le seul compteur dont la ligne de base de référence n'était pas utilisable.** Son
  numérateur peut être produit **entièrement par les adversaires** : mesuré avec un greedy contre
  deux politiques uniformes, il mélange la bascule du greedy et celles de deux hasards. La phase 3
  fera jouer les trois sièges par des agents entraînés, donc c'est la population à **trois greedys**
  qui donne sa ligne de base : **71,78 %** (21538/30006) contre **67,18 %** pour le hasard, soit
  **+4,60 pt** et **2 234** parties pour l'établir — là où la composition de référence donnait
  +2,89 pt et 5 868 parties. Le critère du périmètre est textuel : `B1-collectif` est le seul dont
  la **définition nomme un autre joueur**.
- **`B1-savoir-commun`** n'a **aucune inclusion** avec la retenue, dans aucun des deux sens :
  retirer un dos du plateau peut faire **monter comme descendre** l'influence perçue d'une
  famille. Les deux cas sont construits à la main dans
  `tests/mesure/test_comportements.py` — un où le donneur voit un poison que le savoir commun ne
  voit pas, un où c'est l'inverse. C'est pourquoi son écart se publie **sans direction attendue**.
  C'était la seule concurrente annoncée **sans** direction, « inconnu, à mesurer », et voici la
  mesure : **+0,34 point** chez le greedy (4828 contre 4794 sur 10 002), **+0,10 point** chez le
  hasard (10865 contre 10836 sur 30 006). **Le savoir privé ne déplace presque pas le jugement de
  la clause 1 de B1** — 34 parties sur 10 002 changent de verdict. À comparer aux **1,33 point**
  que le même savoir privé déplace sur `B2-contestée` : la vue du décideur pèse pour placer un
  Assassin, presque pas pour juger si une famille est déjà empoisonnée. Cet écart entre les deux
  compteurs est un résultat, et il n'était pas prévisible — c'est bien pourquoi la pré-inscription
  n'annonçait pas de direction. Accessoirement `B1-savoir-commun` est **légèrement plus
  discriminante** que la retenue : **401** parties pour établir son écart greedy−hasard de
  **+12,06 pt**, contre **418** pour `B1-motif`. Cela ne la promeut pas : la retenue qualifie une
  **décision**, et une décision se juge sur ce que le décideur savait.

**Un dénominateur concurrent, et c'est lui qui a failli fausser la conclusion.** B1 est le seul
des sept dont le dénominateur naturel est la partie et non une action. La lecture « au moins un
siège mesuré porte le motif » donne, **sur les mêmes parties** :

| Grain | Greedy (1 siège) | Hasard (3 sièges) |
|---|---|---|
| couples (partie, siège) — retenu | 47,93 % (4794/10002) | **36,11 %** (10836/30006) |
| parties, « au moins un des N sièges » | 47,93 % (4794/10002) | **71,90 %** (7191/10002) |

Comparer 47,93 % à 71,90 % faisait conclure « **le greedy montre le motif moins que le hasard** »,
soit **l'inverse de la vérité**. Le numérateur monte avec le nombre de sièges agrégés, le
dénominateur non. C'est mot pour mot la faute de la phase 1 : un chiffre juste dont la phrase et le
calcul n'ont pas le même sujet grammatical.

**Et c'était encore un défaut au moment de l'audit croisé, dans une autre table.** Le §5 du rapport
portait l'avertissement ; le §6 — celui qui est titré *M4 pour la phase 3* — soustrayait quand même
les deux colonnes et publiait un « parties pour l'établir » pour l'écart de signe inversé. Trois
choses ont changé, et la première est celle qui compte :

1. **le libellé de grain porte le nombre de sièges** — `parties (au moins un des 1 sièges mesurés)`
   contre `parties (au moins un des 3 sièges mesurés)`. Les deux colonnes portaient jusque-là
   **exactement le même libellé**, donc comparer les libellés n'aurait rien détecté ;
2. **`comportements.ecart_de_taux` lève** quand les grains diffèrent, et `cumuler` aussi. Une
   cellule corrigée se re-remplit ; une levée, non ;
3. le §6 écrit **`non comparable : grains différents`**, jamais un tiret.

**La comparaison par partie existe désormais, mais pas dans cette colonne.** La population à
**trois greedys** agrège trois sièges des deux côtés : le grain coïncide et la soustraction est
licite. Elle est au §5 bis du rapport. La colonne du greedy de référence, elle, ne sera jamais
comparable au hasard à ce grain, et c'est écrit à sa place.

**Et B1 n'est pas homogène par siège** — MESURÉ sur 500 donnes × 6 réplicats, politique uniforme :
**37,93 / 36,80 / 33,50 %**, 4,4 points d'étendue, parce que le siège 0 pose en premier et laisse
donc plus de nœuds ultérieurs disponibles pour une bascule. Toute ligne de base B1 doit être
**équilibrée sur les sièges** ; les deux colonnes ci-dessus le sont.

---

## 2. B2 — Placer l'Assassin là où il pourra servir

> **Règles §7.2** : au banquet sur une famille contestée plutôt que dans un domaine sans enjeu ;
> distribution des zones.

**Retenue — `B2-contestée`** : parmi les poses d'Assassin, celles dont la zone de destination
contient, au moment de la pose, au moins une **cible valide** d'une famille dont l'influence
`|d| ≤ 1` **dans la vue du poseur**. `|d| ≤ 1` est la fragilité du §2.2 : à `d = ±1` une carte
standard annule et un Noble inverse.

| Définition | Greedy | Hasard | Écart au retenu (greedy) |
|---|---|---|---:|
| **`B2-contestée`** (retenue) | **68,32 %** (16391/23991) | **64,90 %** (46790/72090) | — |
| `B2-contestée-publique` — savoir commun | 67,00 % (16073/23991) | 63,01 % (45427/72090) | −1,33 pt |
| `B2-fragile-2` — seuil `\|d\| ≤ 2` | 78,83 % (18911/23991) | 75,22 % (54225/72090) | +10,50 pt |
| `B2-cibles` — une cible valide, sans enjeu | 80,84 % (19395/23991) | 78,58 % (56651/72090) | +12,52 pt |
| `B2-banquet` — la seule part posée au banquet | **34,89 %** (8371/23991) | 33,35 % (24041/72090) | **−33,43 pt** |

Dénominateur commun : **poses d'Assassin**, 23 991 pour le greedy, 72 090 pour le hasard.

**Ce que chaque concurrente change.**

- **`B2-contestée-publique`** mesure exactement ce que le savoir privé déplace : **1,33 point**
  chez le greedy, **1,89 point** chez le hasard. C'est petit, et c'est un résultat — un joueur qui
  a posé lui-même un Espion juge la zone un peu plus contestée que ne le ferait un observateur.
  Les deux chiffres répondent à des questions différentes (« le décideur croyait-il placer son
  Assassin là où il servirait » contre « le coup était-il contesté aux yeux d'un observateur ») et
  se publient donc ensemble, jamais l'un à la place de l'autre.
- **`B2-fragile-2`** desserre le seuil de fragilité d'un cran : +10,50 points. L'écart mesure
  combien de zones sont « presque » contestées.
- **`B2-cibles`** retire toute condition d'enjeu : c'est la **borne haute**, 80,84 %. Elle dit
  que sur 4 poses d'Assassin sur 5 il y avait *quelque chose* à tuer, ce qui ne dit rien de
  l'intérêt du coup — et c'est précisément l'écart de 12,52 points avec la retenue qui montre ce
  que la condition d'enjeu retire.
- **`B2-banquet`** est la concurrente **infirmée** (§0). Elle est aussi la seule des quatre à ne
  pas être comparable par inclusion : les autres emboîtent la retenue, elle la coupe.

**La distribution des quatre destinations**, que le §7.2 demande explicitement — dénominateur :
poses d'Assassin.

| Destination | Greedy | Hasard |
|---|---|---|
| banquet-Estime | 18,82 % (4515/23991) | 16,74 % (12066/72090) |
| banquet-Disgrâce | 16,07 % (3856/23991) | 16,61 % (11975/72090) |
| domaine propre | 30,29 % (7266/23991) | 33,14 % (23888/72090) |
| domaine adverse | 34,82 % (8354/23991) | 33,52 % (24161/72090) |

Le hasard est à peu près uniforme sur les trois zones — 33,35 / 33,14 / 33,52 % — ce qui est le
contrôle attendu, une pose plaçant une carte dans chacune. Le greedy s'en écarte de **2,85 points**
sur son propre domaine, au profit du domaine adverse.

---

## 3. B3 — Fabriquer une alliance

> **Règles §7.2** : nourrir un joueur sur une famille où l'IA est elle-même exposée ; corrélation
> entre les familles données et celles que l'IA détient.

**Retenue — `B3-exposé`** : une pose par `i` d'une carte de famille `f` chez `j`, alors que le
domaine de `i` contient déjà une carte de `f` **vivante connue de `i`**. `i` est alors
**objectivement allié de `j` sur `f`** au sens du §2.4.

| Définition | Greedy | Hasard | Écart au retenu (greedy) |
|---|---|---|---:|
| **`B3-exposé`** (retenue) | **33,27 %** (13309/40008) | **46,72 %** (56075/120024) | — |
| `B3-exposé-vraie` — vue de dieu | 38,33 % (15334/40008) | 50,33 % (60403/120024) | +5,06 pt |
| `B3-simultané` — `f` en Lumière dans la vue de `i` | 9,84 % (3935/40008) | 15,07 % (18088/120024) | −23,43 pt |
| `B3-corrélation` — lecture littérale du §7.2 | **sans chiffre** | **sans chiffre** | — |

Dénominateur commun : **poses en domaine adverse**, 4 par siège et par partie.

**Ce que chaque concurrente change.**

- **`B3-exposé-vraie`** borne le possible : **5,06 points** du motif échappent au décideur, parce
  qu'un Espion adverse posé dans son domaine ne lui est pas identifiable. C'est la mesure de son
  angle mort, et elle ne qualifie **aucune décision** — d'où la vue du décideur en primaire.
- **`B3-simultané`** exige que `f` soit déjà **en Lumière** dans la vue de `i`, pas seulement
  non-Obscurité : −23,43 points. Elle est plus proche d'une intention, et c'est aussi le compteur
  B3 le plus discriminant après la retenue.

**`B3-exposé` est le compteur qui sépare le plus fort des dix-huit** : l'écart greedy−hasard vaut
**−13,45 points**, et **72 parties** suffiraient à l'établir. Le greedy nourrit un adversaire sur
une famille où il est exposé **beaucoup moins** que le hasard. Attention à la lecture : il ne
modélise pas l'intérêt qu'il crée en donnant une carte — son B3 mesure la **coïncidence** entre ce
qu'il détient et ce qu'il donne, jamais une alliance construite.

**Pourquoi `B3-corrélation` n'a pas de chiffre, et c'est un trou de ma livraison.** La lecture
littérale du §7.2 demande une corrélation, sur toute la partie, entre le multi-ensemble des
familles données à `j` et celui que `i` détient. Trois raisons de ne pas la chiffrer maintenant, et
une seule est bonne :

1. **Ce n'est pas un taux d'action.** Elle rend un nombre par **(partie, couple ordonné)** —
   DÉDUIT : 3 sièges × 2 adversaires = 6 par partie, soit **60 012** nombres sur la campagne B là
   où la retenue rend un taux sur 40 008 poses. Elle n'entre donc pas dans le tableau de pouvoir
   discriminant, qui compare des proportions.
2. **Elle ne distingue pas une alliance construite d'une coïncidence de pioche** — c'est
   l'argument écrit au §6.3 de la pré-inscription, et il reste vrai.
3. **Et voici la mauvaise raison : sa définition a deux paramètres libres que ma pré-inscription
   n'a pas fixés** — quel indice de recouvrement, et ce que « `i` détient » désigne (sa main, son
   domaine, les deux). Les fixer **maintenant**, après avoir vu les autres chiffres, serait
   exactement la liberté que la pré-inscription existe pour supprimer. Je ne le fais donc pas, et
   je le remonte tel quel : **une concurrente annoncée doit être définie au même niveau de
   précision que la retenue, ou ne pas être annoncée.**

---

## 4. B4 — Refuser de tuer quand le meurtre coûterait

> **Règles §7.2** : fréquence des situations où refuser de tuer est possible.

**La lecture littérale est vide, et c'est le premier résultat de B4.** Refuser est **toujours**
légal (§4.1, arbitrage R2) : « fréquence des situations où refuser est possible » vaut donc
**100 % par construction**, sur tout agent, sans rien mesurer. Le dénominateur retenu est les
**nœuds de ciblage offrant au moins une cible**, où refuser est un **choix** et non un constat.

**Retenue — trois nombres qui somment aux refus, plus deux de contexte.** Le partage entre les deux
premiers est ce qui distingue un comportement d'un tirage au sort.

| Définition | Greedy | Hasard | Ce qu'elle est |
|---|---|---|---|
| `B4-brut` — taux de refus | **23,65 %** (4773/20179) | **30,28 %** (18059/59645) | la grandeur demandée par le §7.2 |
| `B4-strict` — tout meurtre baissait strictement l'écart | **38,78 %** (1851/4773) | 7,96 % (1437/18059) | **un comportement** |
| `B4-départage` — refuser était à égalité | **61,22 %** (2922/4773) | 58,32 % (10532/18059) | **un tirage au sort** |
| `B4-contre-nature` — un meurtre était strictement meilleur | **0 %** (0/4773) | 33,72 % (6090/18059) | **un défaut** |
| `B4-tout-dos` — toutes les cibles sont des dos | 3,89 % (784/20179) | 5,02 % (2994/59645) | contexte |
| `B4-meurtre-coûteux` — symétrique du refus | **0 %** (0/15406) | 4,77 % (1983/41586) | contrôle |

**Identité vérifiée, non déduite** : `1851 + 2922 + 0 = 4773` refus chez le greedy,
`1437 + 10532 + 6090 = 18059` chez le hasard. `comportements.verifier_b4` **lève** si elle tombe.

**Le dénominateur concurrent, et il change tout.** Prendre **tous** les nœuds de ciblage, comme le
ferait la lecture littérale, y compris ceux sans aucune cible où le refus est **forcé** :

*DÉDUIT, sous l'hypothèse que le taux de 82,53 % de nœuds à ≥ 1 cible mesuré en phase 1 sous jeu
aléatoire vaut aussi sur la campagne B — non re-mesuré.* Total des nœuds de ciblage du greedy
≈ 20 179 / 0,8253 = **24 450**, dont ≈ **4 271** sans cible, tous refus forcés. Le taux de refus
deviendrait `(4773 + 4271)/24450` = **36,99 %** au lieu de 23,65 %, soit un facteur **1,56**.

Et mon propre §6.4 annonçait un facteur `1/0,8253` = **1,21** : c'est faux, parce que ce facteur
suppose le numérateur inchangé alors que les nœuds ajoutés sont **tous** des refus. L'ordre de
grandeur de la conclusion tient — le dénominateur littéral gonfle mécaniquement le taux — mais le
chiffre que j'avais écrit d'avance ne tient pas.

**Ce que le partage des trois nombres dit, et c'est le résultat le plus fin de la phase.** Le
départage décide **61,22 %** des refus du greedy, et il déplace son gain de **+0,0011**, soit
**0,09 demi-largeur** de son IC 99 %. Donc **une majorité des refus du greedy sont
stratégiquement indifférents sur cette instance**. Deux usages : il désarme la lecture « le greedy
refuse dans 23,65 % des cas », et il donne un étalon à la phase 3 — un agent qui refuse dans les
mêmes proportions n'a rien appris ; un agent dont les refus déplacent son gain a appris quelque
chose.

**Une surinterprétation retirée.** Mon §5.4.1 désignait les nœuds tout-dos comme **le** mécanisme
de l'égalité. Ils n'en sont qu'un mécanisme **minoritaire** : **3,89 %** des nœuds, contre
**61,22 %** de départage. La majorité des égalités vient de nœuds où une cible identifiable existe
mais dont le meurtre ne change pas l'écart évalué — typiquement une carte d'une famille
Indifférente.

**Les deux zéros ne sont pas « rien à détecter ».** Ils sont nuls **par construction** — `choisir`
prend un argmax —, et un taux nul a une variance estimée nulle : la formule normale rendrait
« écart détectable 0,00 % », soit « tout est détectable », le contraire de la vérité. Ce qui se dit
d'un zéro est sa **borne haute exacte de Clopper-Pearson** : à 1 000 parties, un agent dépassant
**1,10 %** (`B4-contre-nature`) ou **0,34 %** (`B4-meurtre-coûteux`) est **séparable** du greedy ;
en dessous, il ne l'est pas.

**Trois de ces compteurs sont jugés par l'évaluation myope du greedy lui-même, et cela change ce
qu'ils disent.** Défaut majeur relevé par l'audit croisé, et il ne porte pas sur les chiffres mais
sur leur lecture. `B4-strict`, `B4-départage` et `B4-contre-nature` se définissent par rapport à
`greedy.evaluer_actions`, qui **ne regarde pas les Assassins du même bloc encore en attente** — la
pose du greedy est évaluée conjointement, ses ciblages non. Conséquence, mot pour mot :

> Le zéro de `B4-contre-nature` **ne dit pas** que le greedy n'a jamais commis de meurtre
> contre-productif. Il dit qu'il n'a jamais **contredit sa propre évaluation**.

Deux énoncés différents, et **seul le second est vrai**. Les dénominateurs de `B4-strict` et
`B4-départage` sortent du même argmax, donc la même lecture s'applique aux trois. Pour un agent de
la phase 3 ce même zéro cesse d'être tautologique — son argmax n'est pas celui de l'étalon — et
redevient un diagnostic. Le §4 bis du rapport chiffre l'incohérence et son intervalle.

**Sur quelle évaluation « coûterait » est jugé** : sur `agents.greedy.evaluer_actions`, y compris
pour l'agent de la phase 3, dont la fonction de valeur propre ne servira **pas** d'étalon. Le prix
est écrit d'avance : un agent qui refuse par anticipation d'un retournement — donc pour une bonne
raison à horizon long — comptera dans `B4-contre-nature`, et ce cas doit se lire comme un signe de
planification, pas comme un défaut.

---

## 5. B5 — Se méfier des Espions

> **Règles §7.2** : ne pas traiter une majorité serrée comme acquise s'il reste des cartes cachées.

**Retenue — `B5-renfort`** : parmi les nœuds où (a) une famille `f` a `|d| = 1` au banquet **dans
la vue du décideur**, (b) il reste au moins un **dos** au banquet qu'il ne peut pas identifier, et
(c) il a une carte de `f` en main — la part où il **renforce le côté déjà favorable**.

| Définition | Greedy | Hasard | Dénominateur |
|---|---|---|---:|
| **`B5-renfort`** (retenue) | **20,41 %** (3811/18671) | **21,44 %** (11096/51742) | couples (nœud, famille) |
| `B5-pire-cas` — marge pire cas du §2.6 | 19,00 % (2651/13956) | 21,58 % (8563/39674) | couples (nœud, famille) |

**Ce que la concurrente change : le dénominateur, pas le taux.** `B5-pire-cas` remplace `|d|` par
la marge pire cas — `d` diminué de 1 par dos du côté favorable, un dos étant toujours un Espion
donc de valeur 1. Elle **sélectionne d'autres nœuds** : **13 956** contre **18 671**, soit
**−25,3 %**. Les taux, eux, ne diffèrent que de 1,41 point. C'est le sens annoncé au §6.5, et il
tient : la concurrente répond à la même question sur une population différente.

**Ce que la ligne de base du greedy vaut, écrit d'avance et confirmé.** Le greedy traite un dos
comme **absent** : la présence d'un dos n'entre pas dans sa décision, donc sa méfiance est
**nulle par construction**. `B5-renfort` chez lui ne mesure qu'une chose : à quelle fréquence son
évaluation myope l'amène à renforcer. L'écart greedy−hasard, **−1,03 point**, demanderait
**19 030** parties pour être établi : **`B5-renfort` ne peut rien tester au budget de la phase 3**.
`B5-pire-cas`, avec **3 846**, non plus.

**L'objectif de précision fixé d'avance est tenu, et pas là où je l'attendais.** Je prévoyais que
B5 serait le plus étroit des sept et tomberait sous 3 000 observations, donc publié avec son
intervalle et un avertissement. Ses deux dénominateurs sont à **18 671** et **13 956** : le seuil
de 3 000 n'est franchi par aucun des dix-huit compteurs.

---

## 6. B6 — Exploiter la pioche connue

> **Règles §7.2** : jouer différemment en fin de partie, quand l'incertitude tombe.

**Retenue — `B6-distance`** : la **distance de variation totale** entre la distribution des
catégories d'action au **tour 1** et celle au **tour 4**, sur trois groupes fixés avant de mesurer
— banquet (Estime / Disgrâce), domaine adverse (cadeau / neutre / poison), ciblage (refus /
meurtre). Chaque groupe garde **son** dénominateur ; les trois ne sont jamais agrégés.

| Groupe | Retenue — tour 1 contre tour 4 | | Concurrente — tour 4 contre tours 1–3 | |
|---|---:|---:|---:|---:|
| | **Greedy** | **Hasard** | **Greedy** | **Hasard** |
| banquet | 0,1589 | 0,0017 | 0,0560 | 0,0036 |
| domaine adverse | 0,6566 | 0,5823 | 0,3328 | 0,2918 |
| ciblage | 0,2793 | 0,2712 | 0,1438 | 0,1366 |

**Ce que la concurrente change.** `B6-dernier-contre-reste` agrège les tours 1 à 3 dans son terme
de comparaison : trois fois plus de nœuds, donc **plus stable statistiquement** — et trois **états
de plateau différents** mélangés, donc elle **dilue** l'écart qu'elle mesure. Le cas construit à la
main dans `tests/mesure/test_comportements.py` le chiffre exactement : sur un agent qui joue Estime
au tour 1 puis Disgrâce aux tours 2, 3 et 4, la retenue vaut **1** — le maximum, les deux tours
n'ont aucune catégorie commune — et la concurrente **1/3**. Le même comportement, deux chiffres
dans un rapport de 3.

**Le facteur de dilution, mesuré.** La concurrente rend, groupe par groupe, **1,9 à 2,8 fois**
moins que la retenue chez le greedy — 0,0560 contre 0,1589 au banquet (×2,84), 0,3328 contre
0,6566 en domaine adverse (×1,97), 0,1438 contre 0,2793 en ciblage (×1,94). Et surtout elle dilue
le **contraste** greedy−hasard, qui est la seule quantité dont la phase 3 se servira : au banquet
il passe de **0,1572** à **0,0524**, soit un facteur **3,0** ; en domaine adverse de **0,0743** à
**0,0410**, facteur **1,8**. Le sens annoncé au §6.6 tient donc dans ses deux termes — plus stable,
et plus diluée — et le prix de la stabilité est maintenant chiffré.

**Elle n'est nulle chez personne, et ce n'est pas une preuve de compréhension.** L'état du plateau
change avec le tour : au tour 4 plus de cartes sont posées, plus de familles ont un statut tranché,
donc un agent à **horizon d'un tour** joue mécaniquement différemment sans rien savoir de la
pioche. C'est pourquoi la ligne de base est nécessaire : la phase 3 ne conclura que sur l'**écart**
entre la distance de son agent et celles-ci, jamais sur la distance seule.

**Ce que le contraste greedy/hasard dit déjà.** Sur le banquet, le hasard est à **0,0017** — il
joue le tour 4 comme le tour 1, ce qui est la définition d'une politique sans état — et le greedy à
**0,1589** : **deux ordres de grandeur**. Le quotient des deux ne se cite pas -- 0,0017
est un chiffre arrondi au quatrieme decimal, donc son rapport ne serait pas reconstructible. Sur le domaine adverse et le ciblage les deux sont proches
(0,6566 contre 0,5823 ; 0,2793 contre 0,2712) : là, l'essentiel de la variation vient du plateau,
pas de l'agent.

---

## 7. B7 — Ne pas défendre ce qui est déjà sûr

> **Règles §7.2** : sur une famille dont la marge est hors d'atteinte compte tenu du résidu et des
> tours restants, jouer ailleurs ; fréquence des cartes « gaspillées ».

**Retenue — `B7-gaspillage`** : la part des poses au banquet qui placent une carte de famille `f`
**du côté déjà favorable** d'une `f` **hors d'atteinte**. « Hors d'atteinte » signifie
`|d| >` le minimum de deux bornes : le **matériel** encore mobilisable contre `f` d'après le résidu
(morts exclus, §4.1) plus 2 par carte tuable par un Assassin en circulation, et les **occasions**
restantes — `tours_restants × joueurs` poses au banquet, chacune faisant varier `d` d'au plus 2.

| Définition | Greedy | Hasard | Écart au retenu (greedy) |
|---|---|---|---:|
| **`B7-gaspillage`** (retenue) | **0,15 %** (61/40008) | **0,17 %** (203/120024) | — |
| `B7-gaspillage-vraie` — vue de dieu | 0,20 % (82/40008) | 0,24 % (289/120024) | +0,05 pt |
| `B7-lumière` — toute pose renforçant une Lumière | **11,81 %** (4723/40008) | 13,45 % (16140/120024) | **+11,65 pt** |
| `B7-occasions` — contexte : au moins une famille hors d'atteinte | 1,22 % (488/40008) | 1,19 % (1432/120024) | — |

Dénominateur commun : **poses au banquet**, 4 par siège et par partie.

**Ce que la concurrente change, et c'est le plus grand écart des dix-huit.** `B7-lumière` oublie la
borne de portée : elle compte **toute** pose renforçant une famille déjà en Lumière, atteignable ou
non. **11,81 % contre 0,15 %, un facteur 77,4.** C'est la définition qu'on obtient en oubliant la
borne, donc celle qui ferait croire à un gaspillage massif. Publier les deux est le seul moyen de
montrer ce que la borne retire — et 77,4 fois, c'est ce qu'elle retire.

**`B7-gaspillage` n'a aucun pouvoir discriminant au budget de la phase 3, et ce n'est pas une
opinion.** L'occasion ne survient que dans **1,22 %** des poses au banquet — 488 sur 40 008 —, donc
il en resterait de l'ordre de **49** à 1 000 parties. L'écart greedy−hasard observé vaut **−0,02
point** quand l'écart détectable à 1 000 parties est **0,30 %** : il faudrait **320 163** parties
pour trancher. Un lecteur de la phase 3 qui comparerait son agent au 0,15 % comparerait du bruit.

Et l'asymétrie est totale : l'écart détectable, **0,30 %**, vaut **le double du taux mesuré**. Seul
un agent portant ce taux **au triple** — 0,45 % — serait séparable du greedy ; **aucun agent ne peut
en être séparé par le bas**, pas même un agent à 0 %, qui n'est qu'à 0,15 point, soit la moitié du
détectable. Un compteur dont un côté entier est hors d'atteinte ne teste rien de ce côté-là.

**Et ils sont deux, pas un.** C'est le quatrième défaut, relevé par l'humain sur son propre
contrôle : `B7-gaspillage-vraie` est aveugle par le bas de la même façon — **0,35 %** d'écart
détectable contre **0,2050 %** de taux mesuré. Aucun agent ne sera jugé sur la vue de dieu, donc
cela ne change aucune conclusion, mais écrire le cas comme isolé était faux.

La correction n'est pas une phrase : le §6 du rapport **calcule** le critère sur chaque ligne et
liste les compteurs marqués. Une prose se corrige une fois ; un critère n'oublie pas la ligne
suivante.

C'est un fait de **l'instance** — sur 4 tours, une famille devient rarement hors d'atteinte avant
la fin — et non un défaut du compteur. `B7-occasions` existe précisément pour que ce quasi-zéro ne
se lise pas comme « il ne gaspille pas ».

**Une réserve qui reste ouverte.** `_poids_de_bascule_disponible` est une **proposition** : je n'ai
pas démontré qu'elle est la borne minimale. Une borne plus serrée classerait davantage de familles
« hors d'atteinte », donc **`B7-gaspillage` est un plancher**, pas le gaspillage.

---

## 8. Ce qui reste sans chiffre, en un endroit

| Concurrente annoncée | État | Pourquoi |
|---|---|---|
| `B3-corrélation` | **sans chiffre** | pas un taux ; et deux paramètres libres que la pré-inscription n'a pas fixés — les fixer après avoir vu les autres chiffres serait exactement la liberté que la pré-inscription supprime (§3) |

Une seule des treize concurrentes annoncées reste sans chiffre. `B1-savoir-commun` et
`B6-dernier-contre-reste` étaient dans ce même état — **annoncés dans la pré-inscription et jamais
implémentés**, ce qui est un trou de ma livraison et non un choix. Ils sont mesurés depuis, sur
l'échantillon publié, et leurs compteurs sont testés sur **deux compositions de sièges** chacun —
l'enseignement de méthode qui a coûté les deux défauts de B1.

**Contrôle de non-régression du rapport.** Le rapport a été régénéré avec les deux nouveaux
compteurs sur les **mêmes seeds**. Le diff avec la version précédente ne contient que les deux
lignes `B1-savoir-commun`, la colonne `B6-dernier-contre-reste` et les durées machine :
**aucun des chiffres déjà publiés n'a bougé**. C'est le contrôle qui établit que les deux ajouts
sont additifs et non comportementaux.
