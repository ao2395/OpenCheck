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
│   ├── main.py                    # Main application entry point
│   ├── capture/
│   │   └── screenshot.py          # Real-time screen capture
│   ├── recognition/
│   │   └── vision_api.py          # Claude/OpenAI Vision API for FEN extraction
│   ├── engine/
│   │   └── model.py               # Custom move prediction model inference
│   └── ui/
│       ├── overlay.py             # GUI overlay
│       └── console.py             # Console output
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
# Google Gemini (Recommended - Fast & Free tier available)
GOOGLE_API_KEY=your_google_api_key_here

# OR use Claude
ANTHROPIC_API_KEY=your_anthropic_key_here

# OR use OpenAI
OPENAI_API_KEY=your_openai_key_here
```

**Get API Keys:**
- **Gemini** (Recommended): https://makersuite.google.com/app/apikey - Free tier available!
- **Claude**: https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/

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

### Running OpenCheck

Once you've trained your model and placed `chess_model.pth` in the `models/` directory:

```bash
# Run with default settings
python src/main.py

# Custom options
python src/main.py --interval 3.0 --vision-api claude

# Disable overlay (console only)
python src/main.py --no-overlay

# Use specific model file
python src/main.py --model path/to/your/model.pth

# Use different vision API
python src/main.py --vision-api gemini  # Default
python src/main.py --vision-api claude
python src/main.py --vision-api openai
```

#### Command-Line Options

```
--model PATH          Path to trained model (default: models/chess_model.pth)
--interval SECONDS    Capture interval in seconds (default: 2.0)
--no-overlay         Disable GUI overlay
--no-console         Disable console output
--vision-api API     Vision API: 'gemini', 'claude', or 'openai' (default: gemini)
--monitor NUM        Monitor number to capture (default: 1)
```

#### Using the Overlay

- **F9**: Toggle overlay visibility
- **Drag**: Click and drag the title bar to reposition
- **X Button**: Hide overlay
- **Always on Top**: Overlay stays above all windows

The overlay displays:
- Best move in UCI format (e.g., "e2e4")
- Standard chess notation (e.g., "e4" or "Nf3")
- Move visualization (from → to)
- Model confidence percentage

#### Console Output

Real-time analysis is printed to console with:
- Colored output for better readability
- Move details in UCI and SAN notation
- ASCII chess board visualization
- Timestamps and status messages

### Testing Components

#### Test Model Inference

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
- ✅ GUI overlay
- ✅ Console output
- ✅ Main real-time pipeline
- ⏳ Board position detection (uses full screen - could be optimized)

## Next Steps

1. **Train your model** on Google Colab with your dataset
   - Decompress your `.zst` file: `zstd -d your_dataset.json.zst`
   - Upload notebook and dataset to Colab
   - Update `dataset_path` in config
   - Run all cells and wait for training to complete
2. **Download chess_model.pth** and place in `models/` directory
3. **Set up API keys** in `.env` file (Claude or OpenAI)
4. **Run the application**: `python src/main.py`
5. **Open chess.com** and start a game
6. **Watch the magic happen!** The overlay will show suggested moves

## How It Works (Step-by-Step)

1. **Every 2 seconds** (configurable), OpenCheck captures your screen
2. **Vision API** (Gemini, Claude, or GPT-4) analyzes the image and extracts the board position as FEN
3. **Your trained model** predicts the best move based on the position
4. **GUI overlay** displays the move suggestion on top of your browser
5. **Console** shows detailed analysis with board visualization

## Vision API Comparison

| API | Speed | Cost | Quality | Free Tier |
|-----|-------|------|---------|-----------|
| **Gemini 1.5 Flash** | ⚡ Fastest | 💰 Cheapest | ✓ Excellent | ✓ Yes (60 RPM) |
| Claude Sonnet | 🔸 Fast | 💰💰 Moderate | ✓ Excellent | Limited |
| GPT-4 Vision | 🔸 Moderate | 💰💰💰 Expensive | ✓ Excellent | ✗ No |

**Recommendation**: Use Gemini for best speed/cost ratio!

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
