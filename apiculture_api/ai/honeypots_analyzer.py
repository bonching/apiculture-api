"""
Honeypots Analyzer - ML-based honeycomb cell detection and location analysis
Identifies honeypots (honeycomb cells) in beehive images taken from top view
"""

import cv2
import numpy as np
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

logger = logging.getLogger('honeypots_analyzer')
logger.setLevel(logging.INFO)


@dataclass
class HoneypotDetectionResult:
    """Result from honeypot detection analysis"""
    honeypots_detected: bool
    total_honeypots: int
    filled_honeypots: int
    empty_honeypots: int
    fill_percentage: float
    confidence: float
    honeypot_locations: List[Dict]
    grid_analysis: Dict
    details: Dict


class HoneypotsAnalyzer:
    """
    Analyzes beehive images to detect and locate honeypots (honeycomb cells).
    Assumes top-down view of beehive box with camera at the top center.
    Calculates 3D positions relative to the center of the beehive box.
    """

    def __init__(self, model_path: Optional[str] = None,
                 box_width_mm: float = 460.0,
                 box_height_mm: float = 370.0,
                 camera_height_mm: float = 50.0):
        """
        Initialize the honeypots analyzer.

        Args:
            model_path: Optional path to ML model for honeycomb detection
            box_width_mm: Physical width of beehive box in millimeters (default: 460mm for Langstroth)
            box_height_mm: Physical height of beehive box in millimeters (default: 370mm for Langstroth)
            camera_height_mm: Distance from camera to top of honeycomb in millimeters (default: 50mm)
        """
        self.model_path = model_path
        self._net = None

        # Physical dimensions for 3D mapping
        self.box_width_mm = box_width_mm
        self.box_height_mm = box_height_mm
        self.camera_height_mm = camera_height_mm

        # Try to load ML model if available
        if model_path:
            try:
                self._net = cv2.dnn.readNet(model_path)
                logger.info(f"Loaded honeypot detection model from {model_path}")
            except Exception as e:
                logger.warning(f"Could not load ML model: {str(e)}. Using heuristic detection.")
                self._net = None

    def analyze_image_bytes(self, image_bytes: bytes, content_type: Optional[str] = None) -> HoneypotDetectionResult:
        """
        Analyze image bytes to detect honeypots and their locations.

        Args:
            image_bytes: Image data as bytes
            content_type: MIME type of the image

        Returns:
            HoneypotDetectionResult with detection details
        """
        if not image_bytes:
            return HoneypotDetectionResult(
                honeypots_detected=False,
                total_honeypots=0,
                filled_honeypots=0,
                empty_honeypots=0,
                fill_percentage=0.0,
                confidence=0.0,
                honeypot_locations=[],
                grid_analysis={},
                details={'method': 'validation_check', 'reason': 'empty image'}
            )

        # Use ML model if available, otherwise use heuristic detection
        if self._net is not None:
            return self._analyze_with_model(image_bytes, content_type)
        else:
            return self._analyze_with_heuristics(image_bytes, content_type)

    def _analyze_with_model(self, image_bytes: bytes, content_type: Optional[str] = None) -> HoneypotDetectionResult:
        """Analyze using ML model (placeholder for future implementation)."""
        logger.info("ML model analysis not yet implemented, falling back to heuristics")
        return self._analyze_with_heuristics(image_bytes, content_type)

    def _analyze_with_heuristics(self, image_bytes: bytes, content_type: Optional[str] = None) -> HoneypotDetectionResult:
        """
        Analyze using computer vision heuristics.
        Detects hexagonal honeycomb patterns and determines fill status.
        """
        try:
            # Decode image
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if img is None:
                return HoneypotDetectionResult(
                    honeypots_detected=False,
                    total_honeypots=0,
                    filled_honeypots=0,
                    empty_honeypots=0,
                    fill_percentage=0.0,
                    confidence=0.0,
                    honeypot_locations=[],
                    grid_analysis={},
                    details={'method': 'heuristic_cv', 'reason': 'failed to decode image'}
                )

            height, width = img.shape[:2]
            logger.info(f"Analyzing image: {width}x{height}")

            # Convert to grayscale and HSV for analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Detect honeycomb cells using contour detection
            honeypot_locations = self._detect_honeycomb_cells(img, gray, hsv)

            # Classify cells as filled or empty
            filled_cells, empty_cells = self._classify_cells(img, hsv, honeypot_locations)

            total_honeypots = len(honeypot_locations)
            filled_honeypots = len(filled_cells)
            empty_honeypots = len(empty_cells)
            fill_percentage = (filled_honeypots / total_honeypots * 100) if total_honeypots > 0 else 0.0

            # Grid analysis - divide image into regions
            grid_analysis = self._analyze_grid_distribution(honeypot_locations, filled_cells, empty_cells, width,
                                                            height)

            # Calculate confidence based on detection quality
            confidence = self._calculate_confidence(honeypot_locations, img)

            logger.info(f"Detected {total_honeypots} honeypots ({filled_honeypots} filled, {empty_honeypots} empty)")

            return HoneypotDetectionResult(
                honeypots_detected=total_honeypots > 0,
                total_honeypots=total_honeypots,
                filled_honeypots=filled_honeypots,
                empty_honeypots=empty_honeypots,
                fill_percentage=round(fill_percentage, 2),
                confidence=round(confidence, 2),
                honeypot_locations=honeypot_locations,
                grid_analysis=grid_analysis,
                details={
                    'method': 'heuristic_cv',
                    'description': 'Hexagonal contour detection with HSV-based fill classification',
                    'image_size': f'{width}x{height}',
                    'content_type': content_type
                }
            )

        except Exception as e:
            logger.error(f"Error in honeypot analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            return HoneypotDetectionResult(
                honeypots_detected=False,
                total_honeypots=0,
                filled_honeypots=0,
                empty_honeypots=0,
                fill_percentage=0.0,
                confidence=0.0,
                honeypot_locations=[],
                grid_analysis={},
                details={'method': 'heuristic_cv', 'reason': 'analysis failed', 'error': str(e)}
            )

    def _detect_honeycomb_cells(self, img, gray, hsv) -> List[Dict]:
        """
        Detect individual honeycomb cells using contour detection.
        Returns list of cell locations with coordinates.
        """
        honeypot_locations = []

        # Apply adaptive thresholding to handle varying lighting
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        # Morphological operations to clean up
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        height, width = img.shape[:2]
        min_area = (width * height) * 0.0005  # Minimum cell area (0.05% of image)
        max_area = (width * height) * 0.05    # Maximum cell area (5% of image)

        for idx, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            # Filter by area
            if area < min_area or area > max_area:
                continue

            # Approximate contour to polygon
            epsilon = 0.04 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Hexagons have 6 sides, but we'll accept 5-8 sides due to imperfect detection
            if len(approx) >= 5 and len(approx) <= 8:
                # Get bounding box and center
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2

                # Calculate aspect ratio (hexagons are roughly square)
                aspect_ratio = float(w) / h if h > 0 else 0
                if 0.5 < aspect_ratio < 2.0:  # Reasonable aspect ratio
                    # Determine location quadrant
                    quadrant = self._get_quadrant(center_x, center_y, width, height)

                    # Calculate 3D coordinates from center of beehive box
                    coords_3d = self._calculate_3d_coordinates(
                        center_x, center_y, width, height
                    )

                    honeypot_locations.append({
                        'id': idx,
                        'center_x': center_x,
                        'center_y': center_y,
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'area': int(area),
                        'vertices': len(approx),
                        'quadrant': quadrant,
                        'relative_x': round(center_x / width, 3),
                        'relative_y': round(center_y / height, 3),
                        # 3D coordinates from center of box
                        'position_3d': coords_3d
                    })

        logger.info(f"Detected {len(honeypot_locations)} potential honeycomb cells")
        return honeypot_locations

    def _classify_cells(self, img, hsv, honeypot_locations: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Classify honeycomb cells as filled (with honey/capped) or empty.
        Uses color analysis - filled cells tend to be golden/brown, empty cells are darker.
        """
        filled_cells = []
        empty_cells = []

        for cell in honeypot_locations:
            # Extract region of interest
            x, y, w, h = cell['x'], cell['y'], cell['width'], cell['height']
            roi_hsv = hsv[y:y+h, x:x+w]

            # Calculate mean color in HSV space
            mean_hsv = cv2.mean(roi_hsv)[:3]
            h_mean, s_mean, v_mean = mean_hsv

            # Honey characteristics in HSV:
            # - Hue: 10-30 (yellow-orange-brown)
            # - Saturation: 30-255 (colored, not gray)
            # - Value: 100-255 (bright to medium)

            # Capped cells (white wax):
            # - Saturation: 0-50 (low saturation, whitish)
            # - Value: 180-255 (bright)

            # Empty cells:
            # - Value: 0-100 (dark)

            is_filled = False
            cell_type = 'empty'

            # Check for honey (golden color)
            if 10 <= h_mean <= 30 and s_mean > 30 and v_mean > 100:
                is_filled = True
                cell_type = 'honey'
            # Check for capped cells (white/light colored)
            elif s_mean < 50 and v_mean > 180:
                is_filled = True
                cell_type = 'capped'
            # Check for medium brightness (partial fill)
            elif v_mean > 100 and s_mean > 20:
                is_filled = True
                cell_type = 'partial'

            # Add classification to cell data
            cell_classified = cell.copy()
            cell_classified['filled'] = is_filled
            cell_classified['type'] = cell_type
            cell_classified['hsv_mean'] = {
                'h': round(h_mean, 1),
                's': round(s_mean, 1),
                'v': round(v_mean, 1)
            }

            if is_filled:
                filled_cells.append(cell_classified)
            else:
                empty_cells.append(cell_classified)

        logger.info(f"Classification: {len(filled_cells)} filled, {len(empty_cells)} empty")
        return filled_cells, empty_cells

    def _analyze_grid_distribution(self, honeypot_locations: List[Dict], filled_cells: List[Dict],
                                   width: int, height: int) -> Dict:
        """
        Analyze the distribution of honeypots across a 3x3 grid.
        Helps identify which areas of the hive have more honey production.
        """
        # Create 3x3 grid
        grid = {
            'top_left': {'total': 0, 'filled': 0},
            'top_center': {'total': 0, 'filled': 0},
            'top_right': {'total': 0, 'filled': 0},
            'middle_left': {'total': 0, 'filled': 0},
            'middle_center': {'total': 0, 'filled': 0},
            'middle_right': {'total': 0, 'filled': 0},
            'bottom_left': {'total': 0, 'filled': 0},
            'bottom_center': {'total': 0, 'filled': 0},
            'bottom_right': {'total': 0, 'filled': 0}
        }

        # Map cells to grid positions
        for cell in honeypot_locations:
            quadrant = cell['quadrant']
            if quadrant in grid:
                grid[quadrant]['total'] += 1

        # Count filled cells in each grid position
        filled_ids = {cell['id'] for cell in filled_cells}
        for cell in honeypot_locations:
            if cell['id'] in filled_ids:
                quadrant = cell['quadrant']
                if quadrant in grid:
                    grid[quadrant]['filled'] += 1

        # Calculate fill percentage for each grid position
        for position, data in grid.items():
            if data['total'] > 0:
                data['fill_percentage'] = round((data['filled'] / data['total']) * 100, 2)
            else:
                data['fill_percentage'] = 0.0

        return grid

    def _calculate_3d_coordinates(self, pixel_x: int, pixel_y: int,
                                  image_width: int, image_height: int) -> Dict:
        """
        Calculate 3D coordinates (in mm) from the center of the beehive box.

        Coordinate system:
        - Origin (0, 0, 0) = center of beehive box at top surface
        - X-axis: horizontal (left to right when viewing from top)
        - Y-axis: depth (top to bottom when viewing from top)
        - Z-axis: vertical (positive upward from honeycomb surface)

        Camera is positioned at (0, 0, camera_height_mm) looking down.

        Args:
             pixel_x: X coordinate in image (pixels)
             pixel_y: Y coordinate in image (pixels)
             image_width: Total image width (pixels)
             image_height: Total image height (pixels)

        Returns:
            Dictionary with 3D coordinates in mm and additional metrics
        """
        # Calculate center of image (camera position projected onto honeycomb)
        image_center_x = image_width / 2
        image_center_y = image_height / 2

        # Calculate pixel offset from center
        offset_x_pixels = pixel_x - image_center_x
        offset_y_pixels = pixel_y - image_center_y

        # Convert pixel coordinates to millimeters
        # Assume image shows the full beehive box
        pixels_per_mm_x = image_width / self.box_width_mm
        pixels_per_mm_y = image_height / self.box_height_mm

        # Calculate real-world offsets in mm from center
        x_mm = offset_x_pixels / pixels_per_mm_x
        y_mm = offset_y_pixels / pixels_per_mm_y

        # Z coordinate is negative (honeycomb is below camera)
        # Camera looks down, so z = -camera_height_mm at honeycomb surface
        z_mm = -self.camera_height_mm

        # Calculate distance from center of box (2D distance on honeycomb plane)
        distance_from_center_mm = np.sqrt(x_mm**2 + y_mm**2)

        # Calculate angle from center (in degrees, 0 = right, 90 = down, etc.)
        angle_degrees = np.degrees(np.arctan2(y_mm, x_mm))

        # Polar coordinates (useful for circular hive patterns)
        radius_mm = distance_from_center_mm
        theta_degrees = angle_degrees

        return {
            'x_mm': round(float(x_mm), 2),              # Horizontal offset from center
            'y_mm': round(float(y_mm), 2),              # Depth offset from center
            'z_mm': round(float(z_mm), 2),              # Vertical position (negative = below camera)
            'distance_from_center_mm': round(float(distance_from_center_mm), 2),
            'angle_degrees': round(float(angle_degrees), 2),
            'polar_radius_mm': round(float(radius_mm), 2),
            'polar_theta_degrees': round(float(theta_degrees), 2)
        }

    def _get_quadrant(self, x: int, y: int, width: int, height: int) -> str:
        """Determine which quadrant (3x3 grid) a point belongs to."""
        col = 'left' if x < width / 3 else ('center' if x < 2 * width / 3 else 'right')
        row = 'top' if y < height / 3 else ('middle' if y < 2 * height / 3 else 'bottom')
        return f"{row}_{col}"

    def _calculate_confidence(self, honeypot_locations: List[Dict], img) -> float:
        """
        Calculate confidence score based on detection quality.
        Higher confidence when cells are regularly spaced and have consistent sizes.
        """
        if len(honeypot_locations) < 5:
            return 0.3  # Low confidence with few detections

        # Calculate size variance (consistent sizes = higher confidence)
        areas = [cell['area'] for cell in honeypot_locations]
        mean_area = np.mean(areas)
        std_area = np.std(areas)
        cv_area = std_area / mean_area if mean_area > 0 else 1.0  # Coefficient of variation

        # Lower CV = more consistent = higher confidence
        size_confidence = max(0, 1 - cv_area)

        # Number of detections (more = better)
        count_confidence = min(1.0, len(honeypot_locations) / 100)  # Max confidence at 100+ cells

        # Combine metrics
        overall_confidence = (size_confidence * 0.6 + count_confidence * 0.4)

        return max(0.0, min(1.0, overall_confidence))


# Convenience function for quick analysis
def analyze_honeypots(image_bytes: bytes, content_type: Optional[str] = None,
                      model_path: Optional[str] = None) -> HoneypotDetectionResult:
    """
    Analyze image for honeypot detection.

    Args:
         image_bytes: Image data as bytes
         content_type: MIME type of the image
         model_path: Optional path to ML model

    Returns:
        HoneypotDetectionResult with detection details
    """
    analyzer = HoneypotsAnalyzer(model_path=model_path)
    return analyzer.analyze_image_bytes(image_bytes, content_type)
