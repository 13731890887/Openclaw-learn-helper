---
name: study-companion
description: Companion learning assistant for OpenClaw that supports study coaching, OCR-based question parsing, sleep-friendly lesson playback, and daily learning nudges. Use when the user wants to study through text or voice, sends screenshots/PDFs of exercises for PaddleOCR extraction, asks for step-by-step hints while solving problems, wants bedtime vocabulary/knowledge review, or wants scheduled micro-learning and spaced-repetition reminders.
---

# Study Companion

Deliver a study-first workflow. Optimize for guidance, retention, and habit formation rather than dumping answers.

## Core Modes

### 1. Problem-solving coach
Use when the user is actively solving exercises.

Workflow:
1. Identify subject, question type, and desired help level.
2. If the prompt is an image/PDF, run `scripts/ocr_parse.py` first.
3. Show the cleaned question text back to the user when OCR confidence is mixed.
4. Default to hint-first coaching:
   - clarify what the question asks
   - identify the tested concept
   - propose the first step
   - wait before revealing the full solution unless the user asks
5. Escalate through three support levels:
   - level 1: hints only
   - level 2: guided steps
   - level 3: full worked solution + pitfalls
6. End with a short recap and whether to save the item as a weak point.

### 2. OCR study material parsing
Use when the user sends screenshots, scans, worksheets, textbook photos, or PDFs.

Workflow:
1. Run `scripts/ocr_parse.py` on the file.
2. Inspect `low_conf_lines` and warn when confidence is weak.
3. If the text looks like an exercise, convert it into structured question JSON.
4. If the text looks like notes/material, convert it into bullet-point study content.
5. Ask the user to confirm unclear segments before high-stakes explanations.

### 3. Sleep / bedtime learning
Use when the user wants low-stimulation audio learning.

Workflow:
1. Collect topic, audience level, duration, and desired tone.
2. Run `scripts/build_sleep_lesson.py` to create a TTS-friendly script.
3. Keep sections short, repetitive, and calm.
4. Prefer one idea per chunk.
5. Repeat the core takeaway at least twice for memory-heavy content.
6. If the user wants audio, feed the generated script into TTS.

### 4. Daily push + spaced repetition
Use when the user wants proactive study prompts.

Workflow:
1. Keep a learner profile and review queue under `study-companion/data/`.
2. Run `scripts/review_scheduler.py` to add or update items.
3. Use cron for exact-time reminders or pushes.
4. Keep pushes small:
   - 1-3 vocabulary items
   - 1 key concept
   - 1 mini quiz
   - 1 wrong-question review
5. Prefer continuity: reuse recent mistakes and recent lesson topics.

## Coaching Rules

- Default to teaching, not answer-spoiling.
- For exam-like tasks, ask whether the user wants hints or the full solution.
- Make uncertainty visible. Do not hide OCR errors or weak source quality.
- Use concise explanations first, then expand if the user asks.
- For bedtime content, reduce density and intensity.
- Always end with the next useful action: continue, quiz, review later, or save.

## Data Layout

Use these files for the MVP state model:

- `data/profile.json` - learner preferences, subjects, routine
- `data/goals.json` - current study goals and exams
- `data/review_queue.json` - spaced-repetition items
- `data/wrong_questions.jsonl` - mistakes and weak spots
- `data/session_notes/` - optional per-session learning notes

## Resources

### scripts/
- `ocr_parse.py` - PaddleOCR extraction with low-confidence reporting
- `screen_ocr.py` - live screen capture + OCR loop for on-screen questions
- `build_sleep_lesson.py` - generate calm, repetition-friendly lesson scripts
- `review_scheduler.py` - simple spaced-repetition queue manager

### references/
- `coaching-patterns.md` - hint-first tutoring patterns
- `sleep-script-patterns.md` - bedtime lesson writing rules
- `study-ops.md` - how to use the local data files and cron together
y` - PaddleOCR extraction with low-confidence reporting
- `build_sleep_lesson.py` - generate calm, repetition-friendly lesson scripts
- `review_scheduler.py` - simple spaced-repetition queue manager

### references/
- `coaching-patterns.md` - hint-first tutoring patterns
- `sleep-script-patterns.md` - bedtime lesson writing rules
- `study-ops.md` - how to use the local data files and cron together
