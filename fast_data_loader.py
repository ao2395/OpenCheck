# Fast Data Loading - Add this cell BEFORE the data loading cell

import multiprocessing as mp
from functools import partial

def parse_position_fast(line, validate_sample_rate=0.001):
    """
    Fast parsing with minimal validation
    Only validates a small sample to catch major issues

    Args:
        line: JSON line string
        validate_sample_rate: Fraction of positions to validate (0.001 = 0.1%)
    """
    try:
        obj = json.loads(line.strip())

        fen = obj.get('fen')
        evals = obj.get('evals')

        if not fen or not evals or not evals[0].get('pvs'):
            return None

        first_pv = evals[0]['pvs'][0]
        line_moves = first_pv.get('line', '')

        if not line_moves:
            return None

        moves = line_moves.strip().split()
        if not moves:
            return None

        best_move = moves[0]

        # Get evaluation
        evaluation = first_pv.get('cp', 0)
        if 'mate' in first_pv:
            mate = first_pv['mate']
            evaluation = 10000 if mate > 0 else -10000

        # Only validate a small sample (0.1% by default)
        if random.random() < validate_sample_rate:
            try:
                board = chess.Board(fen)
                move = chess.Move.from_uci(best_move)
                if move not in board.legal_moves:
                    return None
            except:
                return None

        return (fen, best_move, evaluation)

    except:
        return None


def load_json_dataset_fast(filepath, max_samples=None, num_workers=4, validate_rate=0.001):
    """
    FAST dataset loading with multiprocessing and minimal validation

    Args:
        filepath: Path to .json, .jsonl, .json.gz, or .jsonl.zst file
        max_samples: Maximum number of samples to load
        num_workers: Number of parallel workers
        validate_rate: Fraction of positions to validate (0.001 = 0.1%)

    Returns:
        List of (fen, best_move, evaluation) tuples
    """
    import random

    data = []
    is_gzipped = filepath.endswith('.gz')
    is_jsonl = 'jsonl' in filepath

    if not is_jsonl:
        print("ERROR: This fast loader only works with JSONL files!")
        print("Use the regular loader for JSON arrays.")
        return []

    open_fn = gzip.open if is_gzipped else open
    mode = 'rt' if is_gzipped else 'r'

    print(f"Fast loading from {filepath}...")
    print(f"Workers: {num_workers}, Validation rate: {validate_rate*100}%")

    # Read all lines first (faster than processing line-by-line)
    print("Reading file...")
    with open_fn(filepath, mode) as f:
        if max_samples:
            lines = [f.readline() for _ in range(max_samples) if f.readline()]
        else:
            lines = f.readlines()

    print(f"Processing {len(lines)} lines with {num_workers} workers...")

    # Use multiprocessing pool
    parse_fn = partial(parse_position_fast, validate_sample_rate=validate_rate)

    with mp.Pool(num_workers) as pool:
        # Process in chunks with progress bar
        chunk_size = 10000
        for i in tqdm(range(0, len(lines), chunk_size), desc="Loading"):
            chunk = lines[i:i+chunk_size]
            results = pool.map(parse_fn, chunk)

            # Filter out None values
            data.extend([r for r in results if r is not None])

    print(f"Successfully loaded {len(data)} valid positions")
    return data
