"""
Real-time screenshot capture for chess.com
"""

import mss
import numpy as np
from PIL import Image
import time


class ScreenCapture:
    """
    Captures screenshots from the screen, optimized for chess.com
    """
    def __init__(self, monitor_number=1):
        """
        Args:
            monitor_number: Monitor to capture from (1 = primary)
        """
        self.sct = mss.mss()
        self.monitor_number = monitor_number
        self.monitor = self.sct.monitors[monitor_number]

        print(f"Initialized screen capture")
        print(f"Monitor: {self.monitor['width']}x{self.monitor['height']}")

    def capture_full_screen(self):
        """
        Capture the entire screen

        Returns:
            PIL.Image: Screenshot image
        """
        screenshot = self.sct.grab(self.monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        return img

    def capture_region(self, x, y, width, height):
        """
        Capture a specific region of the screen

        Args:
            x, y: Top-left corner coordinates
            width, height: Region dimensions

        Returns:
            PIL.Image: Screenshot of the region
        """
        region = {
            'top': y,
            'left': x,
            'width': width,
            'height': height,
            'mon': self.monitor_number
        }

        screenshot = self.sct.grab(region)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
        return img

    def capture_to_numpy(self):
        """
        Capture screenshot as numpy array (for OpenCV processing)

        Returns:
            numpy.ndarray: Screenshot in BGR format
        """
        screenshot = self.sct.grab(self.monitor)
        img = np.array(screenshot)
        # Convert RGBA to RGB
        img = img[:, :, :3]
        # Convert RGB to BGR for OpenCV
        img = img[:, :, ::-1]
        return img

    def find_chess_board(self, img=None):
        """
        Attempt to find the chess board in the screenshot
        This is a placeholder - will be implemented with board detection

        Args:
            img: PIL.Image or None (captures new screenshot if None)

        Returns:
            dict: Board location info {x, y, width, height} or None
        """
        # TODO: Implement chess board detection
        # For now, return None to use full screen
        return None

    def save_screenshot(self, filepath, region=None):
        """
        Save a screenshot to file

        Args:
            filepath: Path to save the image
            region: Optional region dict {x, y, width, height}
        """
        if region:
            img = self.capture_region(**region)
        else:
            img = self.capture_full_screen()

        img.save(filepath)
        print(f"Screenshot saved to {filepath}")


class ContinuousCapture:
    """
    Continuously captures screenshots at a specified interval
    """
    def __init__(self, interval=2.0, monitor_number=1):
        """
        Args:
            interval: Time between captures in seconds
            monitor_number: Monitor to capture from
        """
        self.screen_capture = ScreenCapture(monitor_number)
        self.interval = interval
        self.running = False
        self.last_capture_time = 0
        self.latest_image = None

    def should_capture(self):
        """Check if enough time has passed for next capture"""
        current_time = time.time()
        if current_time - self.last_capture_time >= self.interval:
            return True
        return False

    def capture_once(self):
        """Capture a single screenshot and update state"""
        self.latest_image = self.screen_capture.capture_full_screen()
        self.last_capture_time = time.time()
        return self.latest_image

    def get_latest_image(self):
        """Get the most recent captured image"""
        return self.latest_image

    def set_interval(self, interval):
        """Update capture interval"""
        self.interval = interval


# Example usage
if __name__ == "__main__":
    # Test screen capture
    capture = ScreenCapture()

    print("\nCapturing full screen...")
    img = capture.capture_full_screen()
    print(f"Captured image size: {img.size}")

    # Save test screenshot
    capture.save_screenshot("test_screenshot.png")

    # Test continuous capture
    print("\nTesting continuous capture (3 captures, 1 second apart)...")
    continuous = ContinuousCapture(interval=1.0)

    for i in range(3):
        if continuous.should_capture():
            img = continuous.capture_once()
            print(f"Capture {i+1}: {img.size}")
        time.sleep(1.1)

    print("\nScreen capture test complete!")
