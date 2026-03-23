#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

LOW_CONF_THRESHOLD = 0.85


def configure_paddle_env() -> None:
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


def load_ocr(lang: str):
    configure_paddle_env()
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as e:  # pragma: no cover - import guard
        raise RuntimeError(
            "PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle"
        ) from e

    try:
        return PaddleOCR(use_textline_orientation=True, lang=lang)
    except TypeError:
        return PaddleOCR(use_angle_cls=True, lang=lang)


def call_ocr(ocr, input_path: Path):
    try:
        return ocr.ocr(str(input_path), cls=True)
    except TypeError:
        return ocr.predict(str(input_path))


def extract_lines(result: Any) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []

    if isinstance(result, list):
        for page_index, page in enumerate(result):
            if isinstance(page, dict):
                rec_texts = page.get("rec_texts") or []
                rec_scores = page.get("rec_scores") or []
                for row_index, (text, conf) in enumerate(zip(rec_texts, rec_scores)):
                    lines.append(
                        {
                            "page": page_index,
                            "row": row_index,
                            "text": str(text).strip(),
                            "confidence": float(conf),
                        }
                    )
                continue

            if hasattr(page, "json"):
                try:
                    page = page.json
                except Exception:
                    pass

            for row_index, row in enumerate(page or []):
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                lines.append(
                    {
                        "page": page_index,
                        "row": row_index,
                        "text": str(row[1][0]).strip(),
                        "confidence": float(row[1][1]),
                    }
                )

    return lines


def run_ocr(input_path: Path, lang: str = "ch") -> dict[str, Any]:
    ocr = load_ocr(lang)
    result = call_ocr(ocr, input_path)
    lines = extract_lines(result)
    low_conf_lines = [item for item in lines if item["confidence"] < LOW_CONF_THRESHOLD]
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


def infer_subject(text: str) -> str:
    lowered = text.lower()
    if re.search(r"(函数|方程|几何|导数|积分|概率|三角形|圆|x=|y=|sin|cos|tan|\d+\s*[\+\-\*/=]\s*\d+)", text):
        return "math"
    if re.search(r"(英语|完形填空|阅读理解|grammar|choose the best answer|translation|阅读下列)", lowered):
        return "english"
    if re.search(r"(化学|物理|生物|实验|电流|速度|加速度|分子|元素)", text):
        return "science"
    if re.search(r"(历史|地理|政治|朝代|气候|经纬度|制度)", text):
        return "humanities"
    if re.search(r"(原则|作者|中心思想|文章|下列对|根据材料|阅读下面)", text):
        return "chinese"
    return "general"


def build_hint(structured: dict[str, Any], subject: str, text: str) -> str:
    kind = structured.get("kind")
    if kind == "multiple_choice":
        return "先读题干，再逐个排除选项，优先圈出题干里的限定词和转折词。"
    if kind == "fill_in_blank":
        return "先判断空格前后要填的是定义、结论还是关键词，再回到原文找对应句。"
    if kind == "worksheet":
        return "先拆分成小题，找出每一题分别在考什么，不要一次性全做。"
    if subject == "math":
        return "先列已知和所求，再找公式或等量关系，不要急着代数运算。"
    if subject == "english":
        return "先定位题干关键词，再回原文对应句，优先判断同义替换和转折。"
    if subject == "science":
        return "先写出概念和条件，再判断题目考的是现象解释、公式还是实验结论。"
    if subject == "chinese":
        return "先概括段落主旨，再看题目问的是中心思想、论证方式还是细节判断。"
    return "先用一句话复述题目在问什么，再决定需要公式、概念还是原文定位。"


def analyze_study_text(full_text: str, structured: dict[str, Any], low_conf_count: int = 0) -> dict[str, Any]:
    text = full_text.strip()
    if not text:
        return {
            "subject": "unknown",
            "question_type": "empty",
            "confidence_note": "未识别到文字，建议重截一张更清晰的图。",
            "summary": "没有可分析的题目文本。",
            "hint": "重新截图时尽量只保留题干和选项。",
            "next_action": "retake",
        }

    subject = infer_subject(text)
    question_type = str(structured.get("kind", "notes"))
    confidence_note = (
        f"有 {low_conf_count} 行低置信度文本，结论前需要人工复核。"
        if low_conf_count
        else "OCR 结果可直接用于初步分析。"
    )

    if question_type == "multiple_choice":
        question = str(structured.get("question", "")).strip() or text.splitlines()[0]
        summary = f"这是一道{subject}选择题，核心题干是：{question}"
        next_action = "排除法检查每个选项"
    elif question_type == "fill_in_blank":
        summary = "这是一道填空题，先判断空格所需信息类型，再回原文或公式定位。"
        next_action = "定位空格前后的线索词"
    elif question_type == "worksheet":
        item_count = len(structured.get("items", []))
        summary = f"这是一个包含 {item_count} 个小题的题组，适合逐题拆解。"
        next_action = "先做最短、信息最完整的小题"
    elif question_type == "notes":
        summary = "更像一段教材或笔记内容，不是标准题面。"
        next_action = "先提炼主题，再决定是否转成问答或测验"
    else:
        summary = "题目结构已提取，但类型还比较宽泛。"
        next_action = "先确认题目要求和限制条件"

    return {
        "subject": subject,
        "question_type": question_type,
        "confidence_note": confidence_note,
        "summary": summary,
        "hint": build_hint(structured, subject, text),
        "next_action": next_action,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR study materials and emit structured JSON")
    parser.add_argument("input", type=Path)
    parser.add_argument("--lang", default="ch")
    parser.add_argument("--out", type=Path, default=Path("ocr_result.json"))
    parser.add_argument("--analyze", action="store_true", help="include a lightweight study analysis block")
    args = parser.parse_args()

    data = run_ocr(args.input, args.lang)
    if args.analyze:
        data["analysis"] = analyze_study_text(
            data["full_text"],
            data["structured"],
            data["low_conf_count"],
        )
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
