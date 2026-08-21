# Phase 3 -- le premier agent entraine

Genere par `uv run python -m mesure.phase3_mesure`. Aucune interpretation : chaque chiffre porte sa decomposition, sa composition et son denominateur. Les seuils rappeles sont ceux de `mesure/phase3_hypothese_et_instrument.md`, commite **avant** l'entrainement.

Instance : `familles=4`, 5 roles, `exemplaires=2`, `joueurs=3` -- 40 cartes, 4 tours par joueur.

Algorithme : **PPO a masque d'actions**, reseau unique partage par les trois sieges, tete de valeur, `gamma = 1`, `lambda = 1`. Pool d'entrainement : 60 % copie courante, 40 % checkpoint fige. **Ni le greedy ni l'aleatoire n'entrent dans le pool.**

## 1. Le juge -- gain moyen contre deux greedys

**Composition : 1 agent entraine contre 2 greedys, sieges permutes.** 2000 donnes x 3 sieges = **6000 parties**. Bootstrap **par donne**, 10000 rechantillons.

**Le niveau nul du gain moyen est exactement 0,0000**, et il n'est pas estime : sous l'hypothese nulle, l'esperance du gain mesure vaut 0 par la somme nulle du paragraphe 5.2 et par la permutation systematique des sieges. Voir le paragraphe 1 de la pre-inscription.

| Grandeur | Valeur | Niveau nul |
|---|---:|---:|
| **Gain moyen** | **-0.1643** | **0,0000** (exact) |
| IC 99 % bootstrap par donne | [-0.1824 ; -0.1462] | |
| Part de victoire fractionnee | 22.38 % | 33.33 % (exact) |
| Part de victoire stricte | 16.87 % | **inconnu d'avance -- jamais un seuil** |

**Seuil du protocole : la borne basse de l'IC 99 % est-elle strictement positive ?** Elle vaut **-0.1824**. **NON.** La borne haute est negative : **l'agent est battu par le greedy**.

### Le gain par siege -- a cote de la moyenne, jamais a sa place

**L'avantage de siege est massif dans cette composition** : contraste apparie entre sieges extremes **+0,5735**, IC 99 % [+0,5218 ; +0,6240], mesure sur la population de l'hypothese nulle. Un chiffre d'un seul siege ne se compare **jamais** a un chiffre agrege sur trois.

| Siege occupe | Gain moyen de l'agent |
|---|---:|
| siege 0 | -0.3069 |
| siege 1 | -0.1998 |
| siege 2 | +0.0139 |

Somme des trois : **-0.4928**, soit **trois fois le gain moyen** (-0.1643 x 3 = -0.4928).

> **Ce n'est PAS un controle de nullite, et une premiere redaction de ce rapport le presentait comme tel.** Elle ecrivait « elle n'est nulle qu'a la precision d'echantillonnage », ce qui n'est vrai que **sous l'hypothese nulle**. Chaque siege portant le meme nombre de parties, la somme des trois moyennes vaut `3 x moyenne` **par identite arithmetique**, quel que soit l'agent : elle ne vaut zero que si le gain moyen vaut zero. Ce qui est nul par construction, c'est la somme des gains des **trois sieges d'une meme partie** -- invariant I5 --, et c'est verifie au paragraphe 6, partie par partie.

## 2. Le dimensionnement, remesure sur la composition reelle

La pre-inscription mesure `sigma` et `rho` **sous l'hypothese nulle** -- le greedy mis a la place de l'agent. Un agent different a une distribution de gain differente : l'ecart entre le **SUPPOSE** de la pre-inscription et le **MESURE** ci-dessous est un chiffre, et non un oubli.

| Grandeur | Pre-inscription (hypothese nulle) | Mesure ici |
|---|---:|---:|
| `sigma(gain)` | 0,6494 | **0.5710** |
| `rho` intra-donne | −0,1400 | **-0.0565** |
| effet de plan (analyse de variance) | 0,7200 | **0.8870** |
| effet de plan (bootstrap) | 0,7223 | **0.8817** |

