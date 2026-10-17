"""Streamlit browser UI. No rule calculations happen here."""
from __future__ import annotations
import json
from pathlib import Path
import streamlit as st
from unstoppable import GameEngine, Catalog, load_catalog, RuleError, CatalogError

ROOT = Path(__file__).parent
DEMO = ROOT / 'data' / 'demo_cards.json'

st.set_page_config(page_title='Sleevecraft | Unstoppable Engine', page_icon='🃏', layout='wide')
st.markdown('''<style>
.block-container {padding-top:1.5rem; max-width:1400px}
[data-testid="stMetricValue"] {font-size:1.45rem}
[data-testid="stSidebar"] {background-color:#101a2b}
h2,h3 {letter-spacing:-.02em}
small {color:#a3b5cc}
</style>''', unsafe_allow_html=True)


def do(action: str, **kwargs) -> None:
    try:
        st.session_state.engine.act(action, **kwargs)
        st.rerun()
    except (RuleError, CatalogError) as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f'Unexpected engine error: {exc}. Export a save and report the steps that caused this.')


def name(uid: str, threat: bool = False) -> str:
    engine = st.session_state.engine
    sleeve = engine.state.sleeves[uid]
    return engine.catalog.name(sleeve.threat_id if threat else sleeve.core_id)


def upgrade_desc(uid: str) -> str:
    e = st.session_state.engine
    u = e.state.sleeves[uid].upgrades
    if not u:
        return 'No installed upgrades'
    return ' | '.join(f'{slot}: {e.catalog.name(cid)}' for slot, cid in u.items())


def core_card(uid: str, interactive: bool = False, *, exhaust: bool = False) -> None:
    e = st.session_state.engine
    c = e.catalog.card(e.state.sleeves[uid].core_id)
    with st.container(border=True):
        st.markdown(f'**{c.get("name", "Unknown core")}**  · `{uid}`')
        st.caption(f'{c.get("type", "").title()} • {c.get("faction", "none").title()} • Cost {c.get("cost", 0)} AP • Lv {c.get("level", 0)}')
        st.write(upgrade_desc(uid))
        if c.get('effects'):
            with st.expander('Abilities', expanded=False):
                for trigger, effects in c['effects'].items():
                    st.code(f'{trigger}: {json.dumps(effects, ensure_ascii=False)}', language='json')
        if interactive:
            if st.button('Play card', key=f'play_{uid}',
                         disabled=(e.state.pending is not None or e.state.phase != 'main'),
                         use_container_width=True):
                do('play', uid=uid)
        if exhaust:
            ready = not e.state.sleeves[uid].exhausted
            if st.button('Exhaust ally' if ready else 'Exhausted', key=f'exhaust_{uid}',
                         disabled=not ready or e.state.pending is not None or e.state.phase != 'main',
                         use_container_width=True):
                do('exhaust', uid=uid)


def threat_card(uid: str, *, on_deck=False) -> None:
    e = st.session_state.engine
    t = e.catalog.card(e.state.sleeves[uid].threat_id)
    att, deff, total = e.threat_stats(uid)
    with st.container(border=True):
        st.markdown(f'**{name(uid, True)}** · `{uid}`')
        st.caption('ON-DECK THREAT' if on_deck else 'ACTIVE THREAT')
        st.write(f'⚔️ {att} attack　🛡️ {deff} defense　🩸 {e.state.sleeves[uid].damage}/{total} damage')
        keywords = t.get('keywords', [])
        if keywords:
            st.caption('Keywords: ' + ', '.join(x if isinstance(x, str) else f"{x['name']} {x.get('value','')}" for x in keywords))
        if e.state.sleeves[uid].upgrades:
            st.caption('Mods: ' + upgrade_desc(uid))


if 'engine' not in st.session_state:
    st.session_state.engine = GameEngine.new(load_catalog(DEMO), seed=42)

