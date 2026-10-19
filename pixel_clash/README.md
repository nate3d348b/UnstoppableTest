# Pixel Clash ⚡

An expandable, original pixel-art, single-player-versus-CPU fighting game in the browser,
hosted inside a Streamlit app. No game-engine installation is required.

## Play

- Choose Ember, Volt, or Onyx, then click **START FIGHT**.
- **A / D:** move; **W:** jump; **S:** block.
- **J:** punch; **K:** kick; **L:** special projectile.
- First to win two rounds wins the match. Mobile/touch controls are included.
- To use keyboard controls, click inside the game once to focus it.

## Streamlit Community Cloud deployment

1. In [Streamlit Community Cloud](https://share.streamlit.io/), click **Create app**.
2. Choose **I have an app** and choose the GitHub repository.
3. Set the branch to `pixel-clash-prototype`.
4. Set the main file path to `pixel_clash/app.py`.
5. Click **Deploy**. This folder has its own `requirements.txt`.

For local runs, install requirements and run `streamlit run pixel_clash/app.py`
from the repository root.

## Adding a fighter

Character statistics are stored in `pixel_clash/characters.json`. To add a new
fighter, add another JSON object with a new unique `id` and the keys present in
the existing entries. `speed`, `jump`, `health`, and `power` control the fighter.
Color fields currently drive original placeholder pixel art.

Future releases can add dedicated animations, move sets, hitboxes, and sprite
assets while leaving the Streamlit launcher unchanged.

## Project files

- `app.py` : Streamlit launcher, loads assets and assembles the frame
- `game.html` : in-browser UI markup
- `game.css` : responsive styling
- `game.js` : game loop, combat, CPU AI, rendering, touch/keyboard input
- `characters.json` : fighter data
- `requirements.txt` : Streamlit dependency

This version is a playable **prototype**, not a polished arcade engine.
Online multiplayer and fully unique sprite animations are not implemented yet.
