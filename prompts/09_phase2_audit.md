# Prompt d'audit — phase 2, mesurer le jeu avant d'y jouer

**À coller dans une conversation NEUVE, distincte de celle qui a mesuré.**
Ne jamais réutiliser la conversation de construction.

Écrit sur le modèle de [07_phase1_audit.md](07_phase1_audit.md), adapté à une phase qui
produit à la fois des **chiffres** et un **agent** — le greedy, qui devient la référence de
toutes les phases suivantes.

---

```
CONTEXTE

Une autre conversation vient de mesurer le terrain du jeu Courtisans avant tout
entrainement : avantage de siege, variance des scores, winrate du greedy, et
frequence des sept comportements B1 a B7 chez le greedy. Tu es l'auditeur. Tu n'as
pas participe a cette mesure et tu ne verras pas son raisonnement — c'est
volontaire : son raisonnement t'ancrerait sur ses angles morts.

Ce projet a un historique precis, et il est presque entierement fait d'erreurs de
mesure.

  - Un plafond de performance a pilote trois mois de travail. Il etait calcule par
    une metrique qui faisait jouer une politique uniforme sur 35 % du jeu. Le
    chiffre existait, il etait reproductible, et il ne mesurait pas ce qu'on
    croyait.
  - Cinq briques d'entrainement ont ete validees sur des instances qui violaient
    deux regles du jeu.
  - L'audit de la phase 0, sur du code, a trouve neuf defauts en trois tours, dont
    deux qui vivaient dans du code affiche a 100 % de couverture.
  - L'audit de la phase 1 a rejete une mesure sur UN chiffre : « 0 sur 1 000
    retournements invisibles des trois joueurs ». Le nombre etait juste et
    reproductible au bit pres. Il etait faux quand meme, parce que le calcul
    agregeait quatre familles en un booleen de partie avant de comparer : la phrase
    parlait de retournements, le calcul parlait de parties. Le vrai chiffre est une
    partie sur treize a dix-huit.

CE QUI REND CETTE PHASE PLUS DANGEREUSE QUE LA PRECEDENTE

Le protocole annonce que la phase 2 « ne peut pas echouer : elle produit des faits ».
C'est vrai de son go/no-go et faux de tout le reste. Ces quatre mesures sont des
LIGNES DE BASE : toutes les phases suivantes les citeront sans les rejouer. Une ligne
de base fausse ne se voit jamais — elle rend simplement tous les progres ulterieurs
incomparables, et personne ne saura pourquoi. C'est exactement le mode de defaut qui a
coute trois mois a ce projet.

Deux consequences pour toi.

  - Un chiffre juste mais mal enonce est un defaut BLOQUANT, comme en phase 1. Le
    critere n'est pas « le nombre se recalcule », c'est « la phrase decrit le calcul ».
  - Le greedy n'est pas un instrument, c'est un AGENT. S'il lit `vue_privilegiee()`,
    il connait les Espions adverses et son winrate est gonfle — et ce winrate fixera
    l'echelle de toutes les phases suivantes. C'est ta cible numero un.

CE QUE TU AUDITES

Quatre mesures, un agent, et sept definitions.

  M1  avantage de siege, 10 000 parties appariees, trois agents aleatoires
  M2  variance du score final entre parties
  M3  winrate du greedy contre l'aleatoire
  M4  frequence de chacun des sept comportements B1 a B7 chez le greedy
  Le greedy lui-meme, reecrit contre `courtisans/` pour cette phase
  Sept definitions operationnelles de B1 a B7, qui n'existaient pas avant

Perimetre : ce que le constructeur a ajoute. `courtisans/` est audite deux fois et hors
sujet — si tu y trouves un defaut, c'est un resultat, mais signale-le a part.

TON POINT DE DEPART

Le travail que tu audites est sur la branche `claude/courtisans-phase-2-baseline-559e17`,
dont la tete est `02ae24b`. Le moteur de reference est `moteur-conforme`, tete `19f99f2`.

Verifie ta base AVANT toute chose : `git merge-base --is-ancestor 68a5c16 HEAD` doit
reussir. Les quatre agents precedents ont tous demarre sur un worktree branche sur
`main`, ou le paquet `courtisans/` n'existe pas. Si ta base est fausse, tu auditeras du
vide sans le savoir.

Sur ce depot, `uv` exige `UV_LINK_MODE=copy` : OneDrive refuse les liens durs.

DOCUMENTS A LIRE, DANS CET ORDRE

  1. documentations/01_regles.md                 — paragraphes 2.2, 2.6, 5, 7.1 et 7.2
  2. documentations/05_protocole_experimental.md — paragraphes 1, 2 et 3, phase 2
  3. documentations/06_journal_decisions.md      — les entrees du 17/08 et du 18/08
  4. documentations/07_protocole_audit_croise.md — tes controles A1 a A7
  5. documentations/08_modele_compte_rendu.md    — paragraphes 3 et 4, ton format

  Ne lis PAS le code du constructeur avant d'avoir ecrit tes propres definitions de
  B1 a B7 et ton propre greedy. C'est la seule facon de savoir si sa lecture des
  regles est la bonne : deux lectures independantes du meme texte, comparees apres.

ORDRE DE TRAVAIL — NON NEGOCIABLE

  Etape 0. Les documents. Puis DIX LIGNES : ce que tu comptes verifier, tes sept
           definitions de B1 a B7 en une ligne chacune, ECRITES AVANT DE LIRE LES
           SIENNES, et tes controles hostiles prevus. Aucun code avant ma reponse.

  Etape 1. Reecris ce qui prononce un verdict, sans regarder son code : ton propre
           greedy depuis le paragraphe 7.1 des regles, tes sept compteurs de
           comportement, et ton propre calcul d'intervalle de confiance. Une
           reimplementation independante est le seul controle qu'une erreur de lecture
           partagee ne passe pas.

  Etape 2. Ecris tes controles hostiles comme des tests executables. Au minimum :
           - des parties construites a la main, resultat calcule de tete, avec des
             controles NEGATIFS — une configuration ou un comportement doit valoir
             EXACTEMENT zero, pas « peu » ;
           - une instance sans Assassin : la frequence de B4 doit valoir exactement 0 ;
           - une position ou le greedy DOIT refuser de tuer, et une ou il doit tuer ;
           - la preuve que son greedy ne lit pas la vue de dieu. Ne te contente pas de
             grep : construis deux etats qui ne different QUE par l'identite d'un
             Espion adverse et verifie que son greedy joue le meme coup. S'il joue
             differemment, il triche, et M3 comme M4 sont a refaire.

  Etape 3. Rejoue ses chiffres toi-meme, avec ton code. Compare. Un desaccord est un
           resultat ; une concordance aussi, et elle vaut d'etre dite.

  Etape 4. Reintroduis dans SON code la faute exacte que tu soupconnes, une par une, et
           verifie que ses tests tombent. Une correction non tenue par un test se
           defait au commit suivant.

  Etape 5. Verdict, au format du paragraphe 3 de 08_modele_compte_rendu.md.

LES QUATRE QUESTIONS QUE TU POSES A CHAQUE CHIFFRE

  1. La phrase decrit-elle le calcul ? Quel est le sujet grammatical du taux, et
     est-ce l'unite reellement comptee ? C'est le defaut qui a rejete la phase 1.
  2. Le chiffre porte-t-il son echantillon — seeds, politique, grain, denominateur ?
     L'auditeur de la phase 1 a lui-meme commis cette faute, deux fois.
  3. Le seuil discrimine-t-il ? A partir de quelle taille d'echantillon est-il
     franchi ? En phase 1, quatre criteres etaient satisfaits des 1, 3, 3 et 12
     parties sur 1 000 : ils constataient, aucun ne testait. Le seuil de 38 % de M1 a
     le meme probleme, a 9,9 erreurs-type de l'attendu.
     Cherche en particulier, pour chacun des sept, le cas ou l'ecart DETECTABLE au
     budget de la phase 3 depasse le taux MESURE lui-meme. Alors aucun agent ne peut
     etre separe du greedy par le bas -- pas meme un agent a zero, qui n'est distant
     que du taux mesure. Un compteur aveugle d'un seul cote ne teste rien de ce
     cote-la, et rien dans le chiffre publie ne le montre.
  4. Un zero ou un cent pour cent a-t-il ete confronte a un cas construit a la main ?
     Un absolu est ce qu'un lecteur retient, et c'est ce qui a ete faux en phase 1.

TROIS PIEGES SPECIFIQUES A CETTE PHASE

  a) B1 ET B3 MESURES SUR LE GREEDY NE MESURENT PAS UNE PLANIFICATION. Le greedy a un
     horizon d'un tour par construction : il ne planifie rien. Ce qu'un compteur voit
     chez lui est la frequence a laquelle le MOTIF apparait par coincidence. C'est la
     bonne ligne de base, mais si son rapport ne le dit pas, il produit une phrase
     fausse au sens du controle 1 ci-dessus. Verifie qu'il l'ecrit.

  b) LE PLAFOND DE B1. La phase 1 a mesure que 7,40 % des parties contiennent une
     perte d'acquis de famille qu'AUCUN des trois joueurs ne pouvait voir. Aucune
     politique ne peut planifier ces retournements-la. Une ligne de base de B1 qui
     ignore ce plafond sera comparee a tort aux agents des phases suivantes.

  c) UNE CONCURRENTE ANNONCEE PUIS NON MESUREE. Sa pre-inscription annonce, pour chaque
     comportement, des definitions concurrentes et le sens attendu de leur ecart. Une
     concurrente sans chiffre ne remplit pas son office : elle existe precisement pour
     chiffrer ce que le choix de definition coute. Verifie deux choses. D'abord
     qu'aucune n'a disparu de la livraison sans raison ecrite. Ensuite, quand une
     raison est donnee, qu'elle ne depende pas des chiffres deja vus -- une concurrente
     abandonnee APRES avoir lu les autres resultats est exactement la liberte que la
     pre-inscription existe pour supprimer, et elle se defend avec les memes mots
     qu'un abandon legitime.
     Symetriquement : un sens annonce d'avance puis INFIRME par la mesure est un
     resultat, pas un accident. Il doit etre ecrit comme tel, avec la raison pour
     laquelle le raisonnement d'avance etait faux. Un rapport ou les douze directions
     annoncees tiennent toutes les douze merite un controle a lui seul.

CE QUE TU NE FAIS PAS

  - Tu ne corriges rien. Tu constates, tu prouves, tu rends un verdict. Le
    constructeur corrige.
  - Tu ne modifies ni `courtisans/`, ni `mesure/`, ni `documentations/`.
  - Tu n'entraines aucun reseau. Ni toi ni lui : ce n'est pas cette phase.
  - Tu n'ouvres pas de front nouveau lors d'une RE-verification : a l'etape 6 du
    cycle, tu ne verifies que les defauts que tu as listes. Une observation hors liste
    se signale, etiquetee comme telle, sans compter dans le verdict.

TON VERDICT

  ACCEPTE                — les sept controles sont concluants
  ACCEPTE SOUS RESERVE   — defauts mineurs, listes, qui ne changent aucune conclusion
  REJETE                 — au moins un defaut bloquant

Est bloquant : une mesure dont la phrase ne decrit pas le calcul ; un greedy qui voit
plus que son info-set ; une definition de comportement qui rend un chiffre non
comparable a ce qu'il pretend comparer ; un chiffre non reconstructible.

Un audit qui ne trouve rien doit expliquer POURQUOI il n'a rien trouve, et dire ce
qu'il a cherche sans le trouver. Trois cibles saines nommees valent mieux qu'un
verdict nu.

COMMENCE PAR

  Les documents, puis tes dix lignes, dont tes sept definitions ecrites AVANT de lire
  les siennes. Pas de code avant ma reponse.
```

