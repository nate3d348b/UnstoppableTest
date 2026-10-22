# Unstoppable: Card Logic & Engine Considerations

**Status:** Living design backlog, started 2026-10-21  
**Source:** Card spreadsheet discussions and the user's clarifications.  
**Important:** This records *requirements and interpretation*, **not a claim that they are already implemented**. The final Excel workbook is authoritative for card numbers and wording; the typed official rulebook will settle remaining questions.

Legend: **Confirmed** = explicitly clarified by user or agreed notation; **Check rulebook/card** = pending verification; **Design** = recommended implementation, not a game rule.

## A. Card-data conventions and import

- [ ] **Confirmed:** Excel is the transcription source. Use the final supplied workbook for all actual HP, damage, AP, credit and other numerical values, even where earlier screenshots/examples differ.
- [ ] **Confirmed:** Ability text uses human-readable Python-inspired pseudocode, not valid Python/JSON. Nested `{...}` represents keyed groups/conditions; square brackets `[...]` represent ordered collections or option lists according to the enclosing keyword. `Choose One: [{...}, {...}]` means select exactly one option.
- [ ] **Design:** Preserve raw spreadsheet text and an independently generated executable AST/JSON representation, plus stable card ID, source row, parsing warnings and review status. Never silently discard unsupported rules.
- [ ] **Design:** Support one card definition with many physical copies, and **persistent sleeve IDs** for each physical assembly.
- [ ] **Confirmed:** Some cards start pre-sleeved as a paired core/threat; other threats start in threat-only sleeves and take a drafted loose core later. Loose cores and upgrades remain separate until placed in sleeves. Each sleeve's core, threat, upper upgrade and lower upgrade identities must persist across zone changes.
- [ ] **Design:** Catalog/sleeve validation: legal card categories and slots, quantities, ownership, no sleeve duplicated across zones, no accidental revelation of concealed threat faces.

## B. Ability resolution, ordering, conditions

- [ ] **Confirmed:** When playing a core, put it in front of the player core-side up and resolve its effects. Players may resolve eligible printed effects **including upgrades in any chosen order**, and may forfeit effects they cannot or do not want to resolve. No fixed left-to-right evaluation across independent effects.
- [ ] **Design:** Introduce a **resumable effect/decision stack**: unresolved effect choices, targets, calculations, temporary payments, suspended nested effects, provenance, trigger ordering, and post-effect outcomes. Prompt before resolving effects that need user decisions.
- [ ] **Confirmed:** `{Pay: {...}, Then: {...}}` means the consequence is only available after the stated payment *actually succeeds*. Example: losing 1 HP to deal damage cannot produce damage without losing HP. Declining the cost forfeits that linked payoff.
- [ ] **Confirmed:** `{Sequence: [{If Possible: {...}}, {...}]}` performs the first instruction if possible, then proceeds even if that instruction was impossible. When a card is available to discard, a required "discard if possible" instruction must be performed to continue. The dependent later damage occurs even when hand is empty.
- [ ] **Check rulebook/card:** Clarify the general semantics of *ordinary* sequence steps when they cannot resolve. Do **not** assume that any failure always terminates every sequence; distinguish `Pay` from non-cost sequencing and the printed wording.
- [ ] **Confirmed:** `{Choose One: [{...}, {...}]}` is mutually exclusive. The chosen branch can include immediate or delayed effects.
- [ ] **Confirmed:** Level gates `Level 2+`, `Level 3+`, `Level 4+` are cumulative where applicable, not replacement tiers. Independent conditional branches can coexist.
- [ ] **Design:** Resolve variable quantities and conditions at the effect's actual resolution time unless the rulebook explicitly locks a value earlier.
- [ ] **Design:** Preserve separate instances of `Deal Damage: 1, Deal Damage: 1` and `Repeat X times: {Deal Damage: 1}` rather than combining into single damage, as targeting, timing and triggers might differ.
- [ ] **Confirmed:** Track the result of an immediately preceding effect for `If Defeated`. E.g. 2 damage defeats the **on-deck** threat -> gain an AP; defeat of an active threat or earlier unrelated defeat doesn't qualify.
- [ ] **Design:** Capture effect outcome metadata (target UID/zone at time, damage dealt, defeated?, cards moved, previous zone, resources actually paid) so follow-up conditions can inspect the exact event.
- [ ] **Confirmed:** Conditions include strict inequalities (`strictly less than`, `strictly more than`), current active threat count, damaged active-threat count, threats defeated *this turn*, first card played *this turn*, and upgrade counts.
- [ ] **Confirmed:** When an ability says "number of upgrades", for the recently discussed core it includes upgrades **in hand and in play**; do not implicitly count cards elsewhere.
- [ ] **Design:** Use turn-local counters: cards played, threats defeated, trained levels gained (total gained, not just number of training activations), credits spent, upgrades purchased, etc. Reset at correct boundaries.

