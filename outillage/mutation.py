"""Test de mutation : verifier que la suite sait echouer.

**Pourquoi cet outil existe.** A l'etape 6, la suite affichait 395 verts sur 395. En
supprimant deux blocs de l'encodage -- la phase et la zone de l'Assassin en cours -- puis
en faisant compter les cartes mortes dans le residu, elle affichait encore 395 sur 395.
Deux des trois pieges du paragraphe 4.2, classes bloquant et critique, n'etaient enforces
par aucun test alors que tout passait.

La cause est generale : **un test qui verifie la coherence entre deux sorties du meme
calcul ne teste rien.** C16 et I8 comparaient la chaine et le tenseur, tous deux rendus
depuis la meme observation ; retirer un champ des deux les laissait coherents.

Une suite qui passe sans qu'on ait verifie qu'elle sait echouer n'est pas une suite de
tests. Cet outil applique une mutation connue au depot, rejoue la suite, et rapporte combien
de tests tombent. Une mutation qui ne fait rien tomber designe un trou.

**Le perimetre, et pourquoi il s'est elargi le 23/08.** Les vingt premieres mutations ne
touchent que `courtisans/` -- le moteur et son adaptateur. « 20 mutations, toutes detectees »
ne disait donc rien des ~2 500 lignes de `agents/` et `mesure/`, c'est-a-dire du code qui
**entraine** et du code qui **mesure**. Le paragraphe 0.3 du protocole a ete elargi le 21/08,
et la raison se lit dans l'histoire du projet : le defaut le plus instructif de la phase 2 --
un facteur trois indu dans six budgets, qui a survecu a DEUX verifications reussies -- vivait
dans le GENERATEUR, pas dans le moteur. Une suite qui sait attraper une faute de regle et pas
une faute de mesure protege le chiffre qu'elle publie moitie moins qu'elle ne le croit.

**`agents/greedy.py` est EXEMPT, et c'est le seul invariant que la regle protegeait.** C'est
l'etalon de toutes les phases : un agent de reference se documente au lieu de se corriger, et
une mutation qui le change deplacerait la ligne de base a laquelle tout le reste se compare.
`FICHIERS_EXEMPTS` le tient, et `principal` leve si une mutation le vise -- une exemption
ecrite en commentaire n'est pas une exemption.

**UNE MUTATION QUI SURVIT EST UN RESULTAT, PAS UN ECHEC.** Elle nomme un trou de la suite. Le
code de sortie 1 dit « il y a des survivantes », pas « l'outil a echoue » : elles se
rapportent, elles ne se cachent pas, et on ne fabrique pas un test a la hate pour en faire
tomber une sans dire ce qu'elle a appris.

**LA PASSE DE BASE, ET LE MODE DE DEFAILLANCE QU'ELLE FERME.** Cet outil lit des ECARTS : il
compare une suite mutee a une suite non mutee. Jusqu'au 23/08/2026 il ne mesurait jamais le
second terme. `principal` verifiait que le depot etait propre, puis ecrivait `detectee` des
que `rouges` etait non nul -- **sans jamais savoir si ce rouge venait de la mutation**.

Le calcul se fait, il ne se craint pas : **un seul rouge preexistant fait que la campagne
entiere rapporte zero survivante.** Les 57 lignes portent alors `rouges >= 1`, les 57 sont
etiquetees `detectee`, et les 57 sont fausses. C'est le pire mode de defaillance possible pour
un tel outil : **il annonce une suite parfaite exactement quand la suite est cassee.**

Et ce n'etait pas une hypothese. Le releve d'etape 0 de la phase 4 a ete commite avec un
document que `test_les_documents_de_mesure_...` exigeait de nommer ; la suite est passee au
rouge, et une campagne rejouee sur ce depot aurait rendu **56 detectees, 0 survivante, 1
expiree** -- un feu vert integral et faux, sur l'instrument meme qui venait de publier onze
survivantes.

**`_passe_de_base` joue donc la suite NON MUTEE une fois, en tete de campagne, et l'outil
REFUSE de commencer si elle n'est pas verte.** Un instrument qui mesure des ecarts doit refuser
de tourner quand son zero n'est pas a zero. Son compte est rapporte en tete du releve, pour que
tout lecteur voie le zero sur lequel les 57 ecarts sont lus.

**Toute correction de defaut arrive avec sa mutation.** Les cinq dernieres de la liste
remettent, une a une, les defauts trouves par l'audit de la phase 0 : un correctif dont la
mutation survit n'est tenu par aucun test, et il repartira au prochain refactoring.

Usage :

    uv run python outillage/mutation.py                  # toutes les mutations
    uv run python outillage/mutation.py --cible tests/infoset
    uv run python outillage/mutation.py --nom residu-compte-les-morts

L'outil refuse de tourner si le depot a des modifications non commitees : il restaure les
fichiers avec `git checkout`, ce qui detruirait un travail en cours.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

#: Les fichiers qu'aucune mutation ne vise, et le motif est unique : `agents/greedy.py` est
#: l'**etalon** de toutes les phases. La ligne de base « trois greedys, un seul siege compte »,
#: le 86,52 % du garde-fou, le juge de B4 : les trois passent par lui. Le muter ne testerait pas
#: la suite, il deplacerait le metre. Un agent de reference se documente au lieu de se corriger.
#:
#: Ecrit comme une **donnee que `principal` verifie**, et non comme une phrase de la docstring :
#: c'est la seule forme d'exemption qui resiste a un ajout distrait de mutation.
FICHIERS_EXEMPTS: frozenset[str] = frozenset({"agents/greedy.py"})

#: Le delai de garde d'une passe de la suite, en secondes. **MESURE** : la suite complete
#: prend 169 s sur la machine du projet (une passe -- le paragraphe 0.2 en exige trois avant
#: qu'une duree se CITE ; celle-ci ne se cite pas, elle dimensionne une marge). Le delai est
#: pose a **15 minutes**, soit plus de cinq fois la passe la plus lente observee : assez large
#: pour qu'une machine chargee ne le franchisse pas, assez court pour qu'un blocage se voie.
#:
#: Sans lui, `masse-binomiale-part-de-zero` a fait tourner une passe **2 h 48** sans rendre la
#: main. Une mutation qui bloque la suite n'est pas un verdict : c'est un troisieme etat.
DELAI_DE_GARDE = 15 * 60



@dataclass(frozen=True)
class Passe:
    """Ce qu'une passe de la suite a rendu.

    Attributes:
        verts: tests passes.
        rouges: tests en echec.
        tombes: les **identifiants** des tests en echec. Ils ne servent pas au verdict d'une
            ligne -- c'est `rouges` qui le donne -- mais a un controle que rien d'autre ne
            peut faire : voir `tombes_sous_TOUTES_les_mutations`.
    """

    verts: int
    rouges: int
    tombes: frozenset[str]


@dataclass(frozen=True)
class Mutation:
    """Une faute plausible, injectee volontairement dans le coeur.

    Attributes:
        nom: identifiant court, utilisable avec `--nom`.
        fichier: chemin relatif du fichier a muter.
        avant: le texte a remplacer. Doit apparaitre exactement une fois.
        apres: le texte de remplacement.
        vise: ce que la mutation casse, en une ligne.
    """

    nom: str
    fichier: str
    avant: str
    apres: str
    vise: str


#: **Le temoin negatif : une mutation qui ne change RIEN.** Elle insere un commentaire, donc
#: le comportement du depot est identique au caractere pres apres application.
#:
#: **Ce qu'elle attrape, et pourquoi la passe de base ne suffisait pas.** La passe de base
#: mesure le zero *avant* la premiere mutation. Elle ne voit donc pas un test qui reagit au
#: FAIT QU'UN FICHIER A ETE EDITE plutot qu'a un changement de comportement -- un tel test est
#: vert tant qu'aucune mutation n'est en place, et rouge sous **toutes** a la fois.
#:
#: Ce n'est pas theorique. Le 23/08/2026, deux cas de `tests/outillage/test_mutation.py`
#: verifiaient les invariants du catalogue en lisant le DISQUE : « ce motif apparait
#: exactement une fois dans sa source ». Sous mutation, le fichier ne contient plus son
#: `avant`, les deux tombaient, et la campagne a rendu **56 detectees, 0 survivante** --
#: exactement `+2 rouges` sur chaque ligne, les onze survivantes reelles effacees.
#:
#: **C'est le mode de defaillance que la passe de base venait de fermer, refait par la
#: correction elle-meme.** Le temoin le ferme comme CLASSE : si la suite n'est pas verte avec
#: une mutation qui ne change rien, un test reagit a l'edition et non au comportement, et tout
#: verdict de la campagne serait faux.
MUTATION_TEMOIN = Mutation(
    nom="TEMOIN-ne-change-rien",
    fichier="mesure/instance.py",
    avant="ENTRAINEMENT_3J = GameConfig(",
    apres="# Temoin du test de mutation : cette ligne ne change aucun comportement.\n"
    "ENTRAINEMENT_3J = GameConfig(",
    vise=(
        "RIEN -- c'est le temoin negatif. La suite doit rester VERTE sous cette mutation ; "
        "si elle rougit, un test reagit a l'edition d'un fichier et non a un changement de "
        "comportement, et il se deguiserait en detection sur toutes les lignes a la fois."
    ),
)


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        nom="espions-adverses-visibles",
        fichier="courtisans/infoset.py",
        avant=(
            "        if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:\n"
            "            dos.append(posee)\n"
            "        else:\n"
            "            connues.append(posee)"
        ),
        apres=(
            "        connues.append(posee)\n"
            "        if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:\n"
            "            dos.append(posee)"
        ),
        vise="l'identite des Espions adverses fuite dans l'encodage (invariant I7)",
    ),
    Mutation(
        nom="phase-et-assassin-absents",
        fichier="courtisans/infoset.py",
        avant=(
            '        Bloc("phase", _phase_one_hot(etat)),\n'
            '        Bloc("assassin", _assassin_one_hot(assassin, joueur, config)),\n'
        ),
        apres="",
        vise="deux poses differentes donnent le meme tenseur avec des cibles differentes",
    ),
    Mutation(
        nom="residu-compte-les-morts",
        fichier="courtisans/infoset.py",
        avant=(
            "                - compte_main[(famille, role)]\n"
            "                - compte_morts[(famille, role)]\n"
            "            )"
        ),
        apres="                - compte_main[(famille, role)]\n            )",
        vise="le residu surestime ce qui circule encore (regle 2 du paragraphe 4.2)",
    ),
    Mutation(
        nom="meurtre-obligatoire",
        fichier="courtisans/engine.py",
        avant="        return list(range(len(self.cibles_courantes()) + 1))",
        apres=(
            "        cibles = self.cibles_courantes()\n"
            "        return list(range(len(cibles) + 1)) if not cibles else list(\n"
            "            range(len(cibles))\n"
            "        )"
        ),
        vise="le refus de tuer disparait quand une cible existe (regle R2, test C5)",
    ),
    Mutation(
        nom="fin-joueur-par-joueur",
        fichier="courtisans/engine.py",
        avant=(
            "        self._joueur = (self._joueur + 1) % self.config.joueurs\n"
            "        if self._joueur == 0:\n"
            "            self._tours_joues += 1\n"
            "            if not rules.peut_entamer_un_tour_de_table(\n"
            "                len(self._pioche), self.config.joueurs\n"
            "            ):"
        ),
        apres=(
            "        self._joueur = (self._joueur + 1) % self.config.joueurs\n"
            "        if True:\n"
            "            self._tours_joues += 1 if self._joueur == 0 else 0\n"
            "            if len(self._pioche) < 3:"
        ),
        vise="la fin de partie est testee joueur par joueur, donc les tours sont inegaux",
    ),
    Mutation(
        nom="noble-vaut-un",
        fichier="courtisans/cards.py",
        avant="        Role.NOBLE: 2,",
        apres="        Role.NOBLE: 1,",
        vise="l'influence se compte en cartes et non en valeur (arbitrage Q1)",
    ),
    Mutation(
        nom="points-au-poseur",
        fichier="courtisans/rules.py",
        avant="        totaux[posee.zone.proprietaire] += int(statut) * posee.carte.valeur",
        apres="        totaux[posee.poseur] += int(statut) * posee.carte.valeur",
        vise="les points vont au poseur et non au proprietaire du domaine (test C11)",
    ),
    Mutation(
        nom="morts-comptes-au-decompte",
        fichier="courtisans/engine.py",
        avant="        statuts = rules.statuts(self._posees, self.config.familles)",
        apres=(
            "        statuts = rules.statuts(\n"
            "            self._posees + self._defausse, self.config.familles\n"
            "        )"
        ),
        vise="une carte tuee compte encore dans l'influence (test C9, invariant I6)",
    ),
    Mutation(
        nom="main-non-triee",
        fichier="courtisans/rules.py",
        avant="    return tuple(sorted(cartes))",
        apres="    return tuple(cartes)",
        vise="l'ordre canonique de la main disparait, une action ne designe plus la meme carte",
    ),
    Mutation(
        nom="doublons-non-masques",
        fichier="courtisans/rules.py",
        avant="        representantes.setdefault(contenu, action)",
        apres="        representantes[(contenu, action)] = action",
        vise="deux actions legales posent les memes cartes aux memes endroits (test C14)",
    ),
    # ---------------------------------------------------------------------------------
    # Ajoutees le 17/08, une par defaut trouve par l'audit de la phase 0. Chacune remet
    # exactement le defaut tel qu'il etait : si elle survit, le correctif n'est tenu par
    # aucun test et il repartira au prochain refactoring.
    # ---------------------------------------------------------------------------------
    Mutation(
        nom="observation-sans-joueur",
        fichier="courtisans/engine.py",
        avant="        if not 0 <= player < self.config.joueurs:",
        apres="        if False:",
        vise=(
            "un identifiant reserve passe pour un joueur : observation bien formee qui "
            "n'est la vue de personne (defaut 2 de l'audit)"
        ),
    ),
    Mutation(
        nom="observateur-absent",
        fichier="courtisans/openspiel_adapter.py",
        avant="    def make_py_observer(",
        apres="    def _observateur_desactive(",
        vise=(
            "le harnais de validite d'OpenSpiel ne peut plus tourner (defaut 1 de l'audit)"
        ),
    ),
    Mutation(
        nom="libelle-de-cible-ambigu",
        fichier="courtisans/openspiel_adapter.py",
        avant=(
            '            f"tuer le {_ordinal(self._etat.rang_public_de_cible(cible))} "\n'
            '            f"{_apparence(cible.carte)} {_situation(cible.zone)}"'
        ),
        apres=(
            '            f"tuer le "\n'
            '            f"{_apparence(cible.carte)} {_situation(cible.zone)}"'
        ),
        vise=(
            "deux cibles de meme apparence dans une meme zone portent le meme nom, ce "
            "qu'OpenSpiel interdit (defaut 7, trouve par random_sim_test)"
        ),
    ),
    Mutation(
        nom="libelle-nomme-un-dos",
        fichier="courtisans/openspiel_adapter.py",
        avant=(
            "    apparence = apparence_publique(carte)\n"
            "    if apparence is None:\n"
            "        return LIBELLE_DU_DOS\n"
            "    famille, role = apparence"
        ),
        apres=(
            "    apparence = (carte.famille, carte.role)\n"
            "    famille, role = apparence"
        ),
        vise=(
            "le libelle d'une cible nomme la famille et le role d'une carte posee face "
            "cachee, que le joueur qui choisit ne connait pas (arbitrage du 17/08 ; "
            "l'invariant I7 ne couvre pas action_to_string)"
        ),
    ),
    Mutation(
        nom="bornes-de-joueurs-desynchronisees",
        fichier="courtisans/openspiel_adapter.py",
        avant="        max_num_players=max(JOUEURS_AUTORISES),",
        apres="        max_num_players=5,",
        vise=(
            "les bornes declarees a OpenSpiel ne sont plus celles que GameConfig accepte "
            "(defaut 5 de l'audit)"
        ),
    ),
    Mutation(
        nom="player-obligatoire",
        fichier="courtisans/openspiel_adapter.py",
        avant="    def information_state_string(self, player: int | None = None) -> str:",
        apres="    def information_state_string(self, player: int) -> str:",
        vise=(
            "l'appel sans argument leve sur un noeud de decision valide, ce qui casse les "
            "34 appels de la bibliotheque dont policy.py:309 (defaut R1, ma faute)"
        ),
    ),
    Mutation(
        nom="chaine-de-jeu-sans-config",
        fichier="courtisans/openspiel_adapter.py",
        avant=(
            "            _type_de_jeu(), _info_de_jeu(self.config), "
            "parametres_depuis_config(self.config)"
        ),
        apres="            _type_de_jeu(), _info_de_jeu(self.config), params or {}",
        vise=(
            "`str(jeu)` perd la configuration, donc `load_game(str(jeu))` rend un autre "
            "jeu sans rien lever (defaut R2)"
        ),
    ),
    Mutation(
        nom="roles-separes-par-virgule",
        fichier="courtisans/openspiel_adapter.py",
        avant='SEPARATEUR_ROLES = "-"',
        apres='SEPARATEUR_ROLES = ","',
        vise=(
            "la chaine du jeu n'est plus relisible par la grammaire d'OpenSpiel, qui "
            "decoupe les parametres sur la virgule (defaut R2)"
        ),
    ),
    Mutation(
        nom="tours-arrondis-au-dessus",
        fichier="courtisans/config.py",
        avant="        return self.nb_cartes // (CARTES_PAR_TOUR * self.joueurs)",
        apres="        return -(-self.nb_cartes // (CARTES_PAR_TOUR * self.joueurs))",
        vise=(
            "le paragraphe 3.4 est lu `ceil` la ou il ecrit `floor` : 8 tours a 4 joueurs "
            "au lieu de 7 (defaut 6 de l'audit)"
        ),
    ),
    # ---------------------------------------------------------------------------------
    # Ajoutee le 20/08, avec la fermeture de l'obstacle A de la phase 3.
    #
    # Elle ne remet pas « une validation absente » : elle remet le **contournement d'une
    # parade existante**. `observation-sans-joueur` ci-dessus casse le controle lui-meme,
    # dans `engine.py` ; celle-ci le laisse intact et fait simplement en sorte que
    # `vue_du_joueur` ne l'appelle plus -- exactement l'etat du depot avant le 20/08, et
    # exactement la facon dont le defaut 2 de la phase 0 est revenu.
    #
    # Les deux sont necessaires et aucune ne remplace l'autre : un correctif qui
    # reecrirait le controle dans `infoset` au lieu de l'appeler survivrait a celle-ci et
    # tomberait sur l'autre, et un correctif qui appelle la parade sans qu'aucun test ne
    # l'exerce survivrait a celle-ci seule.
    # ---------------------------------------------------------------------------------
    Mutation(
        nom="vue-du-joueur-contourne-la-parade",
        fichier="courtisans/infoset.py",
        avant="    etat._joueur_observe(joueur)\n    vue = etat.vue_privilegiee()",
        apres="    vue = etat.vue_privilegiee()",
        vise=(
            "`vue_du_joueur` n'appelle plus la parade de la phase 0 : `tenseur(etat, -1)` "
            "-- or JOUEUR_HASARD vaut -1 -- rend 205 flottants qui ne sont le tenseur "
            "d'aucun siege, et rien ne leve (obstacle A de la phase 3, reouverture du "
            "defaut 2 de l'audit de la phase 0)"
        ),
    ),
    # ---------------------------------------------------------------------------------
    # Ajoutees le 23/08, ouverture de la phase 4 : **le perimetre s'etend a `agents/` et
    # `mesure/`**, paragraphe 0.3 du protocole, elargi le 21/08.
    #
    # Pourquoi. Les vingt mutations ci-dessus ciblent toutes `courtisans/`. « 20 mutations,
    # toutes detectees » ne disait donc RIEN des ~2 500 lignes qui **entrainent** et qui
    # **mesurent** -- et le defaut le plus instructif de la phase 2, un facteur trois indu
    # dans six budgets qui a survecu a DEUX verifications reussies, vivait dans le
    # GENERATEUR, pas dans le moteur.
    #
    # `agents/greedy.py` reste EXEMPT, et c'est le seul invariant que la regle protegeait :
    # c'est l'etalon de toutes les phases, un agent de reference se documente au lieu de se
    # corriger, et une mutation qui le change changerait la ligne de base a laquelle tout le
    # reste se compare. `_greedy_est_exempt` ci-dessous le tient, plutot que ce commentaire.
    #
    # Chaque mutation vise un **invariant ecrit** -- une docstring qui promet quelque chose,
    # un arbitrage du protocole, ou un defaut deja paye. Aucune ne deplace un hyperparametre
    # de plan : changer `TAUX_APPRENTISSAGE` ne serait pas une faute, seulement un autre run.
    # ---------------------------------------------------------------------------------
    Mutation(
        nom='perception-nomme-les-dos',
        fichier='agents/perception.py',
        avant='                    carte=cible.carte if connue else None,',
        apres='                    carte=cible.carte,',
        vise=(
            "la redaction disparait : l'identite d'un dos adverse entre dans la Perception, "
            'donc dans ce que le decideur recoit'
        ),
    ),
    Mutation(
        nom='perception-decide-sur-un-noeud-de-chance',
        fichier='agents/perception.py',
        avant=(
            '    if etat.phase() in (Phase.TERMINAL, Phase.CHANCE):\n'
            '        raise ValueError('
        ),
        apres=(
            '    if False:\n'
            '        raise ValueError('
        ),
        vise=(
            'un agent appele sur un noeud de chance ou terminal recoit une Perception au lieu '
            "d'une levee"
        ),
    ),
    Mutation(
        nom='masque-laisse-une-probabilite-aux-illegales',
        fichier='agents/reseau.py',
        avant='    return torch.softmax(logits.masked_fill(~plan, float("-inf")), dim=-1)',
        apres='    return torch.softmax(logits.masked_fill(~plan, -30.0), dim=-1)',
        vise=(
            'une action illegale garde une probabilite tres petite mais NON NULLE : elle est '
            'tiree un coup sur un million, tres loin de la cause'
        ),
    ),
    Mutation(
        nom='tirer-ne-verifie-plus-la-somme',
        fichier='agents/reseau.py',
        avant='    if not math.isfinite(total) or abs(total - 1.0) > 1e-6:',
        apres='    if False:',
        vise=(
            'une loi qui ne somme pas a 1 -- masque mal applique -- est tiree quand meme et '
            'rend un indice sans signification'
        ),
    ),
    Mutation(
        nom='valeur-non-aplatie',
        fichier='agents/reseau.py',
        avant='        return self.tete_politique(cache), self.tete_valeur(cache).squeeze(-1)',
        apres='        return self.tete_politique(cache), self.tete_valeur(cache)',
        vise=(
            'la tete de valeur rend (n, 1) au lieu de (n,) : la MSE contre des retours (n,) '
            'diffuse en matrice n x n sans rien lever'
        ),
    ),
    Mutation(
        nom='deterministe-ignore-le-masque',
        fichier='agents/reseau.py',
        avant='    return int(torch.argmax(loi[0]).item())',
        apres='    return int(torch.argmax(logits.cpu()[0]).item())',
        vise=(
            "la variante deterministe prend l'argmax des logits BRUTS : elle peut rendre une "
            'action illegale'
        ),
    ),
    Mutation(
        nom='politique-reseau-observe-le-siege-zero',
        fichier='agents/politique_reseau.py',
        avant=(
            '        observation = tenseur(etat, etat.current_player())\n'
            '        actions = etat.legal_actions()'
        ),
        apres=(
            '        observation = tenseur(etat, 0)\n'
            '        actions = etat.legal_actions()'
        ),
        vise=(
            "l'agent decide sur le tenseur du siege 0 quel que soit le siege qu'il occupe -- "
            "il voit la main d'un autre"
        ),
    ),
    Mutation(
        nom='charger-laisse-le-reseau-en-entrainement',
        fichier='agents/politique_reseau.py',
        avant='    modele.eval()\n    return modele',
        apres='    return modele',
        vise=(
            'un checkpoint relu reste en mode entrainement : il mesurerait autre chose que ce '
            "qu'il a appris"
        ),
    ),
    Mutation(
        nom='gain-du-siege-zero',
        fichier='agents/entrainement.py',
        avant='                trajectoires.gains[noeud] = gains[siege]',
        apres='                trajectoires.gains[noeud] = gains[0]',
        vise=(
            'chaque noeud porte le gain du siege 0 et non celui du siege qui decidait : '
            "l'agent apprend le retour de quelqu'un d'autre"
        ),
    ),
    Mutation(
        nom='noeuds-du-pool-collectes',
        fichier='agents/entrainement.py',
        avant=(
            '                if decideur is None:\n'
            '                    # **Seuls les n'
        ),
        apres=(
            '                if True:\n'
            '                    # **Seuls les n'
        ),
        vise=(
            'les noeuds joues par un checkpoint fige entrent dans la mise a jour : PPO '
            'devient hors-politique sans que le ratio le sache'
        ),
    ),
    Mutation(
        nom='avantage-sans-ligne-de-base',
        fichier='agents/entrainement.py',
        avant=(
            '    avantages = retours - torch.tensor(\n'
            '        trajectoires.valeurs, dtype=torch.float32, device=appareil\n'
            '    )'
        ),
        apres=(
            '    avantages = retours - 0.0 * torch.tensor(\n'
            '        trajectoires.valeurs, dtype=torch.float32, device=appareil\n'
            '    )'
        ),
        vise=(
            "la tete de valeur ne sert plus de ligne de base a l'avantage : le critique "
            "n'entre plus dans le gradient de politique"
        ),
    ),
    Mutation(
        nom='alea-de-partie-partage',
        fichier='agents/entrainement.py',
        avant='                alea=random.Random(DECALAGE_TIRAGE + donne),',
        apres='                alea=random.Random(DECALAGE_TIRAGE),',
        vise=(
            "toutes les parties d'une vague partagent un generateur : une partie depend de "
            "celles qui l'accompagnent, et rien n'est rejouable a l'unite"
        ),
    ),
    Mutation(
        nom='composition-toujours-self-play',
        fichier='agents/entrainement.py',
        avant='        if alea.random() >= PART_SELF_PLAY:',
        apres='        if False:',
        vise=(
            "le pool fige n'est jamais joue : l'entrainement est du self-play pur et le "
            "garde-fou contre l'effondrement de convention disparait"
        ),
    ),
    Mutation(
        nom='tete-plus-grande-que-l-espace-d-action',
        fichier='agents/entrainement.py',
        avant='    nb_actions = 6 * 2 * (CONFIG.joueurs - 1)',
        apres='    nb_actions = 6 * 2 * CONFIG.joueurs',
        vise=(
            "la tete du reseau ne fait plus la taille de l'espace d'action du moteur, et le "
            'controle `max(legal_actions) >= nb_actions` ne mord pas'
        ),
    ),
    Mutation(
        nom='garde-fou-de-portee-un',
        fichier='agents/campagne.py',
        avant='PORTEE_DU_GARDE_FOU = 3',
        apres='PORTEE_DU_GARDE_FOU = 1',
        vise=(
            "le garde-fou cherche un progres plus petit que l'ecart detectable a son budget : "
            "il se declenche quoi que fasse l'agent"
        ),
    ),
    Mutation(
        nom='garde-fou-se-contente-d-un-ecart-etabli',
        fichier='agents/campagne.py',
        avant='            declenche = not apparie.progres_etabli',
        apres='            declenche = not apparie.etabli',
        vise=(
            'le defaut v5 : un EFFONDREMENT etabli rassure le garde-fou au lieu de le '
            'declencher'
        ),
    ),
    Mutation(
        nom='garde-fou-sans-bonferroni',
        fichier='agents/campagne.py',
        avant='    risque_corrige = 0.01 / CHECKPOINTS_ATTENDUS',
        apres='    risque_corrige = 0.01',
        vise='huit regards au risque nominal de 1 % : le risque global monte a ~8 %',
    ),
    Mutation(
        nom='pool-garde-les-plus-anciens',
        fichier='agents/campagne.py',
        avant='            del pool[0]',
        apres='            del pool[-1]',
        vise=(
            'le plafond du pool jette le checkpoint le plus RECENT : le pool se remplit des '
            'versions les plus faibles'
        ),
    ),
    Mutation(
        nom='intitule-du-garde-fou-sans-population',
        fichier='agents/campagne.py',
        avant=(
            '    return (\n'
            '        f"1 agent entraine AU CHECKPOINT contre 2 aleatoires, '
            '{donnes} donnes, seeds "\n'
            '        f"{DEPART_DONNE_GARDE_FOU}+ (garde-fou)"\n'
            '    )'
        ),
        apres='    return "1 agent entraine contre 2 aleatoires (garde-fou)"',
        vise=(
            "retour du defaut 5 : le nom ne porte plus ni l'agent, ni les donnes, ni les "
            'seeds, et deux campagnes distinctes redeviennent homonymes'
        ),
    ),
    Mutation(
        nom='garde-fou-se-compare-a-lui-meme',
        fichier='agents/campagne.py',
        avant='PREMIER_CHECKPOINT_QUI_DECLENCHE = PORTEE_DU_GARDE_FOU + 1',
        apres='PREMIER_CHECKPOINT_QUI_DECLENCHE = PORTEE_DU_GARDE_FOU',
        vise=(
            'au checkpoint `PORTEE`, `jalons[numero - PORTEE - 1]` vaut `jalons[-1]` : le '
            'garde-fou compare le checkpoint a LUI-MEME, ecart nul, declenchement certain'
        ),
    ),
    Mutation(
        nom='progres-etabli-redevient-etabli',
        fichier='mesure/bootstrap.py',
        avant=(
            '        return self.intervalle[0] > 0.0\n'
            ''
        ),
        apres=(
            '        return self.intervalle[0] > 0.0 or self.intervalle[1] < 0.0\n'
            ''
        ),
        vise=(
            'le defaut v5 remis AU SITE UNIQUE : `progres_etabli` ne distingue plus un '
            "progres d'un effondrement"
        ),
    ),
    Mutation(
        nom='percentiles-apparies-unilateraux',
        fichier='mesure/bootstrap.py',
        avant=(
            '    bas = int(risque / 2 * repetitions)\n'
            '    haut = min(repetitions - 1, int((1 - risque / 2) * repetitions))\n'
            '    return EcartApparie('
        ),
        apres=(
            '    bas = int(risque * repetitions)\n'
            '    haut = min(repetitions - 1, int((1 - risque) * repetitions))\n'
            '    return EcartApparie('
        ),
        vise=(
            "l'intervalle de l'ecart apparie devient unilateral a chaque bout tout en "
            "s'annoncant a 99 % : il est trop etroit, et le garde-fou declenche moins"
        ),
    ),
    Mutation(
        nom='rho-sur-des-groupes-inegaux',
        fichier='mesure/bootstrap.py',
        avant='    if len(tailles) != 1:',
        apres='    if False:',
        vise=(
            'le rapport intraclasse est calcule sur des donnes de tailles differentes, ce que '
            'sa formule ne permet pas, et il rend un nombre sans le signaler'
        ),
    ),
    Mutation(
        nom='appariement-par-rang-de-valeur',
        fichier='mesure/bootstrap.py',
        avant='    differences = [b - a for a, b in zip(avant, apres, strict=True)]',
        apres=(
            '    differences = [b - a for a, b in zip(sorted(avant), sorted(apres), strict=True)]'
        ),
        vise=(
            "l'appariement est detruit : chaque donne est comparee a une AUTRE donne, et "
            "l'ecart apparie perd tout son sens en gardant sa forme"
        ),
    ),
    Mutation(
        nom='masse-binomiale-part-de-zero',
        fichier='mesure/binomiale.py',
        avant='    mode = min(n, max(0, int((n + 1) * p)))',
        apres='    mode = 0',
        vise=(
            'la recurrence part de k = 0 : pour n = 10 000 le premier terme vaut 1e-1760, '
            'donc zero en flottant, et toute la loi se normalise a partir de rien'
        ),
    ),
    Mutation(
        nom='clopper-pearson-borne-basse-unilaterale',
        fichier='mesure/binomiale.py',
        avant='queue_superieure(k, n, p) - alpha / 2)',
        apres='queue_superieure(k, n, p) - alpha)',
        vise=(
            "la borne basse est prise a `alpha` et non `alpha/2` : l'intervalle n'est plus "
            "bilateral alors que son intitule l'annonce"
        ),
    ),
    Mutation(
        nom='r2-devient-r0',
        fichier='mesure/retournement.py',
        avant=(
            '        avant is not Statut.INDIFFERENTE and avant is not apres'
            ' for avant, apres in transitions\n    )'
        ),
        apres=(
            '        avant is not apres'
            ' for avant, apres in transitions\n    )'
        ),
        vise=(
            "R2 -- perte d'acquis -- compte aussi les departs d'Indifference : il devient R0, "
            "et l'inclusion R2 sous R0 devient une egalite"
        ),
    ),
    Mutation(
        nom='r3-ignore-le-statut-final',
        fichier='mesure/retournement.py',
        avant='    r3 = bool(signes) and suite[-1] is not signes[0]',
        apres='    r3 = bool(signes) and signes[-1] is not signes[0]',
        vise=(
            'R3 -- divergence finale -- compare au dernier statut NON indifferent : une '
            "famille qui finit Indifferente n'est plus vue comme divergente"
        ),
    ),
    Mutation(
        nom='vue-d-un-siege-voit-tous-les-espions',
        fichier='mesure/partie.py',
        avant='        return self.joueur is not None and posee.poseur == self.joueur',
        apres='        return self.joueur is not None',
        vise=(
            "la vue d'un siege compte les Espions ADVERSES poses face cachee : elle devient "
            "la vue de dieu et l'ecart vrai/vu s'annule"
        ),
    ),
    Mutation(
        nom='part-fractionnee-ne-somme-plus-a-un',
        fichier='mesure/phase2.py',
        avant='    return [1 / vainqueurs if score == meilleur else 0.0 for score in scores]',
        apres='    return [1.0 if score == meilleur else 0.0 for score in scores]',
        vise=(
            'la part fractionnee donne 1 a chaque ex aequo : elle ne somme plus a 1 par '
            "partie, et son niveau neutre de 33,3333 % cesse d'etre exact"
        ),
    ),
    Mutation(
        nom='quantile-sans-bonferroni',
        fichier='mesure/dimensionnement.py',
        avant='    return _NORMALE.inv_cdf(1 - risque / comparaisons / 2)',
        apres='    return _NORMALE.inv_cdf(1 - risque / 2)',
        vise=(
            'la correction de Bonferroni est ignoree : `comparaisons` est recu, verifie, et '
            'jamais utilise'
        ),
    ),
    Mutation(
        nom='sieges-non-permutes',
        fichier='mesure/phase3.py',
        avant=(
            '        for siege in range(CONFIG.joueurs):\n'
            '            politiques: list[Politique] = []'
        ),
        apres=(
            '        for siege in [0] * CONFIG.joueurs:\n'
            '            politiques: list[Politique] = []'
        ),
        vise=(
            "l'agent occupe TOUJOURS le siege 0 : les trois replicats ne permutent plus rien, "
            "et le niveau nul cesse d'etre exact alors que l'avantage de siege est massif"
        ),
    ),
    Mutation(
        nom='adversaires-partagent-un-alea',
        fichier='mesure/phase3.py',
        avant=(
            '                        + CONFIG.joueurs * siege\n'
            '                        + place\n'
            '                    )'
        ),
        apres=(
            '                        + CONFIG.joueurs * siege\n'
            '                    )'
        ),
        vise=(
            'les deux adversaires partagent un generateur : ils jouent de facon correlee, ce '
            "qui n'est pas la composition annoncee"
        ),
    ),
    Mutation(
        nom='gain-lu-au-siege-zero',
        fichier='mesure/phase3.py',
        avant=(
            '            [trace.gains[siege] for trace, siege in zip(groupe, sieges, strict=True)]'
        ),
        apres='            [trace.gains[0] for trace, siege in zip(groupe, sieges, strict=True)]',
        vise=(
            "le gain rapporte n'est pas celui du siege de l'agent mais toujours celui du "
            'siege 0'
        ),
    ),
    Mutation(
        nom='separation-exacte-toujours-disjointe',
        fichier='mesure/phase3_mesure.py',
        avant=(
            '        borne_de_l_autre = taux_autre - demi\n'
            '        disjoints = borne_de_l_autre > borne'
        ),
        apres=(
            '        borne_de_l_autre = taux_autre - demi\n'
            '        disjoints = True'
        ),
        vise=(
            'toute ligne portant un zero est declaree separable, meme quand les deux bornes '
            'se croisent'
        ),
    ),
    Mutation(
        nom='b4-strict-avale-le-departage',
        fichier='mesure/comportements.py',
        avant=(
            '            if decision.refus():\n'
            '                refus += 1\n'
            '                if meilleur_meurtre < valeur_refus:'
        ),
        apres=(
            '            if decision.refus():\n'
            '                refus += 1\n'
            '                if meilleur_meurtre <= valeur_refus:'
        ),
        vise=(
            "les refus de DEPARTAGE sont comptes comme des refus STRICTS : l'identite de "
            '`verifier_b4` tient toujours, donc rien ne le signale'
        ),
    ),
    Mutation(
        nom='b4-meurtre-couteux-au-mauvais-denominateur',
        fichier='mesure/comportements.py',
        avant='meurtre_couteux, meurtres, "meurtres"',
        apres='meurtre_couteux, noeuds_avec_cible, "meurtres"',
        vise=(
            'le denominateur de B4-meurtre-couteux devient les noeuds de ciblage et non les '
            'meurtres : le taux publie est divise par ~3'
        ),
    ),
)


def _depot_propre() -> bool:
    sortie = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=RACINE,
        capture_output=True,
        text=True,
        check=True,
    )
    return sortie.stdout.strip() == ""


def _restaurer(fichier: str) -> None:
    subprocess.run(["git", "checkout", "--", fichier], cwd=RACINE, check=True)


def _appliquer(mutation: Mutation) -> None:
    chemin = RACINE / mutation.fichier
    source = chemin.read_text(encoding="utf-8")
    occurrences = source.count(mutation.avant)
    if occurrences != 1:
        raise SystemExit(
            f"mutation {mutation.nom} : le motif apparait {occurrences} fois dans "
            f"{mutation.fichier}, il en faut exactement une. Le code a change : mets la "
            f"mutation a jour plutot que de la contourner."
        )
    chemin.write_text(source.replace(mutation.avant, mutation.apres), encoding="utf-8")


def _jouer(cible: str, delai: float = DELAI_DE_GARDE) -> Passe | None:
    """Rejoue la suite et rend `(verts, rouges)`, ou `None` si le delai de garde expire.

    **Le delai existe parce qu'une mutation l'a exige, et le cas est instructif.**
    `masse-binomiale-part-de-zero` fait partir la recurrence de la loi binomiale de `k = 0`
    au lieu du mode. Pour les `n` de l'ordre de 10 000 que les calculs de puissance
    emploient, le premier terme vaut `1e-1760` -- zero en flottant -- et toute la loi se
    normalise a partir de rien. Un balayage qui cherche le `n` d'une puissance cible ne
    converge alors **jamais**. La suite n'a pas fini : elle a tourne **2 h 48** la ou elle
    prend 169 s, et l'outil l'a attendue sans rien dire.

    **Un blocage n'est ni « detectee » ni « survit », et le confondre avec l'un des deux
    serait faux dans les deux sens.** L'appeler « detectee » compterait comme un succes de la
    suite ce qui est un arret sans verdict ; l'appeler « survit » designerait un trou de test
    qui n'est pas celui-la. C'est un troisieme etat, `EXPIRE`, et il se rapporte comme tel.

    **Et il dit quelque chose de la suite, pas seulement de la mutation** : la suite n'a
    aucun delai de garde propre, donc un blocage y est indiscernable d'une lenteur. C'est
    exactement ce qui a coute presque trois heures ici.
    """
    try:
        sortie = subprocess.run(
            [sys.executable, "-m", "pytest", cible, "-q", "--tb=no", "-p", "no:cacheprovider"],
            cwd=RACINE,
            capture_output=True,
            text=True,
            check=False,
            timeout=delai,
        )
    except subprocess.TimeoutExpired:
        return None
    lignes = [ligne for ligne in sortie.stdout.splitlines() if ligne.strip()]
    if not lignes:
        return None
    derniere = lignes[-1]
    verts = rouges = 0
    valeur = 0
    for morceau in derniere.replace(",", " ").split():
        if morceau.isdigit():
            valeur = int(morceau)
        elif morceau.startswith("passed"):
            verts = valeur
        elif morceau.startswith("failed"):
            rouges = valeur
    tombes = frozenset(
        ligne.split()[1] for ligne in lignes if ligne.startswith("FAILED ")
    )
    return Passe(verts=verts, rouges=rouges, tombes=tombes)


def tombes_sous_TOUTES_les_mutations(
    tombes_par_mutation: Sequence[frozenset[str]],
) -> frozenset[str]:
    """Les tests qui sont tombes sous **chaque** mutation jouee. **Le detecteur de miroir.**

    *Le nom ne commence pas par `test` : pytest collecterait la fonction comme un cas des
    qu'un module de test l'importe, et elle sortirait en erreur de collecte.*

    **Ce que ce controle etablit.** Une mutation change UN comportement. Un test qui tombe
    sous *toutes* les mutations a la fois ne peut pas reagir a ce comportement-la : il reagit
    a autre chose -- le plus souvent au FAIT QU'UN FICHIER A ETE EDITE. Un tel test se deguise
    en detection sur toutes les lignes du releve, efface toutes les survivantes, et **la passe
    de base ne peut pas le voir**, puisqu'il est vert tant qu'aucune mutation n'est en place.

    **Ce n'est pas theorique, et c'est ne dans une correction.** Le 23/08/2026, deux cas de
    `tests/outillage/test_mutation.py` verifiaient les invariants du catalogue en lisant le
    DISQUE. `_appliquer` remplace `avant` par `apres` ; sous mutation, le motif n'est plus la,
    les deux cas tombaient, et la campagne a rendu **56 detectees, 0 survivante** -- exactement
    `+2 rouges` sur chaque ligne, les onze survivantes reelles effacees.

    **Ce que ce controle N'ETABLIT PAS.** Un test qui tombe sous toutes les mutations *peut*
    etre legitime -- un test tres general, qui verifierait par exemple que le depot entier
    reste coherent. Le controle **signale**, il ne condamne pas : c'est a la lecture de
    trancher. Il ne dit rien non plus des tests qui tombent sous *plusieurs* mutations sans
    tomber sous toutes.

    Rend l'ensemble vide s'il n'y a aucune passe, plutot que l'intersection de rien -- qui
    n'est pas definie et que Python rendrait sous forme d'erreur.
    """
    if not tombes_par_mutation:
        return frozenset()
    intersection = set(tombes_par_mutation[0])
    for tombes in tombes_par_mutation[1:]:
        intersection &= tombes
    return frozenset(intersection)


def refus_de_la_passe_de_base(
    verts: int, rouges: int, nb_mutations: int
) -> str | None:
    """Le motif de refus si la passe de base n'est pas verte, ou `None` si elle l'est.

    **Publique et pure, pour qu'un cas puisse l'eprouver.** La regle vivait dans le corps de
    `principal`, qui joue 57 passes de 169 s : personne ne peut la mettre a l'epreuve la ou
    elle est. Une regle qu'aucun cas ne peut exercer est du meme genre que les onze trous que
    cet outil vient de trouver -- et ce serait le comble, ici.

    Ce qu'elle etablit : **un outil qui lit des ecarts refuse de tourner quand son zero n'est
    pas a zero.** Elle ne juge pas la qualite de la suite, elle juge si un ecart y est lisible.
    """
    if rouges:
        return (
            f"la suite NON MUTEE est ROUGE : {rouges} test(s) en echec sur "
            f"{verts + rouges}. **L'outil refuse de commencer.** Il lit des ECARTS contre "
            f"cette passe ; avec un rouge preexistant, les {nb_mutations} mutations "
            f"sortiraient toutes `detectee` -- y compris celles qui ne changent rien -- et le "
            f"releve annoncerait une suite parfaite au moment precis ou elle est cassee. "
            f"Repare la suite, puis relance."
        )
    if verts <= 0:
        return (
            f"la passe de base n'a compte aucun test vert ({verts}). Une cible qui ne "
            f"collecte rien rend `0 vert, 0 rouge`, ce qui passerait pour un zero sain : "
            f"les mutations seraient alors toutes lues contre une suite vide."
        )
    return None


def _passe_de_base(cible: str, delai: float) -> Passe:
    """Joue la suite **non mutee** et rend sa `Passe`. **Le zero de l'instrument.**

    Appelee une fois, en tete de campagne. `principal` leve si `rouges` n'est pas nul : les
    57 verdicts qui suivent sont des ECARTS lus contre ce compte-la, et un ecart ne se lit pas
    contre un zero inconnu.

    **Elle n'attrape pas un rouge de plus.** Elle rend le compte tel quel ; c'est l'appelant
    qui refuse. La distinction compte : une fonction qui leverait ici ne pourrait pas etre
    utilisee pour simplement *rapporter* la ligne de base.

    Raises:
        SystemExit: si la suite non mutee expire. Un zero qu'on ne peut pas mesurer n'est pas
            un zero ; continuer rapporterait 57 ecarts contre rien.
    """
    resultat = _jouer(cible, delai)
    if resultat is None:
        raise SystemExit(
            f"la suite NON MUTEE a expire apres {delai:.0f} s. La ligne de base de l'outil "
            f"n'est pas mesurable, donc aucun des ecarts qui suivraient ne serait lisible."
        )
    return resultat


def principal() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--cible", default="tests", help="selection pytest a rejouer")
    analyseur.add_argument("--nom", default=None, help="ne jouer qu'une mutation")
    analyseur.add_argument(
        "--noms",
        default=None,
        help=(
            "liste de mutations separees par des virgules. **Sert a REPRENDRE** une campagne "
            "interrompue sans rejouer ce qui a deja rendu un verdict : rejouer 44 passes de "
            "169 s pour en obtenir 13 couterait deux heures pour rien."
        ),
    )
    analyseur.add_argument(
        "--delai",
        type=float,
        default=DELAI_DE_GARDE,
        help=f"delai de garde d'une passe, en secondes (defaut {DELAI_DE_GARDE:.0f})",
    )
    arguments = analyseur.parse_args()

    if not _depot_propre():
        raise SystemExit(
            "le depot a des modifications non commitees : l'outil restaure les fichiers "
            "avec git checkout et les detruirait. Commite d'abord."
        )

    vises_exempts = sorted({m.nom for m in MUTATIONS if m.fichier in FICHIERS_EXEMPTS})
    if vises_exempts:
        raise SystemExit(
            f"ces mutations visent un fichier EXEMPT ({', '.join(sorted(FICHIERS_EXEMPTS))}) : "
            f"{', '.join(vises_exempts)}. L'etalon ne porte aucune mutation -- il se documente "
            f"au lieu de se corriger, et le muter deplacerait la ligne de base a laquelle tout "
            f"le reste se compare."
        )

    doublons = sorted({m.nom for m in MUTATIONS if [x.nom for x in MUTATIONS].count(m.nom) > 1})
    if doublons:
        raise SystemExit(f"deux mutations portent le meme nom : {', '.join(doublons)}")

    if arguments.nom and arguments.noms:
        raise SystemExit("--nom et --noms s'excluent : choisir l'un des deux")
    if arguments.noms:
        demandes = [n.strip() for n in arguments.noms.split(",") if n.strip()]
        connus = {m.nom for m in MUTATIONS}
        inconnus = [n for n in demandes if n not in connus]
        if inconnus:
            raise SystemExit(f"mutation(s) inconnue(s) : {', '.join(inconnus)}")
        mutations = [m for m in MUTATIONS if m.nom in set(demandes)]
    else:
        mutations = [m for m in MUTATIONS if arguments.nom in (None, m.nom)]
    if not mutations:
        raise SystemExit(f"aucune mutation nommee {arguments.nom!r}")

    # **Le zero de l'instrument, mesure avant le premier ecart.** Voir la docstring du module :
    # sans cette passe, un seul rouge preexistant fait rapporter « toutes detectees » a une
    # campagne dont les 57 verdicts sont faux.
    base = _passe_de_base(arguments.cible, arguments.delai)
    verts_base, rouges_base = base.verts, base.rouges
    print(
        f"passe de BASE, sans mutation : {verts_base} verts, {rouges_base} rouges "
        f"(cible {arguments.cible!r})"
    )
    refus = refus_de_la_passe_de_base(verts_base, rouges_base, len(mutations))
    if refus is not None:
        raise SystemExit(refus)

    # **Le temoin negatif.** Voir `MUTATION_TEMOIN` : la passe de base ne peut pas voir un
    # test qui reagit a l'EDITION d'un fichier plutot qu'a un changement de comportement,
    # parce qu'un tel test est vert tant qu'aucune mutation n'est en place.
    _appliquer(MUTATION_TEMOIN)
    try:
        temoin = _jouer(arguments.cible, arguments.delai)
    finally:
        _restaurer(MUTATION_TEMOIN.fichier)
    if temoin is None:
        raise SystemExit(
            f"le TEMOIN a expire apres {arguments.delai:.0f} s alors qu'il ne change rien : "
            f"la suite n'est pas stable, aucun ecart n'y est lisible."
        )
    verts_temoin, rouges_temoin = temoin.verts, temoin.rouges
    print(
        f"TEMOIN, mutation qui ne change rien : {verts_temoin} verts, {rouges_temoin} rouges"
    )
    if (verts_temoin, rouges_temoin) != (verts_base, rouges_base):
        raise SystemExit(
            f"le TEMOIN ne rend pas la passe de base : {verts_temoin}/{rouges_temoin} contre "
            f"{verts_base}/{rouges_base}. **Un ou plusieurs tests reagissent a l'EDITION d'un "
            f"fichier et non a un changement de comportement.** Ils tomberaient sous les "
            f"{len(mutations)} mutations a la fois, se deguiseraient en detections, et "
            f"effaceraient toutes les survivantes du releve. C'est exactement ce qui est "
            f"arrive le 23/08/2026 -- voir `MUTATION_TEMOIN`. L'outil refuse de commencer."
        )
    print()

    print(f"{'mutation':40s} {'verts':>6s} {'rouges':>7s}  verdict")
    print("-" * 86)
    survivantes = []
    expirees = []
    tombes_par_mutation: list[frozenset[str]] = []
    for mutation in mutations:
        _appliquer(mutation)
        try:
            resultat = _jouer(arguments.cible, arguments.delai)
        finally:
            _restaurer(mutation.fichier)
        if resultat is None:
            expirees.append(mutation)
            print(
                f"{mutation.nom:40s} {'-':>6s} {'-':>7s}  "
                f"EXPIRE apres {arguments.delai:.0f} s -- la suite ne rend pas la main"
            )
            continue
        verts, rouges = resultat.verts, resultat.rouges
        tombes_par_mutation.append(resultat.tombes)
        verdict = "detectee" if rouges else "SURVIT -- trou de test"
        if not rouges:
            survivantes.append(mutation)
        print(f"{mutation.nom:40s} {verts:6d} {rouges:7d}  {verdict}")

    print("-" * 86)

    # **Le detecteur de miroir.** Une mutation change UN comportement ; un test qui tombe sous
    # TOUTES ne peut pas reagir a celui-la. Voir `tombes_sous_TOUTES_les_mutations` : ce
    # controle est ce qui aurait vu, le 23/08/2026, les deux cas qui ont efface onze
    # survivantes du releve. Il ne coute aucune passe -- les noms sont deja dans la sortie.
    miroirs = tombes_sous_TOUTES_les_mutations(tombes_par_mutation)
    if miroirs and len(tombes_par_mutation) > 1:
        print(
            f"\n!! {len(miroirs)} test(s) sont tombes sous les {len(tombes_par_mutation)} "
            f"mutations jouees. **Un test qui tombe sous toutes ne reagit a aucune** : il "
            f"reagit le plus souvent au fait qu'un fichier a ete edite, il se deguise en "
            f"detection sur toutes les lignes, et il efface les survivantes du releve. "
            f"La passe de base ne peut pas le voir. A LIRE avant de croire ce releve :"
        )
        for nom in sorted(miroirs):
            print(f"  - {nom}")
        print()

    if expirees:
        print(
            f"{len(expirees)} mutation(s) ont fait EXPIRER la suite. **Ce n'est ni une "
            f"detection ni une survie** : la suite n'a rendu aucun verdict, et elle n'a pas de "
            f"delai de garde propre -- un blocage y est indiscernable d'une lenteur."
        )
        for mutation in expirees:
            print(f"  - {mutation.nom} ({mutation.fichier}) : {mutation.vise}")
    if survivantes:
        print(
            f"{len(survivantes)} mutation(s) non detectee(s) sur {len(mutations)}. "
            f"**C'est un RESULTAT, pas un echec de l'outil** : chacune nomme un trou de la "
            f"suite de tests, et se rapporte telle quelle."
        )
        for mutation in survivantes:
            print(f"  - {mutation.nom} ({mutation.fichier}) : {mutation.vise}")
        return 1
    if expirees:
        return 1
    print(
        f"{len(mutations)} mutation(s), toutes detectees -- lues contre une passe de base a "
        f"{verts_base} verts et {rouges_base} rouges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
