# Journal des décisions

**Une entrée par tour de boucle d'investigation. Antichronologique — le plus récent en haut.**

Format et règles : [05_protocole_experimental.md](05_protocole_experimental.md) §0.

```
[date] Phase X.Y — <titre>
Hypothèse   : énoncé falsifiable, écrit AVANT l'expérience
Instrument  : métrique, seuil chiffré, durée à laquelle elle devient décisive
Résultat    : ce qu'on a mesuré
Audit       : le chiffre mesure-t-il ce qu'on croit ? sur quel support ? comparable ?
Décision    : go / pivot / abandon — avec justification
Impact plan : phases invalidées ou modifiées
```

---

## [2026-08-19] Phase 2 — Mesurer le jeu avant d'y jouer

**Hypothèse.** *Écrite et commitée avant toute mesure, `mesure/phase2_hypothese_et_instrument.md`.*
La position de départ n'avantage aucun siège de façon décisive. Seuil du protocole : un siège
au-delà de 38 % des parties rend l'avantage structurel et impose la permutation systématique.

**Instrument.** Trois campagnes sur `entrainement-3j`, 10 002 parties chacune. A : trois
aléatoires, 1 667 donnes × 6 réplicats, seeds 0–1666, `Random(2000000 + 6×donne + réplicat)`.
A contrôle : seeds 10000–11666. B : 1 greedy contre 2 aléatoires, 3 334 donnes × 3 sièges,
`Random(3000000 + 3×donne + siège)`. Bootstrap **par donne**, 10 000 réchantillons,
`Random(2500000)`. Une quatrième population ajoutée après l'audit : trois greedys, décalage
`6000000`, pour la seule ligne de base collective. Rapport régénérable par
`uv run python -m mesure.phase2`.

**Résultat. Les quatre mesures sont établies, et le seuil n'est pas franchi.**

- **M1.** Siège le plus favorisé à **33,50 %** de part de victoire fractionnée, +0,35 σ de
  l'attendu ; gains moyens à ±0,004 de zéro. Le seuil de 38 % n'est pas franchi, et il
  n'aurait rien testé : il est à **9,9 σ** de la valeur nulle à n = 10 002, et ne devient un
  test à 5 % qu'à n = 392. Trois niveaux neutres coexistent — 0,0000 pour le gain, 33,33 %
  pour la part fractionnée, `(1 − P(ex æquo))/3` pour la part stricte, qui **ne peut donc pas
  servir de seuil**.
- **M2.** σ(score) = **4,412**, σ(gain) = **0,6652**. Corrélation intra-donne mesurée à
  **ρ = 0,0066** sous jeu aléatoire, soit un facteur de gain de 1,01 contre les « cinq à dix »
  qu'annonce le §1 du protocole — affirmation qui reste **non appuyée**. À 1 000 parties
  appariées, l'écart de gain détectable est **+0,1013**.
- **M3.** Greedy contre deux aléatoires : gain moyen **+0,7978**, part de victoire fractionnée
  **86,52 %** — à comparer à 33,33 %, pas à 50 %. Et un résultat que M1 seul ne pouvait pas
  donner : **l'avantage de siège est négligeable sous jeu aléatoire et massif sous jeu
  greedy**, contraste apparié entre sièges extrêmes **+0,1890** IC 99 % [+0,1588 ; +0,2196].
  La permutation systématique était donc la bonne décision, pour une autre raison que celle
  qui la motivait.
- **M4.** Dix-sept compteurs, chacun avec son dénominateur, son grain et sa vue. `B1-motif`
  **47,93 %**, `B4-brut` **23,65 %**, `B7-gaspillage` **0,15 %**. Chaque ligne porte l'écart
  détectable au budget de la phase 3 ; **19 lignes sur 34 sont hors budget**.

**Audit.** **Trois tours**, par une conversation distincte qui a réimplémenté depuis le texte
des règles sa propre vue légale, son greedy, ses sept compteurs et son intervalle de confiance,
sans réutiliser une ligne du constructeur, et écrit **75 contrôles hostiles et de
re-vérification**. Code : `audit/phase2/` et `tests/audit_phase2/`. Verdicts dans
`audit/verdict_phase_2.md`, `audit/verdict_phase_2_tour_2.md` et
`audit/verdict_phase_2_tour_3.md`.

*Tour 1 — livrable `02ae24b`, verdict **REJETÉ**.*

Ce que l'audit a **confirmé**, par du code indépendant : σ(gain) 0,6671 contre 0,6652 ; gains
de siège du greedy 0,714 / 0,815 / 0,895 contre 0,697 / 0,812 / 0,886, donc le résultat central
de M3 ; taux de refus B4 23,81 % IC 99 % [22,53 ; 25,12] contre 23,65 % ; **395 lignes sur 395
du rapport régénérées à l'identique** ; et que **B7 est aveugle par le bas** — écart détectable
0,12 % pour un taux de 0,10 %, un agent à zéro exact n'en est pas séparable. Deux lectures
indépendantes du §2.2 ont convergé sur l'Indifférence comme seuil de B1, comme elles avaient
convergé sur R2 en phase 1.

