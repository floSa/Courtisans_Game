# Audit — phase 3 — VERDICT : REJETE

Branche auditee `phase-3-premier-agent` a `9c96f65`. Branche d'audit `audit-phase-3`,
poussee des le premier commit. Plan de recherche pre-inscrit et commite **avant toute
lecture du code du constructeur** : `ca1aa87`, `tests/audit_phase3/PLAN_PRE_INSCRIT.md`.

Controle de base : `git merge-base --is-ancestor 9c96f65 HEAD` — OK depuis `audit-phase-3`.
Il ECHOUE depuis `main`, qui porte `b5e4228` et ne contient pas la phase 3.

## Constats

| # | Controle | Resultat |
|---|---|---|
| A1 | Tests rejoues moi-meme | **1132 verts / 1132 annonces**, 0 rouge, **0 saute** — les 10 controles sur l'agent entraine ont tourne |
| A2 | Tests relus contre la spec | 2 controles de l'auto-audit verifient ce que le code fait et non ce que la regle dit (defauts 3 et 4) |
| A3 | Tests hostiles ecrits par moi | **97**, tous verts, dans `tests/audit_phase3/` |
| A4 | Criteres d'acceptation reverifies | 4/4 du §11 de la pre-inscription ; 2/3 des regles pre-inscrites du §8.1 et du §9.2 tenues |
| A5 | Niveaux de preuve | 1 MESURE presente comme etabli qui ne l'est pas (defaut 1) ; 1 regle pre-inscrite citee pour une grandeur qu'elle ne surveillait pas (defaut 7) |
| A6 | Valeurs en dur, duplications | 3 : `passe=True` en dur dans 2 controles sur 10, 1 branche morte (defauts 3, 6) |
| A7 | Chiffres reconstruits | **12/12** des chiffres du juge et du dimensionnement, par une troisieme implementation |

## Tests hostiles ecrits (97, tous verts)

`tests/audit_phase3/test_a3_aveuglement.py` — 88, mon brouilleur, mon piege, mon compteur :
1. le brouilleur change vraiment la verite cachee, et ne fabrique pas un paquet impossible — vert
2. le brouillage deplace le score final au moins une fois — vert
3. tenseur, chaine et actions legales invariants sous brouillage complet — vert (30 graines)
4. logits du reseau identiques **bit a bit** — vert (30 graines)
5. partie entiere rejouee avec un brouillage NEUF a chaque nœud : meme suite d'actions — vert
6. les 4 acces privilegies pieges mordent quand on les teste sur eux-memes — vert
7. partie entiere jouee avec chacun des 4 acces explosif — vert
8. **compteur** : 0 appel privilegie sur plus de 50 decisions, et le compteur sait compter — vert
9. un tenseur qui fuiterait UNE composante serait attrape (17/30 et 21/30 etats) — vert
10. constat : dans `entrainement-3j` la main adverse est **toujours vide** — vert

`tests/audit_phase3/test_a3_gardes.py` — 9 :
11. `ecart_de_taux` et `cumuler` levent aux grains differents, pas au meme — vert
12. `verifier_inclusion_b1` mord aux DEUX grains — vert
13. elle compare des numerateurs **sans** passer par la garde de grain — vert
14. R4 est concluant sur le pire cas imaginable — vert
15. R4 ignore les zeros de la LIGNE DE BASE — vert
16. R5 est concluant sur un facteur dix d'unite — vert
17. aucune ligne ne peut etre exclue « hors budget », meme a un budget d'UNE partie — vert

## Defauts

