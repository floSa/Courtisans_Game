# Audit — phase 2, tour 2 — VERDICT : ACCEPTÉ SOUS RÉSERVE

Corrections auditées : `72630a1`. Verdict du tour 1 : [verdict_phase_2.md](verdict_phase_2.md).
Re-vérification limitée aux sept points listés. Toute observation hors de ces sept est
étiquetée comme telle et ne compte pas au verdict. Je n'ai rien corrigé dans son code —
`git diff` sur `agents/`, `courtisans/`, `mesure/` est vide après mes réinjections.

## Constats

| # | Contrôle | Résultat |
|---|---|---|
| A1 | Tests rejoués moi-même | **965 verts / 966, 1 rouge** en 83 s. Le rouge est à moi et porte la réserve 1. Son parc : **288 tests** sur les fichiers de la phase 2, +22 au tour 2 |
| A2 | Tests relus contre la spec | Les 18 tests ajoutés vérifient tous une **règle ou un invariant nommé**, pas un retour de fonction. Aucun attendu calculé par la fonction testée |
| A3 | Tests hostiles écrits par moi | **30 de plus**, soit 66 au total — 29/30 verts, 1 rouge (réserve 1). Un des 36 du tour 1 est **requalifié**, voir plus bas |
| A4 | Les sept points revérifiés | **7 / 7**, dont deux avec réserve |
| A5 | Niveaux de preuve | 0 DÉDUIT déguisé en MESURÉ. Le seul DÉDUIT du §4 des concurrentes reste étiqueté et daté « non re-mesuré » |
| A6 | Valeurs en dur, duplications | **0** — `ruff` propre sur `agents/` et `mesure/` ; `BUDGET_PHASE_3` nommé ; **un seul** site de calcul de budget, vérifié par grep sur `rapport_phase2.py` |
| A7 | Chiffres reconstruits | **6 / 6 budgets** de la troisième population, avec mon quantile et **mon** dénominateur par partie. Et je ne m'appuie sur aucun de vos calculs |

## Les sept points

### 1. Défaut bloquant — **levé**

Les quatre branches sont vérifiées par moi : `ecart_de_taux` et `cumuler` **lèvent** tous
deux `GrainsIncomparables` sur deux grains différents, et **passent** tous deux sur le même —
une garde qui lèverait toujours interdirait la table entière, et rien ne l'aurait signalé.

Le point qui rend la correction réelle et non cosmétique : le grain porte désormais
`len(retenus)`, donc *« parties (au moins un des 1 sièges mesurés) »* contre *« ... des 3
sièges mesurés »*. MESURÉ en faisant tourner ses deux campagnes côte à côte : les deux
libellés diffèrent et la garde lève entre eux. Avant, ils étaient identiques — une parade qui
aurait comparé les libellés n'aurait rien levé, et c'était le vrai risque.

La distinction que je cherchais à casser tient aussi : un dénominateur vide rend `None` et ne
lève **pas**, un grain incomparable lève. Confondre les deux ferait lire « pas comparable » là
où il faut lire « l'occasion ne s'est pas présentée ».

Dans le rapport : les cinq lignes `-par-partie` portent « non comparable : grains différents »
dans les **deux** colonnes, le `-23.97` a disparu, et le titre du §6 nomme ce qui n'est pas
comparable. MESURÉ par parcours des 34 lignes.

### 2. Défaut majeur B1 — **levé**

Réinjection par moi de la faute exacte du tour 1 — `exige_obscurite=False` → `True` sur la
clause 3 de `B1-motif` : **1 rouge, 963 verts**, et le rouge est
`test_b1_compte_une_famille_qui_finit_EXACTEMENT_indifferente`. Le piège mord, et il mord au
bon endroit. Son code est restauré à l'octet près après la réinjection.

MESURÉ que sa prémisse est assertée et non supposée : son test vérifie que la famille finit
**exactement** Indifférente, puis exige `B1-motif` à 1 et `B1-strict` à 0. Un cas qui aurait
fini en Obscurité passerait sous les deux lectures et ne séparerait rien.

### 3. Défaut majeur horizon — **levé, avec réserve 1**