**Ecart de gain detectable a ce budget** : **+0.0237** sur 6000 parties, 99 % bilateral et 80 % de puissance. La pre-inscription annoncait **+0,0243**.

**Demi-largeur de l'IC 99 % du gain** : **0.0181** sur 6000 parties.

> **Elle ne se compare pas telle quelle au 0,0183 de la pre-inscription**, et c'est la faute du projet appliquee a un budget plutot qu'a une population. Une demi-largeur depend de **deux** choses : `sigma`, propre a la composition, et `n`, propre au budget. Le 0,0183 est pre-inscrit **a 6 000 parties**. Le confronter a une demi-largeur mesuree sur un autre nombre de parties melangerait un effet de composition et un effet de budget.
>
> **Ce qui se compare est `sigma`**, qui ne depend pas de `n` : **0.5710** ici contre **0,6494** sous l'hypothese nulle, soit **-12.1 %**. `sigma` a bouge de plus de 10 % : la pre-inscription le donnait comme SUPPOSE, et il faut donc le dire ici plutot que de laisser le budget se lire comme s'il n'avait pas bouge.
>
> Pour memoire, la demi-largeur **ramenee a 6 000 parties** vaut `0.0181 x sqrt(6000 / 6000)` = **0.0181**, et c'est **cette** valeur qui se lit contre 0,0183. La conversion suppose que l'effet de plan est le meme aux deux tailles, ce qui est vrai a `rho` constant.

## 3. Le pool -- chaque composition, nommee

**Aucune de ces lignes n'est le juge.** Le juge est le gain moyen contre deux greedys, et lui seul. Les autres compositions repondent a d'autres questions.

| Composition | Parties | Gain moyen | IC 99 % | Part fractionnee | Neutre |
|---|---:|---:|---|---:|---:|
| 1 agent entraine contre 2 greedys, sieges permutes | 6000 | -0.1643 | [-0.1824 ; -0.1462] | 22.38 % | 33.33 % |
| 1 agent entraine contre 2 aleatoires (garde-fou) | 1500 | +0.5505 | [+0.5070 ; +0.5937] | 70.03 % | 33.33 % |
| 1 agent entraine, variante DETERMINISTE, contre 2 greedys (robustesse -- jamais a la place de la reference) | 6000 | -0.1679 | [-0.1855 ; -0.1503] | 22.14 % | 33.33 % |
| 1 agent entraine contre 2 copies de `checkpoint_01.pt` | 1500 | +0.2050 | [+0.1598 ; +0.2523] | 47.00 % | 33.33 % |
| 1 agent entraine contre 2 copies de `checkpoint_02.pt` | 1500 | +0.1957 | [+0.1482 ; +0.2433] | 46.38 % | 33.33 % |
| 1 agent entraine contre 2 copies de `checkpoint_03.pt` | 1500 | +0.1420 | [+0.0982 ; +0.1858] | 42.80 % | 33.33 % |
| 1 agent entraine contre 2 copies de `checkpoint_04.pt` | 1500 | +0.1232 | [+0.0812 ; +0.1665] | 41.54 % | 33.33 % |
| 1 agent entraine contre 2 copies de `checkpoint_05.pt` | 1500 | +0.0395 | [-0.0018 ; +0.0810] | 35.97 % | 33.33 % |
| 1 agent entraine contre 2 copies de `checkpoint_06.pt` | 1500 | +0.0227 | [-0.0198 ; +0.0648] | 34.84 % | 33.33 % |
| 1 agent entraine contre 2 copies de `checkpoint_07.pt` | 1500 | +0.0405 | [-0.0037 ; +0.0837] | 36.03 % | 33.33 % |
| 1 agent entraine contre 2 copies de `checkpoint_08.pt` | 1500 | +0.0225 | [-0.0173 ; +0.0635] | 34.83 % | 33.33 % |

