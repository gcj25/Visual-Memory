"""Local JSON observation memory: one atomic file per observation (no single file to clobber)."""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

_ID = re.compile(r"^obs_[0-9a-f]{12}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class SceneMemory:
    def __init__(self, obs_dir: Path, image_dir: Path):
        self.obs_dir, self.image_dir = obs_dir, image_dir
        obs_dir.mkdir(parents=True, exist_ok=True)
        image_dir.mkdir(parents=True, exist_ok=True)
        self.warnings: list[str] = []

    # ---- images (original bytes, content-addressed, deduplicated) ----
    def store_image(self, loaded) -> str:
        name = f"{loaded.image_id}.{loaded.extension}"
        target = self.image_dir / name
        if not target.exists():
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_bytes(loaded.raw)
            os.replace(tmp, target)
        return name

    def image_path(self, stored_file: str) -> Path | None:
        p = (self.image_dir / Path(stored_file).name).resolve()
        return p if p.parent == self.image_dir.resolve() and p.exists() else None

    # ---- observations ----
    def save(self, record: dict) -> dict:
        record = dict(record)
        record["observation_id"] = f"obs_{uuid.uuid4().hex[:12]}"
        record["timestamp"] = now_iso()
        path = self.obs_dir / f"{record['observation_id']}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2))
        os.replace(tmp, path)
        return record

    def _read(self, path: Path) -> dict | None:
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or "observation_id" not in data:
                raise ValueError("missing observation_id")
            return data
        except (json.JSONDecodeError, ValueError, OSError) as e:
            self.warnings.append(f"skipped unreadable observation file {path.name}: {e}")
            try:  # quarantine so it is not re-read; never delete
                path.rename(path.with_suffix(".json.corrupt"))
            except OSError:
                pass
            return None

    def all(self) -> list[dict]:
        out = [r for p in sorted(self.obs_dir.glob("obs_*.json")) if (r := self._read(p)) is not None]
        return sorted(out, key=lambda r: r.get("timestamp", ""))

    def get(self, observation_id: str) -> dict | None:
        if not _ID.match(observation_id):
            return None
        p = self.obs_dir / f"{observation_id}.json"
        return self._read(p) if p.exists() else None

    def latest(self) -> dict | None:
        records = self.all()
        return records[-1] if records else None

    def has_image(self, image_id: str) -> bool:
        return any(r.get("image", {}).get("image_id") == image_id for r in self.all())

    @staticmethod
    def summary(r: dict) -> dict:
        return {"observation_id": r["observation_id"], "timestamp": r.get("timestamp"), "role": r.get("role"),
                "image": r.get("image"), "detection_count": len(r.get("detections", [])),
                "comparison": r.get("comparison")}