La pré-inscription **n'est pas amendée** : `git diff 02ae24b 72630a1 --
mesure/phase2_hypothese_et_instrument.md` est vide. C'est la bonne discipline, et c'est
vérifié plutôt que cru. `mesure/coherence_greedy.py` et le §4 bis existent, avec deux lectures
et leurs deux dénominateurs, intervalles exacts compris.

Vous avez raison contre votre propre formulation, et le rapport l'écrit : plancher pour M3 —
un agent plus myope que sa spécification est plus faible, donc le gain publié minore —, aucun
sens déterminé pour M4, puisque les compteurs B4 sont jugés par l'évaluation myope elle-même.

**Mais le compte est faux et aucun nom n'est donné.** Voir réserve 1.

**Requalification de mon propre test.** Mon
`test_la_valeur_annoncee_par_la_pose_est_celle_qui_sera_realisee` du tour 1 interdisait
l'écart. Le constructeur a répondu en le **documentant** plutôt qu'en le corrigeant, et il a
raison ici : la ligne de base de toutes les phases suivantes est celle de *cet* agent, et
déplacer l'étalon après publication est précisément le mode de défaut du projet. Laisser mon
test rouge rapporterait faussement dans l'autre sens. Il caractérise désormais : l'écart doit
**exister** — sinon le §4 bis décrirait un phénomène absent — et rester sous 2 % des tours.
Vert. C'est mon test, pas son code : la séparation constructeur/auditeur est intacte.

### 4. Le critère « aveugle par le bas » — **vérifié**

`Budget.aveugle_par_le_bas` est un champ **calculé**, `detectable > taux`. Vérifié aux deux
bornes : vrai sur `B7-gaspillage`, faux sur `B7-lumiere`.

Et les deux lignes sont les bonnes. J'ai recalculé le critère sur les 34 lignes du §6 avec ma
propre formule — `δ = (z_α + z_β) √(2pq / (1000 × par_partie))` — et j'obtiens **exactement le
même ensemble** que les lignes marquées : `B7-gaspillage` et `B7-gaspillage-vraie`, deux.
Les deux taux nuls, eux, n'ont pas de marqueur mais une borne exacte, ce qui est le traitement
correct : à taux nul la variance estimée est nulle et la formule normale rendrait « tout est
détectable ».

### 5. La garde de campagne scindée — **vérifié**

Trois branches, chacune tenue par un cas à moi : `campagne_b` refuse `nb_greedys = 0` et
`nb_greedys = 4` ; `campagne_b(nb_greedys=3)` **accepte** — M4 en a besoin — et
`mesurer_m3(..., nb_greedys=3)` **refuse**. Le paramètre `nb_greedys` de `mesurer_m3` est
positionnel sans défaut, vérifié par `inspect.signature` : un défaut le rendrait facultatif et
l'oublier ferait recalculer M3 sur une population où il n'a pas d'objet.

La garde confondait bien une mesure avec une phase. Trois greedys n'ont pas de winrate relatif
— la symétrie donne un tiers — mais leurs comportements se mesurent parfaitement.

### 6. La troisième population — **vérifiée comme une première livraison, avec réserve 2**

MESURÉ en rejouant sa campagne à 600 donnes, `depart=6000000`, `nb_greedys=3` : les six taux
tombent à **+0,03 à +1,06 point** des valeurs publiées sur 3 334 donnes, tous du même côté —
ce que produit une fluctuation d'échantillon commune à six définitions emboîtées, la
demi-largeur à 99 % valant environ 2,3 points à cette taille.

Le critère de périmètre est vérifiable sur le texte, comme annoncé : la docstring de
`motif_b1` porte « joueurs **différents** » et « n'importe quel siège » ; celles de `b4` et
`b5` ne nomment aucun autre joueur. `B4-tout-dos` et `B5-renfort` sont nommés dans le rapport
avec leur raison d'exclusion et renvoyés au journal comme question ouverte de la phase 3. Le
raisonnement sur le critère textuel contre un critère de degré est le bon, et il est écrit.

`M3 n'a pas d'objet ici` est écrit **et** tenu par le code (point 5).

**Mais l'inclusion n'est pas vérifiée sur cette population.** Voir réserve 2.

### 7. Défaut 5, les six budgets — **levé, et c'est là que mon temps a le plus rapporté**

J'ai reconstruit l'**unité avant la valeur**, sans lire son code de budget d'abord : un
compteur `-par-partie` rend **un** booléen par partie quel que soit le nombre de sièges, parce
que l'agrégation est dans son numérateur ; un compteur au grain du couple `(partie, siège)` en
rend autant que de sièges mesurés. J'ai ensuite vérifié que ce nombre égale `n / 10 002`, et
seulement après j'ai calculé.

| Compteur | mon obs./partie | écart | mon budget | publié |
|---|---:|---:|---:|---:|
| `B1-collectif` | 3,0 | 4,60 % | **745** | 745 |
| `B1-collectif-par-partie` | 1,0 | 3,37 % | **1 295** | 1 295 |
| `B1-motif-par-partie` | 1,0 | 10,63 % | **299** | 299 |
| `B1-tentative-par-partie` | 1,0 | 7,38 % | **239** | 239 |
| `B1-strict-par-partie` | 1,0 | 2,33 % | **10 400** | 10 400 |
| `B1-savoir-commun-par-partie` | 1,0 | 10,90 % | **280** | 280 |

**6 / 6 à l'unité près**, avec mes propres quantiles — `z = 2,5758293 + 0,8416212`, calculés
par bissection sur `erf` dans mon module, pas importés du sien.

Le mécanisme du facteur trois est confirmé de l'extérieur : `745 × 3 = 2 235`, soit le
`2 234` que vous aviez validé. Votre formule le reproduisait parce qu'elle recevait le même
`par_partie` erroné — deux implémentations qui partagent la même hypothèse fausse concordent
parfaitement, et A7 ne vaut jamais preuve que le chiffre est juste.

Les parades tiennent : `observations_par_partie` lève sur un compteur `-par-partie` dont le
dénominateur n'est pas le nombre de parties, **et** rend exactement `1.0` quand il l'est — les
deux branches. Elle lève aussi sur `nb_parties = 0`. Un seul site calcule un budget :
`parties_pour_separer_un_taux` et `ecart_de_taux_detectable` ne sont appelés nulle part dans
`rapport_phase2.py`, qui passe quatre fois par `budget_d_un_compteur`. **19 lignes sur 34** du
§6 portent `(hors budget)`, conforme.

## Ce que je devais — mon 7,33 %

Numérateur, dénominateur, échantillon, graines, et la réponse.

Mon chiffre du tour 1 était mesuré sur **trois greedys**, jamais nommés. `audit/phase2/coherence_horizon.py`,
instance `entrainement-3j`, donnes 0 à 3 399, départage `Random(777)` partagé, adversaires
uniformes `Random(3000000 + 3 × donne + siège)`, dénominateur « nœud de ciblage où au moins un
Assassin reste en attente », argmax myope contre argmax cohérent comparés comme **ensembles** :

| Population | Numérateur / dénominateur | Taux | IC 99 % exact | Sièges-parties mesurés | Parties jouées |
|---|---:|---:|---|---:|---:|
| trois greedys | 287 / 4 145 | **6,92 %** | [5,95 ; 8,00] | 10 200 | 3 400 |
| un greedy, deux uniformes | 204 / 4 145 | **4,92 %** | [4,10 ; 5,85] | 10 200 | 10 200 |

**L'unité de l'échantillon est le siège-partie mesuré, pas la partie jouée**, et les deux
diffèrent d'un facteur trois entre les deux protocoles : à trois greedys une seule partie par
donne suffit et ses trois sièges sont mesurés, à un greedy la donne est rejouée trois fois avec
un siège mesuré à chaque fois. Les deux colonnes de droite le montrent, et c'est l'égalité des
**10 200 sièges-parties** — non celle des parties jouées — qui rend les deux taux comparables.

**Le dénominateur 4 145 est bien le même pour les deux, et c'est structurel.** Chaque joueur
joue ses trois cartes à chaque tour (§3.2) et recomplète sa main depuis une pioche fixée par la
donne (§3.3) : la main d'un siège à un tour donné est donc déterminée par la **seule donne**, et
avec elle le nombre d'Assassins qu'il pose. MESURÉ sur 40 donnes et trois compositions —
trois greedys, un greedy contre deux uniformes, trois uniformes — le vecteur des Assassins en
main est **identique dans les trois cas**. Sur les mêmes donnes les deux populations offrent
donc exactement les mêmes nœuds ; seul le contenu du plateau y diffère. Ce n'est pas un report
recopié d'une population à l'autre, et c'est désormais tenu par un test plutôt que supposé.

Mon 7,33 % tombe dans le premier intervalle, son 4,23 % dans le second, et les deux ne se
recouvrent pas. Son échantillon fait 4 063 nœuds sur 10 002 sièges-parties de campagne B, le
mien 4 145 sur 10 200 — soit **0,4062 contre 0,4064 nœud par siège-partie mesuré**, ce qui
achève d'établir que la définition du dénominateur est identique à la sienne.

Les deux nombres sont justes. **C'est le mien qui était mal étiqueté** : j'ai publié un taux
sans nommer sa population, la faute exacte que je reprochais ailleurs. Le point est clos et il
m'appartient.

**Réserve 3, sur mon propre harnais, relevée après le verdict.** Mon champ s'appelait `parties`
et comptait des itérations — 3 400 et 10 200 —, si bien que ma phrase « 0,406 contre 0,407 nœud
par partie » nommait une unité qui n'était pas celle du calcul, et juxtaposait de surcroît mon
chiffre et le sien comme s'ils venaient du même protocole. Aucune conclusion ne change : les
deux taux, leurs bornes et leur non-recouvrement sont inchangés. Mais c'est le critère de cette
phase entière appliqué à ma propre table, et il fallait qu'il y passe aussi.

## Réserves — aucune ne change une conclusion

| # | Gravité | Réserve | Où | Preuve |
|---|---|---|---|---|
| 1 | mineur | Le §4 bis écrit « **Trois** compteurs de B4 sont jugés par cette même évaluation myope ». Le code en montre **quatre** : `b4` décide `B4-strict`, `B4-departage`, `B4-contre-nature` **et** `B4-meurtre-couteux` sur des comparaisons de `decision.valeurs`, produit par `evaluer_actions` ; seuls `B4-brut` et `B4-tout-dos` ne lisent aucune valeur. Et **aucun des quatre n'est nommé** : le lecteur est renvoyé à la section 5. L'omis est `B4-meurtre-couteux`, c'est-à-dire l'un des deux zéros absolus du rapport | `mesure/resultats/phase2.md` §4 bis ; `mesure/comportements.py` `b4` | MESURÉ : test `test_p3_les_compteurs_juges_par_l_evaluation_myope_sont_QUATRE_et_nommes`, **rouge** |
| 2 | mineur | L'inclusion `B1-collectif ≥ B1-motif` — celle dont la chute a déjà révélé un compteur faux — est vérifiée par le rapport sur les **deux anciennes** colonnes (7 008 ≥ 4 794 et 20 157 ≥ 10 836) et **pas sur la troisième population**, qui est précisément celle qui existe pour `B1-collectif`. Le §5 bis ne publie pas `B1-motif` au grain du couple à trois greedys, donc le lecteur ne peut pas la refaire | `mesure/rapport_phase2.py:678-683` ; §5 bis du rapport | MESURÉ par moi à 600 donnes : **3 916 ≥ 2 528**, même grain — l'inclusion tient, mais personne ne la publie |

## Hors des sept points — signalé, non compté au verdict

Mes trois mineurs du tour 1 non listés ce tour-ci, et leur état MESURÉ :

- **encodage** : `mesure/resultats/phase2.md` est toujours en cp1252 quand les quatre autres
  documents de la phase sont en UTF-8. Toujours ouvert.
- **`vue_du_joueur` publique** : `vue_du_joueur(etat, -1)` et `(etat, 3)` ne lèvent toujours
  pas. Toujours ouvert.
- **deux tautologies comptées comme deux prédictions** : le §0 des concurrentes annonce
  toujours « Onze tiennent » avec ✅ sur les lignes 8 et 9, sans dire qu'elles étaient nulles
  par construction — ce que la pré-inscription écrit pourtant elle-même. Toujours ouvert.
- **la cellule sans nombre** : « voir `B4-departage` » est toujours dans la table du §4.
  Toujours ouvert.

## Justification du verdict

Aucun défaut bloquant ne subsiste, donc **ACCEPTÉ SOUS RÉSERVE**. Les quatre défauts du tour 1
sont corrigés, et trois des quatre le sont **avec la parade qui empêche la correction de se
défaire** : une levée d'exception plutôt qu'une cellule réécrite, un invariant asserté plutôt
qu'une convention, une fonction unique plutôt que trois sites. C'est la différence entre une
correction et un correctif.

Les deux réserves sont de la même famille et je les nomme ensemble : **un compte à la place de
noms**. « Trois compteurs de B4 » sans les nommer, et une inclusion vérifiée « sur les deux
colonnes » qui n'en compte plus deux depuis qu'il y en a trois. Ni l'une ni l'autre ne déplace
un chiffre publié ; les deux se referment en écrivant quatre noms et une ligne de plus.

Je note pour la suite que le point le plus rentable de ce tour n'a été trouvé ni par le
constructeur ni par moi, mais par la relecture humaine — et que la vérification qui l'a laissé
passer était un A7 réussi. **Un chiffre qui se reconstruit n'est pas un chiffre juste** ; il
n'est juste que si son unité a été reconstruite d'abord, séparément.