| # | Gravite | Defaut | Ou | Preuve |
|---|---|---|---|---|
| 1 | **bloquant** | « il progressait encore au dernier » n'est pas etabli, et ma remesure lui donne le signe oppose | `phase3_entree_de_journal.md`, rapport §4 | MESURE ci-dessous |
| 2 | **bloquant** | le garde-fou reecrit sur cette phrase tuerait ce run au 3e checkpoint | `documentations/05` sur `main` (`b5e4228`) | MESURE : 7/7 |
| 3 | majeur | « chacun des dix est verifie capable d'echouer » : faux pour 4, impossible pour 2 | `mesure/phase3_audit.py:186,206` | MESURE : tests 14-16 |
| 4 | majeur | R4 declare « 0 valeur extreme » pendant que le rapport publie deux zeros absolus | `mesure/phase3_audit.py:185-201` | MESURE : test 15 |
| 5 | majeur | deux populations differentes publiees sous le **meme nom** | `phase3_mesure.py:413` / `campagne.py:152` | MESURE : 1500 vs 1800 parties |
| 6 | majeur | la regle « hors budget », pre-inscrite avec ses 8 noms, est du code mort et n'a pas ete appliquee | `phase3_mesure.py:284-291` | MESURE : test 17 |
| 7 | mineur | la marge de 10 % pre-inscrite portait sur la demi-largeur, pas sur `sigma` — et elle n'est pas franchie | pre-inscription §3, rapport §2 | MESURE : −1,1 % |
| 8 | mineur | l'ecart detectable suppose des denominateurs egaux ; 5 lignes ne les ont pas | `phase2.ecart_de_taux_detectable` | MESURE : 0 ligne bascule |
| 9 | mineur | le tableau central du rapport ne se rend pas comme un tableau | `rapport_phase3.py:362-377` | MESURE : rendu GFM |
| 10 | mineur | « les quatre plages » suivi d'une liste de six | `phase3_mesure.py:71` | lecture |
| 11 | mineur | « memes seeds » designe la phase 2, pas la campagne de l'agent | rapport §5 | `DEPART_B = 0` |
| 12 | mineur | `verifier_inclusion_b1` compare des numerateurs sans garde de grain | `comportements.py:757` | MESURE : test 13 |
| 13 | mineur | « paragraphe 10 de la pre-inscription » pour 7 points dont un n'y est pas | rapport §8 | lecture |
| 14 | mineur | les 20 mutations ne couvrent **aucun** fichier de la phase 3 | `outillage/mutation.py` | 20/20 sur `courtisans/` |

## Le detail des deux bloquants

### 1. « Encore en progression au dernier »

**Ce qui est ecrit.** Entree de journal : « **croissance monotone sans exception**, et il
progressait **encore au dernier** ». Rapport §4 : meme phrase. C'est elle, et elle seule, qui
porte la decision — « ce que le resultat ecarte est le budget, pas la methode ».

**Ce qui est vrai.** Les sept pas consecutifs valent **+2,19 / +2,25 / +1,45 / +1,84 / +2,50 /
+1,71 / +0,86** pt. La pre-inscription §8.1 fixe elle-meme l'ecart detectable de ce budget a
**2,75 pt** (iid) et la demi-largeur de Bonferroni a **2,60 pt**. **Aucun des sept pas n'est
individuellement detectable au budget que le constructeur s'est donne.** Les huit IC publies
se recouvrent **7 fois sur 7** d'un checkpoint au suivant.

**Ma remesure**, memes 600 donnes `40000-40599`, memes checkpoints, mon aleatoire de tirage et
mes deux adversaires, bootstrap **apparie** par donne — donc plus puissant que ses IC non
apparies :

```
ckpt   1       2       3       4       5       6       7       8
lui  57,33   59,52   61,77   63,22   65,06   67,56   69,27   70,13   monotone
moi  56,23   58,50   60,81   64,92   64,51   67,64   70,98   70,45   DEUX inversions

ecarts apparies, IC 99 % par donne :
  1 -> 2  +2,27 pt  [-0,77 ; +5,28]  dans le bruit
  2 -> 3  +2,31 pt  [-0,82 ; +5,62]  dans le bruit
  3 -> 4  +4,10 pt  [+0,94 ; +7,31]  ETABLI
  4 -> 5  -0,41 pt  [-3,46 ; +2,71]  dans le bruit
  5 -> 6  +3,13 pt  [-0,06 ; +6,43]  dans le bruit
  6 -> 7  +3,34 pt  [+0,45 ; +6,23]  ETABLI
  7 -> 8  -0,53 pt  [-3,19 ; +2,23]  dans le bruit
  1 -> 8 +14,22 pt  [+10,99 ; +17,49] ETABLI
```

