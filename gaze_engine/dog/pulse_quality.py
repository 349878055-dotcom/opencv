"""
狗平庸质检规则
TODO: 填充
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DogPulseQualityReport:
    enabled: bool = True
    fixes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "fixes": self.fixes}