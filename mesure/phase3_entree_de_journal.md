# Phase 3 — proposition d'entrée de journal

*Au format du §4 de [08_modele_compte_rendu.md](../documentations/08_modele_compte_rendu.md) et
du §0.1 de [05_protocole_experimental.md](../documentations/05_protocole_experimental.md).
Proposée par le constructeur ; la décision n'est pas la sienne.*

*Réécrite au tour 2, après un audit qui a rendu **REJETÉ** — deux bloquants, quatre majeurs,
huit mineurs, 97 contrôles hostiles. Ce qui a changé n'est pas un détail de rédaction : **une
des deux phrases du résultat était fausse, et c'est celle qui portait la décision.***

---

## [2026-08-22] Phase 3 — Le premier agent entraîné

**Hypothèse.** *Écrite et commitée avant tout entraînement,
`mesure/phase3_hypothese_et_instrument.md`.* Un agent entraîné en self-play avec un pool
d'adversaires figés, sur `entrainement-3j`, obtient contre **deux greedys**, sièges permutés, un
**gain moyen strictement positif, borne basse de son IC 99 % bootstrap par donne comprise**.

**Instrument.** PPO à masque d'actions, réseau unique partagé par les trois sièges, tête de
valeur, `γ = 1`, `λ = 1`. Ni le greedy ni l'aléatoire n'entrent dans le pool d'entraînement.
Juge : gain moyen, niveau nul **exactement 0,0000**. Budget **dimensionné sur la composition**,
jamais emprunté : `σ = 0,6494` et `ρ = −0,1400` mesurés sur « un greedy contre deux greedys »,
2 000 donnes, seeds 20000–21999 — d'où **2 000 donnes × 3 sièges = 6 000 parties**, écart
détectable **+0,0243**. Bootstrap **par donne**, 10 000 rééchantillons. Garde-fou : **600 donnes
× 3 = 1 800 parties** par checkpoint, seeds 40000–40599, **les mêmes à chaque checkpoint**,
écart détectable pré-inscrit **2,75 points**. Entraînement : plafond 2 h, checkpoint tous les
quarts d'heure, seeds `100000+`. Rapport régénérable par
`uv run python -m mesure.phase3_mesure`.

**Résultat. L'agent est battu par le greedy, et il a appris pendant son run. Les deux sont
établis. Ce qui n'est PAS établi, et qu'un premier tour affirmait, c'est qu'il apprenait
encore à la fin.**

- **Le juge — H est INFIRMÉE, et de façon établie, pas par manque de puissance.** Gain moyen
  **−0,1643**, IC 99 % **[−0,1824 ; −0,1462]** sur 6 000 parties : la borne **haute** est
  négative. Part de victoire fractionnée **22,38 %** contre **33,3333 %** au neutre. L'effet
  vaut **sept fois** l'écart détectable remesuré (+0,0237). Ce n'est pas « non conclu au
  budget » : c'est « battu », au sens de la table go/no-go. **Trois implémentations
  indépendantes concordent, et chacune sur son échantillon nommé** — la mienne **−0,1643** sur
  2 000 donnes × 3, seeds 60000–61999 ; celle du pilote **−0,1719** sur **400 donnes** × 3,
  même départ ; celle de l'auditeur **−0,1734** sur 2 000 donnes × 3, mêmes seeds. Les trois
  IC se contiennent mutuellement, les trois bornes hautes sont négatives.
- **L'instrument est calibré sur les seeds exactes du verdict** : le greedy mis à la place de
  l'agent, seeds 60000–61999, rend **+0,0062**, IC 99 % **[−0,0124 ; +0,0255]**, qui contient 0.
  L'auditeur retrouve **+0,0152**, IC **[−0,0036 ; +0,0338]**.
- **L'agent apprend — entre son premier et son dernier checkpoint, et c'est là ce qui est
  établi.** Écart **apparié** de part fractionnée contre deux aléatoires, mêmes 600 donnes des
  deux côtés : *MESURÉ*, **+12,80 points, IC [+8,33 ; +17,40]**, qui exclut 0. L'auditeur,
  avec son propre aléa de tirage, mesure **+14,22 points, IC [+10,99 ; +17,49]**. **Les deux
  intervalles ne sont pas au même risque et il faut le dire** : le mien est corrigé de
  Bonferroni pour 8 regards — `z = 3,2272` —, le sien est un 99 % simple. C'est ce qui explique
  qu'il soit plus étroit, et non une différence de population : ce sont les mêmes 600 donnes.
