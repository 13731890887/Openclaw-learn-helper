#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Real-time screen OCR using PaddleOCR")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds between captures")
    parser.add_argument("--lang", default="ch")
    parser.add_argument("--once", action="store_true", help="capture only once")
    parser.add_argument("--json", action="store_true", help="print JSON instead of plain text")
    parser.add_argument("--show-empty", action="store_true", help="emit output even when OCR text is empty")
    parser.add_argument("--min-confidence", type=float, default=0.60)
    parser.add_argument("--left", type=int)
    parser.add_argument("--top", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    return parser


def load_ocr(lang: str):
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle"
        ) from e
    try:
        return PaddleOCR(use_textline_orientation=True, lang=lang)
    except TypeError:
        return PaddleOCR(use_angle_cls=True, lang=lang)


def capture_image(region: dict[str, int] | None):
    try:
        import mss  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        mss = None
        Image = None

    if mss and Image:
        with mss.mss() as sct:
            monitor = region or sct.monitors[1]
            shot = sct.grab(monitor)
            return Image.frombytes("RGB", shot.size, shot.rgb)

    try:
        from PIL import ImageGrab  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Screen capture requires either `mss` + `Pillow` or Pillow ImageGrab support"
        ) from e

    bbox = None
    if region:
        bbox = (
            region["left"],
            region["top"],
            region["left"] + region["width"],
            region["top"] + region["height"],
        )
    return ImageGrab.grab(bbox=bbox)


def run_ocr(ocr, image, min_confidence: float) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        image.save(tmp_path)
        result = ocr.ocr(str(tmp_path), cls=True)
    finally:
        tmp_path.unlink(missing_ok=True)

    lines: list[dict[str, Any]] = []
    for page in result or []:
        for row in page or []:
            text = row[1][0].strip()
            confidence = float(row[1][1])
            if confidence < min_confidence:
                continue
            if not text:
                continue
            lines.append({"text": text, "confidence": confidence})

    full_text = "\n".join(item["text"] for item in lines)
    text_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    avg_conf = round(sum(i["confidence"] for i in lines) / len(lines), 4) if lines else None
    return {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "line_count": len(lines),
        "average_confidence": avg_conf,
        "text": full_text,
        "lines": lines,
        "hash": text_hash,
    }


def print_payload(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return
    ts = payload["captured_at"]
    print(f"[{ts}]", flush=True)
    print(payload["text"], flush=True)
    print("-" * 40, flush=True)


def main() -> int:
    args = build_parser().parse_args()
    region = None
    if all(value is not None for value in (args.left, args.top, args.width, args.height)):
        region = {
            "left": args.left,
            "top": args.top,
            "width": args.width,
            "height": args.height,
        }

    ocr = load_ocr(args.lang)
    last_hash = None

    while True:
        image = capture_image(region)
        payload = run_ocr(ocr, image, args.min_confidence)
        changed = payload["hash"] != last_hash
        has_text = bool(payload["text"].strip())

        if changed and (has_text or args.show_empty):
            print_payload(payload, args.json)
            last_hash = payload["hash"]

        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        raise SystemExit(130)
