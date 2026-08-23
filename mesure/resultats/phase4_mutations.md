# Phase 4, etape 0 -- le perimetre des mutations, etendu a `agents/` et `mesure/`

**MESURE le 23/08/2026**, `uv run python outillage/mutation.py`, sur la suite complete
(`tests`, 1 172 cas). Une mutation = une passe entiere de la suite. Chaque ligne porte le
nombre de tests verts et rouges que la mutation a produits.

> **Ce document ne juge pas l'agent.** Il juge la SUITE DE TESTS. Une mutation qui survit
> ne dit rien du code mute -- elle dit que rien ne le tient.

## Le compte

| | mutations | detectees | **survivantes** | expirees |
|---|---:|---:|---:|---:|
| `courtisans/` -- les 20 d'origine | 20 | 20 | **0** | 0 |
| `agents/` (hors `greedy.py`) -- neuves | 20 | 11 | **9** | 0 |
| `mesure/` -- neuves | 17 | 14 | **2** | 1 |
| **total** | **57** | **45** | **11** | **1** |

**`agents/greedy.py` porte 0 mutation**, et c'est le seul invariant que la regle du §0.3
protegeait : c'est l'etalon de toutes les phases. L'exemption est desormais une **donnee**
que `principal` verifie -- `FICHIERS_EXEMPTS` --, pas une phrase de docstring.

**Les 20 mutations du coeur sont toutes detectees, comme en phase 3.** Ce qui change, c'est
qu'on sait maintenant ce que ce chiffre ne disait pas : sur les 37 mutations neuves, **11
survivent**. Le code qui entraine et le code qui mesure sont tenus bien moins serre que le
moteur -- et c'est exactement l'endroit ou la phase 2 s'est trompee, avec un facteur trois
indu qui vivait dans le generateur et a survecu a deux verifications reussies.

## Le troisieme verdict : `EXPIRE`

`masse-binomiale-part-de-zero` n'a **pas rendu de verdict**. Elle fait partir la recurrence
de la loi binomiale de `k = 0` au lieu du mode ; pour les `n` de l'ordre de 10 000 des
calculs de puissance, le premier terme vaut `1e-1760` -- zero en flottant --, la loi entiere
se normalise a partir de rien, et un balayage qui cherche le `n` d'une puissance cible ne
converge jamais.

**La premiere campagne a tourne 2 h 48 sur cette seule mutation**, la ou une passe prend
169 s, parce que `_jouer` appelait `subprocess.run` sans `timeout`. Corrige : delai de garde
a 15 minutes, et un **troisieme etat**. Un blocage n'est ni « detectee »
ni « survit » : l'appeler « detectee » compterait comme un succes de la suite un arret sans
verdict, l'appeler « survit » designerait un trou de test qui n'est pas celui-la.

> **Et il dit quelque chose de la suite, pas seulement de la mutation.** `tests` n'a **aucun
> delai de garde propre** : un test qui boucle y est indiscernable d'un test lent. C'est un
> trou de meme nature que les onze ci-dessous, et il n'est pas comble par ce document.

## Les 11 survivantes -- ce que chacune apprend

| Fichier | Mutation | Ce qu'aucun test ne tient |
|---|---|---|
| `agents/perception.py` | `perception-decide-sur-un-noeud-de-chance` | un agent appele sur un noeud de chance ou terminal recoit une Perception au lieu d'une levee |
| `agents/reseau.py` | `valeur-non-aplatie` | la tete de valeur rend (n, 1) au lieu de (n,) : la MSE contre des retours (n,) diffuse en matrice n x n sans rien lever |
| `agents/politique_reseau.py` | `politique-reseau-observe-le-siege-zero` | l'agent decide sur le tenseur du siege 0 quel que soit le siege qu'il occupe -- il voit la main d'un autre |
| `agents/entrainement.py` | `avantage-sans-ligne-de-base` | la tete de valeur ne sert plus de ligne de base a l'avantage : le critique n'entre plus dans le gradient de politique |
| `agents/entrainement.py` | `tete-plus-grande-que-l-espace-d-action` | la tete du reseau ne fait plus la taille de l'espace d'action du moteur, et le controle `max(legal_actions) >= nb_actions` ne mord pas |
| `agents/campagne.py` | `garde-fou-se-contente-d-un-ecart-etabli` | le defaut v5 : un EFFONDREMENT etabli rassure le garde-fou au lieu de le declencher |
| `agents/campagne.py` | `garde-fou-sans-bonferroni` | huit regards au risque nominal de 1 % : le risque global monte a ~8 % |
| `agents/campagne.py` | `pool-garde-les-plus-anciens` | le plafond du pool jette le checkpoint le plus RECENT : le pool se remplit des versions les plus faibles |
| `agents/campagne.py` | `intitule-du-garde-fou-sans-population` | retour du defaut 5 : le nom ne porte plus ni l'agent, ni les donnes, ni les seeds, et deux campagnes distinctes redeviennent homonymes |
| `mesure/phase3.py` | `adversaires-partagent-un-alea` | les deux adversaires partagent un generateur : ils jouent de facon correlee, ce qui n'est pas la composition annoncee |
| `mesure/phase3_mesure.py` | `separation-exacte-toujours-disjointe` | toute ligne portant un zero est declaree separable, meme quand les deux bornes se croisent |

