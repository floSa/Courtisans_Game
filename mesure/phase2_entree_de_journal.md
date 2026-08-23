# Phase 2 — proposition d'entrée de journal

**Ceci est une PROPOSITION.** Je ne modifie pas `documentations/`. L'entrée ci-dessous est au
format du §4 de [08_modele_compte_rendu.md](../documentations/08_modele_compte_rendu.md) et
attend une chose avant d'être reportée dans
[06_journal_decisions.md](../documentations/06_journal_decisions.md) : la décision de l'humain, qui
n'est pas la mienne.

**L'audit croisé a rendu son verdict — REJETÉ — et ses quatre défauts sont corrigés.** Le champ
**Audit** porte donc le verdict réel, ce que l'audit a trouvé que je n'avais pas vu, et ce qu'il a
confirmé. Détail des corrections et de leurs tests dans
[phase2_corrections_audit.md](phase2_corrections_audit.md). Le champ reste ouvert sur un point :
l'audit doit re-vérifier cette liste, et la population à trois greedys qui lui est ajoutée comme
cinquième point.

---

## [2026-08-19] Phase 2 — Ligne de base du terrain : siège, variance, greedy, comportements

**Hypothèse.** Quatre, écrites et commitées dans `mesure/phase2_hypothese_et_instrument.md`
(`710e116`) **avant** la première mesure.

- **H1** — Aucun siège n'a d'avantage sous jeu aléatoire sur `entrainement-3j` : la part de
  victoire des trois sièges reste sous le seuil de **38,00 %** du §4 du protocole.
- **H2** — L'écart-type du score final permet de dimensionner la phase 3, et l'appariement par
  donne « divise par cinq à dix » le nombre de parties nécessaires — ce qui **implique**
  `ρ ∈ [0,8 ; 0,9]`, chiffre que le protocole avance sans mesure d'appui.
- **H3** — Un greedy à horizon d'un tour bat significativement trois politiques uniformes, et
  son écart au niveau neutre est mesurable au budget de la phase.
- **H4** — Les sept comportements B1 à B7 décrits **en prose** au §7.2 des règles admettent
  chacun une définition opérationnelle dont la ligne de base est mesurable, non dégénérée, et
  comparable à celle du hasard.

**Instrument.** Pré-inscription de 973 lignes commitée avant toute mesure : les quatre
hypothèses, leurs seuils, les sept définitions opérationnelles avec leurs **concurrentes**, la
règle de départage du greedy comme élément d'instrument, la vue sur laquelle chaque compteur est
défini, et « ce que ces mesures n'établiront pas ». Un greedy écrit pour la phase — il n'existait
pas dans le dépôt —, aveugle à `vue_privilegiee()` **par construction** (il ne reçoit jamais de
`State`) puis **par test**. Trois campagnes de 10 002 parties sur seeds cités, sièges permutés
inconditionnellement, bootstrap **par donne** à 10 000 rééchantillons. Dimensionnement par
calcul **binomial exact**, contrôlé à l'unité contre `scipy.stats`. **894 tests**, `ruff` propre.

- reproduire : `UV_LINK_MODE=copy uv run python -m mesure.phase2`
- rejouer les tests : `UV_LINK_MODE=copy uv run pytest -q`

**Résultat.** Détail décomposé dans `mesure/resultats/phase2.md` ; les sept définitions et leurs
concurrentes chiffrées dans `mesure/phase2_definitions_et_concurrentes.md`. **Douze des treize
concurrentes annoncées d'avance sont chiffrées ; sur les douze sens annoncés, dix sont
falsifiables — neuf tiennent, un est infirmé — et deux sont des contrôles nuls par
construction, vérifiés.** *Corrigé le 20/08/2026, défaut mineur 3 : ce texte disait « onze des
douze sens annoncés tiennent », en comptant comme tenus les deux zéros que la pré-inscription
déclare impossibles à infirmer au §6.4.*

- **M1 — H1 non infirmée, et le seuil du protocole ne servait à rien.** Parts de victoire
  fractionnées **33,42 / 33,50 / 33,08 %** (niveau neutre exact **33,3333 %**), maximum à
  **+0,35 erreur-type** de l'attendu ; bloc de contrôle sur seeds disjoints **34,06 / 32,94 /
  33,00 %**, maximum à **+1,54**. **Aucun des trois seuils n'est franchi.** Le seuil de 38,00 %
  du protocole est à **9,90 erreurs-type** de l'attendu : il ne pouvait rien détecter, et c'est
  un résultat sur le protocole, pas sur le jeu.
