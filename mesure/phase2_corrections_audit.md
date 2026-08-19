# Phase 2 — les quatre défauts de l'audit croisé, corrigés

**Verdict de l'audit croisé : REJETÉ.** Les trois défauts qu'il a trouvés ont été recalculés
indépendamment par l'humain et tiennent tous les trois ; un quatrième, mineur, vient de l'humain.
Ce document est la liste que l'audit re-vérifiera, et rien d'autre : pour chaque défaut, ce qui a
été corrigé, le test qui le tient, et la preuve que le test mord.

**Ce qui n'a pas été touché.** `courtisans/` est intact. Aucune campagne n'a été rejouée sans
accord écrit. Le travail ne repart pas de l'étape 3.

Reproduire :

```bash
UV_LINK_MODE=copy uv run pytest -q
```

```bash
UV_LINK_MODE=copy uv run python -m mesure.phase2
```

```bash
UV_LINK_MODE=copy uv run python -m mesure.coherence_greedy --donnes 200
```

---

## Défaut 1 — BLOQUANT — deux grains soustraits dans la table que la phase 3 citera

**Le défaut.** Les cinq lignes `-par-partie` du §6 soustrayaient un greedy mesuré sur **un** siège
d'un hasard mesuré sur **trois**, agrégés par « au moins un ». Le signe s'en inversait — **+11,82
pt** au même grain, **−23,97 pt** en mélangeant les deux — et la ligne recevait quand même un
« parties pour l'établir : 102 » qui la présentait comme un effet réel. Le §5 portait
l'avertissement ; le §6, celui qui est titré *M4 pour la phase 3*, ne contenait ni le mot
« grain » ni le mot « comparable ». **Et le même défaut était déjà sorti au même endroit** — une
réserve du tour 2 de la phase 1 portait sur cette section.

**La correction, en quatre pièces.**