with st.sidebar:
    st.title('🃏 Sleevecraft')
    st.caption('A browser framework for the physical card-crafting game Unstoppable. Unofficial, personal prototype.')
    st.info('DEMO CONTENT: card names, effects and boss are placeholders, not a faithful published card set.')
    st.subheader('Start a game')
    uploaded = st.file_uploader('Optional custom card catalog (JSON)', type=['json'], key='catalog_file',
                                help='Omit to play the included demo catalog.')
    seed = st.number_input('Random seed', min_value=0, max_value=2147483647, value=42, step=1)
    difficulty = st.selectbox('Difficulty', ['normal', 'hard', 'expert'])
    if st.button('New game', type='primary', use_container_width=True):
        try:
            catalog = Catalog(json.load(uploaded)) if uploaded else load_catalog(DEMO)
            st.session_state.engine = GameEngine.new(catalog, seed=int(seed), difficulty=difficulty)
            st.rerun()
        except (RuleError, CatalogError, ValueError, KeyError, TypeError) as exc:
            st.error(f'Catalog/setup error: {exc}')
    st.divider()
    st.subheader('Save and continue')
    save_data = json.dumps(st.session_state.engine.export_save(), indent=2)
    st.download_button('⬇️ Download game save', save_data, file_name='sleevecraft_save.json',
                       mime='application/json', use_container_width=True)
    uploaded_save = st.file_uploader('Load existing saved game', type=['json'], key='save_file')
    if st.button('Load save', disabled=uploaded_save is None, use_container_width=True):
        try:
            st.session_state.engine = GameEngine.from_save(json.load(uploaded_save))
            st.rerun()
        except (RuleError, CatalogError, ValueError, KeyError, TypeError) as exc:
            st.error(f'Invalid save: {exc}')
    st.download_button('⬇️ Download current card catalog',
                       json.dumps(st.session_state.engine.catalog.data, indent=2),
                       file_name='my_cards.json', mime='application/json', use_container_width=True)
    with st.expander('Developer details'):
        st.caption('The seed makes card order reproducible. Saves include the catalog, game state, and RNG state.')
        st.write(f'{len(st.session_state.engine.catalog.cards)} printed card definitions loaded.')

e = st.session_state.engine
s = e.state
p = s.player
scenario = e.catalog.scenario
st.title('Unstoppable · Game workspace')
st.caption(f'{scenario.get("name", "Scenario")} | {p.name} | Turn {s.turn} | {s.phase.upper().replace("_", " ")} | {s.difficulty.title()}')
if s.demo_mode:
    st.warning('This is a mechanics sandbox using original dummy cards. Boss logic and card text still need the real data.')
if s.result != 'ongoing':
    (st.success if s.result == 'victory' else st.error)(f'{s.result.upper()}: game finished. Download your save or start a new game.')

stats = st.columns(7)
for box, label, value in zip(stats,
                             ['Health', 'Armor', 'Action points', 'Credits', 'Level', 'Trained level', 'Boss progress'],
                             [f'{p.hp}/10', f'{p.armor}/10', f'{p.action_points}/6', p.credits,
                              p.level, p.draft_level, f'{s.boss_damage}/{scenario.get("boss_goal", "?")}']):
    box.metric(label, value)
track = scenario.get('danger_track', [])
st.write(f'**Danger** · space {s.danger_index}/{len(track)-1}, value **{e.danger_value}**')
st.progress(min(1.0, s.danger_index / max(1, len(track)-1)))

if s.pending:
    pending = s.pending
    st.subheader('⚡ Your decision')
    kind = pending['kind']
    labels = {
        'draft':'Choose one loose core to insert into the next threat-only sleeve',
        'target':'Select a visible target for damage',
        'level_discard':'Level up: discard cards until you have only 3 in hand',
        'level_eliminate':'Level up: you may permanently eliminate one card',
        'discard_ally':'Rage: select an ally to discard',
        'eliminate':'Select a card to eliminate',
        'refresh':'Choose an ally to refresh',
        'market_cycle':'Choose an upgrade slot to replace, or finish cycling'
    }
    st.info(labels.get(kind, kind))
    options = pending.get('options', [])
    if kind == 'draft':
        fmt = lambda i: f'{e.catalog.name(options[i])} · {e.catalog.card(options[i]).get("type")} · cost {e.catalog.card(options[i]).get("cost",0)} AP · option {i+1}'
        choices = list(range(len(options)))
    elif kind == 'market_cycle':
        fmt = lambda i: f'Slot {i+1}: {e.catalog.name(s.upgrade_market[i])}'
        choices = list(range(len(options)))
    else:
        fmt = lambda uid: f'{name(uid, threat=(kind=="target"))} ({uid})'
        choices = options
    if choices:
        picked = st.selectbox('Choose', choices, format_func=fmt, key=f'decision_{kind}_{s.turn}_{len(options)}')
        if st.button('Confirm decision', type='primary', key=f'confirm_{kind}'):
            do('choose', selection=picked)
    if pending.get('optional') and st.button('Skip / done', key=f'skip_{kind}'):
        do('choose', selection='__skip__')