**De combien le chiffre bouge.** Le dernier pas passe de **+0,86 pt a −0,53 pt** : il change de
signe. Deux pas sur sept sont etablis ; cinq sont dans le bruit. La monotonie « sans exception »
n'est pas une propriete de l'agent, c'est une propriete de son tirage : un autre aleatoire de
politique, sur les memes donnes, la casse a deux endroits.

**Ce qui reste debout, et il faut le dire aussi fort.** `ckpt 1 -> 8 : +14,22 pt, IC
[+10,99 ; +17,49]`. **« L'agent apprend » est CONFIRME** — entre le premier et le dernier
checkpoint, contre deux aleatoires, sur 1 800 parties par point. Ce qui n'est pas etabli, c'est
qu'il apprenait **encore a la fin**, et c'est exactement la moitie de la phrase qui decide.

**Et le rapport se contredit lui-meme sur ce point, dans son propre §3** : contre ses propres
checkpoints 5, 6, 7 et 8, les quatre IC **contiennent zero**. Sur la derniere heure du run,
l'agent ne se depasse pas de facon etablie. Le §3 le dit ; l'entree de journal, ecrite apres,
ecrit « l'agent apprend, **sans ambiguite** » et n'en reprend rien.

### 2. Le garde-fou, quatrieme defaut, dans le texte qui corrigeait le troisieme

`documentations/05` sur `main` (`b5e4228`, 21/08) reecrit le garde-fou **en citant le resultat
de la phase 3 comme preuve** — « croissance monotone sans exception sur huit checkpoints,
encore en progression au dernier ». La nouvelle regle :

> « Il se declenche si, sur **trois checkpoints consecutifs**, cette part n'a pas progresse —
> intervalles a 99 % qui se recouvrent d'un checkpoint au suivant. »

MESURE, sur les huit jalons de `models/phase3/journal.jsonl` :

```
ckpt 1 [53,92 ; 60,85] -> ckpt 2 [55,92 ; 63,20]  SE RECOUVRENT
ckpt 2 -> 3, 3 -> 4, 4 -> 5, 5 -> 6, 6 -> 7, 7 -> 8 : SE RECOUVRENT
couples consecutifs qui se recouvrent : 7/7
=> premier declenchement : checkpoint 3, a 45 minutes sur 120.
```

**Le garde-fou reecrit pour ne pas tuer un agent qui apprend tuerait ce run-ci a 45 minutes.**
C'est le quatrieme defaut du meme garde-fou, et il est ne dans le texte qui corrigeait le
troisieme. Il est hors du perimetre de `9c96f65` — mais il en derive directement, puisqu'il
s'appuie sur la phrase du defaut 1.

## Ce que j'ai CONFIRME par du code independant

`audit/phase3/ma_boucle.py` — ma construction de partie, mon tour de sieges, mon aleatoire,
ma part fractionnee, mon bootstrap. Aucune fonction de `mesure/phase3*.py` importee.

**Le verdict « battu ».** 2 000 donnes x 3 sieges, seeds `60000-61999` :

| | lui | le pilote (400 donnes) | **moi (2 000 donnes)** |
|---|---:|---:|---:|
| gain moyen | −0,1643 | −0,1719 | **−0,1734** |
| IC 99 % par donne | [−0,1824 ; −0,1462] | [−0,2108 ; −0,1315] | **[−0,1915 ; −0,1553]** |
| part fractionnee | 22,38 % | 21,88 % | **21,77 %** |
| `sigma(gain)` | 0,5710 | 0,5659 | **0,5654** |
| demi-largeur | 0,0181 | — | **0,0181** |