- **M2 — H2 infirmée sur son seul chiffre.** Écart-type du score **4,412**, du gain **0,6652**.
  Corrélation intra-donne **ρ = +0,0066**, quand « diviser par cinq à dix » implique
  `ρ ∈ [0,8 ; 0,9]`. L'appariement par donne ne gagne **rien** ici : **1 034** parties sans lui
  et **1 027** avec, pour détecter un écart de gain de +0,10. Écart détectable à 1 000 parties
  appariées : **+0,1013**.
- **M3 — H3 établie.** Greedy contre deux uniformes : gain **+0,7978**, IC 99 %
  [**+0,7857** ; **+0,8101**], part de victoire **86,52 %** (niveau neutre 33,3333 %).
  Composition rapportée à côté, deux greedys contre un uniforme : **+0,2010** et **46,73 %**.
  Variante de robustesse à départage déterministe : **+0,7989**.
- **M4 — H4 établie pour six des sept ; B7 a bien une définition mesurable, mais sa ligne de base
  ne peut rien tester à ce budget.** **Trente-quatre** lignes de compteur publiées — dont 5 au
  grain `-par-partie`, non comparable entre une colonne à un siège et une à trois, et 4 qui forment
  la distribution des destinations d'Assassin. Chacune porte son numérateur, son dénominateur, le
  **grain** de ce dénominateur et sa **vue**, sur deux lignes de base — greedy et hasard. Les deux zéros de contrôle sont exacts :
  `B4-contre-nature` **0/4773** et `B4-meurtre-coûteux` **0/15406**, tous deux nuls par
  construction de l'argmax, publiés avec leur **borne haute exacte de Clopper-Pearson** à
  1 000 parties (**1,10 %** et **0,34 %**) pour qu'un zéro ne se lise pas comme « aucun agent ne
  peut faire mieux ».
- **Deux résultats que la mesure prescrite ne pouvait pas produire.** Le greedy, lui, a un effet
  de siège **massif** : **+0,6965 / +0,8116 / +0,8855**, contraste apparié entre extrêmes
  **+0,1890**, IC 99 % [**+0,1588** ; **+0,2196**]. Et `B1-motif` sous jeu uniforme n'est pas
  homogène par siège — **37,93 / 36,80 / 33,50 %**, 4,4 points d'étendue, parce que le siège 0
  pose en premier : **un siège peut être behavioralement asymétrique sans être avantagé**.
- **Le départage déterministe est le résultat le plus fin de la phase.** Il décide **61,22 %**
  des refus du greedy et déplace son gain de **+0,0011**, soit **0,09 demi-largeur** de son
  IC 99 %. Donc **une majorité des refus du greedy sont stratégiquement indifférents sur cette
  instance** — fait du jeu, pas de l'implémentation.
- **Dix-neuf compteurs sur vingt-sept ne peuvent pas établir, à 1 000 parties, l'écart qu'ils
  montrent** entre le greedy et le hasard — 99 % bilatéral, puissance 80 %, grains `-par-partie`
  exclus parce que non comparables entre une colonne à un siège et une colonne à trois. **Huit**
  sont utilisables sous **500** parties : `B3-exposé` **72**, `B3-exposé-vraie` **96**,
  `B4-strict` **123**, `B3-simultané` **189**, `B1-strict` **377**, `B1-savoir-commun` **401**,
  `B1-motif` **418**, `B4-brut` **477**. Les trois plus extrêmes de l'autre bord : `B7-gaspillage` **320 163**,
  `B5-renfort` **19 030**, `B4-départage` **13 824**. Sur `B7-gaspillage`, l'écart détectable à
  1 000 parties (**0,30 %**) vaut **le double du taux mesuré** (0,15 %) : il ne pourrait séparer
  qu'un agent portant ce taux **au triple**, et **aucun agent ne peut en être séparé par le
  bas** — même un agent à 0 % n'est qu'à 0,15 point, soit la moitié du détectable.

**Audit.** **VERDICT : REJETÉ.** Trois défauts trouvés par l'auditeur, recalculés indépendamment
par l'humain et tenus tous les trois ; un quatrième, mineur, et un **cinquième, majeur**, trouvés
par l'humain — ce dernier dans la table que j'avais ajoutée pour corriger le premier. Les cinq sont
corrigés, chacun avec le test qui le tient.

**Ce que l'audit a trouvé et que je n'avais pas vu.**

