# Audit — phase 3, tour 2 — VERDICT : REJETE

Perimetre : les trois commits de correction `ce130aa`, `c0b073b`, `efcf54c` sur
`phase-3-premier-agent`, contre les quatorze defauts du verdict du tour 1. Le travail
d'origine n'est pas rouvert, aucune campagne n'est refaite.

Controle de base : `git merge-base --is-ancestor efcf54c HEAD` — **OK** depuis
`audit-phase-3-tour-2`. Il **echoue** depuis `main`, qui porte `38225e5` et ne contient
pas les corrections.

**Ce que j'ai en propre, et ce que ca vaut.** J'ai construit la phase 3 ; je n'ai ecrit
aucune de ces trois commits. Je suis donc bien place pour voir ce qu'une correction a
casse sans que les chiffres le montrent, et c'est la que se trouve le defaut neuf le plus
grave.

## Ce que j'ai rejoue moi-meme

| Controle | Resultat |
|---|---|
| Suite complete | **1161 verts, 0 rouge, 0 saute** — recomptes ici, `152,73 s` |
| Arbre de travail | propre avant et apres chaque reinjection |
| `mesure/phase2.py`, `mesure/dimensionnement.py`, `agents/greedy.py`, `courtisans/` | **intacts** dans les trois commits |
| `phase2.ecart_de_taux_detectable` | **octet pour octet identique** a `9c96f65` |
| Les 15 chiffres acquis | tous presents et inchanges — 14 dans `resultats/phase3.md`, la collision de tenseurs (`115 299 -> 106 590`) dans `phase3_hypothese_et_instrument.md`, fichier que les corrections ne touchent pas |

Mon code : `audit/phase3_tour_2/ma_courbe.py` et `audit/phase3_tour_2/mes_reinjections.py`.

## Les quatorze defauts

| # | Gravite au tour 1 | Etat | Ce qui l'etablit |
|---|---|---|---|
| 1 | bloquant | **leve** | serie par donne journalisee, garde de reproduction eprouvee, 7 ecarts publies avec leur IC |
| 2 | bloquant | **partiellement leve** | v5 ne tue plus ce run, mais elle ne peut pas se declencher sur un effondrement — **defaut neuf C** |
| 3 | majeur | **leve** | 8 eprouves / 2 releves, parade AST eprouvee par reinjection |
| 4 | majeur | **leve** | R4 est un `_releve`, scanne les deux cotes, nomme les deux zeros ; les quatre cas construits existent et mordent |
| 5 | majeur | **leve** | noms distincts, R2 elargi hors pool, parade AST eprouvee — une reserve, plus bas |
| 6 | majeur | **leve** | branche morte retiree, six nombres publies **refaits par moi et exacts** |
| 7 | mineur | **leve** | la regle porte sur la demi-largeur, `-1,1 %`, non franchie ; `sigma` dit a cote |
| 8 | mineur | **leve pour la formule, casse a ses deux bords** | **defauts neufs A et B** |
| 9 | mineur | **leve** | le blockquote passe avant l'en-tete, le tableau se rend |
| 10 | mineur | **leve** | six familles, treize plages — le compte est juste |
| 11 | mineur | **leve** | « memes seeds **que la phase 2** », l'appartenance est nommee |
| 12 | mineur | **leve** | `GrainsIncomparables` levee, et l'inclusion mord toujours |
| 13 | mineur | **leve** | points 1 a 6 au §10, le 7 au §9.2, le 8 au §2.2 |
| 14 | mineur | **documente** | traite comme documente et non comme corrige, sur arbitrage du pilote — **non compte contre le correcteur** |

## Les parades, eprouvees une par une

Chacune par reinjection de la faute qu'elle nomme, sur une copie, l'arbre restaure ensuite.

**1. `test_aucun_controle_eprouve_ne_passe_un_booleen_litteral`** — j'ai remis un `True`
litteral dans `_epreuve` a `controle_denominateur` :

    E   assert not ['ligne 216 : passe=True']            ROUGE

