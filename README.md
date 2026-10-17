# Sleevecraft: Unstoppable web framework

An **unofficial, personal, browser-playable, solo-first framework** for exploring the mechanics of the physical card-crafting game *Unstoppable*. Built in Python with [Streamlit](https://streamlit.io/). **All bundled cards and the boss are invented demo data, not published card text.** No copyrighted card art is included.

## Current deployment & development status

- **Hosted prototype:** [natestoppable.streamlit.app](https://natestoppable.streamlit.app).
- **Project snapshot and known limitations:** [PROJECT_STATUS.md](PROJECT_STATUS.md).
- **Continuous integration:** [GitHub Actions tests](.github/workflows/python-ci.yml) run on pull requests and pushes to `main` using Python 3.11 and 3.12.
- **Regression tests:** `python -m unittest discover -s tests -v` (22 tests with the integrity suite).
- **Scope:** this is a **demo-backed solo framework**, not a complete, verified rules implementation. Real cards, exact boss logic, and advanced timing are still to be implemented.

Develop features on branches and review through pull requests. The unpacked source files, not the historical `unstoppable_web_framework.zip` export in the repository, are the source of truth.

## Play online without installing Python on your computer

1. Create a GitHub repository and upload **the contents of this folder** (not the ZIP as one file). Include the hidden `.streamlit` folder, or omit it and accept Streamlit's default styling.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in using GitHub.
3. Create an app from the repository; set **entrypoint / main file to `app.py`** and pick your branch.
4. Deploy. Open the generated `*.streamlit.app` URL in a browser on your computer or phone.
5. In the sidebar, start a demo or upload your own content JSON. Download saves to preserve progress across sessions.

The published hosting provider controls app access and visibility. **Do not assume your hosted app is private**. Review its access/sharing settings before uploading personal content. Uploaded card data and saves live in the running Streamlit session; you must download a save to keep a lasting record. This repository has no database and doesn't send card data to a custom backend, but Streamlit's hosting still processes data on its servers.

For local development, install dependencies (`python -m pip install -r requirements.txt`) and run `python -m streamlit run app.py`. The code does not require Node.js, a web server you administer, or a traditional desktop UI.

## What exists now

- Card definitions validated from JSON; unknown effect operators **fail validation**.
- Separate objects for **a card definition**, **loose core/upgrade copies**, and **physical sleeve instances** with durable IDs.
- Three sleeve shapes: **pre-sleeved core + threat**, **threat-only sleeve ready for drafting**, **boss-only sleeve**.
- Sleeve has **core side / threat side** and independent **top / bottom upgrades** with modifiers that can apply to **both sides**.
- Game zones: deck (threat-side up), hand (core-side up), battlefield, allies, played tactics, discard, eliminated, unsleeved core piles per level, unsleeved upgrade pile, market, threat-only sleeve reserve, boss deck/in-play/discard.
- Setup with 10 starter sleeves, initial 3-card hand, 3 active threats, 3 starting credits, level discs and action points.
- Upkeep → draft → main → threat → cleanup loop, with a decision system that can pause on target selection, draft choices, ally discard and elimination.
- Draft 3 loose cores from current level; return the 2 unchosen copies to the *bottom* of that level deck; pair chosen core with next threat-only sleeve (threat face concealed), add to hand.
- Play tactics and allies, exhaust allies, spend action points, buy upgrades, use faction-conditional and simple numerical effects, pick damage targets.
- Attack + defense threat HP; persistent threat damage; defeated sleeve flips to hand; when-defeated bonuses; damage armor-before-health.
- Threat keywords: **Fast, Taunt, Rage, Terror and Crazed X** (basic behavior supported).
- Cleanup resets AP and armor, discards tactics, refills with Fast exceptions, advances danger with difficulty-dependent skips.
- Level up: level discs advance, cards in play discarded, discard hand to 3, optional elimination, shuffle discard into new threat-side-up deck.
- Boss framework: separate deck/zone, scenario-specific triggers, `boss_damage` victory goal, configurable danger track. **Demo boss goal is a placeholder, not a real published scenario**.
- Deterministic RNG by seed, human-readable log, action-level rollback, downloadable/uploadable save (including full catalog and random state).
- Automated engine tests using **Python's standard-library unittest**.

## Not yet a rules-complete digital adaptation

This project implements the *architecture and a large part of the solo turn loop*, **not all printed abilities or all official exceptions**. Card content is intentionally missing. The remaining work is meaningful:

- **Actual published content**: four hero/portrait definitions, ten-card start lists, exact card text, the 100 loose level 1–6 cores, 39 threats, upgrades, boss scenarios, and setup recipes. Import the catalog progressively.
- **Flexible effect timing/choices**: selectable ordering of simultaneous effects and upgrades; nested interrupts; optional on-card triggers; delayed and repeat effects; exact timing of boss events, reveals, on-defeat, and level-up. Current engine runs deterministic fixed order for multiple same-timing effects.
- **Full keyword cases**: faction keywords Bargain and their optional cost prompts, all conditional/variable effect interactions, additional card-specific text; printed cards with unique behavior must have added handlers.
- **Bosses**: exact unique boss rules, threat/encounter decks, victory conditions and boss-card abilities must be implemented from the scenario data. The demo uses a generic boss-damage counter.
- **Optional danger spaces** and all card elimination edge cases need final timing reviews; market cycle and optional eliminate are exposed as decisions.
- **Two-player cooperative mode** is deliberately not enabled. Use this solo engine as the baseline; a future version can add multiple `PlayerState` objects, coordinated drafting, cross-player targeting, shared danger and boss state.
- **Deck exhaustion and empty-pile corner cases** and rare interrupt chains require more exhaustive testing against the printed rulebook.
- Artwork, animations, advanced accessibility, game histories across hosting restarts, and cloud accounts are out of scope.

See [`DATA_FORMAT.md`](DATA_FORMAT.md) for card import examples and [`ARCHITECTURE.md`](ARCHITECTURE.md) for modules, action/decision flow, and expansion checklist.

## Project files

```text
app.py                    Streamlit browser interface
unstoppable/models.py     Physical sleeves, player and game state
unstoppable/catalog.py    Validate/load JSON, register allowed operators
unstoppable/engine.py     Rule transitions, card movements, effects, decisions
unstoppable/__init__.py   Public imports
data/demo_cards.json      Invented dummy content and boss scenario
requirements.txt          Streamlit dependency
.streamlit/config.toml    Optional dark UI styling
tests/test_engine.py      Rule and save/restore tests
```

## Test without Streamlit

```bash
python -m unittest discover -s tests -v
```

## Reference

Rule details were adapted from the official [Renegade Unstoppable rulebook](https://www.retailers.renegadegamestudios.com/content/File%20Storage%20for%20site/Rulebooks/Unstoppable/Unstoppable_Rulebook_WEB.pdf), also accessible as a [searchable text rulebook](https://www.rulespal.com/unstoppable/rulebook). Game mechanics used for engineering purposes. *Unstoppable* is owned by its respective creators/publishers; this fan project is not affiliated with them.
