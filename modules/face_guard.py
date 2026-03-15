# modules/face_guard.py
_MOUTH_IDX = [
    61,
    146,
    91,
    181,
    84,
    17,
    314,
    405,
    321,
    375,
    78,
    191,
    80,
    81,
    82,
    13,
    312,
    311,
    310,
    415,
]


def detect_mask(face_lm, frame=None) -> bool:
    try:
        ys = [face_lm[i].y for i in _MOUTH_IDX]
        mouth_height = max(ys) - min(ys)
        face_height = abs(face_lm[152].y - face_lm[10].y)
        if face_height < 1e-4:
            return False
        return (mouth_height / face_height) < 0.02
    except (IndexError, AttributeError):
        return False


def face_quality_ok(face_lm) -> bool:
    try:
        for idx in [1, 33, 263]:
            lm = face_lm[idx]
            if not (0.0 <= lm.x <= 1.0 and 0.0 <= lm.y <= 1.0):
                return False
        return True
    except (IndexError, AttributeError):
        return False