- **« Croissance monotone sans exception » et « encore en progression au dernier » sont
  RETIRÉES.** Elles étaient dans le rapport du tour 1 et dans la décision. **Aucun des sept
  pas consécutifs n'est établi** : ils valent +2,19 / +2,25 / +1,45 / +1,83 / +2,50 / +1,71 /
  **+0,86** point, et **les sept intervalles appariés contiennent tous 0**. *La barre qui les
  juge est la demi-largeur de leur propre IC apparié — de **3,56 à 4,06 points**, Bonferroni
  pour 8 regards —, et non les **2,75** de la pré-inscription, qui sont un détectable **iid sur
  un NIVEAU** et non sur un écart apparié. Les deux disent la même chose ici, et le tour 1
  citait le second comme s'il était le premier ; c'est la faute du projet, et elle est restée
  jusqu'à la relecture finale du tour 2.* La remesure de l'auditeur, **mêmes
  donnes** et autre aléa de tirage, porte **deux inversions** et un dernier pas **négatif**,
  −0,53 pt, IC [−3,19 ; +2,23]. **La monotonie était une propriété de mon tirage, pas de mon
  agent.**
- **Le critère terminal du garde-fou n'est pas franchi** — 70,13 % contre 86,52 % — et la
  prémisse que le protocole lui prêtait (« l'agent n'apprend pas ») est bien fausse ici :
  l'écart des extrêmes la contredit. Mais **ce qui ne suit pas, et que le tour 1 en tirait**,
  c'est « il n'a pas fini d'apprendre », donc « rallonger ». Cette conclusion demandait une
  pente à la fin, et aucun écart mesuré ne la montre.
- **`σ` a bougé de −12,1 %** — 0,5710 contre 0,6494. **Mais la règle des 10 % que je m'étais
  donnée portait sur la DEMI-LARGEUR, pas sur `σ`**, et elle n'est **pas** franchie : 0,0181
  mesurée contre 0,0183 pré-inscrite, soit **−1,1 %**. Le tour 1 déclarait franchie une règle
  portant sur une autre grandeur. Et le constat vaut mieux que la correction : **la règle était
  aveugle au mouvement qu'elle prétendait détecter**, `σ` ayant chuté pendant que l'effet de
  plan montait de 0,7200 à 0,8870 — les deux se compensent dans le produit qu'elle surveillait.
- **`ρ` reste négatif** — −0,0565 contre −0,1400 sous l'hypothèse nulle. La permutation des
  sièges **réduit** la variance dans les deux cas, effet de plan 0,8817 par bootstrap et 0,8870
  par analyse de variance, deux routes indépendantes.
- **Le critique n'apprend pas, et ce n'est pas une propriété du jeu.** `perte_valeur` vaut
  0,3923 au premier checkpoint et 0,3908 au huitième, sans amélioration entre les deux.
  *MESURÉ par l'audit*, `audit/phase3/critique.py` **sur la branche `audit-phase-3`** — ce
  fichier n'est pas sur celle-ci, et je n'ai pas refait cette mesure moi-même : variance des
  retours **0,4190**, MSE réelle
  de `final.pt` **0,3809**, soit **`R² = +0,09`** ; plancher irréductible `E[Var(R | état)]`
  **0,1815**, donc un `R²` qui **plafonne à 0,57**. *Et ce plafond est une **borne**, pas une
  cible* : il est mesuré en rejouant le **même état complet**, donc pour un critique qui verrait
  plus qu'un info-set. Un critique sur info-set ne peut pas faire mieux, il peut faire moins
  bien. Décisif : ce plancher **s'effondre** avec la profondeur
  — 0,32 à la première décision, **0,0075** à l'avant-dernière — alors que la MSE du critique
  reste **plate**, 0,36 à 0,30. À l'avant-dernière décision la partie est presque écrite et le
  critique y fait **quarante fois** l'erreur irréductible. **La lecture « la valeur est
  imprédictible dans ce jeu » est réfutée ; il reste « le critique est mal spécifié ou
  sous-entraîné ».**
- **Comportements, comparés à une ligne de base RÉGÉNÉRÉE** — trois greedys à **un seul siège
  compté**, même composition, même décalage `6000000`, mêmes seeds **que la phase 2** : les
  donnes 0–1999, quand l'agent joue les donnes 60000–61999. **Les deux échantillons ne partagent
  aucune donne, et la comparaison n'est donc pas appariée** ; l'écart détectable est calculé sur
  les **deux** effectifs. **`B1-motif` 42,48 % contre 45,83 %** : l'agent manifeste le motif de
  retournement **moins** que le greedy. **`B4-brut` 31,93 % contre 15,93 %** : il refuse de tuer
  deux fois plus souvent. **`B4-contre-nature` 35,87 % contre 0,00 %**, et cet écart n'établit
  ni planification ni erreur.

