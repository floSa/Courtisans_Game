# Audit — phase 2 — VERDICT : REJETÉ

Livrable audité : `02ae24b`. Moteur de référence : `19f99f2`. Code de l'audit : `audit/phase2/`
et `tests/audit_phase2/`. Aucune ligne du constructeur n'a été lue avant que mes sept
définitions, mon greedy, mes sept compteurs et mon intervalle de confiance ne soient écrits.

## Constats

| # | Contrôle | Résultat |
|---|---|---|
| A1 | Tests rejoués moi-même | **903 / 903 verts en 199 s**, dont 214 ajoutés par la phase 2. Aucun test annoncé vert qui ne le soit |
| A2 | Tests relus contre la spec | **0 sur les 214** ne vérifient le code au lieu de la règle. Aucun attendu calculé par la fonction testée ; 64 littéraux calculés à la main dans `test_comportements.py` seul |
| A3 | Tests hostiles écrits par moi | **36** — 35 verts, **1 rouge** (défaut 3). 11 visent son code, 25 mes propres instruments |
| A4 | Critères d'acceptation revérifiés | **4 / 4** mesures établies et consignées. Le go/no-go de la phase 2 est satisfait |
| A5 | Niveaux de preuve du compte rendu | **0 DÉDUIT présenté comme MESURÉ.** Le seul DÉDUIT du livrable est étiqueté et daté comme non re-mesuré (§4 des concurrentes, extrapolation du 82,53 % de la phase 1) |
| A6 | Valeurs en dur, duplications | **0** sur son code — `ruff` propre sur `agents/` et `mesure/`. Les décalages de graine sont des constantes nommées |
| A7 | Chiffres reconstruits | **395 / 395 lignes identiques** après régénération complète, durées machine normalisées |

## Tests hostiles écrits

1. **Le greedy doit refuser** — position bâtie à la main, refuser vaut 1, tuer vaut 0 — **vert**
2. **Le greedy doit tuer** — la symétrique, tuer remonte de −1 à 0 — **vert**
3. **Aveuglement différentiel, vecteur d'évaluation entier** — deux plateaux ne différant que par l'identité d'un Espion adverse — **vert**
4. **Aveuglement quand le dos est une cible** — `cibles_courantes()` rend l'identité — **vert**
5. **Aveuglement sur balayage de 60 parties entières**, identité de chaque dos permutée à chaque nœud, 200+ nœuds porteurs — **vert**
6. **Cohérence de son horizon** — la valeur promise par la pose est-elle réalisée — **ROUGE**
7. **Le renommage `_vue_du_joueur` → `vue_du_joueur` ne change ni `chaine` ni `tenseur`** — 6 945 vues comparées à une partition réécrite depuis le §4.2 — **vert**
8. **Le corps de la fonction renommée est inchangé** — comparaison AST des deux versions, hors docstring — **vert**
9. **`vue_du_joueur` publique refuse un identifiant qui n'est pas un siège** — **vert au sens du test, mais il constate l'absence de garde** (défaut 4)
10. **Sans Assassin, le dénominateur de B2 et B4 vaut exactement 0 et aucun taux n'est publié** — **vert**
11. **Six mutations réinjectées dans son code** (étape 4) — cinq tuées par un test nommé, **une survivante** (défaut 2)

Plus 25 contrôles négatifs à zéro exact sur mes propres compteurs, dont B1 quand la bascule
précède le don, B3 sans exposition, B7 quand la carte affaiblit la famille imprenable.

## Défauts

