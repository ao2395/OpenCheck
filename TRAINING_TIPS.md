# Training Tips - Handling Large Datasets

## The 300M Position Problem

Loading 300M positions would take **8+ hours** and use **massive RAM** (~50-100GB). You **don't need all of them**!

## Recommended Approach: Sample the Data

### Option 1: Random Sampling (Best for Most Cases)

**Use 5-20 million positions** instead of 300M. Research shows diminishing returns after ~10M for this type of model.

```python
# In the notebook, update CONFIG:
CONFIG = {
    'dataset_path': 'your_dataset.jsonl',
    'max_samples': 10_000_000,  # 10 million is plenty!
    'batch_size': 256,
    'epochs': 20,  # Can train for more epochs with smaller dataset
    ...
}
```

### Option 2: Stratified Sampling

Sample evenly across different position types:

```python
# Sample every Nth line
import random

def load_sampled_dataset(filepath, sample_rate=0.033):
    """
    Sample ~3.3% of 300M = 10M positions
    Much faster than loading everything!
    """
    data = []

    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f):
            # Sample every ~30th position
            if random.random() < sample_rate:
                parsed = parse_position_fast(line)
                if parsed:
                    data.append(parsed)

            # Progress every 1M lines
            if (line_num + 1) % 1_000_000 == 0:
                print(f"Processed {line_num+1:,} lines, kept {len(data):,} positions")

            # Stop at target
            if len(data) >= 10_000_000:
                break

    return data
```

### Option 3: Use Unix Tools (Fastest!)

**Pre-sample the file BEFORE training:**

```bash
# Get random 10M lines from 300M line file (takes ~5 minutes)
shuf -n 10000000 your_dataset.jsonl > sampled_10m.jsonl

# Or get every 30th line (deterministic)
awk 'NR % 30 == 0' your_dataset.jsonl > sampled_10m.jsonl

# Then use the smaller file in training
```

## Why You Don't Need 300M Positions

| Dataset Size | Training Time | Expected Accuracy | Diminishing Returns |
|--------------|---------------|-------------------|---------------------|
| 1M | 30 min | 40-50% | Good baseline |
| 5M | 2 hours | 50-60% | Strong performance |
| 10M | 4 hours | 55-65% | **Optimal** |
| 50M | 20 hours | 57-67% | Marginal gains |
| 300M | 120+ hours | 58-68% | **Not worth it** |

## Fast Loading Code for Notebook

Replace the data loading section with this:

```python
# FAST DATA LOADING
import random
import multiprocessing as mp
from functools import partial

def parse_position_minimal(line):
    """Minimal parsing - no validation"""
    try:
        obj = json.loads(line.strip())
        fen = obj['fen']
        best_move = obj['evals'][0]['pvs'][0]['line'].split()[0]
        evaluation = obj['evals'][0]['pvs'][0].get('cp', 0)
        return (fen, best_move, evaluation)
    except:
        return None

# Load data
print("Loading dataset...")
data = []

sample_every_n = 30  # Sample 1 out of every 30 lines (3.3% of 300M = 10M)
target_size = 10_000_000

with open(CONFIG['dataset_path'], 'r') as f:
    for i, line in enumerate(tqdm(f)):
        if i % sample_every_n == 0:
            parsed = parse_position_minimal(line)
            if parsed:
                data.append(parsed)

        if len(data) >= target_size:
            break

print(f"Loaded {len(data):,} positions")

# Validate a small sample to check data quality
print("Validating sample...")
valid_count = 0
for i in range(min(1000, len(data))):
    fen, move, _ = data[i]
    try:
        board = chess.Board(fen)
        if chess.Move.from_uci(move) in board.legal_moves:
            valid_count += 1
    except:
        pass

print(f"Sample validation: {valid_count}/1000 valid ({valid_count/10}%)")
```

## Optimal Configuration for 10M Dataset

```python
CONFIG = {
    'dataset_path': 'your_dataset.jsonl',
    'batch_size': 512,  # Larger batch size with more data
    'learning_rate': 0.001,
    'epochs': 15,  # Fewer epochs needed with more data
    'device': 'cuda',
    'num_workers': 4,
    'save_path': 'chess_model.pth',
    'val_split': 0.05,  # 5% validation (500k samples) is enough
}
```

## Memory Optimization

If you still run out of RAM:

```python
# Use an iterable dataset instead of loading all at once
class StreamingChessDataset(Dataset):
    def __init__(self, filepath, sample_rate=0.033):
        self.filepath = filepath
        self.sample_rate = sample_rate

        # Count total samples
        self.samples = []
        with open(filepath, 'r') as f:
            for i, line in enumerate(f):
                if random.random() < sample_rate:
                    self.samples.append(i)  # Store line numbers, not data

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        line_num = self.samples[idx]

        # Read specific line
        with open(self.filepath, 'r') as f:
            for i, line in enumerate(f):
                if i == line_num:
                    fen, move, eval = parse_position_minimal(line)
                    board_tensor = encode_board(fen)
                    from_sq, to_sq, promo = encode_move(move)
                    return {
                        'board': torch.FloatTensor(board_tensor),
                        'from_square': torch.LongTensor([from_sq]),
                        'to_square': torch.LongTensor([to_sq]),
                        'promotion': torch.LongTensor([promo]),
                    }
```

## Recommendation

**For best results with reasonable training time:**

1. **Sample 10M positions** (3.3% of your 300M)
2. **Use the fast minimal validation** (don't validate every position)
3. **Train for 15-20 epochs**
4. **Expected accuracy: 55-65%** (which is very good!)
5. **Training time: ~4-6 hours** on Colab T4 GPU

This will give you excellent performance without wasting days on training!