## C. Faction mechanics and resources

- [ ] **Confirmed:** **Conspire** activates if at least one *other* same-faction card exists in hand or in play; the ability's own card does not satisfy Conspire.
- [ ] **Confirmed:** **Bargain N** is optional; paying its effective credit cost activates the Bargain effect. Discount cost by 1 per same-faction card in hand and/or in play, **including the card itself**.
- [ ] **Design:** Track changing faction membership, count distinct faction identities correctly, and recalculate Focus/Unite/Conspire/Bargain at their relevant timing.
- [ ] **Check rulebook:** Obtain definitive official `Focus X` and `Unite X` definitions and details about what qualifies as in-play. Do not extrapolate solely from example cards.
- [ ] **Confirmed:** A temporary ability can make a card count as its original faction **plus** another player-chosen faction until the end of turn. It does not replace its original faction.
- [ ] **Confirmed:** One card looks at 3 loose cores from the **Level X** deck, where X is **Unite X**, keeps one, and puts the others on the bottom. User changed transcription from "Draw Cards" to **"Look at Cards"**.
- [ ] **Design:** Support temporary per-turn discounts (next Bargain cost, next upgrade purchase) and track consumption/expiry. Discount floors and stacking await rulebook confirmation.
- [ ] **Design:** Support temporary individual card-cost discounts that follow *specified sleeve instances*, selected randomly from hand; expire when the source leaves play or at the printed duration. Store source UID, target UIDs and modifier value. Define selection behavior with fewer eligible cards via printed rules.
- [ ] **Confirmed:** `Gain Action Point`, credit, HP, armor, Train Level effects may each be separate selectable effects; resource changes can make other actions eligible later in the same turn.
- [ ] **Confirmed:** Damage/healing expressions can depend on current HP, HP *actually lost*, armor *actually lost*, eligible upgrades, number of affected threats, Focus/Unite X and trained levels gained this turn.

## D. Targeting, card movement, and randomness

- [ ] **Confirmed:** Targeting can specify active threats vs on-deck threat; some attacks deal 1 damage to **each active threat** and explicitly **ignore Taunt**. Preserve target scopes and ignore-keyword overrides.
- [ ] **Design:** Distinguish single-target effects, all-target effects, repeated distinct effects, and random targets; validate chosen targets at resolution time.
- [ ] **Confirmed:** `Remove/Eliminate Card` means remove a physical card/sleeved assembly **from the current run**, storing it in an eliminated zone. It becomes available again in a fresh setup; it is not a normal discard.
- [ ] **Check rulebook:** Which zones are eligible for elimination, whether loose cards differ, and when an entire sleeve (core, threat, upgrades) is removed versus a particular component. The user's understanding is to remove the entire assembly unless a rule says otherwise.
- [ ] **Confirmed:** Look/search/draw can refer to **top or bottom of player's deck**, a **level-specific loose core deck**, discard pile, or combined deck+discard; card selection can be chosen or random.
- [ ] **Confirmed:** Search an ally from deck or discard, put it in hand; a subsequent instruction acts differently **if the ally came from the deck** (e.g. put the searching card/Hire Bodyguard on deck bottom). Preserve origin of the selected card across instructions.
- [ ] **Design:** Support adding a **random** discarded card to hand; seeded randomness must remain reproducible through save/load and tests.
- [ ] **Design:** Support search misses, empty zones, bottom-of-deck placement, returning unchosen looked-at cores to bottom, and reordering policy without accidentally duplicating/removing sleeves.
- [ ] **Design:** `Refresh Ally: X` may ask player to select multiple allies, with validation and partial availability rules.
- [ ] **Check rulebook:** Whether forced reshuffling occurs during searches/draws, and how abilities behave when fewer than requested cards are available.

