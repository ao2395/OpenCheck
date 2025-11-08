"""
Board Calibration Tool
Manually mark the chess board corners once, then save for reuse
"""

import cv2
import numpy as np
from PIL import Image
import json
from pathlib import Path


class BoardCalibrator:
    """Interactive board calibration tool"""

    def __init__(self, config_file='board_config.json'):
        self.config_file = Path(config_file)
        self.corners = []
        self.image = None
        self.display_image = None

    def calibrate_from_screenshot(self, screenshot_path):
        """
        Interactive calibration: user clicks 4 corners of the board

        Args:
            screenshot_path: Path to a screenshot showing the chess board

        Returns:
            dict: Board configuration with corners and region
        """
        # Load image
        img = cv2.imread(screenshot_path)
        if img is None:
            print(f"Error: Could not load {screenshot_path}")
            return None

        self.image = img.copy()
        self.display_image = img.copy()

        print("=" * 70)
        print("Board Calibration")
        print("=" * 70)
        print("\nInstructions:")
        print("1. Click the 4 corners of the chess board in this order:")
        print("   - Top-left corner")
        print("   - Top-right corner")
        print("   - Bottom-right corner")
        print("   - Bottom-left corner")
        print("2. Press 'r' to reset if you make a mistake")
        print("3. Press 's' to save when all 4 corners are marked")
        print("4. Press 'q' to quit without saving")
        print("=" * 70)

        # Create window and set mouse callback
        cv2.namedWindow('Board Calibration', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Board Calibration', 1200, 800)
        cv2.setMouseCallback('Board Calibration', self._mouse_callback)

        while True:
            cv2.imshow('Board Calibration', self.display_image)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\nCalibration cancelled")
                cv2.destroyAllWindows()
                return None
            elif key == ord('r'):
                print("\nReset - click corners again")
                self.corners = []
                self.display_image = self.image.copy()
            elif key == ord('s'):
                if len(self.corners) == 4:
                    config = self._create_config()
                    cv2.destroyAllWindows()
                    return config
                else:
                    print(f"\nNeed 4 corners, you've marked {len(self.corners)}")

        cv2.destroyAllWindows()
        return None

    def _mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks to mark corners"""
        if event == cv2.EVENT_LBUTTONDOWN and len(self.corners) < 4:
            self.corners.append((x, y))

            # Draw the corner
            cv2.circle(self.display_image, (x, y), 8, (0, 255, 0), -1)

            # Draw corner number
            label = ['Top-Left', 'Top-Right', 'Bottom-Right', 'Bottom-Left'][len(self.corners) - 1]
            cv2.putText(self.display_image, label, (x + 15, y - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Draw lines between corners
            if len(self.corners) > 1:
                cv2.line(self.display_image, self.corners[-2], self.corners[-1],
                        (0, 255, 0), 2)

            # Close the square
            if len(self.corners) == 4:
                cv2.line(self.display_image, self.corners[3], self.corners[0],
                        (0, 255, 0), 2)
                print("\n✓ All 4 corners marked! Press 's' to save or 'r' to reset")
            else:
                print(f"Corner {len(self.corners)}/4 marked: {label}")

    def _create_config(self):
        """Create configuration from marked corners"""
        # Calculate bounding box
        xs = [c[0] for c in self.corners]
        ys = [c[1] for c in self.corners]

        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        width = x_max - x_min
        height = y_max - y_min

        config = {
            'corners': self.corners,
            'region': {
                'x': x_min,
                'y': y_min,
                'width': width,
                'height': height
            },
            'square_size': {
                'width': width // 8,
                'height': height // 8
            }
        }

        return config

    def save_config(self, config):
        """Save calibration config to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"\n✓ Configuration saved to {self.config_file}")
        print(f"\nBoard region: x={config['region']['x']}, y={config['region']['y']}, "
              f"w={config['region']['width']}, h={config['region']['height']}")
        print(f"Square size: {config['square_size']['width']}x{config['square_size']['height']}")

    def load_config(self):
        """Load calibration config from file"""
        if not self.config_file.exists():
            return None

        with open(self.config_file, 'r') as f:
            config = json.load(f)

        print(f"✓ Loaded board configuration from {self.config_file}")
        return config

    def auto_detect_chesscom_board(self, screenshot_path):
        """
        Automatically detect chess.com board using color detection

        Args:
            screenshot_path: Path to chess.com screenshot

        Returns:
            dict: Board configuration or None if detection failed
        """
        img = cv2.imread(screenshot_path)
        if img is None:
            return None

        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Chess.com default board colors (green and beige/cream)
        # Light squares: beige/cream
        # Dark squares: green

        # Detect green squares (dark squares)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        # Find contours
        contours, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Find the largest rectangular contour
        max_area = 0
        best_contour = None

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                # Check if roughly square
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                if 0.8 < aspect_ratio < 1.2 and area > 10000:  # Roughly square and large enough
                    max_area = area
                    best_contour = contour

        if best_contour is not None:
            x, y, w, h = cv2.boundingRect(best_contour)

            # Expand slightly to ensure we get the full board
            margin = int(w * 0.02)  # 2% margin
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = w + 2 * margin
            h = h + 2 * margin

            # Create corners
            corners = [
                (x, y),           # Top-left
                (x + w, y),       # Top-right
                (x + w, y + h),   # Bottom-right
                (x, y + h)        # Bottom-left
            ]

            config = {
                'corners': corners,
                'region': {
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h
                },
                'square_size': {
                    'width': w // 8,
                    'height': h // 8
                },
                'auto_detected': True
            }

            print("✓ Automatically detected chess.com board")
            print(f"Region: x={x}, y={y}, w={w}, h={h}")

            return config

        print("⚠ Automatic detection failed, please use manual calibration")
        return None


