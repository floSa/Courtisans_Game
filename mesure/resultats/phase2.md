# Phase 2 -- les quatre mesures

Genere par `uv run python -m mesure.phase2`. Aucune interpretation : chaque chiffre porte sa decomposition. Les seuils rappeles sont ceux de `mesure/phase2_hypothese_et_instrument.md`, commites **avant** la mesure.

## 1. Ce qui a ete joue

Instance : `familles=4`, 5 roles, `exemplaires=2`, `joueurs=3` -- 40 cartes, 4 tours par joueur.

| Campagne | Composition | Donnes | Parties | Seeds de donne | Alea de politique |
|---|---|---:|---:|---|---|
| A | trois aleatoires | 1667 x 6 replicats | **10002** | 0 a 1666 | `Random(2000000 + 6 x donne + replicat)` |
| A controle | trois aleatoires | 1667 x 6 | **10002** | 10000 a 11666 | idem |
| B | 1 greedy, 2 aleatoires | 3334 x 3 sieges | **10002** | 0 a 3333 | `Random(3000000 + 3 x donne + siege)` |

Bootstrap : **par donne**, 10000 rechantillons, `Random(2500000)`. Chaque donne entre avec **tous** ses replicats : tirer des parties detruirait la structure qu'on mesure.

## 2. M1 -- avantage de siege (seeds 0+)

**Deux niveaux neutres, et ils ne sont pas les memes.** `0,0000` pour le gain moyen `returns()` -- exact, par la somme nulle du paragraphe 5.2, tenue par l'invariant I5. `33,33 %` pour la part de victoire fractionnee -- exact aussi, les parts `1/k` sommant a 1 sur les sieges a chaque partie. Un siege a `+0,05` de gain n'est pas mediocre ; un siege a `0,05` de part de victoire le serait.

### Gain moyen `returns()` -- niveau neutre **0,0000**

| Siege | Moyenne | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |
|---|---:|---|---:|---:|---:|---:|
| siege 0 | +0.0013 | [-0.0155 ; +0.0192] | +0.0067 | +0.0069 | 1.068 | 9363 |
| siege 1 | +0.0025 | [-0.0143 ; +0.0201] | +0.0067 | +0.0066 | 0.997 | 10032 |
| siege 2 | -0.0038 | [-0.0210 ; +0.0132] | +0.0066 | +0.0068 | 1.035 | 9666 |

Controle de somme nulle sur les moyennes : **+0.00e+00**, soit zero a la precision machine.

### Part de victoire fractionnee -- niveau neutre **33,3333 %**

| Siege | Part | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |
|---|---:|---|---:|---:|---:|---:|
| siege 0 | 33.42 % | [32.25 % ; 34.58 %] | 0.44 % | 0.46 % | 1.058 | 9457 |
| siege 1 | 33.50 % | [32.36 % ; 34.68 %] | 0.44 % | 0.45 % | 1.021 | 9796 |
| siege 2 | 33.08 % | [31.93 % ; 34.26 %] | 0.44 % | 0.45 % | 1.049 | 9538 |

Controle : les trois parts somment a **1.000000**, soit 1 exactement.

### Part de victoire stricte -- niveau neutre **inconnu d'avance**

Elle vaut `(1 - P(ex aequo)) / 3` et **ne peut donc pas servir de seuil**. Rapportee parce que c'est la lecture spontanee de « gagner une partie ».

| Siege | Part stricte |
|---|---:|
| siege 0 | 28.52 % |
| siege 1 | 28.45 % |
| siege 2 | 28.19 % |

### Les trois seuils, et ce que le resultat en dit

| Seuil | Valeur | Origine | Franchi ? |
|---|---:|---|---|
| protocole | 38.00 % | paragraphe 3 du protocole, phase 2 | non |
| detection 99 % | 34.55 % | bilateral, non corrige | non |
| detection 99 % Bonferroni | 34.72 % | corrige pour 3 sieges | non |

Le siege le plus favorise est le **siege 1**, a 33.50 %, soit **+0.35 erreurs-type** de l'attendu (calcul iid a n = 10002).

**Puissance de cette mesure**, ecrite a cote du resultat pour qu'une absence de detection ne se lise pas comme une absence d'effet :

| Ecart vrai | Parties pour 80 % (exact stable) | Puissance exacte a n = 10002 |
|---|---:|---:|
| un siege a 38.00 % | 1531 (premier franchissement 1501) | 100.0 % |
| un siege a 35.00 % | 11629 (premier franchissement 11539) | 71.5 % |

## 2. M1 -- avantage de siege (bloc de controle, seeds 10000+)

