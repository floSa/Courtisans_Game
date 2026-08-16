# Départ propre — mode d'emploi

**Copie le contenu de ce dossier dans ton nouveau dépôt vide, et rien d'autre.**

```
nouveau_depot/
├── PILOTE.md              ← commence ici, c'est le seul document qui te parle
├── LISEZMOI.md            ← ce fichier, tu peux le supprimer après lecture
├── documentations/        ← le corpus de référence, pour toi et pour les agents
└── prompts/               ← les prompts à coller dans des conversations neuves
```

Aucun code. C'est délibéré : une conversation neuve qui trouverait l'ancien code irait
le lire et hériterait de ses défauts.

---

## Les trois choses à faire dans l'ordre

**1. Répondre aux deux dernières questions de règles** — §11 de
[documentations/01_regles.md](documentations/01_regles.md). Elles bloquent tout le reste.

**2. Créer le dépôt** : nouveau dossier, `git init`, nouvelle branche, copier ces fichiers,
premier commit.

**3. Coller** [prompts/01_moteur_construction.md](prompts/01_moteur_construction.md) dans
une conversation neuve.

Le détail de chaque action est dans [PILOTE.md](PILOTE.md).

---

## Ce qu'il faut savoir sur les documents

**`01_regles.md` fait seule autorité sur les règles.** Tout le reste en découle. Si tu ne
relis qu'un document, c'est celui-là — et relis-le en entier, parce qu'une règle mal rédigée
là ne sera rattrapée par aucun audit en aval.

**`02_audit_conformite.md` parle de l'ancien dépôt.** Il explique pourquoi on repart de zéro,
avec les mesures qui le justifient. Il cite des fichiers qui n'existent pas dans ce nouveau
dépôt — c'est normal, c'est un document historique. Les agents doivent le lire pour
comprendre les erreurs à ne pas refaire, pas pour aller chercher le code.

**`05_protocole_experimental.md` est le document le moins à jour.** Il a été écrit quand le
plan visait encore 2 joueurs avec un oracle exact. Depuis, la cible est 3 joueurs et le juge
est le greedy en parties appariées. À réécrire après la phase moteur, quand on saura ce
qu'on a.

---

## Les deux fichiers de code à récupérer séparément

Pas maintenant — quand la phase d'entraînement arrivera, et seulement à ce moment-là :

| Fichier | Pourquoi |
|---|---|
| `app/greedy_bot.py` | l'agent le plus fort jamais mesuré ; sert de **juge**, pas de base de code |
| `cfr/solve_mini.py` | l'infrastructure d'oracle CFR+ avec checkpoint |

Les récupérer plus tôt reviendrait à réintroduire l'ancien code dans le nouveau dépôt.

---

## Ce qui a été corrigé le 16/08, et qui explique la méthode

Deux auditeurs indépendants ont relu les règles et le vecteur d'état sans voir le
raisonnement qui les avait produits. Ils ont trouvé onze défauts dans les règles dont six
bloquants, et six dans le vecteur dont deux qui rendaient une phase du jeu injouable.

Trois de ces défauts étaient des **règles inventées** : un retrait de cartes selon le nombre
de joueurs, une main de six cartes, et un comptage faux — chacun présenté avec une
justification cohérente qui les rendait crédibles à la lecture.

C'est pour ça que le protocole impose : deux conversations par phase, l'auditeur ne voit
jamais le raisonnement du constructeur, il écrit ses tests hostiles **avant** de lire le
code, et il recalcule chaque chiffre au lieu de le lire.
