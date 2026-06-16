"""XR intent schemas — 공간 입력 → CPoW 창조 오브젝트."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from cpow_engine.models import CreativeObject, PropertyDef
from cpow_engine.physics import create_heat_object, create_material_object


@dataclass
class XRDeviceInfo:
    """XR 헤드셋·컨트롤러 메타데이터."""

    device_type: str  # quest3, vision_pro, pcvr, ar_glasses
    tracking: str = "6dof"  # 3dof, 6dof
    hand_tracking: bool = True
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_type": self.device_type,
            "tracking": self.tracking,
            "hand_tracking": self.hand_tracking,
            "session_id": self.session_id,
        }


@dataclass
class XRSpatialPose:
    """공간 좌표 — 손·오브젝트 위치."""

    x: float
    y: float
    z: float
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    scale: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "rotation_x": self.rotation_x,
            "rotation_y": self.rotation_y,
            "rotation_z": self.rotation_z,
            "scale": self.scale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> XRSpatialPose:
        return cls(
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            z=float(data.get("z", 0)),
            rotation_x=float(data.get("rotation_x", 0)),
            rotation_y=float(data.get("rotation_y", 0)),
            rotation_z=float(data.get("rotation_z", 0)),
            scale=float(data.get("scale", 1.0)),
        )

    def distance_to(self, other: XRSpatialPose) -> float:
        return (
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        ) ** 0.5


@dataclass
class XRCreationIntent:
    """XR에서 발생한 창조 의도 — API로 전송되는 단위."""

    creator_id: str
    gesture: str  # pinch_spawn, draw_connection, sculpt_property
    pose: XRSpatialPose
    target_pose: XRSpatialPose | None = None
    property_hint: str = ""  # heat_intensity, material_type, etc.
    intensity: float = 1.0
    label: str = ""
    device: XRDeviceInfo | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "creator_id": self.creator_id,
            "gesture": self.gesture,
            "pose": self.pose.to_dict(),
            "target_pose": self.target_pose.to_dict() if self.target_pose else None,
            "property_hint": self.property_hint,
            "intensity": self.intensity,
            "label": self.label,
            "device": self.device.to_dict() if self.device else None,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> XRCreationIntent:
        target = data.get("target_pose")
        device = data.get("device")
        return cls(
            creator_id=str(data["creator_id"]),
            gesture=str(data["gesture"]),
            pose=XRSpatialPose.from_dict(data.get("pose", {})),
            target_pose=XRSpatialPose.from_dict(target) if target else None,
            property_hint=str(data.get("property_hint", "")),
            intensity=float(data.get("intensity", 1.0)),
            label=str(data.get("label", "")),
            device=XRDeviceInfo(**device) if device else None,
            timestamp=float(data.get("timestamp", time.time())),
        )


def intent_to_creative_object(intent: XRCreationIntent) -> CreativeObject:
    """XR 창조 의도 → CPoW CreativeObject 변환."""
    spatial_entropy = _spatial_entropy(intent.pose, intent.target_pose)
    base_intensity = intent.intensity * (1.0 + spatial_entropy * 0.1)

    if intent.property_hint == "heat_intensity" or intent.gesture == "heat_pinch":
        return create_heat_object(
            intent.creator_id,
            intent.label or "XR 열원",
            heat_intensity=base_intensity * 100.0,
        )

    if intent.property_hint == "material_type" or intent.gesture == "material_sculpt":
        material = intent.label or "xr_material"
        conductivity = min(1.0, 0.3 + intent.pose.scale * 0.2)
        return create_material_object(
            intent.creator_id,
            intent.label or "XR 재료",
            material,
            thermal_conductivity=conductivity,
        )

    if intent.gesture == "pinch_spawn":
        return CreativeObject(
            creator_id=intent.creator_id,
            label=intent.label or "XR 창조물",
            properties=[
                PropertyDef(
                    name=intent.property_hint or "xr_energy",
                    value=base_intensity * 50.0,
                    unit="joules_per_tick",
                ),
                PropertyDef(
                    name="spatial_x",
                    value=intent.pose.x,
                    unit="meters",
                ),
                PropertyDef(
                    name="spatial_y",
                    value=intent.pose.y,
                    unit="meters",
                ),
                PropertyDef(
                    name="spatial_z",
                    value=intent.pose.z,
                    unit="meters",
                ),
            ],
        )

    return CreativeObject(
        creator_id=intent.creator_id,
        label=intent.label or "XR generic",
        properties=[
            PropertyDef("xr_gesture", 0.0, intent.gesture),
            PropertyDef("intensity", base_intensity, ""),
        ],
    )


def connection_distance(intent: XRCreationIntent) -> float | None:
    """두 오브젝트 연결 시 공간 거리."""
    if intent.target_pose is None:
        return None
    return intent.pose.distance_to(intent.target_pose)


def _spatial_entropy(
    pose: XRSpatialPose, target: XRSpatialPose | None
) -> float:
    """공간 복잡도 — 단순 반복 배치 억제용 힌트."""
    complexity = abs(pose.x) + abs(pose.y) + abs(pose.z) + pose.scale
    if target:
        complexity += pose.distance_to(target)
    return min(1.0, complexity / 10.0)
