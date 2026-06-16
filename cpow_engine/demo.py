"""CPoW MVP 데모 — Heat 속성 오브젝트 생성 → 에너지 발생."""

from __future__ import annotations

import argparse
import json
import sys

from cpow_engine.chain.bridge import OffChainBridge
from cpow_engine.chain.genesis import load_genesis
from cpow_engine.areas import AreaRegistry, SimulationMode
from cpow_engine.collab import CollaborativeWorld
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.cpow import CPoWEngine
from cpow_engine.engine import SimulationEngine
from cpow_engine.physics import (
    create_heat_object,
    create_material_object,
)
from cpow_engine.shared_state import ConflictStrategy, StatePatch


def run_demo(seed: int = 42, ticks: int = 3) -> None:
    engine = SimulationEngine()

    heat = create_heat_object("user_alpha", "창조된 열원", heat_intensity=100.0)
    metal = create_material_object(
        "user_alpha",
        "철괴",
        "iron",
        thermal_conductivity=0.8,
        melting_point=1538.0,
    )

    print("=== CPoW Simulation Engine MVP ===")
    print(f"시드: {seed} | 틱: {ticks}")
    print()

    engine.create_object(heat)
    engine.create_object(metal)
    engine.connect_objects(heat.id, metal.id)

    print(f"[창조] {heat.label} (heat_intensity={100.0})")
    print(f"[창조] {metal.label} (material_type=iron)")
    print(f"[연결] {heat.label} → {metal.label}")
    print()

    for t in range(1, ticks + 1):
        delta, score = engine.tick()
        print(f"--- Tick {t} ---")
        for interaction in delta.interactions:
            target = interaction.target_id or "(환경)"
            print(
                f"  상호작용: {interaction.effect_type} "
                f"({interaction.source_id} → {target}) "
                f"에너지 Δ={interaction.energy_delta:.2f}"
            )
        if score:
            print(
                f"  CPoW 점수: 에너지={score.energy:.2f} "
                f"경제가치={score.economic_value:.2f} "
                f"창조성={score.creativity_score:.2f}"
            )
        print(f"  에너지 풀: {engine.state.energy_pool:.2f}")
        print(f"  엔트로피: {engine.state.entropy:.3f}")
        print()

    _demo_shared_state(engine)
    print("=== 데모 완료 ===")


def run_chain_demo(seed: int = 42, ticks: int = 5) -> None:
    genesis = load_genesis()
    engine = SimulationEngine()
    bridge = OffChainBridge(engine, genesis)

    print("=== CPoW L1 Protocol Demo ===")
    print(f"Chain: {genesis.chain_id}")
    print(f"Genesis hash: {genesis.hash[:16]}...")
    print(f"Token: {genesis.token_params.symbol} ({genesis.token_params.name})")
    print(f"Physics laws: {len(genesis.physics_laws)} immutable rules")
    print()

    heat = create_heat_object("creator_1", "프로토콜 열원", heat_intensity=100.0)
    metal = create_material_object("creator_1", "철괴", "iron")

    for obj in (heat, metal):
        result = bridge.submit_creation(obj)
        status = "✓" if result.success else "✗"
        print(f"  [{status}] On-chain 등록: {obj.label} (block #{result.block_height})")

    engine.create_object(heat)
    engine.create_object(metal)
    engine.connect_objects(heat.id, metal.id)

    total_minted = 0.0
    for t in range(1, ticks + 1):
        delta, score, submission = bridge.tick_and_maybe_submit()
        print(f"--- Tick {t} (chain height: {bridge.chain_height}) ---")
        if score:
            print(f"  CPoW: energy={score.energy:.2f} creativity={score.creativity_score:.2f}")
        if submission and submission.success:
            total_minted += submission.energy_minted
            print(f"  L1 제출: {submission.reason} (+{submission.energy_minted:.2f} NRG)")
        print(f"  Off-chain 에너지 풀: {engine.state.energy_pool:.2f}")

    balance = bridge.get_energy_balance("creator_1")
    print()
    print(f"온체인 NRG 잔액 (creator_1): {balance:.2f}")
    print(f"총 발행: {total_minted:.2f} NRG")
    print(f"최종 블록 높이: {bridge.chain_height}")
    print("=== L1 데모 완료 ===")