- **A1, bloquant — deux grains soustraits dans la table que la phase 3 citera.** Les cinq lignes
  `-par-partie` du §6 soustrayaient un greedy sur **un** siège d'un hasard sur **trois** : le signe
  s'inversait, **+11,82 pt** au même grain contre **−23,97 pt** en mélangeant les deux, et la ligne
  recevait quand même un « parties pour l'établir : 102 ». Mon §5 portait l'avertissement ; mon §6,
  titré *M4 pour la phase 3*, ne contenait ni « grain » ni « comparable ». **C'était la deuxième
  fois au même endroit** — une réserve du tour 2 de la phase 1 portait déjà sur cette section. Son
  compteur indépendant chiffre le mécanisme : le seul changement de grain fait passer B1 de
  **46,78 %** à **84,00 %** sur 600 parties, soit **37,22 points d'artefact**, et le fait que
  84,00 % soit légèrement sous les 84,93 % qu'on attendrait de trois sièges indépendants est la
  signature de sièges corrélés dans une même partie. Corrigé par une **levée** —
  `comportements.ecart_de_taux` refuse deux grains différents — et non par une cellule corrigée :
  une cellule se re-remplit.
- **A2, majeur — la clause du seuil de B1 n'était tenue par aucun test.** La clause 3 dit
  « Indifférente **ou** en Obscurité », et l'auditeur est arrivé à la même lecture du §2.2
  **indépendamment de moi**. Mais il a réintroduit la faute du tour 1 de la phase 1 — restreindre à
  l'Obscurité — et obtenu **913 tests verts, zéro rouge**. La régression aurait coûté **9,27
  points** de taux publié quand l'écart détectable de la phase 3 est de **7,64 points** : plus
  grande que ce que la phase suivante peut mesurer, et silencieuse. Corrigé par une partie
  construite à la main finissant **exactement Indifférente** ; la faute réinjectée fait tomber
  **exactement un test**, celui-là.
- **A3, majeur — le greedy ne fait pas ce que disait sa spécification.** Sa pose est évaluée avec
  ses Assassins résolus conjointement, ses ciblages se décident un nœud à la fois, et `Perception`
  ne porte pas les Assassins en attente. L'incohérence est **structurelle** : l'action de pose de
  l'adaptateur est atomique, donc le bloc est choisi d'un coup pendant que le ciblage se décide
  après, sans mémoire de ce qu'il contenait. Corrigé dans la **description**, pas dans le code — un
  correctif referait un autre agent et invaliderait M3 et M4 entiers.
- **A4, mineur, trouvé par l'humain — deux compteurs aveugles par le bas, pas un.**
  `B7-gaspillage-vraie` l'est aussi : **0,35 %** d'écart détectable contre **0,2050 %** de taux.
  Corrigé par un critère **calculé** sur chaque ligne du §6, pas par une phrase.

**Un point sur lequel j'ai eu raison contre l'humain, et il l'a acté.** Son « plancher global » sur
A3 était trop large. Pour **M3**, plus myope que sa spécification veut dire plus faible, donc
`+0,7978` et `86,52 %` sont bien un **plancher**. Pour **M4**, non : `B4-strict`, `B4-départage` et
`B4-contre-nature` sont jugés **par `evaluer_actions`**, l'évaluation myope elle-même. Le zéro de
`B4-contre-nature` ne dit pas que le greedy n'a jamais commis de meurtre contre-productif ; il dit
qu'il n'a jamais **contredit sa propre évaluation**. **Quatre compteurs, pas un** —
`B4-strict`, `B4-départage`, `B4-contre-nature` et `B4-meurtre-coûteux`, les quatre qui lisent
`decision.valeurs`. J'avais d'abord écrit « trois », et l'omis était **l'un des deux zéros
absolus** : l'audit l'a relevé au tour suivant.

**Une garde qui confondait une mesure avec une phase.** `campagne_b` refusait `nb_greedys=3` en
disant « la mesure n'a plus d'objet » : vrai de **M3** — trois politiques identiques rendent un
tiers de part de victoire par **symétrie** — et faux de **M4**. Scindée en deux gardes, un test par
branche.

**Ce que l'audit a établi et qui ne bouge plus.** Un audit qui confirme est un résultat.

- Rapport régénéré : **395 lignes sur 395 identiques**, tous les chiffres se reconstruisent.
- **Trois concordances obtenues sans mon code** : `σ(gain)` **0,6671** contre **0,6652** ; refus B4
  **23,81 %**, IC 99 % [22,53 ; 25,12], qui contient mon **23,65 %** ; contraste apparié de siège
  **+0,181** contre **+0,189**.
- **Le résultat le plus important est confirmé** : avantage de siège négligeable sous jeu
  aléatoire, **massif** sous jeu greedy.
