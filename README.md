# Text Fantasy MMORPG Simulator

A Python standard-library medieval fantasy text MMORPG simulator set in the
Eldermist valley. It focuses on NPC dialogue, quests, faction reputation,
exploration, turn-based combat, loot, crafting, shops, secrets, world events,
and JSON saves.

## Run

```bash
python -m fantasy_mmorpg --name Aria --class mage
```

Available classes:

- `knight`
- `ranger`
- `mage`
- `cleric`
- `rogue`
- `commoner`

The CLI autosaves to `saves/eldermist_save.json` when you quit.

## Example commands

```text
look
talk mira
ask mira about rumors
accept rats
fight
attack
complete rats
go north
gather moonleaf
search
inventory
equip warden shield
shop
buy healing draught
recipes
craft healing draught
quests
journal
factions
save
quit
```

Names are fuzzy, so `go woods`, `talk ansem`, and `accept herbs` work.

## World features

- 11 connected zones, from Eldermist Village to Dragonwake Crater.
- 15 named NPCs with distinct factions, personalities, shops, and dialogue topics.
- 8 quests covering combat, gathering, exploration, lore recovery, and endgame dragon threats.
- 10 enemy types with loot tables and abilities.
- 30+ items across weapons, armor, potions, materials, quest items, lore relics, and tools.
- Faction reputation for Hearthfolk, Crownwardens, Silver Chapel, Thornbound Circle,
  Black Banner, Ashen Covenant, and the Old Kingdom.
- Discoverable secrets in every major location.
- Random world events that alter the valley's mood and reputation.
- JSON save/load support for player, world, and active combat state.

## Test

```bash
python -m unittest
```