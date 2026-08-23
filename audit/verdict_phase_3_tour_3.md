# Re-verification — phase 3, tour 3 — VERDICT : ACCEPTE SOUS RESERVE

Perimetre : le commit `5bb9479` sur `phase-3-premier-agent`, contre les sept defauts que
j'ai trouves au tour 2 — A, B, C, D a G — et ma reserve. **Ce n'est pas un troisieme
audit** : je ne rouvre ni les douze defauts leves au tour 2, ni rien d'acquis au tour 1.

Controle de base : `git merge-base --is-ancestor 5bb9479 HEAD` — **OK** depuis
`audit-phase-3-tour-3`.

Mes reinjections : `audit/phase3_tour_3/mes_reinjections.py`.

## Ce que j'ai rejoue

| Controle | Resultat |
|---|---|
| Suite complete | **1172 verts, 0 rouge, 0 saute** — recomptes ici |
| Les 14 chiffres acquis du rapport | **tous presents, tous inchanges** ; seules bougent les durees machine |
| Arbre de travail | propre avant et apres chaque reinjection |

## Etat des sept defauts et de la reserve

| | Etat | Ce qui l'etablit |
|---|---|---|
| **A** — deux lignes changent de statut sous une phrase qui dit le contraire | **leve** | `separable` a trois etats, le rendu **leve**, les deux lignes sont separables par leur borne exacte, R4 nomme le traitement recu |
| **B** — le cas maquillait son entree | **leve** | trois parades, **les trois mordent** sous falsification |
| **C** — le garde-fou aveugle a un effondrement | **leve** | **mon** effondrement declenche maintenant ; un progres etabli ne declenche pas ; predicat a un seul site |
| **D** — verdict lu dans le champ de la regle retiree | **leve** | recalcule depuis `de_portee`, et un blockquote dit pourquoi |
| **E** — signature qui decrit autre chose qu'elle-meme | **leve** | `RejeuDeCheckpoint`, chaque champ sous son nom |
| **F** — parade qui fige un run au lieu de le mesurer | **leve** | 3,8333 pt et 1,8280 pt **mesures sur le journal**, refaits par moi |
| **G** — trois regles a deux sites | **leve** | `phase3.graine_du_garde_fou`, `import random` en tete, predicat dans `bootstrap` seul |
| **reserve** — la parade des intitules aveugle a un nom calcule | **PARTIELLEMENT levee** | elle attrape une des deux formes d'appel, et manque celle que le depot ecrit |

### A — les parades, eprouvees

**Les quatre cas de taux degenere sont tranches**, aucun ne repart non conclu, chacun avec
le nom de sa regle :

```
zero du cote BASE    separable=True   bornes exactes
zero du cote AGENT   separable=True   bornes exactes
LES DEUX a zero      separable=False  bornes exactes
bouts OPPOSES 0/100  separable=True   bornes exactes
CENT du cote agent   separable=True   bornes exactes
aucun degenere       separable=True   detectable a deux echantillons
```

**Le rendu leve.** J'ai fabrique une ligne qu'aucune regle ne tranche — taux non degeneres,
detectable `None` par effectif attendu sous 1 :

    ValueError: Z : aucune regle n'a tranche cette ligne (AUCUNE -- non conclu), et un
    tableau ne publie pas un verdict qu'il n'a pas calcule. Ecart 0.00799..., detectable
    None, agent 1000/3814, base 500/1967.

**Mes deux bornes.** `0/1967 -> 0,2338 %`, `0/10382 -> 0,0443 %`, refaites par moi. Les deux
lignes sont separables de tres loin, et le tableau le dit desormais.