### Ce que ces lignes disent, et ce qu'elles ne disent pas

La pre-inscription annonce, au paragraphe 6, que **« un agent qui ecrase ses propres checkpoints mais ne bat pas le greedy est le symptome exact de l'effondrement de convention en self-play »**. C'est la contrepartie assumee d'avoir sorti le greedy du pool d'entrainement.

**Confrontee aux chiffres, cette phrase ne s'applique qu'a moitie, et il faut le dire plutot que de la laisser conclure a notre place.**

- l'agent bat son **premier** checkpoint de **+0.2050** -- un ecart reel, mais sur un adversaire vieux de quinze minutes ;
- il bat son **dernier** de **+0.0225**, IC 99 % [-0.0173 ; +0.0635], **qui contient zero** : sur les quinze dernieres minutes, l'amelioration contre lui-meme n'est **pas etablie** a ce budget.

**« Ecraser » ne decrit donc pas ce qui est mesure.** La marge sur un checkpoint decroit a mesure que le checkpoint se rapproche de l'agent final, ce qui est attendu et ne prouve rien a soi seul : un checkpoint recent est un adversaire plus fort. Ce que ces lignes etablissent est plus etroit -- **l'agent a progresse contre lui-meme sur la duree du run**, et cette progression n'a pas suffi a atteindre le greedy.

**Ce qu'elles n'etablissent PAS** : qu'une convention de self-play soit la cause. Une convention stable et un apprentissage inacheve produisent tous deux un agent qui bat ses anciennes versions sans battre un adversaire exterieur. **Rien ici ne separe les deux hypotheses**, et il faudrait pour cela une population que cette phase n'a pas mesuree -- par exemple un second agent entraine depuis une autre graine, qui n'aurait aucune raison de partager la convention du premier.

### La variante deterministe -- rapportee a cote, jamais a la place

**Une mesure de consequence, et elle ne se lit qu'en juxtaposant les deux nombres** -- c'est la meme forme qu'en phase 2 pour le departage du greedy, et la meme raison : un renvoi vers une autre section ne se lit pas.

| | |
|---|---:|
| gain moyen, agent echantillonne (reference) | **-0.1643** |
| gain moyen, agent deterministe | **-0.1679** |
| ecart | **-0.0036** |
| demi-largeur de l'IC 99 % de la reference | 0.0181 |
| l'ecart, en demi-largeurs | **0.20** |

**Autrement dit : prendre l'action la plus probable plutot que d'echantillonner ne deplace pas le gain de l'agent a ce budget.** L'entropie de sa politique est basse -- 0,34 au dernier checkpoint --, donc les deux departages tirent le plus souvent la meme action, et ce chiffre le confirme plutot que de le supposer.

**Ce que ce chiffre n'etablit pas** : que la variante deterministe soit une bonne politique. Elle est **biaisee** -- l'indice d'une action de pose encode l'assignation, la position au banquet et l'adversaire vise --, et son seul usage est d'etre rapportee ici.

## 4. Le garde-fou -- un agent contre deux aleatoires

**Ce n'est pas un juge.** Depasser 86,52 % ne dit rien sur le fait de battre le greedy : le greedy y est deja. C'est un detecteur d'agent qui n'apprend pas.

Le **86,52 %** est une **moyenne sur les trois sieges**, agregee sur les 10 002 parties de la campagne B de la phase 2, et il ne se compare qu'a une mesure agregee de la meme facon. La colonne ci-dessous l'est.

Chaque checkpoint : 600 donnes x 3 sieges. IC corrige de **Bonferroni pour 8 regards**.