**Deux niveaux neutres, et ils ne sont pas les memes.** `0,0000` pour le gain moyen `returns()` -- exact, par la somme nulle du paragraphe 5.2, tenue par l'invariant I5. `33,33 %` pour la part de victoire fractionnee -- exact aussi, les parts `1/k` sommant a 1 sur les sieges a chaque partie. Un siege a `+0,05` de gain n'est pas mediocre ; un siege a `0,05` de part de victoire le serait.

### Gain moyen `returns()` -- niveau neutre **0,0000**

| Siege | Moyenne | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |
|---|---:|---|---:|---:|---:|---:|
| siege 0 | +0.0109 | [-0.0060 ; +0.0282] | +0.0067 | +0.0067 | 1.004 | 9960 |
| siege 1 | -0.0059 | [-0.0223 ; +0.0117] | +0.0066 | +0.0066 | 0.980 | 10203 |
| siege 2 | -0.0050 | [-0.0220 ; +0.0118] | +0.0066 | +0.0066 | 0.999 | 10012 |

Controle de somme nulle sur les moyennes : **+8.67e-19**, soit zero a la precision machine.

### Part de victoire fractionnee -- niveau neutre **33,3333 %**

| Siege | Part | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |
|---|---:|---|---:|---:|---:|---:|
| siege 0 | 34.06 % | [32.91 % ; 35.17 %] | 0.44 % | 0.45 % | 1.005 | 9952 |
| siege 1 | 32.94 % | [31.78 % ; 34.07 %] | 0.44 % | 0.44 % | 1.001 | 9996 |
| siege 2 | 33.00 % | [31.86 % ; 34.16 %] | 0.44 % | 0.44 % | 0.986 | 10144 |

Controle : les trois parts somment a **1.000000**, soit 1 exactement.

### Part de victoire stricte -- niveau neutre **inconnu d'avance**

Elle vaut `(1 - P(ex aequo)) / 3` et **ne peut donc pas servir de seuil**. Rapportee parce que c'est la lecture spontanee de « gagner une partie ».

| Siege | Part stricte |
|---|---:|
| siege 0 | 28.72 % |
| siege 1 | 27.85 % |
| siege 2 | 27.81 % |

### Les trois seuils, et ce que le resultat en dit

| Seuil | Valeur | Origine | Franchi ? |
|---|---:|---|---|
| protocole | 38.00 % | paragraphe 3 du protocole, phase 2 | non |
| detection 99 % | 34.55 % | bilateral, non corrige | non |
| detection 99 % Bonferroni | 34.72 % | corrige pour 3 sieges | non |

Le siege le plus favorise est le **siege 0**, a 34.06 %, soit **+1.54 erreurs-type** de l'attendu (calcul iid a n = 10002).

**Puissance de cette mesure**, ecrite a cote du resultat pour qu'une absence de detection ne se lise pas comme une absence d'effet :

| Ecart vrai | Parties pour 80 % (exact stable) | Puissance exacte a n = 10002 |
|---|---:|---:|
| un siege a 38.00 % | 1531 (premier franchissement 1501) | 100.0 % |
| un siege a 35.00 % | 11629 (premier franchissement 11539) | 71.5 % |

## 3. M2 -- variance du score final

Sur 10002 parties de la campagne A, soit 30006 scores.

| Grandeur | Valeur |
|---|---|
| Ecart-type du score, par siege | 4.419 / 4.402 / 4.413 |
| Ecart-type du score, sieges confondus | **4.412** |
| Ecart-type du gain `returns()` | **0.6652** |
| Valeurs de score distinctes, par siege | 29 / 29 / 29 |
| Part de la valeur modale, par siege | 8.60 % / 8.92 % / 8.61 % |
| Parties a trois ex aequo | 1.55 % |

La precision de l'ecart-type a cette taille est de **0.707 % relatif** (`1 / sqrt(2n)`), et 5 % relatif sont atteints des 200 parties. **M2 est donc decide bien avant la fin de la campagne** : son contenu reel est la correlation intra-donne et le tableau ci-dessous.

### Correlation intra-donne -- le cinquieme trou du protocole

Le paragraphe 1 du protocole affirme que l'appariement « divise par cinq a dix » le nombre de parties necessaires, ce qui implique `rho` dans `[0,80 ; 0,90]`. **Aucune mesure du depot ne l'appuyait.** Voici la mesure.

| Grandeur | Siege 0 | Siege 1 | Siege 2 |
|---|---:|---:|---:|
| `rho` sur le score | -0.0049 | -0.0032 | +0.0031 |
| `rho` sur le gain | +0.0123 | +0.0007 | +0.0068 |

