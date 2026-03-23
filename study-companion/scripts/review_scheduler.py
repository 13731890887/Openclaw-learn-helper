#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc
DEFAULT_INTERVALS = [0, 1, 3, 7, 14]


@dataclass
class ReviewItem:
    item_id: str
    prompt: str
    answer: str
    source: str
    kind: str = "fact"
    status: str = "new"
    streak: int = 0
    interval_days: int = 0
    due_at: str = ""
    last_result: str | None = None
    notes: str = ""



def utc_now() -> datetime:
    return datetime.now(UTC)



def load_queue(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8-sig"))



def save_queue(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")



def add_item(path: Path, item: ReviewItem) -> None:
    queue = load_queue(path)
    if not item.due_at:
        item.due_at = utc_now().isoformat()
    queue.append(asdict(item))
    save_queue(path, queue)



def review_item(path: Path, item_id: str, result: str) -> dict[str, Any]:
    queue = load_queue(path)
    for item in queue:
        if item.get("item_id") != item_id:
            continue

        streak = int(item.get("streak", 0))
        if result == "again":
            streak = 0
            interval = DEFAULT_INTERVALS[1]
            status = "relearning"
        else:
            streak += 1
            interval = DEFAULT_INTERVALS[min(streak, len(DEFAULT_INTERVALS) - 1)]
            status = "review"

        due_at = (utc_now() + timedelta(days=interval)).isoformat()
        item.update(
            {
                "streak": streak,
                "interval_days": interval,
                "status": status,
                "due_at": due_at,
                "last_result": result,
            }
        )
        save_queue(path, queue)
        return item

    raise SystemExit(f"Item not found: {item_id}")



def due_items(path: Path, limit: int) -> list[dict[str, Any]]:
    queue = load_queue(path)
    now = utc_now()
    due = []
    for item in queue:
        due_at = item.get("due_at")
        if not due_at:
            due.append(item)
            continue
        if datetime.fromisoformat(due_at) <= now:
            due.append(item)
    due.sort(key=lambda item: item.get("due_at", ""))
    return due[:limit]



def main() -> None:
    parser = argparse.ArgumentParser(description="Manage a simple spaced-repetition review queue")
    parser.add_argument("command", choices=["add", "review", "due"])
    parser.add_argument("--queue", type=Path, default=Path("review_queue.json"))
    parser.add_argument("--item-id")
    parser.add_argument("--prompt")
    parser.add_argument("--answer")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--kind", default="fact")
    parser.add_argument("--notes", default="")
    parser.add_argument("--result", choices=["hard", "good", "easy", "again"])
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.command == "add":
        if not (args.item_id and args.prompt and args.answer):
            raise SystemExit("add requires --item-id --prompt --answer")
        item = ReviewItem(
            item_id=args.item_id,
            prompt=args.prompt,
            answer=args.answer,
            source=args.source,
            kind=args.kind,
            notes=args.notes,
        )
        add_item(args.queue, item)
        print(json.dumps({"status": "ok", "action": "add", "item_id": args.item_id}, ensure_ascii=False))
        return

    if args.command == "review":
        if not (args.item_id and args.result):
            raise SystemExit("review requires --item-id --result")
        updated = review_item(args.queue, args.item_id, args.result)
        print(json.dumps(updated, ensure_ascii=False, indent=2))
        return

    print(json.dumps(due_items(args.queue, args.limit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
