# Re-vérification croisée des corrections — phase 3, tour 2

**À coller dans la conversation n° 6 — Construction de la phase 3.** Elle est rouverte, et
**elle change de rôle** : elle audite les corrections écrites par la conversation n° 7.

Remplace [14_phase3_reverification.md](14_phase3_reverification.md), annulé.

---

```
TU CHANGES DE ROLE. TU AUDITES, TU NE CONSTRUIS PLUS.

CE QUI S'EST PASSE, ET POURQUOI CA T'ARRIVE

Tu as construit la phase 3. Une autre conversation l'a auditee et a rendu REJETE : deux
bloquants, quatre majeurs, huit mineurs, 97 controles hostiles.

Le pilote a ecrit un prompt de corrections a TON adresse. Lors du relais, il a ete colle
dans la conversation d'AUDIT. C'est donc l'auditeur qui a corrige ses propres constats,
sur `phase-3-premier-agent`, commits `ce130aa`, `c0b073b`, `efcf54c`. Il l'a signale deux
fois ; le pilote l'a lu sans reagir. **L'erreur est celle du pilote, pas la tienne ni la
sienne.**

Le paragraphe 5 de `documentations/07_protocole_audit_croise.md` compte comme disqualifiant
un defaut corrige par l'auditeur. La raison n'est pas formelle : **personne ne peut
etablir la validite de ses propres corrections.** Faire re-verifier ces corrections par
leur auteur n'etablirait rien du tout.

**Les roles ont donc effectivement change de mains, et on les prend comme ils sont.** La
conversation n° 7 est le CONSTRUCTEUR de ces corrections. Tu en es l'AUDITEUR. Tu n'as
ecrit aucune de ces trois commits : ton independance vis-a-vis d'elles est reelle.

Ce qui reste vrai : le livrable d'origine est le TIEN. Tu audites des corrections apportees
a ton propre travail par quelqu'un d'autre. Ce n'est pas un conflit d'interet, c'est le
contraire — tu es la personne la mieux placee pour voir si une correction a casse ce
qu'elle ne devait pas toucher, et la moins susceptible de laisser passer une correction
complaisante.

CE QUE TU AUDITES, ET RIEN D'AUTRE

Les trois commits `ce130aa`, `c0b073b`, `efcf54c`, contre les quatorze defauts de l'audit.
Tu ne rouvres pas ton propre travail d'origine, tu ne refais aucune campagne.

TON VERDICT EST UN MOT : ACCEPTE, ACCEPTE SOUS RESERVE, ou REJETE.

Tu es IRRECEVABLE si tu CORRIGES au lieu de CONSTATER. Cette fois, la regle est la raison
meme pour laquelle tu es sollicite : si tu corriges, on aura fait deux fois la meme faute
et il faudra une quatrieme conversation.

CE QUE LE PILOTE A DEJA RECALCULE

Pour que tu ne le refasses pas a l'identique, pas pour que tu le croies.

  - 1 161 tests verts, 0 rouge, 0 saute. Recomptes par moi.
  - `git diff 9c96f65 -- courtisans/` est VIDE. Le cœur est intact, donc les 20 mutations
    n'avaient pas a etre rejouees : la condition posee est la bonne.
  - Les 15 chiffres acquis sont tous presents et inchanges dans le rapport du tour 2, y
    compris le verdict -0,1643, IC [-0,1824 ; -0,1462], part 22,38 %.
  - La branche `audit-phase-3` ne touche aucun fichier du livrable. Les corrections sont
    bien sur `phase-3-premier-agent` et nulle part ailleurs.

CE QUE TU DOIS CHERCHER EN PRIORITE

  1. QU'UNE CORRECTION N'AIT PAS CASSE CE QU'ELLE NE DEVAIT PAS TOUCHER. C'est ce que toi
     seul peux voir, parce que le code d'origine est le tien. Les 15 chiffres acquis sont
     identiques — mais un chiffre identique ne prouve pas qu'un calcul n'a pas change de
     route. Verifie les routes, pas seulement les valeurs.

  2. QUE LES PARADES MORDENT VRAIMENT. Chaque correction annonce quelque chose qui
     l'empeche de se defaire. Ce sont ces parades qu'il faut eprouver, pas les cellules
     reecrites. En particulier :
       - `test_aucun_controle_eprouve_ne_passe_un_booleen_litteral`, qui LIT L'AST de
         `mesure/phase3_audit.py`. Reinjecte un `True` litteral dans un `_epreuve` et
         verifie qu'il tombe.
       - `test_les_intitules_du_depot_sont_deux_a_deux_DISTINCTS`, qui lit les litteraux
         `intitule=` de tout `mesure/` et `agents/`. Redonne le meme nom a deux campagnes.
       - `mesure/phase3_courbe.py`, qui doit LEVER si un jalon n'a pas sa serie par donne.
       - `test_parties_requises_et_separable_sont_le_MEME_critere`.

  3. QUE LE JOURNAL DU RUN AIT ETE COMPLETE ET NON REFAIT. C'est le point le plus sensible
     du tour. `completer` doit rejouer l'evaluation de chaque checkpoint et EXIGER que les
     quatre nombres deja journalises soient reproduits a l'identique, sinon lever. Si la
     serie par donne avait ete produite par une nouvelle mesure, les IC apparies ne
     porteraient pas sur les memes parties que les niveaux publies, et tout le defaut 1
     serait mal corrige. Verifie-le sur le code ET en cassant la reproduction.

  4. QUE LES QUATRE CONTROLES NON CASSES LE SOIENT MAINTENANT, chacun par reinjection de sa
     propre faute, et que les deux `releves` portent un statut distinct qui ne se compte pas
     parmi les concluants.

  5. QUE R4 VOIE LES DEUX ZEROS DES DEUX COTES, et que les quatre cas construits a la main
     qu'il nomme existent et confrontent bien ces zeros-la — y compris le contre-cas ou une
     politique uniforme en produit, sans lequel un compteur mort rendrait le meme zero.

  6. QUE LA REGLE MORTE SOIT DEVENUE UN NOMBRE. La branche `elif hors_budget` est retiree et
     chaque ligne non separable publie combien de parties il faudrait. Verifie ce nombre par
     ton propre calcul sur au moins deux lignes.

  7. QUE `ecart_detectable_deux_echantillons` N'AIT PAS TOUCHE LA FONCTION DE LA PHASE 2,
     qui porte les chiffres d'un livrable audite et clos.

  8. LE TEXTE ECRIT EN DERNIER. Le §5 du compte rendu de corrections est une relecture
     finale qui a trouve trois defauts dans ses propres corrections. C'est le texte le plus
     recent du livrable, donc le lieu le plus probable du defaut suivant. Six fois dans ce
     projet, le defaut neuf est ne dans la correction du precedent — dont deux fois chez le
     pilote.

CE QUI A CHANGE AU PROTOCOLE, ET QUE TU DOIS LIRE AVANT

  a) LE GARDE-FOU, ET SA BARRE CORRIGEE. Tu avais raison contre le pilote : la barre de
     2,75 pt est un detectable IID SUR UN NIVEAU, quand le test porte sur un ECART APPARIE
     dont la barre est la demi-largeur de son propre intervalle, 3,56 a 4,06 pt ici.
     Recalcule par moi : les ecarts de portee deux valent en moyenne 3,76 pt pour une barre
     de 3,83 — SOUS le seuil. La portee de trois est MINIMALE, pas confortable.

     Verifie que `portee_minimale` calcule bien sur la grandeur appariee.

  b) LE PERIMETRE DES MUTATIONS EST ELARGI. `agents/greedy.py` reste exempt — c'est
     l'etalon. `mesure/` et le reste de `agents/` entrent, parce que le defaut le plus
     instructif de la phase 2 vivait dans le generateur et pas dans le moteur.
     L'elargissement N'EST PAS retroactif : c'est le premier travail de la phase 4. Le
     defaut 14 est traite comme documente, pas comme corrige — ne le compte pas contre le
     correcteur.

CE QUE TU NE FAIS PAS

  - Tu ne corriges rien. Si tu trouves un defaut, tu le nommes et tu le chiffres.
  - Tu ne rouvres pas ce qui etait acquis : le verdict « battu », l'aveuglement, la
    disjonction des populations, la calibration du niveau nul. Trois implementations les
    ont confirmes.
  - Tu ne refais aucune campagne, tu ne relances aucun entrainement.
  - Tu ne juges ni l'arbitrage du perimetre des mutations, ni la decision. Les deux sont au
    pilote.
  - Tu ne modifies aucun document de `documentations/`.

CE QUE TU DOIS ME RENDRE

  1. Ton verdict en un mot.
  2. Pour chacun des quatorze defauts : leve, partiellement leve, ou non leve — et pour
     ceux qui ne le sont pas, ce qui manque exactement.
  3. Tout defaut NEUF apparu dans les corrections. C'est ce que je te demande de chercher en
     priorite apres les parades.
  4. Ton avis, en tant qu'auteur du code d'origine, sur ce qu'une correction aurait pu
     casser sans que les chiffres le montrent.

CONTROLE DE BASE

    git merge-base --is-ancestor efcf54c HEAD

Et pousse ta branche.
```

---

## Notes pour l'humain qui colle ce bloc

**Destinataire :** conversation n° 6 — Construction de la phase 3. Elle est rouverte et **change
de rôle** : elle devient l'auditeur des corrections.

**La conversation n° 7 est close.** Ne lui envoie plus rien, et ne la compacte pas : son dossier
complet a déjà été rendu, il est conservé.

**Pourquoi ce changement :** la n° 7 a corrigé les défauts qu'elle avait trouvés, parce que
`prompts/13` lui a été collé au lieu d'aller à la n° 6. Personne ne peut établir la validité de
ses propres corrections.
