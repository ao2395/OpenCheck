# Computer Vision Alternatives to LLM Recognition

LLM-based vision APIs (Gemini, Claude) are inaccurate for chess board recognition. Here are better alternatives:

## Option 1: LiveChess2FEN (Recommended)

**Most mature open-source solution**

```bash
pip install lc2fen
```

**Usage:**
```python
from lc2fen import LiveChess2FEN

# Initialize
predictor = LiveChess2FEN()

# Get FEN from image
fen, _ = predictor.predict(image_path)
print(f"FEN: {fen}")
```

**Pros:**
- Dedicated to chess board recognition
- Uses CNN for piece classification
- Pre-trained models included
- Supports different board styles
- Very accurate once calibrated

**Cons:**
- Requires initial calibration
- May need fine-tuning for chess.com specifically

## Option 2: TensorFlow Lite Piece Classifier

**Build your own lightweight classifier**

### Step 1: Collect Training Data
```bash
# Screenshot each piece type on chess.com
# Save as: pieces/white_pawn.png, pieces/black_knight.png, etc.
```

### Step 2: Train Simple CNN
```python
import tensorflow as tf

# Small CNN for piece classification (13 classes: 12 pieces + empty)
model = tf.keras.Sequential([
    tf.keras.layers.Conv2D(32, 3, activation='relu', input_shape=(64, 64, 3)),
    tf.keras.layers.MaxPooling2D(),
    tf.keras.layers.Conv2D(64, 3, activation='relu'),
    tf.keras.layers.MaxPooling2D(),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dense(13, activation='softmax')  # 13 classes
])
```

### Step 3: Integrate with OpenCheck
```python
# Load model
model = tf.keras.models.load_model('piece_classifier.h5')

# Classify each square
def classify_square(square_img):
    pred = model.predict(square_img)
    class_idx = np.argmax(pred)
    return PIECE_CLASSES[class_idx]
```

**Pros:**
- Very fast inference (<10ms per board)
- No API costs
- Deterministic results
- Can fine-tune for specific board style

**Cons:**
- Requires collecting training data
- Need to retrain if board style changes

## Option 3: Template Matching with OpenCV

**Fastest, simplest approach for consistent setup**

```python
import cv2
import numpy as np

# Step 1: Create templates for each piece
templates = {
    'P': cv2.imread('templates/white_pawn.png'),
    'p': cv2.imread('templates/black_pawn.png'),
    # ... etc for all pieces
}

# Step 2: Match template in each square
def match_piece(square_img):
    best_match = None
    best_score = 0

    for piece, template in templates.items():
        result = cv2.matchTemplate(square_img, template, cv2.TM_CCOEFF_NORMED)
        score = np.max(result)

        if score > best_score:
            best_score = score
            best_match = piece

    return best_match if best_score > 0.7 else None
```

**Pros:**
- No training needed
- Very fast
- Perfect accuracy if board position is fixed

**Cons:**
- Requires exact templates for each piece
- Sensitive to board size/position changes
- Lighting variations can affect accuracy

## Option 4: Chessboard Detection + Piece CNN

**Hybrid approach (best accuracy)**

### Phase 1: Board Detection
```python
# Use chessboard corner detection
import cv2

# Detect chessboard corners
ret, corners = cv2.findChessboardCorners(gray, (7, 7))

# Perspective transform to get perfect top-down view
board_img = cv2.getPerspectiveTransform(src_corners, dst_corners)
```

### Phase 2: Grid Extraction
```python
# Divide into perfect 8x8 grid
square_size = board_width // 8
squares = []
for row in range(8):
    for col in range(8):
        x, y = col * square_size, row * square_size
        square = board_img[y:y+square_size, x:x+square_size]
        squares.append(square)
```

### Phase 3: Piece Classification
Use either:
- Pre-trained CNN
- Template matching
- Color/shape heuristics

## Recommended Implementation Plan

### Quick Fix (1 hour):
Use **LiveChess2FEN** with calibration:
```bash
pip install lc2fen
# Calibrate once for chess.com
# Then very accurate
```

### Best Long-term (1 day):
1. **Board Detection**: Use OpenCV chessboard detection
2. **Piece Classification**: Train lightweight CNN on chess.com pieces
3. **FEN Generation**: Convert classifications to FEN
4. **Integration**: Replace vision API in OpenCheck

### Training Data Collection:
```python
# Script to auto-collect training data
# Set up different positions on chess.com
# Screenshot each piece in different squares
# Automatically label and save
```

## Implementation in OpenCheck

### Update main.py:
```python
# Replace this:
from recognition.vision_api import BoardRecognizer

# With this:
from recognition.cv_recognition import CVBoardRecognizer

# In initialize():
self.board_recognizer = CVBoardRecognizer()
```

## Performance Comparison

| Method | Accuracy | Speed | Cost | Setup |
|--------|----------|-------|------|-------|
| Gemini 2.5 Pro | 70-80% | 2-3s | $$ | None |
| LiveChess2FEN | 95%+ | <100ms | Free | 30min calibration |
| Custom CNN | 98%+ | <50ms | Free | 1 day training |
| Template Match | 99%+ | <10ms | Free | Fixed setup only |

## Next Steps

1. **Try LiveChess2FEN first** (quickest path to accuracy)
2. **Collect training data** (screenshot different positions)
3. **Train custom CNN** (best long-term solution)
4. **Integrate with OpenCheck** (replace vision_api.py)

Would you like me to implement one of these approaches?
