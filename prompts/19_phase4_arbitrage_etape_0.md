# Phase 4, iteration 1 — arbitrage du pilote sur l'etape 0

Destination : **conversation n° 8 — Construction de la phase 4**.
Ecrit par le pilote le 23/08/2026, apres recalcul independant du compte des mutations.

---

## 1. Ce que j'ai recalcule moi-meme, et ce que ca donne

Je n'accepte pas un chiffre d'agent sans le refaire. Le verdict tient en deux phrases, et
elles ne disent pas la meme chose :

> **Ton compte est exact, sur les trois populations que tu nommes.** Je l'ai refait, et je le
> confirme, y compris sur six mutations que j'ai rejouees moi-meme.
>
> **Et il n'est aujourd'hui reproductible par personne**, pour une raison que le §1.2 etablit
> et qui ne vient pas de ta mesure.

| Ce que j'ai verifie | Comment | Resultat |
|---|---|---|
| Le total des motifs | import de `MUTATIONS`, comptage par fichier | **57** — `courtisans/` 20, `agents/` 20, `mesure/` 17 |
| L'exemption de l'etalon | `[m.nom for m in MUTATIONS if m.fichier in FICHIERS_EXEMPTS]` | **liste vide** — `agents/greedy.py` porte 0 mutation |
| L'unicite des noms | `Counter` sur `m.nom` | **aucun doublon** |
| L'unicite de chaque `avant` dans son fichier | `src.count(m.avant) == 1` sur les 57 | **57/57**, aucune exception |
| La validite Python de chaque version mutee | `ast.parse` sur les 57 textes mutes | **57/57 valides** — aucune « detection » n'est une `SyntaxError` |
| Le releve brut contre le tableau de synthese | relecture des 57 lignes du rapport | **45 detectees / 11 survivantes / 1 expiree**, et le detail par racine reproduit exactement `20-0-0`, `11-9-0`, `14-2-1` |
| `verts + rouges` | sur les 56 lignes qui portent un verdict | **= 1 172 partout**, aucune ligne ne fuit |
| « les rouges vont de 1 a 79, mediane 5 » | sur les **45 detections** | **exact** — min 1, max 79, mediane 5 |

Deux remarques sur la derniere ligne. Ta phrase nomme sa population (les detections) : c'est
bien. Sur cet echantillon, **14 des 45 detections ne tiennent qu'a UN seul test rouge**, et 20
a quatre ou moins. Ce chiffre-la merite d'etre publie a cote du « 1 a 79 » : il dit combien
de tes detections sont a une reecriture de test de devenir des survivantes.

**Le controle de base est bon de mon cote aussi** : `9eb61e0` est ancetre de `HEAD` (`cb9000b`),
arbre propre, la branche `phase-4-tete-de-valeur` est poussee.

J'ai en outre rejoue moi-meme six mutations avec ton outil, choisies pour que le resultat soit
discriminant : les quatre qui portent sur la tete de valeur, une du garde-fou, et **une detection
faible en temoin** — si mon rejeu rendait « survit » partout, il ne prouverait rien.

### 1.1 — Le rejeu, et ce qu'il a fallu pour le lire

Voici ce que mon rejeu a rendu, brut :

| Mutation | Ton verdict | Verts | Rouges | Mon verdict brut |
|---|---|---:|---:|---|
| `bornes-de-joueurs-desynchronisees` (temoin) | detectee, 1 rouge | 1170 | **2** | detectee |
| `valeur-non-aplatie` | **SURVIT** | 1171 | **1** | detectee |
| `politique-reseau-observe-le-siege-zero` | **SURVIT** | 1171 | **1** | detectee |
| `avantage-sans-ligne-de-base` | **SURVIT** | 1171 | **1** | detectee |
| `tete-plus-grande-que-l-espace-d-action` | **SURVIT** | 1171 | **1** | detectee |
| `garde-fou-se-contente-d-un-ecart-etabli` | **SURVIT** | 1171 | **1** | detectee |

