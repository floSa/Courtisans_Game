# Re-vérification du tour 3 — phase 3

**À coller dans la conversation n° 6.** Elle reste **auditeur des corrections**.

---

```
LA CONVERSATION N° 7 A CORRIGE LE TOUR 3. TU RE-VERIFIES A, B, C, D A G ET TA RESERVE.

Rien d'autre. Ce n'est pas un troisieme audit. Perimetre : commit `5bb9479` sur
`phase-3-premier-agent`, contre les sept defauts que tu as trouves au tour 2.

TON VERDICT EST UN MOT. Tu constates, tu ne corriges pas -- c'est la regle qui a coute un
tour entier a ce projet.

CE QUE LE PILOTE A RECALCULE

  - 1 172 tests verts, 0 rouge, 0 saute. Recomptes.
  - `git diff 9c96f65 -- courtisans/` VIDE. Les 20 mutations n'avaient pas a etre rejouees.
  - TES DEUX BORNES EXACTES, refaites par moi : 0/1967 -> 0,2338 %, 0/10382 -> 0,0443 %.
    Les deux tombent au quatrieme decimal.

UN DEFAUT QUE JE TE REMETS, ET QUE NI TOI NI LUI N'AVEZ NOMME

Ces deux bornes sont des Clopper-Pearson **UNILATERALES a 99 %**. Je l'ai etabli en les
recalculant des deux facons :

    0/1967   unilaterale 0,2338 %   bilaterale 0,2690 %
    0/10382  unilaterale 0,0443 %   bilaterale 0,0510 %

Ce sont ses chiffres qui sont unilateraux. **Tout le reste du rapport publie des
intervalles BILATERAUX a 99 %.** Deux quantites portant le meme intitule « 99 % » n'ont pas
le meme risque, et le rapport ne dit pas laquelle il emploie ou.

La conclusion ne bouge pas -- 0,2690 % reste tres loin de 35,87 %, et 0,0510 % de 3,66 %.
**C'est le libelle qui est en cause, pas le nombre**, et c'est exactement la faute maison :
une grandeur exacte sous un intitule qui en designe une autre. Verifie si le depot le dit,
et sinon compte-le.

CE QUE TU DOIS EPROUVER EN PRIORITE

  1. LES PARADES DU DEFAUT A. Il annonce trois choses : `separable` distingue `None` de
     `False` ; le rendu LEVE sur toute ligne qu'aucune regle n'a tranchee ; R4 fait suivre
     chaque zero du traitement recu. Fabrique une ligne qu'aucune regle ne tranche et
     verifie que la generation tombe. Et verifie les QUATRE cas de taux degenere qu'il dit
     traiter -- il a trouve en s'eprouvant que deux cotes a zero, cas parfaitement banal,
     faisait tomber le rapport entier.

  2. LES DEUX PARADES DU DEFAUT B. Un cas relit les cinq comptes DANS
     `mesure/resultats/phase3.md` ; un autre relit le tableau livre et refuse un verdict non
     calcule sur une ligne a zero, eprouve sur la ligne exacte que le tour 2 publiait.
     Falsifie a nouveau une entree et verifie que les deux mordent. C'est ton propre defaut,
     tu es le mieux place pour le refaire.

  3. LE DEFAUT C. Le predicat vit desormais dans `bootstrap.EcartApparie.progres_etabli`, a
     un seul site -- la v5 l'avait recopie dans `campagne.py`, et c'est la copie qui portait
     la faute. Repasse TON effondrement de -17,80 pt IC [-18,43 ; -17,08] et verifie qu'il
     declenche maintenant. Verifie aussi qu'un progres etabli positif ne declenche pas.

  4. SES SEPT DEFAUTS NEUFS, TROUVES PAR LUI. Le plus instructif : le decompte ajoute a
     `test_parties_requises_et_separable_sont_le_MEME_critere` est TOMBE DU PREMIER COUP --
     son balayage `range(2900, 3101, 20)` ne visitait que la branche non separable. Vert
     depuis le tour 2 sans avoir jamais eprouve la moitie de l'equivalence qu'il annonce.

     C'est ta reserve sur les intitules, sous une troisieme forme : UNE PARADE QUI NE
     VERIFIE PAS AVOIR INSPECTE QUELQUE CHOSE. Cherche-la partout ailleurs dans le depot,
     y compris dans TES propres controles de `tests/audit_phase3/`.

  5. QUE `portee_minimale` RECOIVE DES GRANDEURS MESUREES et non transcrites : il annonce
     3,8333 pt et 1,8280 pt mesures sur le journal, rendant 3. Refais le calcul.

  6. LE TEXTE ECRIT EN DERNIER, ET L'AVANT-DERNIER. Tu avais raison au tour 2 : deux des
     trois defauts neufs etaient dans `c0b073b`, pas dans la relecture finale. Applique la
     meme regle a ce tour-ci.

CE QUE TU NE FAIS PAS

  - Tu ne rouvres aucun des douze defauts leves au tour 2, ni rien d'acquis au tour 1.
  - Tu ne refais aucune campagne, tu ne relances aucun entrainement.
  - Tu ne corriges rien.
  - Tu ne modifies aucun document de `documentations/`.

CE QUE TU ME RENDS

  1. Ton verdict en un mot.
  2. Pour chacun de A, B, C, D a G et ta reserve : leve, partiellement leve, ou non leve.
  3. Le point unilaterale / bilaterale ci-dessus : etabli ou non.
  4. Tout defaut NEUF apparu dans ces corrections.

    git merge-base --is-ancestor 5bb9479 HEAD

Et pousse ta branche.
```

---

## Notes pour l'humain

**Destinataire :** conversation n° 6, toujours auditeur des corrections.

**Conversation n° 7 :** rien, elle attend le verdict.
