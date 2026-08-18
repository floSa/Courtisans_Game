# Audit — phase 1, mesure de l'instance `entrainement-3j`

| Tour | Livrable | Verdict |
|---|---|---|
| Audit initial | `3f5b75d` | **REJETÉ** — 1 défaut bloquant, 5 mineurs |
| Re-vérification | `d7398bd` | **ACCEPTÉ SOUS RÉSERVE** — 6 défauts sur 6 corrigés, 2 réserves mineures |

Format : §3 de [08_modele_compte_rendu.md](../documentations/08_modele_compte_rendu.md).
Méthode : [07_protocole_audit_croise.md](../documentations/07_protocole_audit_croise.md).
Auditée : branche `claude/courtisans-phase-1-measure-3900b7`, base `e3bdd42`. Périmètre
vérifié : `mesure/` et `tests/mesure/` seuls, aux deux tours.

Le corps de ce document est l'audit initial, **conservé tel quel** : c'est lui qui a produit
la liste de défauts, et l'effacer effacerait la trace de ce qui a été trouvé. La
re-vérification est à la fin.

Un seul motif de rejet au premier tour : **une affirmation fausse dans le compte rendu**, au
sens de 07 §3. Les trois critères de go/no-go étaient satisfaits dès ce tour-là et revérifiés
par l'auditeur — l'instance était bonne, c'est un chiffre qui ne l'était pas.

---

## Avertissement sur l'échantillon — à lire avant tout chiffre

Une campagne est définie par **deux** paramètres, pas un : les graines de donne, et le
**décalage de politique** qui dérive le générateur des choix. Deux campagnes de mêmes graines
et de décalages différents jouent les **mêmes donnes** mais **pas les mêmes parties**, et
rendent donc des chiffres différents, tous deux justes.

| Décalage | Valeur | Emploi |
|---|---|---|
| `DECALAGE_CONSTRUCTEUR` | `1 000 000` | ses parties exactes. **Tout chiffre opposé au sien est calculé avec celui-là** |
| `DECALAGE_AUDITEUR` | `10**9` | mes campagnes propres, dont le contrôle de stabilité H2 |

**Ma première rédaction a confondu les deux** : elle annonçait 70 événements invisibles dans
66 parties (mon décalage) puis 81 dans 75 parties (le sien) sur les mêmes seeds 0–999, sans
dire que l'échantillon différait. Ce n'était ni un grain ni une définition : mêmes 1 000
donnes, mais la politique ne fait pas les mêmes choix, donc les cartes ne vont pas aux mêmes
endroits. Les deux comptes sont justes ; leur juxtaposition sans étiquette ne l'était pas.

Cause racine dans mon propre code : le décalage était un littéral en dur dans le corps de
`joue_campagne` — **exactement le défaut A6 que cet audit reproche au constructeur**, commis
ici. Il est désormais un paramètre nommé, le relevé imprime son échantillon, et les deux
comptes sont épinglés par
[tests/audit/test_echelle_de_l_invisible.py](../tests/audit/test_echelle_de_l_invisible.py).

---

## Constats

| # | Contrôle | Résultat |
|---|---|---|
| A1 | Tests rejoués moi-même | **39/39** annoncés verts dans `tests/mesure`, **635/635** sur toute la suite. Les **deux** fichiers de résultats se rejouent à l'identique : 0 ligne différente sur 174, hors lignes de temps mural |
| A2 | Tests relus contre la spec | **1** assertion sur 39 tests vérifie le code au lieu de la règle |
| A3 | Tests hostiles écrits par moi | **16** — 16 verts, dont 1 ignoré hors de la branche du constructeur (2 rouges au départ, sur **mes** attendus) + 2 contrôles hors suite (820 couples Clopper-Pearson, 5 blocs de 1 000 parties) |
| A4 | Critères d'acceptation revérifiés | **3/3** go/no-go, **4/4** statistiques exigées par 05 §3 |
| A5 | Niveaux de preuve | **0** DÉDUIT présenté comme MESURÉ — mais **1 MESURÉ faux**, et **0** affirmation préfixée dans le compte rendu, contre 4 SUPPOSÉ correctement posés dans la pré-inscription |
| A6 | Valeurs en dur, duplications | **2** chez lui — l'instance définie 3 fois ; 4 littéraux dans les décompositions du rapport. **1 chez moi**, corrigée : le décalage de politique en dur |
| A7 | Chiffres reconstruits | **17 groupes de chiffres sur 18** reconstruits par une implémentation écrite indépendamment, dont les trois du go/no-go. Le 18ᵉ est le zéro, et il est faux |