- **La preuve d'aveuglement est jugée plus forte que la sienne** — statique, dynamique avec
  `vue_privilegiee` piégée, différentielle, chacune assortie d'un test vérifiant que le piège mord.
  Cinq contrôles à lui, dont un balayage de 60 parties permutant l'identité de chaque dos à chaque
  nœud : **rien trouvé**. Le greedy ne triche pas.
- **La lecture de la clause 3 confirmée indépendamment** : deux lectures séparées du même texte
  convergent. C'est le meilleur résultat de cet audit, et il vaut plus que le chiffre.

**A5, majeur, trouvé par l'humain DANS la table ajoutée pour corriger A1 — six budgets gonflés
d'un facteur trois.** La colonne « parties pour l'établir » de la troisième population divisait le
dénominateur par partie par le nombre de sièges. Un compteur `-par-partie` rend **une** observation
de Bernoulli par partie — « au moins un des trois sièges » est un seul booléen, l'agrégation étant
dans son **numérateur** — donc son dénominateur par partie vaut **1,0** et pas 1/3. Le texte que le
générateur imprimait énonçait la faute mot pour mot.

| Ligne | Publié | Juste |
|---|---:|---:|
| `B1-collectif-par-partie` | 3 885 | **1 295** |
| `B1-motif-par-partie` | 895 | **299** |
| `B1-tentative-par-partie` | 715 | **239** |
| `B1-strict-par-partie` | 31 199 | **10 400** |
| `B1-savoir-commun-par-partie` | 838 | **280** |
| **`B1-collectif`** (grain du couple) | **2 234** | **745** |

**La sixième ligne n'était pas dans la liste de l'audit.** `B1-collectif` est au grain du couple
`(partie, siège)` : son dénominateur par partie **est** 3,0 — trois sièges mesurés — et le
générateur passait 1,0. Même cause racine, valeur juste différente.

**C'est la quatrième fois dans ce projet qu'un nombre juste porte une phrase décrivant autre
chose**, et cette fois dans la table ajoutée pour corriger la troisième. Ce n'est pas un échec de
la correction de A1 : la parade lève, les cellules refusent de se remplir. C'est que **toute table
neuve est une première livraison** — ce que j'avais écrit moi-même de cette table, et qui rend la
trouvaille normale.

La parade, exigée par l'humain et de la même forme que celle du grain : **une seule fonction**,
`phase2.budget_d_un_compteur`, appelée par les **trois** tables qui traduisent un écart en budget —
le §6, le §5 bis, et le paragraphe sur B7 qui déduisait aussi son propre dénominateur. Elle reçoit
le **nombre de parties**, calculé du plan (`donnes_b × joueurs`) et jamais déduit d'un compteur. Et
`observations_par_partie` **lève** si un compteur `-par-partie` a un dénominateur différent du
nombre de parties : l'invariant est asserté, pas supposé.

**Contrôle de non-régression de la centralisation** : sur les 19 lignes du §6 que le diff expose,
le couple (dénominateur par partie, parties requises) est **inchangé sur les 19**. Les trois lignes
que l'humain avait reconstruites — 418, 72, 320 163 — sont épinglées par un test.

**Et voici ce que ce contrôle ne dit pas.** Il établit la **neutralité du refactor**, et rien de
plus : que ces 19 lignes ont la **même** unité qu'avant, pas qu'elles ont la **bonne**. Si l'une
d'elles portait un dénominateur par partie faux depuis le début, ce contrôle passerait exactement de
la même façon. C'est le piège du `2 234` appliqué à un **contrôle** au lieu d'un nombre — voir
l'enseignement (g). Ce qui tient l'unité de ces lignes n'est pas ce contrôle : c'est
`observations_par_partie`, qui **lève** quand le dénominateur d'un compteur `-par-partie` n'est pas
le nombre de parties, et le cas qui l'exerce sur deux compositions de sièges.

**Un désaccord de valeur reste ouvert sur A3, et c'est à l'humain de le fermer.** J'ai reproduit le
`7,33 %` de l'auditeur avec mon propre compteur, sur les 200 premières donnes de la campagne B puis
sur la campagne entière. Deux conclusions séparées :

- **Le dénominateur est le même chez les deux implémentations, et ce résultat est solide.** La
  question admettait deux lectures — parmi les nœuds à Assassin en attente, ou parmi tous les nœuds
  de ciblage. La seconde mesure **0,72 %**, IC 99 % [0,58 ; 0,87], ce qui **exclut** 7,33 % d'un
  facteur **8,4**. Les deux implémentations comptent donc sur les nœuds à Assassin en attente. Ce
  résultat tenait déjà à 246 nœuds et ne dépend pas de la valeur.
