# Content data format (v1)

`data/demo_cards.json` is a functioning example. It has two top-level elements: `cards`, an array of printed card **definitions**, and `scenario`, a setup recipe. IDs are strings; human-facing names may be edited freely.

## Card definitions

A tactic **core** (a loose card, until placed in a sleeve):

```json
{
  "id": "core_001", "kind": "core", "name": "Example Tactic",
  "type": "tactic", "level": 1, "faction": "junker", "cost": 1,
  "effects": {"on_play": [{"op": "damage", "amount": 2, "target": "choose"}]}
}
```

An ally core has `"type":"ally"`, often with `"effects":{"on_exhaust":[...]}`. Cards can define multiple triggers.

A **threat** (to be the hidden reverse of a core):

```json
{
  "id": "threat_001", "kind": "threat", "name": "Example Threat",
  "attack": 1, "defense": 2,
  "keywords": [{"name": "crazed", "value": 5}, "taunt"],
  "effects": {"on_defeat": [{"op": "credits", "amount": 1}]}
}
```

Threat health is `attack + defense`. For danger-dependent defense, use `"defense_mode":"danger"`. Damage persists in a particular sleeve until defeat.

An **upgrade** is initially an unsleeved card, later installed **between** a core and its threat. Its core modifier may *help* you, and its threat modifier may *hurt* you.

```json
{
  "id": "upgrade_001", "kind": "upgrade", "name": "Example Upgrade",
  "slot": "top", "requires": "tactic", "cost": 2,
  "discount": {"faction": "junker", "amount": 1},
  "core_modifiers": {"cost": -1},
  "threat_modifiers": {"attack": 1, "defense": 0},
  "effects": {"on_play": [{"op": "credits", "amount": 1}]}
}
```

Allowed slots are `top` and `bottom`; each sleeve holds at most one of each. The requirement is `tactic`, `ally` or `either`.

A boss-only card is `{"id":"boss_card_01","kind":"boss","name":"...","effects":{...}}` and remains outside the player's normal sleeve/deck cycle.

## A scenario recipe

```json
{
  "name": "Example Boss", "character": "Example Hero",
  "boss_goal": 4, "starting_health": 10, "starting_credits": 3,
  "starter_sleeves": [
    {"core": "core_001", "threat": "threat_001", "count": 6},
    {"core": "core_002", "threat": "threat_002", "count": 4}
  ],
  "reserve_threats": [
    {"threat": "threat_001", "count": 20}
  ],
  "loose_cores": {
    "1": ["core_001", "core_001", "core_003"],
    "2": ["core_004"]
  },
  "loose_upgrades": ["upgrade_001", "upgrade_001"],
  "boss_cards": ["boss_card_01"],
  "danger_track": [
    {"value": 0},
    {"value": 1, "skip_for": ["normal"]},
    {"value": 2, "effects": [{"op": "market_cycle"}]},
    {"value": 3}
  ],
  "on_setup": [{"op":"draw_boss"}],
  "on_level_up": []
}
```

**Important physical distinction:** `starter_sleeves` contains **pre-paired physical sleeves**, `reserve_threats` creates **threat-only sleeves waiting for a core**, `loose_cores` holds **unsleeved cores sorted by level**, and `loose_upgrades` is the **unsleeved upgrade deck**. An entry appearing 3 times in a loose array is three printed physical copies, not one mutable definition. `count` makes multiple pre-sleeved copies. A sleeve gets a unique runtime ID such as `S0008`. No upgrades are assumed to be pre-installed, but the sleeve model can hold both slots.

## Effects DSL

Each printed card has `"effects": {"on_play": [...], "on_exhaust": [...], "on_defeat": [...], ...}`. Implemented trigger names:

- Card triggers: `on_play`, `on_exhaust`, `on_defeat`, `on_reveal`, `on_upkeep` (allies), `on_threat_phase` (threats), `on_enter_hand`. Scenario hooks: `scenario.on_setup`, `scenario.on_level_up` (effect arrays). Card-level `on_level_up` / `on_cleanup` are not yet interpreted and are rejected until added.

Operators currently recognized:

| `op` | Data | Behavior |
|---|---|---|
| `damage` | `amount`, `target: "choose"` | Damage one visible threat or on-deck threat, with prompt and Taunt restriction |
| `credits` | `amount` | Gain/spend credits (negative supported) |
| `action_points` | `amount` | Gain/spend AP, cap 6 |
| `health` | `amount` | Heal / change HP, cap 10 |
| `armor` | `amount` | Armor, cap 10 |
| `train` | `amount` | Temporarily advance small level disc, cap 6 |
| `boss_damage` | `amount` | Add boss damage, check objective |
| `refresh` | `target` (optional) | Refresh ally, asks player if several eligible |
| `discard_ally` | none | Prompt to discard an ally if present |
| `eliminate` | `optional` boolean | Prompt to eliminate from hand/play/discard |
| `market_cycle` | none | Prompt to replace upgrade market slots |
| `draw_boss` | none | Draw and reveal boss-only sleeve into boss-in-play |
| `conditional` | `condition`, `effects` | Implemented: `level_at_least`, `conspire` |
| `repeat` | `times`, `effects` | Repeat a series of effects (safety cap 20) |
| `noop` | none | Explicitly no effect |

Numeric `amount` or `times` can be an integer or a variable:

```json
{"amount": {"per": "focus", "base": 0}}
```

Supported variables: `focus` (same-faction cards in hand/play), `unite` (different represented factions), `danger` (danger track value). For example, `{"op":"damage","amount":{"per":"focus"},"target":"choose"}`.

Conditions include `{"kind":"level_at_least","value":2}` and `{"kind":"conspire"}`. Other complex rules must be added as Python handlers with tests before importing cards that require them. **Unknown operators throw a validation error** instead of silently doing the wrong thing.

### Import process when you provide actual cards

1. Send batches of core, threat, upgrade or boss card information. Photos or a spreadsheet can work.
2. We add their definitions to `cards[]` with stable IDs and translate their printed effects into supported actions/conditions. We implement and test any missing effect operators.
3. Then we update `starter_sleeves`, `reserve_threats`, loose decks, and the boss scenario recipe separately. This protects us from accidentally confusing the two faces of a card.
4. Upload the revised JSON through the app's sidebar and select **New game**. The browser UI uses the updated content without changing the game engine code for ordinary supported abilities.

Specialized abilities will sometimes require new engine code. JSON can describe data and *known behavior*, but cannot magically implement rules we haven't programmed.