---

## Notes pour l'humain qui lance ce prompt

**Ce qu'il faut donner :** l'accès au dépôt, la branche du constructeur, et ce bloc. **Pas**
le compte rendu du constructeur avant l'étape 0 — l'auditeur doit écrire ses sept définitions
de B1 à B7 sans les avoir vues. C'est ce qui a produit le meilleur résultat de la phase 1 :
deux lectures indépendantes du §2.2 tombant sur la même définition, ce qui a rendu le chiffre
solide bien plus que le chiffre lui-même.

**Vérifie sa base.** Comme les trois agents précédents, il démarrera peut-être sur un worktree
branché sur `main`, où `courtisans/` n'existe pas. `git log --oneline -1` doit montrer
`68a5c16` ou un descendant.

**Ce qu'il te demandera d'arbitrer :** probablement le seuil de M1, et le choix entre sa
définition d'un comportement et celle du constructeur quand elles divergent. Tranche en
citant le §7.2 des règles, pas en choisissant la plus stricte — c'est l'erreur qu'a faite
l'agent de la phase 1 sur « retournement », et le §2.2 tranchait déjà.

**Le contrôle qui compte le plus.** Deux états qui ne diffèrent que par l'identité d'un Espion
adverse doivent produire le même coup du greedy. C'est la seule preuve qu'il ne triche pas, et
c'est plus fort qu'une relecture de son code.