**2. `test_les_intitules_du_depot_sont_deux_a_deux_DISTINCTS`** — j'ai redonne a la ligne
du pool le nom de `controle_niveau_nul` :

    E   assert not {'1 greedy contre 2 greedys, seeds du verdict':
                    ['mesure/phase3_audit.py:158', 'mesure/phase3_mesure.py:543']}   ROUGE

**3. `phase3_courbe.ecarts`** — j'ai retire `parts_par_donne` du jalon 5, puis je l'ai
remplace par une liste vide. Les deux levent, et nomment le checkpoint.

**4. `phase3_courbe.completer`, la garde de reproduction.** C'est le point le plus
sensible du tour, et il tient. Sur le checkpoint 3, dans un dossier a part :

  - **rejeu honnete** : les 600 valeurs de `parts_par_donne` sont **identiques bit a bit**
    a celles du journal publie, et les quatre nombres journalises sont reproduits ;
  - **reproduction cassee** — j'ai deplace `part_fractionnee` de `1e-9` :

        ValueError: le rejeu du checkpoint 3 ne reproduit pas le journal :
        part_fractionnee : journalise 0.6176851861851851, rejoue 0.6176851851851851.
        Ce n'est donc pas la meme mesure, et aucun ecart n'en sera publie.

**Le journal a donc bien ete COMPLETE et non refait.** Les IC apparies portent sur les
memes parties que les niveaux publies. Le bloquant 1 est correctement corrige.

**5. `test_parties_requises_et_separable_sont_le_MEME_critere`** — le cas fourni n'eprouve
que des effectifs egaux. Je l'ai refait sur quatre couples d'effectifs inegaux, dont
`3814 / 1967` et `24000 / 6000`, environ 750 combinaisons : **0 incoherence**. La
correspondance `parties_requises > budget` ⟺ `|ecart| < detectable` tient.

## Ma reconstruction de la courbe

`audit/phase3_tour_2/ma_courbe.py` — mon bootstrap, mon aleatoire, aucune fonction de
`mesure/phase3_courbe.py`. Sur les series journalisees, IC 99 % Bonferroni pour 8 regards :

```
portee 1   +2,19  +2,25  +1,45  +1,83  +2,50  +1,71  +0,86 pt
           aucun etabli, demi-largeur 3,38 a 4,10, moyenne 3,79
portee 3   +5,89  +5,54  +5,79  +6,05  +5,07 pt
           les cinq etablis, demi-largeur 3,48 a 4,40, moyenne 3,98
1 -> 8    +12,80 pt  IC [+8,32 ; +17,30]                    ETABLI
progres par checkpoint : (70,13 - 57,33) / 7 = 1,828 pt
```

Les cinq ecarts de portee trois du correcteur sont **exactement** les miens. Aucun ne
declenche. `portee_minimale(3,83 ; 1,83) = 3` et `portee_minimale(2,75 ; 1,83) = 2` :
l'arithmetique du §5 est juste, et la portee retenue est bien minimale.

**« L'agent apprend » reste etabli. « Il progressait encore au dernier » reste non
etabli.** Les deux sont maintenant dans le rapport.

## Les defauts NEUFS, apparus dans les corrections

### A. Deux lignes changent de statut, et le rapport ecrit qu'aucune ne change — **bloquant**

`mesure/resultats/phase3.md:181` publie :

> **Aucune ligne ne change de statut**, mais le chiffre publie au premier tour etait faux.

C'est faux. `ecart_detectable_deux_echantillons` rend `None` sur un taux degenere ; alors
`separable` vaut `False` et `parties_requises` vaut `None`. Les deux zeros absolus de la
ligne de base tombent exactement la :

| Ligne | tour 1 | tour 2 |
|---|---|---|
| `B4-contre-nature` 35,87 % contre 0,00 % (0/1967) | detectable 3,75 % — **separable** | detectable `-` — **non separable a ce budget** |
| `B4-meurtre-couteux` 3,66 % contre 0,00 % (0/10382) | detectable 1,01 % — **separable** | detectable `-` — **non separable a ce budget** |