**Le greedy ne triche pas**, et c'était la cible numéro un. Sa preuve est à trois niveaux —
statique, `vue_privilegiee` piégée pour lever pendant la décision, brouillage différentiel des
Espions adverses, de la pioche et des mains — chacun assorti d'un test que **le piège mord** et
que **le brouilleur change vraiment la vérité**. L'auditeur l'a refaite par cinq contrôles
distincts, dont un balayage de 60 parties permutant l'identité de chaque dos à chaque nœud.

Ce que l'audit a **trouvé** : un défaut **bloquant** — cinq lignes du §6 publiaient sous
l'intitulé « écart greedy-hasard observé » une différence entre **deux grains**, greedy sur un
siège contre hasard sur trois agrégés, avec **inversion de signe** sur B1 (−23,97 pt au lieu de
+11,82 pt) et un coût en parties qui la présentait comme un effet réel. Le §5 portait
l'avertissement, le §6 non — et c'était la réserve laissée ouverte au tour 2 de la phase 1, au
même endroit. Deux **majeurs** : la clause d'Indifférence de B1 n'était tenue par aucun test —
la faute du tour 1 de la phase 1, réinjectée, passait 913 tests et déplaçait le chiffre publié
de 9,27 points, plus que les 7,64 points détectables au budget de la phase 3 ; et le greedy
évaluait sa pose sous une résolution conjointe des Assassins que son ciblage, myope, ne
poursuit pas — 7,33 % des nœuds à Assassin en attente ont un argmax différent. Quatre mineurs.

*Tour 2 — corrections `72630a1`, verdict **ACCEPTÉ SOUS RÉSERVE**.*

Les quatre défauts sont corrigés, et **trois le sont avec la parade qui empêche la correction
de se défaire** : une exception `GrainsIncomparables` levée par `ecart_de_taux` **et**
`cumuler` plutôt que des cellules réécrites, un grain qui porte le nombre de sièges agrégés
là où les deux libellés étaient auparavant identiques, un invariant asserté dans
`observations_par_partie`, et une fonction unique `budget_d_un_compteur` là où trois sites
déduisaient chacun leur dénominateur. Le greedy n'est pas corrigé mais **caractérisé** — §4 bis,
`mesure/coherence_greedy.py`, un test de caractérisation — et c'est le bon choix : la ligne de
base des phases suivantes est celle de *cet* agent, et déplacer l'étalon après publication est
le mode de défaut du projet. La pré-inscription n'est pas amendée, vérifié par `git diff`.

**Un cinquième défaut a été trouvé après le verdict, par relecture humaine, et il est le plus
instructif de la phase.** Le générateur divisait les budgets par un facteur trois qui n'avait
pas lieu d'être : un compteur `-par-partie` rend **un** booléen par partie quel que soit le
nombre de sièges, l'agrégation étant dans son numérateur. Six budgets étaient gonflés d'un
facteur exactement trois. Il a été validé deux fois avant d'être vu, par une vérification qui
reproduisait le nombre en recevant **le même dénominateur erroné** — deux implémentations qui
partagent la même hypothèse fausse concordent parfaitement. Les six valeurs corrigées, 745,
1 295, 299, 239, 10 400, 280, ont été reconstruites par l'auditeur avec ses propres quantiles
et son propre dénominateur par partie, dérivé du **texte de l'unité avant tout calcul** :
**6 sur 6 à l'unité près**.

Deux réserves, de la même famille — **un compte à la place de noms**. Le §4 bis écrit « trois
compteurs de B4 sont jugés par cette même évaluation myope » là où le code en concerne
**quatre**, et n'en nomme aucun ; l'omis est `B4-meurtre-couteux`, l'un des deux zéros absolus
du rapport. Et l'inclusion `B1-collectif ≥ B1-motif`, dont la chute a déjà révélé un compteur
faux, est vérifiée sur les deux anciennes colonnes et pas sur la troisième population — celle
qui existe précisément pour `B1-collectif`. L'auditeur l'a vérifiée lui-même : 3 916 ≥ 2 528 au
même grain, elle tient.

*Tour 3 — corrections `479a57e`, verdict **ACCEPTÉ**.*

Les deux réserves sont levées et le test que l'auditeur avait laissé rouge revient par son nom,
vert : `test_p3_les_compteurs_juges_par_l_evaluation_myope_sont_QUATRE_et_nommes`. Le §4 bis
écrit désormais **quatre** compteurs, les nomme, et ajoute que **les deux zéros absolus sont
dans ce lot** — aucune occurrence de « trois compteurs de B4 » ne survit dans le dépôt, y
compris dans `agents/greedy.py`, la spécification de l'agent, où la phrase était la même.
`verifier_inclusion_b1` **lève** et le rapport l'appelle sur les **trois** populations avant
d'écrire, aux **deux** grains — extension au grain `-par-partie` qui n'était contrôlé nulle
part. L'auditeur a éprouvé les deux branches aux deux grains, y compris le cas d'égalité, qui
est licite. **977 tests verts, 0 rouge.**

