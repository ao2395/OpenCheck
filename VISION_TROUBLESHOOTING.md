# Vision API Troubleshooting

## Problem: Inaccurate Board Recognition

If you're getting illegal moves or wrong positions, the vision API is misreading the board.

### Solution 1: Switch to Claude Vision (Recommended)

Claude Vision is generally more accurate for chess positions than Gemini.

**Steps:**

1. Get an Anthropic API key from https://console.anthropic.com/

2. Add to your `.env` file:
```bash
ANTHROPIC_API_KEY=your_key_here
```

3. Run with Claude Vision:
```bash
python src/main.py --vision-api claude --vision-attempts 3
```

### Solution 2: Improve Gemini Accuracy

**Try image preprocessing (now enabled by default):**
```bash
python src/main.py --vision-attempts 3 --save-screenshots
```

**Improve board visibility:**
- Make chess.com fullscreen
- Use high-contrast board theme (e.g., green/white)
- Ensure good lighting
- Center the board on screen
- Remove overlays/move highlights

**Check saved screenshots:**
The `--save-screenshots` flag saves each capture. Verify:
- Board is clearly visible
- Pieces are sharp and distinct
- No UI elements overlapping the board

### Solution 3: Manual Cropping

If full-screen capture includes too much noise:

1. Find your board coordinates using a screenshot tool
2. Edit `src/capture/screenshot.py` to crop to just the board
3. Example: only capture pixels [100:900, 100:900]

### Comparison: Vision APIs

| API | Accuracy | Speed | Cost |
|-----|----------|-------|------|
| Claude Vision | ⭐⭐⭐⭐⭐ | Fast | Medium |
| Gemini Flash | ⭐⭐⭐ | Very Fast | Low |
| GPT-4 Vision | ⭐⭐⭐⭐ | Medium | High |

### Debug Mode

Run with full debugging:
```bash
python src/main.py \
  --vision-api claude \
  --vision-attempts 3 \
  --save-screenshots \
  --verbose
```

This will:
- Use Claude Vision (most accurate)
- Try 3 times per capture
- Save each screenshot
- Show detailed logs

### Still Not Working?

If board recognition is still inaccurate:

1. **Test standalone:**
   ```bash
   python src/recognition/vision_api.py path/to/board_screenshot.png
   ```

2. **Check the FEN manually:**
   - Compare console output to actual board
   - Note which squares are misread
   - Adjust board theme/size accordingly

3. **Consider traditional CV:**
   - For consistent board position, a classical computer vision approach might work better
   - Libraries like `chess-board-detection` use template matching
   - More setup but deterministic results