### B — les trois parades, chacune sous falsification

  - j'ai remis `(1, 1967)` a la place de `(0, 1967)` dans le cas :
    **rouge**, `- bornes exactes -- un taux degenere / + detectable a deux echantillons` ;
  - j'ai remis `(1, 1967)` dans le cas **qui relit la source** : **rouge** ;
  - j'ai remis dans `mesure/resultats/phase3.md` le verdict du tour 2 :

        AssertionError: le rapport publie conclut sur des lignes a zero absolu sans les
        avoir calculees : ['`B4-contre-nature`']. « Non separable a ce budget » est une
        conclusion.

**Un cas qui va rechercher ses chiffres dans le document livre est la bonne reponse au
defaut B**, parce que contre une entree falsifiee une assertion soigneuse ne sert a rien.

### C — mon effondrement, repasse

```
effondrement -20 pt   ecart -0.1780  IC [-0.1843 ; -0.1708]  etabli  progres NON  -> DECLENCHE
progres      +20 pt   ecart +0.1783  IC [+0.1715 ; +0.1847]  etabli  progres OUI  -> non
stagnation exacte     ecart +0.0000  IC [+0.0000 ; +0.0000]  non etabli           -> DECLENCHE
```

C'est exactement le chiffre du tour 2 — `-17,80 pt, IC [-18,43 ; -17,08]` — et il declenche.
Le predicat vit dans `bootstrap.EcartApparie.progres_etabli` et nulle part ailleurs.

### F — les grandeurs sont mesurees

Refaites par moi depuis `models/phase3/journal.jsonl` : demi-largeur appariee **3,8333 pt**
(min 3,5602, max 4,0602), progres par checkpoint **1,8280 pt**, `portee_minimale = 3` pour
une portee retenue de 3. Les deux nombres du commit sont exacts.

### La reserve — partiellement levee, et je l'ai mesuree dans les deux formes

Le commit annonce : « la parade des intitules evalue les appels [...] donc redonner au pool
le nom du garde-fou via `intitule_du_garde_fou()` la fait tomber ». **C'est vrai d'une
ecriture sur deux.**

`_cle_d_un_intitule` resout un appel par
`getattr(<module du FICHIER ou l'appel se trouve>, <nom de la fonction>)`. Il evalue donc
l'appel seulement si la fonction est un attribut de module **du fichier appelant** :

| Ecriture donnee au pool | Parade |
|---|---|
| `from agents.campagne import intitule_du_garde_fou` puis `intitule=intitule_du_garde_fou()` | **rouge** |
| `from agents import campagne as X` puis `intitule=X.intitule_du_garde_fou()` | **VERT** |

La seconde est celle que le depot ecrit deja : `phase3_mesure.main()` importe
`from agents import campagne as campagne_module`, et `phase3_courbe` importe
`from agents.campagne import evaluer_le_garde_fou` dans le corps d'une fonction. J'ai donne
au pool **exactement** la meme chaine que le garde-fou par cette voie, verifie qu'elle est
identique, et la parade **reste verte**.

Le `getattr` cherche le nom dans le mauvais module : pour un `ast.Attribute`, il resout
`attr` contre le module appelant au lieu de l'objet dont l'attribut est pris.

**Et la garde de non-vacuite ne peut pas le voir.** `_cle_d_un_intitule` ne renvoie pas
`None` sur un appel non resolu : il retombe sur `ast.unparse`. L'appel entre donc dans `vus`
et compte dans `len(vus) >= 5` comme s'il avait ete resolu. J'ai instrumente le depot :
**1 appel resolu, 0 en repli** aujourd'hui — mon injection en aurait ajoute un que le
decompte n'aurait pas distingue. La garde compte ce qu'elle a **vu**, pas ce qu'elle a
**resolu**.

`R2` reste le second filet et l'attrape — je l'ai verifie, il passe au rouge sur ce doublon.
**Un filet sur deux, comme au tour 2**, et c'est pour cela que je ne compte pas la reserve
comme levee.

## Le point unilaterale / bilaterale : ETABLI

Refait par moi, et les chiffres du pilote tombent au quatrieme decimal :

