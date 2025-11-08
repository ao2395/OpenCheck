"""
OpenCheck - Real-time Chess Board Analyzer
Main application entry point
"""

import os
import sys
import time
import threading
import random
from pathlib import Path
from dotenv import load_dotenv
import chess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from capture.screenshot import ScreenCapture
from recognition.vision_api import BoardRecognizer
from recognition.template_matcher import TemplateMatcher
from engine.model import ChessEngine
from ui.overlay import MoveOverlay
from ui.console import ConsoleOutput


class OpenCheckApp:
    """
    Main application class for OpenCheck
    Integrates all components for real-time chess analysis
    """

    def __init__(self, config=None):
        """
        Initialize the application

        Args:
            config: Configuration dictionary (optional)
        """
        # Load environment variables
        load_dotenv()

        # Default configuration
        self.config = {
            'model_path': 'models/chess_model.pth',
            'capture_interval': 2.0,  # seconds
            'monitor_number': 1,
            'show_overlay': True,
            'show_console': True,
            'overlay_alpha': 0.85,
            'overlay_position': (100, 100),
            'verbose': True,
            'vision_api': 'gemini',  # 'gemini', 'claude', or 'openai'
            'use_templates': False,  # Use template matching instead of vision API
            'templates_dir': 'templates',
            'board_config': 'board_config.json',  # Board calibration config
        }

        # Override with provided config
        if config:
            self.config.update(config)

        # Components
        self.screen_capture = None
        self.board_recognizer = None
        self.chess_engine = None
        self.overlay = None
        self.console = None

        # State
        self.running = False
        self.last_fen = None

    def initialize(self):
        """Initialize all components"""
        # Console output
        if self.config['show_console']:
            self.console = ConsoleOutput(
                verbose=self.config['verbose'],
                use_colors=True
            )
            self.console.print_config(self.config)
        else:
            self.console = None

        try:
            # Screen capture
            self._log("Initializing screen capture...", 'info')
            self.screen_capture = ScreenCapture(
                monitor_number=self.config['monitor_number']
            )

            # Board recognizer (Template Matching or Vision API)
            self._log("Initializing board recognizer...", 'info')
            if self.config['use_templates']:
                self._log("Using template matching for board recognition", 'info')
                self.board_recognizer = TemplateMatcher(
                    templates_dir=self.config['templates_dir'],
                    config_file=self.config['board_config']
                )
            else:
                self._log(f"Using {self.config['vision_api']} vision API for board recognition", 'info')
                self.board_recognizer = BoardRecognizer(
                    prefer=self.config['vision_api']
                )

            # Chess engine (your trained model)
            model_path = self.config['model_path']
            if not Path(model_path).exists():
                self._log(
                    f"Model not found at {model_path}. Please train the model first!",
                    'error'
                )
                self._log(
                    "See chess_model_training.ipynb for training instructions.",
                    'info'
                )
                return False

            self._log("Loading chess engine...", 'info')
            self.chess_engine = ChessEngine(model_path)

            if self.console:
                self.console.print_model_info(model_path)

            # GUI Overlay
            if self.config['show_overlay']:
                self._log("Initializing GUI overlay...", 'info')
                self.overlay = MoveOverlay(
                    alpha=self.config['overlay_alpha'],
                    position=self.config['overlay_position']
                )
                self.overlay.show_waiting()

            self._log("All components initialized successfully!", 'success')
            return True

        except Exception as e:
            self._log(f"Initialization failed: {e}", 'error')
            return False

    def _log(self, message, status='info'):
        """Helper to log messages"""
        if self.console:
            self.console.print_status(message, status)
        else:
            print(f"[{status.upper()}] {message}")

    def analyze_position(self):
        """Capture, recognize, and analyze the current position"""
        try:
            start_time = time.time()

            # Show loading state
            if self.overlay:
                self.overlay.show_loading()

            if self.console and self.config['verbose']:
                self.console.print_analysis_start()

            # Step 1: Capture screenshot
            img = self.screen_capture.capture_full_screen()

            # Save screenshot for debugging
            if self.config.get('save_screenshots', False):
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_path = f"debug_screenshot_{timestamp}.png"
                img.save(debug_path)
                self._log(f"Saved screenshot to {debug_path}", 'info')

            if self.console and self.config['verbose']:
                self.console.print_capture_info(img.size)

            # Step 2: Extract FEN from image
            num_attempts = self.config.get('vision_attempts', 1)
            fen = self.board_recognizer.get_fen_from_image(img, num_attempts=num_attempts)

            if not fen:
                self._log("Failed to extract FEN from image", 'error')
                if self.overlay:
                    self.overlay.show_error("Could not recognize board")
                return

            # Check if position changed
            if fen == self.last_fen:
                # Position unchanged, skip analysis
                return

            self.last_fen = fen

            if self.console and self.config['verbose']:
                self.console.print_fen_extracted(fen)

            if self.console and self.config['verbose']:
                self.console.print_board(fen)

            # Validate FEN before predicting
            try:
                board = chess.Board(fen)
                legal_moves = list(board.legal_moves)
                self._log(f"Position has {len(legal_moves)} legal moves", 'info')

                if len(legal_moves) == 0:
                    self._log("Position has no legal moves (checkmate or stalemate)", 'warning')
                    if self.overlay:
                        self.overlay.show_error("Game over")
                    return
            except Exception as e:
                self._log(f"Invalid FEN from vision API: {e}", 'error')
                if self.overlay:
                    self.overlay.show_error("Invalid board position")
                return

            # Step 3: Predict best move
            moves = self.chess_engine.predict_move(fen, top_k=3)

            if not moves:
                self._log("No legal moves predicted by model", 'warning')
                # Fallback: show a random legal move
                if legal_moves:
                    fallback_move = random.choice(legal_moves).uci()
                    self._log(f"Using random legal move: {fallback_move}", 'info')
                    moves = [(fallback_move, 0.0)]
                else:
                    if self.overlay:
                        self.overlay.show_error("No moves found")
                    return

            best_move, confidence = moves[0]

            # Verify the move is actually legal
            try:
                move_obj = chess.Move.from_uci(best_move)
                if move_obj not in board.legal_moves:
                    self._log(f"Model predicted illegal move: {best_move}", 'error')
                    # Try next move in the list
                    for alt_move, alt_conf in moves[1:]:
                        alt_move_obj = chess.Move.from_uci(alt_move)
                        if alt_move_obj in board.legal_moves:
                            self._log(f"Using alternative legal move: {alt_move}", 'info')
                            best_move, confidence = alt_move, alt_conf
                            break
                    else:
                        self._log("No legal moves in top predictions", 'error')
                        if self.overlay:
                            self.overlay.show_error("Model error")
                        return
            except Exception as e:
                self._log(f"Error validating move: {e}", 'error')
                if self.overlay:
                    self.overlay.show_error("Invalid move")
                return

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Step 4: Display results
            # Console output
            if self.console:
                self.console.print_move(
                    best_move,
                    evaluation=None,  # We don't have eval from the model
                    confidence=confidence,
                    fen=fen
                )
                self.console.print_analysis_complete(duration_ms)

            # Overlay output
            if self.overlay:
                self.overlay.update_move(
                    best_move,
                    evaluation=None,
                    confidence=confidence,
                    fen=fen
                )

        except KeyboardInterrupt:
            raise
        except Exception as e:
            self._log(f"Analysis error: {e}", 'error')
            if self.overlay:
                self.overlay.show_error(str(e))

    def trigger_analysis(self):
        """Manually trigger a single analysis (called by button press)"""
        # Run in a separate thread to avoid blocking the UI
        threading.Thread(target=self.analyze_position, daemon=True).start()

    def run(self):
        """Start the application"""
        # Initialize
        if not self.initialize():
            return

        self._log("Starting OpenCheck...", 'success')
        self._log("Click 'Analyze Position' button to capture and analyze", 'info')

        if self.console:
            self.console.print_separator()
            self.console.print_waiting()

        # Connect overlay button to trigger analysis
        self.running = True
        if self.overlay:
            self.overlay.set_capture_callback(self.trigger_analysis)

        try:
            if self.overlay:
                # Run overlay (blocking)
                self.overlay.run()
            else:
                # No overlay, just keep running
                self._log("Warning: No overlay available. Use Ctrl+C to exit.", 'warning')
                while self.running:
                    time.sleep(0.1)

        except KeyboardInterrupt:
            self._log("\nShutting down...", 'info')
        finally:
            self.stop()

    def stop(self):
        """Stop the application"""
        self.running = False

        if self.overlay:
            self.overlay.destroy()

        self._log("OpenCheck stopped", 'info')


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='OpenCheck - Chess Board Analyzer')

    parser.add_argument(
        '--model',
        type=str,
        default='models/chess_model.pth',
        help='Path to trained model file'
    )

    parser.add_argument(
        '--interval',
        type=float,
        default=2.0,
        help='(Deprecated - manual capture only) Capture interval in seconds'
    )

    parser.add_argument(
        '--no-overlay',
        action='store_true',
        help='Disable GUI overlay'
    )

    parser.add_argument(
        '--no-console',
        action='store_true',
        help='Disable console output'
    )

    parser.add_argument(
        '--vision-api',
        type=str,
        choices=['gemini', 'claude', 'openai'],
        default='gemini',
        help='Vision API to use (default: gemini)'
    )

    parser.add_argument(
        '--monitor',
        type=int,
        default=1,
        help='Monitor number to capture (default: 1)'
    )

    parser.add_argument(
        '--save-screenshots',
        action='store_true',
        help='Save screenshots for debugging vision accuracy'
    )

    parser.add_argument(
        '--vision-attempts',
        type=int,
        default=1,
        help='Number of vision API attempts (uses most common result, default: 1)'
    )

    parser.add_argument(
        '--use-templates',
        action='store_true',
        help='Use template matching instead of vision API (more accurate for consistent board position)'
    )

    parser.add_argument(
        '--templates-dir',
        type=str,
        default='templates',
        help='Directory containing piece templates (default: templates/)'
    )

    parser.add_argument(
        '--board-config',
        type=str,
        default='board_config.json',
        help='Board calibration config file (default: board_config.json)'
    )

    args = parser.parse_args()

    # Build config from args
    config = {
        'model_path': args.model,
        'capture_interval': args.interval,
        'monitor_number': args.monitor,
        'show_overlay': not args.no_overlay,
        'show_console': not args.no_console,
        'vision_api': args.vision_api,
        'save_screenshots': args.save_screenshots,
        'vision_attempts': args.vision_attempts,
        'use_templates': args.use_templates,
        'templates_dir': args.templates_dir,
        'board_config': args.board_config,
    }

    # Create and run app
    app = OpenCheckApp(config)

    try:
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
