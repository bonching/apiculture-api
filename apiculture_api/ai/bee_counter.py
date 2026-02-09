from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class BeeCountResult:
    """Result of bee counting.

    Contract:
      - bee_count: estimated number of bees visible in the image (>= 0)
      - confidence: 0..1 heuristic confidence of the estimate.
      - details: optional debug metadata (e.g., algorithm used)

    This implementation is dependency-light and works without heavy ML libraries.
    If OpenCV is available, it uses a simple blob detection heuristic.
    Otherwise, it returns a conservative stub.
    """

    bee_count: int
    confidence: float = 0.0
    details: Optional[Dict[str, Any]] = None


class BeeCounter:
    """Counts bees in an image.

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
            gray_blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            height, width = img.shape[:2]
            total_pixels = height * width

            # Estimate image scale factor based on resolution
            # Higher resolution images have smaller bees relative to image size
            scale_factor = max(1, min(width, height) / 200)

            # Method 1: MSER (Maximally Stable Extremal Regions)
            # Best for detecting individual bees even when touching
            mser = cv2.MSER_create()
            # Adjust area based on image size
            min_area = int(5 * scale_factor)
            max_area = int(500 * scale_factor * scale_factor)
            mser.setMinArea(min_area)
            mser.setMaxArea(max_area)
            try:
                regions, _ = mser.detectRegions(gray)
                mser_count = len(regions)
            except:
                mser_count = 0

            # Method 2: Bee-colored region analysis (yellow/brown)
            # Bees are typically yellow/brown colored
            lower_bee1 = np.array([15, 40, 40])   # Yellow-brown
            upper_bee1 = np.array([35, 255, 255])
            lower_bee2 = np.array([0, 40, 40])   # Orange-brown
            upper_bee2 = np.array([15, 255, 255])
            lower_bee3 = np.array([35, 20, 40])   # Darker brown/golden
            upper_bee3 = np.array([50, 255, 255])

            mask1 = cv2.inRange(hsv, lower_bee1, upper_bee1)
            mask2 = cv2.inRange(hsv, lower_bee2, upper_bee2)
            mask3 = cv2.inRange(hsv, lower_bee3, upper_bee3)
            bee_mask = cv2.bitwise_or(cv2.bitwise_or(mask1, mask2), mask3)

            # Clean up the mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            bee_mask = cv2.morphologyEx(bee_mask, cv2.MORPH_OPEN, kernel)
            bee_mask = cv2.morphologyEx(bee_mask, cv2.MORPH_CLOSE, kernel)

            # Find contours on bee-colored regions
            contours, _ = cv2.findContours(bee_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Filter contours by area (bee-sized regions)
            min_bee_contour = int(8 * scale_factor)
            max_bee_contour = int(800 * scale_factor * scale_factor)
            bee_contours = [c for c in contours if min_bee_contour < cv2.contourArea(c) < max_bee_contour]
            contour_count = len(bee_contours)

            # Method 3: Coverage-based estimation
            # For densely packed images where individual detection fails
            bee_pixel_count = np.count_nonzero(bee_mask)
            bee_coverage = bee_pixel_count / total_pixels

            # Estimate average bee size based on image resolution
            # Small images: bees appear larger relative to image
            # Typical bee in image: 20-60 pixels depending on resolution
            estimated_bee_area = int(25 * scale_factor)
            coverage_count = int(bee_pixel_count / estimated_bee_area) if estimated_bee_area > 0 else 0

            # Method 4: Adaptive thresholding + contour detection
            # Good for high contrast bee images
            adaptive = cv2.adaptiveThreshold(gray_blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            adaptive_contours, _ = cv2.findContours(adaptive, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            adaptive_filtered = [c for c in adaptive_contours if min_bee_contour < cv2.contourArea(c) < max_bee_contour]
            adaptive_count = len(adaptive_filtered)

            # Combine methods using weighted average based on confidence
            # Higher weight to methods that typically perform better
            counts = {
                'mser': mser_count,
                'contour': contour_count,
                'coverage': coverage_count,
                'adaptive': adaptive_count
            }

            # Determine the best estimate based on image characteristics
            # For dense images (high edge ratio, high bee coverage), use MSER or coverage
            edges = cv2.Canny(gray_blurred, 50, 150)
            edge_ratio = np.count_nonzero(edges) / total_pixels

            if edge_ratio > 0.15 and bee_coverage > 0.05:
                # Dense image with many bees - MSER or coverage-based is more reliable
                # Use median of MSER and coverage to avoid outliers
                if mser_count > 50:
                    # MSER found many regions - likely accurate
                    final_count = int(mser_count * 0.7 + coverage_count * 0.3)
                    method_used = "mser_coverage_hybrid"
                else:
                    # Use coverage-based as primary
                    final_count = int(coverage_count * 0.8 + contour_count * 0.2)
                    method_used = "coverage_contour_hybrid"
                confidence = min(0.85, 0.5 + bee_coverage * 2)
            elif contour_count > 10:
                # Moderate density - contour detection is reliable
                final_count = int(contour_count * 0.6 + adaptive_count * 0.4)
                method_used = "contour_adaptive_hybrid"
                confidence = min(0.8, 0.4 + (contour_count / 100))
            else:
                # Sparse image - use maximum of available counts
                final_count = max(contour_count, adaptive_count, min(mser_count, 50))
                method_used = "sparse_max"
                confidence = 0.6 if final_count > 0 else 0.3

            # Sanity check: ensure count is reasonable
            final_count = max(0, final_count)

            return BeeCountResult(
                bee_count=final_count,
                confidence=round(confidence, 2),
                details={
                    "algorithm": "multi_method_hybrid",
                    "method_used": method_used,
                    "mser_count": mser_count,
                    "contour_count": contour_count,
                    "coverage_count": coverage_count,
                    "adaptive_count": adaptive_count,
                    "bee_coverage": round(bee_coverage, 4),
                    "edge_ratio": round(edge_ratio, 4),
                    "scale_factor": round(scale_factor, 2),
                    "content_type": content_type,
                    "image_shape": list(img.shape)
                }
            )
        except Exception as e:
            # OpenCV missing or processing failed.
            return BeeCountResult(
                bee_count=0,
                confidence=0.0,
                details={
                    "reason": "analysis failed",
                    "content_type": content_type,
                    "error": str(e),
                    "hint": "Install opencv-python to enable bee counting"
                }
            )


_default_counter = BeeCounter()


def count_bees(image_bytes: bytes, *, content_type: Optional[str] = None) -> BeeCountResult:
    """Convenience wrapper used by the API."""

    return _default_counter.count_bees(image_bytes=image_bytes, content_type=content_type)