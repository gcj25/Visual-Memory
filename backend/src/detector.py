"""Pretrained YOLO (COCO) detector wrapper. Loads once, filters to the frozen whitelist."""
from __future__ import annotations

import threading
import urllib.request

import numpy as np

from config import WEIGHTS_DIR, WHITELIST, Settings
from .schemas import Detection


class DetectorUnavailable(RuntimeError):
    pass


class Detector:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None
        self._lock = threading.Lock()
        self.error: str | None = None
        self.active_labels: list[str] = []
        self.missing_labels: list[str] = []
        self._cache: dict[tuple, list[tuple]] = {}

    # ---- lifecycle -------------------------------------------------
    def load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            try:
                path = WEIGHTS_DIR / self.settings.model_name
                if not path.exists():
                    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
                    try:
                        urllib.request.urlretrieve(self.settings.model_url, path)
                    except Exception as e:  # noqa: BLE001
                        path.unlink(missing_ok=True)
                        raise DetectorUnavailable(
                            f"Model weights not found at {path} and download from {self.settings.model_url} "
                            f"failed: {e}. Place the weights file there manually.") from e
                from ultralytics import YOLO  # imported lazily: heavy

                model = YOLO(str(path))
                names = set(model.names.values())
                self.active_labels = [w for w in WHITELIST if w in names]
                self.missing_labels = [w for w in WHITELIST if w not in names]
                self._model = model
                self.error = None
            except DetectorUnavailable as e:
                self.error = str(e)
                raise
            except Exception as e:  # noqa: BLE001
                self.error = f"Failed to initialise detector: {type(e).__name__}: {e}"
                raise DetectorUnavailable(self.error) from e

    @property
    def ready(self) -> bool:
        return self._model is not None

    def info(self) -> dict:
        import torch
        import ultralytics

        return {"name": self.settings.model_name, "family": "Ultralytics YOLO (COCO-pretrained)",
                "device": self.settings.device, "cuda_available": bool(torch.cuda.is_available()),
                "ultralytics_version": ultralytics.__version__, "torch_version": torch.__version__.split("+")[0],
                "confidence_threshold": self.settings.detector_conf, "imgsz": self.settings.detector_imgsz,
                "whitelist": list(WHITELIST), "missing_whitelist_labels": self.missing_labels}

    def status(self) -> dict:
        return {"initialized": self.ready, "model": self.settings.model_name, "error": self.error}

    # ---- inference -------------------------------------------------
    def detect(self, image_bgr: np.ndarray, image_id: str, sha256: str | None = None,
               conf: float | None = None) -> list[Detection]:
        conf = self.settings.detector_conf if conf is None else conf
        h, w = image_bgr.shape[:2]
        key = (sha256, round(conf, 4), self.settings.model_name, self.settings.detector_imgsz)
        if sha256 and key in self._cache:
            raw = self._cache[key]
        else:
            self.load()
            with self._lock:
                results = self._model.predict(image_bgr, conf=conf, imgsz=self.settings.detector_imgsz,
                                              device=self.settings.device, verbose=False)
            raw = []
            r = results[0]
            names = r.names
            for box, c, k in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), r.boxes.cls.cpu().numpy()):
                label = names[int(k)]
                if label not in WHITELIST:
                    continue
                raw.append((label, tuple(float(v) for v in box), float(c)))
            raw.sort(key=lambda t: (t[1][0], t[1][1]))  # deterministic ordering
            if sha256:
                self._cache[key] = raw
        return [Detection(id=f"{image_id}_d{i:02d}", image_id=image_id, class_name=label, bbox=bbox,
                          confidence=c, image_width=w, image_height=h) for i, (label, bbox, c) in enumerate(raw)]