`rho` moyen sur le gain : **+0.0066**, soit un facteur de gain de **1.01** contre les 5 a 10 annonces.

**Ce que ce chiffre dit, et ce qu'il ne dit pas.** Il est mesure **sous jeu uniformement aleatoire**, ou l'alea de la politique domine tout : la donne n'explique que 0.66 % de la variance du gain. Sous cette politique-la, l'appariement ne rapporte rien.

Il ne **refute pas** l'affirmation du protocole, qui porte sur la comparaison de deux agents *differents* sur la meme donne. Il l'**infirme pour les deux politiques mesurees ici** -- voir aussi l'effet de plan du greedy en section 4, qui vaut ~0,94, soit un gain de 6 % et non un facteur 5 a 10. L'affirmation reste donc **non appuyee**, et c'est a ce titre qu'elle remonte comme cinquieme trou du protocole : pas comme une erreur etablie, comme un chiffre publie sans mesure.

### Le tableau de dimensionnement -- le produit livre de M2

Pour chaque ecart de gain moyen qu'on voudrait etablir, les parties necessaires a 99 % bilateral et 80 % de puissance, avec `sigma = 0.6652` mesure et `rho = 0.0066` mesure.

| Ecart de gain moyen | Sans appariement | Avec appariement |
|---|---:|---:|
| +0.02 | 25838 | 25668 |
| +0.05 | 4134 | 4107 |
| +0.10 | 1034 | 1027 |
| +0.20 | 259 | 257 |
| +0.30 | 115 | 115 |

**Lecture inverse, pour la phase 3** : a 1 000 parties appariees -- le budget que le paragraphe 3 du protocole lui fixe --, l'ecart de gain moyen detectable est **+0.1013**. C'est le chiffre qui dira si son seuil de « > 55 % contre le greedy » est atteignable a ce budget.

## 4. M3 -- winrate du greedy contre l'aleatoire

**Les deux niveaux neutres, a nouveau, parce que c'est ici que la confusion coute le plus cher.** `0,0000` pour le gain moyen, `33,3333 %` pour la part de victoire fractionnee. Le chiffre de reference du protocole -- « si le greedy est a 60 % » -- est une part de victoire, et son point de comparaison est **33,33 %, pas 50 %** : a trois joueurs, 50 % est deja une domination.

### Gain moyen `returns()` -- niveau neutre **0,0000**

| Mesure | Moyenne | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |
|---|---:|---|---:|---:|---:|---:|
| 1 greedy contre 2 aleatoires (reference) | +0.7978 | [+0.7857 ; +0.8101] | +0.0048 | +0.0047 | 0.946 | 10571 |
| 2 greedys contre 1 aleatoire | +0.2010 | [+0.1967 ; +0.2051] | +0.0016 | +0.0016 | 0.998 | 10024 |
| 1 greedy, departage deterministe | +0.7989 | [+0.7860 ; +0.8112] | +0.0048 | +0.0048 | 0.985 | 10150 |

### Part de victoire fractionnee -- niveau neutre **33,3333 %**

| Mesure | Part | IC 99 % bootstrap | ET iid | ET boot | Effet | n eff. |
|---|---:|---|---:|---:|---:|---:|
| 1 greedy contre 2 aleatoires (reference) | 86.52 % | [85.70 % ; 87.31 %] | 0.32 % | 0.31 % | 0.946 | 10575 |
| 2 greedys contre 1 aleatoire | 46.73 % | [46.44 % ; 47.02 %] | 0.11 % | 0.11 % | 1.002 | 9980 |
| 1 greedy, departage deterministe | 86.60 % | [85.77 % ; 87.40 %] | 0.32 % | 0.31 % | 0.957 | 10446 |

| Mesure | Part stricte | Parties |
|---|---:|---:|
| 1 greedy contre 2 aleatoires (reference) | 83.78 % | 10002 |
| 2 greedys contre 1 aleatoire | 41.11 % | 10002 |
| 1 greedy, departage deterministe | 83.88 % | 10002 |

### L'effet de siege du greedy -- et il n'a rien a voir avec celui de M1

**M1 mesure le siege sous jeu uniformement aleatoire ; ceci le mesure sous jeu greedy.** Rien ne disait d'avance que les deux se ressembleraient, et le tableau ci-dessous montre qu'ils ne se ressemblent pas du tout. Chaque ligne porte le gain du greedy sur les seules parties ou il occupait ce siege -- un tiers des parties, appariees par donne.

**1 greedy contre 2 aleatoires (reference)**