## E. Ally/tactic life cycles, triggers, modifiers

- [ ] **Confirmed:** A **tactic** stays in play until the end of that turn, when it leaves play; an **ally** can remain in play across turns. The source card must remain in play while its effects are resolved.
- [ ] **Confirmed:** An `Active Effect` can be a **triggered** ability (`while card in play, when an upgrade is bought: deal 1 damage, gain 1 health`) or a **continuous** modifier (e.g. extra faction membership).
- [ ] **Design:** Implement an event system: subscribe sources while active/in play; fire on events such as upgrade purchase, threat defeat, entering play, leaving play, end turn. Automatically unregister/re-evaluate once source leaves play.
- [ ] **Check rulebook:** Mandatory vs optional triggered abilities; simultaneous ordering; multiple triggers across repeated purchases; exact phase timing.
- [ ] **Design:** Independent effects from a played card and installed upgrades all participate in the same player-selectable resolution experience, respecting payment/sequence/choice groups.
- [ ] **Design:** Temporary delayed effects such as `End of Turn: {Gain Credit: 2}` must survive initial resolution, resolve at the scheduled time, and expire correctly. Temporary next-Bargain and next-upgrade discounts must expire correctly.
- [ ] **Design:** Faction identity changes and discounts need scoped lifetimes (end turn, while source in play, until next purchase/use).
- [ ] **Design:** Effects activated by exhausting an ally require a ready, legal ally; nested subordinate effects remain distinct (e.g. optional Bargain plus separate level gates).

## F. Open questions / verification checklist

- [ ] Receive typed rulebook or PDF; normalize terminology and timing windows for all keywords. Official wording takes priority over speculative engine behavior.
- [ ] Confirm optional forfeiture granularity for compound `Pay`, `Sequence`, conditional, and nested effects.
- [ ] Confirm interaction between play-order selection and dependent sequences: linked steps cannot be reordered across their dependency.
- [ ] Confirm whether a currently resolving card counts as in play for Focus/Unite, Conspire, Bargain and upgrades; current discussion assumes yes.
- [ ] Confirm the exact max/min values and payment legality for HP/armor, especially health loss at low HP.
- [ ] Confirm targeted damage when a threat is defeated mid-sequence, immediately flipping its sleeve into hand and possible on-defeat triggers.
- [ ] Confirm delayed effects and ability durations if the source is discarded/eliminated earlier than expected.
- [ ] Confirm constraints for first-card-played-this-turn random discount, including 0/1 eligible cards and target leaves/re-enters hand.
- [ ] Confirm whether card abilities have faction/card-specific exceptions beyond the shared rules.
- [ ] Verify actual game numbers with **final Excel workbook**, not example screenshots or assistant-authored sample values.

## G. Engineering implementation checklist (proposed order)

1. [ ] Build **card grammar import and AST** from Excel rows: group vs ordered sequence vs mutually exclusive choice vs payment vs conditions; preserve original text and surface parse ambiguities.
2. [ ] Build **effect resolution stack/decision queue** with flexible independent-effect ordering, linked sequencing, pausing and resuming.
3. [ ] Add **payment transaction/outcome model**, `If Possible`, and exact prior-outcome predicates (`If Defeated`, previous zone, actual health/armor lost).
4. [ ] Add **evaluation context**, quantity expressions, strict comparisons, faction counts, state/turn counters and level gates.
5. [ ] Add **events**, trigger registration, continuous modifiers, scoped durations, expiring discounts and end-of-turn delayed effects.
6. [ ] Add generic **target selection/card movement** including searches, looking at level piles, random selection, zone-origin tracking, entire-sleeve elimination.
7. [ ] Add tests per real card: normal, declined, impossible, edge case, nested trigger, ordering difference, zone integrity, seeded randomness, save/restore.
8. [ ] Populate catalog and scenario setup from final user-provided workbook; separately validate official rulebook compliance.
9. [ ] Add UI affordances: unresolved-effect tray, ordered effect choices, explicit pay/skip actions, eligible-target highlighting, event history and sleeve inspector.

**Maintenance rule:** Every new ambiguous card belongs here with: original workbook cell/card ID, proposed meaning, rulebook decision, engine feature, regression tests and implementation status.