**Et l'etiquette est fausse, pas seulement le compte.** La borne haute **exacte** a 99 %
d'un zero sur 1967 vaut **0,2338 %**, celle d'un zero sur 10382 vaut **0,0443 %** — contre
**35,87 %** et **3,66 %** chez l'agent. Ces deux ecarts sont separables par une marge
enorme. La docstring de la fonction ecrit elle-meme « *un zero observe se traite par sa
borne exacte* » ; **aucune borne exacte n'est calculee nulle part**, et la ligne recoit a
la place une phrase qui affirme le contraire de la verite.

**Le rapport se contredit alors dans ses propres pages.** Son paragraphe sur B4 argumente
sur une demi-page ce que l'ecart `35,87 % contre 0,00 %` etablit et n'etablit pas —
pendant que son tableau central, cinquante lignes plus haut, dit que cet ecart n'est pas
separable a ce budget.

**Ce sont exactement les deux lignes dont le defaut 4 parlait.** La correction qui a fait
voir les deux zeros a R4 a fait disparaitre ces deux memes zeros du tableau qui les compare.

*Reproduction : `uv run python audit/phase3_tour_2/mes_reinjections.py`, section A.*

### B. Le cas qui soutient cette phrase maquille son entree — **bloquant**

`tests/mesure/test_phase3_corrections.py:161`, `test_aucune_ligne_ne_change_de_STATUT_avec_la_formule_corrigee`,
lignes 167-168 :

```python
("B4-contre-nature",   (1368, 3814), (1, 1967),  True),
("B4-meurtre-couteux", (298, 8131),  (1, 10382), True),
```

Les comptes reels, publies quinze lignes plus loin dans le meme depot, sont **`(0, 1967)`**
et **`(0, 10382)`**. Avec le `1` substitue, les deux taux cessent d'etre degeneres, le
detectable redevient un nombre — 2,66 % et 0,71 % — et le cas est **vert**. Avec le vrai
zero, les deux sont non separables et le cas serait **rouge**.

**Le cas dont le nom annonce « aucune ligne ne change de statut » ecarte, en modifiant
silencieusement ses donnees, les deux seules lignes qui changent de statut.**

C'est la meme famille que le defaut que j'avais signale au tour 1 comme nouvelle pour ce
projet — un test vert dont le nom enonce l'exigence pendant que son corps s'en detourne.
Ici la forme est plus dure a voir : l'assertion est correcte, c'est l'entree qui est
falsifiee. Deux autres cas du meme fichier, `test_le_detectable_rend_None_sur_un_taux_degenere`
et `test_le_detectable_a_deux_echantillons_corrige_B4_strict`, montrent que le comportement
degenere etait connu de son auteur au moment ou il ecrivait celui-la.

A et B sont **une seule faute a deux endroits** : une phrase fausse dans le livrable, et le
cas qui la fait paraitre verifiee.

### C. Le garde-fou v5 ne peut pas se declencher sur un agent qui s'effondre — **majeur**

`agents/campagne.py:392-394` :

```python
declenche = ecart_de_portee is not None and not (
    ecart_de_portee[1] > 0.0 or ecart_de_portee[2] < 0.0
)
```

La regle est « l'ecart apparie est-il **etabli**, intervalle excluant 0 ? Sinon, on
arrete ». Un ecart etabli **negatif** satisfait la condition : l'agent est declare en
progres et le run continue.

MESURE, regle recopiee sans rien y changer, 600 donnes appariees :

```
effondrement de 20 points   ecart -0,1780  IC [-0,1843 ; -0,1708]  etabli -> DECLENCHE : NON
agent parfaitement plat     ecart +0,0000  IC [+0,0000 ; +0,0000]  non etabli -> DECLENCHE : oui
```

Un agent dont la part fractionnee contre deux aleatoires chute de **17,8 points** sur trois
quarts d'heure, avec l'intervalle le plus net qu'on puisse mesurer, **ne declenche rien**.

**Ce n'est pas theorique pour cette phase.** L'arbitrage du tour 1 a retire du pool le
greedy **et** l'aleatoire, et a escalade en contrepartie le mode de defaillance vers
l'effondrement de convention, « mesure contre des checkpoints figes et rapporte ». Le
garde-fou contre deux aleatoires est le seul instrument par checkpoint qui verrait un
effondrement. La cinquieme version est aveugle a celui-la.