| Siege occupe | Gain moyen | IC 99 % bootstrap | Parties |
|---|---:|---|---:|
| siege 0 | +0.6965 | [+0.6706 ; +0.7223] | 3334 |
| siege 1 | +0.8116 | [+0.7903 ; +0.8317] | 3334 |
| siege 2 | +0.8855 | [+0.8690 ; +0.9015] | 3334 |

Contraste entre les deux sieges extremes, **apparie par donne** : **+0.1890**, IC 99 % [+0.1588 ; +0.2196] -- **etabli**. Chaque donne fournit les deux sieges, donc la difference ne contient plus la variance de distribution.

**2 greedys contre 1 aleatoire**

| Siege occupe | Gain moyen | IC 99 % bootstrap | Parties |
|---|---:|---|---:|
| siege 0 | -0.0758 | [-0.0967 ; -0.0549] | 6668 |
| siege 1 | +0.1829 | [+0.1621 ; +0.2046] | 6668 |
| siege 2 | +0.4959 | [+0.4744 ; +0.5175] | 6668 |

Contraste entre les deux sieges extremes, **apparie par donne** : **+0.5717**, IC 99 % [+0.5371 ; +0.6066] -- **etabli**. Chaque donne fournit les deux sieges, donc la difference ne contient plus la variance de distribution.

**1 greedy, departage deterministe**

| Siege occupe | Gain moyen | IC 99 % bootstrap | Parties |
|---|---:|---|---:|
| siege 0 | +0.6898 | [+0.6641 ; +0.7145] | 3334 |
| siege 1 | +0.8134 | [+0.7924 ; +0.8338] | 3334 |
| siege 2 | +0.8936 | [+0.8772 ; +0.9093] | 3334 |

Contraste entre les deux sieges extremes, **apparie par donne** : **+0.2038**, IC 99 % [+0.1744 ; +0.2347] -- **etabli**. Chaque donne fournit les deux sieges, donc la difference ne contient plus la variance de distribution.

**Consequence sur l'arbitrage de la phase 2.** Permuter les sieges inconditionnellement etait la bonne decision, et pour une raison que M1 seul ne pouvait pas donner : l'avantage de siege est **negligeable sous jeu aleatoire et massif sous jeu greedy**. Un protocole qui aurait teste le seuil de 38 % sur des agents aleatoires aurait conclu « inutile de neutraliser » -- et se serait trompe des la premiere mesure d'agent.

### Le departage change 61 % des refus et ne change pas le gain

**Ce n'est pas un doublon, c'est une mesure de consequence nulle**, et elle ne se lit qu'en juxtaposant les deux nombres :

| | |
|---|---:|
| part des refus du greedy que le **departage** decide (section 5) | voir `B4-departage` |
| ecart de gain entre departage aleatoire et deterministe | **+0.0011** |
| demi-largeur de l'IC 99 % du gain de reference | 0.0122 |
| l'ecart, en demi-largeurs | **0.09** |

Autrement dit : **une majorite des decisions de refus du greedy sont strategiquement indifferentes sur cette instance.** C'est un fait du JEU, pas de l'implementation, et il n'est nulle part ailleurs dans ce depot.

Deux usages immediats. Il **desarme** la lecture « le greedy refuse dans X % des cas » en montrant que la majorite de ces refus ne coutent rien. Et il donne a la phase 3 un **etalon** : un agent qui refuse dans les memes proportions n'a rien appris ; un agent dont les refus deplacent son gain a appris quelque chose.

## 5. M4 -- B1 a B7, ligne de base du greedy ET du hasard

**Deux points de comparaison, pas un.** « Le greedy fait B4 dans X % des cas » n'est pas interpretable sans savoir ce que le hasard donne. La colonne « hasard » vient de la campagne A, tous sieges confondus ; la colonne « greedy » de la campagne B, siege du greedy seul.

Chaque ligne porte son **denominateur**, son **grain** et sa **vue** : un taux dont le sujet grammatical n'est pas l'unite comptee n'est pas auditable.

**B1 a deux grains, et un seul se compare.** C'est le seul des sept dont le denominateur naturel est la partie et non une action, donc agreger les sieges mesures par un « au moins un » gonfle son numerateur **sans toucher au denominateur**. La colonne « hasard » porte trois sieges, la colonne « greedy » un seul : seules les lignes au grain `(partie, siege)` se comparent. Les lignes `-par-partie` repondent a une autre question -- *cette partie contient-elle le motif quelque part* -- et leur valeur monte mecaniquement avec le nombre de sieges agreges. **Ce defaut a ete trouve par l'audit de l'etape 4, apres une premiere lecture qui concluait l'inverse.**

