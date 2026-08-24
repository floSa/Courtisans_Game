# Phase 4, iteration 1 — arbitrage de cloture

Destination : **conversation n° 8**. Ecrit par le pilote le 24/08/2026.
Repond au releve `phase4_le_plafond_du_critique.md`.

---

## 1. J'ai refait ta mesure avec ma propre implementation. Elle tient.

Je n'ai reutilise du depot que le moteur pour **jouer** — c'est du calcul, pas une conclusion.
L'ajustement du regresseur, la separation des seeds, l'arret precoce et le R² sont ecrits par
moi, sans lire ton `mesure/phase4.py`. Seeds de test 900000+, seeds d'apprentissage 500000+,
disjoints, tous deux hors plage.

| | toi | moi |
|---|---:|---:|
| Critique de la phase 3, R² hors plage | +0,1012 | **+0,0958** |
| Regresseur, ~29 k nœuds | — | +0,0733 |
| Regresseur, ~115 k nœuds | +0,0871 (77 k) | +0,0915 |
| Regresseur, ~461 k nœuds | +0,1035 (307 k) | **+0,1071** |
| Pente par doublement | +0,0079 | **+0,0078 a +0,0091** |
| Plus de capacite aide-t-elle ? | non | **non** — largeur 128 sous largeur 32 aux **trois** volumes |

Deux choses meritent d'etre dites nettement.

**La pente se reproduit.** Mesuree sur deux intervalles differents des tiens, avec un autre
regresseur et un autre optimiseur, elle donne le meme +0,008. Extrapolee depuis mon point a
461 k, elle predit **+0,121 a 1,54 M** — ton chiffre mesure est **+0,1217**. Deux
implementations independantes tombent sur la meme courbe a la troisieme decimale.

**Ton point le plus important est confirme, et c'est celui qui va contre le plan** : un
regresseur hors ligne, avec acces libre aux memes donnees et un arret precoce choisi **sur le
test** — donc une borne haute optimiste — ne depasse le critique de la phase 3 que d'environ
**+0,01 a +0,02**. Le critique n'est pas mauvais. **Il est pres du plafond de ce qu'un
observateur aveugle peut atteindre dans ce jeu.**

Je le dis aussi nettement que j'aurais dit l'inverse : **l'hypothese de l'iteration 1 est
refutee, et c'est ta mesure qui l'a etablie, avant l'entrainement.**

---

## 2. Je clos l'iteration 1 sur le constat. Le run de 2 h ne se lance pas.

Tu ne le lances pas, et voici le raisonnement, pour qu'il soit auditable.

- Le seuil intermediaire que j'avais specifie est **franchissable** : la marge existe, elle vaut
  ~+0,02. Un run pourrait le franchir.
- Mais **le seuil intermediaire ne decide rien**, et je l'avais ecrit dans `prompts/21` §1.
  Seul le gain contre deux copies de l'agent de la phase 3 tranche.
- Or rien n'etablit qu'une precision de 0,12 fasse gagner la ou 0,10 fait perdre. **Lancer le
  run reviendrait a payer 2 h pour deplacer une grandeur intermediaire dont on ignore si elle
  commande le resultat.** C'est le piege que ce prompt repete depuis le debut, sous une forme
  plus fine : non plus « faire monter le R² sans jouer mieux », mais « faire monter le R² de
  deux centiemes en esperant que ca compte ».

**Ce que la phase 4 iteration 1 produit n'est donc pas un agent. C'est un resultat negatif
solide**, et `prompts/18` le designait d'avance comme publiable : *« un critique repare qui ne
fait pas gagner etablirait que le critique n'etait pas la limite »*. La mesure fait mieux : elle
etablit qu'il n'y avait presque rien a reparer.

---

## 3. Ce que tu ecris, et rien de plus

**Une entree de journal**, dans `documentations/06_journal_decisions.md`, au-dessus de celle de
la phase 3. Elle porte :

1. **L'hypothese, telle qu'elle etait pre-inscrite**, et le fait qu'elle est **refutee**.
2. **Les chiffres, chacun avec sa population nommee** — c'est la faute de signature du projet,
   ne la refais pas ici. Le critique a +0,10 : sur quel echantillon, combien de nœuds, quels
   seeds. Le plafond a +0,12 : idem, et **avec la mention que l'arret precoce est choisi sur le
   test, donc que c'est une borne haute optimiste**.
3. **La pente de +0,008 par doublement**, et sa consequence chiffree : 53 doublements pour
   atteindre 0,545, ce qui est une reduction a l'absurde et **pas une prediction**.
4. **La distinction qui porte tout le resultat** : le plancher de 0,545 est calcule sur l'etat
   **complet**. L'ecart entre +0,12 et 0,545 n'est pas un manque de donnees ni un defaut de
   modele — **c'est ce que le jeu cache a un joueur honnete**. Ecris-le en toutes lettres.
5. **Ce qui est infirme** : le point 5 de mon arbitrage — plus de capacite **empire** la
   generalisation. Aux trois volumes, chez toi comme chez moi.
6. **Ce qui garde son diagnostic mais perd son remede** : le point 3. Le critique est bien
   presque nul tot, mais les nœuds tardifs pesent 8,2 % de la perte. Ponderer vers la
   profondeur viserait 8 % du probleme.
7. **Ce que ce constat N'ETABLIT PAS.** Au minimum : qu'un R² plus eleve ferait gagner ; que
   l'architecture testee soit la meilleure possible ; que la pente reste lineaire au-dela de
   1,5 M nœuds. Une extrapolation de trois intervalles n'est pas une loi.
8. **La lecon de methode**, et elle est a toi : tu as mesure le plafond **avant** d'ecrire la
   pre-inscription, alors que le plan te disait d'ecrire la pre-inscription d'abord. Si tu avais
   suivi le plan, tu aurais pre-inscrit un seuil sur une marge que tu croyais large, lance 2 h
   d'entrainement, et decouvert ensuite que la marge valait 2 %. **Nomme cette lecon** : quand
   une phase repose sur une marge supposee, la marge se mesure avant de se pre-inscrire.

**Pas de pre-inscription. Pas de run. Pas de code neuf.** L'instrument que tu as ecrit,
`mesure/phase4.py` et ses 11 tests, reste : il sert au constat et il servira a l'audit.

---

## 4. Deux choses a corriger avant de clore

**Le releve de la soiree porte une correction en cours de route** — a 307 k nœuds tu as conclu
a +0,005 de marge et tu l'as annonce, avant de mesurer +0,02 sur une population quatre fois
plus grande. **Tu l'as ecrit a l'endroit ou tu t'es trompe, et c'est bien.** Verifie seulement
qu'aucune phrase du document ne cite encore le +0,005 sans dire sur quelle population il avait
ete lu.

**Les deux relevés de mutations valides** doivent toujours etre cote a cote sous des noms
distincts. Je te l'avais demande, je ne l'ai pas revu passer. Si c'est fait, dis-le ; sinon,
fais-le maintenant, c'est une minute.

---

## 5. Apres

Quand l'entree de journal est ecrite, poussee, et la suite verte : **arret**. La conversation
n° 9 — l'audit croise de la phase 4 — sera ouverte, et son travail sera de refaire ce plafond
**sans lire une ligne de ton `mesure/phase4.py`**. C'est le seul moyen qu'un resultat qui
**ferme une direction** merite la confiance qu'on va lui accorder.

Ne prepare rien pour elle. N'anticipe pas ses questions. Ecris le constat et arrete-toi.