Son chiffre tombe dans mon intervalle, le mien dans le sien. **La borne haute est negative dans
les trois. L'agent est battu par le greedy : ETABLI, contre une troisieme implementation.**
Gains par siege chez moi −0,3053 / −0,2111 / −0,0037, chez lui −0,3069 / −0,1998 / +0,0139.

**Le niveau nul.** Le greedy mis a la place de l'agent, memes seeds : **+0,0152, IC 99 %
[−0,0036 ; +0,0338]** — contient 0. Sa calibration (+0,0062, [−0,0124 ; +0,0255]) est
concordante, et l'espérance exacte a 0,0000 est bien une consequence de la somme nulle et de la
permutation complete, non une estimation. Part fractionnee 34,34 % contre le neutre exact
33,3333 %. **Un niveau nul mal place n'est pas ce qui declare cet agent battu.**

**L'agent ne triche pas.** 88 controles a moi. Le tenseur, la chaine et les logits ne bougent
**pas d'un bit** quand je permute la pioche, les mains adverses et l'identite des dos ; une
partie entiere rejouee avec un brouillage **neuf a chaque nœud** rend exactement la meme suite
d'actions ; les quatre acces privilegies pieges ne sont appeles **aucune fois** sur plus de
50 decisions, compteur a l'appui ; le piege mord quand on le teste sur lui-meme ; mon
brouilleur attrape un tenseur qui fuiterait **une seule** composante (17/30 et 21/30 etats).
Constat annexe utile : dans `entrainement-3j` **la main adverse est toujours vide** — le moteur
ne remplit que celle du joueur courant. L'information cachee de cette instance, c'est la pioche
et l'identite des Espions poses, rien d'autre.

**Les populations sont disjointes AU NIVEAU DES DONNES, pas seulement des seeds.** J'ai hache
les pioches reellement produites : 14 600 donnes de mesure, toutes distinctes entre elles, et
**0 collision** contre les **1 486 336** donnes d'entrainement balayees **en entier**. L'agent
n'a jamais ete juge sur une donne qu'il avait vue. Le defaut que son auto-audit a trouve avant
la mesure etait reel, et sa correction tient.

**Les gardes de grain mordent.** `ecart_de_taux` et `cumuler` levent bien aux grains differents
et pas au meme ; `verifier_inclusion_b1` mord aux **deux** grains sur la population regeneree.

**Les ecarts detectables des comportements.** Recalcules ligne a ligne avec les effectifs reels
des deux cotes : **0 des 34 lignes ne change de statut**. Cinq detectables sont faux (defaut 8),
aucune conclusion ne bascule.

**Les 20 mutations.** 20 motifs, **20 detectees, 0 survivante**, sur mon propre run —
1 220 = 1 132 + mes 88. Elles ne portent que sur `courtisans/` (defaut 14).

**L'arret anticipe** n'est declenche ni sur sa colonne ni sur la mienne.

**Les durees** : 4 passes enregistrees, etendue publiee — le §0.2 est tenu.

## Mon avis sur le diagnostic du critique (point d)

**Ton unite est juste, ta valeur aussi, et ta conclusion est trop prudente d'un cran.**

`agents/entrainement.py:347` calcule bien `mse_loss(valeurs, retours)` ou `retours` est le gain
terminal du siege, recopie tel quel sur chaque nœud — `gamma = 1`, aucune actualisation, aucune
normalisation, aucun clipping. Ce n'est ni une cible GAE ni un retour actualise : c'est le gain
brut. **Ta reference est la bonne**, et tu es le premier de ce projet a reconstruire l'unite
avant la valeur sur ce point.

MESURE par moi, deux echantillons, dont un **hors** de la plage d'entrainement (tes seeds
`700000+` y tombent, les miens `5000000+` non — sans consequence, les deux concordent) :