left, right = st.columns([1.7, 1], gap='large')
with left:
    st.subheader(f'🪪 Your hand · {len(p.hand)} cores')
    if not p.hand:
        st.caption('Your hand is empty. Defeat threats to reclaim their core sides.')
    for start in range(0, len(p.hand), 3):
        slots = st.columns(3)
        for col, uid in zip(slots, p.hand[start:start+3]):
            with col:
                core_card(uid, interactive=True)
    st.subheader(f'⚔️ Battlefield · {len(p.battlefield)} threats')
    if not p.battlefield:
        st.caption('No active threats.')
    for start in range(0, len(p.battlefield), 3):
        slots = st.columns(3)
        for col, uid in zip(slots, p.battlefield[start:start+3]):
            with col:
                threat_card(uid)
    st.subheader('👁️ On-deck threat')
    if p.deck:
        threat_card(p.deck[0], on_deck=True)
    else:
        st.caption('Deck empty. The next level-up event may rebuild it from the discard pile.')

with right:
    st.subheader('🧰 Zones')
    st.write(f'**Deck:** {len(p.deck)} sleeved cards (only the top threat is visible)')
    st.write(f'**Discard:** {len(p.discard)} | **Eliminated:** {len(p.eliminated)}')
    st.write(f'**Reserve threat-only sleeves:** {len(s.reserve_threats)}')
    st.write(f'**Boss deck:** {len(s.boss_deck)} | **Boss cards in play:** {len(s.boss_in_play)}')
    with st.expander('Loose unsleeved core decks'):
        for level, ids in sorted(s.loose_cores.items(), key=lambda x: int(x[0])):
            st.write(f'Level {level}: {len(ids)} cards')
    st.subheader(f'🤝 Allies · {len(p.allies)}')
    for uid in p.allies:
        core_card(uid, exhaust=True)
    with st.expander(f'Tactics in play ({len(p.tactics)})'):
        for uid in p.tactics:
            st.write(f'{name(uid)} ({uid})')
    st.subheader('🔧 Upgrade market')
    for i, upgrade_id in enumerate(s.upgrade_market):
        card = e.catalog.card(upgrade_id)
        st.caption(f'{i+1}. {card["name"]} · {card["slot"]} · {card.get("cost",0)} credits · requires {card.get("requires","either")}')
    install_targets = p.hand + p.tactics + p.allies
    if s.upgrade_market and install_targets:
        market_i = st.selectbox('Choose loose upgrade', list(range(len(s.upgrade_market))),
                                format_func=lambda i: f'{e.catalog.name(s.upgrade_market[i])} ({i+1})')
        target_uid = st.selectbox('Install into sleeve', install_targets,
                                  format_func=lambda uid: f'{name(uid)} ({uid}) · {upgrade_desc(uid)}')
        if st.button('Buy and sleeve upgrade', disabled=s.phase != 'main' or bool(s.pending),
                     use_container_width=True):
            do('buy', market_index=market_i, uid=target_uid)
    else:
        st.caption('Buy upgrades during the main phase with a core card in hand or play.')
    if st.button('End main phase → Threat + Cleanup', disabled=s.phase != 'main' or bool(s.pending),
                 use_container_width=True, type='primary'):
        do('end_main')

st.divider()
with st.expander(f'📜 Game log ({len(s.log)} events)', expanded=True):
    for line in reversed(s.log[-60:]):
        st.text(line)
with st.expander('Inspect physical sleeves (debug view)', expanded=False):
    st.caption('This debug view intentionally exposes both faces. Regular play hides the threat back of cards in hand.')
    inspect = st.selectbox('Select sleeve', list(s.sleeves), format_func=lambda uid: uid)
    if inspect:
        st.json(vars(s.sleeves[inspect]))
