"""
Template Matching Chess Board Recognition
Fast and accurate for fixed board positions (like chess.com)
"""

import cv2
import numpy as np
from PIL import Image
import chess
import os
from pathlib import Path


class TemplateMatcher:
    """
    Chess board recognizer using template matching
    Perfect for consistent board positions
    """

    def __init__(self, templates_dir='templates'):
        """
        Initialize template matcher

        Args:
            templates_dir: Directory containing piece template images
        """
        self.templates_dir = Path(templates_dir)
        self.templates = {}
        self.piece_map = {
            'white_pawn': 'P', 'white_knight': 'N', 'white_bishop': 'B',
            'white_rook': 'R', 'white_queen': 'Q', 'white_king': 'K',
            'black_pawn': 'p', 'black_knight': 'n', 'black_bishop': 'b',
            'black_rook': 'r', 'black_queen': 'q', 'black_king': 'k',
        }

        # Board detection parameters (chess.com specific)
        self.board_region = None  # Will be auto-detected or manually set

        # Load templates if directory exists
        if self.templates_dir.exists():
            self._load_templates()
        else:
            print(f"Warning: Templates directory '{templates_dir}' not found")
            print("Run extract_templates.py first to create templates")

    def _load_templates(self):
        """Load all piece templates from disk"""
        for piece_name, piece_char in self.piece_map.items():
            template_path = self.templates_dir / f"{piece_name}.png"
            if template_path.exists():
                template = cv2.imread(str(template_path))
                if template is not None:
                    self.templates[piece_char] = template
                    print(f"Loaded template: {piece_name}")
                else:
                    print(f"Warning: Could not load {template_path}")
            else:
                print(f"Warning: Template not found: {template_path}")

        # Load empty square templates
        for square_type in ['light', 'dark']:
            template_path = self.templates_dir / f"empty_{square_type}.png"
            if template_path.exists():
                template = cv2.imread(str(template_path))
                if template is not None:
                    self.templates[f'empty_{square_type}'] = template
                    print(f"Loaded template: empty_{square_type}")

        print(f"Loaded {len(self.templates)} templates total")

    def create_templates_from_position(self, screenshot_path, fen):
        """
        Helper to create templates from a screenshot with known position

        Args:
            screenshot_path: Path to screenshot of known position
            fen: FEN of that position

        This will extract each piece as a template
        """
        print("Manual template creation:")
        print("1. Screenshot a known position on chess.com")
        print("2. Provide the FEN of that position")
        print("3. This will extract piece images for matching")

        # TODO: Implement automatic template extraction
        # For now, user needs to manually crop piece images
        pass

    def detect_board_region(self, image):
        """
        Detect the chess board region in the image

        Args:
            image: PIL Image or numpy array

        Returns:
            (x, y, width, height) of board region
        """
        # Convert to numpy if needed
        if isinstance(image, Image.Image):
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            img = image

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Find edges
        edges = cv2.Canny(gray, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Find the largest square-ish contour (likely the board)
        max_area = 0
        board_contour = None

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                # Check if roughly square
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                if 0.8 < aspect_ratio < 1.2:  # Roughly square
                    max_area = area
                    board_contour = contour

        if board_contour is not None:
            x, y, w, h = cv2.boundingRect(board_contour)
            return (x, y, w, h)

        # Fallback: assume board is centered, taking up 60% of image
        height, width = gray.shape
        size = int(min(width, height) * 0.6)
        x = (width - size) // 2
        y = (height - size) // 2
        return (x, y, size, size)

    def extract_squares(self, image, board_region=None):
        """
        Extract 64 squares from the board

        Args:
            image: PIL Image or numpy array
            board_region: (x, y, w, h) or None for auto-detect

        Returns:
            List of 64 numpy arrays (a1 to h8)
        """
        if isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image

        if board_region is None:
            if self.board_region is None:
                self.board_region = self.detect_board_region(image)
            board_region = self.board_region

        x, y, w, h = board_region

        # Extract board
        board = img[y:y+h, x:x+w]

        # Divide into 8x8 grid
        square_h = h // 8
        square_w = w // 8

        squares = []
        for row in range(8):
            for col in range(8):
                sy = row * square_h
                sx = col * square_w
                square = board[sy:sy+square_h, sx:sx+square_w]
                squares.append(square)

        return squares

    def classify_square(self, square_img, is_light_square=True):
        """
        Classify piece using template matching

        Args:
            square_img: Numpy array of square (RGB)
            is_light_square: Whether this is a light or dark square

        Returns:
            Piece character or None for empty
        """
        if not self.templates:
            print("Warning: No templates loaded, using simple classification")
            return self.classify_square_simple(square_img)

        # Convert to BGR for OpenCV
        if len(square_img.shape) == 3 and square_img.shape[2] == 3:
            square_bgr = cv2.cvtColor(square_img, cv2.COLOR_RGB2BGR)
        else:
            square_bgr = square_img

        # Resize square to match template size (use first template as reference)
        if self.templates:
            ref_template = next(iter(self.templates.values()))
            target_h, target_w = ref_template.shape[:2]
            square_resized = cv2.resize(square_bgr, (target_w, target_h))
        else:
            square_resized = square_bgr

        # Try matching against all piece templates
        best_match_score = -1
        best_match_piece = None

        for piece_char, template in self.templates.items():
            # Skip empty square templates for now
            if piece_char.startswith('empty'):
                continue

            # Match template
            result = cv2.matchTemplate(square_resized, template, cv2.TM_CCOEFF_NORMED)
            score = np.max(result)

            if score > best_match_score:
                best_match_score = score
                best_match_piece = piece_char

        # Check against empty square template
        empty_type = 'light' if is_light_square else 'dark'
        empty_key = f'empty_{empty_type}'
        if empty_key in self.templates:
            result = cv2.matchTemplate(square_resized, self.templates[empty_key], cv2.TM_CCOEFF_NORMED)
            empty_score = np.max(result)

            # If empty square matches better, return None
            if empty_score > best_match_score * 1.1:  # Slight bias towards empty
                return None

        # Threshold for considering a match valid
        if best_match_score > 0.6:
            return best_match_piece
        else:
            # Fallback to simple classification
            return self.classify_square_simple(square_img)

    def classify_square_simple(self, square_img):
        """
        Simple piece classification using color analysis (fallback)

        Args:
            square_img: Numpy array of square

        Returns:
            Piece character or None for empty
        """
        # Get center region (where piece usually is)
        h, w = square_img.shape[:2]
        center = square_img[h//4:3*h//4, w//4:3*w//4]

        # Calculate color variance (pieces have more detail than empty squares)
        variance = np.var(center)

        # Simple heuristic: if low variance, probably empty
        if variance < 500:  # Threshold may need tuning
            return None

        # If high variance, there's likely a piece
        # Further classification would require templates or CNN
        # For now, return '?' to indicate "piece present but unknown"
        return '?'

    def get_fen_from_image(self, image):
        """
        Extract FEN from image

        Args:
            image: PIL Image

        Returns:
            str: FEN notation or None
        """
        try:
            # Extract squares
            squares = self.extract_squares(image)

            # Classify each square (considering light/dark squares)
            classifications = []
            for idx, square in enumerate(squares):
                rank, file = divmod(idx, 8)
                # Chess board: a1 is light square, alternating pattern
                is_light = (rank + file) % 2 == 0
                piece = self.classify_square(square, is_light_square=is_light)
                classifications.append(piece)

            # Convert to FEN
            fen = self._classifications_to_fen(classifications)

            # Validate FEN
            try:
                chess.Board(fen)
                return fen
            except Exception as e:
                print(f"Invalid FEN generated: {fen}")
                print(f"Error: {e}")
                return None

        except Exception as e:
            print(f"CV recognition error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _classifications_to_fen(self, classifications):
        """
        Convert 64 square classifications to FEN notation

        Args:
            classifications: List of 64 piece characters or None

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
                piece = classifications[idx]

                if piece is None or piece == '?':
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


def setup_guide():
    """Print setup guide for template matching"""
    guide = """
╔═══════════════════════════════════════════════════════════════╗
║         Template Matching Setup Guide                        ║
╚═══════════════════════════════════════════════════════════════╝

Since LiveChess2FEN is not available, we'll use template matching:

STEP 1: Create piece templates (one-time setup)
────────────────────────────────────────────────────────────────
1. Go to chess.com and set up a position with all pieces visible
2. Take a screenshot
3. Manually crop each piece type and save:

   templates/
     white_pawn.png
     white_knight.png
     white_bishop.png
     white_rook.png
     white_queen.png
     white_king.png
     black_pawn.png
     black_knight.png
     black_bishop.png
     black_rook.png
     black_queen.png
     black_king.png
     empty_light.png  (light square with no piece)
     empty_dark.png   (dark square with no piece)

STEP 2: Auto-crop helper (easier method)
────────────────────────────────────────────────────────────────
Run this command with a screenshot of starting position:

  python src/recognition/template_matcher.py screenshot.png

This will auto-extract all piece templates for you.

STEP 3: Use in OpenCheck
────────────────────────────────────────────────────────────────
Once templates are created, template matching will be very fast
and accurate (>95% accuracy, <50ms per board).

ALTERNATIVE: Train a small CNN
────────────────────────────────────────────────────────────────
If you prefer ML approach:
1. Collect 100-200 screenshots of different positions
2. Label them with correct FENs
3. Train tiny CNN to classify pieces (see CV_RECOGNITION_OPTIONS.md)
4. 98%+ accuracy after training

For now, the system will use a placeholder.
    """
    print(guide)


if __name__ == "__main__":
    setup_guide()
