"""Serialisable objects. The sleeve is the unit that moves between zones."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Sleeve:
    uid: str
    core_id: str | None = None
    threat_id: str | None = None
    upgrades: dict[str, str] = field(default_factory=dict)
    damage: int = 0
    exhausted: bool = False
    face: str = "threat"
    boss_only: bool = False


@dataclass
class PlayerState:
    name: str = "Demo Pilot"
    hp: int = 10
    armor: int = 0
    credits: int = 3
    action_points: int = 3
    level: int = 1
    draft_level: int = 1
    deck: list[str] = field(default_factory=list)
    hand: list[str] = field(default_factory=list)
    battlefield: list[str] = field(default_factory=list)
    tactics: list[str] = field(default_factory=list)
    allies: list[str] = field(default_factory=list)
    discard: list[str] = field(default_factory=list)
    eliminated: list[str] = field(default_factory=list)


@dataclass
class GameState:
    player: PlayerState = field(default_factory=PlayerState)
    sleeves: dict[str, Sleeve] = field(default_factory=dict)
    loose_cores: dict[str, list[str]] = field(default_factory=dict)
    loose_upgrades: list[str] = field(default_factory=list)
    upgrade_market: list[str] = field(default_factory=list)
    reserve_threats: list[str] = field(default_factory=list)
    boss_deck: list[str] = field(default_factory=list)
    boss_in_play: list[str] = field(default_factory=list)
    boss_discard: list[str] = field(default_factory=list)
    boss_damage: int = 0
    danger_index: int = 0
    phase: str = "upkeep"
    turn: int = 1
    result: str = "ongoing"
    pending: dict[str, Any] | None = None
    queue: list[dict[str, Any]] = field(default_factory=list)
    resume: str = ""
    log: list[str] = field(default_factory=list)
    revealed: list[str] = field(default_factory=list)
    effect_counts: dict[str, int] = field(default_factory=dict)
    next_uid: int = 1
    seed: int = 0
    difficulty: str = "normal"
    demo_mode: bool = False


class RuleError(ValueError):
    """An attempted command is illegal in the current game state."""


class CatalogError(ValueError):
    """The supplied content JSON is invalid or unsupported."""
