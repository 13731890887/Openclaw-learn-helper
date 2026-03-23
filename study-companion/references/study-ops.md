# Study Ops

This MVP uses local JSON/JSONL files as the study memory layer.

## Files
- `data/profile.json`: learner preferences, favorite subjects, speaking pace, reminder times
- `data/goals.json`: active goals, exams, current focus
- `data/review_queue.json`: spaced repetition items
- `data/wrong_questions.jsonl`: mistakes worth revisiting

## Suggested cron usage
- Morning: 1-3 new items
- Afternoon: 1 quick recall question
- Evening: wrong-question replay or sleep lesson reminder

## Suggested agent behavior
- Reuse the learner's current goals before inventing new topics.
- Convert solved mistakes into review items.
- Keep push messages brief enough to finish in under one minute.
