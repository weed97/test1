# 마법 체계 (Magic System)

## 원칙

1. **마나(Mana)** — 모든 마법 시전의 자원. 캐릭터의 `stats.mana` / `stats.max_mana`로 관리.
2. **원소(Element)** — fire, water, earth, air, light, shadow, arcane 중 하나 이상.
3. **등급(Tier)** — 0(戏法) ~ 5(전설). 등급당 기본 마나 비용 = `tier * 8 + 4`.
4. **시전 판정** — `d20 + spellcasting_mod + tier_penalty` vs `DC 10 + tier * 2`.
   - tier_penalty = `-tier` (고위 마법일수록 어려움)
5. **대실패** — natural 1이면 역효과(자해, 마나 소진, 주변 왜곡) 발생.
6. **대성공** — natural 20이면 추가 효과(광역, 지속, 강화) 1회.

## 원소 상성

| 공격 → 방어 | fire | water | earth | air | light | shadow |
|-------------|------|-------|-------|-----|-------|--------|
| fire        | —    | 약    | 보통  | 강  | 보통  | 강     |
| water       | 강   | —     | 약    | 보통| 강    | 보통   |
| earth       | 보통 | 강    | —     | 약  | 보통  | 강     |
| air         | 약   | 보통  | 강    | —   | 보통  | 약     |
| light       | 보통 | 약    | 보통  | 보통| —     | 강     |
| shadow      | 약   | 보통  | 약    | 강  | 약    | —      |

- **강**: 데미지 ×1.5, **약**: ×0.5, **보통**: ×1.0

## 금지 및 제약

- 동일 턴에 tier 3 이상 마법 2회 시전 불가(과부하).
- shadow 원소는 `world.tension >= 0.5`일 때 위력 +20%, 실패 시 tension +0.05.
- light 원소는 `time_of_day == night`일 때 DC +2.

## 상태 이상

| 상태     | 효과                          | 해제              |
|----------|-------------------------------|-------------------|
| burning  | 턴당 HP 3%                    | water 계열        |
| frozen   | 행동 1회 스킵                 | fire 계열         |
| silenced | 마법 시전 불가 2턴            | light/heal        |
| cursed   | 모든 판정 -2, 3턴             | 제사/고급 light   |
