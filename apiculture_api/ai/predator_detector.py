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
            return PredatorDetectionResult(False, 0.0, None, {'method': 'validation_check', 'reason': 'empty image'})

        # If we have a loaded model, use it for detection.
        if self._net is not None:
            return self._analyze_with_model(image_bytes, content_type)

        # Otherwise, use heuristic-based detection (fallback)
        return self._analyze_with_heuristics(image_bytes, content_type)

    def _analyze_with_model(self, image_bytes: bytes, content_type: Optional[str] = None) -> PredatorDetectionResult:
        """Analyze using ML model."""
        try:
            import cv2 # type: ignore
            import numpy as np # type: ignore

            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return PredatorDetectionResult(False, 0.0, None, {'method': 'opencv_dnn_model', 'reason': 'failed to decode image'})

            # Basic preprocessing; real model may need different scaling/size.
            blob = cv2.dnn.blobFromImage(img, scalefactor=1.0 / 255.0, size=(224, 224), swapRB=True)
            self._net.setInput(blob)
            out = self._net.forward()

            # Interpret output as class scores
            scores = out.flatten()
            if scores.size == 0:
                return PredatorDetectionResult(False, 0.0, None, {'method': 'opencv_dnn_model', 'reason': 'no detections'})

            class_id = int(scores.argmax())
            confidence = float(scores[class_id])
            label = self.labels.get(class_id)

            predator_labels = {"wasp", "hornet", "bear", "skunk", "raccoon", "bird"}
            predator_detected = (label in predator_labels) and confidence >= 0.6

            return PredatorDetectionResult(
                predator_detected=predator_detected,
                confidence=confidence,
                predator=label if predator_detected else None,
                details={
                    "method": "opencv_dnn_model",
                    "class_id": class_id,
                    "label": label,
                    "model_path": self.model_path
                }
            )
        except Exception as e:
            return PredatorDetectionResult(False, 0.0, None, {'method': 'opencv_dnn_model', 'reason': 'analysis failed', 'error': str(e)})

    def _analyze_with_heuristics(self, image_bytes: bytes, content_type: Optional[str] = None) -> PredatorDetectionResult:
        """Analyze using color and shape heuristics for common bee predators.

        This fallback method detects:
        - Wasps/Hornets: yellow/black or orange/black striped patterns, larger size
        - Bears: brown/black fur textures
        - Birds: feather patterns and beak-like shapes
        """
        try:
            import cv2 # type: ignore
            import numpy as np # type: ignore

            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return PredatorDetectionResult(False, 0.0, None, {'method': 'color_pattern_heuristic_analysis', 'reason': 'failed to decode image'})

            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            height, width = img.shape[:2]

            # Analyze for wasp/hornet characteristics
            wasp_score = self._detect_wasp_hornet(img, hsv)

            # Note: Bear and bird detection disabled to reduce false positives
            # with close-up bee images. Enable when a proper ML model is available.
            bear_score = 0.0  # self._detect_bear(img, hsv)
            bird_score = self._detect_bird(img, hsv)

            # Determine the most likely predator
            max_score = max(wasp_score, bear_score, bird_score)
            predator_type = None

            # Use a threshold that balances detection vs false positives
            # Note: Bees and hornets have similar yellow/black patterns, so
            # perfect separation requires ML model. This heuristic aims for
            # reasonable detection with acceptable false positive rate.
            if max_score > 0.32:  # Threshold for detection
                if wasp_score == max_score:
                    predator_type = "hornet/wasp"
                elif bear_score == max_score:
                    predator_type = "bear"
                elif bird_score == max_score:
                    predator_type = "bird"

            predator_detected = max_score > 0.32

            return PredatorDetectionResult(
                predator_detected=predator_detected,
                confidence=float(max_score),
                predator=predator_type,
                details={
                    "method": "color_pattern_heuristic_analysis",
                    "description": "HSV color analysis with yellow/black pattern detection for wasps/hornets",
                    "wasp_score": float(wasp_score),
                    "bear_score": float(bear_score),
                    "bird_score": float(bird_score),
                    "content_type": content_type,
                    "image_size": f"{width}x{height}"
                }
            )
        except Exception as e:
            return PredatorDetectionResult(False, 0.0, None, {'method': 'color_pattern_heuristic_analysis', 'reason': 'heuristic analysis failed', 'error': str(e)})

    def _detect_wasp_hornet(self, img, hsv) -> float:
        """Detect wasp/hornet patterns: yellow/orange with black stripes."""
        try:
            import cv2 # type: ignore
            import numpy as np # type: ignore

            # Yellow range (wasps, hornets) - expanded to catch more variations
            yellow_lower1 = np.array([20, 40, 40])
            yellow_upper1 = np.array([40, 255, 255])

            # Orange range (some hornet species) - expanded
            orange_lower = np.array([5, 40, 40])
            orange_upper = np.array([20, 255, 255])

            # Black range - adjusted to be more permissive
            black_lower = np.array([0, 0, 0])
            black_upper = np.array([180, 255, 70])

            # Create masks
            yellow_mask = cv2.inRange(hsv, yellow_lower1, yellow_upper1)
            orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
            black_mask = cv2.inRange(hsv, black_lower, black_upper)

            # Combine yellow and orange
            warning_color_mask = cv2.bitwise_or(yellow_mask, orange_mask)

            total_pixels = img.shape[0] * img.shape[1]
            warning_ratio = np.count_nonzero(warning_color_mask) / total_pixels
            black_ratio = np.count_nonzero(black_mask) / total_pixels

            # Bees also have yellow/black patterns, so we need to be more careful
            # Hornets typically have:
            # 1. More warning colors (>15%) with moderate black (>3%)
            # 2. Or very strong warning colors (>20%)
            # Avoid detecting small close-up bee images

            score = 0.0

            # Strongly favor images with substantial warning colors AND black
            if warning_ratio > 0.15 and black_ratio > 0.05:
                # Good combination of warning colors and black
                score = min(1.0, (warning_ratio * 1.8 + black_ratio * 2.0) * 0.6)
            elif warning_ratio > 0.25 and black_ratio > 0.04:
                # Very high warning colors with some black
                score = min(0.9, (warning_ratio * 1.5 + black_ratio * 2.5) * 0.7)
            elif warning_ratio > 0.12 and black_ratio > 0.08:
                # Moderate warning colors but good black presence
                score = min(0.8, (warning_ratio + black_ratio * 2.0) * 1.5)

            return score
        except Exception:
            return 0.0

    def _detect_bear(self, img, hsv) -> float:
        """Detect bear characteristics: brown/dark fur texture."""
        try:
            import cv2 # type: ignore
            import numpy as np # type: ignore

            # Brown color range
            brown_lower = np.array([10, 30, 30])
            brown_upper = np.array([25, 200, 200])

            brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
            total_pixels = img.shape[0] * img.shape[1]
            brown_ratio = np.count_nonzero(brown_mask) / total_pixels

            # Bears have lots of brown/dark fur and should be large images
            # Require substantial brown coverage to avoid false positives
            if brown_ratio > 0.40:
                # Check for texture (fur is not uniform)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                texture = cv2.Laplacian(gray, cv2.CV_64F).var()

                # Higher texture variance indicates fur
                if texture > 150:
                    return min(1.0, brown_ratio * 2.0)

            return 0.0
        except Exception:
            return 0.0

    def _detect_bird(self, img, hsv) -> float:
        """Detect bird characteristics: varied colors, edge patterns."""
        try:
            import cv2 # type: ignore
            import numpy as np # type: ignore

            # Birds have varied colors and distinct edges (feathers, beak)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)

            total_pixels = img.shape[0] * img.shape[1]
            edge_ratio = np.count_nonzero(edges) / total_pixels

            # Check color variety (birds can be colorful)
            color_std = np.std(hsv[:, :, 0])

            # Check for yellow/tan colors (common in birds)
            yellow_lower = np.array([20, 40, 40])
            yellow_upper = np.array([40, 255, 255])
            yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
            yellow_ratio = np.count_nonzero(yellow_mask) / total_pixels

            # Check for brown/tan colors (feathers)
            brown_lower = np.array([10, 30, 30])
            brown_upper = np.array([25, 200, 200])
            brown_mask = cv2.inRange(hsv, brown_lower, brown_upper)
            brown_ratio = np.count_nonzero(brown_mask) / total_pixels

            # Check for black (for contrast)
            black_lower = np.array([0, 0, 0])
            black_upper = np.array([180, 255, 70])
            black_mask = cv2.inRange(hsv, black_lower, black_upper)
            black_ratio = np.count_nonzero(black_mask) / total_pixels

            score = 0.0

            if yellow_ratio > 0.40 and brown_ratio > 0.08 and edge_ratio > 0.05 and color_std < 0.1:
                score = min(1.0, (yellow_ratio * 0.8 + brown_ratio * 2.0 + edge_ratio * 5.0) * 0.5)
                score = max(score, 0.5)

            elif edge_ratio > 0.10 and color_std > 30:
                score = min(1.0, edge_ratio * 5.0)

            elif yellow_ratio > 0.30 and brown_ratio > 0.12 and edge_ratio > 0.06:
                score = min(0.8, (brown_ratio * 3.0 + edge_ratio * 4.0) * 0.5)

            return score
        except Exception:
            return 0.0


# Default singleton used by the API.
_default_detector = PredatorDetector()


def analyze_predators(image_bytes: bytes, *, content_type: Optional[str] = None) -> PredatorDetectionResult:
    """Convenience wrapper used by the API."""

    return _default_detector.analyze_image_bytes(image_bytes=image_bytes, content_type=content_type)
