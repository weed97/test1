"""VariableManager - JSON 기반 변수의 로드/저장/실시간 갱신.

8개의 예측 불가 변수를 중심으로, 헌터/성좌/시뮬레이션 설정을 모두 관리한다.
[외부 업데이트] 질의를 통해 런타임 중에도 값이 실시간으로 변경될 수 있다.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

# 8개 예측 불가 변수의 정식 이름 (순서 고정).
UNPREDICTABLE_KEYS: Tuple[str, ...] = (
    "randomness_intensity",
    "fate_deviation",
    "constellation_mood",
    "probability_distortion",
    "event_mutation_rate",
    "crisis_escalation",
    "luck_factor",
    "chaos_resonance",
)


class VariableManager:
    """variables.json 을 메모리에 올려두고 실시간 수정/저장을 담당한다."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.data: Dict[str, Any] = {}
        self.load()

    # ------------------------------------------------------------------ #
    # 로드 / 저장
    # ------------------------------------------------------------------ #
    def load(self) -> None:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"변수 설정 파일을 찾을 수 없습니다: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as fh:
            self.data = json.load(fh)
        self._validate()

    def save(self) -> None:
        """현재 변수 상태를 JSON 파일에 다시 기록한다 (실시간 영속화)."""
        with open(self.config_path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)

    def _validate(self) -> None:
        uv = self.data.get("unpredictable_variables", {})
        missing = [k for k in UNPREDICTABLE_KEYS if k not in uv]
        if missing:
            raise ValueError(f"예측 불가 변수 누락: {', '.join(missing)}")

    # ------------------------------------------------------------------ #
    # 예측 불가 변수 접근
    # ------------------------------------------------------------------ #
    def uvar(self, key: str) -> float:
        """예측 불가 변수의 현재 값을 반환한다."""
        if key not in UNPREDICTABLE_KEYS:
            raise KeyError(f"알 수 없는 예측 불가 변수: {key}")
        return float(self.data["unpredictable_variables"][key]["value"])

    def uvars(self) -> Dict[str, float]:
        """8개 예측 불가 변수를 {이름: 값} 딕셔너리로 반환한다."""
        return {k: self.uvar(k) for k in UNPREDICTABLE_KEYS}

    def uvar_meta(self, key: str) -> Dict[str, Any]:
        return self.data["unpredictable_variables"][key]

    def set_uvar(self, key: str, value: float) -> float:
        """예측 불가 변수를 min/max 범위로 보정하여 설정하고, 보정된 값을 반환한다."""
        meta = self.data["unpredictable_variables"][key]
        lo = float(meta.get("min", float("-inf")))
        hi = float(meta.get("max", float("inf")))
        clamped = max(lo, min(float(value), hi))
        meta["value"] = clamped
        return clamped

    # ------------------------------------------------------------------ #
    # 일반 설정 접근 (점 표기 경로 지원: "hunter.hp" 등)
    # ------------------------------------------------------------------ #
    def get_path(self, path: str) -> Any:
        node: Any = self.data
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                raise KeyError(f"경로를 찾을 수 없습니다: {path}")
        return node

    def set_path(self, path: str, value: Any) -> Any:
        """점 표기 경로에 값을 설정한다.

        예측 불가 변수(unpredictable_variables.*)는 자동으로 범위 보정된다.
        'foo' 같은 단일 키는 예측 불가 변수의 단축 이름으로 우선 해석한다.
        존재하지 않는 키는 KeyError 를 발생시킨다(임의 키 생성 방지).
        """
        # 단축 이름: 예측 불가 변수 이름이면 그쪽으로 라우팅
        if path in UNPREDICTABLE_KEYS:
            return self.set_uvar(path, _coerce(value))

        parts = path.split(".")
        if parts[0] == "unpredictable_variables" and len(parts) >= 2:
            key = parts[1]
            if key in UNPREDICTABLE_KEYS and (len(parts) == 2 or parts[2] == "value"):
                return self.set_uvar(key, _coerce(value))
            raise KeyError(f"수정할 수 없는 키입니다: {path}")

        if len(parts) < 2:
            raise KeyError(f"수정할 수 없는 키입니다: {path}")

        node: Any = self.data
        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node or not isinstance(node[part], dict):
                raise KeyError(f"수정할 수 없는 키입니다: {path}")
            node = node[part]
        if parts[-1] not in node:
            raise KeyError(f"수정할 수 없는 키입니다: {path}")
        coerced = _coerce_like(node.get(parts[-1]), value)
        node[parts[-1]] = coerced
        return coerced

    def hunter_config(self) -> Dict[str, Any]:
        return dict(self.data.get("hunter", {}))

    def constellation_config(self) -> Dict[str, Any]:
        return dict(self.data.get("constellation", {}))

    def simulation_config(self) -> Dict[str, Any]:
        return dict(self.data.get("simulation", {}))

    def updatable_keys(self) -> List[str]:
        """[외부 업데이트] 질의에서 수정 가능한 키 목록."""
        keys = list(UNPREDICTABLE_KEYS)
        for section in ("hunter", "constellation", "simulation"):
            for k in self.data.get(section, {}):
                keys.append(f"{section}.{k}")
        return keys


def _coerce(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"숫자로 변환할 수 없는 값: {value!r}")


def _coerce_like(reference: Any, value: Any) -> Any:
    """기존 값의 타입에 맞춰 입력 문자열을 변환한다."""
    if isinstance(value, str):
        text = value.strip()
        if isinstance(reference, bool):
            return text.lower() in ("1", "true", "yes", "on", "참")
        if isinstance(reference, int):
            return int(float(text))
        if isinstance(reference, float):
            return float(text)
        if reference is None:
            # null 자리: 숫자면 숫자로, 아니면 문자열
            try:
                num = float(text)
                return int(num) if num.is_integer() else num
            except ValueError:
                return text
        return text
    return value