- **Les valeurs, elles, ne se recouvrent pas.** Ma mesure sur la campagne entière donne **4,23 %**
  (172/4063), IC 99 % **[3,46 ; 5,11]**, et **7,33 % en sort**. Ce n'est ni un défaut de l'audit ni
  un défaut de mon compteur : c'est un désaccord entre deux implémentations qui comptent la même
  chose sur des échantillons différents. **L'échantillon de l'auditeur ne m'est pas connu** — sans
  son numérateur et son dénominateur la question n'est pas tranchable, ce qui est le contrôle
  numéro 2 de son propre audit appliqué à son chiffre. Aucune moyenne, aucune préférence, aucune
  explication inventée.

**La réserve 2 est fermée par la population à trois greedys.** `B1-collectif` mesuré sur trois
greedys vaut **71,78 %** (21538/30006) contre **70,07 %** avec un greedy et deux hasards, pour un
hasard à **67,18 %** : l'écart à établir passe de **+2,89** à **+4,60** points, et le nombre de
parties nécessaires de **5 868** à **745**. La ligne de base collective que la phase 3 doit
utiliser est celle-là, et non celle de la composition de référence.

**Ce que mon propre auto-audit avait trouvé (étape 4), et qui reste au dossier :**

1. **B1 comparait un agrégat de 3 sièges à un agent sur 1 siège.** B1 est le seul des sept dont
   le dénominateur naturel est la partie, donc agréger les sièges par un « au moins un » gonfle
   le numérateur **sans toucher au dénominateur**. **Ma première lecture disait l'inverse de la
   vérité** — « le greedy montre le motif moins que le hasard ». Dénominateur primaire devenu le
   couple `(partie, siège mesuré)` ; valeurs justes **47,93 %** contre **36,11 %**.
2. **`B1-collectif` n'agrégeait que les sièges mesurés**, donc il retombait au chiffre près sur
   `B1-motif` dès qu'on mesurait un agent seul — muet exactement dans le cas où il sert, un don
   du greedy retourné par un adversaire. Corrigé à **70,07 %**, inclusion `collectif ≥ motif`
   assertée sur les deux compositions de sièges.
3. **Cause racine commune de 1 et 2 : aucun de mes 30 cas de compteurs n'exerçait le nombre de
   sièges mesurés.** Ce n'est pas deux erreurs isolées, c'est un trou de stratégie de test.
4. **À taux nul, ma formule normale rendait « écart détectable 0,00 %, 0 partie »** — soit
   « tout est détectable », le contraire de la vérité, puisque la variance estimée d'un zéro est
   nulle. `ecart_de_taux_detectable` rend désormais `None`, et un zéro se publie avec sa borne
   exacte de Clopper-Pearson.

Deux défauts relevés par l'humain, non par moi :

5. **La taille d'échantillon dépendait d'une formule non nommée** — écart de 19 parties entre
   deux formes normales également défendables. Arbitré par le calcul binomial exact, **plus
   grand que les deux**. Parade structurelle : une enum `Variance`, qui rend impossible de
   calculer une taille de proportion sans **nommer** l'écart-type retenu.
6. **`B7-gaspillage` constate au lieu de tester** — diagnostic confirmé, et pire que l'estimation
   qui l'a déclenché : **320 163** parties, pas ~100 000.

Deux surinterprétations retirées de mon propre rapport :

7. Le verdict sur `ρ` devient « **infirmée pour les deux politiques mesurées, non appuyée en
   général** » : je n'ai mesuré ni agents entraînés ni `complet-3j`.
8. Les nœuds tout-dos ne sont qu'un mécanisme **minoritaire** de l'égalité de B4 — **3,89 %**,
   contre **61,22 %** de départage. Mon §5.4.1 les désignait comme **le** mécanisme.

Un chiffre d'auteur corrigé, et il change une conclusion :

9. **Mon premier tableau de pouvoir discriminant était calculé sur les pourcentages arrondis du
   rapport, non sur les comptes bruts** : il sous-estimait le besoin de `B7-gaspillage` de
   **32 %** (218 653 au lieu de 320 163). Seul le tableau du rapport, calculé sur les comptes,
   est autoritatif.

Une direction annoncée d'avance et **infirmée** par la mesure :