def run_collab_demo(ticks: int = 3) -> None:
    policy = CollabPolicy(
        pulse_interval_sec=0.0,
        min_creator_cooldown_sec=0.0,
    )
    world = CollaborativeWorld("open_alpha", policy=policy)
    creators = [
        ("alice", "작은 불", 55.0),
        ("bob", "큰 불", 500.0),
        ("carol", "중간 불", 80.0),
    ]

    print("=== CPoW 협동 오픈월드 데모 ===")
    print(f"월드: {world.world_id} | 틱: {ticks}")
    print(
        f"정책: damp={world.policy.damp_factor} "
        f"pulse={world.policy.pulse_interval_sec}s "
        f"cooldown={world.policy.min_creator_cooldown_sec}s"
    )
    print()

    for creator_id, label, heat in creators:
        obj = create_heat_object(creator_id, label, heat_intensity=heat)
        result = world.submit_creation(creator_id, obj)
        status = "✓" if result.ok else "✗"
        applied = world.state.objects.get(result.object_id)
        heat_val = applied.get_property("heat_intensity") if applied else None
        damp_note = ""
        if result.verdict and result.verdict.magnitude > world.policy.noise_threshold:
            damp_note = (
                f" (요청 {heat:.0f} → 반영 {heat_val.value:.1f}, "
                f"damp={result.verdict.applied_damping:.2f})"
            )
        print(f"  [{status}] {creator_id}: {label}{damp_note}")

    print()
    print("--- 펄스 리듬 시뮬레이션 (8초 간격) ---")
    paced = CollaborativeWorld(
        "open_alpha_paced",
        policy=CollabPolicy(
            pulse_interval_sec=8.0,
            min_creator_cooldown_sec=4.0,
        ),
        now=0.0,
    )
    for cid, label, heat in creators:
        r = paced.submit_creation(cid, create_heat_object(cid, label, heat))
        print(
            f"  큐: {cid} → {label} "
            f"(대기 {r.pending_count}명, {r.seconds_until_pulse:.0f}s 후 펄스)"
        )
    pulse = paced.advance_pulse(force=True)
    print(f"  펄스 #{pulse.pulse_number}: {pulse.applied_count}개 함께 반영")
    print()

    for t in range(1, ticks + 1):
        delta, score = world.advance_tick()
        print(f"--- Tick {t} --- noise={world.world_noise_level():.3f}")
        if score:
            print(f"  CPoW: energy={score.energy:.2f} creativity={score.creativity_score:.2f}")
        print(f"  오브젝트: {len(world.state.objects)} | 에너지 풀: {world.state.energy_pool:.2f}")

    pub = world.to_public_dict()
    print()
    print(f"기여자: {list(pub['contributors'].keys())}")
    print(f"노이즈 레벨: {pub['noise_level']}")
    print("=== 협동 데모 완료 ===")