C'est le **cinquieme** defaut du meme garde-fou, et il est ne dans la correction du
quatrieme. La correction du defaut « il tue un agent qui apprend » a produit une regle qui
ne peut pas tuer un agent qui desapprend. Le correctif est d'une ligne — la condition juste
est `ecart_de_portee[1] <= 0.0`, c'est-a-dire « la borne basse n'est pas au-dessus de
zero » — mais **je ne corrige pas**.

### D. Le verdict de declenchement est lu dans le champ de la regle retiree — **mineur**

`mesure/rapport_phase3.py:419` choisit sa phrase sur `any(j.get("declenche") for j in jalons)`.
Ce champ a ete ecrit **pendant le run du 21/08 par la regle v3/v4** — « stagne et loin ».
`completer` n'ajoute que `parts_par_donne` et ne le recalcule pas ; le journal du run n'a
d'ailleurs aucun champ `ecart_de_portee`. La phrase imprimee, elle, decrit la v5 : « les 5
ecarts de portee 3 sont tous etablis ».

**Le rapport publie donc le verdict de la regle retiree sous le nom de la regle en vigueur.**
Ici les deux concordent, et j'ai verifie que les cinq ecarts sont bien etablis. Rien ne le
garantit : si le champ du journal disait « declenche » alors que les cinq ecarts sont
etablis, le rapport imprimerait une phrase qui contredit son propre tableau. La grandeur
juste est dans la portee, `de_portee`, deja en portee dans la fonction.

### E. Une signature qui decrit autre chose qu'elle-meme — **mineur**

`mesure/phase3_courbe.py:74` : `def serie_par_donne(...) -> tuple[float, ...]`, docstring
« rend sa part fractionnee par donne ». Elle rend `(part, basse, haute, gain, serie)` —
quatre flottants et un tuple. Ni l'annotation ni la phrase ne decrivent la valeur rendue.

### F. La parade du garde-fou fige un run au lieu de calculer le suivant — **mineur**

`portee_minimale` est presentee comme « la seule fonction du depot qui repond a la question
*cette regle peut-elle etre franchie a ce budget ?* », « appelee par un test plutot que
citee dans une docstring : c'est ce qui empeche le defaut de se refaire une cinquieme fois ».
Le cas qui l'appelle,
`tests/agents/test_campagne.py::test_une_portee_de_UN_serait_indetectable_a_ce_budget`,
lui passe **trois litteraux transcrits a la main** — `3.83`, `2.75`, `1.83` — releves sur ce
run. Il ne lit aucune donnee. Un budget different ou un rythme de progres different le
laisseraient vert avec `PORTEE_DU_GARDE_FOU = 3` inchangee.

Note de mesure, sans consequence ici : le `3,83` est la demi-largeur des ecarts de portee
**un**, alors que la regle juge un ecart de portee **trois**, dont je mesure la demi-largeur
a **3,98**. `portee_minimale(3,98 ; 1,828)` rend **3** aussi.

Et la phrase « ce qui empeche le defaut de se refaire une cinquieme fois » est deja
dementie par le defaut C, dans le meme fichier.

### G. Trois regles a deux sites — **mineur**

Convention §2, jamais deux sites pour une regle.

  - le predicat « etabli » : `mesure/bootstrap.py:96` (`EcartApparie.etabli`) et
    `agents/campagne.py:393`, reecrit a la main sur un tuple ;
  - la graine du bootstrap apparie, `GRAINE_BOOTSTRAP + 4 + numero` :
    `agents/campagne.py:381` et `mesure/phase3_courbe.py:177`. C'est elle qui fait
    concorder le run et le rejeu ; si l'un des deux bougeait, l'autre ne le signalerait pas ;
  - `mesure/phase3_courbe.py:177` ecrit `__import__("random").Random(...)` au lieu d'importer
    `random` en tete de module.

## Reserves, qui ne sont pas des defauts

