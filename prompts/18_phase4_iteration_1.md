# Prompt de construction — phase 4, itération 1 : la tête de valeur

**À coller dans une conversation NEUVE — c'est la conversation n° 8.**

L'audit se fait dans une **autre** conversation, la n° 9, avec un prompt qui sera donné quand le
compte rendu existera.

---

```
CONTEXTE

Tu ouvres la phase 4 du projet Courtisans, premiere iteration. Les phases 0 a 3 sont
closes, chacune auditee par une conversation independante. 1 172 tests verts, 0 rouge.

    entrainement-3j : familles=4, les 5 roles, exemplaires=2, joueurs=3
                      4 x 5 x 2 = 40 cartes ; 40 // 9 = 4 tours par joueur

CE QUE LA PHASE 3 A ETABLI, ET QUE TU NE REFAIS PAS

  L'AGENT EST BATTU PAR LE GREEDY. Gain moyen -0,1643 contre deux greedys, sieges
  permutes, IC 99 % [-0,1824 ; -0,1462] sur 6 000 parties. Part fractionnee 22,38 %
  contre 33,3333 % au neutre exact. Confirme par TROIS implementations independantes.

  ET IL APPREND. Ecart apparie entre son premier et son dernier checkpoint : +12,80 pt,
  IC 99 % [+8,33 ; +17,40], avec Bonferroni pour 8 regards.

  CE QUI N'EST PAS ETABLI, et ne doit pas etre reecrit : qu'il apprenait ENCORE a la fin.
  Les huit intervalles se recouvrent 7 fois sur 7. Une remesure sur les memes donnes,
  autre alea de tirage, porte deux inversions et un dernier pas negatif.

  DONC LE BUDGET N'EST PAS ECARTE, IL EST NON DESIGNE. Ce n'est pas la meme chose. Ne
  l'ecris pas comme si la phase 3 avait montre que rallonger ne sert a rien : elle a
  montre que rien ne montre que ca servirait.

CE QUE TU VIENS FAIRE, ET POURQUOI C'EST CELUI-LA

L'agent a une tete de politique et une TETE DE VALEUR. La seconde estime, depuis un
info-set, le gain que la partie va rendre. C'est elle qui fournit la ligne de base de
l'avantage de PPO : sans elle, le gradient est domine par le bruit du retour.

ELLE N'APPREND PAS. MESURE en phase 3, par le pilote puis par l'auditeur :

  perte_valeur au premier checkpoint : 0,3923      au huitieme : 0,3908
  variance des retours, hors plage d'entrainement (seeds 5000000+) : 0,4190
  MSE reelle du critique de `models/phase3/final.pt` sur ces memes noeuds : 0,3809
  R2 = 1 - MSE/Var = +0,093
  (dans la plage d'entrainement, seeds 700000+ : 0,4320 / 0,3747 / +0,113)

Un critique qui predirait la constante zero ferait 0,4190. Le sien fait 0,3809. Il
n'explique donc **rien de plus que la moyenne, ou presque**, et il ne progresse pas d'une
seconde en deux heures.

ET CE N'EST PAS LA FAUTE DU JEU. C'est le point qui rend cette iteration possible.
L'auditeur a mesure le PLANCHER -- la part de variance qu'aucun critique ne peut
predire -- en rejouant le meme etat 24 fois sous la politique de l'agent, sur 400 etats :

  E[Var(R | etat complet)] = 0,1815     part irreductible : 43,3 %
  => R2 ATTEIGNABLE : 0,57

C'est une BORNE, pas une cible : elle est calculee sur l'etat COMPLET, donc sur plus
qu'un info-set. Un critique parfait voyant seulement l'info-set ferait moins bien.

Et le profil par profondeur tranche definitivement :

  profondeur            0      4      8     12     16     18     19
  plancher Var(R|s)   0,32   0,32   0,26   0,21   0,025  0,035  0,0075
  MSE du critique     0,36   0,41   0,40   0,40   0,31   0,27   0,30

A l'avant-derniere decision la partie est PRESQUE ECRITE -- 0,0075 de variance
irreductible -- et le critique y fait encore 0,30, soit quarante fois l'erreur qu'un
critique correct y ferait. **Un jeu impredictible ne donnerait pas ce profil.**

LE PIEGE DE CETTE ITERATION, ET C'EST LE PLUS IMPORTANT DE CE PROMPT

TU PEUX FAIRE MONTER LE R2 SANS QUE L'AGENT JOUE MIEUX. Un critique qui colle mieux aux
retours ne rend pas mecaniquement PPO meilleur.

Ce projet a deja perdu trois mois sur exactement cette faute : une metrique
d'exploitabilite qui descendait pendant qu'un tiers du jeu se jouait au hasard. Personne
ne demandait a ce chiffre ce qu'il mesurait.

CONSEQUENCE, NON NEGOCIABLE : tu pre-inscris DEUX seuils, et le second seul decide.

  SEUIL INTERMEDIAIRE, diagnostique. Le R2 du critique, mesure HORS de la plage
  d'entrainement, sur la meme methode que celle de la phase 3 -- MSE / variance des
  retours sur les noeuds. Il dit si tu as repare ce que tu es venu reparer.

  SEUIL DECISIF, le seul qui tranche l'iteration. Gain moyen du nouvel agent contre
  DEUX COPIES DE L'AGENT DE LA PHASE 3, sieges permutes, borne basse de l'IC 99 %
  bootstrap par donne STRICTEMENT POSITIVE. C'est le go/no-go d'iteration du protocole.

  ET TU RAPPORTES AUSSI, sans que ce soit un seuil : le gain moyen contre DEUX GREEDYS,
  meme forme, pour situer l'agent sur l'echelle de la phase 3.

UN R2 QUI MONTE ET UN GAIN QUI NE BOUGE PAS EST UN RESULTAT PUBLIABLE, ET IL EST
INTERESSANT : il etablirait que la qualite du critique n'est pas ce qui limite cet agent.
Ne le presente pas comme un echec, et surtout ne le rehabille pas.

UNE VARIABLE A LA FOIS -- CE QUE CA INTERDIT ICI

Tu changes LA TETE DE VALEUR. Architecture, cibles, optimisation, ponderation de sa
perte : c'est un seul levier, celui-la.

TU NE TOUCHES PAS, dans la meme iteration : le budget d'entrainement, la taille du reseau
de politique, la composition du pool, gamma, lambda, le nombre de checkpoints, la
composition de mesure. Si tu crois qu'un de ces leviers doit bouger, REMONTE-LE, ne le
tranche pas.

LA TETE AUXILIAIRE EST UNE AUTRE ITERATION. Le paragraphe 7.1 de la pre-inscription de la
phase 3 a ecrit d'avance une tete de regression sur l'ecart de score final, entrainee par
une perte separee qui n'entre jamais dans le retour ni dans l'avantage. C'est une bonne
idee et elle reste reservee pour l'iteration 2. Elle est DISTINCTE de reparer le critique
existant : ne fais pas les deux, on ne saurait plus laquelle a compte.

LE TRAVAIL A FAIRE AVANT TOUTE MESURE, ET IL PASSE EN PREMIER

  ETAPE 0. ETENDRE LE PERIMETRE DES MUTATIONS. Aujourd'hui `outillage/mutation.py` porte
  20 motifs qui ciblent tous `courtisans/`. « 20 mutations, toutes detectees » ne dit donc
  RIEN des ~2 500 lignes de `agents/` et `mesure/` -- c'est-a-dire du code qui entraine et
  du code qui mesure.

  Le paragraphe 0.3 du protocole a ete elargi le 21/08 : `agents/greedy.py` reste EXEMPT,
  c'est l'etalon et c'est le seul invariant que la regle protegeait. Tout le reste de
  `agents/` et tout `mesure/` entrent dans le perimetre.

  La raison se lit dans l'histoire du projet : le defaut le plus instructif de la phase 2
  -- un facteur trois indu dans six budgets, qui a survecu a DEUX verifications reussies
  -- vivait dans le GENERATEUR, pas dans le moteur.

  UNE MUTATION QUI SURVIT EST UN RESULTAT, PAS UN ECHEC. Elle nomme un trou de la suite de
  tests. Tu les rapportes toutes, tu ne les caches pas, et tu ne fabriques pas un test
  a la hate pour faire tomber un survivant sans dire ce qu'il t'a appris.

  Rends-moi le compte avant de continuer.

  ETAPE 0 BIS. LES TROIS RESERVES DE LA PHASE 3, traitees et dites separement :
    1. Un intitule « 99 % » qui couvre deux risques. Les deux bornes exactes de
       Clopper-Pearson sont UNILATERALES -- 0,2338 % pour 0/1967, 0,0443 % pour 0/10382 --
       quand tout le reste du rapport publie des intervalles BILATERAUX a 99 %. Les
       bilaterales vaudraient 0,2690 % et 0,0510 %. La conclusion ne bouge pas, LE LIBELLE
       EST FAUX, et `mesure/resultats/phase3.md` ecrit QUATRE FOIS « borne haute a 99 % »
       sans qualificatif.
    2. Le rendu du verdict exact n'est ecrit que pour UN des QUATRE cas que la regle
       couvre : un zero cote agent est annonce « de la ligne de base », un cent est
       annonce « le zero », deux zeros font parler d'un intervalle qui n'existe pas.
       Aucun n'est atteignable sur les donnees de la phase 3 -- c'est latent, pas faux.
    3. La parade des intitules ne couvre qu'une ecriture d'appel : `from agents import
       campagne as X` puis `X.intitule_du_garde_fou()` passe au travers, et c'est
       l'ecriture du depot.

ORDRE DE TRAVAIL -- NON NEGOCIABLE

  Etape 0.  Le perimetre des mutations. Compte rendu avant de continuer.
  Etape 0b. Les trois reserves.
  Etape 1.  DOUZE LIGNES MAXIMUM : ce que tu as compris, ce que tu comptes changer dans la
            tete de valeur et pourquoi, et ce qui te semble mal specifie. AUCUN CODE AVANT
            MA REPONSE.
  Etape 2.  HYPOTHESE ET INSTRUMENT, ecrits et COMMITES avant tout entrainement. Ils
            contiennent : ton seuil intermediaire chiffre sur le R2, ton seuil decisif,
            sigma et rho MESURES sur ta composition -- un agent contre deux copies de
            l'agent de la phase 3 --, le nombre de parties qui en decoule, et l'ecart
            detectable a ce budget. Le modele est `mesure/phase3_hypothese_et_instrument.md`.
  Etape 3.  Les tests AVANT d'entrainer.
  Etape 4.  Entrainement. Plafond 2 h par run, checkpoint toutes les 15 minutes.
  Etape 5.  Mesure. Sieges permutes. Compositions nommees.
  Etape 6.  AUTO-AUDIT, ecrit AVANT de voir le resultat.
  Etape 7.  RELIS CE QUE TU AS ECRIT EN DERNIER, ET AUSSI L'AVANT-DERNIER. Six fois dans
            ce projet le defaut neuf est ne dans la correction du precedent -- et au tour 2
            de la phase 3, deux des trois defauts neufs n'etaient PAS dans la relecture
            finale mais dans le commit d'avant.
  Etape 8.  Compte rendu, paragraphe 2 de `08_modele_compte_rendu.md`. MESURE / DEDUIT /
            SUPPOSE sur chaque affirmation.

CE QUE TU DOIS SAVOIR DU GARDE-FOU, PARCE QU'IL T'APPARTIENT MAINTENANT

Il a porte CINQ defauts successifs en phase 3, dont deux du pilote, et quatre sont nes
dans le texte qui corrigeait le precedent. Sa forme actuelle :

  portee TROIS checkpoints ; declenchement si l'ecart apparie entre le checkpoint k et le
  checkpoint k-3 n'est pas un PROGRES ETABLI -- borne basse de son IC strictement
  superieure a zero. Un ecart etabli NEGATIF declenche : c'est un effondrement.

La regle generale qui manquait aux cinq versions : UN GARDE-FOU NE PEUT CHERCHER QU'UN
PROGRES PLUS GRAND QUE CE QUE SON PROPRE BUDGET LUI PERMET DE DETECTER, et la barre se lit
sur la grandeur testee -- ici la demi-largeur de l'IC de l'ECART APPARIE, 3,56 a 4,06 pt
en phase 3, et non l'ecart detectable iid d'un NIVEAU, 2,75 pt.

Recalcule ta portee minimale sur TON budget. Ne transcris pas 3.

LES CHIFFRES DE LA PHASE 3 QUE TU CITERAS, AVEC LEUR POPULATION

  1 agent PPO contre 2 greedys, 6 000 parties, seeds 60000-61999 :
      gain -0,1643  IC [-0,1824 ; -0,1462]  part fractionnee 22,38 %  sigma 0,5710
      rho -0,0565   effet de plan 0,8870    ecart detectable +0,0237
  1 greedy contre 2 greedys (l'hypothese nulle) : sigma 0,6494  rho -0,1400
  1 greedy contre 2 aleatoires : part fractionnee 86,52 %, gain +0,7978 -- MOYENNE SUR
      LES TROIS SIEGES, agregee sur 10 002 parties, ne se compare qu'a une mesure agregee
      de la meme facon.
  Niveaux nuls : gain 0,0000 exact ; part fractionnee 33,3333 % ; la part STRICTE n'est
      jamais un seuil, sa valeur nulle depend de la frequence des ex aequo.
  Comportements, ligne de base « trois greedys, un seul siege compte » : B1-motif 42,48 %
      contre 45,83 %, B4-brut 31,93 % contre 15,93 %, B4-contre-nature 35,87 % contre
      0,00 % (0/1967).

CE QUE TU NE FAIS PAS

  - Tu ne modifies pas `courtisans/`. Il est audite quatre fois. Un defaut suppose se
    remonte, il ne se corrige pas.
  - TU NE TOUCHES PAS A `agents/greedy.py`. C'est l'etalon de toutes les phases, il ne
    porte aucune mutation, et un agent de reference se documente au lieu de se corriger.
  - Tu ne changes aucun chiffre publie de la phase 3, ni aucun seuil pour faire passer une
    mesure.
  - Tu ne lis jamais `vue_privilegiee()` depuis un agent. `agents/perception.py` est la
    frontiere d'aveuglement et ta tete de valeur la respecte : elle voit un info-set, pas
    l'etat. Si tu crois avoir besoin de plus, REMONTE-LE -- un critique qui voit l'etat
    complet n'est pas utilisable a l'inference, et le plancher de 0,57 est calcule sur
    l'etat complet precisement pour cette raison.
  - Tu ne fais pas l'iteration 2. Pas de tete auxiliaire, pas de PSRO, pas de ligue.

CE QUE TU DOIS ME DONNER A LA FIN

  1. Le perimetre des mutations etendu, et le compte -- survivants nommes s'il y en a.
  2. Les trois reserves de la phase 3, traitees et dites separement.
  3. L'hypothese et l'instrument, commites AVANT l'entrainement.
  4. Le R2 du critique, avant et apres, mesure HORS plage d'entrainement, avec son
     echantillon.
  5. Le gain moyen contre deux copies de l'agent de la phase 3, avec son IC 99 %.
  6. Le gain moyen contre deux greedys, avec son IC 99 %.
  7. La courbe d'apprentissage avec L'IC DE SES ECARTS, pas seulement de ses niveaux.
  8. Ce que ta mesure N'ETABLIT PAS.
  9. Une proposition d'entree de journal.

CONTROLE DE BASE, A FAIRE EN PREMIER

    git merge-base --is-ancestor 9eb61e0 HEAD

Six agents sur six ont demarre au mauvais endroit jusqu'ici. Et pousse ta branche des le
premier commit : deux fois deja, un verdict entier est reste sans upstream.

Note : uv exige UV_LINK_MODE=copy sur ce depot (OneDrive, os error 396).

MACHINE

PC fixe, Ryzen 9600X, RTX 4060, 64 Go. AUCUNE DUREE NE SE CITE SUR UN SEUL CHRONOMETRAGE :
trois passes minimum, avec l'etendue.

COMMENCE PAR

  Le controle de base, puis l'etape 0. Le compte des mutations avant tout le reste.
```

---

## Notes pour l'humain qui lance ce prompt

**Destinataire :** conversation NEUVE, **n° 8 — Construction de la phase 4**.

**Ce qu'il rend en premier :** le compte des mutations sur `agents/` et `mesure/`. Des mutations
qui survivent sont attendues et normales — c'est du code jamais muté. Ne le laisse pas les cacher.

**Le piège de cette phase**, et c'est celui qui a coûté trois mois au projet : il peut faire
monter le R² du critique sans que l'agent joue mieux. Le seuil qui décide est le jeu, pas le R².
Le prompt le lui dit trois fois.

**Ensuite :** l'audit, conversation n° 9, quand son compte rendu existera.