Une **quatrième occurrence de la même faute** est sortie dans ce tour, trouvée par le
constructeur dans la dernière phrase qu'il venait d'écrire : sa ligne de durées machine annonçait
« −26 % à +16 % » sur « les cinq campagnes » alors que le −26 % venait de `B, 3 greedys`, qui
n'existe que dans les passes 3 à 5 et que la phrase excluait. Deux chiffres exacts sur une
population que la phrase ne nommait pas. Corrigé en « −23,3 % à +15,5 % », refait par l'auditeur.

Quatre mineurs du tour 1 restent ouverts, hors du périmètre re-vérifié : l'encodage cp1252 du
rapport généré quand les quatre autres documents sont en UTF-8 ; `vue_du_joueur`, rendue
publique par cette phase, qui ne valide pas son argument et rend une vue n'appartenant à aucun
siège — réouverture du défaut 2 de la phase 0 sur une entrée neuve ; deux des douze directions
annoncées comptées comme tenues alors que la pré-inscription les déclare nulles **par
construction** ; et une cellule « voir `B4-departage` » dans une table dont le texte dit
qu'elle ne se lit qu'en juxtaposant deux nombres.

**Le seul point resté ouvert au tour 1 est clos, et il appartenait à l'auditeur.** Son 7,33 %
et le 4,23 % du constructeur mesurent la même chose sur **deux populations différentes** :
trois greedys donne 287/4 145 = 6,92 % IC 99 % [5,95 ; 8,00], un greedy contre deux uniformes
donne 204/4 145 = 4,92 % IC 99 % [4,10 ; 5,85], et 0,4064 contre 0,4062 nœud par **siège-partie
mesuré** établit que la définition du dénominateur est identique. Les deux populations comptent
10 200 sièges-parties pour 3 400 et 10 200 parties jouées : c'est l'égalité des sièges-parties,
non celle des parties, qui rend les deux taux comparables. Et leur dénominateur commun de
4 145 nœuds est **structurel** — chaque joueur vide sa main à chaque tour et la recomplète
depuis une pioche fixée par la donne, donc la main d'un siège, et le nombre d'Assassins qu'il
pose, ne dépendent pas de la politique ; MESURÉ identique sur 40 donnes et trois compositions.
Les deux nombres étaient justes ; celui de l'auditeur était publié sans nommer sa population —
la faute qu'il reprochait ailleurs.

Une **troisième réserve** a été relevée après le verdict, dans le harnais de l'auditeur
lui-même : son compteur s'appelait `parties` et comptait des itérations, si bien que sa phrase
« nœud par partie » nommait une unité qui n'était pas celle du calcul. Aucun taux, aucune borne
et aucune conclusion ne changent. Corrigée, et tenue par deux tests — l'un sur l'égalité des
sièges-parties, l'autre sur l'indépendance de la main à la politique.

**Décision. Go.** Verdict final **ACCEPTÉ** au tour 3. La phase 2 est close. Les quatre lignes de base sont établies et citables par
les phases suivantes, à trois conditions écrites dans le rapport lui-même : B1 et B3 mesurent
chez le greedy la fréquence à laquelle le **motif** apparaît par coïncidence, jamais une
planification ; B1 est plafonné par les 7,40 % de parties portant une perte d'acquis qu'aucun
siège ne pouvait voir, mesurés en phase 1 ; et **19 des 34 lignes de M4 sont hors du budget de
la phase 3**, B7 n'y pouvant rien séparer du tout.

**Impact plan.** La phase 3 s'ouvre sans modification, avec quatre contraintes qui en viennent.
La permutation des sièges est **obligatoire et inconditionnelle** — non parce que M1 l'exige,
il ne la déclenche pas, mais parce que l'avantage de siège sous jeu greedy est massif. Le seuil
« > 55 % contre le greedy sur 1 000 parties appariées » doit être relu contre l'écart de gain
détectable mesuré, **+0,1013** à ce budget. Les comparaisons de comportement doivent citer les
lignes **au même grain**, la garde levant désormais si elles ne le sont pas. Et la ligne de base
collective de `B1-collectif` est celle des **trois greedys**, pas celle d'un greedy contre deux
hasards.