| # | s | Parties d'entrainement | Entropie | Part fractionnee | IC (Bonferroni) | Gain moyen |
|---:|---:|---:|---:|---:|---|---:|
| 1 | 902 | 185344 | 0.4726 | 57.33 % | [53.92 % ; 60.85 %] | +0.3600 |
| 2 | 1800 | 380928 | 0.3515 | 59.52 % | [55.92 % ; 63.20 %] | +0.3928 |
| 3 | 2701 | 564736 | 0.3811 | 61.77 % | [58.21 % ; 65.06 %] | +0.4265 |
| 4 | 3601 | 751104 | 0.3909 | 63.22 % | [59.90 % ; 66.61 %] | +0.4483 |
| 5 | 4501 | 935424 | 0.3435 | 65.06 % | [61.77 % ; 68.31 %] | +0.4758 |
| 6 | 5402 | 1119744 | 0.3428 | 67.56 % | [64.17 % ; 70.77 %] | +0.5133 |
| 7 | 6302 | 1303552 | 0.3091 | 69.27 % | [66.14 % ; 72.53 %] | +0.5390 |
| 8 | 7201 | 1486336 | 0.3370 | 70.13 % | [67.05 % ; 73.19 %] | +0.5519 |

**Critere terminal du protocole** : au dernier checkpoint, la part fractionnee vaut **70.13 %** contre **86,52 %**. **NON franchi.**

**Arret anticipe** : non declenche : la condition de stagnation n'a jamais ete remplie.

> **Le critere terminal n'est pas franchi, et la raison que le protocole lui prete est FAUSSE ici. C'est un resultat sur le protocole, pas sur l'agent.**
>
> Le protocole ecrit : « si apres 2 h l'agent n'a pas depasse 86,52 %, on arrete : **l'agent n'apprend pas**, et rallonger ne dira rien de plus ». La premisse est verifiable, et elle est contredite par la colonne ci-dessus : la part fractionnee **croit a chaque checkpoint sans exception**, de **57.33 %** a **70.13 %** sur 8 mesures, et l'agent progressait encore au dernier.
>
> Ce n'est donc pas un agent qui n'apprend pas : c'est un agent qui **n'a pas fini d'apprendre** dans le budget de 2 h. Le seuil de 86,52 % est le niveau du greedy, et rien ne disait qu'il serait atteint en 2 h -- le protocole le posait comme detecteur de panne, et il fonctionne ici comme mesure de distance restante.
>
> **La distinction n'est pas rhetorique** : les deux lectures menent a des decisions opposees. « L'agent n'apprend pas » conduit a changer de methode ; « l'agent n'a pas fini » conduit a rallonger le budget, qui est le levier 1 de la phase 4. Le rapport ne tranche pas -- il etablit que la premisse du protocole ne tient pas, et remonte l'arbitrage.

## 5. Les comportements B1 a B7

**La ligne de base est REGENEREE**, et ce n'est pas une commodite : ma composition est un agent contre deux greedys, un seul siege mesure. Sa ligne de base est donc **trois greedys, UN seul siege compte**, et elle n'existe pas dans le depot. Memes seeds, meme composition, meme decalage de graine `6000000` : seuls les sieges **comptes** changent.

`comportements.ecart_de_taux` **leve** si les grains different. Elle est appelee plutot que contournee : une ligne dont le grain differe fait tomber la mesure au lieu de produire un nombre qu'il faudrait relire.

**Les exclusions sont recalculees au budget de 6000 parties**, jamais recopiees : ce sont des proprietes du couple `(ligne, budget)`. Voir `mesure/phase3_budget_des_comportements.py`.

| Compteur | Agent | Ligne de base | Ecart | Detectable | Separable ? |
|---|---|---|---:|---:|---|
> **Les lignes `-par-partie` portent ici les MEMES nombres que leur ligne au grain du couple, et ce n'est pas un defaut.** Un seul siege est mesure par partie, donc « au moins un des 1 sieges » et « le siege mesure » comptent exactement la meme chose. C'est deja le cas de la colonne a un siege de la phase 2. Les deux sont gardees pour que le grain reste lisible dans le libelle, et parce que `ecart_de_taux` leve si on les compare a une population qui en agrege trois.

