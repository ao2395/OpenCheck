"""
Helper script to extract piece templates from a chess.com screenshot
Run this with a screenshot of the starting position to create templates
"""

import cv2
import numpy as np
from PIL import Image
import chess
from pathlib import Path
import sys


def extract_templates_from_starting_position(screenshot_path, output_dir='templates', config_file='board_config.json'):
    """
    Extract piece templates from a screenshot of the starting position

    Args:
        screenshot_path: Path to screenshot showing starting position
        output_dir: Directory to save templates
        config_file: Path to board calibration config (optional)
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Load image
    img = cv2.imread(screenshot_path)
    if img is None:
        print(f"Error: Could not load image from {screenshot_path}")
        return False

    print(f"Loaded image: {img.shape}")

    # Convert to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Try to load board region from config first
    config_path = Path(config_file)
    if config_path.exists():
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        region = config['region']
        board_region = (region['x'], region['y'], region['width'], region['height'])
        print(f"✓ Using calibrated board region from {config_file}")
        x, y, w, h = board_region
    else:
        # Detect board region automatically
        board_region = detect_board_region(img)
        x, y, w, h = board_region
        print(f"⚠ No calibration found, using auto-detection")

    print(f"Board region: x={x}, y={y}, w={w}, h={h}")

    # Extract board
    board = img_rgb[y:y+h, x:x+w]

    # Divide into 8x8 grid
    square_h = h // 8
    square_w = w // 8

    print(f"Square size: {square_w}x{square_h}")

    # Starting position FEN
    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    board_obj = chess.Board(starting_fen)

    # Piece name mapping
    piece_names = {
        'P': 'white_pawn',
        'N': 'white_knight',
        'B': 'white_bishop',
        'R': 'white_rook',
        'Q': 'white_queen',
        'K': 'white_king',
        'p': 'black_pawn',
        'n': 'black_knight',
        'b': 'black_bishop',
        'r': 'black_rook',
        'q': 'black_queen',
        'k': 'black_king',
    }

    # Track which pieces we've saved (only save once per piece type)
    saved_pieces = set()

    # Extract each square and save piece templates
    for rank in range(8):
        for file in range(8):
            # Chess coordinates (a1 = bottom-left)
            chess_rank = 7 - rank  # Flip vertically
            chess_file = file
            square_idx = chess_rank * 8 + chess_file

            # Get piece at this square
            piece = board_obj.piece_at(square_idx)

            if piece:
                piece_char = piece.symbol()
                piece_name = piece_names.get(piece_char)

                if piece_name and piece_name not in saved_pieces:
                    # Extract square image
                    sy = rank * square_h
                    sx = file * square_w
                    square_img = board[sy:sy+square_h, sx:sx+square_w]

                    # Save template
                    output_file = output_path / f"{piece_name}.png"
                    cv2.imwrite(str(output_file), cv2.cvtColor(square_img, cv2.COLOR_RGB2BGR))

                    print(f"Saved {piece_name} template from {chess.square_name(square_idx)}")
                    saved_pieces.add(piece_name)

    # Save empty square templates (light and dark)
    # Extract from e3 (light) and d3 (dark) which are empty in starting position
    for empty_rank, empty_file, square_type in [(5, 4, 'light'), (5, 3, 'dark')]:
        sy = empty_rank * square_h
        sx = empty_file * square_w
        square_img = board[sy:sy+square_h, sx:sx+square_w]

        output_file = output_path / f"empty_{square_type}.png"
        cv2.imwrite(str(output_file), cv2.cvtColor(square_img, cv2.COLOR_RGB2BGR))
        print(f"Saved empty_{square_type} template")

    print(f"\n✓ Successfully extracted {len(saved_pieces)} piece templates + 2 empty squares")
    print(f"Templates saved to: {output_path.absolute()}")
    print("\nTemplates created:")
    for piece_name in sorted(saved_pieces):
        print(f"  - {piece_name}.png")
    print("  - empty_light.png")
    print("  - empty_dark.png")

    return True


def detect_board_region(img):
    """
    Detect the chess board region in the image

    Args:
        img: OpenCV image (BGR)

    Returns:
        (x, y, width, height) of board region
    """
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


if __name__ == "__main__":
    print("=" * 70)
    print("Chess.com Template Extractor")
    print("=" * 70)
    print()
    print("This script extracts piece templates from a screenshot of the")
    print("starting position on chess.com")
    print()
    print("INSTRUCTIONS:")
    print("1. Go to chess.com and start a new game")
    print("2. Take a screenshot of the starting position")
    print("3. Run this script with the screenshot path:")
    print()
    print("   python src/recognition/extract_templates.py screenshot.png")
    print()
    print("=" * 70)
    print()

    if len(sys.argv) < 2:
        print("ERROR: Please provide screenshot path")
        print("Usage: python src/recognition/extract_templates.py <screenshot.png>")
        sys.exit(1)

    screenshot_path = sys.argv[1]

    if not Path(screenshot_path).exists():
        print(f"ERROR: File not found: {screenshot_path}")
        sys.exit(1)

    success = extract_templates_from_starting_position(screenshot_path)

    if success:
        print("\n✓ Template extraction complete!")
        print("\nNext steps:")
        print("1. Verify templates look correct in the 'templates/' directory")
        print("2. Run OpenCheck with template matching:")
        print("   python src/main.py --use-templates")
    else:
        print("\n✗ Template extraction failed")
        sys.exit(1)
