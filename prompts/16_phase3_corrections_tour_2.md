# Corrections du tour 2 — phase 3

**À coller dans la conversation n° 7.** Elle est rouverte, et elle reste dans le rôle qu'elle
occupe depuis le tour 1 des corrections : **constructeur des corrections**.

Verdict de la conversation n° 6, qui les a auditées : **REJETÉ**, deux bloquants neufs, un
majeur neuf, quatre mineurs neufs.

---

```
L'AUDIT CROISE DE TES CORRECTIONS A RENDU : REJETE.

Douze des quatorze defauts sont LEVES, et bien leves. Le verdict ne porte pas sur ce qui
manque, il porte sur CE QUE TES CORRECTIONS ONT INTRODUIT. Trois defauts neufs, dont deux
bloquants, et deux d'entre eux sont dans `c0b073b`, pas dans ta relecture finale : tu as
cherche au bon endroit, pas assez loin.

Pour la sixieme fois dans ce projet, le defaut neuf est ne dans la correction du precedent.

CE QUE LE PILOTE A VERIFIE LUI-MEME AVANT DE TE TRANSMETTRE

J'ai lu les deux bloquants dans le depot, pas dans le rapport d'audit. Les deux sont exacts.

  - `mesure/resultats/phase3.md` publie, dans son tableau :
        `B4-contre-nature`   35.87 % (1368/3814)  contre  0.00 % (0/1967)   -> non separable
        `B4-meurtre-couteux`  3.66 % (298/8131)   contre  0.00 % (0/10382)  -> non separable
    avec un tiret a la place du detectable. Et le MEME rapport argumente une demi-page sur ce
    que l'ecart 35,87 % / 0,00 % etablit.

  - `tests/mesure/test_phase3_corrections.py:167-168` ecrit `(1, 1967)` et `(1, 10382)`. Les
    comptes reels sont `(0, 1967)` et `(0, 10382)`.

DEFAUT A -- BLOQUANT. « AUCUNE LIGNE NE CHANGE DE STATUT » EST FAUX, ET SUR LES DEUX LIGNES
DU DEFAUT 4.

`ecart_detectable_deux_echantillons` rend `None` sur un taux degenere. Les deux lignes qui
portent un zero absolu passent donc de SEPARABLE -- 3,75 % et 1,01 % au tour 1 -- a
« non separable a ce budget », sans detectable et sans nombre de parties.

L'etiquette n'est pas seulement absente, ELLE EST FAUSSE. La borne haute exacte a 99 % de
ces zeros vaut 0,2338 % et 0,0443 %, et l'ecart les depasse largement. Ta propre docstring
prescrit qu'un zero observe se traite par sa borne exacte : aucune borne exacte n'est
calculee nulle part dans le depot.

Et ton rapport se contredit dans le meme document : son texte etablit un ecart que son
tableau declare non separable.

CE QUE TU CORRIGES. Le zero se traite par sa borne exacte, comme ta docstring le dit deja.
La parade est une garde qui LEVE, ou un statut distinct : `None` ne doit pas pouvoir
s'imprimer comme « non separable », qui est une conclusion. Et le rapport doit dire la meme
chose dans son texte et dans son tableau.

DEFAUT B -- BLOQUANT. LE CAS QUI SOUTIENT CETTE PHRASE MAQUILLE SON ENTREE.

`tests/mesure/test_phase3_corrections.py` porte
`test_aucune_ligne_ne_change_de_STATUT_avec_la_formule_corrigee`, et ce cas ecrit `1` la ou
la mesure dit `0`, sur les deux seules lignes qui changent de statut.

Avec le `1`, les deux redeviennent separables et le cas est vert. LE CAS NOMME « AUCUNE
LIGNE NE CHANGE DE STATUT » ECARTE, EN MODIFIANT SES DONNEES, LES DEUX SEULES LIGNES QUI
CHANGENT DE STATUT.

C'est la meme famille que le test de la phase 2 dont le nom disait « refuse » et le corps
affirmait que l'appel reussissait -- mais ici l'assertion est correcte, c'est l'ENTREE qui
est falsifiee. Un cas dont on choisit les donnees pour qu'il passe ne teste rien.

CE QUE TU CORRIGES. Le cas prend les comptes REELS. S'il tombe, c'est qu'il avait raison de
tomber, et c'est le defaut A qu'il faut corriger, pas le cas.

DEFAUT C -- MAJEUR. LE GARDE-FOU v5 EST AVEUGLE A UN EFFONDREMENT.

`agents/campagne.py:392` teste « l'ecart apparie est-il ETABLI ? ». Un ecart etabli NEGATIF
satisfait la condition. Mesure par l'auditeur : un effondrement de -17,80 pt, IC
[-18,43 ; -17,08], NE DECLENCHE PAS.

C'est exactement le mode de defaillance que l'arbitrage du tour 1 avait escalade en
retirant le greedy et l'aleatoire du pool d'entrainement : l'effondrement de convention en
self-play. Le garde-fou cense le voir ne le voit pas.

Cinquieme defaut du meme garde-fou, ne dans la correction du quatrieme.

CE QUE TU CORRIGES. Le declenchement porte sur un progres ETABLI ET POSITIF -- borne basse
de l'IC de l'ecart strictement superieure a zero. Un ecart etabli negatif doit declencher,
pas rassurer. Et le test qui le tient doit passer un effondrement, pas seulement une
stagnation.

LES QUATRE MINEURS NEUFS

  D. Le verdict de declenchement du rapport est lu dans `j["declenche"]`, champ ecrit par la
     regle RETIREE, pendant que la phrase imprimee decrit la v5. Elles concordent ici, rien
     ne le garantit.
  E. `serie_par_donne` est annotee `tuple[float, ...]` et rend cinq valeurs.
  F. `portee_minimale` n'est appelee qu'avec trois litteraux transcrits de ce run : la parade
     fige un run au lieu de calculer le suivant.
  G. Trois regles a deux sites : le predicat « etabli », la graine du bootstrap apparie, et
     `__import__("random")`.

LA RESERVE DE L'AUDITEUR, A TRAITER AUSSI

Ta parade des intitules ne lit que les `ast.Constant`. L'auditeur a redonne au pool le nom du
garde-fou VIA `intitule_du_garde_fou()` et le cas reste vert. R2 l'attrape toujours, donc il
reste UN filet, pas deux. Dis-le ou couvre le cas.

CE QUI EST LEVE ET NE SE REFAIT PAS

Douze des quatorze. Ne les rouvre pas. L'auditeur a notamment eprouve, et je le confirme :
tes trois parades mordent quand on leur reinjecte leur faute ; le rejeu honnête du
checkpoint 3 rend les 600 valeurs IDENTIQUES BIT A BIT au journal publie, et une
reproduction cassee de 1e-9 leve en nommant le champ -- ton journal a bien ete COMPLETE et
non refait ; sa courbe independante retrouve tes cinq ecarts de portee trois au chiffre
pres, et tes six `parties_requises`.

CE QUI A CHANGE AU PROTOCOLE

Tu avais raison : `documentations/05` citait encore 2,75 pt a un endroit, la grandeur d'un
NIVEAU, quand le code teste un ECART APPARIE dont la barre vaut 3,56 a 4,06 pt. Corrige.
Le protocole et `agents/campagne.py` s'accordent maintenant.

CE QUE TU NE FAIS PAS

  - Tu ne rouvres aucun des douze defauts leves.
  - Tu ne refais aucune campagne, tu ne relances aucun entrainement.
  - Tu ne modifies aucun document de `documentations/`.
  - Tu ne changes aucun des 15 chiffres acquis.

CE QUE TU ME RENDS

  1. A, B, C corriges, chacun avec ce qui l'empeche de se defaire.
  2. D a G, et la reserve sur les intitules.
  3. Le rapport et l'entree de journal remis d'accord avec eux-memes sur les deux zeros.
  4. La suite verte, et le compte.
  5. RELIS EN DERNIER CE QUE TU AS ECRIT EN DERNIER -- et cette fois, regarde aussi ce que tu
     as ecrit AVANT-DERNIER. Deux des trois defauts neufs sont dans `c0b073b`, pas dans ta
     relecture finale.
```

---

## Notes pour l'humain

**Destinataire :** conversation n° 7. Elle reste constructeur des corrections.

**Ensuite :** retour à la conversation n° 6, qui re-vérifie **uniquement** A, B, C, D à G et la
réserve.
