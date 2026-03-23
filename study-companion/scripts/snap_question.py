#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def load_ocr_parse_module():
    script_path = Path(__file__).with_name("ocr_parse.py")
    spec = importlib.util.spec_from_file_location("ocr_parse_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load OCR parser from {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture a screenshot, downscale it, OCR it, and analyze the study question"
    )
    parser.add_argument("--lang", default="ch")
    parser.add_argument("--max-width", type=int, default=1200)
    parser.add_argument("--max-height", type=int, default=1200)
    parser.add_argument("--min-confidence", type=float, default=0.60)
    parser.add_argument("--output-dir", type=Path, default=Path("memory/snaps"))
    parser.add_argument("--input", type=Path, help="reuse an existing image instead of interactive capture")
    parser.add_argument(
        "--memory-mode",
        choices=["auto", "low", "balanced", "high"],
        default="auto",
        help="auto adapts to free memory; low uses a smaller image; high keeps more detail",
    )
    parser.add_argument("--json", action="store_true", help="print the full JSON payload")
    parser.add_argument("--keep-original", action="store_true", help="keep the raw screenshot file")
    return parser


def capture_interactive(target_path: Path) -> bool:
    command = ["screencapture", "-i", "-x", str(target_path)]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        if "cancel" in stderr.lower():
            return False
        raise RuntimeError(stderr or "Interactive screenshot failed")
    return target_path.exists() and target_path.stat().st_size > 0


def downscale_image(input_path: Path, output_path: Path, max_width: int, max_height: int) -> dict[str, int]:
    from PIL import Image  # type: ignore

    with Image.open(input_path) as img:
        source_width, source_height = img.size
        resized = img.convert("RGB")
        resized.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resized.save(output_path, format="PNG", optimize=True)
        width, height = resized.size

    return {
        "source_width": source_width,
        "source_height": source_height,
        "width": width,
        "height": height,
    }


def resolve_size_limits(memory_mode: str, max_width: int, max_height: int) -> tuple[int, int]:
    presets = {
        "low": (960, 960),
        "balanced": (1200, 1200),
        "high": (1600, 1600),
    }
    preset_width, preset_height = presets[memory_mode]
    return min(max_width, preset_width), min(max_height, preset_height)


def detect_available_memory_gb() -> float | None:
    try:
        completed = subprocess.run(
            ["vm_stat"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    lines = completed.stdout.splitlines()
    page_size = 4096
    stats: dict[str, int] = {}
    for line in lines:
        if "page size of" in line:
            parts = line.split("page size of", 1)[1].split("bytes", 1)[0].strip()
            page_size = int(parts)
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            stats[key.strip()] = int(digits)

    available_pages = (
        stats.get("Pages free", 0)
        + stats.get("Pages inactive", 0)
        + stats.get("Pages speculative", 0)
        + stats.get("Pages purgeable", 0)
    )
    if available_pages <= 0:
        return None
    return available_pages * page_size / (1024 ** 3)


def resolve_dynamic_memory_mode(memory_mode: str) -> tuple[str, float | None]:
    if memory_mode != "auto":
        return memory_mode, None

    available_gb = detect_available_memory_gb()
    if available_gb is None:
        return "balanced", None
    if available_gb < 3.0:
        return "low", available_gb
    if available_gb < 6.0:
        return "balanced", available_gb
    return "high", available_gb


def print_plain(payload: dict) -> None:
    meta = payload["image"]
    print(f"[{payload['captured_at']}]")
    print(
        f"截图尺寸: {meta['source_width']}x{meta['source_height']} -> "
        f"{meta['width']}x{meta['height']}"
    )
    memory_line = f"内存模式: {meta['memory_mode']}"
    if meta.get("available_memory_gb") is not None:
        memory_line += f" | 可用内存约: {meta['available_memory_gb']:.2f} GB"
    print(memory_line)
    print(f"题型: {payload['analysis']['question_type']} | 学科: {payload['analysis']['subject']}")
    print(f"识别说明: {payload['analysis']['confidence_note']}")
    print("识别文本:")
    print(payload["ocr"]["full_text"] or "(空)")
    print("分析:")
    print(payload["analysis"]["summary"])
    print(f"提示: {payload['analysis']['hint']}")
    print(f"下一步: {payload['analysis']['next_action']}")


def main() -> int:
    args = build_parser().parse_args()
    if args.max_width <= 0 or args.max_height <= 0:
        raise SystemExit("--max-width and --max-height must be positive integers")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / f"{timestamp}-raw.png"
    scaled_path = output_dir / f"{timestamp}-scaled.png"
    json_path = output_dir / f"{timestamp}-analysis.json"

    if args.input:
        raw_path = args.input.resolve()
    else:
        if not capture_interactive(raw_path):
            print("Screenshot cancelled.", file=sys.stderr)
            return 130

    resolved_memory_mode, available_memory_gb = resolve_dynamic_memory_mode(args.memory_mode)
    max_width, max_height = resolve_size_limits(resolved_memory_mode, args.max_width, args.max_height)
    image_meta = downscale_image(raw_path, scaled_path, max_width, max_height)

    ocr_parse = load_ocr_parse_module()
    data = ocr_parse.run_ocr(scaled_path, args.lang)
    if args.min_confidence > 0:
        original_lines = list(data["lines"])
        lines = [line for line in original_lines if line["confidence"] >= args.min_confidence]
        low_conf_lines = [line for line in original_lines if line["confidence"] < args.min_confidence]
        data["lines"] = lines
        data["line_count"] = len(lines)
        data["low_conf_count"] = len(low_conf_lines)
        data["low_conf_lines"] = low_conf_lines
        data["full_text"] = "\n".join(line["text"] for line in lines if line["text"])
        data["average_confidence"] = round(
            sum(line["confidence"] for line in lines) / len(lines), 4
        ) if lines else None
        data["structured"] = ocr_parse.classify_text(data["full_text"])

    analysis = ocr_parse.analyze_study_text(
        data["full_text"],
        data["structured"],
        data["low_conf_count"],
    )
    payload = {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "image": {
            "raw_path": str(raw_path),
            "scaled_path": str(scaled_path),
            "memory_mode": resolved_memory_mode,
            "requested_memory_mode": args.memory_mode,
            "available_memory_gb": available_memory_gb,
            **image_meta,
        },
        "ocr": data,
        "analysis": analysis,
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.input and not args.keep_original:
        raw_path.unlink(missing_ok=True)
        payload["image"]["raw_path"] = None

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_plain(payload)
        print(f"JSON: {json_path}")
        print(f"缩放图: {scaled_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        raise SystemExit(130)
