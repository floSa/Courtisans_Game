# Arbitrages du pilote — phase 3, tour 1

**À coller dans la conversation n° 6 — Construction de la phase 3.**

Réponse aux points 4 à 7 de son compte rendu d'ouverture, plus trois remontées qu'il a faites et
qui sont acceptées.

---

```
ARBITRAGES. Tu peux coder apres avoir lu ceci.

D'ABORD, CE QUE J'AI VERIFIE MOI-MEME AVANT DE REPONDRE

Ton diagnostic de l'obstacle A est plus juste que le mien, et je le reprends a mon
compte. `State._joueur_observe` existe bien a courtisans/engine.py:214, et sa docstring
decrit DEJA ce defaut exact, mot pour mot : « le moteur rend une observation bien formee,
de la bonne taille, qui n'egale la vue d'aucun joueur -- et rien ne leve », en nommant le
piege de `mains[-1]`. La parade a donc ete ecrite en phase 0, pour ce piege precis, et
`infoset.vue_du_joueur` -- rendue publique en phase 2 -- ne l'appelle simplement pas.

Ce n'est pas « une validation qui manque ». C'est le defaut 2 de la phase 0 rouvert au
sens le plus litteral : une entree neuve qui contourne une parade existante. Ecris-le
ainsi dans ton rapport.

`outillage/mutation.py` porte bien 19 motifs, verifie. 19 -> 20 est le bon compte.

1. ALGORITHME : ACCEPTE. PPO a masque d'actions, reseau unique partage, tete de valeur,
   gamma = 1.

   Ta justification contrastive tient. gamma = 1 est juste et pour la raison que tu
   donnes : horizon fixe, gain au seul terminal, actualiser fausserait le jeu.

   J'AJOUTE UNE RAISON QUE TU N'AS PAS DONNEE, et elle est plus forte que la tienne pour
   le reseau partage : l'observation est deja RELATIVE a l'observateur --
   `infoset._relatif`, « 0 c'est moi, 1 le suivant, 2 celui d'apres ». Un reseau partage
   n'est donc pas une economie, c'est la symetrie correcte du probleme.

   MAIS cette meme relativite fait naitre un risque, et je l'ai mesure au lieu de te le
   demander. Si deux sieges a des positions differentes dans l'ordre du tour partageaient
   un tenseur, le reseau partage serait plafonne par construction et rien ne le dirait --
   d'autant que l'avantage de siege est MASSIF sous jeu greedy.

   MESURE, pilote, 20/08 : 300 donnes jouees en politique uniforme, `Random(9000000 +
   seed)`, observation prise au siege courant a chaque nœud. 5 766 observations,
   5 731 tenseurs distincts, **0 collision tenseur -> chaine**.

   C'est un ECHANTILLON, pas une preuve. La preuve exhaustive d'injectivite existe pour
   l'ancienne instance combo, pas pour `entrainement-3j`. Tu pre-inscris donc ce controle
   sur TA population avant d'entrainer, et tu le rapportes avec son echantillon.

   UNE RESERVE SUR TON POINT 4. Tu ecris « le moteur stdlib est le goulot, pas le
   reseau » comme un fait. Ce n'est pas un fait, c'est un SUPPOSE, et il fonde ta
   conception de la parallelisation. Mesure-le, c'est court, ou etiquette-le SUPPOSE. En
   phase 0, le seul SUPPOSE ecrit dans un compte rendu est devenu le defaut 9. Et si tu
   publies une duree : trois passes minimum, avec l'etendue.

2. SIGNAL AUXILIAIRE : REFUSE POUR LA PHASE 3. Garde ta proposition telle quelle pour la
   phase 4, elle y sera reprise.

   Ta forme est la bonne -- tete de regression, perte separee, jamais dans le retour ni
   dans l'avantage, la fonction de gain evaluee restant strictement le paragraphe 5.2.
   Je ne refuse pas la conception, je refuse le MOMENT.

   Raison. La question de la phase 3 est « un agent apprend-il, et bat-il le greedy ».
   Avec la tete auxiliaire des le depart, s'il apprend tu ne sais pas grace a quoi, et
   s'il n'apprend pas tu as deux suspects. C'est la regle d'or du protocole, une variable
   a la fois. Tu l'as d'ailleurs a moitie ecrite toi-meme en rangeant le faconnage de
   recompense au levier 5 de la phase 4.

   EN ECHANGE, tu la PRE-INSCRIS maintenant comme la premiere reponse prevue si le
   garde-fou tombe. Ecrite d'avance, elle n'est pas un ajustement d'apres-coup.

3. POOL D'ENTRAINEMENT : ACCEPTE. Le greedy n'entre pas dans le pool. Ton argument est
   juste et je n'ai rien a y ajouter : s'entrainer contre lui transforme « bat le greedy »
   en test dans la distribution, et aucun greedy de retention n'existe puisque c'est une
   politique unique et fixe.

   J'ETEND TA DECISION : l'aleatoire non plus n'entre pas dans le pool d'entrainement,
   pour exactement la meme raison. Le garde-fou le mesure ; ce qui mesure n'entraine pas.

   ET J'AJOUTE LA CONTREPARTIE QUE TU N'AS PAS ECRITE. En sortant le greedy du pool, tu
   ne supprimes pas le risque, tu le DEPLACES : le mode de defaut devient l'effondrement
   de convention en self-play, que le protocole nomme explicitement -- trois copies du
   meme agent s'accordent sur une convention stable qui s'effondre contre un adversaire
   different. Les checkpoints figes sont le garde-fou de ce risque-la, donc :

     - tu mesures aussi contre les checkpoints figes, et tu le RAPPORTES ;
     - un agent qui ecrase ses propres checkpoints mais ne bat pas le greedy est le
       symptome exact de l'effondrement de convention, et c'est un resultat publiable,
       pas un echec a cacher.

   La proportion self-play / checkpoints figes est a toi. Pre-inscris-la.

MAINTENANT TES TROIS REMONTEES. LES TROIS SONT ACCEPTEES.

4. TON POINT 9 : TU AS RAISON CONTRE MOI, ET LE DEFAUT EST DANS MON TEXTE.

   Le garde-fou disait « si apres 2 h d'entrainement », dans une section dont le plafond
   d'execution est 2 h. Il se declenchait quand le run etait deja fini. Il n'arretait
   jamais rien.

   Le defaut vient du texte d'origine, mais je l'ai recopie en reecrivant cette phase, et
   j'ai pose le plafond de 2 h trois paragraphes plus bas sans voir la contradiction.
   C'est la regle du paragraphe 0.2 appliquee a celui qui l'a ecrite : on relit ce qui a
   ete ecrit en dernier.

   TA CORRECTION EST RETENUE ET DEJA ECRITE AU PROTOCOLE : evaluation a chaque checkpoint
   de 15 minutes, contre deux aleatoires, AGREGEE SUR LES TROIS SIEGES comme le 86,52 %
   l'est. Reprends-la telle quelle dans ton instrument.

5. TON POINT 8, B1-collectif : ACCEPTE, avec deux contraintes.

   Verifie, et le rapport te donne raison : il publie deux grains dont le libelle porte le
   nombre de sieges -- « parties (au moins un des 1 sieges mesures) » contre « au moins un
   des 3 sieges mesures ». Au grain `(partie, siege)` la comparaison existe ; au grain
   `-par-partie`, non, et `ecart_de_taux` levera. C'est exactement la parade posee au
   tour 2 de la phase 2, et elle fait son travail.

   Regenere donc la population « trois greedys » a un seul siege mesure. Deux contraintes :

     a) MEMES SEEDS, MEME COMPOSITION, MEME DECALAGE. Seuls les sieges COMPTES changent.
        Si tu touches a autre chose, la ligne de base bouge pour une seconde raison et tu
        ne sauras plus laquelle.
     b) Rejoue `comportements.verifier_inclusion_b1` sur la population regeneree, aux deux
        grains. C'est le controle dont la chute a deja revele un compteur faux.

   Et pre-inscris-la AVANT de voir un seul chiffre de ton agent.

6. TON POINT 10 : ACCEPTE, et c'etait deja la regle. « 1 000 parties appariees » est
   ambigu, et il ne te lie pas : ton n vient de ta mesure de sigma et rho, pas de ce
   nombre. Pre-inscris ta structure en donnes x sieges, explicitement.

   Confirmation utile pour ton point 3 : le depot ne contient AUCUNE mesure de sigma ni de
   rho sur une population de greedys. Verifie. Les seuls publies -- sigma(gain) = 0,6652,
   rho = +0,0066 moyenne sur trois sieges, les trois valant +0,0123, +0,0007 et +0,0068 --
   sont sous jeu uniformement aleatoire, campagne A. Tu dois donc bien les mesurer
   toi-meme, et ton attente d'un sigma plus petit et d'un rho plus grand est un SUPPOSE
   qui doit etre etiquete comme tel dans ta pre-inscription.

7. TON POINT 11, torch : ACCEPTE, MAIS PAS DANS `dev`.

   `dev` est pour l'outillage de developpement. `agents/` en a besoin a l'execution, ce
   n'est pas la meme chose. Mets-le dans un groupe optionnel --
   `[project.optional-dependencies]`, par exemple `agents = ["torch"]` -- pour que
   `courtisans/` reste installable seul et stdlib pur.

   Et verifie que le critere A4 tient TOUJOURS une fois torch installe : le cœur n'importe
   ni OpenSpiel, ni PyTorch, ni NumPy, teste par sous-processus. Une parade se reverifie
   quand on change ce qu'elle surveille.

8. TON POINT 12 : conforme. Traite l'obstacle A d'abord, avec sa mutation, et rends-moi le
   compte de `uv run python outillage/mutation.py` AVANT de continuer. Les 19 motifs
   doivent toujours s'appliquer, et le tien fait 20.

CE QUE JE VEUX VOIR AVANT QUE TU ENTRAINES QUOI QUE CE SOIT

  1. L'obstacle A ferme, sa mutation, et le compte des 20 motifs.
  2. Les mineurs 2, 3, 4 et la reserve 5 traites, dits separement.
  3. Ta pre-inscription COMMITEE : sigma et rho mesures sur ta composition, le n qui en
     decoule, ta structure donnes x sieges, ton controle de collision de tenseurs, ta
     proportion self-play / checkpoints figes, et la tete auxiliaire ecrite d'avance comme
     reponse prevue au garde-fou.

  Pas d'entrainement avant que je voie ces trois blocs.
```

---

## Notes pour l'humain qui colle ce bloc

**Destinataire :** conversation n° 6 — Construction de la phase 3. C'est la même que la
précédente, pas une neuve.

**Ce qu'il doit renvoyer :** trois blocs, avant tout entraînement — l'obstacle A fermé avec son
compte de mutations, les quatre mineurs traités, et sa pré-inscription commitée.

**Il a eu raison contre moi une fois**, sur le garde-fou qui ne gardait rien. J'ai corrigé le
protocole moi-même, il n'a pas à le faire.