**Quatre d'entre elles tombent sur la tete de valeur et sur ce qui l'entoure** --
`valeur-non-aplatie`, `avantage-sans-ligne-de-base`, `tete-plus-grande-que-l-espace-d-action`,
`politique-reseau-observe-le-siege-zero`. C'est le composant que l'iteration 1 vient reparer,
et il n'est tenu par aucun test de forme ni de cablage. **Rien dans la suite n'etablit
aujourd'hui que la tete de valeur sert de ligne de base a PPO** : annuler sa contribution a
l'avantage ne fait tomber aucun cas.

**Quatre autres sont dans le garde-fou** -- le meme garde-fou qui a porte cinq defauts
successifs en phase 3. Le plus instructif est `garde-fou-se-contente-d-un-ecart-etabli` : le
predicat `progres_etabli` **a** sa parade, un cas lui passe un effondrement, mais le **site
d'appel** n'en a aucune. Remettre `apparie.etabli` a la place de `apparie.progres_etabli`
dans `campagne.entrainer` ne fait rien tomber. La correction du cinquieme defaut tient sur le
predicat, pas sur son cablage -- et c'est mot pour mot le mode de retour que le §0.2 decrit.

`intitule-du-garde-fou-sans-population` est la **reserve 3 mesuree** : ramener l'intitule a
la chaine generique -- l'etat exact du defaut 5 avant sa correction -- ne fait tomber aucun
test, parce que la parade ne lit que les expressions `intitule=` et que le pool passe par
`intitules_hors_pool=`.

`separation-exacte-toujours-disjointe` est dans le code de la **reserve 2** : la regle des
bornes exactes, ecrite au tour 2 pour remplacer un verdict non calcule, n'est elle-meme
tenue par aucun cas.

## Ce que ce document N'ETABLIT PAS

- **Il ne dit pas que les 45 detections sont de bonnes detections.** « Un test tombe » n'est
  pas « le bon test tombe pour la bonne raison ». Les rouges vont de **1 a 79**, mediane
  **5** ; une detection a un seul rouge peut etre fortuite.
- **Il ne mesure aucune couverture.** 37 mutations sur ~2 500 lignes est un echantillon
  choisi par moi, pas un balayage. Un trou qu'aucune de mes 37 ne vise reste invisible.
- **Il ne comble aucun des 11 trous.** Les combler est un travail a part, et le §0.2
  interdit de fabriquer un test a la hate pour faire tomber un survivant sans dire ce qu'il
  a appris.

## Reproduire

```
UV_LINK_MODE=copy uv run python outillage/mutation.py
```

Reprise partielle, sans rejouer ce qui a deja rendu un verdict :

```
UV_LINK_MODE=copy uv run python outillage/mutation.py --noms nom1,nom2
```

## Le releve brut, les 57

