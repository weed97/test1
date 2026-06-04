# Economy

## Currency
Coins, base unit **copper (c)**. `100 copper = 1 silver (s)`, `100 silver = 1 gold (g)`.
Prices are quoted in copper internally.

## Prices & the market
- Every tradeable good has a **base value** and a **market index** (a multiplier near
  1.0) that drifts over time and reacts to world events.
- Merchants **sell above** and **buy below** the market price. Players typically receive
  ~45% of market value when selling.
- A good harvest lowers food prices; a war scare raises weapons and armour; a plague
  raises potions. World events apply `market` multipliers per category tag
  (e.g. `weapon`, `food`, `potion`, `luxury`, `ore`).

## What moves a price (for the world-event role)
- supply shocks (mine strike, failed harvest), demand shocks (war, festival),
  disruption (bandits on roads), confidence (royal wedding, dragon sighting).
- Keep multipliers modest: 0.7–1.4 per event. The market mean-reverts toward 1.0.

## Reputation & charisma at the till
- Standing with a merchant's faction discounts (friendly/honored) or marks up
  (unfriendly/hostile) prices.
- A charismatic haggler shaves a little more off. Be consistent with the character's
  greed trait.

## Limits (enforce)
1. No infinite money: selling crashes a good's local price; buying nudges it up.
2. Merchants have limited coin; very large sales may exceed their purse.
