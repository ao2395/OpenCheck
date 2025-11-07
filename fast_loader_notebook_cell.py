# FAST DATA LOADER - Replace the "Data Loading Functions" cell with this

def load_json_dataset(filepath, max_samples=None, sample_rate=None):
    """
    FAST dataset loader with minimal validation

    Args:
        filepath: Path to .json, .jsonl, .json.gz, or .jsonl.zst file
        max_samples: Maximum number of samples to load (None = use sample_rate)
        sample_rate: Sample every Nth line (e.g., 30 = take 1 out of 30 lines)

    Returns:
        List of (fen, best_move, evaluation) tuples
    """
    data = []

    # Auto-calculate sample rate if max_samples provided
    if max_samples and not sample_rate:
        # Assume ~300M lines, calculate rate to get max_samples
        estimated_total = 300_000_000
        sample_rate = max(1, estimated_total // max_samples)
        print(f"Auto sample rate: 1 in {sample_rate} lines")

    sample_rate = sample_rate or 1  # No sampling by default

    # Check file type
    is_gzipped = filepath.endswith('.gz')
    is_jsonl = 'jsonl' in filepath

    if not is_jsonl:
        print("ERROR: Fast loader requires JSONL format!")
        print("Convert your data to JSONL (one JSON per line)")
        return []

    open_fn = gzip.open if is_gzipped else open
    mode = 'rt' if is_gzipped else 'r'

    print(f"Fast loading from {filepath}...")
    print(f"Sampling: 1 in {sample_rate} lines")

    # Fast loading with minimal parsing
    line_count = 0
    valid_count = 0

    with open_fn(filepath, mode) as f:
        for line in tqdm(f, desc="Loading", unit=" lines"):
            line_count += 1

            # Sample every Nth line
            if line_count % sample_rate != 0:
                continue

            try:
                obj = json.loads(line.strip())

                # Fast extraction without validation
                fen = obj['fen']
                best_move = obj['evals'][0]['pvs'][0]['line'].split()[0]

                # Get evaluation
                evaluation = obj['evals'][0]['pvs'][0].get('cp', 0)
                if 'mate' in obj['evals'][0]['pvs'][0]:
                    mate = obj['evals'][0]['pvs'][0]['mate']
                    evaluation = 10000 if mate > 0 else -10000

                data.append((fen, best_move, evaluation))
                valid_count += 1

                # Stop if we hit max_samples
                if max_samples and len(data) >= max_samples:
                    break

            except (KeyError, IndexError, json.JSONDecodeError):
                continue

    print(f"\nProcessed {line_count:,} lines")
    print(f"Successfully loaded {len(data):,} positions")

    # Validate a small sample (100 random positions)
    if data:
        import random
        sample_size = min(100, len(data))
        sample_indices = random.sample(range(len(data)), sample_size)

        valid_sample = 0
        for i in sample_indices:
            fen, move, _ = data[i]
            try:
                board = chess.Board(fen)
                if chess.Move.from_uci(move) in board.legal_moves:
                    valid_sample += 1
            except:
                pass

        print(f"Validation check: {valid_sample}/{sample_size} valid ({valid_sample/sample_size*100:.1f}%)")

    return data


def parse_position(obj):
    """Kept for compatibility - not used by fast loader"""
    pass