Cinq de tes onze survivantes sortaient **detectees** chez moi. Sans le temoin j'aurais conclu
que tes survivantes n'existent pas.

Le temoin dit autre chose : **il rend 2 rouges la ou tu en publies 1.** Chacun de mes six
chiffres vaut le tien **plus exactement un**. Un decalage constant n'est pas un desaccord de
mesure, c'est un terme additif. J'ai donc joue la suite **sans aucune mutation** :

```
1 failed, 1171 passed in 161.76s
FAILED tests/audit_phase2/test_reverification.py::test_les_neuf_documents_de_mesure_sont_dans_le_meme_encodage
```

**La suite est ROUGE sur `cb9000b`.** Le rouge est le tien : le test exige que tout document
de `mesure/` soit inscrit dans la liste nommee `DOCUMENTS_DE_MESURE`, et **tu as commite
`mesure/resultats/phase4_mutations.md` sans l'y inscrire**. Ton propre rapport d'etape 0 casse
un test de la suite dont ce meme rapport publie le total.

Retire le terme additif, et **tes onze verdicts sont confirmes, les six que j'ai rejoues** :
1170-2 devient 1-rouge pour le temoin, 1171-1 devient **0 rouge** pour les cinq autres. Ta
campagne a tourne avant ce commit, sur une suite verte ; ses chiffres sont bons. **Je le dis
aussi nettement que je dirais l'inverse.**

### 1.2 — Ce que cet incident etablit, et qui est plus grave que le test casse

**`outillage/mutation.py` n'etablit jamais sa ligne de base.** `principal` verifie que le
depot est propre ; il ne joue **pas une seule fois la suite non mutee** avant de commencer.
`_jouer` rend `(verts, rouges)` et `principal` ecrit `detectee` des que `rouges` est non nul —
sans jamais savoir si ce rouge vient de la mutation.

La consequence se calcule, elle ne se craint pas :

> **Un seul rouge preexistant fait que la campagne entiere rapporte zero survivante.** Sur
> `cb9000b` aujourd'hui, une campagne complete rendrait **56 detectees, 0 survivante, 1
> expiree** — et les 56 seraient fausses.

C'est le pire mode de defaillance possible pour cet outil : **il annonce une suite parfaite
exactement quand la suite est cassee.** Le rouge preexistant se deguise en detection sur les
57 lignes a la fois. Et ce n'est pas une hypothese : c'est l'etat du depot maintenant. Qui que
ce soit rejouant ta campagne aujourd'hui obtient un feu vert integral et faux.

Trois choses en decoulent, et elles passent **avant** tout le reste :

1. **Inscris le document par son nom** dans `DOCUMENTS_DE_MESURE`, et remets la suite au vert.
   Le message du test te le dit deja : « Un compte se perime, une liste non. »
2. **Donne a `mutation.py` une passe de base** : joue la suite non mutee **une fois, en tete
   de campagne**, et **refuse de commencer** si elle n'est pas verte. Un outil qui mesure des
   ecarts doit refuser de tourner quand son zero n'est pas a zero. Rapporte le compte de la
   passe de base en tete du releve, pour que tout lecteur voie le zero sur lequel les 57
   ecarts sont lus.
3. **Rejoue la campagne apres**. Je ne demande pas ce rejeu parce que je doute de tes onze —
   je viens de les confirmer sur six. Je le demande parce que **le releve publie n'est
   aujourd'hui reproductible par personne** : celui qui le refait n'obtient pas tes chiffres.
   Un resultat qu'on ne peut pas refaire n'est pas un resultat, quelle que soit sa justesse.

Et une remarque qui n'est pas une consolation. Le test qui est tombe s'appelle
`test_les_neuf_documents_de_mesure...` : il y en a **dix** desormais. Ce test, ecrit pour
imposer une liste de noms contre un compte, porte un **compte** dans son propre nom, et ce
compte vient de se perimer. Renomme-le en meme temps.

