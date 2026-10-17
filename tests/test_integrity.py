"""Regression tests for sleeve uniqueness and rejected actions.

Run with: python -m unittest discover -s tests -v
"""
from __future__ import annotations

from pathlib import Path
import json
import unittest

from unstoppable import GameEngine, RuleError, load_catalog

DEMO_CATALOG = Path(__file__).resolve().parents[1] / "data" / "demo_cards.json"


class SleeveIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(DEMO_CATALOG)

    def assert_valid_zones(self, game: GameEngine) -> None:
        s, p = game.state, game.state.player
        player_zones = (
            p.deck, p.hand, p.battlefield, p.tactics, p.allies,
            p.discard, p.eliminated,
        )
        other_zones = (
            s.reserve_threats, s.boss_deck, s.boss_in_play, s.boss_discard,
        )
        all_uids = [uid for zone in (*player_zones, *other_zones) for uid in zone]
        self.assertEqual(
            len(all_uids), len(set(all_uids)),
            "A sleeve is present in more than one zone",
        )
        self.assertEqual(set(all_uids), set(s.sleeves), "A sleeve is missing from all zones")

        for uid in p.hand + p.tactics + p.allies + p.discard + p.eliminated:
            self.assertIsNotNone(s.sleeves[uid].core_id, f"{uid} has no core in a player zone")
        for uid in p.deck + p.battlefield:
            self.assertIsNotNone(s.sleeves[uid].threat_id, f"{uid} has no threat face")
        for uid in s.reserve_threats:
            self.assertIsNone(s.sleeves[uid].core_id, f"{uid} is no longer threat-only")

    def test_initial_setup_and_first_draft_keep_each_sleeve_in_one_zone(self):
        for seed in range(12):
            with self.subTest(seed=seed):
                game = GameEngine.new(self.catalog, seed=seed)
                self.assert_valid_zones(game)
                self.assertEqual(game.state.pending["kind"], "draft")
                game.act("choose", selection=0)
                self.assert_valid_zones(game)

    def test_subsequent_turns_preserve_sleeve_zones(self):
        game = GameEngine.new(self.catalog, seed=19)
        for _ in range(20):
            self.assert_valid_zones(game)
            if game.state.result != "ongoing":
                break
            decision = game.state.pending
            if decision:
                kind = decision["kind"]
                selection = "__skip__" if decision.get("optional") else (
                    0 if kind == "draft" else decision["options"][0]
                )
                game.act("choose", selection=selection)
            elif game.state.phase == "main":
                game.act("end_main")
            else:
                self.fail(f"No action available during {game.state.phase}")
        self.assert_valid_zones(game)

    def test_rejected_action_does_not_change_state_or_randomness(self):
        game = GameEngine.new(self.catalog, seed=42)
        game.act("choose", selection=0)
        before = json.dumps(game.export_save(), sort_keys=True)
        with self.assertRaises(RuleError):
            game.act("play", uid="not-a-sleeve")
        self.assertEqual(json.dumps(game.export_save(), sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