| | dans la plage | hors plage |
|---|---:|---:|
| variance des retours sur les nœuds | 0,4320 | **0,4190** |
| MSE reelle du critique de `final.pt` | 0,3747 | **0,3809** |
| `R2 = 1 − MSE/Var` | +0,113 | **+0,093** |

Ta variance **0,4275 est confirmee**. Ton « de l'ordre de 11 % » l'est aussi — par la mesure
directe du R2, meme si le rapport `0,39 / 0,4275` que ta phrase decrit donne 8,8 %.

**Ce que tu n'as pas fait, et qui separe tes deux lectures : le PLANCHER.** Un critique parfait
ne fait pas 0 : il fait `E[Var(R | etat))]`. Je l'ai estime en **rejouant le meme etat 24 fois**
sous la politique de l'agent, sur 400 etats :

```
PLANCHER E[Var(R | etat complet)] : 0,1815      part IRREDUCTIBLE : 43,3 %
```

Donc **43 % de la variance du retour est du bruit que rien ne peut predire**, et un critique
parfait — voyant meme plus que l'info-set — plafonnerait vers 0,18. Le critique observe est a
0,38. Il a donc encore **~0,20 de MSE a gagner**, pas 0,39.

**Et voici ce qui tranche entre tes deux lectures, sans entrainer quoi que ce soit.** La
variance irreductible **s'effondre avec la profondeur**, la MSE du critique **non** :

```
profondeur          0      4      8     12     16     18     19
plancher Var(R|s)  0,32   0,32   0,26   0,21   0,025  0,035  0,0075
MSE du critique    0,36   0,41   0,40   0,40   0,31   0,27   0,30
```

A l'avant-derniere decision, la partie est **presque ecrite** — il ne reste que 0,0075 de
variance irreductible — et le critique y fait encore **0,30**, soit **quarante fois** l'erreur
qu'un critique correct y ferait. Un jeu dont la valeur serait « presque impredictible » ne
donnerait pas ce profil-la.

**Ta seconde lecture est donc REFUTEE.** La valeur d'un info-set n'est pas impredictible dans
ce jeu : elle est bruitee au debut et **quasi determinee a la fin**, et le critique est aussi
mauvais aux deux bouts. Il reste ta premiere lecture, et elle est maintenant chiffree :
**critique mal specifie ou sous-entraine**, avec 0,20 de MSE laissee sur la table et un
`R2` de 0,10 la ou 0,57 est atteignable.

Une precision de forme qui ne change pas ta conclusion : la `perte_valeur` du journal est la
moyenne **sur les quatre epoques** de la vague courante, mesuree **pendant** l'optimisation et
**sur les donnees de cette vague** — c'est une perte d'entrainement, pas une perte de
validation. Une perte d'entrainement plate est un symptome plus severe, pas moins.

**Consequence pour la phase 4, et elle contredit l'entree de journal du constructeur.** Le
levier que ce diagnostic designe n'est pas le **budget** (levier 1) mais la **tete de valeur**
— ce qui rejoint ce que la pre-inscription elle-meme avait ecrit d'avance au §7.1 comme reponse
prevue. Rallonger un run dont le critique explique 10 % de la variance rallonge un run dont
l'avantage de PPO est domine par le bruit.

## Proposition d'entree de journal

*Redigee par l'auditeur, qui detient les chiffres remesures. Format du §4 de
`08_modele_compte_rendu.md` et du §0.1 de `05_protocole_experimental.md`.*

---

## [2026-08-21] Phase 3 — Le premier agent entraine

**Hypothese.** Ecrite et commitee avant tout entrainement, `mesure/phase3_hypothese_et_instrument.md` :
un agent entraine en self-play avec un pool d'adversaires figes, sur `entrainement-3j`, obtient
contre **deux greedys**, sieges permutes, un **gain moyen strictement positif, borne basse de son
IC 99 % bootstrap par donne comprise**.