```
0/1967    unilaterale 99 % = 0,2338 %    bilaterale 99 % = 0,2690 %    publie 0,2338 %
0/10382   unilaterale 99 % = 0,0443 %    bilaterale 99 % = 0,0510 %    publie 0,0443 %
```

`borne_haute_exacte_d_un_zero` calcule `1 - risque**(1/total)` avec `risque = 0,01` : c'est
la queue entiere d'un cote, donc une borne **unilaterale**. Le reste du rapport publie des
intervalles **bilateraux** — `mesure/resultats/phase3.md:49` ecrit meme, pour l'ecart
detectable, « **99 % bilateral** et 80 % de puissance ».

**Le depot le dit une fois, et le livrable ne le dit jamais.**

  - `mesure/phase3_mesure.py:385`, docstring de `separer_un_taux_degenere` : le seul endroit
    du depot ou le mot « unilaterale » apparait pour ces bornes. Et il le dit bien — 1 % du
    cote exact, 0,5 % du cote normal, total borne par 1,5 %, avec le motif ;
  - `borne_haute_exacte_d_un_zero`, docstring : « a 99 % », deux fois, sans qualificatif ;
  - `mesure/resultats/phase3.md` : « borne haute **a 99 %** », **quatre fois**, sans
    qualificatif — lignes 190, 221, 223, 250 ;
  - `mesure/phase3_entree_de_journal.md:104` : les deux nombres publies **sans aucun niveau**.

La conclusion ne bouge pas : 0,2690 % reste tres loin de 35,87 %. **C'est le libelle**, et
c'est la faute maison — deux grandeurs de risques differents sous le meme intitule, dans le
document qu'une phase suivante citera sans le rejouer. Le seul texte qui le corrige est une
docstring que le rapport ne reprend pas.

**Une seconde imprecision du meme genre, dans la meme cellule.** Le rapport ecrit « le zero
[...] a pour borne haute a 99 % 0.2338 %, **et l'agent est au-dela** » a cote de 35.87 %.
Ce que le code confronte est la **borne basse** de l'agent, **33,87 %** — le paragraphe 12
dit bien que le critere est un non-recouvrement, mais la cellule ne publie qu'une des deux
bornes du recouvrement.

## Defaut NEUF

### Le rendu du verdict exact est ecrit pour un des quatre cas que la regle couvre

`separer_un_taux_degenere` traite quatre cas, et sa symetrique
`borne_basse_exacte_d_un_cent` existe explicitement pour la suite : « le tableau de la
phase 3 ne porte aucun taux a 100 %, mais [...] une phase suivante qui en produirait un
retomberait sur le defaut qu'on vient de corriger. **La regle est ecrite pour les deux
bouts.** » La regle, oui. **La phrase qui la publie, non** — `mesure/rapport_phase3.py`,
branche `REGLE_BORNES_EXACTES`. Ce que j'obtiens en rendant les quatre cas :

| Cas | Ce que le rapport publie |
|---|---|
| zero du cote **agent** | « le zero **de la ligne de base** a pour borne haute a 99 % 0.2338 % » — **mauvais cote** |
| **cent** du cote agent | « **le zero** [...] a pour **borne haute** a 99 % **99.8793 %** » — ce n'est ni un zero, ni une borne haute |
| **les deux** a zero | « non separable -- la borne exacte [...] **croise l'intervalle de l'autre cote** » — il n'y a pas d'autre intervalle : les deux cotes sont degeneres, `borne_de_l_autre == borne` par construction, et la docstring de la fonction dit la verite : « l'ecart vaut exactement zero, il n'y a rien a etablir, **et c'est une conclusion** » |

`SeparationExacte` porte le champ `cote` — « agent », « ligne de base », « les deux » — qui
dit exactement ce qu'il faudrait pour ecrire ces trois phrases juste. **`Comparaison` ne le
garde pas** : seul `borne_exacte` traverse la frontiere, et l'information est jetee la ou la
phrase se compose.

