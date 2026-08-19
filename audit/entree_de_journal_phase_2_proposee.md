# Entrée de journal proposée par l'auditeur — phase 2

Format du §4 de [08_modele_compte_rendu.md](../documentations/08_modele_compte_rendu.md).
C'est l'audit qui clôt la phase ; cette entrée est ma proposition, à reporter dans
[06_journal_decisions.md](../documentations/06_journal_decisions.md) en haut, avant celle du
18/08.

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

**Quatre enseignements de méthode.**

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