1. **Le libellé de grain porte le nombre de sièges agrégés.** `parties (au moins un des 1 sièges
   mesurés)` contre `parties (au moins un des 3 sièges mesurés)`. C'était nécessaire : les deux
   colonnes portaient jusqu'ici **exactement le même libellé** — `parties (au moins un siège
   mesuré)` —, donc comparer les libellés n'aurait rien détecté. Le rapport montre désormais la
   différence dans sa propre colonne « grain ».
2. **`comportements.ecart_de_taux` lève** `GrainsIncomparables` quand les deux grains diffèrent, et
   son message **nomme les deux** : « non comparable » sans dire de quoi à quoi renvoie le lecteur
   au code. C'est une levée et non une cellule corrigée, précisément parce qu'une cellule corrigée
   se re-remplit.
3. **`comportements.cumuler` lève aussi.** C'est l'autre endroit où deux grains se rencontrent :
   `mesurer_comportements` additionne les comptes de chaque composition de sièges, et deux
   compositions de tailles différentes auraient additionné des numérateurs de sens différents en ne
   gardant qu'un libellé — silencieusement.
4. **Le §6 écrit `non comparable : grains différents`** dans les deux colonnes, **jamais un
   tiret** : un tiret se lit « pas encore mesuré », et quelqu'un le remplirait. Le titre du §6
   nomme maintenant ce qui n'est pas comparable.

**Les tests, dans `tests/mesure/test_comportements.py`.**

| Test | Ce qu'il tient |
|---|---|
| `test_le_grain_par_partie_porte_le_nombre_de_sieges_agreges` | le libellé porte le compte, et le grain au couple ne le porte pas — son unité ne dépend pas du nombre de sièges |
| `test_un_ecart_entre_deux_grains_differents_leve` | la levée, et que le message nomme les deux grains |
| `test_un_ecart_entre_deux_memes_grains_se_calcule` | **l'autre branche** — au grain du couple la comparaison vaut `+11,82` pt et doit passer |
| `test_un_ecart_sans_taux_rend_none_et_ne_leve_pas` | un dénominateur vide n'est pas un grain incomparable ; les deux cas ne se confondent pas |
| `test_le_cumul_refuse_deux_grains_differents` | les deux branches de `cumuler` |

**Une garde dont le `raise` n'est pas couvert est une garde dont on ne sait pas si elle lève** :
les deux branches sont exercées pour `ecart_de_taux` comme pour `cumuler`.

**L'arbitrage écrit sur la comparaison par partie.** Elle **existe désormais**, mais pas parce
qu'on l'a réclamée : la campagne à trois greedys autorisée pour la réserve 2 (voir plus bas)
agrège **trois** sièges des deux côtés, donc le grain coïncide et la soustraction est licite. Elle
est publiée au §5 bis, à côté de la colonne de référence qui reste marquée non comparable. Le
`-par-partie` du greedy de référence, lui, ne sera jamais comparable au hasard, et c'est écrit.

---

## Défaut 2 — MAJEUR — la clause du seuil de B1 n'était tenue par aucun test

**Le défaut.** La clause 3 de `B1-motif` dit « Indifférente **ou** en Obscurité ». C'est la bonne
lecture du §2.2 des règles, et l'auditeur y est arrivé **indépendamment** — deux lectures séparées
du même texte convergent, ce qui rend ce choix plus solide que le chiffre lui-même. Mais **aucun
test ne la retenait** : l'auditeur a réintroduit la faute exacte du tour 1 de la phase 1 —
restreindre à l'Obscurité — et obtenu **913 tests verts, zéro rouge**.

Ce que la faute coûterait : le taux publié tomberait de **47,93 %** à **38,66 %**, soit **9,27
points**, quand l'écart détectable au budget de la phase 3 est de **7,64 points**. La régression
serait donc **silencieuse et plus grande que ce que la phase suivante peut mesurer**.

**La correction.** Une partie construite à la main où une famille finit **exactement
Indifférente** — `d(f1) = +2 − 2 = 0` — et où `B1-motif` doit compter **1** tandis que `B1-strict`
compte **0**. La prémisse est **assertée** et non supposée : `statut_de(...) is
Statut.INDIFFERENTE`. Sans cette assertion, un changement de plateau pourrait faire glisser la
famille en Obscurité et le test continuerait de passer en ne testant plus rien.

`test_b1_compte_une_famille_qui_finit_EXACTEMENT_indifferente`, vérifié sur les **deux**
compositions de sièges.

**La preuve que le piège mord.** La faute a été réintroduite localement — `attendu = statut is
Statut.OBSCURITE` sans condition — et la suite complète rejouée :

```
1 failed, 893 passed
FAILED tests/mesure/test_comportements.py::test_b1_compte_une_famille_qui_finit_EXACTEMENT_indifferente
```

**Exactement un test tombe, et c'est celui-là.** Là où l'audit obtenait 913 verts et zéro rouge.
Le fichier a été restauré ensuite.

---

## Défaut 3 — MAJEUR — le greedy ne fait pas ce que disait sa spécification

**Le défaut.** La **pose** du greedy est évaluée avec ses Assassins résolus **conjointement**
(arbitrage G-combiné, §5.3 de l'instrument). Ses **ciblages** se décident **un nœud à la fois**, et
`Perception` ne porte pas les Assassins encore en attente — elle porte `assassin`, celui qui se
résout, et pas la suite. La politique **ne peut donc pas** regarder plus loin.

**L'incohérence est structurelle, pas un accident de code.** L'action de pose de l'adaptateur est
**atomique** — un identifiant encode le bloc de trois cartes entier, fait établi en phase 0 —, donc
le bloc est choisi d'un coup sous une évaluation conjointe pendant que le ciblage se décide après,
sans mémoire de ce que le bloc contenait.

**La correction : la description, pas le code.** Corriger le code referait un autre agent —
`Perception` changerait, donc M3 et M4 entiers seraient à rejouer, et l'audit repartirait de
l'étape 3. Une ligne de base n'a pas besoin d'être forte, elle a besoin d'être **exactement
décrite**. Trois endroits portent la description corrigée :

1. **`agents/greedy.py`**, section « le ciblage se décide SANS les Assassins en attente » — la
   spécification de l'agent, là où un lecteur du code la cherchera.
2. **Le rapport, §4 bis**, avec les chiffres et leurs intervalles.
3. **`mesure/coherence_greedy.py`**, qui mesure l'écart et dit pourquoi il ne le corrige pas.

**Ce que je n'ai PAS fait, et c'est un choix.** La pré-inscription
(`phase2_hypothese_et_instrument.md`, §5.3) décrit l'arbitrage G-combiné sans dire que le ciblage
en sort. Je ne l'ai **pas amendée** : une pré-inscription se lit pour savoir ce qui était prévu
**avant** la mesure, et la corriger après coup détruit exactement ce qu'elle sert à établir. Le
défaut de description est donc consigné là où un lecteur du code le trouvera — la spécification de
l'agent — et ici, jamais dans le document qui précède la mesure.

**Le sens du biais, et il n'est pas le même pour M3 et pour M4.** L'humain proposait un plancher
global ; c'est vrai de M3 et faux de M4.

- **M3 : plancher.** Un agent plus myope que sa spécification est plus **faible**, donc `+0,7978`
  et `86,52 %` sont un **plancher**, pas une estimation de ce qu'un G-combiné complet obtiendrait.
  Un plancher place la barre de la phase 3 plus bas, jamais plus haut.
- **M4 : aucun sens déterminé, et trois compteurs sont tautologiques.** `B4-strict`,
  `B4-départage` et `B4-contre-nature` sont jugés **par `evaluer_actions`**, l'évaluation myope
  elle-même. Le zéro de `B4-contre-nature` **ne dit pas** que le greedy n'a jamais commis de
  meurtre contre-productif : il dit qu'il n'a jamais **contredit sa propre évaluation**. Deux
  énoncés différents, et seul le second est vrai. Les dénominateurs de `B4-strict` et
  `B4-départage` sortent du même argmax, donc la même lecture s'applique aux trois. Pour un agent
  de la phase 3 ce même zéro cesse d'être tautologique et redevient un diagnostic.

**Le test qui tient le comportement myope**, dans `tests/agents/test_greedy.py` :
`test_le_ciblage_ignore_les_assassins_en_attente_et_c_est_caracterise`. Une position construite à
la main où :

| | Tuer | Refuser |
|---|---:|---:|
| évaluation **myope** | −1 | −1 |
| évaluation **cohérente** | −1 | **+1** |

L'argmax myope est **à égalité**, donc le départage uniforme du greedy tire le meurtre **une fois
sur deux** — et ce meurtre est cohéremment dominé de **2 points**. Le test assère les deux
évaluations, que les deux actions sortent du tirage, et que la variante déterministe prend
systématiquement le meurtre. Un « correctif » futur casserait ce test bruyamment, et c'est le but.

Un second test, `test_sans_assassin_en_attente_les_deux_evaluations_coincident`, garantit que la
**seule** différence entre les deux évaluations vient des Assassins en attente — sans quoi le taux
mesuré mélangerait l'incohérence avec une divergence de calcul.

**Le relevé, et pourquoi il n'est pas une reconstruction.** Le moteur expose déjà
`assassins_en_attente()`. La trace l'enregistre à chaque nœud de ciblage, moins son premier élément
qui est l'Assassin courant. Reconstruire cette file depuis les blocs de pose aurait été une
hypothèse de plus à vérifier ; la relever du moteur n'en est pas une. Un test d'intégration sur
30 donnes réelles vérifie que la file décroît de un à chaque nœud consécutif — et **échoue si
aucun bloc à deux Assassins n'apparaît**, pour qu'il ne puisse pas passer en ne vérifiant rien.

Le décideur ne reçoit rien de tout cela : `Perception` est inchangée, et la preuve d'aveuglement
n'est pas touchée.

### Le 7,33 %, reproduit avec son intervalle

**Deux lectures, deux dénominateurs, et c'est le même piège que le défaut 1.** « X % des nœuds où
un Assassin reste en attente avec un argmax myope différent » admet deux lectures : la part parmi
les nœuds **à Assassin en attente**, ou la part parmi **tous** les nœuds de ciblage. Les deux sont
mesurées et publiées séparément, chacune avec son grain.

**Échantillon des 200 donnes autorisées** — ce sont les 200 **premières donnes de la campagne B**,
graines inchangées : mesurer sur d'autres graines aurait fabriqué une population de plus à auditer
pour rien. 600 parties, siège du greedy seul. IC de Clopper-Pearson **exacts** à 99 % bilatéral.

| Lecture | Mesuré | IC 99 % exact | Dénominateur |
|---|---:|---|---|
| parmi les nœuds à Assassin en attente | **3,66 %** (9/246) | **[1,29 % ; 7,95 %]** | 246 nœuds |
| dont l'argmax myope est cohéremment **dominé** | 2,85 % (7/246) | [0,83 % ; 6,82 %] | 246 nœuds |
| parmi **tous** les nœuds de ciblage | 0,62 % (9/1457) | [0,22 % ; 1,37 %] | 1 457 nœuds |

**Échantillon complet** — la campagne B entière, 10 002 parties, siège du greedy. Calculé sur les
traces déjà en mémoire pendant la génération du rapport : **aucune campagne n'est rejouée**. Le
dénominateur est multiplié par 16,5.

| Lecture | Mesuré | IC 99 % exact | Dénominateur |
|---|---:|---|---|
| parmi les nœuds à Assassin en attente | **4,23 %** (172/4063) | **[3,46 % ; 5,11 %]** | 4 063 nœuds |
| dont l'argmax myope est cohéremment **dominé** | 3,13 % (127/4063) | [2,47 % ; 3,90 %] | 4 063 nœuds |
| parmi **tous** les nœuds de ciblage | 0,72 % (172/23991) | [0,58 % ; 0,87 %] | 23 991 nœuds |

Les deux échantillons sont **emboîtés** — les 200 donnes sont le préfixe des 3 334 —, donc ils ne
constituent pas deux estimations indépendantes. Le second remplace le premier ; le premier reste
publié parce que la commande de re-vérification à 200 donnes est celle qui coûte une minute.

### Le résultat qui tient quel que soit le chiffre : les deux implémentations comptent le même dénominateur

L'intervalle de la seconde lecture, **[0,58 % ; 0,87 %]**, exclut 7,33 % d'un facteur **8,4** sur sa
borne haute. La lecture « parmi tous les nœuds de ciblage » est donc **écartée** : l'auditeur a
compté, comme moi, sur les nœuds **à Assassin en attente**. C'est ce que l'intervalle établit, et il
l'établissait déjà à 246 nœuds. **Ce résultat ne dépend pas de la valeur.**

### Le désaccord de valeur, et il ne se résout pas ici

**Les deux intervalles ne se recouvrent pas.** 7,33 % est hors de **[3,46 % ; 5,11 %]**, au-dessus
de la borne haute. Ce n'est ni un défaut de l'audit ni un défaut de mon compteur : c'est un
**désaccord de valeur entre deux implémentations qui comptent la même chose sur des échantillons
différents**.

| Source | Valeur | Échantillon | Intervalle |
|---|---:|---|---|
| audit croisé | **7,33 %** | **non connu de moi** | non publié |
| ce dépôt, 200 donnes | 3,66 % (9/246) | préfixe de la campagne B, 600 parties | [1,29 % ; 7,95 %] |
| ce dépôt, campagne B entière | **4,23 %** (172/4063) | campagne B, 10 002 parties | **[3,46 % ; 5,11 %]** |

**Aucune moyenne, aucune préférence, aucune explication inventée.** L'échantillon de l'auditeur ne
m'est pas connu : sans son numérateur et son dénominateur, la question n'est pas tranchable — c'est
le contrôle numéro 2 de son propre audit, *un chiffre porte son échantillon*, appliqué à son
chiffre. La boucle se ferme en le lui demandant, et ce n'est pas à moi de le faire.

**Et il faut lire la première annonce pour ce qu'elle disait.** À 246 nœuds les deux valeurs étaient
compatibles, et j'avais écrit que 7,33 % était près du bord haut de cet intervalle. Le resserrement
ne contredit pas cette phrase : il la **précise**. Un intervalle trop large pour trancher ne
concluait pas à la concordance des valeurs — il concluait à l'identité du dénominateur, et cette
conclusion-là tient.

---

## Défaut 4 — MINEUR, et il est de l'humain — deux compteurs aveugles, pas un

**Le défaut.** Le paragraphe du rapport sur l'absence de pouvoir discriminant ne traitait que
`B7-gaspillage`. `B7-gaspillage-vraie` l'est aussi : **0,35 %** d'écart détectable contre
**0,2050 %** de taux mesuré. Aucun agent ne sera jugé sur la vue de dieu, donc cela ne change
aucune conclusion — mais la phrase laissait croire que le cas était isolé, et c'était le propre
contrôle numéro 4 de l'humain.

**La correction : un critère calculé, pas une phrase corrigée.** Le §6 marque désormais
**mécaniquement** toute ligne dont l'écart détectable dépasse son propre taux, avec la mention
`(aveugle par le bas)` dans la cellule — un marqueur qui se lit sans légende — et un paragraphe qui
énonce le critère et **liste les compteurs marqués**, liste produite par le générateur.

Ce que « aveugle par le bas » signifie exactement : l'écart détectable dépassant le taux mesuré,
**aucun** agent ne peut être séparé du greedy par le bas sur ce compteur, **pas même un agent à
0 %**. Un compteur dont un côté entier est hors d'atteinte ne teste rien de ce côté-là.

Une prose se corrige une fois ; un critère calculé n'oublie pas la ligne suivante. C'est la même
forme de parade que la levée du défaut 1.

---

## La garde de composition, scindée — un défaut à part entière

**Le défaut.** `campagne_b` refusait `nb_greedys=3` en disant « la mesure n'a plus d'objet ». C'est
vrai de **M3** — trois politiques identiques rendent un tiers de part de victoire et un gain moyen
nul **par symétrie** — et faux de **M4**, où les compteurs de comportement gardent tout leur sens.
**La garde confondait une mesure avec une phase.**

**La correction.** Deux gardes, une par question :

- `campagne_b` ne juge plus que la **composition** : `1..3`, refus à 0 — pas de greedy à mesurer —
  et au-delà de 3 — pas assez de sièges.
- `mesurer_m3` refuse `nb_greedys=3`, avec la **raison** dans son message : la symétrie. Son
  paramètre `nb_greedys` est **obligatoire et sans défaut** — c'est la seule chose que `groupes` ne
  dit pas, et l'oublier ferait calculer M3 sur une population où il n'a pas d'objet sans que la
  garde s'en aperçoive.

**Un test par branche**, dans `tests/mesure/test_phase2.py` :

| Test | Branche |
|---|---|
| `test_la_campagne_b_refuse_une_composition_impossible` | 0, 4, −1 → lève |
| `test_la_campagne_b_accepte_trois_greedys_pour_m4` | 3 → passe, et les **trois** sièges sont mesurés |
| `test_m3_refuse_une_population_a_trois_greedys` | M3 à 3 → lève, message contenant « symétrie » |
| `test_m3_accepte_les_deux_compositions_qui_ont_un_objet` | M3 à 1 et à 2 → mesure |

---

## La troisième population — périmètre, et deux candidats nommés non ajoutés

**Pourquoi elle existe.** `B1-collectif` est le seul compteur dont le **numérateur peut être
produit entièrement par les adversaires** : sa bascule peut être l'action de n'importe qui. Mesuré
avec **un** greedy contre **deux aléatoires**, il mélange donc la bascule du greedy et celles de
deux politiques uniformes. Or la phase 3 fera jouer les trois sièges par des agents entraînés :
une ligne de base collective mesurée contre deux hasards **n'est pas la ligne de base de ce que la
phase 3 comparera**.

**Le périmètre publié, et rien de plus** : `B1-collectif`, sa variante `-par-partie`, et les quatre
autres lignes `-par-partie`. **Six lignes.** Partout ailleurs les chiffres restent ceux qui ont été
audités — trente-quatre lignes fois trois populations feraient cent-deux chiffres dont la plupart
ne répondraient à rien, et chacun serait une affirmation de plus à auditer.

**Deux réparations, deux raisons, et il ne faut pas les confondre** : la **composition des
adversaires** pour `B1-collectif`, le **grain** pour les `-par-partie`.

**Le critère du périmètre se décide sur le TEXTE de la définition, sans mesurer : la définition
nomme-t-elle un autre joueur ?** `B1-collectif` exige que `t₁` et `t₂` soient de joueurs
**différents** — le mot est dans la définition. `B4-tout-dos` dit « toutes les cibles sont des
dos », `B5-renfort` dit « renforcer un côté déjà favorable » : aucune des deux ne nomme personne.

**Le critère que j'avais proposé ne tenait pas, et l'humain l'a rejeté.** Je distinguais « les
adversaires produisent le numérateur » de « les adversaires façonnent le plateau ». C'est un
critère de **degré**, et un critère de degré au bord d'un périmètre dérive toujours vers
l'extérieur : le lecteur suivant ajouterait un compteur de plus avec une raison aussi bonne que la
mienne. Le plateau est façonné par les adversaires dans les **dix-sept** compteurs, donc il n'y a
pas d'arrêt après deux. Le critère textuel, lui, s'arrête où le texte s'arrête.

**`B4-tout-dos` et `B5-renfort` ne sont donc PAS ajoutés.** Leur dépendance à la composition est
réelle et n'est pas jetée : elle est portée à l'entrée de journal comme **question ouverte pour la
phase 3** — voir l'impact plan. Elle concerne la **lecture** de leurs taux par un agent entraîné,
pas le périmètre de cette table.

**Cette population n'a été auditée par personne.** Elle est écrite comme une première livraison,
pas comme un appendice, et l'humain l'ajoute à la liste de l'audit comme cinquième point.

---

## Ce que l'audit a établi et qui ne bouge plus

Consigné ici parce qu'un audit qui confirme est un résultat, pas un silence.

- **Rapport régénéré : 395 lignes sur 395 identiques.** Tous les chiffres se reconstruisent.
- **Trois concordances obtenues sans mon code** : `sigma(gain)` **0,6671** contre mon **0,6652** ;
  refus B4 **23,81 %** avec un IC 99 % [22,53 ; 25,12] qui contient mon **23,65 %** ; contraste
  apparié de siège **+0,181** contre mon **+0,189**.
- **Le résultat le plus important est confirmé** : avantage de siège **négligeable sous jeu
  aléatoire, massif sous jeu greedy**.
- **La preuve d'aveuglement est jugée plus forte que la sienne** — statique, dynamique avec
  `vue_privilegiee` piégée, différentielle, chacune assortie d'un test vérifiant que le piège mord.
  Cinq contrôles à lui, dont un balayage de 60 parties permutant l'identité de chaque dos à chaque
  nœud : **rien trouvé**. Le greedy ne triche pas.
- **La lecture « Indifférente ou en Obscurité » de la clause 3 est confirmée indépendamment.** Deux
  lectures séparées du même texte convergent — c'est le meilleur résultat de cet audit, et il vaut
  plus que le chiffre.