**Audit. VERDICT du tour 1 : REJETÉ** — deux bloquants, quatre majeurs, huit mineurs,
**97 contrôles hostiles** écrits par l'auditeur, tous verts.

**Ce que l'audit a CONFIRMÉ, par du code indépendant, et qui ne bouge pas :** le verdict
« battu » par une troisième implémentation ; la calibration du niveau nul ; **l'aveuglement
complet du réseau** — 88 contrôles : tenseur, chaîne et logits identiques **bit à bit** sous
permutation de la pioche, des mains et de l'identité des dos, **zéro appel privilégié compté**
pendant la décision, et un brouilleur dont il prouve qu'il attraperait un tenseur fuitant **une
seule** composante ; **la disjonction des populations au niveau des DONNES et pas des seuls
seeds** — 0 collision de pioche entre les 14 600 donnes de mesure et les **1 486 336** donnes
d'entraînement balayées en entier ; les gardes de grain ; 20/20 mutations ; 1 132 tests verts
dont **aucun sauté**. *La suite en compte **1 161** au tour 2, toujours 0 rouge et 0 sauté :
29 cas de plus, tous écrits pour faire tomber une correction.*

**Ce que l'auto-audit avait trouvé avant la mesure, et qui tient** : les compositions du pool
tombaient **dans la plage d'entraînement** — départ à 30 000 avec des décalages de +100 000 et
+200 000, quand l'entraînement occupe 100 000 à ~1 586 000. L'agent aurait été jugé sur des
donnes qu'il avait vues. Les six familles de plages sont désormais toutes sous 100 000, et
**l'audit l'a vérifié au niveau des donnes et non des seuls seeds** : 0 collision de pioche.
Cinq autres défauts avaient été trouvés par mes propres tests, tous avant d'avoir un chiffre :
un repli silencieux vers `actions_legales[0]` dans la boucle d'entraînement ; un aléa partagé en
lock-step qui rendait une partie irreproductible à l'unité ; une garde de dénominateur qui
**doublait** celle de `phase2.observations_par_partie` ; une comparaison de demi-largeur d'IC
entre deux budgets différents ; et une règle de garde-fou qui tuait un agent qui apprend.

**Ce que l'audit a TROUVÉ, et qui est corrigé au tour 2 :**

1. **bloquant** — « il progressait encore au dernier » n'était pas établi, et une remesure lui
   donne le signe opposé. *Corrigé : le rapport publie désormais l'IC de ses **écarts**
   appariés, `mesure/phase3_courbe.py`, et la phrase est retirée du rapport comme de la
   décision.*
2. **bloquant** — le garde-fou réécrit le 21/08 aurait tué ce run au checkpoint 3, à
   45 minutes sur 120 : les huit intervalles se recouvrent 7 fois sur 7. *Défaut du pilote,
   corrigé au protocole ; le code suit — portée **3**, déclencheur sur l'**écart apparié**, et
   `portee_minimale` calcule la borne que les quatre versions ignoraient.*
3. **majeur** — deux des dix contrôles ne pouvaient pas échouer, et le compte rendu affirmait
   que **chacun** était vérifié capable d'échouer. *Corrigé : `_epreuve` et `_releve` sont
   distincts, un test **lit l'AST** pour refuser un booléen littéral, et les quatre contrôles
   non cassés le sont. **Huit éprouvés, deux relevés.***
4. **majeur** — R4 ne regardait que l'agent et imprimait « aucune valeur extrême » pendant que
   le rapport publiait deux zéros absolus. *Corrigé : il scanne les deux côtés et nomme lequel ;
   le rapport cite les quatre cas construits à la main qui confrontent ces zéros.*
5. **majeur** — deux populations publiées sous le même nom. *Corrigé : chaque nom porte son
   agent, ses donnes et ses seeds ; R2 reçoit aussi les compositions publiées hors du pool ; et
   un test refuse deux intitulés identiques dans tout `mesure/` et `agents/`.*
6. **majeur** — la règle « hors budget », pré-inscrite avec ses huit noms, était une branche
   inatteignable. *Corrigé : la branche morte est retirée, le rapport dit pourquoi la liste
   pré-inscrite ne se transporte pas — elle est calculée sur l'écart greedy-contre-hasard de la
   phase 2 —, et chaque ligne non séparable publie le nombre de parties qu'il faudrait.*