**Et B1 n'est pas homogene par siege.** MESURE sur 500 donnes x 6 replicats, politique uniforme : 37,93 % au siege 0, 36,80 % au siege 1, 33,50 % au siege 2, soit 4,4 points d'etendue -- le siege 0 pose en premier, donc son « nourrir » laisse plus de nœuds ulterieurs disponibles pour un « baisser ». **Une ligne de base B1 doit donc etre equilibree sur les sieges**, et les deux colonnes ci-dessous le sont : la campagne A compte les trois sieges, la campagne B fait tourner le greedy sur les trois. Un chiffre de 37,58 % a circule en cours d'audit -- c'etait 451/1200, **siege 0 seul**, sur un echantillon de 200 donnes ; il n'a pas cours et ne doit pas etre compare a la colonne greedy.

| Compteur | Greedy | Hasard | Grain du denominateur | Vue |
|---|---|---|---|---|
| `B1-motif` | 47.93 % (4794/10002) | 36.11 % (10836/30006) | couples (partie, siege) | decideur pour le choix, vraie pour ce qui paie |
| `B1-motif-par-partie` | 47.93 % (4794/10002) | 71.90 % (7191/10002) | parties (au moins un siege mesure) | decideur pour le choix, vraie pour ce qui paie |
| `B1-tentative` | 55.63 % (5564/10002) | 49.05 % (14717/30006) | couples (partie, siege) | decideur pour le choix, vraie pour ce qui paie |
| `B1-tentative-par-partie` | 55.63 % (5564/10002) | 86.72 % (8674/10002) | parties (au moins un siege mesure) | decideur pour le choix, vraie pour ce qui paie |
| `B1-strict` | 38.66 % (3867/10002) | 26.53 % (7962/30006) | couples (partie, siege) | decideur pour le choix, vraie pour ce qui paie |
| `B1-strict-par-partie` | 38.66 % (3867/10002) | 56.83 % (5684/10002) | parties (au moins un siege mesure) | decideur pour le choix, vraie pour ce qui paie |
| `B1-collectif` | 70.07 % (7008/10002) | 67.18 % (20157/30006) | couples (partie, siege) | decideur pour le choix, vraie pour ce qui paie |
| `B1-collectif-par-partie` | 70.07 % (7008/10002) | 89.88 % (8990/10002) | parties (au moins un siege mesure) | decideur pour le choix, vraie pour ce qui paie |
| `B1-savoir-commun` | 48.27 % (4828/10002) | 36.21 % (10865/30006) | couples (partie, siege) | publique pour le choix, vraie pour ce qui paie |
| `B1-savoir-commun-par-partie` | 48.27 % (4828/10002) | 71.98 % (7199/10002) | parties (au moins un siege mesure) | publique pour le choix, vraie pour ce qui paie |
| `B2-contestee` | 68.32 % (16391/23991) | 64.90 % (46790/72090) | poses d'Assassin | decideur |
| `B2-contestee-publique` | 67.00 % (16073/23991) | 63.01 % (45427/72090) | poses d'Assassin | publique |
| `B2-fragile-2` | 78.83 % (18911/23991) | 75.22 % (54225/72090) | poses d'Assassin | decideur |
| `B2-banquet` | 34.89 % (8371/23991) | 33.35 % (24041/72090) | poses d'Assassin | publique |
| `B2-cibles` | 80.84 % (19395/23991) | 78.58 % (56651/72090) | poses d'Assassin | decideur |
| `B2-destination/banquet-Estime` | 18.82 % (4515/23991) | 16.74 % (12066/72090) | poses d'Assassin | publique |
| `B2-destination/banquet-Disgrace` | 16.07 % (3856/23991) | 16.61 % (11975/72090) | poses d'Assassin | publique |
| `B2-destination/domaine propre` | 30.29 % (7266/23991) | 33.14 % (23888/72090) | poses d'Assassin | publique |
| `B2-destination/domaine adverse` | 34.82 % (8354/23991) | 33.52 % (24161/72090) | poses d'Assassin | publique |
| `B3-expose` | 33.27 % (13309/40008) | 46.72 % (56075/120024) | poses en domaine adverse | decideur |
| `B3-expose-vraie` | 38.33 % (15334/40008) | 50.33 % (60403/120024) | poses en domaine adverse | vraie |
| `B3-simultane` | 9.84 % (3935/40008) | 15.07 % (18088/120024) | poses en domaine adverse | decideur |
| `B4-brut` | 23.65 % (4773/20179) | 30.28 % (18059/59645) | nœuds de ciblage a >= 1 cible | decideur |
| `B4-strict` | 38.78 % (1851/4773) | 7.96 % (1437/18059) | refus | decideur |
| `B4-departage` | 61.22 % (2922/4773) | 58.32 % (10532/18059) | refus | decideur |
| `B4-contre-nature` | 0.00 % (0/4773) | 33.72 % (6090/18059) | refus | decideur |
| `B4-tout-dos` | 3.89 % (784/20179) | 5.02 % (2994/59645) | nœuds de ciblage a >= 1 cible | decideur |
| `B4-meurtre-couteux` | 0.00 % (0/15406) | 4.77 % (1983/41586) | meurtres | decideur |
| `B5-renfort` | 20.41 % (3811/18671) | 21.44 % (11096/51742) | couples (nœud, famille) | decideur |
| `B5-pire-cas` | 19.00 % (2651/13956) | 21.58 % (8563/39674) | couples (nœud, famille) | decideur |
| `B7-gaspillage` | 0.15 % (61/40008) | 0.17 % (203/120024) | poses au banquet | decideur |
| `B7-gaspillage-vraie` | 0.20 % (82/40008) | 0.24 % (289/120024) | poses au banquet | vraie |
| `B7-lumiere` | 11.81 % (4723/40008) | 13.45 % (16140/120024) | poses au banquet | decideur |
| `B7-occasions` | 1.22 % (488/40008) | 1.19 % (1432/120024) | poses au banquet | decideur |

