# Prompt de construction — phase 3, le premier agent entraîné

**À coller dans une conversation NEUVE — c'est la conversation n° 6.** Écrit sur le modèle de
[08_phase2_construction.md](08_phase2_construction.md).

L'audit de cette phase se fait dans une **autre** conversation, la n° 7, avec un prompt qui sera
donné quand le compte rendu du constructeur existera.

---

```
CONTEXTE

Tu ouvres la phase 3 du projet Courtisans. Les phases 0, 1 et 2 sont closes, auditees
chacune par une conversation independante qui a reimplemente les mesures depuis le texte
des regles sans reutiliser une ligne du constructeur. 977 tests verts, 0 rouge. Le
moteur est audite, l'instance de travail est validee, et le terrain est mesure. Tu ne
touches a rien de tout ca, sauf a un endroit precis nomme plus bas.

    entrainement-3j : familles=4, les 5 roles, exemplaires=2, joueurs=3
                      4 x 5 x 2 = 40 cartes ; 40 // 9 = 4 tours par joueur
                      36 cartes jouees ; 4 jamais piochees

Ce projet a un historique precis, et tu dois le connaitre parce qu'il decrit exactement
la facon dont ton travail peut echouer sans que personne ne s'en apercoive.

Cinq briques d'entrainement ont ete validees sur des instances qui violaient les regles
du jeu. Le plafond de performance qui a pilote trois mois de travail etait mesure par une
metrique qui jouait au hasard sur un tiers du jeu. Personne ne l'a vu, parce que personne
ne demandait a un chiffre ce qu'il mesurait.

La phase 1 a produit une faute plus fine : « 0 sur 1 000 retournements invisibles des
trois joueurs ». Le nombre etait juste, reproductible au bit pres, et faux quand meme --
le calcul agregeait quatre familles avant de comparer, si bien que la phrase parlait de
retournements quand le calcul parlait de parties. Le vrai chiffre est une partie sur
treize a dix-huit.

La phase 2 a produit la meme faute CINQ FOIS EN UNE SEULE PHASE : un chiffre exact sur
une population que sa phrase ne nomme pas. Chez le constructeur, chez l'auditeur, chez le
pilote, et jusque dans l'entree de journal qui nommait la faute quatre fois. Le defaut le
plus instructif etait un facteur trois indu dans six budgets ; il avait SURVECU A DEUX
VERIFICATIONS REUSSIES, parce que la formule de controle recevait le meme denominateur
errone que le generateur.

L'enseignement qui te concerne le plus : REPRODUIRE UN NOMBRE NE LE VALIDE PAS. Il faut
reproduire son UNITE d'abord, et le nombre ensuite. Deux implementations qui partagent la
meme hypothese fausse concordent parfaitement.

CE QU'EST LA PHASE 3

Le paragraphe 3 de documentations/05_protocole_experimental.md, phase 3 : un agent
entraine qui bat le greedy. Self-play avec un pool d'adversaires figes -- le choix
d'algorithme est deja tranche au protocole et tu ne le rouvres pas.

Battre le greedy est un PLANCHER, pas un objectif. Le greedy est aujourd'hui l'agent le
plus fort mesure du projet.

LE SEUIL A CHANGE LE 20/08, ET C'EST LE POINT LE PLUS IMPORTANT DE CE PROMPT

Tu vas lire, dans des documents historiques que je ne reecris pas -- les prompts des
phases precedentes, de vieilles entrees -- un seuil qui dit « > 55 % contre le greedy sur
1 000 parties appariees », avec une bande 45-55 % et un plancher a 45 %.

CE SEUIL EST MORT. Ne le recolle pas. Ces trois nombres sont des intuitions de jeu a DEUX
joueurs. A trois joueurs, la part de victoire fractionnee vaut 33,33 % au neutre : un
agent a 45 % n'est pas « sous le hasard », il est tres au-dessus. Le texte ne nommait par
ailleurs ni la composition de la population, ni l'unite du taux.

Le seuil en vigueur est au paragraphe 3 du protocole, phase 3, et le voici :

  COMPOSITION MESUREE. Un agent contre DEUX greedys, sieges permutes systematiquement.
  Un agent contre deux aleatoires est mesure en parallele, pour le garde-fou seul.

  JUGE. Le GAIN MOYEN, dont la valeur nulle est exactement 0,0000 et ne depend d'aucune
  frequence d'ex aequo. La part de victoire fractionnee est rapportee a cote, comparee a
  33,33 %. La part de victoire STRICTE n'est pas un seuil : sa valeur nulle est
  (1 - P(trois ex aequo)) / 3, elle depend de la frequence des ex aequo.

  SEUIL. L'agent bat le greedy si son gain moyen contre deux greedys est strictement
  positif, BORNE BASSE D'UN INTERVALLE DE CONFIANCE A 99 % COMPRISE, bootstrap par donne
  comme en phase 2.

  GARDE-FOU. Si apres 2 h d'entrainement l'agent, mis a la place du greedy dans la
  composition « un contre deux aleatoires », n'a pas depasse la part de victoire
  fractionnee du greedy dans cette meme composition -- 86,52 % --, on arrete. Ce 86,52 %
  est une MOYENNE SUR LES TROIS SIEGES, agregee sur 10 002 parties, et il ne se compare
  qu'a une mesure agregee de la meme facon.

La formule du gain est au paragraphe 5.2 des regles. A trois joueurs : vainqueur unique
+1 / -0,5 / -0,5 ; deux ex aequo +0,25 / +0,25 / -0,5 ; trois ex aequo 0 / 0 / 0. Somme
nulle dans tous les cas.

CINQ OBSTACLES QUE LE PROTOCOLE NE MENTIONNE PAS, ET QUI SONT L'ESSENTIEL DU TRAVAIL

  A) LA CHAINE D'OBSERVATION LAISSE PASSER UN SIEGE QUI N'EXISTE PAS, ET C'EST LE
     PREMIER TRAVAIL DE LA PHASE. Tout agent entraine passe par la, donc rien d'autre
     ne compte tant que ce n'est pas ferme.

     `courtisans.infoset.vue_du_joueur(etat, joueur)` ne valide pas `joueur`. C'est la
     reouverture du defaut 2 de la phase 0, sur une entree neuve, releve par l'audit de
     la phase 2 et laisse ouvert. MESURE par le pilote le 20/08, sur une partie de la
     seed 0 apres 14 coups :

         vue_du_joueur(s, 0)   ->  23 connues,  2 dos     siege legitime
         vue_du_joueur(s, 1)   ->  20 connues,  5 dos     siege legitime
         vue_du_joueur(s, 2)   ->  22 connues,  3 dos     siege legitime
         vue_du_joueur(s, 3)   ->  20 connues,  5 dos     N'EXISTE PAS, ne leve pas
         vue_du_joueur(s, 7)   ->  20 connues,  5 dos     N'EXISTE PAS, ne leve pas
         vue_du_joueur(s, -1)  ->  20 connues,  5 dos     N'EXISTE PAS, ne leve pas

     C'est deja mauvais. Mais le pilote a sonde la chaine complete, et ce qu'elle fait
     est PIRE que ce que l'audit avait decrit :

         tenseur(s, 3)   ->  leve IndexError, par accident, sans nommer la cause
         tenseur(s, 7)   ->  leve IndexError, par accident, sans nommer la cause
         tenseur(s, -1)  ->  NE LEVE PAS. Rend 205 flottants.

     Ces 205 flottants ne sont le tenseur d'AUCUN siege. Mesure, meme etat :

         tenseur(-1) contre tenseur(0)  :  45 composantes differentes sur 205
         tenseur(-1) contre tenseur(1)  :  27 composantes differentes sur 205
         tenseur(-1) contre tenseur(2)  :  11 composantes differentes sur 205

     C'est un HYBRIDE : l'indexation relative resout -1 en « le dernier siege » par
     l'arithmetique modulaire de Python, pendant que la partition des cartes le resout en
     « personne » -- 5 dos au lieu des 3 du siege 2. `chaine(s, -1)` differe elle aussi
     de `chaine(s, 2)`.

     ET -1 N'EST PAS UNE VALEUR ARBITRAIRE. `courtisans.engine.JOUEUR_HASARD` VAUT -1.
     Une boucle d'entrainement qui ecrit `tenseur(etat, etat.current_player())` sur un
     nœud de distribution entraine ton reseau sur le tenseur de personne, et rien ne le
     signale. `JOUEUR_TERMINAL` vaut -4 et leve, par chance et non par intention.

     Tu fermes ca AVANT d'entrainer quoi que ce soit, et c'est la SEULE modification de
     `courtisans/` que tu as le droit de faire. Deux contraintes non negociables :
     la correction arrive avec ce qui l'empeche de se defaire -- une levee explicite qui
     nomme la cause, pas un IndexError incident -- et APRES TOUTE MODIFICATION DE
     `courtisans/`, tu reverifies que les 19 motifs de `outillage/mutation.py`
     s'appliquent encore : `uv run python outillage/mutation.py`. Une mutation qui cesse
     de s'appliquer ne mesure plus rien, et rien ne le signale.

  B) TU N'AS PAS LE DROIT D'EMPRUNTER TON BUDGET. Le protocole te fixe 1 000 parties
     appariees. Le seul ecart de gain detectable mesure a ce jour est +0,1013 a ce
     budget -- MAIS IL A ETE MESURE SOUS JEU UNIFORMEMENT ALEATOIRE, avec
     sigma(gain) = 0,6652 et rho = +0,0066 moyenne sur trois sieges, les trois valant
     +0,0123, +0,0007 et +0,0068.

     Rien ne dit que ces valeurs tiennent sous « un agent contre deux greedys ». Tu
     mesures donc sigma(gain) et rho SUR TA PROPRE COMPOSITION, en pre-inscription, et tu
     en deduis ton nombre de parties. C'est l'etape 4 de la boucle du paragraphe 2 :
     la mesure peut-elle trancher dans le budget ?

     L'affirmation du paragraphe 1 du protocole selon laquelle l'appariement « divise par
     cinq a dix » le nombre de parties etait publiee sans mesure, et elle est corrigee
     depuis le 20/08 : rho = 0,0066 donne un facteur de gain de 1,01, pas de 5 a 10.
     N'ecris pas pour autant que l'appariement ne sert a rien -- ce serait la meme faute
     dans l'autre sens, un chiffre sur une population que la phrase ne nomme pas.

  C) « SELF-PLAY » ET LA COMPOSITION MESUREE NE SONT PAS LA MEME POPULATION. Le protocole
     dit self-play avec pool fige ; la mesure dit un agent contre deux greedys. A trois
     joueurs, le self-play c'est trois copies du meme agent. Un agent entraine contre
     lui-meme developpe une convention stable a trois, et se mesure contre une population
     ou il est SEUL de son espece.

     Ce n'est pas un detail d'implementation, c'est un ecart entre la population
     d'entrainement et la population d'evaluation, et le protocole ne le traite pas. Tu
     l'ecris, tu proposes comment tu le geres -- proportion de parties contre le pool
     fige pendant l'entrainement, ou autre -- et tu REMONTES l'arbitrage. Ne le tranche
     pas seul.

  D) LA PERMUTATION DES SIEGES EST OBLIGATOIRE ET INCONDITIONNELLE. Pas parce que M1 la
     declenche -- il ne la declenche pas, le siege le plus favorise est a 33,50 % sous jeu
     aleatoire, +0,35 erreur-type de l'attendu. Mais parce que L'AVANTAGE DE SIEGE EST
     NEGLIGEABLE SOUS JEU ALEATOIRE ET MASSIF SOUS JEU GREEDY : gains par siege du greedy
     0,697 / 0,812 / 0,886, contraste apparie entre sieges extremes +0,1890, IC 99 %
     [+0,1588 ; +0,2196].

     Consequence directe : ton agent joue contre des greedys, donc il est dans le regime
     ou l'avantage de siege est massif. Un chiffre mesure sur un seul siege ne se compare
     JAMAIS a un chiffre agrege sur trois. C'etait le defaut bloquant du tour 1 de la
     phase 2, avec inversion de signe sur B1 -- -23,97 pt publie au lieu de +11,82 pt.

  E) LA MOITIE DES LIGNES DE COMPORTEMENT NE PEUT RIEN SEPARER A TON BUDGET. 19 des
     34 lignes de M4 sont hors du budget de la phase 3. B7 est AVEUGLE PAR LE BAS : son
     ecart detectable depasse son propre taux -- `B7-gaspillage` 0,30 % detectable pour un
     taux de 0,15 % (61/40008), `B7-gaspillage-vraie` 0,35 % detectable pour un taux de
     0,20 % (82/40008). Un agent a zero exact n'en est pas separable.

     N'annonce donc aucune difference sur ces lignes. Le rapport de phase 2 porte pour
     chaque ligne son ecart detectable : lis-le avant de comparer, pas apres.

CE QUE TU DOIS REMONTER, PAS TRANCHER SEUL

  a) L'ECART ENTRE POPULATION D'ENTRAINEMENT ET POPULATION D'EVALUATION -- l'obstacle C.

  b) L'ALGORITHME PRECIS. Le protocole tranche « self-play avec pool fige » et ecarte CFR
     avec sa justification. Il ne dit pas lequel. Propose, justifie de facon contrastive
     -- ce que les autres options auraient donne --, et attends ma reponse.

  c) LE SIGNAL D'APPRENTISSAGE. Le gain du paragraphe 5.2 est CATEGORIEL et n'arrive qu'au
     decompte : c'est un credit temporel long sur un signal pauvre. Le paragraphe 5.2 des
     regles autorise explicitement un signal auxiliaire PENDANT l'apprentissage, jamais
     dans la fonction de gain evaluee. Si tu en veux un, propose-le et attends ma reponse.

  d) TOUT DEFAUT QUE TU CROIS VOIR DANS `courtisans/` AILLEURS QU'EN A. Arrete-toi et
     remonte-le. Ne le corrige pas.

QUATRE DEFAUTS MINEURS HERITES DE LA PHASE 2, PLUS UNE RESERVE DE LA PHASE 1

Ils se traitent au DEBUT de la phase, avant toute mesure, et separement de ton travail --
dis explicitement lesquels tu as traites.

  1. Le defaut A ci-dessus, `vue_du_joueur`. C'est le plus serieux et il est deja detaille.
  2. Le rapport genere est ecrit en cp1252 quand les quatre autres documents sont en UTF-8.
  3. Deux des douze directions annoncees en phase 2 sont comptees comme tenues alors que
     la pre-inscription les declare NULLES PAR CONSTRUCTION.
  4. Une cellule « voir B4-departage » figure dans une table dont le texte dit qu'elle ne
     se lit qu'en juxtaposant deux nombres.
  5. La reserve de la phase 1 : rien ne relie `mesure/instance.py` a la description
     independante de `tests/outils.py`. Le pilote l'a EPROUVEE le 20/08 en injectant la
     derive, `familles=4` passe a `5` : 21 tests tombent, donc elle n'est pas muette. Mais
     AUCUN DES 21 NE DIT QUE L'INSTANCE A DERIVE -- ils echouent tous sur des nombres
     calcules a la main, dans tests/mesure/test_parties_construites.py,
     tests/mesure/test_comportements.py et tests/audit/test_echelle_de_l_invisible.py,
     avec pour message « son chiffre doit se reproduire ». Le garde-fou existe par
     accident, pas par intention. Ferme-la par UN test qui le dit.

ORDRE DE TRAVAIL -- NON NEGOCIABLE

C'est la boucle du paragraphe 2 de 05_protocole_experimental.md.

  Etape 0. Lis les documents ci-dessous. Puis reponds-moi en DOUZE LIGNES MAXIMUM : ce que
           tu as compris, l'algorithme que tu proposes et pourquoi, comment tu comptes
           traiter l'ecart entre population d'entrainement et population d'evaluation, et
           ce qui te semble mal specifie. AUCUN CODE AVANT MA REPONSE.

  Etape 1. Ferme l'obstacle A, avec sa mutation, et fais tourner
           `uv run python outillage/mutation.py`. Rends-moi le compte avant de continuer.

  Etape 2. Ecris l'HYPOTHESE et l'INSTRUMENT, AVANT toute mesure, et COMMITE-LES. Ils
           contiennent : sigma(gain) et rho MESURES SUR TA COMPOSITION, le nombre de
           parties que tu en deduis, l'ecart de gain detectable a ce budget, et a quel
           nombre de parties le seuil devient decisif. Le modele qui a tenu deux tours
           d'audit est `mesure/phase2_hypothese_et_instrument.md`.

  Etape 3. Ecris les tests AVANT d'entrainer. Un agent se teste comme le greedy s'est
           teste : la preuve qu'il ne lit pas la vue de dieu, sur des positions ou son
           entree est determinee.

  Etape 4. Entraine. Plafond 2 h par run, checkpoint toutes les 15 minutes. Seeds fixes et
           cites. Le garde-fou de l'etape 2 de la boucle s'applique : si le garde-fou
           ci-dessus tombe, tu arretes et tu le rapportes.

  Etape 5. Mesure. Sieges permutes. Publie les denominateurs et les compositions.

  Etape 6. AUDITE TON PROPRE RESULTAT avant de me le donner. Les trois questions du
           protocole -- la mesure mesure-t-elle ce que je crois ? sur quel support ? est-elle
           comparable a quoi ? Puis celles du paragraphe 0.2 : chaque taux a-t-il le bon
           denominateur ? chaque chiffre nomme-t-il la POPULATION dont il parle ? deux
           lignes comparees sont-elles au meme grain ? un zero ou un cent pour cent a-t-il
           ete confronte a un cas construit a la main ? l'unite a-t-elle ete reconstruite
           AVANT la valeur, et separement ?

  Etape 7. RELIS CE QUE TU VIENS D'ECRIRE, pas ce que tu as mesure en premier. En phase 2,
           quatre fois de suite, le defaut neuf est ne dans le texte qui corrigeait le
           precedent. La correction est le lieu du defaut suivant.

  Etape 8. Compte rendu au format du paragraphe 2 de 08_modele_compte_rendu.md. Chaque
           affirmation prefixee MESURE, DEDUIT ou SUPPOSE. Chaque chiffre decompose. Un
           SUPPOSE dans un compte rendu est un test qui manque : en phase 0, le seul
           SUPPOSE ecrit est devenu le defaut 9.

DOCUMENTS A LIRE, DANS CET ORDRE

  1. documentations/05_protocole_experimental.md — paragraphe 0 EN ENTIER, puis 1, 2, et
                                                   le 3 phase 3. Le paragraphe 0 est
                                                   normatif et il est neuf.
  2. documentations/01_regles.md                 — paragraphes 2.2, 2.6, 4.2, 5.2, 7.1, 7.2
  3. documentations/06_journal_decisions.md      — l'entree du 19/08 EN ENTIER
  4. mesure/resultats/phase2.md                  — le rapport de la phase 2. C'est ta ligne
                                                   de base. Il est en cp1252, voir le
                                                   defaut mineur 2.
  5. documentations/04_conventions_code.md
  6. documentations/08_modele_compte_rendu.md
  7. agents/perception.py et agents/greedy.py    — l'architecture d'aveuglement existe
                                                   deja, tu la reutilises

  L'ARCHITECTURE D'AVEUGLEMENT EST DEJA LA, ET TU LA REUTILISES. `agents/perception.py`
  est la frontiere : ce qui decide ne recoit qu'une `Perception`, donc ne PEUT PAS lire la
  pioche, les mains adverses, l'identite des Espions adverses, `scores()` ni `returns()`.
  L'aveuglement n'est pas une discipline a tenir, c'est une consequence de la signature.
  Ton agent respecte la meme frontiere. S'il lui faut un champ que `Perception` ne porte
  pas, tu l'ajoutes en JUSTIFIANT par le paragraphe 4.2 des regles pourquoi le decideur a
  le droit de le savoir -- et tu le remontes.

  Le moteur s'utilise ainsi :

      from courtisans.cards import Role
      from courtisans.config import GameConfig
      from courtisans.engine import Engine
      config = GameConfig(familles=4, roles=tuple(Role), exemplaires=2, joueurs=3)
      etat = Engine(config).reset(seed)
      etat.legal_actions() / etat.apply(a) / etat.is_terminal()
      etat.scores() / etat.returns() / etat.current_player()

  ATTENTION : `apply` mute l'etat en place et ne rend PAS un nouvel etat.

  L'observation d'un agent :

      from courtisans.infoset import tenseur, chaine
      tenseur(etat, joueur)   # 205 flottants sur entrainement-3j
      chaine(etat, joueur)    # 630 caracteres sur entrainement-3j

  `vue_privilegiee()` est la vue de dieu : pioche, mains, cartes vivantes, defausse.
  Reservee aux tests et a la mesure. UN AGENT NE LA VOIT JAMAIS. C'est le point sur lequel
  je serai le plus exigeant, comme je l'ai ete en phase 2. Le greedy en apporte la preuve a
  trois niveaux -- statique, `vue_privilegiee` piegee pour lever pendant la decision, et
  brouillage differentiel -- chacun assorti d'un test que le piege MORD. Fais au moins
  aussi bien.

  Note : uv exige UV_LINK_MODE=copy sur ce depot (OneDrive, os error 396).

MACHINE

Cette phase tourne sur le PC fixe : Ryzen 9600X, RTX 4060, 64 Go de RAM. La phase 2
n'utilisait aucun GPU ; toi tu peux.

AUCUNE DUREE NE SE CITE SUR UN SEUL CHRONOMETRAGE. Sur cette machine, cinq passes du meme
code donnent un rapport max/min de 2,93 a 3,00 par campagne, DE FACON NON MONOTONE. Le
temps mural mesure l'etat de la machine, pas le cout du code. Toute duree que tu publies
se cite sur au moins trois passes, avec son etendue.

CE QUE TU NE FAIS PAS

  - Tu ne modifies pas `courtisans/`, SAUF l'obstacle A, et avec sa mutation. Si tu crois y
    voir un autre defaut, ARRETE-TOI et remonte-le.
  - TU NE TOUCHES PAS A `agents/greedy.py`. C'est la ligne de base de toutes les phases
    suivantes et elle ne porte aucune mutation ; `outillage/mutation.py` ne cible que
    `courtisans/`, c'est verifie. Un agent de reference se documente, il ne se corrige pas
    apres publication.
  - EN PARTICULIER, tu ne « repares » pas l'incoherence d'horizon du greedy. Elle est
    reelle, connue et MESUREE : sa pose est evaluee Assassins resolus conjointement, son
    ciblage se decide un nœud a la fois sans les Assassins en attente. Elle est DECRITE au
    paragraphe 4 bis du rapport de phase 2, pas corrigee, et c'est delibere -- la corriger
    deplacerait l'etalon de toutes les phases qui l'ont deja cite.
  - Tu ne changes aucun seuil pour faire passer une mesure. Si l'agent ne bat pas le
    greedy, c'est un resultat, et il se rapporte tel quel. Un levier ecarte est un
    resultat, pas un echec.
  - Tu ne compares pas `B4-tout-dos` (3,89 %) ni `B5-renfort` (20,41 %) entre compositions
    differentes. Leurs taux bougeront sous trois agents entraines pour une raison qui n'est
    PAS l'habilete de l'agent. Le critere se decide sur le TEXTE de la definition :
    nomme-t-elle un autre joueur ? `B1-collectif` oui, ces deux-la non.
  - Tu ne cites pas la ligne de base collective de `B1-collectif` depuis la campagne « un
    greedy contre deux hasards ». Elle est celle des TROIS GREEDYS.
  - Tu ne modifies aucun document de `documentations/` sans mon accord.
  - Tu ne fais pas la phase 4. Pas d'iteration sur les leviers, pas de PSRO, pas de ligue.

CE QUE TU DOIS ME DONNER A LA FIN

  1. La fermeture de l'obstacle A, avec sa mutation et le compte de `outillage/mutation.py`.
  2. L'hypothese et l'instrument, ecrits et commites AVANT la mesure, avec sigma(gain) et
     rho mesures sur TA composition et le budget qui en decoule.
  3. Le gain moyen contre deux greedys, avec son IC 99 % bootstrap par donne, et la part de
     victoire fractionnee a cote, comparee a 33,33 %.
  4. Les mesures contre chaque membre du pool, CHACUNE AVEC SA COMPOSITION NOMMEE.
  5. La frequence des comportements B1 a B7, comparee a la ligne de base de la phase 2 AU
     MEME GRAIN -- `ecart_de_taux` et `cumuler` LEVENT si les grains different, sers-t'en
     plutot que de relire des cellules --, en excluant les lignes hors budget.
  6. L'agent, teste, avec la preuve qu'il ne lit pas la vue de dieu.
  7. CE QUE TES MESURES N'ETABLISSENT PAS. En particulier : B1 et B3 mesurent la frequence
     a laquelle un MOTIF apparait, jamais une planification ; et B1 est plafonne par les
     7,40 % de parties portant une perte d'acquis qu'AUCUN siege ne pouvait voir, mesures
     en phase 1. Ces retournements sont invulnerables a toute planification, par n'importe
     quel agent. C'est un plafond de ce que B1 pourra jamais mesurer, pas un defaut
     d'agent.
  8. Une proposition d'entree de journal, au format du paragraphe 4 de
     08_modele_compte_rendu.md et du paragraphe 0.1 du protocole.

CONTROLE DE BASE, A FAIRE EN PREMIER

Les cinq agents lances jusqu'ici ont TOUS cree leur worktree sur une base ou le paquet
`courtisans/` n'existait pas. Verifie, et ne commence pas si ca echoue :

    git merge-base --is-ancestor 45d2717 HEAD

Et pousse ta branche. Deux fois deja, du travail d'agent est reste sans upstream alors
qu'il portait un verdict entier.

COMMENCE PAR

  Le controle de base, puis les documents, puis tes douze lignes. Pas de code avant ma
  reponse.
```

