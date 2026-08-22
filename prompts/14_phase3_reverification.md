# Re-vérification après corrections — phase 3, tour 2

**À coller dans la conversation n° 7 — Audit de la phase 3.** Elle est rouverte, ce n'est pas
une conversation neuve.

---

```
LE CONSTRUCTEUR A CORRIGE. TU RE-VERIFIES CES DEFAUTS, ET RIEN D'AUTRE.

Ce n'est pas un second audit complet. Tu as rendu REJETE sur deux bloquants, quatre
majeurs et huit mineurs. Tu re-verifies ces quatorze points sur la branche
`phase-3-premier-agent`, jusqu'a `efcf54c`.

Ton verdict reste un mot : ACCEPTE, ACCEPTE SOUS RESERVE, ou REJETE.

CE QUE LE PILOTE A DEJA RECALCULE

Comme au tour 1, je te les donne pour que tu ne les refasses pas a l'identique, pas pour
que tu les croies.

  - 1 161 tests verts, 0 rouge, 0 saute. Recomptes par moi.
  - `git diff 9c96f65 -- courtisans/` est VIDE. Le cœur est intact, donc les 20 mutations
    n'avaient pas a etre rejouees : sa condition est la bonne.
  - Les 15 chiffres acquis sont tous presents et inchanges dans le rapport du tour 2, y
    compris le verdict -0,1643, IC [-0,1824 ; -0,1462], part 22,38 %.
  - TA BRANCHE N'A TOUCHE AUCUN FICHIER DU LIVRABLE. `git diff 9c96f65 audit-phase-3 --
    mesure/ agents/ courtisans/ outillage/` est vide. Le constructeur s'inquietait du §5
    de `07`, qui compte comme disqualifiant « un defaut corrige par l'auditeur » : tu n'as
    rien corrige, tu as constate. Le point est clos, il n'y a pas de reserve la-dessus.

CE QUE TU DOIS RE-VERIFIER EN PRIORITE

  1. QUE LES PARADES MORDENT VRAIMENT. Il annonce, pour chaque defaut, quelque chose qui
     empeche la correction de se defaire. Ce sont ces parades qu'il faut eprouver, pas les
     cellules reecrites. En particulier :
       - `test_aucun_controle_eprouve_ne_passe_un_booleen_litteral`, qui LIT L'AST de
         `mesure/phase3_audit.py`. Reinjecte un `True` litteral dans un `_epreuve` et
         verifie qu'il tombe.
       - `test_les_intitules_du_depot_sont_deux_a_deux_DISTINCTS`, qui lit les litteraux
         `intitule=` de tout `mesure/` et `agents/`. Redonne le meme nom a deux campagnes
         et verifie qu'il tombe.
       - `mesure/phase3_courbe.py`, qui doit LEVER si un jalon n'a pas sa serie par donne
         plutot que de deduire un ecart de deux niveaux.
       - `test_parties_requises_et_separable_sont_le_MEME_critere`.

  2. QUE LE JOURNAL DU RUN AIT ETE COMPLETE ET NON REFAIT. Il annonce que `completer`
     rejoue l'evaluation de chaque checkpoint et EXIGE que les quatre nombres deja
     journalises soient reproduits a l'identique, sinon elle leve. C'est le point le plus
     sensible du tour : si la serie par donne avait ete produite par une nouvelle mesure,
     les IC apparies ne porteraient pas sur les memes parties que les niveaux publies.
     Verifie-le sur le code ET en cassant la reproduction.

  3. QUE LES SEPT PAS SOIENT BIEN DANS LE BRUIT ET LE 1->8 BIEN ETABLI. Il publie
     +12,80 pt IC [+8,33 ; +17,40] avec Bonferroni pour 8 regards, la ou tu avais mesure
     +14,22 pt en 99 % simple. Il dit que ce sont deux risques differents sur la meme
     population. Verifie que c'est bien la seule difference.

  4. QUE LES QUATRE CONTROLES NON CASSES LE SOIENT MAINTENANT, chacun par reinjection de
     sa propre faute, et que les deux `releves` portent bien un statut distinct qui ne se
     compte pas parmi les concluants.

  5. QUE R4 VOIE LES DEUX ZEROS DES DEUX COTES, et que les quatre cas construits a la main
     qu'il nomme existent vraiment et confrontent bien ces zeros-la — y compris le
     contre-cas ou une politique uniforme en produit, sans lequel un compteur mort rendrait
     le meme zero.

  6. QUE LA REGLE MORTE SOIT DEVENUE UN NOMBRE. La branche `elif hors_budget` est retiree
     et chaque ligne non separable publie combien de parties il en faudrait. Verifie que
     ce nombre est juste sur au moins deux lignes, par ton propre calcul.

  7. LES HUIT MINEURS, dont le 8 : `ecart_detectable_deux_echantillons` ne doit PAS avoir
     touche la fonction de la phase 2, qui porte les chiffres d'un livrable audite.

  8. LE TEXTE ECRIT EN DERNIER. Son §5 est une relecture finale qui a trouve trois defauts
     dans ses propres corrections. C'est le texte le plus recent du livrable, donc le lieu
     le plus probable du defaut suivant. Cinq fois dans ce projet, le defaut neuf est ne
     dans la correction du precedent — six fois si l'on compte le mien.

CE QUI A CHANGE AU PROTOCOLE, ET QUE TU DOIS LIRE AVANT

  a) LE GARDE-FOU, QUATRIEME VERSION, ET SA BARRE CORRIGEE UNE CINQUIEME FOIS. Le
     constructeur a raison contre moi : la barre que j'avais ecrite — 2,75 pt — est un
     detectable IID SUR UN NIVEAU, quand le test porte sur un ECART APPARIE dont la barre
     est la demi-largeur de son propre intervalle, 3,56 a 4,06 pt ici.

     Recalcule par moi : avec la bonne grandeur, les ecarts de portee DEUX valent en
     moyenne 3,76 pt pour une barre de 3,83 — SOUS le seuil. La portee de trois est donc
     MINIMALE, pas confortable. Elle etait juste, mais pour une raison fausse.

     Verifie que `portee_minimale` calcule bien sur la grandeur appariee, et pas sur le
     detectable iid.

  b) LE PERIMETRE DES MUTATIONS EST ELARGI. `agents/greedy.py` reste exempt — c'est
     l'etalon, et c'est le seul invariant que la regle protegeait. `mesure/` et le reste de
     `agents/` entrent dans le perimetre, parce que le defaut le plus instructif de la
     phase 2 vivait dans le generateur, pas dans le moteur.

     L'elargissement N'EST PAS retroactif sur la phase 3 : c'est le premier travail de la
     phase 4. Le defaut 14 est donc traite comme documente, pas comme corrige. Ne le compte
     pas contre le constructeur, et verifie seulement que la limite est ecrite dans son
     rapport.

CE QUE TU NE FAIS PAS

  - Tu ne rouvres pas ce qui etait acquis au tour 1. Le verdict « battu », l'aveuglement,
    la disjonction des populations, la calibration du niveau nul : tu les as confirmes par
    du code independant, ils ne se refont pas.
  - Tu ne corriges rien.
  - Tu ne juges pas l'arbitrage du perimetre des mutations ni celui de la decision. Les
    deux sont a moi.

CE QUE TU DOIS ME RENDRE

  1. Ton verdict en un mot.
  2. Pour chacun des quatorze defauts : leve, partiellement leve, ou non leve — et pour
     ceux qui ne le sont pas, ce qui manque exactement.
  3. Tout defaut NEUF apparu dans les corrections. C'est ce que je te demande de chercher
     en priorite apres les parades.
  4. Une proposition d'entree de journal mise a jour, si ton verdict la change.

CONTROLE DE BASE

    git merge-base --is-ancestor efcf54c HEAD

Et pousse ta branche.
```

---

## Notes pour l'humain qui colle ce bloc

**Destinataire :** conversation n° 7 — Audit de la phase 3. Elle est rouverte, ce n'est pas une
conversation neuve.

**Ce qu'il doit rendre :** un verdict, et pour chacun des quatorze défauts s'il est levé ou non.
Pas un second audit complet.
