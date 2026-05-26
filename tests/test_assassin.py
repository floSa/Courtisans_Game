"""Tests ciblés sur la logique des assassins."""

from app.jeu import Carte, GameEnv, Role


def _make_carte(env: GameEnv, famille: int, role: int) -> Carte:
    return env.cartes[famille * 5 + role]


def test_assassin_targets_same_queen_zone() -> None:
    env = GameEnv(2, seed=42)
    # Construire un assassin "Reine Estime" et une cible compatible.
    assassin = _make_carte(env, 0, Role.ASSASSIN)
    assassin.position = "Estime"
    assassin.domaine_id = -1

    victim = _make_carte(env, 1, Role.NOBLE)
    victim.position = "Estime"
    victim.domaine_id = -1
    env.plateau_indices.append(victim.id)

    # Une carte en zone Disgrace ne doit pas être ciblée
    safe = _make_carte(env, 2, Role.NOBLE)
    safe.position = "Disgrace"
    safe.domaine_id = -1
    env.plateau_indices.append(safe.id)

    targets = env._get_valid_assassin_targets(assassin)
    assert victim.id in targets
    assert safe.id not in targets


def test_assassin_does_not_target_guards() -> None:
    """Seuls les Gardes sont immunisés contre les assassinats."""
    env = GameEnv(2, seed=42)
    assassin = _make_carte(env, 0, Role.ASSASSIN)
    assassin.position = "Estime"

    garde = _make_carte(env, 1, Role.GARDE)
    garde.position = "Estime"
    garde.domaine_id = -1
    env.plateau_indices.append(garde.id)

    targets = env._get_valid_assassin_targets(assassin)
    assert garde.id not in targets


def test_assassin_can_target_another_assassin() -> None:
    """Règle officielle : un assassin peut tuer un autre assassin (seul le
    Garde est immunisé)."""
    env = GameEnv(2, seed=42)
    assassin = _make_carte(env, 0, Role.ASSASSIN)
    assassin.position = "Estime"

    other_ass = _make_carte(env, 2, Role.ASSASSIN)
    other_ass.position = "Estime"
    other_ass.domaine_id = -1
    env.plateau_indices.append(other_ass.id)

    targets = env._get_valid_assassin_targets(assassin)
    assert other_ass.id in targets


def test_assassin_does_not_target_itself() -> None:
    """Un assassin ne se cible jamais lui-même, même si la zone match."""
    env = GameEnv(2, seed=42)
    assassin = _make_carte(env, 0, Role.ASSASSIN)
    assassin.position = "Estime"
    env.plateau_indices.append(assassin.id)
    targets = env._get_valid_assassin_targets(assassin)
    assert assassin.id not in targets


def test_assassin_targets_same_domain() -> None:
    env = GameEnv(2, seed=42)
    assassin = _make_carte(env, 0, Role.ASSASSIN)
    assassin.position = None
    assassin.domaine_id = 1

    victim = _make_carte(env, 1, Role.NOBLE)
    victim.position = None
    victim.domaine_id = 1
    env.plateau_indices.append(victim.id)

    other = _make_carte(env, 2, Role.NOBLE)
    other.position = None
    other.domaine_id = 0
    env.plateau_indices.append(other.id)

    targets = env._get_valid_assassin_targets(assassin)
    assert victim.id in targets
    assert other.id not in targets