---

## Défauts

| # | Gravité | Défaut | Où | Preuve |
|---|---|---|---|---|
| 1 | **bloquant** | « 0 sur 1 000 R2 invisibles des trois joueurs » est **faux**. Le calcul agrège les 4 familles en un booléen de partie **avant** de comparer les vues : il compte « une partie où la vérité a un R2 et où aucun siège n'a de R2 sur *aucune* famille ». La vérité en a un dans 96 % des parties et chaque siège dans ~93 % : la conjonction est quasi impossible par construction. Le chiffre ne mesure pas ce que sa phrase dit | `mesure/rapport.py:395` et `:402` ; annoncé en `mesure/resultats/seeds_0_999.txt:133`, `:131` du fichier de contrôle, et dans le corps du commit `ba65ae6` | MESURÉ, échelle ci-dessous |
| 2 | mineur | Assertion tautologique : l'attendu est recalculé par **la même expression** que l'implémentation | `tests/mesure/test_parties_construites.py:309` | MESURÉ : les deux expressions sont littéralement identiques |
| 3 | mineur | L'instance `entrainement-3j` est définie **trois** fois, et rien ne vérifie qu'elles concordent | `tests/outils.py:175`, `mesure/rapport.py:44`, `tests/mesure/test_parties_construites.py:36` | MESURÉ : les trois construisent la même configuration ; aucun test ne les compare |
| 4 | mineur | Quatre littéraux en dur dans les **décompositions** du rapport — les chaînes qui rendent les chiffres reconstructibles. `CARTES_PAR_TOUR`, `factorial(3)`, `len(Position)` existent | `mesure/rapport.py:193`, `:196`, `:202`, `:218` | MESURÉ : `CONFIG.cartes_jouees // 3` ligne 218 est faux dès que `CARTES_PAR_TOUR ≠ 3` |
| 5 | mineur | Le seuil D2 « ≥ 8 valeurs distinctes » n'a **aucun pouvoir discriminant** à 1 000 parties : le nombre de valeurs distinctes croît avec N, et le seuil est franchi dès **N = 12 parties** | `mesure/hypothese_et_instrument.md:143` | MESURÉ : min sur les 3 sièges = 4 (N=5), 7 (N=11), **8 (N=12)**, 11 (N=20), 25 (N=1000) |
| 6 | mineur | `intervalle_clopper_pearson` ne valide pas `n > 0` : `(0, 0)` rend `(0.0, 1.0)` sans lever. C'est la fonction qui prononce le go/no-go | `mesure/rapport.py:88`, `:152` | MESURÉ : appel exécuté, rend `(0.0, 1.0)` |

### Preuve du défaut 1 — le même « invisible » à trois niveaux d'agrégation

Mêmes seeds, **décalage `1 000 000`, donc ses parties exactes**. Grain de référence, sa
définition de R2.

```
                                        seeds 0-999   seeds 1000-1999
niveau 1  partie, familles confondues        0             0        <- SON chiffre
niveau 2  famille par famille            5/4000        11/4000
niveau 3  evenement par evenement         81 ev.        61 ev.
          dans                          75/1000       57/1000  parties
```

Le niveau 2 est calculé **avec son propre code et sa propre définition**, en retirant la
seule agrégation des familles. Cinq témoins nommés au bloc 1 : seeds **308** (f1), **453**
(f3), **496** (f3), **539** (f2), **933** (f0). Sur le seed 933, la vérité de f0 fait
`Indifférente → Obscurité → Indifférente` tandis que J0 voit `Indifférente → Lumière` — le
**signe opposé** — J1 reste en Obscurité et J2 en Indifférente. Aucun des trois ne voit le
retournement ; la partie est comptée « vue » parce que la famille 3 en avait un, visible.

Le niveau 3 est mon compteur : 75/1000, **IC99 [5,51 % ; 9,90 %]**. La borne basse exclut 0.

**Dans les deux lectures possibles de sa propre phrase** — R2 comme propriété de famille, ou
R2 comme événement — le chiffre est non nul. Le zéro ne correspond à aucune des deux.