| # | Gravité | Défaut | Où | Preuve |
|---|---|---|---|---|
| 1 | **bloquant** | Les cinq lignes `-par-partie` du §6 publient sous l'intitulé « Écart greedy-hasard observé » une différence entre **deux grains différents** — greedy sur 1 siège contre hasard sur 3 sièges agrégés par « au moins un ». Sur `B1-motif` le signe **s'inverse** : −23,97 pt au lieu de +11,82 pt. Chaque ligne reçoit en outre un « Parties pour l'établir » qui la présente comme un effet établissable à bon compte — 102 parties. Le §5 porte l'avertissement ; le §6, **titré « M4 pour la phase 3 »**, ne contient ni le mot « grain » ni le mot « comparable » | `mesure/resultats/phase2.md` §6 | MESURÉ : 0 occurrence de « grain » et 0 de « comparable » dans le §6 ; MESURÉ par mon compteur indépendant sur 600 parties, le seul changement de grain gonfle B1 de 46,78 % à 84,00 %, soit **+37,22 points** — l'écart publié est dominé par l'artefact |
| 2 | majeur | La clause 3 de `B1-motif` — « Indifférente **ou** en Obscurité », le seuil que l'encadré du §2.2 tranche — **n'est tenue par aucun test**. La faute exacte du tour 1 de la phase 1, réintroduite, passe toute la suite | `mesure/comportements.py`, clause `_paye(..., exige_obscurite=False)` | MESURÉ : mutation appliquée, **913 tests verts, 0 rouge** (ma seule cible rouge déselectionnée). Déplacement du chiffre publié : 47,93 % → 38,66 %, soit **9,27 points**, contre un écart détectable de **7,64 points** au budget de la phase 3 selon son propre §6 |
| 3 | majeur | Horizon incohérent. La pose est évaluée Assassins résolus **conjointement au mieux** (`_meilleur_apres_assassins`, max exhaustif) ; les ciblages se décident **un nœud à la fois** — `Perception` ne porte pas les Assassins en attente, donc la politique ne *peut pas* regarder plus loin. Le greedy choisit une pose pour une valeur qu'il ne réalise pas. Non documenté | `agents/greedy.py` `_valeur_de_ciblage` vs `_meilleur_apres_assassins` ; `agents/perception.py` | MESURÉ sur 2 000 parties : **0,388 % des tours** (93/24 000) promettent une valeur non réalisée ; **7,33 % des nœuds où un Assassin reste en attente** (178/2 429) ont un argmax myope différent de l'argmax cohérent |
| 4 | mineur | `vue_du_joueur`, rendue publique par `a198df8`, ne valide pas son argument `joueur`. `vue_du_joueur(etat, -1)` et `(etat, 3)` rendent une partition bien formée **qui n'est la vue d'aucun siège**, sans lever. `_joueur_observe` protège `information_state_string` ; la nouvelle porte publique le contourne, et `percevoir` ne valide pas davantage — `mains[-1]` y est la main du dernier joueur | `courtisans/infoset.py:84` ; `agents/perception.py` `percevoir` | MESURÉ : test 9. C'est la réouverture du **défaut 2 de la phase 0** sur une entrée neuve. Non atteignable par le pilote actuel, qui passe toujours `current_player()` |
| 5 | mineur | Le rapport livré est encodé en **cp1252** quand les trois autres documents de la phase sont en UTF-8 : 55 octets non-ASCII indécodables, et la corruption est visible — « n<?>uds » pour « nœuds », « <?> gagner une partie <?> ». La commande de reproduction de son en-tête, `uv run python -m mesure.phase2`, **omet la redirection** qui produit le fichier | `mesure/resultats/phase2.md` | MESURÉ : `UnicodeDecodeError` à l'octet 2562 ; 0x9c ×11, 0xab ×22, 0xbb ×22. Les autres `.md` de la phase décodent en UTF-8 sans erreur. Le contenu, lui, est intact — cf. A7 |
| 6 | mineur | Deux des douze directions annoncées, `B4-contre-nature` et `B4-meurtre-coûteux`, sont déclarées nulles **par construction** dans la pré-inscription elle-même (« puisque `choisir` prend un argmax »). Les compter ✅ parmi « onze tiennent sur douze » compte deux tautologies comme deux prédictions falsifiables confirmées | `mesure/phase2_definitions_et_concurrentes.md` §0, lignes 8 et 9 ; §6.4 de la pré-inscription | DÉDUIT du texte des deux documents, non exécuté. Le décompte falsifiable est **9 sur 10**, une infirmée |
| 7 | mineur | Le tableau « Le départage change 61 % des refus et ne change pas le gain » porte, dans une table dont le texte dit « elle ne se lit qu'en juxtaposant les deux nombres », une cellule sans nombre : « voir `B4-departage` » | `mesure/resultats/phase2.md` §4 | MESURÉ : la cellule est littéralement « voir `B4-departage` » |

## Ce que j'ai cherché sans le trouver

