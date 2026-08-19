# Phase 2 — proposition d'entrée de journal

**Ceci est une PROPOSITION.** Je ne modifie pas `documentations/`. L'entrée ci-dessous est au
format du §4 de [08_modele_compte_rendu.md](../documentations/08_modele_compte_rendu.md) et
attend deux choses avant d'être reportée dans
[06_journal_decisions.md](../documentations/06_journal_decisions.md) : le verdict de l'audit
croisé, qui seul clôt la phase, et la décision de l'humain, qui n'est pas la mienne.

Le champ **Audit** est donc rempli de mon **auto-audit de constructeur** (étape 4) et reste
ouvert : ce que l'auditeur trouvera que je n'ai pas vu s'écrit là, et pas ailleurs.

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
calcul **binomial exact**, contrôlé à l'unité contre `scipy.stats`. 878 tests, `ruff` propre.

- reproduire : `UV_LINK_MODE=copy uv run python -m mesure.phase2`
- rejouer les tests : `UV_LINK_MODE=copy uv run pytest -q`

**Résultat.** Détail décomposé dans `mesure/resultats/phase2.md` ; les sept définitions et leurs
concurrentes chiffrées dans `mesure/phase2_definitions_et_concurrentes.md`. **Douze des treize
concurrentes annoncées d'avance sont chiffrées ; onze des douze sens annoncés tiennent.**

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

**Audit.** **VERDICT EN ATTENTE** — l'audit croisé n'a pas eu lieu ; ce qui suit est l'auto-audit
du constructeur (étape 4), et ce champ reste ouvert pour ce que l'auditeur trouvera que je n'ai
pas vu.

Quatre défauts trouvés par moi, tous corrigés :

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
    C'est le seul des douze sens annoncés que la mesure contredise.

**Décision.** **PROPOSÉE : go**, sous quatre réserves. La décision n'est pas la mienne et
n'appartient pas au constructeur.

- Le terrain est mesuré : la phase 3 dispose d'un adversaire de référence chiffré, d'un
  dimensionnement, et de dix-huit compteurs dont **on sait lesquels peuvent tester quoi**.
- **Réserve 1** — `_poids_de_bascule_disponible` est une **proposition**, jamais démontrée
  minimale, donc `B7-gaspillage` est un **plancher** et non le gaspillage.
- **Réserve 2** — `B1-collectif` chez le greedy mélange sa propre bascule et celles de deux
  adversaires **aléatoires** : il n'est **pas comparable** à une phase 3 aux adversaires
  entraînés.
- **Réserve 3** — `FENETRE_STABILITE = 200` est une proposition, appuyée empiriquement sur deux
  valeurs de `p₁` seulement.
- **Réserve 4 — la durée machine dérive, et une troisième passe montre où.** Sur les **mêmes
  seeds**, trois passes successives ont donné **1 013 s**, **1 692 s**, puis **1 961 s** au total.
  La troisième ajoute deux compteurs, donc son total n'est pas comparable — mais les **durées par
  campagne** portent du code inchangé, et elles montent de **+13,7 % à +16,1 %**,
  **uniformément sur les cinq campagnes** : 210,9 → 244,8 ; 216,4 → 247,3 ; 261,0 → 301,5 ;
  307,3 → 351,1 ; 261,6 → 297,5. **Un ralentissement multiplicatif uniforme sur cinq campagnes
  indépendantes est la signature d'une cause machine, pas d'un chemin de code.** Les deux suspects
  à écarter avant la phase 3 restent le bridage thermique et la synchronisation OneDrive du dépôt.
  Et je corrige ma propre formulation : le total **n'est pas** indécomposable — le tableau des
  durées décompose la phase de jeu. Ce qui reste non décomposé est le hors-campagne, **434,8 s**
  puis **519,0 s**, où se mélangent bootstrap, compteurs et rédaction. C'est là que le checkpoint
  annoncé dans ma pré-inscription manque, et nulle part ailleurs.

**Impact plan.** Cinq trous du protocole, trois enseignements de méthode, un point d'API.

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
  — c'est ce qui manquait aux défauts 1, 2 et 3.
- **Point d'API du moteur.** `vue_du_joueur` est devenue publique dans `courtisans/infoset.py`
  (`a198df8`) : c'est l'API par laquelle un agent obtient sa vue sans jamais toucher un `State`.
  Périmètre **renommage seul**, sur autorisation explicite ; **19 mutations sur 19** toujours
  détectées après.
- **Deux réserves de la phase 1 restent ouvertes**, annoncées hors phase 2 et non traitées ici.
- **Rien de tout ceci ne se transporte à `complet-3j`** — 6 familles, 3 exemplaires, 10 tours —
  ni par un facteur ni par une extrapolation. Et **la phase 2 ne valide pas le moteur** : elle le
  suppose conforme, c'est la phase 0 qui l'établit.