### B4 -- le controle d'identite, et la part que le departage produit

`B4-strict + B4-departage + B4-contre-nature` doit valoir exactement le nombre de refus. C'est un **controle**, verifie par `comportements.verifier_b4`, qui leve si l'identite tombe.

| | Greedy | Hasard |
|---|---:|---:|
| somme des trois | 4773 = 4773 refus | 18059 = 18059 refus |

**3.89 % des nœuds de ciblage du greedy n'offrent que des dos.** Sur ceux-la son evaluation est **plate** -- un dos ne compte pas dans l'influence percue, donc le tuer ne change rien -- et c'est la **regle de departage** qui choisit, pas l'heuristique : elle refuse avec probabilite `1/(k+1)`. C'est la part de `B4-brut` qui ne mesure pas un comportement, et elle se lit a cet endroit.

### Une inclusion, verifiee et non deduite

`B1-collectif` majore `B1-motif` **par construction** : le don vient du siege mesure, la bascule de n'importe quel siege. L'inclusion est verifiee sur les deux colonnes -- greedy 7008 >= 4794, hasard 20157 >= 10836. **Une inclusion qui tombe designerait un compteur faux**, et celle-ci est tombee une fois : `B1-collectif` n'agregeait que les sieges mesures, donc il valait exactement `B1-motif` des qu'on mesurait un agent seul -- muet precisement dans le cas ou il sert, un don du greedy retourne par un adversaire.

### Deux choses que la mesure a corrigees dans ma propre lecture

**Le departage explique 61.22 % des refus du greedy, mais les nœuds tout-dos n'en sont que 3.89 %.** Le paragraphe 5.4.1 de la pre-inscription designait les nœuds tout-dos comme le mecanisme de l'egalite : c'est un mecanisme, ce n'est pas **le** mecanisme. La majorite des egalites vient de nœuds ou une cible identifiable existe mais dont le meurtre ne change pas l'ecart evalue -- typiquement une carte d'une famille Indifferente. Ma pre-inscription avait raison sur la necessite de separer les trois nombres, et incomplete sur la cause.

**B7 n'a presque pas d'occasion de se manifester** : 1.22 % des poses au banquet du greedy surviennent alors qu'au moins une famille est hors d'atteinte, soit 488 poses sur 40008. Le gaspillage mesure, 0.15 %, se lit **sur ce fond-la** : sur cette instance a 4 tours, une famille devient rarement hors d'atteinte avant la fin. B7 est donc quasi inmesurable ici, et c'est un fait de l'instance, pas un defaut du compteur -- `B7-occasions` existe precisement pour que ce zero ne se lise pas comme « il ne gaspille pas ».

### B6 -- distance de variation totale entre le tour 1 et le tour 4

**Elle n'est pas nulle chez le greedy, et ce n'est pas une preuve de comprehension** : l'etat du plateau change avec le tour, donc un agent a horizon un tour joue mecaniquement differemment sans rien savoir de la pioche. La phase 3 ne conclura que sur l'**ecart** entre sa distance et celles-ci.

**La concurrente est publiee a cote, et son ecart avec la retenue est un resultat.** **B6-dernier-contre-reste** compare le tour 4 aux tours 1 a 3 **agreges** : son terme de comparaison porte trois fois plus de nœuds, donc il est plus stable -- et il melange trois etats de plateau differents, donc il **dilue** l'ecart. Le choix du paragraphe 6.6 de la pre-inscription se lit sur les deux colonnes de droite.