| `B1-collectif` | 70.37 % (4222/6000) | 72.20 % (4332/6000) | -1.83 pt | 2.85 % | non separable a ce budget |
| `B1-collectif-par-partie` | 70.37 % (4222/6000) | 72.20 % (4332/6000) | -1.83 pt | 2.85 % | non separable a ce budget |
| `B1-motif` | 42.48 % (2549/6000) | 45.83 % (2750/6000) | -3.35 pt | 3.08 % | **separable** |
| `B1-motif-par-partie` | 42.48 % (2549/6000) | 45.83 % (2750/6000) | -3.35 pt | 3.08 % | **separable** |
| `B1-savoir-commun` | 43.13 % (2588/6000) | 46.28 % (2777/6000) | -3.15 pt | 3.09 % | **separable** |
| `B1-savoir-commun-par-partie` | 43.13 % (2588/6000) | 46.28 % (2777/6000) | -3.15 pt | 3.09 % | **separable** |
| `B1-strict` | 28.05 % (1683/6000) | 28.53 % (1712/6000) | -0.48 pt | 2.80 % | non separable a ce budget |
| `B1-strict-par-partie` | 28.05 % (1683/6000) | 28.53 % (1712/6000) | -0.48 pt | 2.80 % | non separable a ce budget |
| `B1-tentative` | 55.53 % (3332/6000) | 61.28 % (3677/6000) | -5.75 pt | 3.10 % | **separable** |
| `B1-tentative-par-partie` | 55.53 % (3332/6000) | 61.28 % (3677/6000) | -5.75 pt | 3.10 % | **separable** |
| `B2-banquet` | 30.56 % (4383/14340) | 36.70 % (5284/14399) | -6.13 pt | 1.86 % | **separable** |
| `B2-cibles` | 79.18 % (11354/14340) | 82.65 % (11901/14399) | -3.47 pt | 1.64 % | **separable** |
| `B2-contestee` | 68.36 % (9803/14340) | 74.26 % (10692/14399) | -5.89 pt | 1.88 % | **separable** |
| `B2-contestee-publique` | 66.40 % (9522/14340) | 72.55 % (10447/14399) | -6.15 pt | 1.91 % | **separable** |
| `B2-destination/banquet-Disgrace` | 18.15 % (2602/14340) | 15.76 % (2270/14399) | +2.38 pt | 1.56 % | **separable** |
| `B2-destination/banquet-Estime` | 12.42 % (1781/14340) | 20.93 % (3014/14399) | -8.51 pt | 1.33 % | **separable** |
| `B2-destination/domaine adverse` | 32.74 % (4695/14340) | 35.41 % (5099/14399) | -2.67 pt | 1.89 % | **separable** |
| `B2-destination/domaine propre` | 36.69 % (5262/14340) | 27.89 % (4016/14399) | +8.80 pt | 1.95 % | **separable** |
| `B2-fragile-2` | 77.11 % (11057/14340) | 81.81 % (11780/14399) | -4.71 pt | 1.70 % | **separable** |
| `B3-expose` | 43.92 % (10542/24000) | 41.25 % (9899/24000) | +2.68 pt | 1.55 % | **separable** |
| `B3-expose-vraie` | 48.80 % (11712/24000) | 46.48 % (11156/24000) | +2.32 pt | 1.56 % | **separable** |
| `B3-simultane` | 6.73 % (1615/24000) | 9.60 % (2304/24000) | -2.87 pt | 0.78 % | **separable** |
| `B4-brut` | 31.93 % (3814/11945) | 15.93 % (1967/12349) | +16.00 pt | 2.06 % | **separable** |
| `B4-contre-nature` | 35.87 % (1368/3814) | 0.00 % (0/1967) | +35.87 pt | 3.75 % | **separable** |
| `B4-departage` | 53.88 % (2055/3814) | 68.38 % (1345/1967) | -14.50 pt | 3.90 % | **separable** |
| `B4-meurtre-couteux` | 3.66 % (298/8131) | 0.00 % (0/10382) | +3.66 pt | 1.01 % | **separable** |
| `B4-strict` | 10.25 % (391/3814) | 31.62 % (622/1967) | -21.37 pt | 2.37 % | **separable** |
| `B4-tout-dos` | 4.95 % (591/11945) | 3.63 % (448/12349) | +1.32 pt | 0.96 % | **non compare** : texte de la definition : elle ne nomme aucun autre joueur |
| `B5-pire-cas` | 18.52 % (1647/8893) | 13.44 % (1219/9068) | +5.08 pt | 1.99 % | **separable** |
| `B5-renfort` | 18.23 % (2270/12454) | 13.27 % (1746/13159) | +4.96 pt | 1.67 % | **non compare** : texte de la definition : elle ne nomme aucun autre joueur |
| `B7-gaspillage` | 0.10 % (24/24000) | 0.08 % (19/24000) | +0.02 pt | 0.10 % | non separable a ce budget |
| `B7-gaspillage-vraie` | 0.13 % (32/24000) | 0.10 % (24/24000) | +0.03 pt | 0.11 % | non separable a ce budget |
| `B7-lumiere` | 10.27 % (2464/24000) | 9.60 % (2304/24000) | +0.67 pt | 0.95 % | non separable a ce budget |
| `B7-occasions` | 0.81 % (195/24000) | 0.62 % (148/24000) | +0.20 pt | 0.28 % | non separable a ce budget |

