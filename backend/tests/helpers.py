from config import Settings
from src.schemas import Detection
from src.object_matching import match_detections
from src.change_detection import classify_changes

W, H = 1000, 800
S = Settings()


def det(i, cls="chair", box=(100, 100, 200, 200), conf=0.9, img="a"):
    return Detection(f"{img}{i}", img, cls, box, conf, W, H)


def run(ref, later, s=S):
    mr = match_detections(ref, later, s)
    return mr, classify_changes(ref, later, mr, s)