| Groupe de categories | Greedy, tour 1 vs 4 | Hasard, tour 1 vs 4 | Greedy, dernier vs reste | Hasard, dernier vs reste |
|---|---:|---:|---:|---:|
| banquet | 0.1589 | 0.0017 | 0.0560 | 0.0036 |
| domaine adverse | 0.6566 | 0.5823 | 0.3328 | 0.2918 |
| ciblage | 0.2793 | 0.2712 | 0.1438 | 0.1366 |

## 6. Ce que chaque compteur peut separer -- M4 pour la phase 3

La phase 3 se donne **1000 parties appariees** (paragraphe 3 du protocole). Pour chaque compteur, l'ecart de taux qu'elle pourra **etablir** a ce budget, a 99 % bilateral et 80 % de puissance, entre son agent et le greedy -- chacun mesure sur un siege tournant.

Le `denominateur par partie` est ce qui decide : un compteur d'action en offre plusieurs par partie, un compteur d'occasion rare beaucoup moins d'une.

| Compteur | Greedy | Denom. / partie | Ecart detectable a 1000 parties | Ecart greedy-hasard observe | Parties pour l'etablir |
|---|---:|---:|---:|---:|---:|
| `B1-motif` | 47.93 % | 1.0000 | 7.64 % | +11.82 pt | 418 |
| `B1-motif-par-partie` | 47.93 % | 1.0000 | 7.64 % | -23.97 pt | 102 |
| `B1-tentative` | 55.63 % | 1.0000 | 7.59 % | +6.58 pt | 1331 |
| `B1-tentative-par-partie` | 55.63 % | 1.0000 | 7.59 % | -31.09 pt | 60 |
| `B1-strict` | 38.66 % | 1.0000 | 7.44 % | +12.13 pt | 377 |
| `B1-strict-par-partie` | 38.66 % | 1.0000 | 7.44 % | -18.17 pt | 168 |
| `B1-collectif` | 70.07 % | 1.0000 | 7.00 % | +2.89 pt | 5868 |
| `B1-collectif-par-partie` | 70.07 % | 1.0000 | 7.00 % | -19.82 pt | 125 |
| `B1-savoir-commun` | 48.27 % | 1.0000 | 7.64 % | +12.06 pt | 401 |
| `B1-savoir-commun-par-partie` | 48.27 % | 1.0000 | 7.64 % | -23.71 pt | 104 |
| `B2-contestee` | 68.32 % | 2.3986 | 4.59 % | +3.42 pt | 1806 |
| `B2-contestee-publique` | 67.00 % | 2.3986 | 4.64 % | +3.98 pt | 1359 |
| `B2-fragile-2` | 78.83 % | 2.3986 | 4.03 % | +3.61 pt | 1250 |
| `B2-banquet` | 34.89 % | 2.3986 | 4.70 % | +1.54 pt | 9284 |
| `B2-cibles` | 80.84 % | 2.3986 | 3.88 % | +2.26 pt | 2956 |
| `B2-destination/banquet-Estime` | 18.82 % | 2.3986 | 3.86 % | +2.08 pt | 3432 |
| `B2-destination/banquet-Disgrace` | 16.07 % | 2.3986 | 3.62 % | -0.54 pt | 45302 |
| `B2-destination/domaine propre` | 30.29 % | 2.3986 | 4.53 % | -2.85 pt | 2532 |
| `B2-destination/domaine adverse` | 34.82 % | 2.3986 | 4.70 % | +1.31 pt | 12952 |
| `B3-expose` | 33.27 % | 4.0000 | 3.60 % | -13.45 pt | 72 |
| `B3-expose-vraie` | 38.33 % | 4.0000 | 3.72 % | -12.00 pt | 96 |
| `B3-simultane` | 9.84 % | 4.0000 | 2.28 % | -5.23 pt | 189 |
| `B4-brut` | 23.65 % | 2.0175 | 4.57 % | -6.62 pt | 477 |
| `B4-strict` | 38.78 % | 0.4772 | 10.78 % | +30.82 pt | 123 |
| `B4-departage` | 61.22 % | 0.4772 | 10.78 % | +2.90 pt | 13824 |
| `B4-contre-nature` | **0 %** | 0.4772 | borne exacte 1.10 % | -33.72 pt | voir ci-dessous |
| `B4-tout-dos` | 3.89 % | 2.0175 | 2.08 % | -1.13 pt | 3360 |
| `B4-meurtre-couteux` | **0 %** | 1.5403 | borne exacte 0.34 % | -4.77 pt | voir ci-dessous |
| `B5-renfort` | 20.41 % | 1.8667 | 4.51 % | -1.03 pt | 19030 |
| `B5-pire-cas` | 19.00 % | 1.3953 | 5.08 % | -2.59 pt | 3846 |
| `B7-gaspillage` | 0.15 % | 4.0000 | 0.30 % | -0.02 pt | 320163 |
| `B7-gaspillage-vraie` | 0.20 % | 4.0000 | 0.35 % | -0.04 pt | 93058 |
| `B7-lumiere` | 11.81 % | 4.0000 | 2.47 % | -1.64 pt | 2255 |
| `B7-occasions` | 1.22 % | 4.0000 | 0.84 % | +0.03 pt | 989815 |

