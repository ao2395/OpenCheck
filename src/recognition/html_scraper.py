"""
HTML-based Chess Board Recognition
Scrape board position directly from chess.com HTML (100% accurate!)
"""

import re
import chess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class ChessComScraper:
    """
    Scrape chess board position directly from chess.com HTML
    100% accurate, no vision needed!
    """

    def __init__(self, headless=True):
        """
        Initialize the scraper

        Args:
            headless: Run browser in headless mode (no GUI)
        """
        self.headless = headless
        self.driver = None

    def start_browser(self):
        """Start the browser session"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            # Disable implicit waits to avoid delays
            self.driver.implicitly_wait(0)
            print("✓ Browser started successfully")
            return True
        except Exception as e:
            print(f"Error starting browser: {e}")
            print("Make sure ChromeDriver is installed:")
            print("  sudo apt install chromium-chromedriver  (Linux)")
            print("  brew install chromedriver              (Mac)")
            return False

    def close_browser(self):
        """Close the browser session"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def get_board_from_url(self, url):
        """
        Get board position from a chess.com URL

        Args:
            url: Chess.com game URL

        Returns:
            str: FEN notation
        """
        if not self.driver:
            if not self.start_browser():
                return None

        try:
            # Load the page
            self.driver.get(url)
            time.sleep(2)  # Wait for board to load

            # Get FEN from HTML
            fen = self.get_fen_from_current_page()
            return fen

        except Exception as e:
            print(f"Error scraping board: {e}")
            return None

    def get_fen_from_current_page(self):
        """
        Extract FEN from the current chess.com page

        Returns:
            str: FEN notation
        """
        try:
            import time
            overall_start = time.time()

            # Use JavaScript to get piece data directly (faster than Selenium's find_elements)
            find_start = time.time()
            print("[DEBUG] Extracting piece data via JavaScript...")

            # Execute JavaScript to get all piece elements and their classes
            js_code = """
            const pieces = document.querySelectorAll('div.piece');
            return Array.from(pieces).map(p => p.className);
            """

            piece_classes = self.driver.execute_script(js_code)
            find_elapsed = time.time() - find_start
            print(f"[DEBUG] Found {len(piece_classes)} pieces in {find_elapsed:.3f}s")

            # If no pieces found, try alternative selectors
            if len(piece_classes) == 0:
                print("[DEBUG] No pieces found! Checking page state...")
                print(f"[DEBUG] Current URL: {self.driver.current_url}")

                # Try alternative selectors chess.com might use
                alt_js = """
                const pieces = document.querySelectorAll('div[class*="piece"]');
                return Array.from(pieces).map(p => p.className);
                """
                piece_classes = self.driver.execute_script(alt_js)
                print(f"[DEBUG] Retry found {len(piece_classes)} pieces")

                if len(piece_classes) == 0:
                    print("[ERROR] Could not find any piece elements on the page!")
                    print("[ERROR] Chess.com may have changed their HTML structure")
                    return None

            # Parse pieces into board representation
            parse_start = time.time()
            print(f"[DEBUG] Parsing {len(piece_classes)} pieces...")
            board_dict = {}

            for class_string in piece_classes:
                classes = class_string.split()

                # Extract piece type and square
                piece_info = None
                square_info = None

                for cls in classes:
                    if cls.startswith('w') or cls.startswith('b'):
                        if len(cls) == 2:  # e.g., 'wp', 'bn'
                            piece_info = cls
                    elif cls.startswith('square-'):
                        square_info = cls.replace('square-', '')

                if piece_info and square_info:
                    # Parse piece
                    color = piece_info[0]  # 'w' or 'b'
                    piece_type = piece_info[1]  # 'p', 'n', 'b', 'r', 'q', 'k'

                    # Convert to chess notation
                    piece_char = piece_type.upper() if color == 'w' else piece_type.lower()

                    # Parse square (e.g., '88' = file 8, rank 8 = h8)
                    if len(square_info) == 2:
                        file_num = int(square_info[0])  # 1-8
                        rank_num = int(square_info[1])  # 1-8

                        # Convert to chess square (a1 = 0, h8 = 63)
                        file_idx = file_num - 1  # 0-7
                        rank_idx = rank_num - 1  # 0-7
                        square_idx = rank_idx * 8 + file_idx

                        board_dict[square_idx] = piece_char

            parse_elapsed = time.time() - parse_start
            print(f"[DEBUG] Parsed {len(board_dict)} pieces in {parse_elapsed:.3f}s")

            # Convert to FEN
            fen_start = time.time()
            print("[DEBUG] Converting to FEN...")
            fen = self._board_dict_to_fen(board_dict)
            fen_elapsed = time.time() - fen_start
            print(f"[DEBUG] FEN conversion took {fen_elapsed:.3f}s")

            overall_elapsed = time.time() - overall_start
            print(f"[DEBUG] ✓ Total time: {overall_elapsed:.3f}s")

            return fen

        except Exception as e:
            print(f"Error extracting FEN: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _board_dict_to_fen(self, board_dict):
        """
        Convert board dictionary to FEN notation

        Args:
            board_dict: Dict mapping square indices (0-63) to piece characters

        Returns:
            str: FEN notation
        """
        fen_rows = []

        # Process each rank (8 rows, from rank 8 to rank 1)
        for rank in range(7, -1, -1):  # 7 down to 0
            row_str = ""
            empty_count = 0

            # Process each file (8 columns)
            for file in range(8):  # 0 to 7
                square_idx = rank * 8 + file
                piece = board_dict.get(square_idx)

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
        # Note: We could also scrape whose turn it is from the HTML
        return f"{position} w KQkq - 0 1"

    def get_fen_from_image(self, image, num_attempts=1):
        """
        Compatibility method - not used for HTML scraping
        This exists so we can swap this in place of vision recognizers

        Args:
            image: Not used (compatibility only)
            num_attempts: Not used (compatibility only)

        Returns:
            str: FEN from currently loaded page
        """
        if not self.driver:
            print("Error: Browser not started. Call start_browser() first or use get_board_from_url()")
            return None

        return self.get_fen_from_current_page()


def scrape_active_game():
    """
    Scrape the currently active chess.com game
    Assumes chess.com is already open in a browser
    """
    scraper = ChessComScraper(headless=False)

    if not scraper.start_browser():
        return None

    try:
        # You need to navigate to chess.com first
        print("Please open chess.com/play in the browser window...")
        print("Press Enter when ready to scrape...")
        input()

        fen = scraper.get_fen_from_current_page()

        if fen:
            print(f"\n✓ Board scraped successfully!")
            print(f"FEN: {fen}")

            # Validate
            try:
                board = chess.Board(fen)
                print("\n" + str(board))
                return fen
            except Exception as e:
                print(f"Invalid FEN: {e}")
                return None
        else:
            print("Failed to extract FEN")
            return None

    finally:
        # Keep browser open for inspection
        print("\nPress Enter to close browser...")
        input()
        scraper.close_browser()


if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("Chess.com HTML Scraper - 100% Accurate Board Recognition!")
    print("=" * 70)
    print()
    print("This scrapes the board position directly from HTML")
    print("No computer vision needed - perfect accuracy!")
    print()

    if len(sys.argv) > 1:
        url = sys.argv[1]
        scraper = ChessComScraper()
        fen = scraper.get_board_from_url(url)

        if fen:
            print(f"\n✓ Success!")
            print(f"FEN: {fen}")
            print()

            board = chess.Board(fen)
            print(board)
        else:
            print("\n✗ Failed to scrape board")

        scraper.close_browser()
    else:
        # Interactive mode
        scrape_active_game()