**Le greedy ne triche pas, et c'est le résultat principal de cet audit.** Je n'ai pas grepé.
J'ai construit deux états ne différant que par l'identité d'un Espion adverse, comparé le
**vecteur d'évaluation entier** et non l'action tirée, refait le cas où le dos est une cible
manipulée, puis balayé 60 parties entières en permutant l'identité de chaque dos à chaque
nœud — égalité partout. Sa propre preuve est à trois niveaux et **plus forte que la mienne** :
statique (le texte de `greedy.py` ne nomme aucun accès interdit, il n'importe ni `Engine` ni
`State`, et la signature de `choisir` ne peut pas porter d'état), dynamique (`vue_privilegiee`
piégée pour lever pendant tout l'appel, **plus un test que le piège mord**), différentielle
(brouillage simultané des Espions adverses, de la pioche jamais tirée et des mains adverses,
**plus un test que le brouilleur change vraiment la vérité**). M3 et M4 ne sont pas à refaire.

**Trois concordances qui valent d'être dites, chacune obtenue par du code écrit sans le sien.**
σ(gain) 0,6671 contre 0,6652. Gains de siège du greedy 0,714 / 0,815 / 0,895 contre
0,697 / 0,812 / 0,886, et je **confirme son résultat le plus important** — l'avantage de siège
est négligeable sous jeu aléatoire et massif sous jeu greedy, mon contraste apparié +0,181
contre son +0,189. Taux de refus B4 sur nœuds à ≥ 1 cible : 23,81 %, IC99 [22,53 ; 25,12],
contre son 23,65 %. Mon Clopper-Pearson recolle `scipy` à 3,5 × 10⁻¹² sur 70 couples et
reproduit au centième le [94,12 % ; 97,42 %] publié en phase 1.

**Deux lectures indépendantes du §2.2 ont convergé.** Sa clause 3 exige « Indifférente ou en
Obscurité » ; j'ai écrit la même chose après correction de ma propre étape 0. Comme la
convergence sur R2 en phase 1, cela vaut plus qu'un accord de chiffres.

**Le pouvoir discriminant de B7, remesuré : il est nul, et il l'est par le bas.** Écart
détectable 0,12 % pour un taux mesuré de 0,10 % à mon grain ; un agent à **zéro exact** n'en
est pas séparable, borne haute 0,09 % contre borne basse du greedy 0,05 %. Son §6 dit la même
chose avec ses chiffres, et l'écrit comme la troisième occurrence dans ce projet d'un critère
qui constate au lieu de tester. Sur les 17 compteurs que j'ai instrumentés, B7 est le seul
aveugle par le bas ; les 16 autres séparent un agent à zéro.

**Deux soupçons que j'ai levés, et qui étaient les miens.** J'ai cru que sa conclusion « le
départage ne change pas le gain » était jugée avec un intervalle trop large, l'écart étant
apparié et l'intervalle non apparié. **Infirmé** : MESURÉ sur 1 500 donnes, la demi-largeur
appariée vaut 0,0186 contre 0,0122 pour la sienne — l'appariement n'aide pas ici, exactement
pour la raison qu'il a lui-même mesurée (`rho` ≈ 0,007). Sa conclusion tient, et elle tient
sous le yardstick plus sévère. J'ai aussi cru son A5 défaillant, faute de niveaux de preuve
dans le rapport : c'était mon motif de recherche qui échouait sur l'accent de « DÉDUIT ».

**Les deux zéros absolus sont adossés à des cas construits à la main**, ce que la phase 1 exige
et que je cherchais à prendre en défaut :
`test_b4_un_refus_contre_nature_est_bien_compte_quand_il_existe` prouve que le compteur *peut*
voir l'événement, et `test_l_aleatoire_produit_lui_des_refus_contre_nature` le prouve par
l'autre bout. Le contrôle 0/0 existe aussi, nommé
`test_un_denominateur_nul_rend_none_et_non_zero`, et ma mutation confirme qu'il le tient.

**Un complément, pas un défaut.** Sous la lecture la plus littérale de « un siège gagne plus de
38 % des parties » — être au score maximum, ex æquo compris —, MESURÉ sur 10 000 parties, mes
trois sièges valent 38,47 %, 38,16 % et 38,90 %. Le seuil du protocole se franchit donc pour
**les trois sièges à la fois**, avec un avantage de siège nul. Cela ne contredit pas sa
conclusion, cela la renforce : ce seuil n'est pas un test d'avantage de siège. Son rapport
nomme trois lectures et écarte à raison la stricte ; celle-ci, la quatrième, n'y est pas.

## Justification du verdict

Un défaut bloquant, donc **REJETÉ**. Le §6 est la section que la phase 3 lira pour se comparer
— son titre le dit — et cinq de ses lignes y portent, sous un intitulé qui annonce un écart
greedy-hasard, une différence entre deux grains, de signe inverse sur B1, assortie d'un coût en
parties qui la présente comme réelle. Le §5 met en garde ; le §6 ne le répète pas, et c'est mot
pour mot la réserve laissée ouverte au tour 2 de la phase 1 sur son §6.

Le reste du livrable est le plus solide que ce projet ait produit. Les sept contrôles sont
concluants sur le fond : les 903 tests passent, les 395 lignes du rapport se régénèrent à
l'identique, aucun DÉDUIT n'est déguisé en MESURÉ, le greedy est aveugle sous trois preuves
indépendantes plus les cinq miennes, et le rapport écrit lui-même les trois choses que le
prompt d'audit m'avait données comme pièges — que B1 chez le greedy mesure une coïncidence et
non un plan, que la phase 1 a posé un plafond de 7,40 % sur ce que B1 peut mesurer, et que B7
n'a aucun pouvoir discriminant à ce budget. Les défauts 2 et 3 ne changent aucun chiffre
publié : ils disent qu'une définition juste n'est pas protégée, et qu'un agent de référence est
légèrement incohérent avec sa propre description. Le défaut 1, lui, change ce qu'un lecteur de
la phase 3 conclura.
