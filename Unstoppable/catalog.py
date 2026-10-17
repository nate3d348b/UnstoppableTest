"""Schema checks for user-provided card and scenario JSON.

Definitions are immutable data. A physical copy is identified by a Sleeve uid
or an index in a loose pile; duplicate printed cards are allowed.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .models import CatalogError

SUPPORTED_OPS = {
    'damage', 'credits', 'action_points', 'health', 'armor', 'train',
    'boss_damage', 'refresh', 'discard_ally', 'eliminate', 'noop',
    'conditional', 'repeat', 'market_cycle', 'draw_boss',
}
SUPPORTED_TRIGGERS = {
    'on_play', 'on_exhaust', 'on_defeat', 'on_reveal', 'on_upkeep',
    'on_threat_phase', 'on_enter_hand',
}
KINDS = {'core', 'threat', 'upgrade', 'boss'}


def _effects(effects: Any, where: str) -> None:
    if not isinstance(effects, list):
        raise CatalogError(f'{where}: effects must be a list')
    for e in effects:
        if not isinstance(e, dict) or e.get('op') not in SUPPORTED_OPS:
            raise CatalogError(f'{where}: unknown effect {e!r}; add an interpreter first')
        for field in ('amount', 'times'):
            if isinstance(e.get(field), dict) and e[field].get('per') not in {'focus', 'unite', 'danger'}:
                raise CatalogError(f'{where}: unsupported {field} expression {e[field]!r}')
        if e['op'] == 'conditional':
            if e.get('condition', {}).get('kind') not in {'level_at_least', 'conspire'}:
                raise CatalogError(f'{where}: unsupported condition {e.get("condition")!r}')
            _effects(e.get('effects', []), where + '/conditional')
        if e['op'] == 'repeat':
            _effects(e.get('effects', []), where + '/repeat')


class Catalog:
    def __init__(self, data: dict[str, Any]):
        if not isinstance(data, dict) or 'cards' not in data or 'scenario' not in data:
            raise CatalogError('Expected {"cards": [...], "scenario": {...}}')
        self.data = data
        self.cards: dict[str, dict] = {}
        for c in data['cards']:
            if not isinstance(c, dict) or not all(k in c for k in ('id', 'kind', 'name')):
                raise CatalogError('Every card requires id, kind, name')
            if c['kind'] not in KINDS or c['id'] in self.cards:
                raise CatalogError(f"Invalid kind or duplicate id: {c['id']}")
            if c['kind'] == 'core' and c.get('type') not in ('tactic', 'ally'):
                raise CatalogError(f"Core {c['id']} requires type tactic or ally")
            if c['kind'] == 'upgrade' and c.get('slot') not in ('top', 'bottom'):
                raise CatalogError(f"Upgrade {c['id']} must have slot top/bottom")
            if c['kind'] == 'threat' and (c.get('attack', 0) < 0 or c.get('defense', 0) < 0):
                raise CatalogError(f"Threat {c['id']}: negative stats")
            for trigger, effects in c.get('effects', {}).items():
                if trigger not in SUPPORTED_TRIGGERS:
                    raise CatalogError(f"Unknown trigger {trigger} on {c['id']}")
                _effects(effects, f"{c['id']}/{trigger}")
            self.cards[c['id']] = c
        self.scenario = data['scenario']
        s = self.scenario
        if not s.get('starter_sleeves') or not s.get('danger_track'):
            raise CatalogError('Scenario must define starter_sleeves and danger_track')
        for spec in s['starter_sleeves']:
            self._assert_ref(spec['core'], 'core')
            self._assert_ref(spec['threat'], 'threat')
            if int(spec.get('count', 1)) < 1:
                raise CatalogError('Starter sleeve count must be positive')
        for spec in s.get('reserve_threats', []):
            self._assert_ref(spec['threat'], 'threat')
        for level, ids in s.get('loose_cores', {}).items():
            if not str(level).isdigit():
                raise CatalogError('Loose core levels must be numeric')
            for ident in ids:
                self._assert_ref(ident, 'core')
        for ident in s.get('loose_upgrades', []):
            self._assert_ref(ident, 'upgrade')
        for ident in s.get('boss_cards', []):
            self._assert_ref(ident, 'boss')
        for space in s['danger_track']:
            if not isinstance(space, dict) or 'value' not in space:
                raise CatalogError('Each danger track space requires value')
            _effects(space.get('effects', []), 'danger_track')
        _effects(s.get('on_setup', []), 'scenario/on_setup')
        _effects(s.get('on_level_up', []), 'scenario/on_level_up')

    def _assert_ref(self, ident: str, kind: str) -> None:
        if ident not in self.cards or self.cards[ident]['kind'] != kind:
            raise CatalogError(f'{ident!r} must reference a {kind} card')

    def card(self, ident: str | None) -> dict:
        if not ident:
            return {}
        try:
            return self.cards[ident]
        except KeyError as e:
            raise CatalogError(f'Missing card ID {ident!r}') from e

    def name(self, ident: str | None) -> str:
        return self.card(ident).get('name', 'Empty side')


def load_catalog(path: str | Path) -> Catalog:
    return Catalog(json.loads(Path(path).read_text(encoding='utf-8')))
