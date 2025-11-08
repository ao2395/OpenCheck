# Vision API Troubleshooting

## Problem: Inaccurate Board Recognition

If you're getting illegal moves or wrong positions, the vision API is misreading the board.

**Current Model**: Gemini 1.5 Pro (now default - more accurate than Flash)

### Solution 1: Improve Gemini Pro Accuracy

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

### Solution 2: Switch to Claude Vision (Most Accurate)

If Gemini Pro still has issues, Claude Vision is the most accurate option.

**Steps:**

1. Get an Anthropic API key from https://console.anthropic.com/
2. Add to `.env`: `ANTHROPIC_API_KEY=your_key_here`
3. Run: `python src/main.py --vision-api claude --vision-attempts 3`

Note: Claude Vision is more expensive than Gemini.

### Comparison: Vision APIs

| API | Accuracy | Speed | Cost | Current |
|-----|----------|-------|------|---------|
| **Gemini 1.5 Pro** | ⭐⭐⭐⭐ | Medium | Low | ✓ Default |
| Claude Vision | ⭐⭐⭐⭐⭐ | Fast | Medium | |
| Gemini 2.0 Flash | ⭐⭐⭐ | Very Fast | Very Low | |
| GPT-4 Vision | ⭐⭐⭐⭐ | Medium | High | |

### Debug Mode

Run with full debugging (using default Gemini Pro):
```bash
python src/main.py \
  --vision-attempts 3 \
  --save-screenshots \
  --verbose
```

This will:
- Use Gemini 1.5 Pro (default)
- Try 3 times per capture (uses most common result)
- Save each screenshot for manual inspection
- Show detailed logs including FEN and legal moves

For maximum accuracy (but higher cost):
```bash
python src/main.py --vision-api claude --vision-attempts 3 --save-screenshots
```

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