| Mutation | Fichier | Verts | Rouges | Verdict |
|---|---|---:|---:|---|
| `espions-adverses-visibles` | `courtisans/infoset.py` | 1095 | 77 | detectee |
| `phase-et-assassin-absents` | `courtisans/infoset.py` | 1150 | 22 | detectee |
| `residu-compte-les-morts` | `courtisans/infoset.py` | 1164 | 8 | detectee |
| `meurtre-obligatoire` | `courtisans/engine.py` | 1108 | 64 | detectee |
| `fin-joueur-par-joueur` | `courtisans/engine.py` | 1093 | 79 | detectee |
| `noble-vaut-un` | `courtisans/cards.py` | 1127 | 45 | detectee |
| `points-au-poseur` | `courtisans/rules.py` | 1142 | 30 | detectee |
| `morts-comptes-au-decompte` | `courtisans/engine.py` | 1149 | 23 | detectee |
| `main-non-triee` | `courtisans/rules.py` | 1156 | 16 | detectee |
| `doublons-non-masques` | `courtisans/rules.py` | 1160 | 12 | detectee |
| `observation-sans-joueur` | `courtisans/engine.py` | 1099 | 73 | detectee |
| `observateur-absent` | `courtisans/openspiel_adapter.py` | 1155 | 17 | detectee |
| `libelle-de-cible-ambigu` | `courtisans/openspiel_adapter.py` | 1157 | 15 | detectee |
| `libelle-nomme-un-dos` | `courtisans/openspiel_adapter.py` | 1162 | 10 | detectee |
| `bornes-de-joueurs-desynchronisees` | `courtisans/openspiel_adapter.py` | 1171 | 1 | detectee |
| `player-obligatoire` | `courtisans/openspiel_adapter.py` | 1168 | 4 | detectee |
| `chaine-de-jeu-sans-config` | `courtisans/openspiel_adapter.py` | 1160 | 12 | detectee |
| `roles-separes-par-virgule` | `courtisans/openspiel_adapter.py` | 1159 | 13 | detectee |
| `tours-arrondis-au-dessus` | `courtisans/config.py` | 1121 | 51 | detectee |
| `vue-du-joueur-contourne-la-parade` | `courtisans/infoset.py` | 1128 | 44 | detectee |
| `perception-nomme-les-dos` | `agents/perception.py` | 1097 | 75 | detectee |
| `perception-decide-sur-un-noeud-de-chance` | `agents/perception.py` | 1172 | 0 | **SURVIT** |
| `masque-laisse-une-probabilite-aux-illegales` | `agents/reseau.py` | 1166 | 6 | detectee |
| `tirer-ne-verifie-plus-la-somme` | `agents/reseau.py` | 1171 | 1 | detectee |
| `valeur-non-aplatie` | `agents/reseau.py` | 1172 | 0 | **SURVIT** |
| `deterministe-ignore-le-masque` | `agents/reseau.py` | 1171 | 1 | detectee |
| `politique-reseau-observe-le-siege-zero` | `agents/politique_reseau.py` | 1172 | 0 | **SURVIT** |
| `charger-laisse-le-reseau-en-entrainement` | `agents/politique_reseau.py` | 1171 | 1 | detectee |
| `gain-du-siege-zero` | `agents/entrainement.py` | 1171 | 1 | detectee |
| `noeuds-du-pool-collectes` | `agents/entrainement.py` | 1171 | 1 | detectee |
| `avantage-sans-ligne-de-base` | `agents/entrainement.py` | 1172 | 0 | **SURVIT** |
| `alea-de-partie-partage` | `agents/entrainement.py` | 1171 | 1 | detectee |
| `composition-toujours-self-play` | `agents/entrainement.py` | 1171 | 1 | detectee |
| `tete-plus-grande-que-l-espace-d-action` | `agents/entrainement.py` | 1172 | 0 | **SURVIT** |
| `garde-fou-de-portee-un` | `agents/campagne.py` | 1168 | 4 | detectee |
| `garde-fou-se-contente-d-un-ecart-etabli` | `agents/campagne.py` | 1172 | 0 | **SURVIT** |
| `garde-fou-sans-bonferroni` | `agents/campagne.py` | 1172 | 0 | **SURVIT** |
| `pool-garde-les-plus-anciens` | `agents/campagne.py` | 1172 | 0 | **SURVIT** |
| `intitule-du-garde-fou-sans-population` | `agents/campagne.py` | 1172 | 0 | **SURVIT** |
| `garde-fou-se-compare-a-lui-meme` | `agents/campagne.py` | 1169 | 3 | detectee |
| `progres-etabli-redevient-etabli` | `mesure/bootstrap.py` | 1171 | 1 | detectee |
| `percentiles-apparies-unilateraux` | `mesure/bootstrap.py` | 1171 | 1 | detectee |
| `rho-sur-des-groupes-inegaux` | `mesure/bootstrap.py` | 1171 | 1 | detectee |
| `appariement-par-rang-de-valeur` | `mesure/bootstrap.py` | 1168 | 4 | detectee |
| `masse-binomiale-part-de-zero` | `mesure/binomiale.py` | - | - | EXPIRE |
| `clopper-pearson-borne-basse-unilaterale` | `mesure/binomiale.py` | 1168 | 4 | detectee |
| `r2-devient-r0` | `mesure/retournement.py` | 1164 | 8 | detectee |
| `r3-ignore-le-statut-final` | `mesure/retournement.py` | 1167 | 5 | detectee |
| `vue-d-un-siege-voit-tous-les-espions` | `mesure/partie.py` | 1168 | 4 | detectee |
| `part-fractionnee-ne-somme-plus-a-un` | `mesure/phase2.py` | 1167 | 5 | detectee |
| `quantile-sans-bonferroni` | `mesure/dimensionnement.py` | 1164 | 8 | detectee |
| `sieges-non-permutes` | `mesure/phase3.py` | 1167 | 5 | detectee |
| `adversaires-partagent-un-alea` | `mesure/phase3.py` | 1172 | 0 | **SURVIT** |
| `gain-lu-au-siege-zero` | `mesure/phase3.py` | 1171 | 1 | detectee |
| `separation-exacte-toujours-disjointe` | `mesure/phase3_mesure.py` | 1172 | 0 | **SURVIT** |
| `b4-strict-avale-le-departage` | `mesure/comportements.py` | 1171 | 1 | detectee |
| `b4-meurtre-couteux-au-mauvais-denominateur` | `mesure/comportements.py` | 1171 | 1 | detectee |