---

## Notes pour l'humain qui lance ce prompt

**Ce qu'il faut donner :** l'accès au dépôt sur `main`, et ce bloc. Rien d'autre — surtout pas
une autre conversation.

**Vérifie sa base.** `git merge-base --is-ancestor 45d2717 HEAD` doit réussir. Les cinq agents
lancés jusqu'ici ont tous démarré au mauvais endroit.

**Vérifie que sa branche est poussée** avant de la croire sauvée. C'est arrivé deux fois : en
phase 1 le travail d'audit était non commité, en phase 2 la branche d'audit n'avait aucun
upstream alors qu'elle portait le verdict entier et 36 contrôles hostiles.

**Ce qu'il te demandera d'arbitrer**, et que tu me renvoies : l'algorithme précis, l'écart entre
la population d'entraînement et celle d'évaluation, et un éventuel signal auxiliaire. Les trois
sont des trous du protocole, pas du travail d'agent.

**Le piège de cette phase.** Elle a un seuil qui peut se rater, contrairement à la phase 2 — donc
la tentation n'est plus de publier un fait creux, elle est de bouger le seuil ou la composition
après avoir vu le résultat. La pré-inscription est commitée avant la mesure exactement pour ça, et
elle ne s'amende pas.

**Le point de vigilance concret.** Il va entraîner un réseau sur des tenseurs. Si sa boucle passe
un siège qui n'existe pas — et `JOUEUR_HASARD` vaut `-1`, ce qui ne lève pas —, il entraîne sur le
tenseur de personne et **rien ne le signale**. C'est pour ça que l'obstacle A passe avant tout le
reste, et que je veux son compte de mutations avant qu'il continue.

**Ensuite :** l'audit de la phase 3, conversation n° 7, quand son compte rendu existera.
