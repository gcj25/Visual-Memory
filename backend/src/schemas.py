"""Internal data representations (plain dataclasses, JSON-serialisable via ``to_dict``)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

CHANGE_TYPES = ("unchanged", "possibly_relocated", "newly_observed", "not_observed")
STATUSES = ("supported", "uncertain")


@dataclass
class Detection:
    id: str
    image_id: str
    class_name: str
    bbox: tuple[float, float, float, float]  # original-image pixel coordinates
    confidence: float  # detector score; NOT a probability of correct identity
    image_width: int
    image_height: int

    def to_dict(self) -> dict:
        d = asdict(self)
        d["bbox"] = [round(float(v), 2) for v in self.bbox]
        d["confidence"] = round(float(self.confidence), 4)
        return d


@dataclass
class Finding:
    finding_id: str
    change_type: str
    status: str
    class_name: str
    explanation: str
    reference_detection: dict | None = None
    later_detection: dict | None = None
    displacement_norm: float | None = None
    area_ratio: float | None = None
    association_quality: dict | None = None
    detector_confidence: dict = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    uncertainty_reasons: list[dict] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