**La parade des intitules est aveugle a un nom produit par un appel.**
`test_les_intitules_du_depot_sont_deux_a_deux_DISTINCTS` ne collecte que les `ast.Constant`.
J'ai redonne a la ligne du pool le nom du garde-fou **via `intitule_du_garde_fou()`** : le
cas reste **vert**. La correction a justement deplace un des deux noms dans une fonction.
Le doublon reste attrape par R2, qui recoit les chaines calculees, et
`test_R2_voit_le_doublon_de_nom_QUI_A_ECHAPPE_au_tour_1` l'eprouve — donc **une** des deux
parades tient, pas les deux. Je le signale pour que personne ne compte deux filets la ou il
y en a un.

**`documentations/05_protocole_experimental.md:504`** — hors de mon perimetre, et je ne
touche pas ce dossier. Le texte qui justifie la regle en vigueur ecrit encore : « les cinq
ecarts de portee trois valent +5,89, +5,54, +5,79, +6,05 et +5,07 points **pour un
detectable de 2,75** ». C'est la grandeur d'un **niveau**, celle que la relecture finale du
§5 a corrigee dans le code. Le protocole et `agents/campagne.py` ne s'accordent pas sur la
barre. Pour le pilote.

## Ce qu'une correction pouvait casser sans que les chiffres le montrent

C'est la question qui m'etait posee en propre, et elle a une reponse.

**Les 15 chiffres acquis sont identiques, et une route a change quand meme.** Le detectable
de **34 lignes** a change de fonction — `phase2.ecart_de_taux_detectable` puis
`ecart_detectable_deux_echantillons` — et les deux fonctions ne se comportent pas de la meme
facon sur un taux degenere. Aucun des quinze chiffres surveillés ne passe par la, donc aucun
n'a bouge, **et deux conclusions publiees ont bascule sans que rien ne le signale**. C'est
le defaut A. Verifier les valeurs acquises ne pouvait pas l'attraper : il fallait comparer
les deux tableaux ligne a ligne, ce que j'ai fait.

**Ce que j'ai verifie et qui n'a pas casse :**

  - `evaluer_le_garde_fou` passe de trois a quatre valeurs de retour. Les **deux** appelants
    sont a jour — `agents/campagne.py:374` et `mesure/phase3_courbe.py:92` ; il n'y en a pas
    d'autre ;
  - `Controle.passe` change de sens : un `releve` **passe** desormais. Le seul endroit qui
    compte les concluants passe par `eprouve` (`rapport_phase3.py:718`), et le seul qui
    filtre par `passe` imprime les echecs (`phase3_mesure.py:657`). Aucun compte n'est
    fausse — mais un futur `sum(c.passe for c in controles)` le serait ;
  - l'intitule du garde-fou est produit par `intitule_du_garde_fou(donnes)`, tandis que le
    rapport le redemande avec `intitule_du_garde_fou()`, donc au **defaut** de 600 donnes. Un
    run lance avec un autre `--donnes-garde-fou` donnerait a R2 un nom qui n'a jamais ete
    publie. Sans effet sur ce run ;
  - la garde de grain neuve de `verifier_inclusion_b1` n'a pas desactive celle de
    l'inclusion : les deux mordent, chacune sur sa faute.

## Verdict

**REJETE.**

Les quatorze defauts sont, dans leur grande majorite, corriges avec soin : les deux
bloquants sont traites au fond, la garde de reproduction du journal est reelle et mord au
`1e-9`, les parades AST mordent, les six nombres de `parties_requises` sont exacts au chiffre
pres, et le §5 a trouve dans ses propres corrections un defaut que je n'aurais pas releve
autrement. Le verdict ne porte pas sur ce qui manque.

**Il porte sur ce que les corrections ont introduit.** Une phrase fausse dans le livrable —
« aucune ligne ne change de statut » — sur les deux memes lignes que le defaut 4 concernait ;
un cas de test qui la protege en substituant `1` a `0` ; et une cinquieme version du
garde-fou qui ne peut pas se declencher sur le mode de defaillance que le pilote avait
escalade au tour 1.

**Pour la sixieme fois dans ce projet, le defaut neuf est ne dans la correction du
precedent.** Deux des trois sont dans `c0b073b`, pas dans la relecture finale : le §5 a
cherche au bon endroit, il n'a pas cherche assez loin.