**Instrument.** PPO a masque d'actions, reseau unique partage par les trois sieges, tete de
valeur, `gamma = 1`, `lambda = 1` ; ni greedy ni aleatoire dans le pool. Juge : le gain moyen,
niveau nul **exactement 0,0000** par somme nulle et permutation complete. Budget dimensionne sur
sa propre composition — `sigma = 0,6494`, `rho = −0,1400` sur « un greedy contre deux greedys »,
2 000 donnes, seeds 20000–21999 — d'ou **2 000 donnes x 3 sieges = 6 000 parties**, ecart
detectable +0,0243. Garde-fou : un agent contre deux aleatoires, **600 donnes x 3 = 1 800 parties**
par checkpoint, seeds 40000–40599, ecart detectable pre-inscrit **2,75 pt**.

**Resultat.**

- **H est INFIRMEE, et de facon etablie.** Gain moyen **−0,1643**, IC 99 % [−0,1824 ; −0,1462]
  sur 6 000 parties, 1 agent contre 2 greedys, sieges permutes, seeds 60000–61999 : la borne
  **haute** est negative. Part fractionnee 22,38 % contre 33,3333 % au neutre exact.
  **Retrouve par une troisieme implementation independante** (l'auditeur, memes seeds,
  2 000 donnes) : **−0,1734, IC [−0,1915 ; −0,1553], part 21,77 %, sigma 0,5654**. Les deux IC
  se contiennent mutuellement.
- **L'instrument est calibre sur les seeds exactes du verdict** : le greedy a la place de
  l'agent rend +0,0062, IC [−0,0124 ; +0,0255] chez le constructeur, **+0,0152, IC
  [−0,0036 ; +0,0338] chez l'auditeur** — les deux contiennent 0.
- **L'agent apprend, entre son premier et son dernier checkpoint, et cela seul est etabli.**
  Part fractionnee contre deux aleatoires, agregee sur trois sieges comme le 86,52 % l'est :
  57,33 -> 70,13 % chez le constructeur, 56,23 -> 70,45 % chez l'auditeur ; **ecart apparie
  ckpt 1 -> 8 : +14,22 pt, IC 99 % [+10,99 ; +17,49]**.
- **« Monotone sans exception » et « encore en progression au dernier » ne sont PAS etablis.**
  Les sept pas consecutifs valent +0,86 a +2,50 pt pour un ecart detectable pre-inscrit de
  2,75 pt, et les huit IC se recouvrent 7 fois sur 7. La remesure de l'auditeur, memes donnes
  et autre aleatoire de tirage, porte **deux inversions** et un **dernier pas negatif**
  (−0,53 pt, IC [−3,19 ; +2,23]). Seuls 2 des 7 pas sont etablis.
- **Le critere terminal du garde-fou n'est pas franchi** — 70,13 % contre 86,52 % — et la raison
  que le protocole lui pretait (« l'agent n'apprend pas ») est bien fausse ici. L'arret anticipe
  n'est declenche ni chez l'un ni chez l'autre.
- **Le critique n'apprend pas.** `perte_valeur` 0,3923 au premier checkpoint, 0,3908 au huitieme,
  sans amelioration entre les deux. MESURE par l'auditeur sur `final.pt` : variance des retours
  **0,4190**, MSE reelle **0,3809**, `R2 = +0,093` ; **plancher irreductible `E[Var(R | etat)]`
  = 0,1815**, soit 43 % de la variance. La variance irreductible s'effondre avec la profondeur
  (0,32 -> 0,0075) alors que la MSE du critique reste plate (0,36 -> 0,30) : **la valeur n'est
  pas impredictible dans ce jeu, c'est le critique qui est mauvais**, y compris la ou la partie
  est deja ecrite.
- **`sigma` a bouge de −12,1 %** (0,5710 contre 0,6494). La regle pre-inscrite portait en fait
  sur la **demi-largeur**, qui n'a bouge que de **−1,1 %** : elle etait aveugle au mouvement
  qu'elle pretendait detecter, `sigma` et l'effet de plan ayant bouge en sens contraire.
