"""Run with: python -m unittest discover -s tests -v"""
from pathlib import Path
import copy
import json
import unittest

from unstoppable import load_catalog, GameEngine, Catalog, CatalogError, RuleError

DEMO = Path(__file__).resolve().parents[1] / 'data' / 'demo_cards.json'


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(DEMO)
        self.engine = GameEngine.new(self.catalog, seed=42)

    def main(self):
        self.engine.act('choose', selection=0)
        self.assertEqual(self.engine.state.phase, 'main')

    def test_no_sleeve_in_two_zones(self):
        self.main()
        s=self.engine.state
        p=s.player
        all_zones = p.deck+p.hand+p.battlefield+p.tactics+p.allies+p.discard+p.eliminated+s.reserve_threats+s.boss_deck+s.boss_in_play+s.boss_discard
        self.assertEqual(len(all_zones), len(set(all_zones)))
        self.assertEqual(set(all_zones), set(s.sleeves))

    def test_five_sides_of_content(self):
        self.assertEqual(len(self.engine.state.player.hand), 3)
        self.assertEqual(len(self.engine.state.player.battlefield), 3)
        self.assertEqual(len(self.engine.state.player.deck), 4)
        self.assertEqual(len(self.engine.state.reserve_threats), 38)
        self.assertEqual(len(self.engine.state.upgrade_market), 6)

    def test_persistent_sleeve_and_loose_draft(self):
        p = self.engine.state.player
        count = len(self.engine.state.reserve_threats)
        picked_id = self.engine.state.pending['options'][0]
        self.main()
        uid = p.hand[-1]
        self.assertEqual(self.engine.state.sleeves[uid].core_id, picked_id)
        self.assertIsNotNone(self.engine.state.sleeves[uid].threat_id)
        self.assertEqual(self.engine.state.sleeves[uid].face, 'core')
        self.assertEqual(len(self.engine.state.reserve_threats), count - 1)

    def test_draft_does_not_expose_threat_back(self):
        self.assertEqual(self.engine.state.pending['kind'], 'draft')
        self.assertTrue(all(self.catalog.card(i)['kind']=='core' for i in self.engine.state.pending['options']))

    def test_play_and_target_selection(self):
        self.main()
        p = self.engine.state.player
        uid = next(u for u in p.hand if self.catalog.card(self.engine.state.sleeves[u].core_id)['type'] == 'tactic')
        old_ap = p.action_points
        self.engine.act('play', uid=uid)
        self.assertIn(uid, p.tactics)
        self.assertLessEqual(p.action_points, old_ap)
        if self.engine.state.pending:
            self.assertEqual(self.engine.state.pending['kind'], 'target')
            self.engine.act('choose', selection=self.engine.state.pending['options'][0])

    def test_invalid_choice_is_atomic(self):
        before = json.dumps(self.engine.export_save(), sort_keys=True)
        with self.assertRaises(RuleError):
            self.engine.act('choose', selection=999)
        self.assertEqual(json.dumps(self.engine.export_save(), sort_keys=True), before)

    def test_cannot_play_during_draft(self):
        with self.assertRaises(RuleError):
            self.engine.act('play', uid=self.engine.state.player.hand[0])

    def test_damage_turns_threat_into_hand_core(self):
        self.main()
        s = self.engine.state
        uid = next((u for u in s.player.battlefield if not self.engine._keywords(u, 'taunt')), s.player.battlefield[0])
        # Use a legal target if a Taunt exists.
        uid = self.engine._legal_targets()[0]
        core = s.sleeves[uid].core_id
        self.engine._damage_threat(uid, self.engine.threat_stats(uid)[2])
        self.assertIn(uid, s.player.hand)
        self.assertEqual(s.sleeves[uid].core_id, core)
        self.assertEqual(s.sleeves[uid].face, 'core')
        self.assertEqual(s.sleeves[uid].damage, 0)

    def test_threat_phase_and_cleanup(self):
        self.main()
        before = self.engine.state.player.hp
        self.engine.act('end_main')
        self.assertLess(self.engine.state.player.hp, before)
        self.assertEqual(self.engine.state.player.armor, 0)
        self.assertEqual(self.engine.state.turn, 2)
        self.assertEqual(self.engine.state.phase, 'draft')

    def test_market_purchase_persists_on_sleeve(self):
        self.main()
        s = self.engine.state
        s.player.credits = 20
        uid = next(u for u in s.player.hand if self.engine._core(u)['type']=='tactic')
        index = next(i for i, ident in enumerate(s.upgrade_market) if self.catalog.card(ident).get('requires','either') in ('either','tactic'))
        upgrade = s.upgrade_market[index]
        slot = self.catalog.card(upgrade)['slot']
        self.engine.act('buy', uid=uid, market_index=index)
        self.assertEqual(s.sleeves[uid].upgrades[slot], upgrade)
        self.assertEqual(len(s.upgrade_market), 6)

    def test_double_upgrade_slot_rejected(self):
        self.main()
        s=self.engine.state
        s.player.credits=99
        uid=next(u for u in s.player.hand if self.engine._core(u)['type']=='tactic')
        for idx,u in enumerate(s.upgrade_market):
            if self.catalog.card(u)['slot']=='top' and self.catalog.card(u).get('requires','either') in ('either','tactic'):
                self.engine.act('buy',market_index=idx,uid=uid)
                break
        else: self.skipTest('No matching market upgrade')
        for idx,u in enumerate(s.upgrade_market):
            if self.catalog.card(u)['slot']=='top':
                with self.assertRaises(RuleError):
                    self.engine.act('buy',market_index=idx,uid=uid)
                break

    def test_save_round_trip_rng(self):
        self.main()
        saved = json.loads(json.dumps(self.engine.export_save()))
        restored = GameEngine.from_save(saved)
        self.assertEqual(restored.export_save(), self.engine.export_save())
        self.engine.act('end_main')
        restored.act('end_main')
        self.assertEqual(restored.export_save(), self.engine.export_save())

    def test_reject_undefined_effects(self):
        data=copy.deepcopy(self.catalog.data)
        data['cards'][0]['effects']['on_play']=[{'op':'make_everything_free'}]
        with self.assertRaises(CatalogError):
            Catalog(data)

    def test_taunt_restricts_targets(self):
        self.main()
        s=self.engine.state
        front=s.player.battlefield[0]
        self.catalog.cards[s.sleeves[front].threat_id].setdefault('keywords',[]).append('taunt')
        allowed = self.engine._legal_targets()
        self.assertTrue(all(self.engine._keywords(uid,'taunt') for uid in allowed))

    def test_level_up_discards_plays_to_deck(self):
        self.main()
        s=self.engine.state
        s.player.deck.clear()
        s.player.battlefield.clear()
        s.player.discard = list(s.player.hand[:1])
        s.player.hand = s.player.hand[1:]
        self.engine._start_level_up('main')
        self.assertEqual(s.phase,'level_up')
        if s.pending['kind']=='level_discard':
            self.fail('Unexpected level discard decision')
        self.engine.act('choose',selection='__skip__')
        self.assertEqual(s.player.level,2)
        self.assertEqual(len(s.player.deck),1)
        self.assertEqual(s.sleeves[s.player.deck[0]].face,'threat')

    def test_cleanup_levelup_resumes_refill_once(self):
        self.main()
        e=self.engine
        s=e.state
        p=s.player
        old_deck=list(p.deck)
        old_battlefield=list(p.battlefield)
        p.deck.clear()
        p.battlefield.clear()
        p.discard.extend(old_deck+old_battlefield)
        e.act('end_main')
        self.assertEqual(s.phase,'level_up')
        for _ in range(10):
            if not s.pending or s.pending['kind']=='draft': break
            kind=s.pending['kind']
            if kind=='level_discard':
                e.act('choose',selection=s.pending['options'][0])
            elif kind=='level_eliminate':
                e.act('choose',selection='__skip__')
            else:
                self.fail(f'Unanticipated level-up decision: {kind}')
        self.assertEqual(s.turn,2)
        self.assertEqual(s.phase,'draft')
        self.assertGreaterEqual(len(p.battlefield),3)
        self.assertEqual(s.danger_index,1)
        self.assertEqual(p.level,2)
        self.assertEqual(len(p.deck)+len(p.battlefield)+len(p.hand)+len(p.discard),11) # 10 starters + drafted card

    def test_scenario_setup_effect_queue_before_draft(self):
        data=copy.deepcopy(self.catalog.data)
        data['scenario']['on_setup']=[{'op':'draw_boss'}]
        engine=GameEngine.new(Catalog(data),seed=42)
        self.assertEqual(len(engine.state.boss_in_play),1)
        self.assertEqual(engine.state.player.armor,1)
        self.assertEqual(engine.state.pending['kind'],'draft')

    def test_crazed_self_damage_ignores_taunt(self):
        self.main()
        e=self.engine
        s=e.state
        p=s.player
        p.hp=4
        target=p.battlefield[0]
        e.catalog.cards[s.sleeves[target].threat_id]['keywords']=[{'name':'crazed','value':5}]
        other=p.battlefield[-1]
        self.assertNotEqual(s.sleeves[target].threat_id,s.sleeves[other].threat_id)
        e.catalog.cards[s.sleeves[other].threat_id]['keywords']=['taunt']
        s.revealed.remove(target)
        e._reveal(target)
        e._run_queue()
        self.assertEqual(s.sleeves[target].damage,2 if target in p.battlefield else 0)

    def test_simulated_game_terminates_or_survives_25_rounds(self):
        engine=GameEngine.new(self.catalog,seed=19)
        for _ in range(500):
            if engine.state.result != 'ongoing' or engine.state.turn>25:
                break
            if engine.state.pending:
                d=engine.state.pending
                kind=d['kind']
                selection='__skip__' if kind in ('level_eliminate','market_cycle') else (0 if kind=='draft' else d['options'][0])
                engine.act('choose',selection=selection)
            elif engine.state.phase=='main':
                p=engine.state.player
                playable=[uid for uid in p.hand if engine._core(uid).get('cost',0)<=p.action_points]
                if playable:
                    engine.act('play',uid=playable[0])
                else:
                    engine.act('end_main')
            else:
                self.fail(f'Engine stuck in phase {engine.state.phase} without decision')
        self.assertTrue(engine.state.result!='ongoing' or engine.state.turn>25)
        self.assertLessEqual(engine.state.player.hp,10)


if __name__=='__main__':
    unittest.main()