10. La pré-inscription annonçait `B2-banquet` « beaucoup plus grande » que `B2-contestée`. Elle
    est **beaucoup plus petite** : **34,89 %** contre **68,32 %**. Le raisonnement était faux, et
    d'une façon qui se voit d'avance : une pose place **trois** cartes, une seule au banquet, donc
    la part des Assassins au banquet est bornée par la mécanique du coup, autour d'un tiers.
    C'est le seul des **dix sens falsifiables** que la mesure contredise. Les douze énoncés
    annoncés comptent en effet deux **contrôles** nuls par construction — voir le §0 de
    `mesure/phase2_definitions_et_concurrentes.md`, défaut mineur 3 corrigé le 20/08/2026.

**Décision.** **PROPOSÉE : go**, sous **trois** réserves — la deuxième est fermée —, **et après
re-vérification par l'audit des quatre corrections et de la population à trois greedys**. La décision n'est pas la mienne et
n'appartient pas au constructeur ; le verdict en cours est REJETÉ jusqu'à cette re-vérification.

- Le terrain est mesuré : la phase 3 dispose d'un adversaire de référence chiffré, d'un
  dimensionnement, et de dix-huit compteurs dont **on sait lesquels peuvent tester quoi**.
- **Réserve 1** — `_poids_de_bascule_disponible` est une **proposition**, jamais démontrée
  minimale, donc `B7-gaspillage` est un **plancher** et non le gaspillage.
- **Réserve 2 — FERMÉE.** `B1-collectif` chez le greedy de référence mélangeait sa propre bascule
  et celles de deux adversaires **aléatoires**. La population à trois greedys, autorisée après
  l'audit, donne la ligne de base collective utilisable : **71,78 %** contre **67,18 %** pour le
  hasard, **+4,60 pt**, **745** parties pour l'établir. Périmètre publié : `B1-collectif`, sa
  variante, et les lignes `-par-partie` — six lignes, et pas une de plus.
- **Réserve 3** — `FENETRE_STABILITE = 200` est une proposition, appuyée empiriquement sur deux
  valeurs de `p₁` seulement.
- **Réserve 4 — la durée machine ne dérive pas, elle VARIE d'un facteur 2,6, et une quatrième
  passe l'établit.** J'avais écrit « ralentissement uniforme, donc cause machine ». La direction
  était fausse et la conclusion trop faible. Sur du **code inchangé et les mêmes seeds**, quatre
  passes donnent :

  | Campagne | passe 1 | passe 2 | passe 3 | passe 4 | passe 5 | max / min |
  |---|---:|---:|---:|---:|---:|---:|
  | A | 210,9 s | **244,8 s** | 94,2 s | 108,8 s | **83,5 s** | **2,93** |
  | A contrôle | 216,4 s | **247,3 s** | 91,7 s | 94,2 s | **82,3 s** | **3,00** |
  | B | 261,0 s | **301,5 s** | 112,7 s | 112,0 s | **101,1 s** | **2,98** |
  | B, 2 greedys | 307,3 s | **351,1 s** | 134,1 s | 132,0 s | **118,1 s** | **2,97** |
  | B, départage déterministe | 261,6 s | **297,5 s** | 113,1 s | 111,5 s | **100,8 s** | **2,95** |

  Non monotone, et un rapport **max/min de 2,93 à 3,00 sur les cinq campagnes**. Les passes 3, 4 et
  5 portent un code **identique sur la phase de jeu**, et les changements d'une passe à la suivante
  s'étalent de **−23,3 %** (A, 108,8 → 83,5) à **+15,5 %** (A, 94,2 → 108,8) sur les cinq
  campagnes. Le total est passé de 1 013 s à 1 961 s puis à **808 s**.

  **Le max/min est la quantité qui porte cette réserve**, parce qu'il ne dépend d'aucun choix de
  paire de passes. Une version précédente de cette ligne annonçait « −26 % à +16 % » : le −26 %
  venait de la campagne `B, 3 greedys` (180,0 → 133,6 s, soit −25,8 %), qui **n'existe que dans les
  passes 3 à 5** puisqu'elle a été ajoutée après l'audit, et que la phrase excluait donc en parlant
  des cinq campagnes ; le +16 % était +15,5 % arrondi vers le haut. Deux chiffres exacts sur une
  population qui n'était pas celle que la phrase nommait — la même faute que les six budgets, en
  plus petit. Consigné ici parce que c'est la troisième forme sous laquelle elle sort.

  **Ce que ça établit, et c'est plus que ce que je disais** : le temps mural mesuré sur cette
  machine n'est **pas un instrument**. Il ne mesure pas le coût du code, il mesure l'état de la
  machine au moment où on l'exécute. Les deux suspects restent le bridage thermique et la
  synchronisation OneDrive du dépôt, mais l'important n'est plus de les départager : c'est que
  **la phase 3 ne peut pas planifier un budget de calcul sur un chronométrage unique**. Toute durée
  citée doit l'être sur au moins trois passes, avec son étendue.

  Et je corrige à nouveau ma formulation : le total **n'est pas** indécomposable — le tableau des
  durées décompose la phase de jeu. Ce qui reste non décomposé est le hors-campagne, où se mélangent
  bootstrap, compteurs et rédaction. C'est là que le checkpoint annoncé dans ma pré-inscription
  manque, et nulle part ailleurs.

