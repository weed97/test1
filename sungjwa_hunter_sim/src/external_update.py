"""[외부 업데이트] 질의 Q&A 핸들러.

입력 형식:
    [외부 업데이트] 질의: <키>=<값>
    [외부 업데이트] 질의: <키>=<값>, <키2>=<값2>
    [외부 업데이트] 질의: 목록            (수정 가능한 키 조회)
    [외부 업데이트] 질의: 상태            (현재 8개 변수 값 조회)

출력 형식:
    [외부 업데이트] 응답: ...
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .variables import UNPREDICTABLE_KEYS, VariableManager

QUERY_PREFIX = "[외부 업데이트] 질의:"
RESPONSE_PREFIX = "[외부 업데이트] 응답:"

_QUERY_RE = re.compile(r"^\s*\[외부\s*업데이트\]\s*질의\s*:\s*(?P<body>.*)$")


class ExternalUpdateHandler:
    def __init__(self, variables: VariableManager, persist: bool = True):
        self.vars = variables
        self.persist = persist

    def is_query(self, text: str) -> bool:
        return bool(_QUERY_RE.match(text or ""))

    def handle(self, text: str) -> str:
        """질의 문자열을 처리하고 '[외부 업데이트] 응답: ...' 문자열을 반환한다."""
        m = _QUERY_RE.match(text or "")
        if not m:
            return f"{RESPONSE_PREFIX} 인식할 수 없는 형식입니다. 예) {QUERY_PREFIX} randomness_intensity=2.4"
        body = m.group("body").strip()

        if body in ("목록", "list", "keys"):
            return f"{RESPONSE_PREFIX} 수정 가능 키 → " + ", ".join(self.vars.updatable_keys())

        if body in ("상태", "status", "vars"):
            pairs = [f"{k}={v:g}" for k, v in self.vars.uvars().items()]
            return f"{RESPONSE_PREFIX} 예측 불가 변수 8종 → " + ", ".join(pairs)

        applied, errors = self._apply_assignments(body)
        if self.persist and applied:
            self.vars.save()

        parts: List[str] = []
        if applied:
            parts.append("적용됨 → " + ", ".join(f"{k}={v:g}" if isinstance(v, float) else f"{k}={v}"
                                                  for k, v in applied))
        if errors:
            parts.append("오류 → " + "; ".join(errors))
        if not parts:
            parts.append("변경 사항이 없습니다.")
        return f"{RESPONSE_PREFIX} " + " | ".join(parts)

    def _apply_assignments(self, body: str) -> Tuple[List[Tuple[str, object]], List[str]]:
        applied: List[Tuple[str, object]] = []
        errors: List[str] = []
        # 쉼표로 다중 할당 분리
        for chunk in self._split_assignments(body):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "=" not in chunk:
                errors.append(f"'{chunk}' (키=값 형식 아님)")
                continue
            key, raw = chunk.split("=", 1)
            key = key.strip()
            raw = raw.strip()
            try:
                new_value = self.vars.set_path(key, raw)
                applied.append((key, new_value))
            except (KeyError, ValueError) as exc:
                errors.append(f"'{key}': {exc}")
        return applied, errors

    @staticmethod
    def _split_assignments(body: str) -> List[str]:
        # 쉼표 또는 세미콜론으로 구분
        return re.split(r"[,;]", body)


def is_external_query(text: str) -> bool:
    return bool(_QUERY_RE.match(text or ""))