Le plus net : **son propre test est un témoin du phénomène que son rapport déclare à zéro.**
`tests/mesure/test_parties_construites.py:154` affirme, sur une partie construite, que les
trois sièges n'ont pas R2 sur la famille 3 et que la vérité l'a — et sa docstring écrit
« **C'est un retournement que personne ne pouvait planifier** ». Le test et le rapport sont
dans le même livrable et se contredisent. Le cas survient dans **une partie sur treize à
dix-huit** (75/1000 = 1 sur 13,3 ; 57/1000 = 1 sur 17,5), et se construit à la main en
quatre poses.

Pour mémoire, sous mon propre décalage la fréquence est du même ordre : 66, 84, 53, 58, 53
parties sur 1 000 selon le bloc, soit une partie sur 11,9 à 18,9. Aucun des sept blocs
mesurés ne donne zéro.

---

## Ce que j'ai cherché et n'ai pas trouvé

- **Le calcul de statut.** Réimplémenté depuis les §2.2 et §5 — banquet seul, en valeur,
  vivantes seules, famille sans carte au banquet Indifférente, dos adverse contribuant zéro
  dans une vue de siège. **11 000 comparaisons, 0 désaccord.** Une erreur de lecture partagée
  aurait été invisible à ses mutations ; il n'y en a pas.
- **La définition du retournement.** La mienne, écrite avant de lire la sienne, est **son R2
  mot pour mot**. **Trois lectures indépendantes du §2.2 convergent** — la sienne,
  l'arbitrage, la mienne. Sur le point exact où le seuil « une partie sur trois » se satisfait
  ou se rate, le corpus documentaire suffit à produire deux fois la même définition sans se
  parler.
- **L'intervalle de confiance.** Quatre calculs indépendants — sa bissection, mon quantile
  Beta, ma bissection sur les queues binomiales exactes, `scipy.binomtest` — donnent
  **[94,1214 % ; 97,4240 %]** pour 960/1 000. Sur **820 couples `(k, n, α)`**, écart maximum
  **2,5 × 10⁻¹²**. Le bug qu'il déclare avoir trouvé dans sa bissection est réellement
  corrigé, et le piège est documenté à la bonne ligne.
- **Le seuil D2 et son amplitude estimée de tête.** Sa prémisse était « un domaine reçoit ~8
  cartes de valeur 1 ou 2 ». MESURÉ : **6,99 cartes vivantes par domaine** en fin de partie,
  sur 600 domaines. L'estimation tenait, et pour la bonne raison. Le défaut 5 porte sur le
  pouvoir discriminant du seuil, pas sur l'estimation.
- **Le piège « ce chiffre dit-il ce qu'un agent saura planifier ? »** Il ne tombe pas dedans.
  `mesure/hypothese_et_instrument.md:207`, écrit avant la mesure : « L'aléatoire n'est pas le
  jeu […] Elle n'établit pas qu'un agent pourra en planifier un (comportement B1) ». Aucune
  surinterprétation à signaler.

---

## Défauts du DOCUMENT — `05_protocole_experimental.md`, pas du constructeur

| # | Terme non défini | Conséquence |
|---|---|---|
| P1 | **« retournement »** (§3, phase 1, Go/no-go) | Le seuil « une partie sur trois » se satisfait ou se rate selon la définition. Ici toutes le franchissent — 100 % (R0), 73 % (R1), 96 % (R2), 86 % (R3) — mais c'est une chance, pas une propriété du protocole |
| P2 | **« distribution non dégénérée »** (même ligne) | Aucun seuil. Les critères D1–D4 sont une proposition de l'agent, et il l'écrit |
| P3 | **« situations où refuser de tuer est possible »** (§3, Rapport attendu) | La lecture littérale est **vide** : refuser est *toujours* légal (§4.1, arbitrage R2), donc la fréquence vaut 100 % par construction. Seule la lecture « nœuds où une cible existe » a un contenu |

Une quatrième, moins grave : le §3 présente « 20 cartes et 2 tours, ou 40 cartes et 4 tours »
comme un arbitrage à trancher en phase 1. Ce n'en est pas un — la variante à 20 cartes est
refusée à la construction par le plancher `tours ≥ 3` du §8 des règles (MESURÉ : H4b).

---

## Justification du verdict