**Impact plan.** Cinq trous du protocole, **sept** enseignements de méthode, une question ouverte
nommée pour la phase 3, les motifs de mutation à inscrire, et un point d'API.

- **`05_protocole_experimental.md` — trois termes non définis.** « retournement »,
  « distribution non dégénérée » et « situations où refuser de tuer est possible ». Le dernier est
  de lecture littérale **vide** : refuser est toujours légal (§4.1, arbitrage R2), donc sa
  fréquence vaut 100 % par construction. Le dénominateur retenu est les nœuds de ciblage offrant
  **au moins une cible**, et il doit être écrit dans le protocole.
- **`05_protocole_experimental.md` — « 20 cartes ou 40 » n'est pas un arbitrage.** La
  configuration à 20 cartes est **refusée à la construction** par le moteur. Le protocole propose
  un choix qui n'existe pas.
- **`05_protocole_experimental.md` — « l'appariement divise par cinq à dix ».** C'est le seul des
  cinq trous qui soit un **chiffre**, il implique `ρ ∈ [0,8 ; 0,9]`, et la mesure donne
  **+0,0066**. À retirer ou à rattacher à une mesure.
- **Le seuil de 38,00 % de M1 constate au lieu de tester** — à **9,90 erreurs-type** de
  l'attendu. Avec `B7-gaspillage` et les quatre critères de non-dégénérescence de la phase 1,
  **c'est la troisième fois dans ce projet**. Tout critère futur publie l'**écart détectable** à
  son budget, avant d'être adopté.
- **Trois enseignements de méthode.** (a) La puissance binomiale exacte est **non monotone** en
  `n`, en dents de scie : un seuil se publie sur son premier `n` **stable** — **1 531** et
  **11 629** — et le premier franchissement — **1 501** et **11 539** — se rend à côté. (b) Une
  taille d'échantillon de proportion **ne se calcule pas sans nommer l'écart-type retenu** ;
  l'enum `Variance` rend l'omission impossible. (c) Tout compteur de comportement se teste sur
  **au moins deux compositions de sièges**, avec l'inclusion ou la monotonie attendue **assertée**
  — c'est ce qui manquait aux défauts 1, 2 et 3. **(d) Un critère de périmètre doit se décider sur
  le TEXTE d'une définition, sans mesurer.** Un critère de degré — « ici les adversaires produisent
  le numérateur, là ils ne font que façonner le plateau » — dérive toujours vers l'extérieur au bord
  d'un périmètre : le lecteur suivant ajoute un élément de plus avec une raison aussi bonne, et rien
  ne l'arrête. Le critère retenu pour la troisième population est textuel — *la définition nomme-t-
  elle un autre joueur ?* — et il s'arrête où le texte s'arrête. **(f) Toute quantité qui traduit un
  résultat en budget doit être produite par UNE fonction, et le nombre de parties doit lui être
  passé depuis le plan, jamais déduit d'un compteur.** Trois tables déduisaient leur dénominateur
  par partie sur place ; l'une s'est trompée d'un facteur trois. Déduire le nombre de parties de
  `B1-motif` marchait **par coïncidence** — son grain est le couple et la composition de référence
  ne mesure qu'un siège — et cessait de marcher dès qu'une population mesurait trois sièges. Une
  coïncidence qui tient est une bombe à retardement, pas une simplification. **(g) Reproduire un nombre ne le
  valide pas — il faut reproduire son UNITÉ d'abord, et le nombre ensuite.** Deux implémentations
  qui partagent la même hypothèse fausse concordent parfaitement. Le `2 234` de `B1-collectif` a été
  reproduit à deux parties près par une seconde implémentation, et il était **trois fois trop
  grand** : le vérificateur avait reçu le dénominateur par partie du générateur au lieu de le
  dériver du grain. **Le contrôle A7 — « les chiffres se reconstruisent » — ne remplace pas le
  contrôle 1 — « le calcul est celui que la phrase décrit ».** Vrai entre constructeur et auditeur,
  et vrai de la phase 3 qui citera ces chiffres sans les recalculer. **(e) Un libellé de grain doit
  porter ce qui rend deux grains différents.** Deux colonnes portaient exactement le même libellé
  en agrégeant l'une un siège et l'autre trois : une parade comparant les libellés n'aurait rien
  levé, et la mention « non comparable » serait restée de la prose. Le libellé porte désormais le
  **compte** des sièges, et c'est lui qui rend la levée possible.