**C'est le defaut A d'un cran en dehors** : une conclusion publiee en mots que le calcul ne
soutient pas. La difference, et elle compte pour le verdict : **aucun de ces trois cas n'est
atteignable sur les donnees de cette phase**, ou les deux zeros sont du cote de la ligne de
base. Le defaut est latent — mais la regle a ete etendue aux quatre cas precisement pour la
phase suivante, et c'est elle qui le rencontrera.

Le troisieme cas est le plus net : c'est celui que le correcteur dit avoir trouve **en
s'eprouvant**, et qui « aurait fait tomber la generation du rapport entier ». Il l'a traite
dans le calcul, pas dans la phrase.

## Ce que j'ai verifie de ses sept defauts neufs

Le plus instructif, refait par moi : le balayage du tour 2,
`range(2900, 3101, 20)`, donne **0 separables / 10 non separables** — il ne visitait bien
qu'une seule de ses deux branches. Celui du tour 3, `range(2700, 3301, 50)`, donne **6 / 6**,
et le cas exige desormais les deux. Son constat est exact.

La parade AST couvre les **deux** ecritures : j'ai injecte `passe=True` **par mot-cle** dans
`controle_denominateur` — **rouge**. Et elle exige d'avoir vu au moins 8 appels.

**J'ai cherche la meme famille ailleurs dans le depot** — un cas qui balaye, n'assert que
l'absence de faute, et resterait vert sur un balayage vide. J'ai instrumente les 17
candidats et les quatre qui lisent reellement le systeme de fichiers. **Aucun n'est vacuous**
en dehors de celui deja nomme : `test_a1_les_dix_huit_controles_de_conformite_existent` et
`test_les_neuf_documents_de_mesure_sont_dans_le_meme_encodage` assertent une **egalite** a un
ensemble nomme, donc un balayage vide les fait tomber ; mes deux controles P1 de
`tests/agents/test_aveuglement_reseau.py` lisent un fichier **nomme**, pas un `glob`, et
`read_text` leve s'il disparait. `tests/audit_phase3/` n'est pas sur cette branche.

**Une note sur ma propre methode, parce qu'elle est de la meme famille.** Ma premiere
injection du `passe=True` par mot-cle n'a rien injecte — mon ancre n'existait pas — et le
cas est reste vert. **J'ai lu ce vert comme un defaut avant de verifier que l'injection avait
eu lieu.** Toutes les reinjections de ce fichier verifient desormais leur ancre avant
d'ecrire, et le resultat ci-dessus est celui du second passage. Une injection qui ne
s'applique pas est une parade a vide, exactement comme celles que ce tour poursuit.

## Verdict

**ACCEPTE SOUS RESERVE.**

Les sept defauts sont leves, et pas de facon formelle : les trois parades du bloquant B
mordent toutes les trois, dont une qui va rechercher ses chiffres dans le document livre ;
mon effondrement du tour 2 declenche maintenant ; le rendu leve sur une ligne qu'aucune
regle n'a tranchee ; les deux bornes exactes sont justes au quatrieme decimal ; et la
relecture de son propre travail a trouve sept defauts de plus, dont un — le balayage a une
seule branche — que j'avais laisse passer au tour 2 en ne vérifiant que le cas symetrique.

**Trois reserves, aucune ne falsifie ce qui est publie sur ce run.**

1. **L'intitule « 99 % » couvre deux risques** dans le document livre. Le code le dit a un
   site ; le rapport et l'entree de journal ne le disent pas. Etabli, sans consequence sur
   la conclusion.
2. **Le rendu du verdict exact n'est ecrit que pour un des quatre cas** que la regle couvre.
   Latent sur ces donnees, atteignable par la phase suivante — celle pour qui la regle a ete
   etendue.
3. **La parade des intitules ne couvre qu'une des deux ecritures d'appel**, et c'est l'autre
   que le depot emploie. `R2` reste le seul filet sur cette forme, comme au tour 2.

Je ne corrige rien.
