#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

LOW_CONF_THRESHOLD = 0.85


def run_ocr(input_path: Path, lang: str = "ch") -> dict[str, Any]:
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as e:  # pragma: no cover - import guard
        raise RuntimeError(
            "PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle"
        ) from e

    ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    result = ocr.ocr(str(input_path), cls=True)

    lines: list[dict[str, Any]] = []
    low_conf_lines: list[dict[str, Any]] = []

    for page_index, page in enumerate(result or []):
        for row_index, row in enumerate(page or []):
            text = row[1][0].strip()
            conf = float(row[1][1])
            item = {
                "page": page_index,
                "row": row_index,
                "text": text,
                "confidence": conf,
            }
            lines.append(item)
            if conf < LOW_CONF_THRESHOLD:
                low_conf_lines.append(item)

    full_text = "\n".join(item["text"] for item in lines if item["text"])
    structured = classify_text(full_text)

    return {
        "file": str(input_path),
        "line_count": len(lines),
        "low_conf_count": len(low_conf_lines),
        "average_confidence": round(
            sum(item["confidence"] for item in lines) / len(lines), 4
        ) if lines else None,
        "lines": lines,
        "low_conf_lines": low_conf_lines,
        "full_text": full_text,
        "structured": structured,
    }


def classify_text(full_text: str) -> dict[str, Any]:
    text = full_text.strip()
    if not text:
        return {"kind": "empty"}

    option_matches = re.findall(r"(?:^|\n)\s*([A-DＡ-Ｄ])[\.．、\s]+(.+)", text)
    if option_matches:
        question_text = re.split(r"(?:^|\n)\s*[A-DＡ-Ｄ][\.．、\s]+", text, maxsplit=1)[0].strip()
        return {
            "kind": "multiple_choice",
            "question": question_text,
            "options": [
                {"label": label, "text": option.strip()}
                for label, option in option_matches
            ],
        }

    numbered_lines = re.findall(r"(?:^|\n)\s*\d+[\)\.、]\s+(.+)", text)
    if len(numbered_lines) >= 2:
        return {
            "kind": "worksheet",
            "items": numbered_lines,
        }

    if "填空" in text or "____" in text or "_____" in text:
        return {"kind": "fill_in_blank", "question": text}

    return {"kind": "notes", "content": text}


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR study materials and emit structured JSON")
    parser.add_argument("input", type=Path)
    parser.add_argument("--lang", default="ch")
    parser.add_argument("--out", type=Path, default=Path("ocr_result.json"))
    args = parser.parse_args()

    data = run_ocr(args.input, args.lang)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
