#!/usr/bin/env python3
"""
Chess Move Prediction Model Training - HPC Version
Multi-GPU training with DataParallel
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torch.distributed as dist
from torch.nn.parallel import DataParallel
import chess
import numpy as np
from tqdm import tqdm
import json
import gzip
import os
import sys
import argparse
from pathlib import Path


# ============================================================================
# Configuration
# ============================================================================

def get_config():
    """Parse command line arguments and return config"""
    parser = argparse.ArgumentParser(description='Chess Model Training')

    parser.add_argument('--dataset', type=str, required=True,
                        help='Path to dataset JSONL file')
    parser.add_argument('--max-samples', type=int, default=10_000_000,
                        help='Maximum samples to load (default: 10M)')
    parser.add_argument('--batch-size', type=int, default=512,
                        help='Batch size per GPU (default: 512)')
    parser.add_argument('--epochs', type=int, default=20,
                        help='Number of epochs (default: 20)')
    parser.add_argument('--lr', type=float, default=0.001,
                        help='Learning rate (default: 0.001)')
    parser.add_argument('--num-workers', type=int, default=12,
                        help='DataLoader workers (default: 12)')
    parser.add_argument('--save-path', type=str, default='chess_model.pth',
                        help='Model save path (default: chess_model.pth)')
    parser.add_argument('--checkpoint-dir', type=str, default='checkpoints',
                        help='Checkpoint directory (default: checkpoints)')
    parser.add_argument('--val-split', type=float, default=0.05,
                        help='Validation split (default: 0.05)')

    args = parser.parse_args()

    config = {
        'dataset_path': args.dataset,
        'max_samples': args.max_samples,
        'batch_size': args.batch_size,
        'learning_rate': args.lr,
        'epochs': args.epochs,
        'num_workers': args.num_workers,
        'save_path': args.save_path,
        'checkpoint_dir': args.checkpoint_dir,
        'val_split': args.val_split,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
    }

    return config


# ============================================================================
# Fast Data Loading
# ============================================================================

def load_json_dataset_fast(filepath, max_samples=None):
    """
    Fast JSONL loader - loads first N samples with minimal validation

    Args:
        filepath: Path to JSONL file
        max_samples: Maximum samples to load

    Returns:
        List of (fen, best_move, evaluation) tuples
    """
    data = []

    is_gzipped = filepath.endswith('.gz')
    open_fn = gzip.open if is_gzipped else open
    mode = 'rt' if is_gzipped else 'r'

    print(f"Loading first {max_samples:,} positions from {filepath}...")

    with open_fn(filepath, mode) as f:
        for line in tqdm(f, total=max_samples, desc="Loading data", unit=" lines"):
            try:
                obj = json.loads(line.strip())
                fen = obj['fen']
                best_move = obj['evals'][0]['pvs'][0]['line'].split()[0]
                evaluation = obj['evals'][0]['pvs'][0].get('cp', 0)

                if 'mate' in obj['evals'][0]['pvs'][0]:
                    mate = obj['evals'][0]['pvs'][0]['mate']
                    evaluation = 10000 if mate > 0 else -10000

                data.append((fen, best_move, evaluation))

                if len(data) >= max_samples:
                    break

            except (KeyError, IndexError, json.JSONDecodeError):
                continue

    print(f"Loaded {len(data):,} positions")

    # Quick validation
    import random
    sample_size = min(100, len(data))
    sample_indices = random.sample(range(len(data)), sample_size)

    valid = 0
    for i in sample_indices:
        fen, move, _ = data[i]
        try:
            board = chess.Board(fen)
            if chess.Move.from_uci(move) in board.legal_moves:
                valid += 1
        except:
            pass

    print(f"Validation check: {valid}/{sample_size} valid ({valid/sample_size*100:.1f}%)")

    return data


# ============================================================================
# Board Encoding
# ============================================================================

def encode_board(fen):
    """Encode FEN to (12, 8, 8) tensor"""
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


def encode_move(move_uci):
    """Encode UCI move to indices"""
    move = chess.Move.from_uci(move_uci)
    from_square = move.from_square
    to_square = move.to_square

    promotion = 0
    if move.promotion:
        promotion_map = {
            chess.KNIGHT: 1,
            chess.BISHOP: 2,
            chess.ROOK: 3,
            chess.QUEEN: 4,
        }
        promotion = promotion_map.get(move.promotion, 0)

    return from_square, to_square, promotion


# ============================================================================
# Dataset
# ============================================================================

class ChessDataset(Dataset):
    def __init__(self, data):
        self.data = data
        print(f"Dataset contains {len(self.data):,} positions")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        fen, best_move, evaluation = self.data[idx]

        board_tensor = encode_board(fen)
        from_sq, to_sq, promo = encode_move(best_move)

        return {
            'board': torch.FloatTensor(board_tensor),
            'from_square': torch.LongTensor([from_sq]),
            'to_square': torch.LongTensor([to_sq]),
            'promotion': torch.LongTensor([promo]),
        }


# ============================================================================
# Model Architecture
# ============================================================================

class ResidualBlock(nn.Module):
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
    def __init__(self, num_res_blocks=10, num_channels=256):
        super(ChessMovePredictor, self).__init__()

        self.conv_input = nn.Conv2d(12, num_channels, kernel_size=3, padding=1)
        self.bn_input = nn.BatchNorm2d(num_channels)
        self.relu = nn.ReLU()

        self.res_blocks = nn.ModuleList([
            ResidualBlock(num_channels) for _ in range(num_res_blocks)
        ])

        self.policy_conv = nn.Conv2d(num_channels, 32, kernel_size=1)
        self.policy_bn = nn.BatchNorm2d(32)
        self.policy_fc1 = nn.Linear(32 * 8 * 8, 512)

        self.from_square_head = nn.Linear(512, 64)
        self.to_square_head = nn.Linear(512, 64)
        self.promotion_head = nn.Linear(512, 5)

    def forward(self, x):
        x = self.relu(self.bn_input(self.conv_input(x)))

        for block in self.res_blocks:
            x = block(x)

        policy = self.relu(self.policy_bn(self.policy_conv(x)))
        policy = policy.view(policy.size(0), -1)
        policy = self.relu(self.policy_fc1(policy))

        from_square = self.from_square_head(policy)
        to_square = self.to_square_head(policy)
        promotion = self.promotion_head(policy)

        return from_square, to_square, promotion


# ============================================================================
# Training Functions
# ============================================================================

def train_epoch(model, dataloader, criterion, optimizer, device, epoch):
    model.train()
    total_loss = 0
    correct_from = 0
    correct_to = 0
    correct_full = 0
    total = 0

    pbar = tqdm(dataloader, desc=f'Epoch {epoch} - Training')
    for batch in pbar:
        boards = batch['board'].to(device)
        from_squares = batch['from_square'].squeeze().to(device)
        to_squares = batch['to_square'].squeeze().to(device)
        promotions = batch['promotion'].squeeze().to(device)

        optimizer.zero_grad()

        from_pred, to_pred, promo_pred = model(boards)

        loss_from = criterion(from_pred, from_squares)
        loss_to = criterion(to_pred, to_squares)
        loss_promo = criterion(promo_pred, promotions)

        loss = loss_from + loss_to + 0.1 * loss_promo

        loss.backward()
        optimizer.step()

        _, from_predicted = torch.max(from_pred, 1)
        _, to_predicted = torch.max(to_pred, 1)
        _, promo_predicted = torch.max(promo_pred, 1)

        correct_from += (from_predicted == from_squares).sum().item()
        correct_to += (to_predicted == to_squares).sum().item()
        correct_full += ((from_predicted == from_squares) &
                        (to_predicted == to_squares) &
                        (promo_predicted == promotions)).sum().item()

        total += boards.size(0)
        total_loss += loss.item()

        pbar.set_postfix({
            'loss': f'{total_loss / (pbar.n + 1):.4f}',
            'acc': f'{100 * correct_full / total:.2f}%',
        })

    return total_loss / len(dataloader), correct_full / total


def validate(model, dataloader, criterion, device, epoch):
    model.eval()
    total_loss = 0
    correct_full = 0
    total = 0

    with torch.no_grad():
        pbar = tqdm(dataloader, desc=f'Epoch {epoch} - Validation')
        for batch in pbar:
            boards = batch['board'].to(device)
            from_squares = batch['from_square'].squeeze().to(device)
            to_squares = batch['to_square'].squeeze().to(device)
            promotions = batch['promotion'].squeeze().to(device)

            from_pred, to_pred, promo_pred = model(boards)

            loss_from = criterion(from_pred, from_squares)
            loss_to = criterion(to_pred, to_squares)
            loss_promo = criterion(promo_pred, promotions)
            loss = loss_from + loss_to + 0.1 * loss_promo

            _, from_predicted = torch.max(from_pred, 1)
            _, to_predicted = torch.max(to_pred, 1)
            _, promo_predicted = torch.max(promo_pred, 1)

            correct_full += ((from_predicted == from_squares) &
                            (to_predicted == to_squares) &
                            (promo_predicted == promotions)).sum().item()

            total += boards.size(0)
            total_loss += loss.item()

            pbar.set_postfix({
                'loss': f'{total_loss / (pbar.n + 1):.4f}',
                'acc': f'{100 * correct_full / total:.2f}%',
            })

    return total_loss / len(dataloader), correct_full / total


# ============================================================================
# Main Training Loop
# ============================================================================

def main():
    config = get_config()

    print("=" * 70)
    print("Chess Move Prediction Training - HPC Multi-GPU")
    print("=" * 70)
    print(f"\nConfiguration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()

    # Check GPU availability
    if not torch.cuda.is_available():
        print("ERROR: CUDA not available!")
        sys.exit(1)

    num_gpus = torch.cuda.device_count()
    print(f"Found {num_gpus} GPU(s)")
    for i in range(num_gpus):
        print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
    print()

    # Create checkpoint directory
    Path(config['checkpoint_dir']).mkdir(exist_ok=True)

    # Load data
    print("Loading dataset...")
    data = load_json_dataset_fast(config['dataset_path'], config['max_samples'])

    if len(data) == 0:
        print("ERROR: No data loaded!")
        sys.exit(1)

    # Create dataset
    dataset = ChessDataset(data)

    # Split train/val
    val_size = int(len(dataset) * config['val_split'])
    train_size = len(dataset) - val_size

    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset, [train_size, val_size]
    )

    print(f"\nDataset split:")
    print(f"  Training: {len(train_dataset):,} samples")
    print(f"  Validation: {len(val_dataset):,} samples")
    print()

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=True,
        num_workers=config['num_workers'],
        pin_memory=True,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=config['num_workers'],
        pin_memory=True,
    )

    # Initialize model
    print("Initializing model...")
    model = ChessMovePredictor(num_res_blocks=10, num_channels=256)

    # Multi-GPU support
    if num_gpus > 1:
        print(f"Using DataParallel with {num_gpus} GPUs")
        model = DataParallel(model)

    model = model.to(config['device'])

    num_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {num_params:,}")
    print()

    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'])
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', patience=3, factor=0.5, verbose=True
    )

    # Training loop
    best_val_acc = 0.0
    history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}

    print("Starting training...")
    print("=" * 70)

    for epoch in range(1, config['epochs'] + 1):
        print(f"\nEpoch {epoch}/{config['epochs']}")
        print("-" * 70)

        # Train
        train_loss, train_acc = train_epoch(
            model, train_loader, criterion, optimizer, config['device'], epoch
        )

        # Validate
        val_loss, val_acc = validate(
            model, val_loader, criterion, config['device'], epoch
        )

        # Update scheduler
        scheduler.step(val_acc)

        # Save history
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)

        print(f"\nResults:")
        print(f"  Train Loss: {train_loss:.4f}, Train Acc: {train_acc*100:.2f}%")
        print(f"  Val Loss: {val_loss:.4f}, Val Acc: {val_acc*100:.2f}%")

        # Save checkpoint every epoch
        checkpoint_path = Path(config['checkpoint_dir']) / f"checkpoint_epoch_{epoch}.pth"
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.module.state_dict() if num_gpus > 1 else model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'train_loss': train_loss,
            'train_acc': train_acc,
            'val_loss': val_loss,
            'val_acc': val_acc,
            'history': history,
        }, checkpoint_path)
        print(f"  Saved checkpoint: {checkpoint_path}")

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_model_path = config['save_path']
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.module.state_dict() if num_gpus > 1 else model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
            }, best_model_path)
            print(f"  ✓ New best model! Saved to {best_model_path} (Val Acc: {val_acc*100:.2f}%)")

    print("\n" + "=" * 70)
    print("Training complete!")
    print(f"Best validation accuracy: {best_val_acc*100:.2f}%")
    print(f"Best model saved to: {config['save_path']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
