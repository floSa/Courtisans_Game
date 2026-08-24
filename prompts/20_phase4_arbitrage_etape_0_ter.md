# Phase 4 — arbitrage du pilote sur le §5.0 et le §5.1, et une condition avant l'etape 0 ter

Destination : **conversation n° 8 — Construction de la phase 4**.
Ecrit par le pilote le 24/08/2026, apres verification independante sur `91db332`.

---

## 1. Verifie, et accepte

J'ai tout refait de mon cote. **Les deux etapes sont bonnes, et le releve est desormais
reproductible — c'etait mon reproche, il est leve.**

| Ce que j'ai verifie | Comment | Resultat |
|---|---|---|
| La suite est verte | `pytest tests -q` chez moi, arbre a `91db332` | **1 240 passed, 0 failed** en 168 s |
| Le compte des cas | `--collect-only` | **1 240**, dont **68** dans `tests/outillage/` — 1 172 + 68, l'ecart est entierement le tien |
| La passe de base et le temoin sont imprimes en tete | lecture du journal brut | `passe de BASE : 1240 verts, 0 rouges` puis `TEMOIN : 1240 verts, 0 rouges` |
| Les 57 verdicts | recomptage independant du journal brut | **45 detectees / 11 survivantes / 1 expiree** |
| La reproduction ligne a ligne | comparaison des rouges avec la campagne du 23/08 | **identiques** : 77, 22, 8, 64, 79, 45, 30, 23, 16, 12, 73, 17, 15, 10, 1 … Les verts montent de +68 partout, ce qui est exactement le nombre de cas que tu as ajoutes |
| Les quatre citations que tu ajoutes aux miennes | lecture des quatre lignes | **exactes, mot pour mot** — `reseau.py:118`, `campagne.py:18`, `campagne.py:257`, `phase3_mesure.py:388` |

**Et tu me corriges sur un point, avec raison.** Je rangeais
`perception-decide-sur-un-noeud-de-chance` parmi les invariants defendus par de la prose seule,
en citant sa clause `Raises:`. Tu la ressors de ce groupe : `perception.py:119` porte une
**levee reelle**, du code executable, que simplement aucun cas n'exerce. C'est une lecture plus
fine que la mienne et l'arithmetique suit — mes six moins celle-la, plus tes quatre, font tes
neuf. Publie-la comme tu l'as ecrite.

Le `TEMOIN` et `tombes_sous_TOUTES_les_mutations` sont deux bons instruments, et leurs
docstrings disent ce qu'ils n'etablissent pas. C'est du travail au-dessus de ce que je
demandais.

---

## 2. Une condition avant l'etape 0 ter

Un seul point, et il est sur le chemin de ce que tu t'appretes a ecrire.

### 2.1 — Le temoin est hors de sa propre population

`MUTATION_TEMOIN` edite **`mesure/instance.py`**. J'ai verifie : ce fichier **ne porte aucune
des 57 mutations**. Le temoin mesure donc que la suite ne reagit pas a l'edition d'un fichier
*que la campagne n'edite jamais*.

Sa docstring ecrit : « Le temoin le ferme comme **CLASSE** ». Elle ne le ferme pas. Elle etablit
qu'aucun test ne reagit a l'edition de `mesure/instance.py`. Un test qui reagirait a l'edition
de `agents/reseau.py` serait **vert sous le temoin**, et il ne tomberait que sous les 4
mutations de ce fichier — donc **jamais sous les 57**, donc `tombes_sous_TOUTES_les_mutations`
ne le verrait pas non plus.

**Un chiffre exact sur une population que sa phrase ne nomme pas.** C'est la faute de signature
de ce projet, et elle vient de se glisser dans l'instrument construit pour l'empecher. C'est le
troisieme etage du meme escalier : le blocage sans delai de garde, puis les deux tests miroirs
nes dans la correction, puis ceci.

### 2.2 — Et la place est deja occupee

Ce n'est pas une objection de principe. J'ai croise les 20 fichiers mutes avec les tests qui
lisent une source depuis le disque :

| Fichier mute | Mutations | Lu depuis le disque par |
|---|---:|---|
| `agents/campagne.py` | **6** | `tests/mesure/test_phase3_audit.py` |
| `agents/reseau.py` | **4** | `tests/agents/test_aveuglement_reseau.py` |
| `mesure/comportements.py` | **2** | `tests/audit_phase2/test_reverification.py` |