## 6. B4 -- le piege de lecture, et pourquoi je refuse la lecture flatteuse

**Quatre compteurs de B4 sont definis par rapport a `greedy.evaluer_actions`**, c'est-a-dire par l'evaluation **myope** du greedy lui-meme -- `B4-strict`, `B4-departage`, `B4-contre-nature` et `B4-meurtre-couteux`. Chez le greedy leur valeur est **tautologique** : `choisir` prend un argmax, donc il ne peut pas se contredire. Les deux zeros absolus de la phase 2 sont dans ce lot.

**Chez un agent dont l'argmax n'est pas celui de l'etalon, ces compteurs cessent d'etre tautologiques.** Ils mesurent alors une chose et une seule : **a quelle frequence l'agent contredit l'evaluation myope du greedy.**

| Compteur | Agent | Ligne de base (3 greedys) | Ce que l'ecart mesure |
|---|---|---|---|
| `B4-contre-nature` | 35.87 % (1368/3814) | 0.00 % (0/1967) | desaccord avec l'evaluation myope |
| `B4-meurtre-couteux` | 3.66 % (298/8131) | 0.00 % (0/10382) | desaccord avec l'evaluation myope |
| `B4-brut` | 31.93 % (3814/11945) | 15.93 % (1967/12349) | desaccord avec l'evaluation myope |
| `B4-strict` | 10.25 % (391/3814) | 31.62 % (622/1967) | desaccord avec l'evaluation myope |

### La lecture que la phase 2 propose, et pourquoi elle ne tient pas ici

Le rapport de la phase 2 ecrit : « pour un agent de la phase 3, ce meme zero cesse d'etre tautologique : son argmax n'est pas celui de l'etalon, donc `B4-contre-nature` devient un vrai diagnostic -- et **un refus par anticipation d'un retournement y comptera, ce qui se lit comme un signe de planification** et non comme un defaut ».

**Je refuse cette lecture pour cet agent, et le motif est dans le paragraphe 1.** `B4-contre-nature` vaut **35.87 %** chez lui contre **0,00 %** chez le greedy. Deux hypotheses expliquent le meme chiffre :