---

## 2. Ce que ton rapport dit, et ce qu'il ne dit pas encore

Ton rapport range les 11 par consequence. Il manque une lecture, et c'est la plus utile pour
la suite : **la forme que ces trous ont tous.**

J'ai ouvert le code de chaque survivante. **Au moins six des onze cassent un invariant qui est
ecrit, en toutes lettres, dans un commentaire ou une docstring a cote de la ligne meme :**

| Survivante | Ou l'invariant est ecrit | Ce qui l'y defend |
|---|---|---|
| `politique-reseau-observe-le-siege-zero` | `agents/politique_reseau.py`, docstring de module, section entiere | « Cette fonction ecrit `tenseur(etat, etat.current_player())`. C'est exactement la ligne que l'obstacle A rendait dangereuse » |
| `garde-fou-se-contente-d-un-ecart-etabli` | `agents/campagne.py:402`, commentaire | « **`progres_etabli`, pas `etabli`.** La v5 demandait « etabli » [...] » |
| `pool-garde-les-plus-anciens` | `agents/campagne.py:379`, commentaire | « Le plafond garde les **plus recents** : un pool rempli de versions tres faibles dilue le signal » |
| `adversaires-partagent-un-alea` | `mesure/phase3.py:267`, commentaire | « Un alea par (donne, siege de l'agent, place) : deux adversaires ne [le partagent pas] » |
| `avantage-sans-ligne-de-base` | `agents/entrainement.py:22`, docstring | « A `lambda = 1` l'avantage vaut `R - V(s)` » |
| `perception-decide-sur-un-noeud-de-chance` | `agents/perception.py:115`, clause `Raises:` | « si l'etat est terminal ou sur un nœud de chance. Un agent n'y decide [pas] » |

« Au moins six » est un plancher que j'ai verifie ligne a ligne, pas un total que je devine.

**La lecture : dans ce depot, les invariants les plus durement acquis sont defendus par de la
prose posee a cote de la ligne, et par rien d'autre.** L'obstacle A, la cinquieme version du
garde-fou, la composition annoncee de la phase 3 : trois choses qui ont coute cher a etablir,
trois commentaires, zero test. Une prose ne tombe pas quand on la contredit. C'est le mode de
retour que le §0.2 decrit, et ta campagne vient de le mesurer sur six cas au lieu de l'affirmer.

Publie cette lecture dans le rapport. Elle vaut plus que le compte.

---

## 3. L'arbitrage : ce qui se comble maintenant, ce qui attend

Tu me demandes si tu combles tout ou partie des 11 avant l'etape 0 bis. Je ne reponds pas par
un nombre, je reponds par un **critere**, pour qu'il se verifie au lieu de se croire :

> **Un trou se comble maintenant si, et seulement si, il porte sur du code que l'iteration 1
> va MODIFIER, ou sur du code que traverse le chiffre qui DECIDE, ou sur du code qui peut
> ARRETER le run.**

Un trou hors de ces trois cas se consigne et attend : le combler serait du travail utile fait
au mauvais moment, et le protocole demande une variable a la fois.

J'ai trace les appelants avant de trancher, pas apres. Ce que ca donne :

### 3.1 — A combler avant l'etape 3 : **neuf**

**Parce que l'iteration 1 modifie ce code (4).**

| Survivante | Pourquoi elle est sur le chemin |
|---|---|
| `valeur-non-aplatie` | C'est la tete elle-meme. `agents/reseau.py:125` rend `self.tete_valeur(cache).squeeze(-1)`. Sans le `squeeze`, la MSE de `entrainement.py:347` diffuse en `n x n` **sans rien lever** — et `347` est la ligne exacte que tu vas toucher. Je m'apprete a te faire modifier une ligne dont aucun test ne tient la forme des deux operandes. |
| `avantage-sans-ligne-de-base` | `entrainement.py:321`, `avantages = retours - valeurs`. C'est **ce a quoi la tete de valeur sert**. Rien n'etablit qu'elle sert de ligne de base : annuler sa contribution ne fait tomber aucun cas. Reparer un organe dont la suite ne sait pas qu'il est branche, c'est reparer a l'aveugle. |
| `tete-plus-grande-que-l-espace-d-action` | Le controle de `construire` ne teste qu'un sens, tete trop petite, et sur le seul etat initial. L'iteration 1 reconstruit le reseau. |
| `politique-reseau-observe-le-siege-zero` | Le chemin de decision de l'agent **mesure**. La preuve P2 interdit `vue_privilegiee()` ; elle ne verifie pas que le siege observe est celui qui decide. Le code est juste — j'ai lu `politique_reseau.py:66` et `:84`, les deux ecrivent `tenseur(etat, etat.current_player())` — mais rien ne le tient. |

**Parce que le chiffre qui decide passe par la (2).**

| Survivante | Pourquoi elle est sur le chemin |
|---|---|
| `adversaires-partagent-un-alea` | `phase3.jouer_composition` est appelee par `mesure/phase3_mesure.py:179` — **le juge** — et par `agents/campagne.py:284` — **le garde-fou**. Si les deux adversaires jouent correles, le gain publie n'est pas le gain de la composition annoncee. |
| `perception-decide-sur-un-noeud-de-chance` | `percevoir` est appelee par `agents/politique.py:34,48` — **le chemin de decision du greedy, l'etalon** — et par `mesure/trace.py:215`, qui produit les traces que lisent B4 et le retournement. La levee est la parade contre l'obstacle A sur ce chemin-la. |

**Parce que ce code peut arreter le run, ou decider ce que l'agent apprend (3).**

| Survivante | Pourquoi elle est sur le chemin |
|---|---|
| `garde-fou-se-contente-d-un-ecart-etabli` | `campagne.py:407` decide si le run continue. Le predicat a sa parade, le **site d'appel** n'en a aucune. Le cinquieme defaut du garde-fou peut revenir par le cablage sans qu'un test bouge — et il tuerait l'iteration 1 en cours de route. |
| `garde-fou-sans-bonferroni` | Meme decision, son intervalle. Le `z = 3,2272` est calcule et imprime ; aucun test ne verifie que l'IC des jalons est celui-la. |
| `pool-garde-les-plus-anciens` | `campagne.py:381`. Le pool est **ce contre quoi l'agent s'entraine**. Jeter le plus recent au lieu du plus ancien change ce qui est appris, pas seulement ce qui est mesure. |

### 3.2 — A traiter a l'etape 0 bis, avec leur reserve : **deux**

`intitule-du-garde-fou-sans-population` **est** la reserve 3, mesuree.
`separation-exacte-toujours-disjointe` **est** dans le code de la reserve 2.

Ne les traite pas deux fois. A l'etape 0 bis, chacune se corrige **avec sa parade**, pas
seulement avec son rendu — tu l'avais dit toi-meme pour la seconde, je l'etends a la premiere.
Une reserve levee dont la mutation survit toujours n'est pas levee : elle est reecrite.

### 3.3 — L'expiree : un verdict, pas un trou-fantome : **une**

`masse-binomiale-part-de-zero` ne rend aucun verdict. Ton diagnostic est le bon et ta
correction de l'outil aussi. Mais tu laisses le second trou ouvert, et il est sur le chemin :
`mesure/binomiale.py` est ce qui **dimensionne un budget**, et l'iteration 1 pre-inscrit un
budget. Donc :

1. Donne a la suite **son propre delai de garde, par test** — un test qui boucle doit y etre
   discernable d'un test lent. Le delai se choisit sur une mesure du test le plus lent, pas
   sur un chiffre rond.
2. **Rejoue ensuite cette mutation** pour qu'elle rende enfin un vrai verdict : detectee ou
   survivante. Si elle sort survivante, elle rejoint le 3.1.

`EXPIRE` doit rester un etat de l'outil. Ce ne doit pas devenir une case ou l'on range ce
qu'on ne sait pas.

---

## 4. Comment un trou comble se prouve comble

C'est ici que le travail peut se saboter tout seul. Ecrire un test pour faire tomber une
mutation est exactement la situation ou nait un test decoratif. Trois exigences, non
negociables :

1. **Chaque nouveau test dit en une ligne CE QU'IL ETABLIT ET SUR QUELLE POPULATION.** Un test
   sans cette ligne ne compte pas comme un trou comble.

2. **Chaque nouveau test est montre ROUGE sous sa mutation et VERT sans elle.** C'est la seule
   preuve qu'il tient quelque chose. Publie les deux etats.

3. **N'ecris aucun test en lisant le `avant` / `apres` de la mutation.** Ecris-le depuis
   l'invariant tel que la docstring ou le commentaire l'enonce — les six du §2 te le donnent
   deja redige. Un test ecrit d'apres la mutation est un miroir de la mutation : il tombe sur
   elle et sur rien d'autre. C'est la meme raison qui fait qu'un auditeur reimplemente au lieu
   de relire.

Et un cas a ne pas escamoter :

> **Si un nouveau test sort rouge sur le code NON mute, ce n'est pas un test a corriger.
> C'est un defaut reel, et tout s'arrete.** Tu me le remontes tel quel, avec le chiffre, sans
> le reparer. Un defaut trouve puis corrige par celui qui l'a trouve, le §5 du protocole
> d'audit croise le compte comme disqualifiant.

Quand les neuf sont combles : **rejoue les dix mutations concernees** (les neuf plus
`masse-binomiale-part-de-zero`) avec `--noms`, pas la campagne entiere — environ 27 minutes au
lieu de deux heures et demie. Publie le tableau avant/apres. Une mutation qui survit encore
apres qu'un test a ete ecrit pour elle est le resultat le plus interessant du lot : dis-le.

---

## 5. L'ordre, desormais

0. **D'ABORD, et avant de lire le reste de ce document** — la suite au vert, la passe de base
   dans `mutation.py`, la campagne rejouee. Les trois du §1.2. Tant que ce n'est pas fait,
   **aucun chiffre de mutation produit dans ce depot ne veut rien dire**, y compris ceux que
   les etapes suivantes vont produire. Remonte-moi le releve rejoue avec son compte de base
   en tete.
1. **Etape 0** — le compte est accepte. Ajoute au rapport la lecture du §2, le « 14 detections
   sur 45 ne tiennent qu'a un rouge », et l'incident du §1.2 : il appartient au rapport, parce
   qu'il porte sur l'instrument qui a produit le rapport.
2. **Etape 0 ter** — les neuf trous du §3.1, plus le delai de garde de la suite et le rejeu de
   `masse-binomiale-part-de-zero`.
3. **Etape 0 bis** — les trois reserves, chacune dite separement, deux d'entre elles avec la
   mutation qui les mesure (§3.2).
4. **Etape 1 et suite** — comme `prompts/18_phase4_iteration_1.md` les ecrit, sans changement.

L'etape 0 bis passe apres l'etape 0 ter : deux des trois reserves ont maintenant une mutation
qui les mesure, et il vaut mieux les corriger une fois, avec leur parade, que deux fois.

Rien d'autre ne change dans `prompts/18`. En particulier, **le seuil qui decide reste le
gain moyen contre deux copies de l'agent de la phase 3, borne basse de l'IC 99 % bootstrap par
donne strictement positive** — et le piege reste le meme : **tu peux faire monter le R2 sans
que l'agent joue mieux.**

Un dernier mot sur ce que tout ce §3 ne dit pas. **Combler neuf trous ne rend pas la suite
bonne.** Ca rend tenus les neuf endroits que je viens de nommer. Les ~2 500 lignes que tes 37
motifs n'echantillonnent pas restent exactement aussi peu tenues qu'avant, et ton rapport a
raison de le dire.
