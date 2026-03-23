#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def configure_paddle_env() -> None:
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


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
    parser.add_argument(
        "--capture-backend",
        choices=["auto", "mss", "imagegrab", "screencapture"],
        default="auto",
        help="screen capture backend",
    )
    parser.add_argument(
        "--save-capture",
        type=Path,
        help="optional path to save the captured frame for debugging",
    )
    return parser


def load_ocr(lang: str):
    configure_paddle_env()
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


def capture_with_mss(region: dict[str, int] | None):
    import mss  # type: ignore
    from PIL import Image  # type: ignore

    with mss.mss() as sct:
        monitors = getattr(sct, "monitors", [])
        if not (region or len(monitors) > 1):
            raise RuntimeError("mss did not report any usable monitors")
        monitor = region or monitors[1]
        shot = sct.grab(monitor)
        return Image.frombytes("RGB", shot.size, shot.rgb)


def capture_with_imagegrab(region: dict[str, int] | None):
    from PIL import ImageGrab  # type: ignore

    bbox = None
    if region:
        bbox = (
            region["left"],
            region["top"],
            region["left"] + region["width"],
            region["top"] + region["height"],
        )
    return ImageGrab.grab(bbox=bbox)


def capture_with_screencapture(region: dict[str, int] | None):
    from PIL import Image  # type: ignore

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    command = ["screencapture", "-x"]
    if region:
        rect = f"{region['left']},{region['top']},{region['width']},{region['height']}"
        command.extend(["-R", rect])
    command.append(str(tmp_path))

    try:
        subprocess.run(command, check=True, capture_output=True)
        return Image.open(tmp_path).copy()
    finally:
        tmp_path.unlink(missing_ok=True)


def capture_image(region: dict[str, int] | None, backend: str):
    try:
        import mss  # type: ignore
    except Exception:
        mss = None
    try:
        from PIL import ImageGrab  # type: ignore
    except Exception:
        ImageGrab = None

    methods: list[tuple[str, Any]] = []
    if backend == "auto":
        methods = [
            ("mss", capture_with_mss if mss else None),
            ("imagegrab", capture_with_imagegrab if ImageGrab else None),
            ("screencapture", capture_with_screencapture),
        ]
    elif backend == "mss":
        methods = [("mss", capture_with_mss if mss else None)]
    elif backend == "imagegrab":
        methods = [("imagegrab", capture_with_imagegrab if ImageGrab else None)]
    else:
        methods = [("screencapture", capture_with_screencapture)]

    errors: list[str] = []
    for name, method in methods:
        if method is None:
            errors.append(f"{name}: backend unavailable")
            continue
        try:
            return method(region)
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    raise RuntimeError("Screen capture failed: " + " | ".join(errors))


def call_ocr(ocr, image_path: Path):
    try:
        return ocr.ocr(str(image_path), cls=True)
    except TypeError:
        return ocr.predict(str(image_path))


def extract_lines(result: Any, min_confidence: float) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []

    if isinstance(result, list):
        for page in result:
            if isinstance(page, dict):
                rec_texts = page.get("rec_texts") or []
                rec_scores = page.get("rec_scores") or []
                for text, confidence in zip(rec_texts, rec_scores):
                    text = str(text).strip()
                    confidence = float(confidence)
                    if text and confidence >= min_confidence:
                        lines.append({"text": text, "confidence": confidence})
                continue

            if hasattr(page, "json"):
                try:
                    page = page.json
                except Exception:
                    pass

            for row in page or []:
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                text = str(row[1][0]).strip()
                confidence = float(row[1][1])
                if text and confidence >= min_confidence:
                    lines.append({"text": text, "confidence": confidence})

    return lines


def run_ocr(ocr, image, min_confidence: float) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        image.save(tmp_path)
        result = call_ocr(ocr, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    lines = extract_lines(result, min_confidence)
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
    region_args = (args.left, args.top, args.width, args.height)
    region = None
    if any(value is not None for value in region_args) and not all(value is not None for value in region_args):
        raise SystemExit("Region capture requires --left --top --width --height together")
    if all(value is not None for value in region_args):
        if args.width <= 0 or args.height <= 0:
            raise SystemExit("--width and --height must be positive integers")
        region = {
            "left": args.left,
            "top": args.top,
            "width": args.width,
            "height": args.height,
        }

    ocr = load_ocr(args.lang)
    last_hash = None

    while True:
        image = capture_image(region, args.capture_backend)
        if args.save_capture:
            args.save_capture.parent.mkdir(parents=True, exist_ok=True)
            image.save(args.save_capture)
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