**Défauts du protocole, à corriger dans
[05_protocole_experimental.md](../documentations/05_protocole_experimental.md).** Cinq trous, dont
quatre déjà relevés en phase 1 et un nouveau. Le seuil de 38 % de M1 ne dit pas ce qu'est
« gagner » quand les égalités sont conservées, et les trois lectures possibles n'ont pas la même
valeur nulle — sous la lecture la plus littérale, « être au score maximum, ex æquo compris »,
les **trois** sièges valent 38,5 % et le seuil se franchit avec un avantage nul. « La variance
du score final » ne nomme pas son unité, et celle qui dimensionne une comparaison est la
variance du **gain**, pas du score. « Si le greedy est à 60 % » ne dit pas contre quoi, ni que
le point de comparaison à trois joueurs est 33,33 %. L'affirmation que l'appariement « divise
par cinq à dix » le nombre de parties nécessaires est **publiée sans mesure** et infirmée pour
les deux politiques mesurées ici — ρ = 0,0066. Enfin la phase 2 est annoncée comme ne pouvant
pas échouer : c'est vrai de son go/no-go et faux de tout le reste, puisqu'elle produit les
lignes de base que toutes les phases suivantes citeront sans les rejouer.

**Six enseignements de méthode.**

- **Un chiffre qui se reconstruit n'est pas un chiffre juste.** Le facteur trois a survécu à
  deux vérifications A7 réussies, parce que la formule de contrôle recevait le même
  dénominateur erroné que le générateur. **L'unité se reconstruit avant la valeur, et
  séparément.** C'est le contrôle qui manquait, et il ne se confond pas avec A7.
- **Une correction arrive avec ce qui l'empêche de se défaire.** Trois des quatre corrections
  de ce tour sont des levées d'exception ou des invariants assertés, pas des cellules
  réécrites — et la seule qui ait été trouvée deux fois au même endroit, le grain du §6, est
  précisément celle qu'un tour antérieur avait corrigée sans parade.
- **Un compte n'est pas une liste de noms.** « Trois compteurs de B4 » en concerne quatre ;
  « vérifiée sur les deux colonnes » n'en couvre plus deux depuis qu'il y en a trois. Les deux
  réserves de ce tour sont la même faute, et elle se referme en écrivant les noms.
- **Un agent de référence se documente, il ne se corrige pas après publication.** L'incohérence
  d'horizon du greedy est réelle et mesurée ; la corriger aurait déplacé l'étalon de toutes les
  phases suivantes. Le test qui l'interdisait a été requalifié en test qui la caractérise, par
  l'auditeur et sur son propre code.
- **La correction est le lieu du défaut suivant, et il faut donc relire ce qui a été écrit en
  dernier, pas ce qui a été mesuré en premier.** Quatre fois de suite dans cette phase : le
  défaut 3 corrigé puis laissé à moitié puis complété, le défaut 5 né dans la table qui
  corrigeait le défaut 1, la réserve 3 née dans le harnais de l'auditeur, et la clause des
  durées née dans le commit qui consignait la leçon. **La même faute — un chiffre exact sur une
  population que sa phrase ne nomme pas — est sortie sous quatre formes dans une seule phase**,
  chez le constructeur comme chez l'auditeur, et chaque fois dans le texte le plus récent.
- **Un contrôle de non-régression n'établit pas la justesse d'une unité, seulement la neutralité
  d'un refactor.** Si une ligne portait un dénominateur faux depuis le début, le contrôle
  passerait à l'identique. C'est le piège du `2 234` appliqué à un contrôle au lieu d'un nombre,
  et c'est le constructeur qui l'a écrit à côté de son propre instrument.

**Et une cinquième occurrence, dans cette entrée même.** La proposition de l'auditeur
annonçait « quatre enseignements de méthode » et en listait **six** — un compte à la place
d'une liste de noms, dans le texte qui nomme cette faute quatre fois. Corrigé au report par
le pilote. La leçon tient donc sur elle-même : **relire ce qui a été écrit en dernier**,
y compris quand c'est la leçon.

---

## [2026-08-18] Phase 1 — L'instance d'entraînement, et audit croisé de sa mesure

**Hypothèse.** *Écrite et commitée avant toute mesure, `mesure/hypothese_et_instrument.md`.*
L'instance `entrainement-3j` — 4 familles, 5 rôles, 2 exemplaires, 3 joueurs, 40 cartes,
4 tours — conserve la substance du jeu : sous jeu uniformément aléatoire, sur 1 000 parties,
les trois joueurs jouent le même nombre de tours (H1), la distribution des scores n'est pas
dégénérée (H2), et au moins un retournement survient dans au moins 33,3 % des parties (H3).