- **Point d'API du moteur.** `vue_du_joueur` est devenue publique dans `courtisans/infoset.py`
  (`a198df8`) : c'est l'API par laquelle un agent obtient sa vue sans jamais toucher un `State`.
  Périmètre **renommage seul**, sur autorisation explicite ; **19 mutations sur 19** toujours
  détectées après.
- **QUESTION OUVERTE POUR LA PHASE 3 — `B4-tout-dos` et `B5-renfort` bougeront pour une raison
  qui n'est pas l'habileté de l'agent.** Ces deux compteurs ne sont **pas** dans le périmètre de la
  troisième population, et le critère de périmètre est clair : leur définition ne nomme aucun autre
  joueur. Mais leurs deux taux dépendent de ce que **font les adversaires**, et pas au sens où tout
  le plateau en dépend :

  - `B4-tout-dos` compte les nœuds de ciblage dont **toutes** les cibles sont des dos. Un dos est
    un Espion posé par quelqu'un d'autre : la **population de dos** sur le plateau est produite par
    les adversaires.
  - `B5-renfort` exige au dénominateur « au moins un dos au banquet » **et** une famille à
    `|d| = 1` : sa population de nœuds dépend à la fois des dos adverses et de la **distribution
    des familles favorables**, elle-même façonnée par leurs poses.

  **Conséquence à écrire avant que quelqu'un s'y trompe** : quand la phase 3 mesurera ces deux
  compteurs sur **trois agents entraînés**, leurs taux bougeront par rapport aux **3,89 %** et
  **20,41 %** publiés ici, pour une raison qui n'est **pas** l'habileté de son agent. Un lecteur
  qui comparerait son agent à ces deux chiffres sans le savoir attribuerait à son agent un écart
  **produit par ses adversaires**. Ce que la phase 3 doit faire : soit mesurer ces deux compteurs
  sur une population de même composition que la sienne, soit ne pas les comparer du tout.

  **Ce que j'avais proposé, et pourquoi c'était refusé.** Je voulais les ajouter au périmètre au
  motif que les adversaires y produisent le numérateur, là où ailleurs ils ne façonnent que le
  plateau. C'est un critère de **degré**, et il a été rejeté pour cette raison — voir l'enseignement
  de méthode (d) ci-dessous.

- **`outillage/mutation.py` ne cible que `courtisans/`** — ses dix-neuf motifs portent sur
  `infoset`, `engine`, `cards`, `rules`, `openspiel_adapter` et `config`. Ni `mesure/` ni `agents/`
  ne portent de mutation, alors que `agents/greedy.py` devient la ligne de base de toutes les
  phases suivantes. Relevé par l'humain, porté au prompt de la phase 3, **rien à faire ici**.
  Quatre motifs évidents à inscrire, chacun avec le test qui doit l'attraper :

  | Motif | Test qui doit tomber |
  |---|---|
  | `max` → `min` dans `_argmax` de `greedy` | tous les cas de position où le coup est déterminé |
  | départage `alea.choice` → premier indice | `M3(G-naïf)` cesserait de différer de M3 ; à couvrir |
  | `_meilleur_apres_assassins` → `evaluer` seul, sans résolution des Assassins | les cas G-combiné |
  | prise en compte des Assassins **en attente** au ciblage | `test_le_ciblage_ignore_les_assassins_en_attente_et_c_est_caracterise` |

  Le quatrième est le seul qui soit déjà tenu : il l'est **par construction** depuis la correction
  du défaut A3, et c'était le but — un « correctif » du comportement myope casse un test nommé.

- **Deux réserves de la phase 1 restent ouvertes**, annoncées hors phase 2 et non traitées ici.
- **Rien de tout ceci ne se transporte à `complet-3j`** — 6 familles, 3 exemplaires, 10 tours —
  ni par un facteur ni par une extrapolation. Et **la phase 2 ne valide pas le moteur** : elle le
  suppose conforme, c'est la phase 0 qui l'établit.