1. **l'agent voit quelque chose que l'evaluation myope ne voit pas** -- il refuse un meurtre localement gagnant parce qu'il anticipe un retournement. C'est la lecture flatteuse ;
2. **l'agent joue moins bien** -- il refuse des meurtres qu'il aurait fallu commettre.

**Les deux produisent exactement le meme compteur.** Ce qui les separe n'est pas dans B4, il est dans le juge : **l'agent est battu par le greedy**, gain moyen negatif borne haute comprise. Un agent qui contredit massivement l'evaluation d'un adversaire qui le bat n'a pas etabli qu'il voit plus loin ; il a etabli qu'il decide autrement. La seconde hypothese est la plus economique, et rien ici ne la refute.

**Ce que ce compteur etablit, mot pour mot** : l'agent contredit l'evaluation myope du greedy a cette frequence. **Il n'etablit ni planification, ni erreur** -- il faudrait pour trancher une evaluation de reference qui ne soit ni myope ni celle de l'agent, et cette phase n'en a pas.

La meme reserve vaut pour `B4-meurtre-couteux`, `B4-strict` et `B4-departage`, dont les denominateurs sortent du meme argmax.

## 7. L'audit de ce resultat, par ses propres controles

**Ces controles sont ecrits et commites AVANT que l'agent ne soit mesure** -- `mesure/phase3_audit.py`. Un controle ecrit apres avoir vu un chiffre est un controle que le chiffre a passe par construction.

Ils portent sur des **unites**, des **denominateurs** et des **populations**, jamais sur des valeurs : reproduire un nombre ne le valide pas, et un facteur trois indu a survecu a deux verifications reussies en phase 2 pour cette raison.

| Question | Controle | Verdict | Preuve |
|---|---|---|---|
| Q1 | le niveau nul du juge, recalibre sur les seeds du verdict | concluant | gain moyen +0.0062, IC 99 % [-0.0124 ; +0.0255] sur 6000 parties, seeds 60000-61999 |
| Q1 | la somme des gains vaut 0 dans chaque partie (I5, paragraphe 5.2) | concluant | ecart maximal a zero : 0.000e+00 sur 6000 parties de « 1 agent entraine contre 2 greedys, sieges permutes » |
| Q2 | chaque siege exactement une fois par donne | concluant | 2000 donnes verifiees, 0 desequilibrees |
| Q2 | le bootstrap tire des donnes -- deux routes vers l'effet de plan concordent | concluant | effet bootstrap 0.8817, effet par analyse de variance 0.8870 ; un bootstrap qui tirerait des parties rendrait 1,0000 |
| Q3 | les plages de donnes ne se chevauchent pas | concluant | dimensionnement [20000, 22000); entrainement [100000, 1586336); garde-fou [40000, 40600); pool aleatoire [70000, 70500); pool checkpoint 1 [80000, 80500); pool checkpoint 2 [81000, 81500); pool checkpoint 3 [82000, 82500); pool checkpoint 4 [83000, 83500); pool checkpoint 5 [84000, 84500); pool checkpoint 6 [85000, 85500); pool checkpoint 7 [86000, 86500); pool checkpoint 8 [87000, 87500); variante deterministe [90000, 92000); verdict [60000, 62000) ; disjointes |
| R1 | le denominateur du verdict est `donnes x sieges` | concluant | 2000 donnes x 3 sieges = 6000, rapporte : 6000 |
| R2 | chaque composition est nommee, et les noms sont distincts | concluant | 11 compositions, 11 noms distincts |
| R3 | les lignes comparees sont au meme grain | concluant | 32 lignes comparees sur 34, 0 a grains differents |
| R4 | les zeros et les cent pour cent sont listes pour traitement individuel | concluant | 0 valeur(s) extreme(s) chez l'agent -- aucune |
| R5 | l'unite -- observations par partie -- coincide, numerateurs non regardes | concluant | 5 compteur(s) dont l'unite differe de plus de 5 % : B4-contre-nature 0.636 vs 0.328, B4-departage 0.636 vs 0.328, B4-meurtre-couteux 1.355 vs 1.730, B4-strict 0.636 vs 0.328, B5-renfort 2.076 vs 2.193. Un ecart n'est pas fautif en soi -- un denominateur d'action depend de la politique -- mais il doit etre lu avant de comparer les taux. |