**Douze des 57 mutations portent sur un fichier dont un test lit la source.** Et ce ne sont pas
douze mutations quelconques : `agents/campagne.py` porte **quatre des onze survivantes**, et
`agents/reseau.py` porte `valeur-non-aplatie` — la survivante qui est dans le fichier que
l'iteration 1 va modifier.

**Ce que ceci N'ETABLIT PAS, et je le dis avant que tu ne le lises de travers : aucun test ne
tombe aujourd'hui de cette facon.** Tes 57 verdicts se reproduisent a l'identique, ce qui est
la meilleure preuve possible qu'aucun ne le fait. **Rien de publie n'est fausse.** C'est un trou
de l'instrument, pas un defaut du chiffre.

Mais c'est un trou sur le chemin. A l'etape 0 ter tu vas ecrire neuf cas sur
`agents/reseau.py`, `agents/entrainement.py`, `agents/campagne.py`, `agents/politique_reseau.py`,
`agents/perception.py` et `mesure/phase3.py`. **Trois de ces fichiers ont deja un test qui lit
leur source**, et ta pente naturelle est d'en ecrire ainsi — tu viens de le faire deux fois. Le
defaut qui a coute la campagne d'hier est a une frappe de revenir, sous une forme que tes deux
instruments neufs ne voient pas.

### 2.3 — Ce que je te demande

Dans l'ordre, et avant le premier des neuf cas :

1. **Deplace le temoin sur un fichier qui porte des mutations.** Un temoin doit vivre dans la
   population dont il parle.
2. **Un temoin par fichier mute qui est lu depuis le disque** — les trois du tableau ci-dessus.
   Trois passes de plus par campagne, environ 8 minutes. C'est ce qui ferme la classe **la ou
   elle est peuplee**, au lieu de l'affirmer.
3. **Une parade statique, en liste de noms.** Un cas qui enumere les couples (fichier mute, test
   qui lit sa source), les compare a une **liste nommee**, et exige qu'un couple nouveau soit
   inscrit avec, en une ligne, pourquoi ce test ne reagit pas a l'edition. Ca ne coute aucune
   passe, ca tourne a chaque suite, et **c'est la seule des trois qui attrape le couple que TU
   vas creer** en ecrivant tes neuf cas. Le message d'echec du cas que tu as renomme dit deja la
   regle : « Un compte se perime, une liste non. »
4. **Corrige la docstring de `MUTATION_TEMOIN`.** « ferme comme CLASSE » devient ce que le
   temoin etablit vraiment, et la limite s'ecrit a cote : un temoin ne parle que des fichiers
   qu'il edite.

Puis rejoue la campagne. Elle ne devrait rien changer aux 57 verdicts — et si elle change
quelque chose, c'est le resultat le plus important de l'etape 0.

---

## 3. L'ordre, mis a jour

1. ~~§5.0 — la suite au vert, la passe de base, la campagne rejouee.~~ **Fait, verifie, accepte.**
2. ~~§5.1 — les trois ajouts au rapport.~~ **Fait, verifie, accepte.**
3. **Le §2 de ce document** — le temoin remis dans sa population, les trois temoins de fichier,
   la parade statique, la docstring corrigee, la campagne rejouee.
4. **Etape 0 ter** — les neuf trous du §3.1 de `prompts/19`, le delai de garde par test, le
   rejeu de `masse-binomiale-part-de-zero`. Les trois exigences du §4 de `prompts/19` tiennent
   sans changement : ce que chaque cas etablit et sur quelle population ; rouge sous sa mutation
   et vert sans ; **jamais ecrit depuis le `avant`/`apres` de la mutation**, toujours depuis
   l'invariant tel que la docstring l'enonce.
5. **Etape 0 bis** — les trois reserves.
6. **Etape 1 et suite** — `prompts/18`, sans changement. Le seuil qui decide reste le gain moyen
   contre deux copies de l'agent de la phase 3, borne basse de l'IC 99 % bootstrap par donne
   strictement positive. Et le piege reste le meme : **tu peux faire monter le R2 sans que
   l'agent joue mieux.**

Un mot pour finir, parce qu'il serait injuste de ne relever que ce qui manque. Tu as trouve
ton propre defaut, tu l'as montre avant de le reparer, tu as commite le journal du rejeu
invalide **sous son nom**, et tu as ferme la classe au lieu de l'instance. C'est exactement ce
que le protocole demande et c'est rare. Le §2 ci-dessus ne dit pas que tu as mal fait : il dit
que l'escalier a une marche de plus.
