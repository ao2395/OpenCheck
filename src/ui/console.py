"""
Console output interface for chess move analysis
Pretty-printed terminal output with colors
"""

import sys
import chess
from datetime import datetime


class ConsoleOutput:
    """
    Handles console output for chess analysis
    """

    # ANSI color codes
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'green': '\033[92m',
        'blue': '\033[94m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'cyan': '\033[96m',
        'magenta': '\033[95m',
        'white': '\033[97m',
        'gray': '\033[90m',
    }

    def __init__(self, verbose=True, use_colors=True):
        """
        Args:
            verbose: Show detailed output
            use_colors: Use ANSI colors in terminal
        """
        self.verbose = verbose
        self.use_colors = use_colors and sys.stdout.isatty()
        self.move_count = 0

        self._print_header()

    def _colorize(self, text, color):
        """Apply color to text if colors are enabled"""
        if self.use_colors and color in self.COLORS:
            return f"{self.COLORS[color]}{text}{self.COLORS['reset']}"
        return text

    def _print_header(self):
        """Print application header"""
        header = """
╔═══════════════════════════════════════╗
║         OpenCheck Chess AI            ║
║     Real-time Move Analysis           ║
╚═══════════════════════════════════════╝
"""
        print(self._colorize(header, 'cyan'))

    def print_status(self, message, status='info'):
        """
        Print a status message

        Args:
            message: Message to print
            status: One of 'info', 'success', 'warning', 'error'
        """
        color_map = {
            'info': 'blue',
            'success': 'green',
            'warning': 'yellow',
            'error': 'red',
        }

        symbol_map = {
            'info': 'ℹ',
            'success': '✓',
            'warning': '⚠',
            'error': '✗',
        }

        color = color_map.get(status, 'white')
        symbol = symbol_map.get(status, '•')

        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted = f"[{timestamp}] {symbol} {message}"

        print(self._colorize(formatted, color))

    def print_move(self, move_uci, evaluation=None, confidence=None, fen=None):
        """
        Print a chess move with details

        Args:
            move_uci: Move in UCI format
            evaluation: Position evaluation in centipawns
            confidence: Model confidence 0-1
            fen: Board FEN for context
        """
        self.move_count += 1

        print("\n" + "─" * 50)
        print(self._colorize(f"Move #{self.move_count}", 'bold'))
        print("─" * 50)

        # UCI move
        print(f"  {self._colorize('UCI:', 'cyan')} {self._colorize(move_uci, 'bold')}")

        # Standard notation
        if fen:
            try:
                board = chess.Board(fen)
                move = chess.Move.from_uci(move_uci)
                san = board.san(move)

                from_sq = chess.square_name(move.from_square)
                to_sq = chess.square_name(move.to_square)

                print(f"  {self._colorize('SAN:', 'cyan')} {self._colorize(san, 'green')}")
                print(f"  {self._colorize('Move:', 'cyan')} {from_sq} → {to_sq}")
            except Exception as e:
                if self.verbose:
                    print(f"  {self._colorize('Error parsing move:', 'red')} {e}")

        # Evaluation
        if evaluation is not None:
            eval_str = self._format_evaluation(evaluation)
            eval_color = 'green' if evaluation > 0 else 'red' if evaluation < 0 else 'yellow'
            print(f"  {self._colorize('Eval:', 'cyan')} {self._colorize(eval_str, eval_color)}")

        # Confidence
        if confidence is not None:
            conf_pct = confidence * 100
            conf_color = 'green' if conf_pct >= 70 else 'yellow' if conf_pct >= 40 else 'red'
            print(f"  {self._colorize('Confidence:', 'cyan')} {self._colorize(f'{conf_pct:.1f}%', conf_color)}")

        print()

    def print_board(self, fen):
        """
        Print ASCII chess board

        Args:
            fen: Board position in FEN notation
        """
        try:
            board = chess.Board(fen)
            print("\n" + self._colorize("Current Position:", 'bold'))
            print()

            # Print board with Unicode pieces
            board_str = str(board)
            lines = board_str.split('\n')

            for i, line in enumerate(lines):
                rank = 8 - i
                colored_line = self._colorize(f"{rank} ", 'gray') + line
                print(colored_line)

            print(self._colorize("  a b c d e f g h", 'gray'))
            print()

            # Print turn
            turn = "White" if board.turn == chess.WHITE else "Black"
            print(f"{self._colorize('To move:', 'cyan')} {turn}")

        except Exception as e:
            self.print_status(f"Error displaying board: {e}", 'error')

    def print_analysis_start(self):
        """Print message when analysis starts"""
        self.print_status("Starting position analysis...", 'info')

    def print_analysis_complete(self, duration_ms):
        """
        Print analysis completion message

        Args:
            duration_ms: Analysis duration in milliseconds
        """
        self.print_status(f"Analysis complete in {duration_ms:.0f}ms", 'success')

    def print_capture_info(self, image_size):
        """
        Print screenshot capture info

        Args:
            image_size: (width, height) tuple
        """
        if self.verbose:
            self.print_status(f"Captured screenshot: {image_size[0]}x{image_size[1]}", 'info')

    def print_fen_extracted(self, fen):
        """
        Print FEN extraction success

        Args:
            fen: Extracted FEN string
        """
        if self.verbose:
            print(self._colorize("Extracted FEN:", 'cyan'))
            print(f"  {fen}")

    def print_error(self, error_msg):
        """
        Print error message

        Args:
            error_msg: Error message
        """
        self.print_status(f"Error: {error_msg}", 'error')

    def print_waiting(self):
        """Print waiting message"""
        print()
        print(self._colorize("⏳ Waiting for chess position...", 'yellow'))
        print(self._colorize("   Open chess.com and start a game", 'dim'))
        print()

    def print_model_info(self, model_path, accuracy=None):
        """
        Print model information

        Args:
            model_path: Path to model file
            accuracy: Model accuracy if available
        """
        print()
        print(self._colorize("Model Loaded:", 'green'))
        print(f"  Path: {model_path}")
        if accuracy:
            print(f"  Accuracy: {accuracy*100:.1f}%")
        print()

    def print_config(self, config):
        """
        Print configuration

        Args:
            config: Dictionary of configuration settings
        """
        print(self._colorize("Configuration:", 'cyan'))
        for key, value in config.items():
            print(f"  {key}: {value}")
        print()

    def _format_evaluation(self, eval_cp):
        """
        Format evaluation in centipawns

        Args:
            eval_cp: Evaluation in centipawns

        Returns:
            Formatted string
        """
        if abs(eval_cp) > 5000:
            if eval_cp > 0:
                return "White winning (M)"
            else:
                return "Black winning (M)"
        else:
            pawns = eval_cp / 100
            if pawns > 0:
                return f"+{pawns:.2f}"
            else:
                return f"{pawns:.2f}"

    def print_separator(self):
        """Print a separator line"""
        print(self._colorize("═" * 50, 'gray'))

    def clear_screen(self):
        """Clear the console screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')


# Example usage
if __name__ == "__main__":
    console = ConsoleOutput(verbose=True, use_colors=True)

    # Simulate application flow
    console.print_model_info("models/chess_model.pth", accuracy=0.67)

    console.print_config({
        'Capture Interval': '2.0s',
        'Vision API': 'Claude',
        'Overlay': 'Enabled',
    })

    console.print_separator()
    console.print_waiting()

    import time
    time.sleep(1)

    console.print_analysis_start()
    console.print_capture_info((1920, 1080))

    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    console.print_fen_extracted(fen)

    console.print_board(fen)

    time.sleep(0.5)

    console.print_move(
        "e7e5",
        evaluation=-15,
        confidence=0.85,
        fen=fen
    )

    console.print_analysis_complete(1250)

    console.print_separator()

    console.print_status("System ready", 'success')