Les sept contrôles convergent, sauf sur un point. L'instrument est solide : sa suite se rejoue
entière (635/635), ses deux rapports se rejouent au chiffre près, son intervalle est exact à
10⁻¹², sa définition du retournement est celle que j'ai écrite indépendamment, et son calcul
de statut est celui que j'ai réécrit depuis les règles — 11 000 comparaisons sans un
désaccord. Les trois critères de go/no-go sont satisfaits et remesurés : `(4,4,4)` dans 5 000
parties sur 5 000, distribution large et stable, retournements à 94,0–95,5 % selon le bloc
contre un seuil de 33,3 %.

Le rejet ne porte donc ni sur l'instance, qui est bonne, ni sur la mesure, qui est
reproductible. Il porte sur **un chiffre dont la phrase ne décrit pas le calcul**, et c'est
exactement la faute qui a coûté trois mois à ce projet : un nombre juste au sens où il se
recalcule, faux au sens où il ne mesure pas son propre énoncé. Ce zéro est le seul absolu du
rapport, c'est celui qu'un lecteur retient, et c'est celui qui compte pour la phase 2 — s'il
était vrai, il dirait qu'aucun retournement n'échappe structurellement à tous les joueurs,
donc que rien ne limite ce qu'un agent peut apprendre à anticiper. Il est faux : le cas
survient dans une partie sur treize à dix-huit, il se construit en quatre poses, et **son
propre test le démontrait déjà**.

Correction attendue : compter l'invisible sans agréger les familles, publier les deux niveaux,
et relire le §5.3 de sa pré-inscription — « cette part-là ne peut être anticipée par personne
d'autre que le poseur » — qui est lui aussi trop fort, puisqu'il existe des retournements que
**même le poseur** ne voit pas. L'auditeur ne corrige rien.

---

## Rejouer

```bash
UV_LINK_MODE=copy uv run pytest tests/audit -q
```

```bash
UV_LINK_MODE=copy uv run python -m mesure.rapport --parties 1000 --depart 0
```

Le code d'audit est dans `audit/` et `tests/audit/`. Ni le moteur, ni l'instance, ni les
documents ne sont modifiés. `mesure/` et `tests/mesure/` appartiennent au constructeur : ils
ont été importés dans le worktree pour rejouer sa suite, jamais ajoutés à cet arbre — les
contrôles hostiles sont autonomes, et le seul test qui a besoin de son code s'ignore
proprement en son absence.

---

# Re-vérification — `d7398bd` — VERDICT : ACCEPTÉ SOUS RÉSERVE

Étape 6 du cycle de 07 §4 : **uniquement les défauts listés**. Aucun front nouveau n'est
ouvert, et les deux observations hors liste sont étiquetées comme telles.

A1 sur la correction : **52/52** tests de mesure, **648/648** sur toute la suite — conforme à
son annonce. Mes **16** contrôles hostiles restent verts contre son code corrigé.

## Les six défauts

| # | Gravité initiale | État | Preuve de la re-vérification |
|---|---|---|---|
| 1 | bloquant | **corrigé** | `compter_invisible` (`mesure/partie.py`) ne compare plus que des grandeurs non agrégées, et publie les deux niveaux avec leurs dénominateurs. **Mon compteur, écrit indépendamment, tombe exactement d'accord au même grain** : 81 événements invisibles sur 2 735, dans 75 parties (seeds 0–999, grain fin) et 61 sur 2 601 dans 57 parties (seeds 1000–1999). Ses chiffres publiés — 79/2 665 dans 74 parties, et 56/2 531 dans 56 — sont au grain **tour**, son grain de référence déclaré. **Il n'y a donc aucun désaccord** : deux implémentations indépendantes rendent le même nombre au même grain. La phrase fausse a disparu du rapport, et la section porte désormais l'explication du défaut |
| 2 | mineur | **corrigé** | La tautologie est remplacée par une donnée écrite à la main : `replace(..., cibles_par_noeud=(0, 1, 5, 0))` puis `assert noeuds_avec_cible == 2`. L'attendu ne réutilise plus la formule testée |
| 3 | mineur | **corrigé, avec réserve** | Ses deux définitions deviennent une seule, `mesure/instance.py::ENTRAINEMENT_3J`, importée par le rapport et par ses tests. La troisième, `tests/outils.py`, est conservée **volontairement** et l'argument est écrit : un oracle qui recalcule l'arithmétique des règles sans importer le moteur ne doit pas être l'objet qu'il vérifie. L'argument est juste. **Réserve** : rien ne compare les deux jeux de paramètres, donc une dérive resterait muette — une assertion d'égalité des quatre valeurs préserverait l'indépendance de l'oracle tout en fermant ce trou |
| 4 | mineur | **corrigé** | Les quatre littéraux sont lus dans `CARTES_PAR_TOUR`, `factorial(CARTES_PAR_TOUR)` et `len(Position)`. Plus aucun `3`, `6` ou `2` en dur dans les décompositions |
| 5 | mineur | **corrigé, et étendu** | Le rapport mesure et affiche le pouvoir discriminant des quatre critères. Il va plus loin que mon constat : D2 est satisfait dès 12 parties, **mais D1 et D3 dès 3, et D4 dès 1**. Les quatre sont annotés « discrimine peu ». Mon constat portait sur D2 seul ; il l'a généralisé contre lui-même |
| 6 | mineur | **corrigé** | `intervalle_clopper_pearson` refuse `n <= 0` avec un message explicite. Vérifié : les deux implémentations lèvent maintenant sur `(0, 0)`, et concordent toujours sur `960/1000` |