def calibrate_board(screenshot_path, auto=True, config_file='board_config.json'):
    """
    Calibrate board position (auto or manual)

    Args:
        screenshot_path: Path to chess.com screenshot
        auto: Try automatic detection first
        config_file: Where to save configuration

    Returns:
        dict: Board configuration
    """
    calibrator = BoardCalibrator(config_file)

    config = None

    # Try automatic detection first if requested
    if auto:
        print("Attempting automatic board detection...")
        config = calibrator.auto_detect_chesscom_board(screenshot_path)

        if config:
            print("\nAutomatic detection successful!")
            print("If the detection looks wrong, run with --manual flag")
        else:
            print("\nAutomatic detection failed, switching to manual mode...")
            auto = False

    # Manual calibration if auto failed or not requested
    if not auto or config is None:
        config = calibrator.calibrate_from_screenshot(screenshot_path)

    if config:
        calibrator.save_config(config)
        return config

    return None


if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("Chess.com Board Calibration Tool")
    print("=" * 70)
    print()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Auto:   python src/recognition/board_calibration.py screenshot.png")
        print("  Manual: python src/recognition/board_calibration.py screenshot.png --manual")
        print()
        print("This will:")
        print("1. Detect/mark the board region")
        print("2. Save coordinates to board_config.json")
        print("3. Use this config for all future captures (faster & more accurate)")
        sys.exit(1)

    screenshot_path = sys.argv[1]
    manual = '--manual' in sys.argv

    if not Path(screenshot_path).exists():
        print(f"Error: Screenshot not found: {screenshot_path}")
        sys.exit(1)

    config = calibrate_board(screenshot_path, auto=not manual)

    if config:
        print("\n✓ Board calibration complete!")
        print("\nNext steps:")
        print("1. Extract piece templates:")
        print("   python src/recognition/extract_templates.py", screenshot_path)
        print("2. Run OpenCheck:")
        print("   python src/main.py --use-templates")
    else:
        print("\n✗ Calibration failed")
        sys.exit(1)
