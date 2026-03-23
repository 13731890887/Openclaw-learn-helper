# OpenClaw Learn Helper

Agent-oriented study helper for macOS. The current MVP focuses on screenshot-first OCR for learning content, then turns the recognized text into lightweight study analysis.

## What This Repo Does

- Capture a screenshot interactively on macOS
- Downscale the image before OCR to control memory usage
- Run PaddleOCR on the captured image
- Classify the extracted text into a rough study shape
- Return a short study-oriented analysis
- Support a shortcut-driven workflow for repeated use

## Current MVP

Primary workflow:

1. Trigger a keyboard shortcut
2. Draw a screenshot region
3. Save a scaled image under `memory/snaps/`
4. Run OCR
5. Emit JSON + terminal-friendly analysis

Main entrypoint for the shortcut flow:

- `study-companion/scripts/run_snap_question.sh`

Main Python workflow:

- `study-companion/scripts/snap_question.py`

## Repository Layout

- `study-companion/SKILL.md`
  Agent usage guidance for the study companion workflow.
- `study-companion/scripts/screen_ocr.py`
  Realtime screen OCR loop.
- `study-companion/scripts/ocr_parse.py`
  OCR parsing and lightweight study analysis.
- `study-companion/scripts/snap_question.py`
  Interactive screenshot -> resize -> OCR -> analysis.
- `study-companion/scripts/run_snap_question.sh`
  Shell launcher intended for Shortcuts / hotkeys.
- `study-companion/scripts/snap_question_launcher.applescript`
  Local AppleScript launcher used for macOS integration.
- `study-companion/data/`
  Learner state, review queue, goals, and wrong-question storage.
- `study-companion/references/`
  Reference material for coaching style and study operations.
- `memory/`
  Local working notes and generated artifacts. Treat as runtime state, not source.

## Requirements

- macOS
- Python virtual environment at `.venv`
- `paddleocr`
- `paddlepaddle`
- `Pillow`
- `mss` optional, but supported by the realtime OCR path
- Screen Recording permission for the app or terminal that launches the workflow

## Recommended Usage

### Interactive screenshot flow

```bash
cd /Users/seqi/projects/Openclaw-learn-helper
bash study-companion/scripts/run_snap_question.sh
```

This opens interactive screenshot capture, scales the image, runs OCR, and prints analysis.

### Re-run from an existing image

```bash
cd /Users/seqi/projects/Openclaw-learn-helper
source .venv/bin/activate
python study-companion/scripts/snap_question.py --input /path/to/image.png
```

### Realtime OCR loop

```bash
cd /Users/seqi/projects/Openclaw-learn-helper
source .venv/bin/activate
python study-companion/scripts/screen_ocr.py --interval 1.0 --show-empty
```

## Memory Strategy

This repo intentionally resizes screenshots before OCR. Runtime image size matters more than PNG file size.

`snap_question.py` supports:

- `--memory-mode auto`
- `--memory-mode low`
- `--memory-mode balanced`
- `--memory-mode high`

Current default launcher uses `auto` and then applies a max image size cap.

Dynamic behavior:

- low memory available: shrink more aggressively
- medium memory available: balanced size
- high memory available: keep more detail

## Output Files

Generated screenshot runs write:

- `memory/snaps/*-scaled.png`
- `memory/snaps/*-analysis.json`

The JSON payload contains:

- image metadata
- OCR lines
- full recognized text
- structured text classification
- lightweight study analysis

## Agent Notes

If an agent is extending this repo, keep these constraints in mind:

- Optimize for study workflows, not generic OCR demos
- Prefer screenshot-first interaction over full-screen continuous capture
- Avoid pushing generated screenshots or OCR output unless explicitly asked
- Keep analysis hint-first and concise
- Make OCR uncertainty visible when confidence is weak
- Preserve local-first operation when possible

## Known Constraints

- Full-screen OCR is substantially heavier than region screenshot OCR
- OCR quality is good for large, clean text, but noisy layouts still need review
- Current analysis is heuristic, not model-based reasoning
- macOS shortcut integration works, but UI polish is still minimal

## Next Good Extensions

- Add visible progress UI during screenshot analysis
- Add richer question-type extraction
- Send OCR text to an LLM or OpenClaw skill/plugin for deeper reasoning
- Store selected items into wrong-question or review queues automatically
