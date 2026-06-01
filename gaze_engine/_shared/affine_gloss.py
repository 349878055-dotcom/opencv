"""eye_gloss 通道 → OpenCV B 通道湿润高光（三物种共用）。"""
from __future__ import annotations

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]


def draw_eye_gloss(
    canvas,
    pupil_center: tuple[int, int],
    iris_r: int,
    gloss: float,
    blink: float,
    *,
    gloss_neutral: float = 0.5,
) -> None:
    """在虹膜上缘外侧（黑区）画 B 通道湿眼高光斑；gloss 高于 neutral 时可见。"""
    if cv2 is None or blink >= 0.92 or iris_r < 3:
        return
    u = (float(gloss) - gloss_neutral) / max(1e-6, 1.0 - gloss_neutral)
    if u <= 0.03:
        return
    u = min(1.0, u)

    px, py = int(pupil_center[0]), int(pupil_center[1])
    spot_x = px - int(iris_r * 0.22)
    spot_y = py - iris_r - max(2, int(1 + u * 4))
    rx = max(2, int(iris_r * (0.14 + 0.10 * u)))
    ry = max(1, int(iris_r * (0.08 + 0.06 * u)))

    cv2.ellipse(
        canvas, (spot_x, spot_y), (rx, ry), -15, 0, 360,
        (255, 0, 0), -1, cv2.LINE_AA,
    )
    if u > 0.30:
        cv2.ellipse(
            canvas,
            (spot_x + max(1, rx // 3), spot_y - max(1, ry // 2)),
            (max(1, rx // 2), max(1, ry // 2)),
            -10,
            0,
            360,
            (255, 0, 0),
            -1,
            cv2.LINE_AA,
        )
