"""Streamlit launcher for Pixel Clash, a client-side canvas fighting game.

UI and combat run inside the embedded browser frame, not on Streamlit's Python
server. This is essential for responsive animation and keyboard controls.
"""

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent

st.set_page_config(page_title="Pixel Clash", page_icon="⚡", layout="wide")
st.markdown(
    """<style>
    .block-container {padding-top: 0.5rem; padding-bottom: 0.3rem; max-width: 1120px;}
    [data-testid="stHeader"] {height: 2rem;}
    </style>""",
    unsafe_allow_html=True,
)


def load_game() -> str:
    """Assemble the self-contained HTML iframe from checked-in game assets."""
    characters = json.loads((HERE / "characters.json").read_text(encoding="utf-8"))
    if not isinstance(characters, list) or len(characters) < 2:
        raise ValueError("The character roster must contain at least two fighters.")
    ids = [character["id"] for character in characters]
    if len(ids) != len(set(ids)):
        raise ValueError("Every fighter in characters.json needs a unique id.")
    html = (HERE / "game.html").read_text(encoding="utf-8")
    css = (HERE / "game.css").read_text(encoding="utf-8")
    javascript = (HERE / "game.js").read_text(encoding="utf-8")
    character_json = json.dumps(characters, ensure_ascii=False).replace("<", "\\u003c")
    # Characters are JSON data, never executable code from user inputs.
    javascript = javascript.replace("__CHARACTERS_JSON__", character_json)
    return html.replace("__GAME_CSS__", css).replace("__GAME_JS__", javascript)


components.html(load_game(), height=870, scrolling=True)
