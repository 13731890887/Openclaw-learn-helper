# Screen OCR

Use `scripts/screen_ocr.py` for live study scenarios where the learner has a question visible on screen.

## What it does
- Captures the whole screen or a selected region.
- Runs PaddleOCR repeatedly.
- Prints only when recognized text changes.
- Filters out very low-confidence lines.

## Typical usage

Whole screen, real-time:

```bash
python scripts/screen_ocr.py --interval 1.0
```

Single capture:

```bash
python scripts/screen_ocr.py --once
```

Specific question area:

```bash
python scripts/screen_ocr.py --left 100 --top 200 --width 900 --height 600
```

JSON output for piping into another tool:

```bash
python scripts/screen_ocr.py --json
```

## Notes
- Prefer selecting a smaller region around the exercise for better speed and accuracy.
- If the screen contains formulas or dense UI, consider lowering capture frequency.
- Requires PaddleOCR. For screen capture, prefer installing `mss` and `Pillow`.