Le §5.3 de la pré-inscription porte un **erratum** qui conserve la phrase fausse plutôt que
de la remplacer, en expliquant pourquoi elle l'était : « personne d'autre que le poseur »
supposait un témoin unique par Espion, ce que deux poseurs distincts sur une même famille
démentent. C'est la bonne façon de traiter une phrase qui a orienté un compteur.

## Contrôle hostile de la correction elle-même

Une correction qui n'est pas sous test peut se défaire au commit suivant. J'ai donc
ré-introduit **la faute exacte** dans `compter_invisible` — le comptage réagrège les familles
avant de comparer les vues — et rejoué sa suite.

MESURÉ : **1 test rouge**,
`tests/mesure/test_parties_construites.py::test_le_comptage_invisible_sur_la_partie_1_construite_a_la_main`,
sur une partie construite à la main, avec le bon message (`familles_invisibles: 0 != 1`).
Fichier restauré, empreinte inchangée. La correction est tenue par un test, pas seulement
appliquée.

## Les trois chiffres du go/no-go, inchangés

MESURÉ sur `d7398bd` : 1 000/1 000 parties à `(4, 4, 4)` tours ; 10/10 critères de
non-dégénérescence ; R2 grain tour vue vraie **96,00 % (960/1 000), IC99
[94,12 % ; 97,42 %]**. La correction ne touchait pas le go/no-go, et elle ne l'a pas touché.

## Réserves

1. **Défaut 3, résiduel** : rien ne relie `mesure/instance.py::ENTRAINEMENT_3J` à
   `tests/outils.py::ENTRAINEMENT_3J`. L'indépendance de l'oracle est justifiée ; l'absence
   de garde-fou contre la dérive ne l'est pas.
2. **Hors liste, signalé sans être compté comme défaut** : dans la section 6 du rapport, le
   grain est nommé une fois, sur le bloc « Rappel non comparable », et n'est répété ni sur
   `NIVEAU FAMILLE` ni sur `NIVEAU EVENEMENT`. Un lecteur qui reconstruit 2 078 familles au
   grain fin au lieu de 2 075 au grain tour ne peut pas savoir laquelle des deux lectures est
   la sienne. C'est exactement la faute que j'ai commise dans mon propre rapport et corrigée
   au commit `14e5123` : **un chiffre doit porter son échantillon, grain compris.**

Les trois défauts du **document** `05_protocole_experimental.md` — P1, P2, P3 ci-dessus —
restent entiers. Ils ne relèvent pas du constructeur et ne gagent pas ce verdict, mais ils
doivent être portés au journal : les définitions qu'il a dû proposer pour mesurer quoi que ce
soit ont tenu deux tours d'audit, et leur place est dans le protocole.

## Justification du verdict de re-vérification

Les six défauts sont corrigés, dont le bloquant, et deux le sont mieux que demandé : le
défaut 5 est étendu aux quatre critères contre son propre intérêt, et le défaut 1 est mis
sous test par une partie construite à la main — ce que j'ai vérifié en ré-introduisant la
faute. Le chiffre qui portait le rejet est désormais publié aux deux niveaux d'agrégation, et
mon implémentation indépendante rend le même nombre au même grain. Il ne reste que deux
points mineurs, dont un que le constructeur a explicitement argumenté. **ACCEPTÉ SOUS
RÉSERVE**, réserves reportées au journal ; la phase 1 est close et la phase 2 s'ouvre sur
`entrainement-3j`.
