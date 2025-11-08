"""
Classical Computer Vision approach for chess board recognition
More accurate and deterministic than LLM-based vision APIs
"""

import cv2
import numpy as np
from PIL import Image
import chess


class CVBoardRecognizer:
    """
    Computer vision-based chess board recognizer
    Uses classical CV techniques instead of LLMs
    """

    def __init__(self):
        """Initialize the CV recognizer"""
        self.board_corners = None
        self.square_size = None

    def detect_board_corners(self, image):
        """
        Detect the chess board corners in the image

        Args:
            image: PIL.Image or numpy array

        Returns:
            corners: List of 4 (x, y) corner coordinates
        """
        # Convert PIL to OpenCV format
        if isinstance(image, Image.Image):
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            img = image

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Find lines using Hough transform
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100,
                                minLineLength=100, maxLineGap=10)

        # Find the board by looking for a grid pattern
        # This is a simplified version - full implementation would:
        # 1. Find horizontal and vertical lines
        # 2. Find intersections forming a grid
        # 3. Detect the 8x8 chess board pattern
        # 4. Return the 4 corners

        # For now, we'll use a simpler heuristic:
        # Assume the board is the largest square-ish region in the image
        height, width = gray.shape

        # Default to full image if detection fails
        # TODO: Implement proper board detection
        return [
            (0, 0),           # top-left
            (width, 0),       # top-right
            (width, height),  # bottom-right
            (0, height)       # bottom-left
        ]

    def extract_squares(self, image, corners=None):
        """
        Extract the 64 individual squares from the board

        Args:
            image: PIL.Image or numpy array
            corners: Board corners (if None, will auto-detect)

        Returns:
            List of 64 square images (from a1 to h8)
        """
        if isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image

        if corners is None:
            corners = self.detect_board_corners(image)

        # Get board dimensions
        height, width = img.shape[:2]

        # Divide into 8x8 grid
        # Assuming square board for simplicity
        square_height = height // 8
        square_width = width // 8

        squares = []
        for row in range(8):
            for col in range(8):
                y1 = row * square_height
                y2 = (row + 1) * square_height
                x1 = col * square_width
                x2 = (col + 1) * square_width

                square = img[y1:y2, x1:x2]
                squares.append(square)

        return squares

    def classify_square(self, square_img):
        """
        Classify what piece (if any) is on a square

        Args:
            square_img: Image of a single square

        Returns:
            str: Piece character (e.g., 'P', 'n', 'K') or None for empty
        """
        # This is where you'd use a small CNN or template matching
        # For now, returning None as a placeholder
        # TODO: Implement piece classification
        # Options:
        # 1. Train a small CNN on chess piece images
        # 2. Use template matching with known piece images
        # 3. Use color/shape heuristics

        return None

    def squares_to_fen(self, squares_classification):
        """
        Convert 64 square classifications to FEN notation

        Args:
            squares_classification: List of 64 piece characters or None

        Returns:
            str: FEN notation
        """
        fen_rows = []

        # Process each rank (8 rows)
        for rank in range(8):
            row_str = ""
            empty_count = 0

            # Process each file (8 columns)
            for file in range(8):
                idx = rank * 8 + file
                piece = squares_classification[idx]

                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    row_str += piece

            # Add remaining empty squares
            if empty_count > 0:
                row_str += str(empty_count)

            fen_rows.append(row_str)

        # Join ranks with /
        position = '/'.join(fen_rows)

        # Add default metadata (white to move, all castling rights)
        return f"{position} w KQkq - 0 1"

    def get_fen_from_image(self, image):
        """
        Extract FEN from board image using computer vision

        Args:
            image: PIL.Image of chess board

        Returns:
            str: FEN notation or None if failed
        """
        try:
            # Step 1: Detect board corners
            corners = self.detect_board_corners(image)

            # Step 2: Extract 64 squares
            squares = self.extract_squares(image, corners)

            # Step 3: Classify each square
            classifications = [self.classify_square(sq) for sq in squares]

            # Step 4: Convert to FEN
            fen = self.squares_to_fen(classifications)

            # Validate
            board = chess.Board(fen)
            return fen

        except Exception as e:
            print(f"CV recognition error: {e}")
            return None


# For demonstration - this would need proper implementation
if __name__ == "__main__":
    recognizer = CVBoardRecognizer()
    print("CV-based chess board recognizer initialized")
    print("Note: This is a template - piece classification needs to be implemented")
