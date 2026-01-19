from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PredatorDetectionResult:
    """Result of predator detection.

    Contract:
      - predator_detected: True when the image likely contains a bee predator.
      - confidence: 0..1 heuristic confidence score.
      - predator: optional label (e.g. "wasp", "hornet", "bear").
      - details: extra metadata useful for debugging.
    """

    predator_detected: bool
    confidence: float = 0.0
    predator: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PredatorDetector:
    """Detects common bee predators in images.

    This repo currently doesn't pin heavy ML dependencies (e.g. torch/tensorflow).
    So this class is implemented to:
      1) Use OpenCV DNN if available and a model is configured.
      2) Fall back to a conservative stub that never triggers defense system.

    You can later plug in a real model by providing:
      - an ONNX model path (or other OpenCV-supported format)
      - class labels including predator types
    """

    def __init__(self, model_path: Optional[str] = None, labels: Optional[Dict[int, str]] = None):
        self.model_path = model_path
        self.labels = labels or {}

        self._net = None
        if model_path:
            try:
                import cv2 # type: ignore

                # OpenCV supports ONNX and other backends.
                self._net = cv2.dnn.readNet(model_path)
            except Exception:
                # If OpenCV isn't installed or model can't be loaded, we keep the stub behavior.
                self._net = None

    def analyze_image_bytes(self, image_bytes: bytes, content_type: Optional[str] = None) -> PredatorDetectionResult:
        """Analyze image bytes and return a detection result."""

        if not image_bytes:
            return PredatorDetectionResult(False, 0.0, None, {'reason': 'empty image'})

        # If we don't have a loaded model, return stub result.
        if self._net is None:
            return PredatorDetectionResult(
                predator_detected=False,
                confidence=0.0,
                predator=None,
                details={
                    "reason": "no model configured",
                    "hint": "Install opencv-python and provide a model_path to enable detection",
                    "content_type": content_type,
                },
            )

        # Minimal OpenCV decode + forward pass. Assumes a classification-ish network.
        try:
            import cv2 # type: ignore
            import numpy as np # type: ignore

            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return PredatorDetectionResult(False, 0.0, None, {'reason': 'failed to decode image'})

            # Basic preprocessing; real model may need different scaling/size.
            blob = cv2.dnn.blobFromImage(img, scalefactor=1.0 / 255.0, size=(224, 224), swapRB=True)
            self._net.setInput(blob)
            out = self._net.forward()

            # Interpret output as class scores
            scores = out.flatten()
            if scores.size == 0:
                return PredatorDetectionResult(False, 0.0, None, {'reason': 'no detections'})

            class_id = int(scores.argmax())
            confidence = float(scores[class_id])
            label = self.labels.get(class_id)

            predator_labels = {"wasp", "hornet", "bear", "skunk", "raccoon", "bird"}
            predator_detected = (label in predator_labels) and confidence >= 0.6

            return PredatorDetectionResult(
                predator_detected=predator_detected,
                confidence=confidence,
                predator=label if predator_detected else None,
                details={"class_id": class_id, "label": label}
            )
        except Exception as e:
            return PredatorDetectionResult(False, 0.0, None, {'reason': 'analysis failed', 'error': str(e)})


# Default singleton used by the API.
_default_detector = PredatorDetector()


def analyze_predators(image_bytes: bytes, *, content_type: Optional[str] = None) -> PredatorDetectionResult:
    """Convenience wrapper used by the API."""

    return _default_detector.analyze_image_bytes(image_bytes=image_bytes, content_type=content_type)
