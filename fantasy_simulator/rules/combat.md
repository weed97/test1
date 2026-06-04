# 전투 규칙 (Combat Rules)

## 턴 구조

1. **선언(Declare)** — 각 참가자가 행동 선택(공격/방어/마법/아이템/도주).
2. **속도 해결(Initiative)** — `d20 + agility_mod`, 높은 순서대로 해결.
3. **해결(Resolve)** — 데미지·상태·마나 소모 적용.
4. **정리(Cleanup)** — 지속 효과, 사망/기절 처리, `world_state.combat` 갱신.

## 공격 판정

```
hit_roll = d20 + attack_mod + situational_bonus
hit_dc   = 10 + target.defense_mod + cover_bonus

hit_roll >= hit_dc  → 명중
natural 20          → 치명타 (데미지 ×2)
natural 1           → 빗나감 + 다음 턴 -1
```

## 데미지

```
base_damage = weapon.damage + strength_mod (물리) 또는 spell.power (마법)
final_damage = max(1, base_damage - target.armor_reduction)
```

- **방어 태세**: 해당 턴 받는 데미지 ×0.5, 공격 불가.
- **엄폐(Cover)**: +2 ~ +5 AC 보너스.

## 도주

- `d20 + agility_mod` vs `10 + highest_enemy.agility_mod`
- 성공 시 전투 종료, `combat` 필드 null.
- 실패 시 적의 기회공격 1회.

## 전투 종료 조건

- 한쪽 전원 HP ≤ 0 (기절 또는 사망 — 캐릭터 `flags.knockout_only` 참조)
- 도주 성공
- 협상/이벤트로 강제 종료 (`event_log`에 기록)

## 위험도 스케일

| threat_level | 적 HP 배율 | 적 공격 배율 | 보상 배율 |
|--------------|------------|--------------|-----------|
| trivial      | 0.5        | 0.5          | 0.3       |
| normal       | 1.0        | 1.0          | 1.0       |
| dangerous    | 1.5        | 1.3          | 1.5       |
| deadly       | 2.0        | 1.6          | 2.5       |
