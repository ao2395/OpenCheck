# OpenCheck - Real-time Chess Board Analyzer

AI-powered chess assistant that analyzes chess.com boards in real-time using computer vision and a custom-trained neural network.

## Overview

OpenCheck captures your chess.com game screen, recognizes the board position using Vision AI, and predicts the best move using a custom-trained CNN model.

### System Flow

```
Screenshot Capture → Board Recognition (Vision API) → FEN → Move Prediction (Your Model) → Display Move
```

## Project Structure

```
OpenCheck/
├── src/
│   ├── capture/
│   │   └── screenshot.py          # Real-time screen capture
│   ├── recognition/
│   │   └── vision_api.py          # Claude/OpenAI Vision API for FEN extraction
│   ├── engine/
│   │   └── model.py               # Custom move prediction model inference
│   └── ui/
│       ├── overlay.py             # GUI overlay (TODO)
│       └── console.py             # Console output (TODO)
├── models/
│   └── chess_model.pth            # Your trained model (place here after training)
├── chess_model_training.ipynb     # Training notebook for Google Colab
├── requirements.txt
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
# Use either Claude or OpenAI Vision API
ANTHROPIC_API_KEY=your_anthropic_key_here
# OR
OPENAI_API_KEY=your_openai_key_here
```

### 3. Train Your Model

**Option 1: Upload to Google Colab**

1. Upload `chess_model_training.ipynb` to Google Colab
2. Upload your dataset (JSON/JSONL format with FEN and evaluations)
3. Update the `dataset_path` in the config cell
4. Run all cells to train
5. Download `chess_model.pth` when complete
6. Place it in the `models/` directory

**Option 2: Train Locally** (requires GPU)

```bash
jupyter notebook chess_model_training.ipynb
```

## Dataset Format

Your dataset should be in JSON or JSONL format:

```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -",
  "evals": [
    {
      "knodes": 1500,
      "depth": 20,
      "pvs": [
        {
          "cp": 25,
          "line": "e2e4 e7e5 g1f3"
        }
      ]
    }
  ]
}
```

**Key Points:**
- `fen`: Board position in FEN notation (required)
- `evals[0].pvs[0].line`: Space-separated UCI moves, first move is the best move
- `cp`: Centipawn evaluation (optional)
- `mate`: Mate score (optional, alternative to cp)

**Supported Formats:**
- `.json` - Single JSON array
- `.jsonl` - One JSON object per line
- `.json.gz` / `.jsonl.gz` - Gzipped versions

## Model Architecture

- **Type**: Convolutional Neural Network (CNN) with residual blocks
- **Input**: Chess board as (12, 8, 8) tensor
  - 12 channels: 6 piece types × 2 colors
- **Output**:
  - From square (64 classes)
  - To square (64 classes)
  - Promotion piece (5 classes: none, N, B, R, Q)
- **Size**: ~19M parameters (10 residual blocks, 256 channels)

Inspired by AlphaZero architecture but trained on engine evaluations.

## Usage

### Test Model Inference

```python
from src.engine.model import ChessEngine

# Load your trained model
engine = ChessEngine('models/chess_model.pth')

# Predict best move for a position
fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
best_move = engine.get_best_move(fen)
print(f"Best move: {best_move}")

# Get top 3 moves with confidence scores
moves = engine.predict_move(fen, top_k=3)
for move, confidence in moves:
    print(f"{move}: {confidence:.4f}")
```

### Test Screenshot Capture

```python
from src.capture.screenshot import ScreenCapture

capture = ScreenCapture()
img = capture.capture_full_screen()
img.save("screenshot.png")
```

### Test Board Recognition

```python
from src.recognition.vision_api import BoardRecognizer
from PIL import Image

recognizer = BoardRecognizer(prefer='claude')
img = Image.open('chess_board.png')
fen = recognizer.get_fen_from_image(img)
print(f"FEN: {fen}")
```

## Training Tips

### Model Training Settings

```python
CONFIG = {
    'batch_size': 256,        # Reduce if OOM on GPU
    'learning_rate': 0.001,   # Default Adam LR
    'epochs': 50,             # Adjust based on dataset size
    'num_res_blocks': 10,     # More blocks = better but slower
    'num_channels': 256,      # Channel width
}
```

### Expected Performance

- **Training time**: ~2-4 hours on Colab T4 GPU (depends on dataset size)
- **Target accuracy**: 40-60% exact move match (good baseline)
- **From-square accuracy**: 60-80%
- **To-square accuracy**: 50-70%

### Dataset Size Recommendations

- **Minimum**: 100K positions
- **Recommended**: 1M+ positions
- **Ideal**: 10M+ positions

## Components Status

- ✅ Project structure
- ✅ Screenshot capture
- ✅ Vision API integration (Claude/OpenAI)
- ✅ Model architecture & training notebook
- ✅ Model inference engine
- ⏳ GUI overlay (pending)
- ⏳ Console output (pending)
- ⏳ Main real-time pipeline (pending)

## Next Steps

1. **Train your model** on Google Colab with your dataset
2. **Download chess_model.pth** and place in `models/`
3. **Test the model** with sample positions
4. **Implement GUI overlay** for displaying moves on screen
5. **Build main pipeline** to connect all components
6. **Test on live chess.com games**

## Technical Details

### FEN Notation

FEN (Forsyth-Edwards Notation) completely describes a chess position:

```
rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

- Piece placement (8 ranks, `/` separated)
- Active color (`w` or `b`)
- Castling rights (`KQkq`)
- En passant square
- Halfmove clock
- Fullmove number

### UCI Move Format

Universal Chess Interface format for moves:

- `e2e4` - Move from e2 to e4
- `e7e8q` - Pawn promotion to queen
- Coordinates: a1 (bottom-left) to h8 (top-right)

## Troubleshooting

**Model not found error:**
- Ensure `chess_model.pth` is in the `models/` directory
- Check the file path in your code

**Vision API errors:**
- Verify API keys in `.env` file
- Check API quota/limits

**CUDA out of memory:**
- Reduce batch size in training config
- Use fewer residual blocks
- Train on Colab instead of locally

## License

MIT

## Contributing

PRs welcome! Areas to improve:
- GUI overlay implementation
- Real-time pipeline optimization
- Support for other chess platforms (Lichess, etc.)
- Model architecture improvements
