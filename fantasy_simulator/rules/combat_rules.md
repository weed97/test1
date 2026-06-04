# Combat Rules

Combat is **turn-based and dice-adjudicated**. The engine (`utils/dice.py`) rolls; the
referee narrates a result *consistent with the roll*. Never let narration contradict the
mechanical outcome.

## Core check
- **Attack:** d100 vs a hit threshold of `accuracy - evasion` (clamped 5–95).
- **Ability check:** d20 + relevant modifier vs a difficulty (DC). Meet or beat to succeed.
- **Opposed check:** both sides roll d20 + modifier; higher wins (attacker wins ties).

## Damage
- Physical: weapon dice + Strength/Dexterity, reduced by the target's Defense.
- Magical: spell power + Intelligence/Wisdom; partly bypasses armour.
- **Critical hit** (small chance, scales with Dexterity): ~1.8× damage.
- **Status effects:** poison/burning/bleed (damage over time), stun (lose a turn),
  blessed/shielded/enraged/hasted (buffs). Apply duration in turns.

## Resolution outcomes the referee may use
- **Decisive win** (large margin): the loser falls, flees, or is captured.
- **Narrow win:** the loser is wounded but escapes or yields.
- **Draw / stalemate:** both withdraw; tension lingers.

## Fairness limits (enforce)
1. Named characters do not die from a single unlucky roll unless the fiction clearly
   warrants it; prefer wounds, capture, or retreat.
2. A defeated player is not deleted — they wake at the Temple, weakened and poorer.
3. Outcomes must follow the dice. If the roll says failure, narrate failure.

## Difficulty guide (DC)
trivial 5 · easy 10 · moderate 15 · hard 20 · heroic 25 · legendary 30.