**10 controles, aucun en echec.**

## 8. Ce que ces chiffres n'etablissent PAS

**Ecrit avant la mesure**, paragraphe 10 de la pre-inscription.

1. **B1 et B3 mesurent la frequence a laquelle un MOTIF apparait, jamais une planification.** Ecrire « l'agent planifie des retournements dans X % des parties » serait faux quel que soit X. Le chiffre s'intitule *frequence du motif*, jamais *frequence de planification*.
2. **B1 est plafonne par les 7,40 % de parties portant une perte d'acquis qu'aucun siege ne pouvait voir**, mesures en phase 1. Ces retournements sont **invulnerables a toute planification, par n'importe quel agent** : c'est un plafond du mesurable, pas un defaut d'agent.
3. **Battre le greedy ne dit pas que l'agent est fort.** Le greedy a un horizon d'un tour, et son gain publie est un **plancher** de lui-meme -- son ciblage est plus myope que sa specification. Aucun chiffre ici ne borne la distance entre l'agent et un bon joueur.
4. **Rien ici ne se transporte a `complet-3j`** -- 6 familles, 90 cartes, 10 tours.
5. **Le controle de collision de tenseurs est un echantillon, pas une preuve d'injectivite.**
6. **Aucun resultat de cette phase ne valide le moteur.** Elle le suppose conforme ; c'est la phase 0 qui l'etablit, et elle est close.
7. **B7 devient separable par le bas a ce budget, il ne devient pas informatif.** `B7-occasions` vaut 1,22 % des poses au banquet : l'occasion de se manifester est rare, et un taux bas se lit sur ce fond-la.

## 9. Duree machine -- 4 passe(s)

**4 passes**, etendue publiee. Le temps mural mesure l'etat de la machine, pas le cout du code : le rapport max/min ci-dessous est a lire comme tel, et non comme une variation du programme.

| Etape | Minimum | Maximum | Rapport max/min |
|---|---:|---:|---:|
| 1 agent contre 2 greedys | 82.2 s | 86.2 s | 1.05 |
| 1 agent contre 2 aleatoires | 16.1 s | 16.7 s | 1.04 |
| 1 agent DETERMINISTE contre 2 greedys | 82.8 s | 85.6 s | 1.03 |
| 1 agent contre 2 x checkpoint_01.pt | 18.8 s | 19.5 s | 1.04 |
| 1 agent contre 2 x checkpoint_02.pt | 21.5 s | 22.2 s | 1.03 |
| 1 agent contre 2 x checkpoint_03.pt | 19.1 s | 19.6 s | 1.03 |
| 1 agent contre 2 x checkpoint_04.pt | 19.1 s | 20.1 s | 1.05 |
| 1 agent contre 2 x checkpoint_05.pt | 22.3 s | 23.0 s | 1.03 |
| 1 agent contre 2 x checkpoint_06.pt | 19.1 s | 19.7 s | 1.03 |
| 1 agent contre 2 x checkpoint_07.pt | 18.9 s | 19.4 s | 1.03 |
| 1 agent contre 2 x checkpoint_08.pt | 18.9 s | 19.5 s | 1.03 |
| ligne de base : 3 greedys, 1 siege compte | 74.0 s | 74.9 s | 1.01 |
| auto-audit | 82.3 s | 82.4 s | 1.00 |

Total par passe : 505.4 s, 504.9 s, 499.4 s, 502.2 s -- etendue 499.4-505.4 s, rapport 1.01.