def run_areas_demo() -> None:
    from cpow_engine.areas.roles import ContributorRole
    from cpow_engine.collab.policy import CollabPolicy
    from cpow_engine.physics import create_material_object, create_heat_object

    reg = AreaRegistry()
    area = reg.found(
        "aria",
        "불의 정원",
        mode=SimulationMode.CREATION_ADVENTURE,
        template="settlement",
    )

    print("=== CPoW 창조 에리어 데모 ===")
    print(f"에리어: {area.label} ({area.area_id})")
    print(f"모드: {area.mode.value} | 창시자: {area.founder_id}")
    print(f"법칙: {area.laws.description or area.laws.name}")
    print(f"문명: {area.economy.stage()['label']} (Lv.{area.economy.civilization_level})")
    print()

    area.world.policy = CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0)

    reg.join(area.area_id, "bob")
    area.join("carol", requested_role=ContributorRole.ADVENTURER)

    mat = create_material_object("bob", "정원 철괴", "iron")
    r1 = area.submit_creation("bob", mat, creation_type="material")
    print(f"  [협력 창조] bob: 철괴 → {r1.reason} (합의 {r1.approvals_received}/{r1.approvals_needed})")
    if r1.consensus_pending:
        area.vote_on_creation("aria", r1.proposal_id, approve=True)
        area.world.advance_pulse(force=True)
        print(f"  [합의] aria 승인 → 반영")

    adv = area.submit_adventure("carol", "explore", label="정원 외곽")
    print(f"  [모험] carol: 탐험 → {adv.reason}")

    pulse = area.advance_pulse(force=True)
    print(f"  [펄스] #{pulse.pulse_number} — 창조 반영")

    seed_id = next(iter(area.world.state.objects))
    grow = area.submit_mutation("bob", seed_id, "grow", factor=1.1)
    print(f"  [변형] bob: 심장 grow → {grow.previous_value:.1f} → {grow.new_value:.1f}")

    rename = area.submit_mutation(
        "bob", seed_id, "rename", text_value="우리의 심장",
    )
    print(f"  [이름] bob: {rename.reason}")

    obj = create_heat_object("bob", "없앨 불", 30.0)
    proposed = area.submit_creation("bob", obj, creation_type="heat")
    if proposed.consensus_pending:
        area.vote_on_creation("aria", proposed.proposal_id, approve=True)
    area.submit_mutation("bob", obj.id, "destroy")
    print(f"  [파괴] bob: 임시 오브젝트 제거")
    print(
        f"  문명 성장: {area.economy.stage()['label']} "
        f"| 시스템: {', '.join(area.economy.systems_unlocked) or '없음'}"
    )
    print(f"  오브젝트: {len(area.world.state.objects)} | 에너지: {area.world.state.energy_pool:.1f}")
    print("=== 에리어 데모 완료 ===")


def _demo_shared_state(engine: SimulationEngine) -> None:
    """다중 유저 충돌 병합 데모."""
    print("--- Shared State: 충돌 병합 ---")
    base = engine.state

    heat_v2 = create_heat_object("user_beta", "강화 열원", heat_intensity=150.0)
    heat_v2.id = list(base.objects.keys())[0]

    patch_a = StatePatch(
        author_id="user_alpha",
        base_version=base.version,
        objects={heat_v2.id: heat_v2},
        energy_delta=10.0,
    )

    heat_v3 = create_heat_object("user_gamma", "약화 열원", heat_intensity=50.0)
    heat_v3.id = heat_v2.id

    patch_b = StatePatch(
        author_id="user_gamma",
        base_version=base.version,
        objects={heat_v3.id: heat_v3},
        energy_delta=5.0,
    )

    merged = engine.apply_remote_patches([patch_a, patch_b])
    obj = list(merged.objects.values())[0]
    heat_prop = obj.get_property("heat_intensity")
    print(f"  병합된 heat_intensity: {heat_prop.value if heat_prop else 'N/A'}")
    print(f"  병합 creator: {obj.creator_id}")
    print(f"  전략: {ConflictStrategy.MERGE.value}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CPoW Simulation Engine MVP 데모"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ticks", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--chain", action="store_true", help="L1 프로토콜 통합 데모")
    parser.add_argument("--collab", action="store_true", help="협동 오픈월드 + 노이즈 감쇄 데모")
    parser.add_argument("--areas", action="store_true", help="창조 에리어 · 모드 · 문명 데모")
    args = parser.parse_args(argv)

    if args.chain:
        run_chain_demo(seed=args.seed, ticks=args.ticks)
        return 0

    if args.collab:
        run_collab_demo(ticks=args.ticks)
        return 0

    if args.areas:
        run_areas_demo()
        return 0

    if args.json:
        engine = SimulationEngine()
        heat = create_heat_object("demo", "열원", 80.0)
        engine.create_object(heat)
        delta, score = engine.tick()
        output = {
            "state": engine.state.to_dict(),
            "delta": delta.to_dict(),
            "score": score.to_dict() if score else None,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0

    run_demo(seed=args.seed, ticks=args.ticks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