- **Comportements**, ligne de base regeneree « trois greedys, un seul siege compte » : `B1-motif`
  42,48 % contre 45,83 %, `B4-brut` 31,93 % contre 15,93 %, `B4-contre-nature` 35,87 % contre
  0,00 %. Ecarts detectables recalcules par l'auditeur avec les effectifs reels des deux cotes :
  **aucune des 34 lignes ne change de statut**.

**Audit. VERDICT : REJETE.** Deux defauts bloquants, quatre majeurs, huit mineurs ; 97 controles
hostiles ecrits par l'auditeur, tous verts. **Ce que l'auditeur a CONFIRME** : le verdict
« battu » par une troisieme implementation, la calibration du niveau nul, l'aveuglement complet
du reseau (88 controles : tenseur et logits invariants bit a bit, zero appel privilegie compte
pendant la decision, piege et brouilleur prouves mordants), la disjonction des populations **au
niveau des donnes** — 0 collision de pioche entre les 14 600 donnes de mesure et les 1 486 336
donnes d'entrainement balayees en entier —, les gardes de grain, l'arret anticipe, les 20/20
mutations, les 1 132 tests verts dont aucun saute. **Ce qu'il a trouve** : « il progressait
encore au dernier » n'est pas etabli et change de signe a la remesure ; le garde-fou reecrit sur
cette phrase le 21/08 tuerait ce run au checkpoint 3 ; deux des dix controles de l'auto-audit
portent `passe=True` en dur et ne peuvent pas echouer, contrairement a ce que le compte rendu
affirme ; R4 declare « aucune valeur extreme » quand le rapport en publie deux ; deux populations
publiees sous le meme nom ; la regle d'exclusion « hors budget » est du code mort et n'a pas ete
appliquee.

**Decision. PROPOSEE : go sur un pivot de diagnostic, pas sur le budget.** L'hypothese est
infirmee et l'agent apprend : les deux sont acquis. Mais **le levier que la mesure designe n'est
pas le budget.** Un critique a `R2 = 0,09` quand 0,57 est atteignable rend l'avantage de PPO
domine par le bruit du retour, et rien dans les donnees ne montre que la courbe montait encore
a la fin. Le §7.1 de la pre-inscription avait ecrit d'avance la reponse a cette situation — une
tete auxiliaire de regression sur l'ecart de score final. C'est elle que la mesure designe,
avant le levier 1.

**Impact plan.**

1. **Le garde-fou de la phase 3 doit etre relu une QUATRIEME fois** : sa forme du 21/08
   (« trois checkpoints consecutifs dont les IC a 99 % se recouvrent ») se declenche 7 fois sur 7
   sur ce run et l'aurait arrete a 45 minutes. Un garde-fou dont le declencheur est le
   recouvrement d'IC a 99 % sur un budget dont l'ecart detectable vaut 2,75 pt ne peut pas ne
   pas se declencher.
2. **Toute courbe d'apprentissage se publie avec l'IC de ses ECARTS, pas seulement de ses
   niveaux.** Le rapport publie huit IC sur huit niveaux et aucun sur les sept ecarts — or c'est
   un ecart qui decide. Les ecarts apparies coutent zero partie de plus.
3. **Un controle qui ne peut pas echouer ne se compte pas dans « dix controles, aucun en
   echec ».** `passe=True` en dur doit devenir un statut distinct — *releve*, pas *concluant*.
4. **La ligne de base « trois greedys a un siege compte » existe et est regenerable** ; toute
   phase mesurant un agent contre deux adversaires doit la citer plutot que la colonne a trois
   sieges de la phase 2.
5. **Les 20 mutations ne couvrent aucun fichier de `agents/` ni de `mesure/`.** La phase 4
   herite d'un moteur mute et de 2 500 lignes de mesure qui ne le sont pas.
