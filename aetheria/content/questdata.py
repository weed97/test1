"""The quests of Aldermere, from cellar rats to the Frostpeak Wyrm."""

from __future__ import annotations

from ..quest import Objective, ObjectiveType, Quest, QuestReward
from ..state import World


def register_quests(world: World) -> None:
    reg = world.quests
    add = reg.register
    OT = ObjectiveType

    add(Quest(
        "q_rats", "Cellar Pests", giver_id="bram",
        summary="Bram's cellar is overrun with giant rats. Clear them out.",
        objectives=(Objective(OT.KILL, "giant_rat", 5,
                              "Exterminate giant rats in the Stag's cellar"),),
        reward=QuestReward(xp=60, gold=40, items=(("ale", 2),),
                           reputation=(("merchants", 8),)),
        faction="merchants",
        on_offer="Down the cellar steps, mind your ankles. Bring me five of the brutes' tails... "
                 "or just clear 'em, I'll take your word.",
        on_complete="Bless you! The ale's safe again. Here's a little something."))

    add(Quest(
        "q_herbs", "The Healer's Errand", giver_id="elin",
        summary="Sister Elin needs moonpetal herbs, which bloom by night in the wood.",
        objectives=(Objective(OT.COLLECT, "moonpetal", 4,
                              "Gather moonpetal (forage at night in the Thornwood)"),),
        reward=QuestReward(xp=70, gold=30, items=(("health_potion", 2),),
                           reputation=(("dawn", 10),)),
        faction="dawn",
        on_offer="Moonpetal only opens under the moon, out past the treeline. Four blooms "
                 "should restock my stores.",
        on_complete="The Light thanks you, and so do I. These will save lives."))

    add(Quest(
        "q_ore", "Steel and Stone", giver_id="mira",
        summary="Mira needs iron ore to keep the forge running. Mine or buy six.",
        objectives=(Objective(OT.DELIVER, "iron_ore", 6,
                              "Deliver iron ore to Mira (mine it in the Frostpeaks)"),),
        reward=QuestReward(xp=80, gold=60, items=(("iron_sword", 1),),
                           reputation=(("merchants", 8),)),
        faction="merchants",
        on_offer="No ore, no steel. The mine's gone dangerous, but six good lumps and "
                 "we're square.",
        on_complete="Now THAT'S ore. Take this blade — I made it myself."))

    add(Quest(
        "q_bandits", "Road Wardens", giver_id="doran",
        summary="Captain Doran wants the Redhand bandits thinned out on the roads.",
        objectives=(Objective(OT.KILL, "bandit", 6,
                              "Slay Redhand bandits on the roads and Thornwood"),),
        reward=QuestReward(xp=140, gold=120, items=(("iron_shield", 1),),
                           reputation=(("crown", 15), ("redhand", -20)),
                           title="Road Warden"),
        faction="crown", prerequisites=(),
        on_offer="Six of the Redhand, and the roads breathe easier. The Crown remembers "
                 "those who serve it.",
        on_complete="Cleanly done. You've the makings of a King's man. Wear this with pride."))

    add(Quest(
        "q_locket", "A Lady's Locket", giver_id="lysa",
        summary="Lysa wants a silver locket lost to bandits on the Thornwood road.",
        objectives=(Objective(OT.COLLECT, "lost_locket", 1,
                              "Recover the lost locket (carried by a bandit)"),),
        reward=QuestReward(xp=90, gold=110, items=(("dagger", 1),),
                           reputation=(("shadowhand", 15),)),
        faction="shadowhand",
        on_offer="A bandit lifted a certain locket from a certain lady. Get it back, "
                 "discreetly, and the Hand pays well.",
        on_complete="Mm. The very one. You've a future in quiet work, friend."))

    add(Quest(
        "q_relic", "What the Fen Keeps", giver_id="morwenna",
        summary="Morwenna bids you retrieve the relic from the drowned ruins — carefully.",
        objectives=(
            Objective(OT.REACH, "sunken_ruins", 1, "Reach the Sunken Ruins"),
            Objective(OT.DELIVER, "sunken_relic", 1,
                      "Recover the Sunken Relic (search the ruined pedestal)"),
        ),
        reward=QuestReward(xp=200, gold=150, items=(("mana_crystal", 2),),
                           reputation=(("fenfolk", 20),), ability="bless"),
        faction="fenfolk", prerequisites=(),
        on_offer="In the sunken halls lies a relic that hums like a struck bell. Bring it to "
                 "me — and do not, whatever you do, use it.",
        on_complete="Good. It is safer in my keeping than on a pedestal for any fool to seize."))

    add(Quest(
        "q_tome", "Forbidden Pages", giver_id="velian",
        summary="Archmagus Velian seeks an ancient tome lost in the Forgotten Shrine.",
        objectives=(Objective(OT.COLLECT, "ancient_tome", 1,
                              "Recover the Ancient Tome (search the shrine altar)"),),
        reward=QuestReward(xp=180, gold=120, items=(("amulet_focus", 1),),
                           reputation=(("conclave", 20),), ability="holy_smite"),
        faction="conclave",
        on_offer="A tome was lost to the Thornwood shrine generations ago. Its pages may "
                 "hold the key to the Wyrm. Retrieve it for the Conclave.",
        on_complete="Remarkable. These passages confirm my fears — and our only hope."))

    add(Quest(
        "q_dragon", "The Frostpeak Wyrm", giver_id="halric",
        summary="Steward Halric calls for a hero to slay Skorvaxis, the Frostpeak Wyrm.",
        objectives=(Objective(OT.KILL, "dragon", 1,
                              "Slay Skorvaxis in the Wyrm's Roost atop the Frostpeaks"),),
        reward=QuestReward(xp=800, gold=2000, items=(("ring_vigor", 1),),
                           reputation=(("crown", 50), ("dawn", 25), ("conclave", 25)),
                           title="Dragonslayer"),
        faction="crown", prerequisites=("q_tome",),
        on_offer="The Wyrm stirs atop the Frostpeaks. End it, and the Crown — and the realm — "
                 "are forever in your debt. Few will return. Will you?",
        on_complete="By all the gods... you DID it. Rise, Dragonslayer. Aldermere is yours to "
                    "call friend, now and always."))
