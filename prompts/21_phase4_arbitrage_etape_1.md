# Phase 4, iteration 1 — arbitrage du pilote sur les douze lignes

Destination : **conversation n° 8**. Ecrit le 24/08/2026.
Repond aux points 7 a 11, plus la question des trailers restee sans reponse.

---

## 0. Les etapes A a D sont acceptees

Onze survivantes, onze tombees. `EXPIRE` a disparu du releve. Suite a 1 290 verts.

Et tu rapportes le resultat qui compte le plus, celui qui est contre toi : **deux mutations ont
survecu au cas ecrit pour elles**, pour la meme raison les deux fois — un invariant tenu **a un
site** au lieu d'etre tenu **a tous ses sites**. `politique_reseau` en a trois, l'intitule du
garde-fou demandait deux parades qui ne se remplacent pas. Ecris cette phrase dans le journal de
la phase : c'est une regle generale, pas un incident.

---

## 1. Point 7 — le seuil intermediaire

Tu as raison, il n'etait pas chiffre. Voici sa forme, et **tu le pre-inscris toi-meme avant de
toucher au code**.

**Ce n'est pas un niveau, c'est un ecart, et il porte sa lateralite.** La barre n'est pas « R²
superieur a *x* ». Elle est :

> Le **R² hors plage** du critique neuf, **compare apparie** a celui du critique de la phase 3
> (+0,093) **sur le meme echantillon hors plage**, avec la **borne basse** de l'IC 99 % bootstrap
> par donne **strictement positive**.

Trois raisons de le poser ainsi, et elles sont deja dans le §0.2 :

- un niveau se compare a une population que sa phrase ne nomme pas ; un ecart apparie nomme les
  deux termes ;
- l'appariement par donne annule la variance de l'echantillon, qui est la meme pour les deux
  critiques ;
- **la lateralite fait partie du chiffre** : on cherche une amelioration, la borne basse suffit.

**Et le 0,57 ne sert a rien ici. Ne l'utilise dans aucun denominateur.** Il est calcule sur
l'etat COMPLET ; un critique aveugle ne peut pas l'atteindre, et personne ne sait de combien il
en est loin. Tu l'as vu et tu as eu raison de le dire. Il reste dans le rapport comme une borne
superieure de contexte, jamais comme cible et jamais comme diviseur.

**Rappel de ce que ce seuil n'est pas.** Il **ne decide rien**. Il diagnostique. Le seul seuil
qui tranche reste le gain moyen contre deux copies de l'agent de la phase 3, borne basse de
l'IC 99 % bootstrap par donne strictement positive. **Un critique repare qui ne fait pas gagner
est un resultat publiable**, pas un echec : il etablirait que le critique n'etait pas la limite.

---

## 2. Point 8 — la frontiere de `gamma` et `lambda`

Je la trace, puisque c'est mon travail. **Ta lecture est la bonne, et voici la ligne exacte.**

`gamma` et `lambda` definissent **l'estimateur d'avantage**. Ce qui est interdit, c'est de
changer la **quantite** que l'avantage estime. Ce qui est permis, c'est de changer la **facon
dont le critique apprend a predire cette meme quantite**.

Concretement :

| | |
|---|---|
| **PERMIS** — ponderer les echantillons de la perte de valeur (par profondeur, par exemple) | Le critique reste un estimateur de la meme cible ; on change de quoi il apprend le plus, pas ce qu'il predit |
| **PERMIS** — normaliser ou rescaler la cible du critique | A une condition sans exception, ci-dessous |
| **PERMIS** — changer la capacite ou l'architecture de la tete | N'a aucun rapport avec l'estimateur d'avantage |
| **INTERDIT** — bootstrapper la cible avec `gamma < 1`, ou introduire un `lambda < 1` | C'est litteralement changer `gamma` et `lambda` |

**La condition sans exception.** Si le critique predit une cible rescalee, **elle doit etre
remise a l'echelle de `R` avant d'entrer dans l'avantage**. L'avantage reste `R - V(s)`, les
deux termes dans la meme unite. Un avantage calcule entre un `R` brut et un `V` normalise
n'est pas un avantage : c'est un melange de deux grandeurs, et il serait faux sans rien lever
— exactement la faute que `valeur-non-aplatie` incarne. **Ecris un cas qui tient cette
egalite d'echelle avant de toucher a la cible.**

---

## 3. Point 9 — le budget, et l'ordre des trois soupcons

« 2 h par run » veut dire **2 h par run**. Mais je ne t'autorise pas trois runs en parallele,
et pas pour une raison de budget.

**Tes trois soupcons ne sont pas de meme force, et tu le dis toi-meme en les classant.**

- Le **point 3** — la cible terminale vue depuis n'importe quelle profondeur — est le seul qui
  s'appuie sur une **mesure** : le profil par profondeur, plancher a 0,0075 contre un critique
  a 0,30. C'est un facteur quarante, et aucune des deux autres hypotheses ne l'explique.