7. **mineur** — la marge de 10 % portait sur la demi-largeur et n'est pas franchie ; **le
   pilote avait propagé l'erreur**. *Corrigé, avec la raison pour laquelle la règle était
   aveugle.*
8. **mineur** — l'écart détectable supposait des dénominateurs égaux ; `B4-strict` passait de
   2,37 à 3,96 pt. *Corrigé : formule à deux échantillons ; **aucune des 34 lignes ne change de
   statut**, et un test le fige.*
9. **mineur** — le tableau central ne se rendait pas comme un tableau. *Corrigé : le blockquote
   passe avant l'en-tête.*
10. **mineur** — « les quatre plages » suivi d'une liste de six. *Corrigé : **six familles,
    treize plages**, et tous les noms écrits.*
11. **mineur** — « mêmes seeds » désignait la phase 2, pas ma campagne. *Écrit.*
12. **mineur** — `verifier_inclusion_b1` comparait des numérateurs sans garde de grain.
    *Corrigé : elle lève.*
13. **mineur** — attribution de sept points au seul §10. *Corrigé, et le point manquant rendu.*
14. **mineur** — les 20 mutations ne couvrent aucun fichier de la phase 3. *Documenté au §8 du
    rapport et **non corrigé** : étendre leur périmètre est un arbitrage remonté au pilote.*

**Trouvé au tour 2, en écrivant le cas qui casse un contrôle** : `controle_bootstrap_par_donne`
divisait par un effet de plan qui peut valoir exactement 0 — `ρ = −1/(m−1)` —, donc levait un
`ZeroDivisionError` au milieu d'un audit. Corrigé.

**Décision. PROPOSÉE : pivot de diagnostic. Le levier n'est pas le budget.**

L'hypothèse est infirmée et l'agent apprend : les deux sont acquis. **Le tour 1 en tirait « ce
que le résultat écarte est le budget, pas la méthode » et désignait le levier 1. Les deux jambes
de cette phrase sont tombées** : la courbe ne montre pas qu'elle montait encore, et le critique
est mesuré défaillant. Rallonger un run dont l'avantage de PPO est dominé par le bruit du retour
rallonge le bruit.

*DÉDUIT, et non mesuré* : le levier que la mesure désigne est la **tête de valeur** — et c'est celui que le §7.1 de ma
propre pré-inscription avait écrit d'avance comme réponse prévue si le garde-fou tombait : une
tête auxiliaire de régression sur l'écart de score final, entraînée par une perte séparée,
**jamais dans le retour ni dans l'avantage**. Il n'est pas implémenté ici : c'est la phase 4, et
une variable à la fois.

**Impact plan.**

1. **Le garde-fou a été corrigé une quatrième fois**, et le code le suit : portée 3, déclencheur
   sur l'écart apparié, `portee_minimale` en parade. La règle générale qui manquait aux quatre
   versions est désormais au protocole : **un garde-fou ne peut chercher qu'un progrès plus
   grand que l'écart détectable à son propre budget.** Sur ce run, les cinq écarts de portée
   trois valent +5,89, +5,54, +5,79, +6,05 et +5,07 points : aucun ne déclenche, et un test le
   vérifie sur le journal réel.
2. **Toute courbe d'apprentissage se publie avec l'IC de ses ÉCARTS**, pas seulement de ses
   niveaux — règle du §0.2 depuis le 22/08. Un écart apparié ne coûte pas une partie de plus :
   la matière était déjà jouée, il ne manquait que de garder la série par donne.
3. **Un contrôle qui ne peut pas échouer ne se compte pas parmi les concluants** — règle du
   §0.2. Le rapport publie désormais « huit éprouvés, deux relevés ».
4. **La phase 4 commence par la tête de valeur, pas par le budget.** Un levier écarté est un
   résultat : le budget n'est pas écarté, il est **non désigné** par cette mesure, ce qui n'est
   pas la même chose et ne se rapporte pas comme tel.
5. **La ligne de base « trois greedys à un siège compté » existe et est régénérable** ; toute
   phase mesurant **un** agent contre deux adversaires doit la citer plutôt que la colonne à
   trois sièges de la phase 2 — **en disant que ses donnes sont celles de la phase 2, pas celles
   de l'agent**.
6. **Les 20 mutations ne couvrent aucun fichier de `agents/` ni de `mesure/`.** La phase 4
   hériterait d'un moteur muté et de ~2 500 lignes de mesure qui ne le sont pas. **Arbitrage de
   périmètre remonté au pilote, non décidé ici.**