### Les deux zeros ne sont pas « rien a detecter »

`B4-contre-nature` et `B4-meurtre-couteux` valent **exactement 0** chez le greedy, par construction : `choisir` prend un argmax. Un taux nul a une variance estimee nulle, donc la formule normale rendrait un ecart detectable de zero -- « tout est detectable » --, ce qui est exactement faux. Ce qui se dit d'un zero, c'est sa **borne haute exacte** de Clopper-Pearson : au budget de 1000 parties, un agent dont ce compteur depasse la borne ci-dessus est **separable** du greedy ; en dessous, il ne l'est pas. C'est ce qui empeche de lire « le greedy ne le fait jamais » comme « aucun agent ne peut faire mieux ».

### B7 n'a aucun pouvoir discriminant a ce budget, et ce n'est pas une opinion

L'occasion ne survient que dans 1.22 % des poses au banquet, soit 488 occasions sur 40008. A 1000 parties il en resterait de l'ordre de 49.

L'ecart greedy-hasard observe vaut -0.02 point, quand l'ecart detectable a 1000 parties est de 0.30 %. **B7 ne peut donc rien separer au budget de la phase 3**, et il faudrait 320163 parties pour esperer trancher l'ecart observe.

**C'est le meme defaut que les quatre criteres de non-degenerescence de la phase 1 et que le seuil de 38 % de M1** : un critere qui constate au lieu de tester. Ca fait trois fois dans ce projet. La colonne « ecart detectable » ci-dessus existe pour que la quatrieme n'arrive pas -- un lecteur de la phase 3 qui comparerait son agent au 0.15 % de B7 comparerait du bruit.

## 7. Ce que ces chiffres n'etablissent PAS

1. **Le greedy ne planifie rien.** Son horizon est d'un tour, par construction. Les 47.93 % de parties portant le motif B1 mesurent la frequence a laquelle le MOTIF apparait par **coincidence** -- deux actions separees, chacune localement optimale, qui forment apres coup la figure d'un plan. Ecrire « le greedy planifie des retournements dans 47.93 % des parties » serait **faux**. Le chiffre s'intitule *frequence du motif B1*, jamais *frequence de planification*.
2. **Le meme avertissement vaut mot pour mot pour B3.** Le greedy ne modelise pas l'interet qu'il cree en donnant une carte : son B3 mesure la coincidence entre ce qu'il detient et ce qu'il donne.
3. **B1 a un plafond que rien ne franchira.** La phase 1 a mesure que 7,40 % des parties portent une perte d'acquis qu'aucun des trois sieges ne pouvait voir. Ces retournements sont invulnerables a toute planification, par n'importe quel agent : une ligne de base B1 basse est un **plafond du mesurable**, pas un defaut d'agent.
4. **Une part de B4 mesure le departage, pas le jeu** -- 3.89 % des nœuds de ciblage. Le taux brut ne se publie donc jamais seul.
5. **M3 ne dit pas que le greedy est fort.** Il dit qu'il bat le hasard. Aucun chiffre ici ne borne la distance entre le greedy et un bon joueur.
6. **M1 ne dit rien de l'avantage de siege sous d'autres politiques.** La permutation systematique rend la question sans consequence pratique ; elle ne la resout pas.
7. **Aucun de ces chiffres ne dit quoi que ce soit de `complet-3j`** -- 6 familles, 3 exemplaires, 10 tours. Rien ne se transporte par un facteur.
8. **La phase 2 ne valide pas le moteur.** Elle le suppose conforme ; c'est la phase 0 qui l'etablit, et elle est close.

## 8. Duree machine

| Campagne | Duree |
|---|---:|
| A | 244.8 s |
| A controle | 247.3 s |
| B | 301.5 s |
| B, 2 greedys contre 1 aleatoire | 351.1 s |
| B, 1 greedy, departage deterministe | 297.5 s |

<!-- duree totale : 1961.2 s -->
