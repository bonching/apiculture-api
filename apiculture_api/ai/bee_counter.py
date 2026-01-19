from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class BeeCountResult:
    """Result of bee counting.

    Contract:
      - bee_count: estimated number of bees in the image (>= 0)
      - confidence: 0..1 heuristic confidence of the estimate.
      - details: extra metadata useful for debugging.

    This implementation is dependency-light and works without heavy ML libraries.
    If OpenCV is available, it uses a simple blob detection heuristic.
    Otherwise, it returns a conservative stub.
    """

    bee_count: int
    confidence: float = 0.0
    details: Optional[Dict[str, Any]] = None


class BeeCounter:
    """Counts bees in images.

    Implementation strategy:
      1) If OpenCV is available, decode the image and run a simple blob detector on edges.
      2) If decoding fails or OpenCV isn't installed, fall back to stub result.

    Note: This is a heuristic, not a production-grade model.
    It's designed to be safe to deploy in this repo without adding big dependencies.
    """

    def count_bees(self, image_bytes: bytes, content_type: Optional[str] = None) -> BeeCountResult:
        if not image_bytes:
            return BeeCountResult(bee_count=0, confidence=0, details={"reason": "empty image"})

        try:
            import cv2 # type: ignore
            import numpy as np # type: ignore

            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return BeeCountResult(bee_count=0, confidence=0, details={"reason": "failed to decode image"})

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)

            # Edge map; bees tend to have high frequency features.
            edges = cv2.Canny(gray, 50, 150)

            # Close gaps so we get blob-like components.
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

            # Configure blob detector. Parameters chosen to be fairly conservative.
            params = cv2.SimpleBlobDetector_Params()
            params.filterByArea = True
            params.minArea = 20
            params.maxArea = 5000
            params.filterByCircularity = False
            params.filterByConvexity = False
            params.filterByInertia = False
            params.filterByColor = True
            params.blobColor = 255

            detector = cv2.SimpleBlobDetector_create(params)
            keypoints = detector.detect(closed)

            # Clamp to sane range and compute a simple confidence heuristic.
            count = max(0, len(keypoints))
            # Confidence rises with count up to a cap; overall heuristic.
            confidence = float(min(0.9, 0.3 + (count / 200.0))) if count > 0 else 0.2

            return BeeCountResult(
                bee_count=count,
                confidence=confidence,
                details={
                    "algorithm": "opncv blob detector",
                    "content_type": content_type,
                    "image_shape": list(img.shape)
                }
            )
        except Exception as e:
            # OpenCV missing or processing failed.
            return BeeCountResult(
                bee_count=0,
                confidence=0,
                details={
                    "reason": "analysis failed",
                    "content_type": content_type,
                    "error": str(e),
                    "hint": "Install opencv-python and provide a model_path to enable detection"
                }
            )


_default_counter = BeeCounter()


def count_bees(image_bytes: bytes, *, content_type: Optional[str] = None) -> BeeCountResult:
    """Convenience wrapper used by the API."""

    return _default_counter.count_bees(image_bytes=image_bytes, content_type=content_type)