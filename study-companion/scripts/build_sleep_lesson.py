#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def make_chunk(title: str, core: str, detail: str, repeat: str | None = None) -> dict[str, str]:
    repeat_line = repeat or core
    script = (
        f"{title}\n"
        f"先记一句：{core}\n"
        f"慢慢听：{detail}\n"
        f"再记一次：{repeat_line}\n"
        f"停两秒，自己在心里重复一遍。"
    )
    return {
        "title": title,
        "core": core,
        "detail": detail,
        "repeat": repeat_line,
        "script": script,
    }


def build_vocab_lesson(items: list[dict[str, str]], topic: str, duration_min: int) -> dict[str, Any]:
    chunks = []
    for item in items:
        word = item.get("word", "")
        meaning = item.get("meaning", "")
        example = item.get("example", "")
        detail = f"{word}，意思是，{meaning}。例句：{example}" if example else f"{word}，意思是，{meaning}。"
        chunks.append(make_chunk(word, f"{word}，{meaning}", detail))

    intro = f"现在开始{topic}。节奏会慢一点。不要着急，只要跟着听。"
    outro = f"今天先到这里。预计时长大约 {duration_min} 分钟。睡前只记住最重要的词义就够了。"

    return {
        "mode": "vocabulary",
        "topic": topic,
        "duration_min": duration_min,
        "intro": intro,
        "chunks": chunks,
        "outro": outro,
        "full_script": "\n\n".join([intro] + [chunk["script"] for chunk in chunks] + [outro]),
    }


def build_knowledge_lesson(items: list[dict[str, str]], topic: str, duration_min: int) -> dict[str, Any]:
    chunks = []
    for index, item in enumerate(items, start=1):
        title = item.get("title", f"知识点 {index}")
        core = item.get("core", "")
        detail = item.get("detail", core)
        repeat = item.get("repeat", core)
        chunks.append(make_chunk(title, core, detail, repeat))

    intro = f"现在开始{topic}的睡前复习。每次只听一个重点。"
    outro = "结束前，回想一下今晚最重要的三个关键词。想不起来也没关系，重复本身就是学习。"

    return {
        "mode": "knowledge",
        "topic": topic,
        "duration_min": duration_min,
        "intro": intro,
        "chunks": chunks,
        "outro": outro,
        "full_script": "\n\n".join([intro] + [chunk["script"] for chunk in chunks] + [outro]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a sleep-friendly lesson script from JSON input")
    parser.add_argument("input", type=Path, help="JSON file describing vocab or knowledge items")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--mode", choices=["vocabulary", "knowledge"], default="vocabulary")
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("sleep_lesson.json"))
    args = parser.parse_args()

    items = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(items, list):
        raise SystemExit("Input JSON must be a list")

    if args.mode == "vocabulary":
        data = build_vocab_lesson(items, args.topic, args.duration)
    else:
        data = build_knowledge_lesson(items, args.topic, args.duration)

    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