- Le **point 4** (la ponderation, `COEFFICIENT_VALEUR = 0,5` contre un avantage blanchi) et le
  **point 5** (la capacite, un `Linear` sur un tronc partage) sont **plausibles et non
  mesures**.

Donc : **un seul run, sur le point 3, d'abord.** 2 h. Puis tu mesures, et tu me rends le
resultat avant d'en lancer un deuxieme. Si le point 3 leve le R² hors plage, la question des
points 4 et 5 change de nature — et il se peut qu'elle ne se pose plus.

Lancer trois variantes tout de suite couterait 6 h pour repondre a une question a laquelle 2 h
suffisent peut-etre. **Ce n'est pas de l'economie, c'est le protocole** : une variable a la
fois, et on ne mesure la suivante qu'apres avoir lu la premiere.

---

## 4. Point 10 — `models/phase3/final.pt` : il existe, et c'est un point unique de defaillance

J'ai verifie, tout de suite, parce que ta question etait la bonne.

| | |
|---|---|
| Sur le disque | **oui** — `models/phase3/final.pt`, 503 025 octets, date du 21/08 10:19 |
| Dans le depot | **non** — `.gitignore` ligne 26 exclut `models/`, ligne 31 `models/phase3/` |
| Empreinte SHA-256 | `772a869fa2c10c9d28fd6d9d70f3a7aa555f18c27f4075b664c4d183f83f0217` |

**Le juge decisif de la phase 4 depend d'un fichier qui n'existe qu'a un seul endroit, non
suivi et non sauvegarde.** S'il disparait, l'agent de la phase 3 n'est plus reproductible : il
faudrait rejouer 2 h d'entrainement, et rien n'etablit qu'on retomberait sur les memes poids.

Ne commite pas 500 Ko de binaire — `models/` est ignore pour une bonne raison. Fais l'autre
chose, et fais-la a l'etape 2 :

**Inscris dans le depot l'IDENTITE du fichier et la RECETTE qui le produit** — l'empreinte
ci-dessus, le commit exact de la phase 3, la graine, la commande. Une empreinte prouve qu'on
joue bien contre le meme adversaire ; une recette dit comment le refaire. **Et un cas qui lit
l'empreinte du fichier present et leve si elle ne correspond pas.** Sans lui, un jour, le juge
decisif tournera contre un autre adversaire que celui qu'il nomme.

---

## 5. Point 11 — les deux copies ne partagent pas d'alea

**Non, et ce n'est pas une supposition : c'est deja ecrit et desormais tenu par un cas.**

`mesure/phase3.py` donne une graine par `(donne, siege de l'agent, place)`, avec le commentaire
« deux adversaires ne partagent jamais de generateur ». C'est la mutation
`adversaires-partagent-un-alea` — une des onze survivantes, que tu viens de faire tomber.

La regle vaut a l'identique pour deux copies du **meme** agent : deux copies qui partagent un
generateur jouent de facon correlee, et la composition mesuree n'est pas celle qui est annoncee.
Pre-inscris-le, comme tu proposais.

---

## 6. Les trailers — ma reponse, en retard, et le retard est de moi

Tu as pose la question hier et je n'ai pas repondu. J'ai verifie : **7 commits sur les 23 de la
branche portent un `Co-Authored-By`**, que le §1 de `09_reprise.md` interdit.

**Reecris la branche, et fais-le comme premier geste de l'etape 2.** Les conditions qui rendent
ca sans danger sont reunies et je les nomme : la branche n'est pas fusionnee dans `main`,
personne d'autre ne travaille dessus, et les anciens SHA restent dans le reflog. Retire les
trailers, force-push, et verifie qu'il n'en reste aucun avant de continuer.

**Ne le fais pas pendant qu'une campagne tourne.** Rien ne tourne aujourd'hui ; c'est le bon
moment, et c'est avant la fusion que ca doit etre fait, pas apres.

Tu as eu raison de ne pas le faire seul. Reecrire un historique deja pousse n'est pas une
decision d'agent.

---

## 7. Ce que tu fais ensuite, dans l'ordre

1. Reecrire la branche sans les trailers, verifier, pousser.
2. Pre-inscrire l'etape 2 : l'hypothese, l'instrument, le seuil intermediaire du §1 ci-dessus,
   le seuil decisif inchange, `sigma` et `rho` mesures sur ta composition, l'empreinte et la
   recette du §4, et la non-correlation du §5. **Rien de tout ca ne s'amende apres avoir vu une
   valeur.**
3. Le cas d'egalite d'echelle du §2, avant de toucher a la cible.
4. **Un** run, sur le point 3 seul. 2 h de plafond.
5. Me rendre le resultat. **Arret.** Les points 4 et 5 ne se lancent pas avant.

Et le piege ne change pas, il ne changera jamais de cette phase : **tu peux faire monter le R²
sans que l'agent joue mieux.**
