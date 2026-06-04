"""Item catalogue: weapons, armour, consumables, materials, treasures and lore."""

from __future__ import annotations

from ..items import EquipSlot, ItemTemplate, ItemType, Rarity
from ..state import World


def register_items(world: World) -> None:
    reg = world.items
    add = reg.register

    # ---- weapons (main hand) ----------------------------------------------
    add(ItemTemplate("rusty_sword", "Rusty Sword", ItemType.WEAPON,
                     "A pitted blade, better than fists. Just.", base_value=8, weight=3.0,
                     slot=EquipSlot.MAIN_HAND, attack_bonus=1, damage_dice=(1, 6),
                     tags=("weapon", "blade")))
    add(ItemTemplate("iron_sword", "Iron Sword", ItemType.WEAPON,
                     "A reliable soldier's blade.", base_value=45, weight=3.5,
                     slot=EquipSlot.MAIN_HAND, attack_bonus=3, damage_dice=(1, 8),
                     rarity=Rarity.COMMON, tags=("weapon", "blade")))
    add(ItemTemplate("steel_longsword", "Steel Longsword", ItemType.WEAPON,
                     "Balanced steel, keen and bright.", base_value=140, weight=4.0,
                     slot=EquipSlot.MAIN_HAND, attack_bonus=5, damage_dice=(1, 10),
                     rarity=Rarity.UNCOMMON, tags=("weapon", "blade")))
    add(ItemTemplate("war_axe", "War Axe", ItemType.WEAPON,
                     "Heavy and brutal; it bites deep.", base_value=110, weight=6.0,
                     slot=EquipSlot.MAIN_HAND, attack_bonus=4, damage_dice=(1, 12),
                     rarity=Rarity.UNCOMMON, tags=("weapon", "axe")))
    add(ItemTemplate("hunting_bow", "Hunting Bow", ItemType.WEAPON,
                     "A supple yew bow for the patient.", base_value=70, weight=2.0,
                     slot=EquipSlot.MAIN_HAND, attack_bonus=3, damage_dice=(1, 8),
                     damage_type="physical", tags=("weapon", "bow")))
    add(ItemTemplate("dagger", "Fine Dagger", ItemType.WEAPON,
                     "Quick, quiet and deadly in the right hands.", base_value=35, weight=1.0,
                     slot=EquipSlot.MAIN_HAND, attack_bonus=2, damage_dice=(1, 6),
                     tags=("weapon", "blade", "light")))
    add(ItemTemplate("oak_staff", "Oak Staff", ItemType.WEAPON,
                     "A focus for channelling the arcane.", base_value=60, weight=2.5,
                     slot=EquipSlot.MAIN_HAND, attack_bonus=1, damage_dice=(1, 4),
                     rarity=Rarity.COMMON, tags=("weapon", "staff", "arcane")))
    add(ItemTemplate("mace_of_dawn", "Mace of the Dawn", ItemType.WEAPON,
                     "Blessed steel that glows with soft light.", base_value=200, weight=4.5,
                     slot=EquipSlot.MAIN_HAND, attack_bonus=5, damage_dice=(1, 8),
                     damage_type="holy", rarity=Rarity.RARE, tags=("weapon", "blunt", "holy")))
    add(ItemTemplate("dragonfang", "Dragonfang", ItemType.WEAPON,
                     "A blade forged from a dragon's tooth; it hums with heat.",
                     base_value=600, weight=4.0, slot=EquipSlot.MAIN_HAND,
                     attack_bonus=9, damage_dice=(2, 8), damage_type="fire",
                     rarity=Rarity.LEGENDARY, tags=("weapon", "blade", "legendary")))

    # ---- off-hand / shields ------------------------------------------------
    add(ItemTemplate("wooden_shield", "Wooden Shield", ItemType.SHIELD,
                     "Planks and a boss of iron.", base_value=20, weight=4.0,
                     slot=EquipSlot.OFF_HAND, defense_bonus=2, tags=("armor", "shield")))
    add(ItemTemplate("iron_shield", "Iron Shield", ItemType.SHIELD,
                     "A sturdy round shield.", base_value=80, weight=6.0,
                     slot=EquipSlot.OFF_HAND, defense_bonus=4, rarity=Rarity.UNCOMMON,
                     tags=("armor", "shield")))

    # ---- armour (body / head / etc) ---------------------------------------
    add(ItemTemplate("leather_armor", "Leather Armor", ItemType.ARMOR,
                     "Boiled leather; light and quiet.", base_value=40, weight=8.0,
                     slot=EquipSlot.BODY, defense_bonus=3, tags=("armor", "light")))
    add(ItemTemplate("chain_mail", "Chain Mail", ItemType.ARMOR,
                     "Interlocking rings turn aside blades.", base_value=130, weight=18.0,
                     slot=EquipSlot.BODY, defense_bonus=6, rarity=Rarity.UNCOMMON,
                     tags=("armor", "medium")))
    add(ItemTemplate("plate_armor", "Plate Armor", ItemType.ARMOR,
                     "A knight's full harness of steel.", base_value=320, weight=30.0,
                     slot=EquipSlot.BODY, defense_bonus=10, rarity=Rarity.RARE,
                     tags=("armor", "heavy")))
    add(ItemTemplate("mage_robe", "Enchanted Robe", ItemType.ARMOR,
                     "Woven with threads that turn aside hostile magic.", base_value=110,
                     weight=3.0, slot=EquipSlot.BODY, defense_bonus=2,
                     rarity=Rarity.UNCOMMON, tags=("armor", "cloth", "arcane")))
    add(ItemTemplate("iron_helm", "Iron Helm", ItemType.ARMOR,
                     "A dented but serviceable helmet.", base_value=35, weight=4.0,
                     slot=EquipSlot.HEAD, defense_bonus=2, tags=("armor",)))
    add(ItemTemplate("leather_boots", "Leather Boots", ItemType.ARMOR,
                     "Worn but comfortable.", base_value=18, weight=2.0,
                     slot=EquipSlot.FEET, defense_bonus=1, tags=("armor", "light")))

    # ---- trinkets / rings / amulets ---------------------------------------
    add(ItemTemplate("ring_vigor", "Ring of Vigor", ItemType.TRINKET,
                     "A warm band that bolsters the body.", base_value=150, weight=0.1,
                     slot=EquipSlot.RING, defense_bonus=2, rarity=Rarity.RARE,
                     tags=("trinket",)))
    add(ItemTemplate("amulet_focus", "Amulet of Focus", ItemType.TRINKET,
                     "Sharpens the wielder's arcane senses.", base_value=180, weight=0.1,
                     slot=EquipSlot.NECK, attack_bonus=2, rarity=Rarity.RARE,
                     tags=("trinket", "arcane")))

    # ---- consumables -------------------------------------------------------
    add(ItemTemplate("minor_health_potion", "Minor Health Potion", ItemType.CONSUMABLE,
                     "A red draught that knits small wounds.", base_value=15, weight=0.3,
                     stackable=True, max_stack=20, heal_amount=25, tags=("potion",)))
    add(ItemTemplate("health_potion", "Health Potion", ItemType.CONSUMABLE,
                     "A potent restorative.", base_value=40, weight=0.3, stackable=True,
                     max_stack=20, heal_amount=60, rarity=Rarity.UNCOMMON, tags=("potion",)))
    add(ItemTemplate("mana_potion", "Mana Potion", ItemType.CONSUMABLE,
                     "Blue and bitter; restores the arcane reserve.", base_value=35,
                     weight=0.3, stackable=True, max_stack=20, mana_amount=45,
                     tags=("potion", "arcane")))
    add(ItemTemplate("stamina_draught", "Stamina Draught", ItemType.CONSUMABLE,
                     "An herbal tonic that renews vigour.", base_value=20, weight=0.3,
                     stackable=True, max_stack=20, stamina_amount=40, tags=("potion",)))
    add(ItemTemplate("antidote", "Antidote", ItemType.CONSUMABLE,
                     "Neutralises most common venoms.", base_value=25, weight=0.2,
                     stackable=True, max_stack=10, effect="regeneration", tags=("potion",)))
    add(ItemTemplate("elixir_might", "Elixir of Might", ItemType.CONSUMABLE,
                     "Fills the drinker with battle-fury.", base_value=70, weight=0.3,
                     stackable=True, max_stack=5, effect="enraged", rarity=Rarity.UNCOMMON,
                     tags=("potion",)))

    # ---- food --------------------------------------------------------------
    add(ItemTemplate("bread", "Loaf of Bread", ItemType.FOOD,
                     "Crusty and filling.", base_value=2, weight=0.5, stackable=True,
                     max_stack=20, heal_amount=8, effect="well_fed", tags=("food",)))
    add(ItemTemplate("ale", "Tankard of Ale", ItemType.FOOD,
                     "Foamy and warming.", base_value=3, weight=0.5, stackable=True,
                     max_stack=20, stamina_amount=10, tags=("food", "luxury")))
    add(ItemTemplate("cheese", "Wheel of Cheese", ItemType.FOOD,
                     "Sharp farmhouse cheese.", base_value=5, weight=0.6, stackable=True,
                     max_stack=10, heal_amount=12, effect="well_fed", tags=("food",)))
    add(ItemTemplate("venison", "Roast Venison", ItemType.FOOD,
                     "A hearty meal of the hunt.", base_value=12, weight=0.8, stackable=True,
                     max_stack=10, heal_amount=20, effect="well_fed", tags=("food",)))

    # ---- crafting materials -----------------------------------------------
    for mat_id, name, value, tags, desc in [
        ("iron_ore", "Iron Ore", 6, ("material", "ore"), "Raw ore flecked with metal."),
        ("iron_ingot", "Iron Ingot", 14, ("material", "metal"), "A bar of smelted iron."),
        ("coal", "Lump of Coal", 3, ("material",), "Fuel for the forge."),
        ("leather_scrap", "Leather Scrap", 4, ("material", "leather"), "A piece of cured hide."),
        ("oak_wood", "Oak Wood", 3, ("material", "wood"), "A length of seasoned oak."),
        ("linen", "Bolt of Linen", 5, ("material", "cloth"), "Plain woven cloth."),
        ("moonpetal", "Moonpetal Herb", 8, ("material", "herb"), "A silver flower that blooms at night."),
        ("redroot", "Redroot", 6, ("material", "herb"), "A pungent crimson root."),
        ("mana_crystal", "Mana Crystal", 40, ("material", "gem", "arcane"), "A shard humming with power."),
        ("ruby", "Ruby", 60, ("material", "gem"), "A blood-red gemstone."),
        ("dragon_scale", "Dragon Scale", 150, ("material",), "A scale hard as steel and warm to the touch."),
        ("wolf_pelt", "Wolf Pelt", 10, ("material", "leather"), "A thick grey pelt."),
        ("spider_silk", "Spider Silk", 12, ("material", "cloth"), "Astonishingly strong thread."),
    ]:
        add(ItemTemplate(mat_id, name, ItemType.MATERIAL, desc, base_value=value,
                         weight=0.5, stackable=True, max_stack=50, tags=tags))

    # ---- treasures (for selling) ------------------------------------------
    add(ItemTemplate("silver_goblet", "Silver Goblet", ItemType.TREASURE,
                     "A finely wrought drinking cup.", base_value=45, weight=0.8,
                     stackable=True, max_stack=10, rarity=Rarity.UNCOMMON,
                     tags=("treasure", "luxury")))
    add(ItemTemplate("gold_idol", "Golden Idol", ItemType.TREASURE,
                     "A small idol of some forgotten god.", base_value=120, weight=2.0,
                     rarity=Rarity.RARE, tags=("treasure", "luxury")))
    add(ItemTemplate("ancient_coin", "Ancient Coin", ItemType.TREASURE,
                     "Stamped with a king long dead.", base_value=25, weight=0.05,
                     stackable=True, max_stack=99, tags=("treasure",)))

    # ---- quest items -------------------------------------------------------
    add(ItemTemplate("rat_tail", "Rat Tail", ItemType.QUEST,
                     "Proof of pest control.", base_value=1, weight=0.1,
                     stackable=True, max_stack=99, tags=("quest",)))
    add(ItemTemplate("bandit_insignia", "Bandit Insignia", ItemType.QUEST,
                     "A crude red-handed badge.", base_value=1, weight=0.1,
                     stackable=True, max_stack=99, tags=("quest",)))
    add(ItemTemplate("lost_locket", "Lost Locket", ItemType.QUEST,
                     "A silver locket with a faded portrait inside.", base_value=1,
                     weight=0.1, tags=("quest",)))
    add(ItemTemplate("sunken_relic", "Sunken Relic", ItemType.QUEST,
                     "An artefact slick with fenwater, thrumming faintly.", base_value=1,
                     weight=1.0, rarity=Rarity.EPIC, tags=("quest",)))
    add(ItemTemplate("ancient_tome", "Ancient Tome", ItemType.BOOK,
                     "Its pages whisper of the Wyrm of Frostpeak.", base_value=80,
                     weight=1.5, rarity=Rarity.RARE, tags=("book", "quest")))
