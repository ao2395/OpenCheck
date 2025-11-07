"""
Chess Move Prediction Model - Inference
Loads the trained .pth model and makes predictions
"""

import torch
import torch.nn as nn
import chess
import numpy as np
from pathlib import Path


class ResidualBlock(nn.Module):
    """Residual block for the chess CNN"""
    def __init__(self, channels):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU()

    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += residual
        out = self.relu(out)
        return out


class ChessMovePredictor(nn.Module):
    """CNN-based chess move prediction model"""
    def __init__(self, num_res_blocks=10, num_channels=256):
        super(ChessMovePredictor, self).__init__()

        # Initial convolution
        self.conv_input = nn.Conv2d(12, num_channels, kernel_size=3, padding=1)
        self.bn_input = nn.BatchNorm2d(num_channels)
        self.relu = nn.ReLU()

        # Residual tower
        self.res_blocks = nn.ModuleList([
            ResidualBlock(num_channels) for _ in range(num_res_blocks)
        ])

        # Policy head (move prediction)
        self.policy_conv = nn.Conv2d(num_channels, 32, kernel_size=1)
        self.policy_bn = nn.BatchNorm2d(32)
        self.policy_fc1 = nn.Linear(32 * 8 * 8, 512)

        # Three outputs: from_square, to_square, promotion
        self.from_square_head = nn.Linear(512, 64)
        self.to_square_head = nn.Linear(512, 64)
        self.promotion_head = nn.Linear(512, 5)  # none, N, B, R, Q

    def forward(self, x):
        # Input: (batch, 12, 8, 8)
        x = self.relu(self.bn_input(self.conv_input(x)))

        # Residual blocks
        for block in self.res_blocks:
            x = block(x)

        # Policy head
        policy = self.relu(self.policy_bn(self.policy_conv(x)))
        policy = policy.view(policy.size(0), -1)  # Flatten
        policy = self.relu(self.policy_fc1(policy))

        # Output heads
        from_square = self.from_square_head(policy)
        to_square = self.to_square_head(policy)
        promotion = self.promotion_head(policy)

        return from_square, to_square, promotion


def encode_board(fen):
    """
    Encode chess board from FEN to tensor representation
    Returns: (12, 8, 8) numpy array
    12 channels: 6 piece types (P,N,B,R,Q,K) × 2 colors (white, black)
    """
    board = chess.Board(fen)
    tensor = np.zeros((12, 8, 8), dtype=np.float32)

    piece_idx = {
        chess.PAWN: 0,
        chess.KNIGHT: 1,
        chess.BISHOP: 2,
        chess.ROOK: 3,
        chess.QUEEN: 4,
        chess.KING: 5,
    }

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            rank, file = divmod(square, 8)
            piece_type = piece_idx[piece.piece_type]
            color_offset = 0 if piece.color == chess.WHITE else 6
            tensor[piece_type + color_offset, rank, file] = 1

    return tensor


def decode_move(from_square, to_square, promotion_idx):
    """
    Decode move indices back to UCI format
    """
    promotion_map = {
        0: None,
        1: chess.KNIGHT,
        2: chess.BISHOP,
        3: chess.ROOK,
        4: chess.QUEEN,
    }

    move = chess.Move(from_square, to_square, promotion=promotion_map[promotion_idx])
    return move.uci()


class ChessEngine:
    """
    Chess engine wrapper for move prediction
    """
    def __init__(self, model_path, device=None):
        """
        Args:
            model_path: Path to the trained .pth file
            device: torch device (cuda/cpu). Auto-detected if None
        """
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Initialize model
        self.model = ChessMovePredictor(num_res_blocks=10, num_channels=256)

        # Load trained weights
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        checkpoint = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()

        print(f"Loaded chess model from {model_path}")
        print(f"Using device: {self.device}")
        if 'val_acc' in checkpoint:
            print(f"Model accuracy: {checkpoint['val_acc']*100:.2f}%")

    def predict_move(self, fen, top_k=3):
        """
        Predict the best move for a given FEN position

        Args:
            fen: Board position in FEN notation
            top_k: Return top K moves

        Returns:
            List of (move_uci, confidence) tuples, sorted by confidence
        """
        # Encode board
        board_tensor = torch.FloatTensor(encode_board(fen)).unsqueeze(0).to(self.device)

        # Predict
        with torch.no_grad():
            from_pred, to_pred, promo_pred = self.model(board_tensor)

            # Get probabilities
            from_probs = torch.softmax(from_pred, dim=1)[0]
            to_probs = torch.softmax(to_pred, dim=1)[0]
            promo_probs = torch.softmax(promo_pred, dim=1)[0]

            # Get top predictions
            moves = []
            board = chess.Board(fen)

            # Try top from_square and to_square combinations
            from_top_k = torch.topk(from_probs, min(top_k * 2, 64))
            to_top_k = torch.topk(to_probs, min(top_k * 2, 64))

            for from_idx, from_conf in zip(from_top_k.indices, from_top_k.values):
                for to_idx, to_conf in zip(to_top_k.indices, to_top_k.values):
                    promo_idx = torch.argmax(promo_probs).item()

                    try:
                        move_uci = decode_move(from_idx.item(), to_idx.item(), promo_idx)
                        move = chess.Move.from_uci(move_uci)

                        # Only include legal moves
                        if move in board.legal_moves:
                            confidence = (from_conf * to_conf).item()
                            moves.append((move_uci, confidence))

                            if len(moves) >= top_k:
                                break
                    except:
                        continue

                if len(moves) >= top_k:
                    break

            # Sort by confidence
            moves.sort(key=lambda x: x[1], reverse=True)

            return moves[:top_k]

    def get_best_move(self, fen):
        """
        Get the single best move for a position

        Args:
            fen: Board position in FEN notation

        Returns:
            move_uci (str): Best move in UCI format, or None if no legal move found
        """
        moves = self.predict_move(fen, top_k=1)
        return moves[0][0] if moves else None


# Example usage
if __name__ == "__main__":
    # Test the engine
    model_path = "models/chess_model.pth"

    if Path(model_path).exists():
        engine = ChessEngine(model_path)

        # Test on starting position
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        print(f"\nTest position: {test_fen}")
        print("\nTop 3 predicted moves:")

        moves = engine.predict_move(test_fen, top_k=3)
        for i, (move, conf) in enumerate(moves, 1):
            print(f"{i}. {move} (confidence: {conf:.4f})")

        best_move = engine.get_best_move(test_fen)
        print(f"\nBest move: {best_move}")
    else:
        print(f"Model not found at {model_path}")
        print("Train the model using chess_model_training.ipynb first!")