**Instrument.** 1 000 parties, donne `Engine.reset(seed)` seeds 0–999, politique uniforme sur
`legal_actions()` avec `Random(1_000_000 + seed)`. Seuil H3 : `p ≥ 1/3`, intervalle exact de
Clopper-Pearson à 99 %, bande d'indécision [0,295 ; 0,372] fixée d'avance. La mesure tranche
dès N = 30 si `p̂ ≥ 0,80`. Le protocole ne définissant pas « retournement », quatre définitions
ont été pré-inscrites ; le go/no-go porte sur **R2, perte d'acquis** — `∃t : s_{t−1} ≠
Indifférente et s_t ≠ s_{t−1}` — parce que l'encadré du §2.2 des règles tranche déjà que le
seuil qui compte est l'Indifférence et non l'Obscurité.

**Résultat.** Hypothèse **vérifiée sur les trois énoncés.** H1 : 1 000/1 000, vecteur de poses
`(4, 4, 4)`. H2 : 10/10 critères, écart-type 4,4 par siège, 25 à 26 valeurs de score
distinctes, mode à 9 %, trois ex æquo dans 1,5 % des parties. H3 : **96,00 % (960/1 000),
IC99 [94,12 % ; 97,42 %]**, soit 2,88 fois le seuil — borne basse à 94,12 %. 2,075 familles
retournées par partie sur 4. Une partie se joue en 1,6 ms, 19,2 décisions. 82,53 % des
7 206 nœuds de ciblage offrent au moins une cible, donc un refus qui est un choix et non un
constat.

**Audit.** Deux tours, par une conversation distincte qui a réimplémenté le calcul de statut,
le compteur de retournements, l'intervalle de confiance et la campagne depuis le texte des
règles, sans réutiliser une ligne du constructeur, et écrit seize contrôles hostiles.
Code de l'audit : `audit/` et `tests/audit/`, verdict détaillé dans
`audit/verdict_phase_1.md`.

*Tour 1 — livrable `3f5b75d`, verdict **REJETÉ**.*

Ce que l'audit a **confirmé** : les trois critères de go/no-go, remesurés indépendamment —
`(4, 4, 4)` dans 5 000 parties sur 5 000, retournements à 94,0–95,5 % selon le bloc de seeds,
étendue de 1,5 point ; l'accord des deux calculs de statut sur **11 000 comparaisons,
0 désaccord** ; l'exactitude de l'intervalle sur **820 couples (k, n, α), écart maximum
2,5 × 10⁻¹²**, par quatre calculs indépendants ; l'estimation « ~8 cartes par domaine » qui
fondait le seuil D2, mesurée à **6,99** ; et la **convergence de trois lectures indépendantes
du §2.2** sur la définition R2, l'auditeur ayant écrit la sienne avant de lire celle du
constructeur. Le constructeur ne surinterprète pas non plus son chiffre : sa pré-inscription
écrit, avant la mesure, que l'aléatoire n'établit pas qu'un agent saura planifier un
retournement.

Ce que l'audit a **trouvé, et que le constructeur avait manqué** : l'affirmation « **0 sur
1 000 retournements R2 invisibles des trois joueurs** » était **fausse**. Le calcul agrégeait
les quatre familles en un booléen de partie avant de comparer les vues, puis les trois sièges
par un `any` ; il comptait « une partie où la vérité a un R2 et où aucun siège n'en a sur
aucune famille », conjonction quasi impossible entre deux grandeurs valant 96 % et ~93 %. Le
même invisible, mêmes seeds, sous le décalage de politique du constructeur, **grain tour** :

| Niveau d'agrégation | seeds 0–999 | seeds 1000–1999 |
|---|---|---|
| partie, familles confondues — *le chiffre publié* | 0 | 0 |
| famille — invisibles / familles en R2 | 5 / 2 075 = **0,241 %** | 11 / 2 026 = **0,543 %** |
| famille — invisibles / emplacements famille × partie | 5 / 4 000 = 0,125 % | 11 / 4 000 = 0,275 % |
| événement — invisibles / pertes d'acquis | 79 / 2 665 = **2,96 %** | 56 / 2 531 = 2,21 % |
| événement — parties touchées | 74 / 1 000 = **7,40 %** | 56 / 1 000 = 5,60 % |

**Le dénominateur retenu au niveau famille est 2 075, les familles qui ont effectivement perdu
un acquis** : la question posée est « parmi les retournements qui ont eu lieu, lesquels
n'étaient visibles de personne ». Rapporter les mêmes 5 aux 4 000 emplacements famille × partie
répond à une autre question — quelle part du plateau porte un retournement invisible — et
divise le taux par deux. Les deux lectures sont justes ; les deux sont écrites ci-dessus
précisément parce qu'un taux sans son dénominateur n'est pas auditable.

Cinq témoins nommés au premier bloc : seeds 308, 453, 496, 539, 933. Le cas se construit à la
main en quatre poses — deux Espions de même famille posés par deux joueurs différents — et
touche **une partie sur treize à dix-huit** (74/1 000 = 1 sur 13,5 ; 56/1 000 = 1 sur 17,9 ;
au grain fin, 75 et 57 pour 1 000, soit 1 sur 13,3 et 1 sur 17,5). **Son propre test le
démontrait déjà** : `tests/mesure/test_parties_construites.py` assertait exactement ce cas, sa
docstring écrivant « un retournement que personne ne pouvait planifier ». Le test et le rapport
se contredisaient dans le même livrable.

Cinq défauts mineurs par ailleurs : une assertion tautologique, l'instance définie trois fois,
quatre littéraux en dur dans les décompositions du rapport, un seuil D2 franchi dès 12 parties
donc sans pouvoir discriminant, et un intervalle qui ne validait pas `n > 0`.

*Tour 2 — correction `d7398bd`, verdict **ACCEPTÉ SOUS RÉSERVE**.*

Les six défauts sont corrigés. Le comptage de l'invisible ne compare plus que des grandeurs
non agrégées et publie les deux niveaux avec leurs dénominateurs ; **l'implémentation
indépendante de l'auditeur rend exactement le même nombre au même grain** — 81 événements
invisibles sur 2 735 dans 75 parties au grain fin, contre 79 sur 2 665 dans 74 parties au
grain tour, celui que le rapport publie. Deux défauts sont corrigés mieux que demandé : le
pouvoir discriminant est mesuré pour les **quatre** critères, et non le seul D2 relevé par
l'audit — D1 et D3 sont satisfaits dès 3 parties, D4 dès 1 —, et le §5.3 de la pré-inscription
porte un erratum qui **conserve** la phrase fausse plutôt que de l'effacer. L'auditeur a
re-vérifié la correction en y ré-introduisant la faute exacte : un test rouge, sur une partie
construite à la main. Les trois chiffres du go/no-go sont inchangés. 648 tests verts chez le
constructeur, les 16 contrôles hostiles de l'auditeur verts contre le code corrigé.

Deux réserves : rien ne relie la définition unique de l'instance dans `mesure/instance.py` à
la description indépendante de `tests/outils.py` — l'indépendance de l'oracle est justifiée,
l'absence de garde-fou contre la dérive ne l'est pas ; et la section 6 du rapport ne répète pas
le grain sur ses deux blocs de comptage, si bien qu'un lecteur reconstruisant 2 078 familles au
grain fin au lieu de 2 075 au grain tour ne peut pas savoir laquelle des deux lectures est la
sienne.

**Décision.** **Go.** La phase 1 est close. `entrainement-3j` est l'instance des phases 2 et 3.

**Impact plan.** La phase 2 s'ouvre sans modification. Une mesure s'ajoute à sa liste : la
fréquence des retournements qu'**aucun** siège ne voit est un **plafond de ce que B1 peut
mesurer**. Une ligne de base d'agent qui ne planifie jamais un retournement doit être lue en
retranchant les ~7 % de parties portant une perte d'acquis qu'aucune politique, aussi bonne
soit-elle, ne pouvait voir venir.

**Défauts du protocole, à corriger dans [05_protocole_experimental.md](05_protocole_experimental.md).**
Trois termes du go/no-go de la phase 1 ne sont définis nulle part, et les trois sont chiffrés :
« retournement », « distribution non dégénérée », et « situations où refuser de tuer est
possible » — dont la lecture littérale est **vide**, refuser étant toujours légal (§4.1,
arbitrage R2), si bien que la fréquence vaudrait 100 % par construction. Les définitions
proposées par le constructeur ont tenu deux tours d'audit et doivent remonter dans le document.
Le §3 présente en outre « 20 cartes ou 40 cartes » comme un arbitrage à trancher en phase 1 :
il n'en est pas un, la variante à 20 cartes étant refusée à la construction par le plancher
`tours ≥ 3` du §8 des règles.

**Trois enseignements de méthode.**

- **Un taux dont le sujet grammatical n'est pas l'unité comptée doit publier son
  dénominateur.** L'erreur de ce tour n'est ni un calcul faux ni un DÉDUIT présenté comme un
  MESURÉ : c'est un chiffre juste, reproductible au bit près, dont la phrase parlait de
  retournements quand le calcul parlait de parties. Aucun contrôle existant ne cherchait cette
  faute-là.
- **Un zéro absolu doit être confronté à un cas construit à la main avant d'être écrit.**
  Celui-ci était contredit par un test du même livrable.
- **Un chiffre doit porter son échantillon — grain et dénominateur compris.** L'auditeur a
  commis deux fois la faute qu'il reprochait : d'abord en juxtaposant deux comptes justes,
  70 et 81 événements sur les mêmes seeds, sans dire que le décalage de politique différait —
  cause racine, une valeur en dur invisible dans les chiffres qu'elle produisait, devenue un
  paramètre nommé ; ensuite en écrivant « 5 familles sur 4 000 » sans dire que « 5 sur 2 075 »
  existait et disait autre chose. Les deux corrections sont dans cette entrée.

---

## [2026-08-17] Phase 0 — Audit croisé du moteur conforme

**Hypothèse.** Le moteur construit par la conversation de l'action 3 implémente les règles de
`01_regles.md`, et ses 502 tests verts l'établissent.

**Instrument.** Protocole d'audit croisé, `07_protocole_audit_croise.md`. Contrôles A1 à A7
par une conversation distincte, qui rejoue tous les chiffres elle-même et écrit ses propres
tests hostiles contre le **texte des règles**, sans appeler une seule fonction du moteur pour
calculer un attendu. Seuil de rejet fixé d'avance : un critère non satisfait, un test hostile
rouge, ou une affirmation fausse dans le compte rendu.

**Résultat.** Hypothèse **partiellement rejetée**. Aucun défaut de conformité aux règles —
61 cas hostiles, dont une construction de fuite d'information à pioches jumelles et une
traduction complète de l'espace d'actions sous permutation des familles, n'en ont produit
aucun. Mais **neuf défauts** dans l'adaptateur, la stratégie de test et la documentation, en
trois tours :

| Tour | Défauts | Les deux qui comptent |
|---|---|---|
| Audit initial | 6 (2 majeurs, 4 mineurs) | `make_py_observer` absent → le harnais de validité d'OpenSpiel ne pouvait pas tourner ; l'observation d'un identifiant réservé rendait une vue **n'appartenant à aucun joueur**, sans lever |
| Correction 1 | +1 trouvé par le correctif | libellés d'action dupliqués — trouvé par `random_sim_test` en une exécution, que 502 tests maison n'avaient pas vu |
| Re-vérification | +2 | régression sur le motif d'appel d'OpenSpiel (34 sites, dont `deep_cfr` et `best_response`) ; le jeu ne survivait pas à un aller-retour par sa propre chaîne de paramètres |

État final, **remesuré par l'auditeur** sur `b90f714` : 576 tests verts, 127/127/127 sur les
trois moteurs, 143 invariants, 8/8 critères, **618 instructions et 0 manquante**, **18
mutations sur 18 détectées**, `ruff` propre.

**La réserve unique de cet audit est levée le 17/08.** Elle portait sur
`_action_to_string`, qui nommait la famille et le rôle de la carte ciblée par un Assassin —
`tuer la cible 1 : f0-ESPION` — y compris lorsque cette carte était un Espion posé face
cachée par un adversaire, dont le joueur qui choisit ignore l'identité. Rien n'en fuitait :
ces libellés n'étaient lus que par du débogage. Mais **rien ne l'aurait signalé non plus**,
l'invariant I7 ne surveillant qu'`information_state_string`. Un dos est désormais dit dos,
situé dans sa zone et numéroté par son rang parmi les cartes de même apparence encore en jeu
— le rang étant ce qui empêche de rouvrir le défaut 7 en anonymisant. Mesures sur `7eabe3b` :
**596 tests verts, 127/127/127, 143 invariants, 8/8 critères, 643 instructions et 0
manquante, 19 mutations sur 19 détectées**, `ruff` propre. **Le nouveau verdict appartient à
l'auditeur** : ce paragraphe constate la correction, il ne la valide pas.

**Audit du résultat.** Deux mesures méritent d'être distinguées de tout le reste :

1. **Deux des neuf défauts vivaient à 100 % de couverture d'instructions.** Le défaut 2 était
   une branche exécutée à chaque appel mais jamais avec l'argument omis ; la régression du
   tour 2 était un refus exécuté mais jamais dans le cas où il devait rendre une valeur. La
   couverture d'instructions **ne peut pas** les voir. La couverture de **branches** est le
   seul changement d'instrument qui les aurait signalés.
2. **La preuve que les phases 2 et 3 sont débloquées a été faite, pas déduite.** L'auditeur a
   fait tourner de vrais consommateurs OpenSpiel de bout en bout sur `rapide-2j` :
   `mcts.MCTSBot` — partie entière, 38 coups, gains [1.0, −1.0] — et
   `rl_environment.Environment` — 14 pas, rewards [1.0, −1.0].

**Décision.** **Go.** Verdict **ACCEPTÉ SOUS RÉSERVE**. La phase 0 est close.

~~Une réserve reste ouverte et demande un arbitrage : `action_to_string` nomme la famille et
le rôle d'un **Espion caché**.~~ **Arbitrée et corrigée le 17/08, avant la phase 1** plutôt
qu'avant la phase 3 : l'invariant I7 ne couvrant qu'`information_state_string`, aucun test
n'aurait signalé le jour où une interface ou une trace d'entraînement se serait mise à lire
ces libellés. Détail au paragraphe « la réserve unique est levée » ci-dessus. **I7 n'a pas été
étendu à `action_to_string`** — ce serait modifier la spécification, et c'est un arbitrage
distinct, resté ouvert.

**Impact plan.** Aucun. La phase 1 s'ouvre sans modification. Trois enseignements de méthode
sont à reporter dans les phases suivantes :

- **La section « Incertain » d'un compte rendu désigne le défaut suivant.** Le constructeur
  avait écrit « SUPPOSÉ que la sérialisation passerait » ; c'était faux, et c'est devenu le
  défaut 9. Un `SUPPOSÉ` dans un compte rendu est un test qui manque.
- **Un arbitrage mal formulé produit une régression.** La consigne disait « la substitution
  disparaît » là où elle aurait dû dire « la substitution est validée » — d'où le défaut R1.
  Un arbitrage doit énoncer ce qui doit **continuer de marcher**, pas seulement ce qui doit
  échouer.
- **Le harnais standard de l'écosystème trouve ce que la suite maison ne cherche pas.**
  Débloquer `random_sim_test` a produit un défaut réel à la première exécution.

---

## [2026-08-15] Pré-phase 0 — Conformité des instances aux règles

**Hypothèse.** Les instances CFR implémentent les règles de Courtisans.

**Instrument.** Lecture croisée instances / `regles.md` / `app/jeu.py`, puis 20 000 playouts
pour quantifier l'impact des écarts trouvés.

**Résultat.**

- **N1** — le meurtre de l'Assassin est obligatoire alors qu'il est facultatif :
  **20.0 %** des résolutions où refuser serait strictement meilleur, perte moyenne
  **1.34 point**, **38.1 %** d'auto-mutilations forcées.
- **N3** — tours inégaux : P0 joue 2 tours (6 cartes), P1 un seul (3 cartes). Idem en 2.1d.
- **N2** — `app/jeu.py::is_done` teste la fin de partie joueur par joueur : à 4 joueurs, les
  deux premiers de l'ordre jouent un tour de plus.

**Audit.** L'ordre de pose intra-tour, suspecté, a été vérifié **sans effet** (0 cas sur 24) :
ce n'était pas un écart. Les mesures d'impact sont myopes (score si la partie s'arrêtait là),
donc indicatives et non exactes — mais l'ordre de grandeur suffit à conclure.

**Décision.** Hypothèse **rejetée**. L'oracle à 0.001783 est l'équilibre exact d'un jeu qui
n'est pas Courtisans.

**Impact plan.** La phase 0 devient bloquante pour tout le reste. Les verdicts des briques
2.1c et 2.1e sont suspendus jusqu'à mesure de la fréquence du passe à l'équilibre (P2.5).

---

## [2026-08-15] Pré-phase 0 — Que mesure le plafond à 0.190 ?

**Hypothèse.** Le chiffre 0.190 mesure la qualité de Deep CFR sur l'instance 2.1e.

**Instrument.** Lecture de `deep_cfr_mini.py`, puis simulation de la collecte de
strategy-memories (sémantique OpenSpiel `_traverse_game_tree`) au budget exact du run
(20 itérations × 2000 traversées).

**Résultat.** `DCFR_MEASURE_NET` vaut 0 par défaut : la métrique est
`buffer_exploitability`, qui **retourne la politique uniforme** pour tout info-set absent du
buffer. Couverture au budget du run : **295 176 / 455 092 = 64.9 %**. Au moins **35 %** des
info-sets jouent au hasard dans la stratégie notée 0.190.

**Audit.** La simulation utilise une politique uniforme, qui **maximise** l'exploration : le
chiffre réel est plus bas, pas plus haut. C'est donc une borne supérieure, à confirmer par
lecture du log réel (P3.0, dix secondes). Aux briques 1 à 2.1d la couverture était totale
(236/236, 12 484/12 484) — la métrique y était honnête, et c'est ce qui rend le 0.190 non
comparable.

**Décision.** Hypothèse **rejetée**. Le 0.190 n'est pas comparable aux chiffres des briques
précédentes.

**Impact plan.** La conclusion « mur de variance à 455k info-sets → ESCHER/DREAM » du
`rapport_expert.md` §34 est **suspendue**. Le diagnostic est rouvert en phase 3, avant toute
phase 4.

---

## [2026-08-15] Pré-phase 0 — L'encodage perd-il de l'information ?

**Hypothèse.** La représentation d'un info-set n'est pas injective : deux info-sets
distincts au sens des règles produisent le même tenseur, ce qui plafonnerait
l'exploitabilité quel que soit l'algorithme.

**Instrument.** Traversée exhaustive des **8 250 001** états de l'instance combo. Trois
contrôles : collisions tenseur → string, non-déterminisme string → tenseur, et cohérence des
actions légales au sein d'un info-set.

**Résultat.**

```
info-sets (strings distinctes) : 475 000   (P0 455 092 + P1 19 908)
tenseurs distincts             : 475 000
2 info-sets → 1 tenseur                       : 0
1 info-set → 2 tenseurs                       : 0
actions légales incohérentes dans un info-set : 0
```

**Audit.** Le harnais a d'abord été validé sur l'instance 2.1c (123 921 états), dont le
résultat correspond à la documentation existante, avant d'être appliqué à 2.1e. Le troisième
contrôle est nouveau — `check_combo.py` ne le faisait pas — et c'était le risque réel, la
string ne codant que la zone-clé de l'assassin en phase de ciblage.

**Décision.** Hypothèse **rejetée**. L'encodage n'est pas la cause du plafond.

**Impact plan.** Réoriente l'investigation vers la métrique et la conformité aux règles.
Les tests d'injectivité deviennent C13 et C14 de la suite de conformité, à exécuter
automatiquement.
