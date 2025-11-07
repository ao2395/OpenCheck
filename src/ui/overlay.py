"""
GUI Overlay for displaying chess move suggestions
Transparent, always-on-top window that shows the best move
"""

import tkinter as tk
from tkinter import ttk
import chess


class MoveOverlay:
    """
    Transparent overlay window for displaying chess move suggestions
    """
    def __init__(self, alpha=0.85, position=(100, 100)):
        """
        Args:
            alpha: Window transparency (0.0-1.0, 1.0 = opaque)
            position: (x, y) initial position of the overlay
        """
        self.root = tk.Tk()
        self.root.title("OpenCheck")

        # Window settings
        self.root.attributes('-alpha', alpha)
        self.root.attributes('-topmost', True)  # Always on top
        self.root.overrideredirect(True)  # Remove window decorations

        # Position
        self.root.geometry(f"+{position[0]}+{position[1]}")

        # Draggable window
        self.root.bind('<Button-1>', self.start_drag)
        self.root.bind('<B1-Motion>', self.drag_window)

        # Visibility toggle
        self.visible = True
        self.root.bind('<F9>', self.toggle_visibility)

        # Create UI
        self._create_ui()

        # Current state
        self.current_move = None
        self.current_eval = None
        self.current_confidence = None

    def _create_ui(self):
        """Create the overlay UI"""
        # Main frame with border
        self.frame = tk.Frame(
            self.root,
            bg='#2c3e50',
            bd=2,
            relief='solid',
            highlightbackground='#3498db',
            highlightthickness=2
        )
        self.frame.pack(padx=5, pady=5)

        # Title bar (for dragging)
        title_frame = tk.Frame(self.frame, bg='#34495e', cursor='fleur')
        title_frame.pack(fill='x', padx=5, pady=(5, 0))

        title_label = tk.Label(
            title_frame,
            text="♔ OpenCheck",
            font=('Arial', 10, 'bold'),
            bg='#34495e',
            fg='#ecf0f1',
            cursor='fleur'
        )
        title_label.pack(side='left', padx=5, pady=3)

        # Close button
        close_btn = tk.Label(
            title_frame,
            text="✕",
            font=('Arial', 10, 'bold'),
            bg='#34495e',
            fg='#e74c3c',
            cursor='hand2'
        )
        close_btn.pack(side='right', padx=5)
        close_btn.bind('<Button-1>', lambda e: self.hide())

        # Enable dragging on title bar
        title_frame.bind('<Button-1>', self.start_drag)
        title_frame.bind('<B1-Motion>', self.drag_window)
        title_label.bind('<Button-1>', self.start_drag)
        title_label.bind('<B1-Motion>', self.drag_window)

        # Content frame
        content_frame = tk.Frame(self.frame, bg='#2c3e50')
        content_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Best move display
        self.move_label = tk.Label(
            content_frame,
            text="Waiting for move...",
            font=('Arial', 16, 'bold'),
            bg='#2c3e50',
            fg='#2ecc71'
        )
        self.move_label.pack(pady=(0, 5))

        # Move in standard notation
        self.notation_label = tk.Label(
            content_frame,
            text="",
            font=('Arial', 12),
            bg='#2c3e50',
            fg='#95a5a6'
        )
        self.notation_label.pack(pady=(0, 5))

        # Evaluation
        self.eval_label = tk.Label(
            content_frame,
            text="",
            font=('Arial', 11),
            bg='#2c3e50',
            fg='#ecf0f1'
        )
        self.eval_label.pack(pady=(0, 2))

        # Confidence
        self.confidence_label = tk.Label(
            content_frame,
            text="",
            font=('Arial', 10),
            bg='#2c3e50',
            fg='#95a5a6'
        )
        self.confidence_label.pack()

        # Status/help text
        help_label = tk.Label(
            content_frame,
            text="F9: Toggle | Drag to move",
            font=('Arial', 8),
            bg='#2c3e50',
            fg='#7f8c8d'
        )
        help_label.pack(pady=(10, 0))

    def start_drag(self, event):
        """Start dragging the window"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def drag_window(self, event):
        """Drag the window"""
        x = self.root.winfo_x() + event.x - self.drag_start_x
        y = self.root.winfo_y() + event.y - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def toggle_visibility(self, event=None):
        """Toggle overlay visibility (F9)"""
        if self.visible:
            self.hide()
        else:
            self.show()

    def hide(self):
        """Hide the overlay"""
        self.root.withdraw()
        self.visible = False

    def show(self):
        """Show the overlay"""
        self.root.deiconify()
        self.visible = True

    def update_move(self, move_uci, evaluation=None, confidence=None, fen=None):
        """
        Update the displayed move

        Args:
            move_uci: Move in UCI format (e.g., "e2e4")
            evaluation: Position evaluation in centipawns (optional)
            confidence: Model confidence 0-1 (optional)
            fen: Board FEN for converting to standard notation (optional)
        """
        self.current_move = move_uci
        self.current_eval = evaluation
        self.current_confidence = confidence

        # Display UCI move
        self.move_label.config(text=f"♟ {move_uci}")

        # Convert to standard notation if FEN provided
        if fen:
            try:
                board = chess.Board(fen)
                move = chess.Move.from_uci(move_uci)
                san = board.san(move)

                # Get from/to squares for display
                from_square = chess.square_name(move.from_square)
                to_square = chess.square_name(move.to_square)

                self.notation_label.config(
                    text=f"{san}  ({from_square} → {to_square})"
                )
            except:
                self.notation_label.config(text="")
        else:
            # Just show from/to
            try:
                move = chess.Move.from_uci(move_uci)
                from_square = chess.square_name(move.from_square)
                to_square = chess.square_name(move.to_square)
                self.notation_label.config(text=f"{from_square} → {to_square}")
            except:
                self.notation_label.config(text="")

        # Display evaluation
        if evaluation is not None:
            eval_text = self._format_evaluation(evaluation)
            self.eval_label.config(text=f"Eval: {eval_text}")
        else:
            self.eval_label.config(text="")

        # Display confidence
        if confidence is not None:
            conf_pct = confidence * 100
            conf_text = f"Confidence: {conf_pct:.1f}%"

            # Color code by confidence
            if conf_pct >= 70:
                color = '#2ecc71'  # Green
            elif conf_pct >= 40:
                color = '#f39c12'  # Orange
            else:
                color = '#e74c3c'  # Red

            self.confidence_label.config(text=conf_text, fg=color)
        else:
            self.confidence_label.config(text="")

    def _format_evaluation(self, eval_cp):
        """
        Format evaluation in centipawns to readable text

        Args:
            eval_cp: Evaluation in centipawns

        Returns:
            Formatted string
        """
        if abs(eval_cp) > 5000:
            # Mate score
            if eval_cp > 0:
                return "White winning"
            else:
                return "Black winning"
        else:
            # Regular evaluation
            pawns = eval_cp / 100
            if pawns > 0:
                return f"+{pawns:.2f}"
            else:
                return f"{pawns:.2f}"

    def show_error(self, message):
        """Display an error message"""
        self.move_label.config(text="⚠ Error", fg='#e74c3c')
        self.notation_label.config(text=message)
        self.eval_label.config(text="")
        self.confidence_label.config(text="")

    def show_loading(self):
        """Display loading state"""
        self.move_label.config(text="🔍 Analyzing...", fg='#3498db')
        self.notation_label.config(text="")
        self.eval_label.config(text="")
        self.confidence_label.config(text="")

    def show_waiting(self):
        """Display waiting state"""
        self.move_label.config(text="♟ Waiting...", fg='#95a5a6')
        self.notation_label.config(text="Start a game on chess.com")
        self.eval_label.config(text="")
        self.confidence_label.config(text="")

    def run(self):
        """Start the overlay (blocking)"""
        self.root.mainloop()

    def update(self):
        """Process pending events (non-blocking)"""
        self.root.update()

    def destroy(self):
        """Close the overlay"""
        self.root.destroy()


# Example usage
if __name__ == "__main__":
    # Create overlay
    overlay = MoveOverlay(alpha=0.9, position=(50, 50))

    # Show waiting state
    overlay.show_waiting()

    # Simulate move updates
    import time
    overlay.root.after(2000, lambda: overlay.show_loading())
    overlay.root.after(3000, lambda: overlay.update_move(
        "e2e4",
        evaluation=25,
        confidence=0.87,
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    ))

    # Another move after 5 seconds
    overlay.root.after(8000, lambda: overlay.update_move(
        "g1f3",
        evaluation=15,
        confidence=0.92,
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    ))

    print("Overlay started! Press F9 to toggle visibility")
    print("Drag the title bar to move the window")
    print("Close with the X button or Ctrl+C in terminal")

    # Run
    try:
        overlay.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        overlay.destroy()
