# Project status

**As of:** 2026-10-17  
**Live app:** https://natestoppable.streamlit.app  
**Repository:** https://github.com/nate3d348b/UnstoppableTest

## Objective

Build a browser-playable, solo-first framework for the physical card-crafting game *Unstoppable*. Use **Python** for game logic, **Streamlit** for the interface, and **JSON** for card/scenario definitions. Populate the real cards from user-supplied information later. Art is deferred.

This is an unofficial personal learning/play project. Every bundled demo card and the example boss are fictional stand-ins, not verified published card content.

## Current implementation (framework, not rules-complete)

- Data-driven card catalog and validation, with unrecognized effect operations rejected instead of ignored.
- A persistent **physical sleeve** with separate `core_id`, `threat_id`, top/bottom upgrade references, face, damage and state.
- Support for starting **pre-sleeved core + threat**, **threat-only sleeves** to receive newly drafted loose cores, and separate boss sleeves.
- Separate printed definitions, loose core/upgrade inventory, and sleeved cards moving between play zones. Drafting a core preserves the sleeve's existing threat side.
- Solo phase progression, drafting, simplified card effects and player decisions, threats, combat, upgrades, level progression, placeholder boss progression, and danger tracking.
- Streamlit interface, JSON save/export/import, seeded random generation and engine logging.
- Automated standard-library `unittest` tests; additional integrity coverage asserts sleeve-zone uniqueness and atomic failure for illegal commands.

## Verification

- The original engine suite contains **19 tests**.
- The proposed integration of `tests/test_integrity.py` adds **3 tests**, for **22 passing tests** when run locally against this revision.
- GitHub Actions checks Python 3.11 and 3.12 on push/PR once merged and granted workflow permission.
- **Not yet verified:** a live click-through of the hosted Streamlit interface, production deployment after these changes, or complete official-rule fidelity.

Run tests locally:

```bash
python -m unittest discover -s tests -v
```

## Known missing work

1. Real character setup lists, printed cores/threats/upgrades, and scenario/card data.
2. Nested effect/interrupt resolution, player-selectable ordering of simultaneous effects, optional triggers and all card-specific abilities.
3. Accurate boss encounter rules, objectives, danger spaces, exception/timing review, and full edge-case tests.
4. Cooperative multiplayer; current architecture is **solo-first**.
5. Improved card inspector, responsive card presentation and accessibility.

## Next milestones

1. **v0.2 engine reliability:** explicit resumable effect-resolution stack; test interrupts, targets, choices, state integrity, timing and save/load.
2. **v0.3 content tooling:** card import workflow with schema checks and diagnostics for unsupported operators; inspect individual sleeves in UI.
3. **v0.4 first real character:** integrate one complete starting deck, including pre-sleeved cards and loose drafting pools supplied by the user.
4. **v0.5 first real boss:** replace demo scenario with verified encounter rules and objectives.

## Repository workflow

Implement changes on a feature branch; run all tests; open a pull request targeting `main`; merge only when reviewed and checks pass. `main` remains the Streamlit deployment branch. A PR should describe tested behaviors and known limitations.

The `unstoppable_web_framework.zip` file in the repository is a legacy export, **not** the source of truth. Change the unpacked Python/JSON files in the repository instead.
