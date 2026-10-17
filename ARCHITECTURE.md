# Architecture & next milestones

## Model

```text
Catalog
  ├── core definitions (type tactic/ally, cost, level, faction, effects)
  ├── threat definitions (attack, defense, keywords, when-defeated)
  ├── upgrade definitions (slot, requirement, cost, two-face modifiers)
  ├── boss definitions
  └── scenario recipe (starter pairs, loose pools, danger track, boss)

GameState
  ├── PlayerState: HP/armor/AP/credits/level, zones with sleeve IDs
  ├── sleeves: uid -> Sleeve(core_id, threat_id, top/bottom upgrades, damage...)
  ├── unsleeved core decks / upgrade pool / market
  ├── reserve threat-only sleeves
  ├── boss deck / boss in-play / shared objective
  ├── queue of pending effects
  ├── pending decision (draft/target/level-up/etc.)
  └── phase, turn, danger, result, event log

GameEngine
  ├── validate command before mutation
  ├── apply command, append/resolve effect queue
  ├── interrupt for choices (never let UI edit HP directly)
  └── resume phase when choices complete

app.py (Streamlit)
  └── displays state + sends commands; no game rules in UI
```

## Lifecycle example: from a loose core to an upgraded threat

1. At setup, the loose level-1 pile has a printed `core_A` copy. Separately, a pre-sleeved `S0001` exists with `core_X` on one face and `threat_Y` on the other. A *threat-only* sleeve `S0045` has no core (`core_id=null`) but contains `threat_Z`.
2. During the draft, draw 3 *loose core* IDs from level-1 pile. The player chooses `core_A`; two other copies go to the bottom of that pile.
3. Pop `S0045` from the reserve and set `S0045.core_id='core_A'`. Its **threat remains `threat_Z` and is not revealed in hand**. Add `S0045` to hand, core side displayed.
4. During main, buy upgrade `upgrade_B`, put it in the **top** upgrade slot of `S0045`, spending credits. This same sleeve now has 4 possible layers: core, threat, top upgrade, bottom upgrade.
5. Play core side; tactical effect triggers; later card is discarded and reshuffled threat-side up. Both upgrade layers remain on the same sleeve. The threat side receives **its own** attack/defense changes when revealed and fought.
6. Defeating that threat moves `S0045` to hand, flips it to its core side, and invokes its threat-side defeat bonus. Never construct a new unrelated sleeve for this action.

## UI/runtime

Use Python 3.11+ and Streamlit Community Cloud. All gameplay occurs in the Python session allocated to your browser. Download/import saves, because a hosted session may restart at any time. Random state is embedded in the save so actions replay reproducibly after restoring.

## Follow-on engineering priorities

1. Fully populated, faithful cards and scenario data from user-provided source material.
2. Explicit interrupt stack: choice of order for effects, optional triggers, target semantics, additional effect keywords, specialized card handlers.
3. Full boss module with data-driven scenario phases, win objectives, threat/boss card events and danger map logic.
4. Expanded tests covering every individual card and exact official timing; seed reproducibility and invariant checks of card-zone uniqueness.
5. Cooperative architecture: multiple players, independent decks and zones, shared threat target routing, shared danger / boss.
6. UI quality: real card templates, swipe-friendly phone experience, keyboard shortcuts, undo/history, animations and optional art.

Nothing about this architecture depends on the dummy content remaining in the app.
