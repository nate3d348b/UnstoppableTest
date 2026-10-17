"""Solo Unstoppable-inspired simulation. UI independent, with serializable state.

Every card is data; every moving game card is a Sleeve. The one-player game
flow, drafting, level-up, persistent damage and sleeves are implemented here.
Unsupported bespoke card rules are *rejected*, not silently approximated.
"""
from __future__ import annotations
from dataclasses import asdict
import copy
import random
from typing import Any
from .models import Sleeve, PlayerState, GameState, RuleError
from .catalog import Catalog


def _tuple_tree(value):
    if isinstance(value, list):
        return tuple(_tuple_tree(v) for v in value)
    return value


class GameEngine:
    def __init__(self, catalog: Catalog, state: GameState, rng: random.Random):
        self.catalog, self.state, self.rng = catalog, state, rng

    @classmethod
    def new(cls, catalog: Catalog, *, seed: int = 42, difficulty: str = 'normal') -> 'GameEngine':
        if difficulty not in {'normal', 'hard', 'expert'}:
            raise RuleError('Difficulty must be normal, hard, or expert')
        rng = random.Random(seed)
        state = GameState(seed=seed, difficulty=difficulty, demo_mode=bool(catalog.data.get('demo')))
        state.player.name = catalog.scenario.get('character', 'Demo Pilot')
        game = cls(catalog, state, rng)
        s = catalog.scenario
        for recipe in s['starter_sleeves']:
            for _ in range(int(recipe.get('count', 1))):
                uid = game._new_sleeve(core=recipe['core'], threat=recipe['threat'])
                state.player.deck.append(uid)
        rng.shuffle(state.player.deck)
        for _ in range(min(3, len(state.player.deck))):
            game._move_draw('hand')
        for _ in range(min(3, len(state.player.deck))):
            game._move_draw('battlefield')
        for spec in s.get('reserve_threats', []):
            for _ in range(int(spec.get('count', 1))):
                state.reserve_threats.append(game._new_sleeve(core=None, threat=spec['threat']))
        rng.shuffle(state.reserve_threats)
        state.loose_cores = {str(k): list(v) for k, v in s.get('loose_cores', {}).items()}
        for pile in state.loose_cores.values():
            rng.shuffle(pile)
        state.loose_upgrades = list(s.get('loose_upgrades', []))
        rng.shuffle(state.loose_upgrades)
        game._fill_market()
        for card_id in s.get('boss_cards', []):
            state.boss_deck.append(game._new_sleeve(threat=card_id, boss_only=True))
        rng.shuffle(state.boss_deck)
        state.player.hp = int(s.get('starting_health', 10))
        state.player.credits = int(s.get('starting_credits', 3))
        state.player.armor = 0
        state.player.action_points = 0
        game._log(f"Set up {state.player.name}, {len(state.player.deck)+len(state.player.hand)+len(state.player.battlefield)} starter sleeves.")
        for uid in state.player.battlefield:
            game._reveal(uid)
        if state.player.deck:
            game._reveal(state.player.deck[0])
        game._enqueue(s.get('on_setup', []), source=None)
        state.resume = 'start_upkeep'
        game._run_queue()
        return game

    def _new_sleeve(self, core=None, threat=None, boss_only=False) -> str:
        uid = f"S{self.state.next_uid:04d}"
        self.state.next_uid += 1
        self.state.sleeves[uid] = Sleeve(uid=uid, core_id=core, threat_id=threat, boss_only=boss_only)
        return uid

    def _log(self, message: str) -> None:
        self.state.log.append(f"T{self.state.turn}: {message}")
        self.state.log = self.state.log[-400:]

    def _move_draw(self, zone: str) -> str:
        p = self.state.player
        uid = p.deck.pop(0)
        card = self.state.sleeves[uid]
        card.face = 'core' if zone == 'hand' else 'threat'
        card.damage = 0 if zone == 'hand' else card.damage
        getattr(p, zone).append(uid)
        return uid

    def _fill_market(self) -> None:
        s = self.state
        while len(s.upgrade_market) < 6 and s.loose_upgrades:
            s.upgrade_market.append(s.loose_upgrades.pop(0))

    def _core(self, uid: str) -> dict:
        return self.catalog.card(self.state.sleeves[uid].core_id)

    def _threat(self, uid: str) -> dict:
        return self.catalog.card(self.state.sleeves[uid].threat_id)

    def _name(self, uid: str, *, threat: bool = False) -> str:
        sleeve = self.state.sleeves[uid]
        return self.catalog.name(sleeve.threat_id if threat else sleeve.core_id)

    def _keywords(self, uid: str, keyword: str) -> list[dict]:
        found = []
        for key in self._threat(uid).get('keywords', []):
            k = {'name': key} if isinstance(key, str) else key
            if k.get('name', '').lower() == keyword:
                found.append(k)
        for upgrade_id in self.state.sleeves[uid].upgrades.values():
            for key in self.catalog.card(upgrade_id).get('threat_keywords', []):
                k = {'name': key} if isinstance(key, str) else key
                if k.get('name', '').lower() == keyword:
                    found.append(k)
        return found

    @property
    def danger_value(self) -> int:
        return int(self.catalog.scenario['danger_track'][self.state.danger_index]['value'])

    def threat_stats(self, uid: str) -> tuple[int, int, int]:
        t = self._threat(uid)
        attack = int(t.get('attack', 0))
        defense = int(t.get('defense', 0))
        if t.get('defense_mode') == 'danger':
            defense = self.danger_value
        for upgrade_id in self.state.sleeves[uid].upgrades.values():
            mods = self.catalog.card(upgrade_id).get('threat_modifiers', {})
            attack += int(mods.get('attack', 0))
            defense += int(mods.get('defense', 0))
        return attack, defense, max(0, attack + defense)

    def _reveal(self, uid: str) -> None:
        if uid in self.state.revealed:
            return
        self.state.revealed.append(uid)
        self._log(f"Revealed {self._name(uid, threat=True)} ({uid}).")
        self._enqueue(self._threat(uid).get('effects', {}).get('on_reveal', []), uid, front=True)
        for k in self._keywords(uid, 'crazed'):
            if self.state.player.hp <= int(k.get('value', 0)):
                self._enqueue([{'op': 'damage', 'amount': 2, 'target': uid, 'ignore_taunt': True, 'ignore_terror': True}], uid, front=True)

    def _enqueue(self, effects: list[dict], source: str | None, *, front: bool = False,
                 trigger: str = '') -> None:
        entries = [{'effect': copy.deepcopy(e), 'source': source,
                    'effect_key': f"{source}:{trigger}:{i}" if trigger else ''}
                   for i, e in enumerate(effects)]
        if front:
            self.state.queue = entries + self.state.queue
        else:
            self.state.queue.extend(entries)

    def _queue_trigger(self, uid: str, trigger: str, front: bool = True) -> None:
        sleeve = self.state.sleeves[uid]
        core_or_threat = sleeve.core_id if trigger in {'on_play', 'on_exhaust', 'on_upkeep', 'on_enter_hand'} else sleeve.threat_id
        cards = [core_or_threat]
        if not sleeve.boss_only:
            cards += list(sleeve.upgrades.values())
        effects = []
        for ident in cards:
            if ident:
                effects.extend(self.catalog.card(ident).get('effects', {}).get(trigger, []))
        self._enqueue(effects, uid, front=front, trigger=trigger)

    def _faction_count(self, source: str | None) -> int:
        if not source:
            return 0
        faction = self._core(source).get('faction', 'none')
        if faction in ('none', None, ''):
            return 0
        p = self.state.player
        return sum(self._core(u).get('faction') == faction for u in p.hand + p.allies + p.tactics)

    def _amount(self, spec: Any, source: str | None) -> int:
        if isinstance(spec, int):
            return spec
        if isinstance(spec, dict):
            per = spec.get('per')
            if per == 'focus':
                return int(spec.get('base', 0)) + self._faction_count(source)
            if per == 'unite':
                p = self.state.player
                factions = {self._core(u).get('faction') for u in p.hand + p.allies + p.tactics}
                return int(spec.get('base', 0)) + len(factions - {'none', None, ''})
            if per == 'danger':
                return int(spec.get('base', 0)) + self.danger_value
        raise RuleError(f'Unsupported amount formula: {spec!r}')

    def _legal_targets(self) -> list[str]:
        p = self.state.player
        targets = list(p.battlefield)
        if p.deck:
            targets.append(p.deck[0])
        taunts = [uid for uid in targets if self._keywords(uid, 'taunt')]
        return taunts or targets

    def _damage_threat(self, uid: str, amount: int, *, ignore_taunt: bool = False,
                       ignore_terror: bool = False) -> None:
        if not ignore_taunt and uid not in self._legal_targets():
            raise RuleError('Target is not visible or is blocked by Taunt')
        if not ignore_terror:
            for _ in self._keywords(uid, 'terror'):
                self.state.player.action_points = max(0, self.state.player.action_points - 1)
        s = self.state.sleeves[uid]
        s.damage += max(0, amount)
        self._log(f"{self._name(uid, threat=True)} takes {amount} damage ({s.damage}/{self.threat_stats(uid)[2]}).")
        if s.damage >= self.threat_stats(uid)[2]:
            p = self.state.player
            if uid in p.battlefield:
                p.battlefield.remove(uid)
            elif p.deck and p.deck[0] == uid:
                p.deck.pop(0)
            s.damage = 0
            s.face = 'core'
            if s.core_id is None:
                raise RuleError('Defeated sleeve lacks a core; supply a core before it enters the player deck')
            p.hand.append(uid)
            self._log(f"Defeated {self._name(uid, threat=True)}. Flipped sleeve into hand: {self._name(uid)}.")
            self._queue_trigger(uid, 'on_enter_hand', front=True)
            self._queue_trigger(uid, 'on_defeat', front=True)
            if p.deck:
                self._reveal(p.deck[0])

    def _damage_player(self, amount: int) -> None:
        p = self.state.player
        shield = min(p.armor, amount)
        p.armor -= shield
        p.hp = max(0, p.hp - (amount - shield))
        self._log(f"Took {amount} damage ({shield} blocked); HP {p.hp}, armor {p.armor}.")
        if p.hp <= 0:
            self.state.result = 'defeat'
            self.state.phase = 'game_over'
            self._log('DEFEAT: health reached zero.')

    def _discard_ally(self, uid: str) -> None:
        p = self.state.player
        if uid not in p.allies:
            raise RuleError('Must discard an ally in play')
        p.allies.remove(uid)
        self.state.sleeves[uid].exhausted = False
        p.discard.append(uid)
        self._log(f"Discarded ally {self._name(uid)}.")

    def _eliminate(self, uid: str) -> None:
        p = self.state.player
        for zone in ('hand', 'discard', 'tactics', 'allies'):
            pile = getattr(p, zone)
            if uid in pile:
                pile.remove(uid)
                p.eliminated.append(uid)
                self._log(f"Eliminated {self._name(uid)} ({uid}) permanently.")
                return
        raise RuleError('May only eliminate a card from hand, play, or discard')

    def _apply_effect(self, entry: dict, target: str | None = None) -> bool:
        e, source = entry['effect'], entry.get('source')
        op = e['op']
        p, s = self.state.player, self.state
        if op == '_player_damage_internal':
            self._damage_player(int(e.get('amount', 0)))
            return True
        if op == 'noop':
            return True
        if op == 'conditional':
            condition = e.get('condition', {})
            kind = condition.get('kind')
            passed = (kind == 'level_at_least' and p.level >= int(condition.get('value', 1))) or (kind == 'conspire' and self._faction_count(source) >= 2)
            if passed:
                self._enqueue(e.get('effects', []), source, front=True)
            return True
        if op == 'repeat':
            count = min(20, max(0, self._amount(e.get('times', 1), source)))
            self._enqueue(e.get('effects', []) * count, source, front=True)
            return True
        if op == 'damage':
            amount = max(0, self._amount(e.get('amount', 0), source))
            requested = target or e.get('target', 'choose')
            if requested == 'choose':
                choices = self._legal_targets()
                if not choices:
                    self._log('Damage effect forfeited (no eligible threats).')
                    return True
                s.pending = {'kind': 'target', 'options': choices, 'entry': entry}
                return False
            self._damage_threat(requested, amount, ignore_taunt=bool(e.get('ignore_taunt', False)),
                                ignore_terror=bool(e.get('ignore_terror', False)))
        elif op == 'credits':
            p.credits = max(0, p.credits + self._amount(e.get('amount', 0), source))
        elif op == 'action_points':
            p.action_points = min(6, p.action_points + self._amount(e.get('amount', 0), source))
        elif op == 'health':
            p.hp = max(0, min(10, p.hp + self._amount(e.get('amount', 0), source)))
            if p.hp == 0:
                s.result, s.phase = 'defeat', 'game_over'
        elif op == 'armor':
            p.armor = min(10, p.armor + self._amount(e.get('amount', 0), source))
        elif op == 'train':
            p.draft_level = min(6, p.draft_level + self._amount(e.get('amount', 1), source))
        elif op == 'boss_damage':
            s.boss_damage += self._amount(e.get('amount', 0), source)
            self._log(f"Boss damage: {s.boss_damage}/{self.catalog.scenario.get('boss_goal', 99)}.")
            if s.boss_damage >= self.catalog.scenario.get('boss_goal', 99):
                s.result = 'victory'
                s.phase = 'game_over'
                self._log('VICTORY: Boss objective completed!')
        elif op == 'refresh':
            options = list(p.allies)
            if not options:
                return True
            uid = e.get('target') or (options[0] if len(options) == 1 else None)
            if uid is None:
                s.pending = {'kind': 'refresh', 'options': options}
                return False
            if uid in p.allies:
                s.sleeves[uid].exhausted = False
        elif op == 'discard_ally':
            if p.allies:
                s.pending = {'kind': 'discard_ally', 'options': list(p.allies)}
                return False
        elif op == 'eliminate':
            options = p.hand + p.discard + p.tactics + p.allies
            if options:
                s.pending = {'kind': 'eliminate', 'options': options, 'optional': bool(e.get('optional', False))}
                return False
        elif op == 'market_cycle':
            s.pending = {'kind': 'market_cycle', 'options': list(range(len(s.upgrade_market))), 'optional': True}
            return False
        elif op == 'draw_boss':
            if s.boss_deck:
                uid = s.boss_deck.pop(0)
                s.boss_in_play.append(uid)
                self._log(f"Boss card revealed: {self._name(uid, threat=True)}.")
                self._queue_trigger(uid, 'on_reveal', front=True)
        else:
            raise RuleError(f'Effect handler not implemented: {op}')
        if op not in {'damage', 'boss_damage', 'noop'}:
            self._log(f"Resolved {op} ({e.get('amount', '')}).")
        return True

    def _run_queue(self) -> None:
        count = 0
        s = self.state
        while s.queue and not s.pending and s.result == 'ongoing':
            count += 1
            if count > 1000:
                raise RuleError('Effect queue safety limit reached (possible infinite loop)')
            entry = s.queue.pop(0)
            key = entry.get('effect_key', '')
            if key:
                s.effect_counts[key] = s.effect_counts.get(key, 0) + 1
            completed = self._apply_effect(entry)
            if key and s.effect_counts[key] >= 4 and entry.get('source'):
                uid = entry['source']
                if uid in s.player.hand + s.player.discard + s.player.allies + s.player.tactics:
                    self._eliminate(uid)
                    self._log('Fourth resolution of same card effect: card eliminated.')
            if not completed:
                break
        if not s.pending and not s.queue and s.result == 'ongoing':
            if s.resume == 'after_threat':
                s.resume = ''
                self._cleanup()
            elif s.resume == 'next_turn':
                s.resume = ''
                s.turn += 1
                self._upkeep()
            elif s.resume == 'start_upkeep':
                s.resume = ''
                self._upkeep()
            elif s.resume == 'draft_after_upkeep' and s.phase == 'upkeep':
                s.resume = ''
                self._begin_draft()
            elif s.resume == 'finish_cleanup' and s.phase == 'cleanup':
                s.resume = ''
                self._finish_cleanup()
            elif s.resume == 'resume_cleanup_refill' and s.phase == 'cleanup':
                s.resume = ''
                self._cleanup()
            elif s.phase == 'main' and not s.player.deck and not s.player.battlefield and s.player.discard:
                self._start_level_up('main')

    def _upkeep(self) -> None:
        s, p = self.state, self.state.player
        if s.result != 'ongoing':
            return
        s.phase, s.resume = 'upkeep', ''
        s.effect_counts.clear()
        p.action_points = 3
        for uid in p.allies:
            s.sleeves[uid].exhausted = False
            self._queue_trigger(uid, 'on_upkeep', front=False)
        self._log('Upkeep: 3 AP, allies refreshed.')
        s.resume = 'draft_after_upkeep'
        self._enqueue([], None)
        self._run_queue()
        if not s.pending and s.phase == 'upkeep':
            self._begin_draft()

    def _begin_draft(self) -> None:
        s, p = self.state, self.state.player
        s.phase = 'draft'
        s.resume = ''
        pile = s.loose_cores.get(str(p.draft_level), [])
        n = min(3, len(pile))
        if n == 0 or not s.reserve_threats:
            self._log('Draft skipped: no loose cores at this level or no spare threat sleeves.')
            p.draft_level = p.level
            s.phase = 'main'
            return
        choices = [pile.pop(0) for _ in range(n)]
        s.pending = {'kind': 'draft', 'options': choices, 'level': str(p.draft_level)}
        self._log(f"Draft: choose 1 of {n} loose level-{p.draft_level} cores.")

    def _start_level_up(self, origin: str) -> None:
        s, p = self.state, self.state.player
        if s.phase == 'level_up' or s.result != 'ongoing':
            return
        s.phase, s.resume = 'level_up', f'levelup_to_{origin}'
        p.level += 1
        p.draft_level = min(6, p.draft_level + 1)
        for zone in ('tactics', 'allies'):
            for uid in getattr(p, zone):
                s.sleeves[uid].exhausted = False
                p.discard.append(uid)
            getattr(p, zone).clear()
        self._log(f"LEVEL UP to {p.level}. Cards in play discarded; discard hand down to three.")
        self._level_discard_or_eliminate()

    def _level_discard_or_eliminate(self) -> None:
        s, p = self.state, self.state.player
        if len(p.hand) > 3:
            s.pending = {'kind': 'level_discard', 'options': list(p.hand)}
        else:
            s.pending = {'kind': 'level_eliminate', 'options': list(p.hand + p.discard), 'optional': True}

    def _finish_level_up(self) -> None:
        s, p = self.state, self.state.player
        self._enqueue(self.catalog.scenario.get('on_level_up', []), None, front=True)
        p.deck = list(p.discard)
        p.discard.clear()
        for uid in p.deck:
            s.sleeves[uid].face = 'threat'
            s.sleeves[uid].damage = 0
            s.sleeves[uid].exhausted = False
        self.rng.shuffle(p.deck)
        s.revealed = [uid for uid in s.revealed if uid not in p.deck]
        if p.deck:
            self._reveal(p.deck[0])
        origin = 'cleanup' if s.resume == 'levelup_to_cleanup' else 'main'
        s.resume = ''
        s.phase = origin
        self._log(f'Reshuffled {len(p.deck)} discard cards into threat-side-up deck.')
        if origin == 'cleanup':
            # Level up interrupts refilling; resume refill, not danger advance.
            s.resume = 'resume_cleanup_refill'
        self._run_queue()

    def _threat_phase(self) -> None:
        s = self.state
        s.phase = 'threat'
        self._log('Threat phase begins.')
        # Damage and Rage are sequenced one threat at a time; decisions pause the queue.
        for uid in list(s.player.battlefield):
            for _ in self._keywords(uid, 'rage'):
                self._enqueue([{'op': 'discard_ally'}], uid)
            self._queue_trigger(uid, 'on_threat_phase', front=False)
            self._enqueue([{'op': '_player_damage_internal', 'amount': self.threat_stats(uid)[0]}], uid)
        s.resume = 'after_threat'
        self._run_queue()

    def _cleanup(self) -> None:
        s, p = self.state, self.state.player
        s.phase = 'cleanup'
        for uid in list(p.tactics):
            p.tactics.remove(uid)
            p.discard.append(uid)
        p.action_points = 0
        p.armor = 0
        self._log('Cleanup: tactics discarded, AP and armor reset.')
        safety = 0
        while True:
            safety += 1
            if safety > 120:
                raise RuleError('Cleanup could not refill battlefield; check content data')
            nonfast = sum(1 for uid in p.battlefield if not self._keywords(uid, 'fast'))
            topfast = bool(p.deck and self._keywords(p.deck[0], 'fast'))
            if nonfast >= 3 and not topfast:
                break
            if not p.deck:
                if not p.discard:
                    self._log('No cards to replenish deck; cannot refill battlefield.')
                    break
                self._start_level_up('cleanup')
                return
            uid = self._move_draw('battlefield')
            self._reveal(uid)
            if p.deck:
                self._reveal(p.deck[0])
            self._run_queue()
            if s.pending or s.result != 'ongoing':
                if s.result == 'ongoing':
                    s.resume = 'resume_cleanup_refill'
                return
        self._run_queue()
        if s.pending or s.result != 'ongoing':
            if s.result == 'ongoing':
                s.resume = 'finish_cleanup'
            return
        self._finish_cleanup()

    def _finish_cleanup(self) -> None:
        s = self.state
        self._advance_danger()
        if s.result != 'ongoing':
            return
        s.resume = 'next_turn'
        self._run_queue()
        if not s.pending and not s.queue and s.phase == 'cleanup':
            s.resume = ''
            s.turn += 1
            self._upkeep()

    def _advance_danger(self) -> None:
        s = self.state
        track = self.catalog.scenario['danger_track']
        new_idx = s.danger_index + 1
        while new_idx < len(track) and s.difficulty in track[new_idx].get('skip_for', []):
            new_idx += 1
        s.danger_index = min(new_idx, len(track) - 1)
        self._log(f"Danger advanced to space {s.danger_index} (value {self.danger_value}).")
        if s.danger_index >= len(track) - 1:
            s.result, s.phase = 'defeat', 'game_over'
            self._log('DEFEAT: danger reached its maximum space.')
            return
        self._enqueue(track[s.danger_index].get('effects', []), None)

    def _get_upgrade_cost(self, upgrade_id: str, target: str) -> int:
        upgrade = self.catalog.card(upgrade_id)
        cost = int(upgrade.get('cost', 0))
        discount = upgrade.get('discount', {})
        if discount.get('faction') == self._core(target).get('faction'):
            cost -= int(discount.get('amount', 0))
        return max(0, cost)

    def _validate_move(self, action: str, **args: Any) -> None:
        s, p = self.state, self.state.player
        if s.result != 'ongoing':
            raise RuleError('The game is over')
        if s.pending:
            if action != 'choose':
                raise RuleError('Resolve the pending decision first')
            return
        if action == 'choose':
            raise RuleError('There is no pending decision')
        if s.phase != 'main':
            raise RuleError(f'Action unavailable during {s.phase}')
        if action == 'end_main':
            return
        uid = args.get('uid')
        if action == 'play':
            if uid not in p.hand:
                raise RuleError('Card is not in hand')
            if p.action_points < max(0, int(self._core(uid).get('cost', 0)) +
                                      sum(int(self.catalog.card(c).get('core_modifiers', {}).get('cost', 0)) for c in s.sleeves[uid].upgrades.values())):
                raise RuleError('Not enough action points')
        elif action == 'exhaust':
            if uid not in p.allies or s.sleeves[uid].exhausted:
                raise RuleError('Ally must be in play and ready')
        elif action == 'buy':
            i = args.get('market_index')
            if not isinstance(i, int) or i < 0 or i >= len(s.upgrade_market):
                raise RuleError('Invalid market index')
            if uid not in p.hand + p.tactics + p.allies:
                raise RuleError('Upgrade target must be in hand or in play')
            u = self.catalog.card(s.upgrade_market[i])
            if u['slot'] in s.sleeves[uid].upgrades:
                raise RuleError('That sleeve upgrade slot is already occupied')
            need = u.get('requires', 'either')
            if need not in ('either', self._core(uid).get('type')):
                raise RuleError(f'Upgrade requires {need} core')
            if p.credits < self._get_upgrade_cost(u['id'], uid):
                raise RuleError('Not enough credits')
        else:
            raise RuleError(f'Unknown action {action}')

    def act(self, action: str, **args: Any) -> None:
        """Validated, atomic user action. Raises RuleError without changing state."""
        snapshot, rng_snapshot = copy.deepcopy(self.state), self.rng.getstate()
        try:
            self._validate_move(action, **args)
            s, p = self.state, self.state.player
            if action == 'choose':
                self._choose(args.get('selection'))
            elif action == 'play':
                uid = args['uid']
                cost = max(0, int(self._core(uid).get('cost', 0)) +
                           sum(int(self.catalog.card(c).get('core_modifiers', {}).get('cost', 0)) for c in s.sleeves[uid].upgrades.values()))
                p.action_points -= cost
                p.hand.remove(uid)
                destination = 'allies' if self._core(uid)['type'] == 'ally' else 'tactics'
                getattr(p, destination).append(uid)
                s.sleeves[uid].exhausted = False
                self._log(f"Played {self._name(uid)} for {cost} AP.")
                self._queue_trigger(uid, 'on_play')
                self._run_queue()
            elif action == 'exhaust':
                uid = args['uid']
                s.sleeves[uid].exhausted = True
                self._log(f"Exhausted ally {self._name(uid)}.")
                self._queue_trigger(uid, 'on_exhaust')
                self._run_queue()
            elif action == 'buy':
                uid, i = args['uid'], args['market_index']
                upgrade_id = s.upgrade_market.pop(i)
                u = self.catalog.card(upgrade_id)
                cost = self._get_upgrade_cost(upgrade_id, uid)
                p.credits -= cost
                s.sleeves[uid].upgrades[u['slot']] = upgrade_id
                self._fill_market()
                self._log(f"Installed {u['name']} in {u['slot']} of {self._name(uid)} for {cost} credits.")
            elif action == 'end_main':
                self._threat_phase()
        except Exception:
            self.state = snapshot
            self.rng.setstate(rng_snapshot)
            raise

    def _choose(self, selection: Any) -> None:
        s, p = self.state, self.state.player
        pending = s.pending
        if pending is None:
            raise RuleError('Nothing to choose')
        kind = pending['kind']
        options = pending.get('options', [])
        if selection == '__skip__' and pending.get('optional'):
            pass
        elif kind in {'draft', 'market_cycle'}:
            if not isinstance(selection, int) or selection not in range(len(options)):
                raise RuleError('Pick a valid option index')
        elif selection not in options:
            raise RuleError('Choose an available card or explicit Skip')
        s.pending = None
        if kind == 'draft':
            chosen_core = options[selection]
            for i, ident in enumerate(options):
                if i != selection:
                    s.loose_cores[pending['level']].append(ident)
            threat_uid = s.reserve_threats.pop(0)
            sleeve = s.sleeves[threat_uid]
            sleeve.core_id, sleeve.face = chosen_core, 'core'
            p.hand.append(threat_uid)
            p.draft_level = min(6, p.level)
            s.phase = 'main'
            self._log(f"Drafted {self.catalog.name(chosen_core)} into threat-only sleeve {threat_uid} (back remains hidden).")
            self._queue_trigger(threat_uid, 'on_enter_hand')
        elif kind == 'target':
            self._apply_effect(pending['entry'], target=selection)
        elif kind == 'discard_ally':
            self._discard_ally(selection)
        elif kind == 'refresh':
            s.sleeves[selection].exhausted = False
        elif kind == 'eliminate' and selection != '__skip__':
            self._eliminate(selection)
        elif kind == 'market_cycle':
            if selection != '__skip__':
                ident = s.upgrade_market.pop(selection)
                s.loose_upgrades.append(ident)
                self._fill_market()
                s.pending = {'kind': 'market_cycle', 'options': list(range(len(s.upgrade_market))), 'optional': True}
                return
        elif kind == 'level_discard':
            p.hand.remove(selection)
            p.discard.append(selection)
            self._level_discard_or_eliminate()
            return
        elif kind == 'level_eliminate':
            if selection != '__skip__':
                self._eliminate(selection)
            self._finish_level_up()
            return
        self._run_queue()
        if not s.pending and not s.queue and s.result == 'ongoing':
            if s.phase == 'upkeep' and s.resume == 'draft_after_upkeep':
                self._begin_draft()
            elif s.phase == 'cleanup' and s.resume == 'finish_cleanup':
                s.resume = ''
                self._finish_cleanup()

    def export_save(self) -> dict:
        return {'format': 'unstoppable-web-save-v1', 'catalog': self.catalog.data,
                'state': asdict(self.state), 'rng_state': self.rng.getstate()}

    @classmethod
    def from_save(cls, data: dict) -> 'GameEngine':
        if data.get('format') != 'unstoppable-web-save-v1':
            raise RuleError('Not an Unstoppable Web v1 save file')
        catalog = Catalog(data['catalog'])
        d = data['state']
        player = PlayerState(**d['player'])
        sleeves = {uid: Sleeve(**contents) for uid, contents in d['sleeves'].items()}
        state = GameState(**{**d, 'player': player, 'sleeves': sleeves})
        rng = random.Random()
        rng.setstate(_tuple_tree(data['rng_state']))
        return cls(catalog, state, rng)
