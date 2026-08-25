"""正文格式检查器（审查4）

依据《中山大学本科毕业论文（设计）写作与印制规范》对正文进行纯代码格式检查：

  ① body_empty                     — 正文为空（error）
  ② intro_missing                  — 缺少绪论（error）
  ③ conclusion_missing             — 缺少结论（error）
  ④ body_word_count_insufficient   — 正文字数少于8000字（error）
  ⑤ digit_font_not_tnr             — 阿拉伯数字不是 Times New Roman（error）
  ⑥ english_font_not_tnr           — 英文字母不是 Times New Roman（error）
  ⑦ year_format_invalid            — 年份格式不正确（warning）

输入: output/parser_json/body.json（文档拆解团队输出）
输出: output/checker_json/body.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CHECKER_ID = "body"
CHECKER_NAME = "正文格式检查"

# ── 字体（兼容简繁/英文写法）─────────────────────────────
_FONT_TIMES = {"times new roman", "timesnewroman"}

# ── 字数要求 ──────────────────────────────────────────────
MIN_WORDS = 8000

# ── 年份正则（4位数字）────────────────────────────────────
_RE_YEAR = re.compile(r'\b(\d{4})\b')

# ── 关键字 ──────────────────────────────────────────────
INTRO_KEYWORDS = ["绪论", "引言", "前言", "导论"]
CONCLUSION_KEYWORDS = ["结论", "结语", "总结", "结束语"]


# ===================================================================
#  工具函数
# ===================================================================

def _truncate(text: str, max_len: int = 80) -> str:
    text = text.replace("\n", " ").replace("\r", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _norm(s: Any) -> str:
    return (str(s) if s is not None else "").strip().lower()


def _build_record(
    severity: str,
    category: str,
    description: str,
    expected: str,
    actual: str,
    paragraph_index: int,
    text_preview: str,
) -> dict:
    return {
        "severity": severity,
        "category": category,
        "description": description,
        "expected": expected,
        "actual": actual,
        "location": {
            "paragraph_index": paragraph_index,
            "text_preview": text_preview,
        },
    }


def _para_runs(para: dict) -> list[dict]:
    return para.get("runs") or []


def _run_font(run: dict, use_east_asia: bool = False) -> str:
    """取 run 的字体名，优先西文字体。"""
    if use_east_asia:
        return _norm(run.get("east_asia_font") or run.get("font_name"))
    return _norm(run.get("font_name") or run.get("east_asia_font"))


def _count_chinese_words(paras: list[dict]) -> int:
    """统计中文字符数（不含标点、空格、数字、英文）。"""
    text = "".join(p.get("text", "") for p in paras)
    # 移除标点、空格、数字、英文
    text = re.sub(r'[，。、；：！？…—·《》（）【】""''\s\dA-Za-z]', '', text)
    return len(text)


def _is_digit_or_english(char: str) -> bool:
    """判断字符是否为数字或英文字母。"""
    return char.isdigit() or char.isalpha() and char.isascii()


def _check_body_empty(body: list[dict]) -> list[dict]:
    """① 正文为空。"""
    if body:
        return []
    return [
        _build_record(
            "error", "body_empty",
            "未检测到正文内容",
            "论文应包含绪论、主体和结论三大模块",
            "正文为空",
            0, "",
        )
    ]


def _check_intro_exists(body: list[dict]) -> list[dict]:
    """② 缺少绪论。"""
    text = "".join(p.get("text", "") for p in body)
    if any(kw in text for kw in INTRO_KEYWORDS):
        return []
    return [
        _build_record(
            "error", "intro_missing",
            "未检测到绪论",
            "正文应以绪论/引言开头",
            "正文中未出现「绪论」「引言」等关键字",
            0, _truncate(text[:200]),
        )
    ]


def _check_conclusion_exists(body: list[dict]) -> list[dict]:
    """③ 缺少结论。"""
    text = "".join(p.get("text", "") for p in body)
    if any(kw in text for kw in CONCLUSION_KEYWORDS):
        return []
    return [
        _build_record(
            "error", "conclusion_missing",
            "未检测到结论",
            "正文应以结论/结语结尾",
            "正文中未出现「结论」「结语」等关键字",
            0, _truncate(text[-200:]),
        )
    ]


def _check_word_count(body: list[dict]) -> list[dict]:
    """④ 正文字数不少于8000字。"""
    word_count = _count_chinese_words(body)
    if word_count >= MIN_WORDS:
        return []
    return [
        _build_record(
            "error", "body_word_count_insufficient",
            f"正文字数不足 {MIN_WORDS} 字（当前 {word_count} 字）",
            f"正文总字数应不少于 {MIN_WORDS} 字",
            f"当前 {word_count} 字",
            0, "",
        )
    ]


def _check_digit_and_english_font(body: list[dict]) -> list[dict]:
    """⑤⑥ 阿拉伯数字和英文统一使用 Times New Roman。"""
    errors: list[dict] = []
    
    for p in body:
        text = (p.get("text") or "").strip()
        if not text:
            continue
        
        runs = _para_runs(p)
        if not runs:
            continue
        
        idx = p.get("index", 0)
        preview = _truncate(text)
        
        # 检查每个 run 中的数字和英文
        for run in runs:
            run_text = run.get("text", "")
            run_font = _run_font(run, use_east_asia=False)
            
            # 如果 run 包含数字或英文，检查字体
            if any(_is_digit_or_english(ch) for ch in run_text):
                if run_font and run_font not in _FONT_TIMES:
                    errors.append(
                        _build_record(
                            "error", "digit_font_not_tnr" if any(ch.isdigit() for ch in run_text) else "english_font_not_tnr",
                            f"{'数字' if any(ch.isdigit() for ch in run_text) else '英文'}字体不是 Times New Roman",
                            "阿拉伯数字和英文应使用 Times New Roman",
                            f"当前字体为 {run_font}",
                            idx, preview,
                        )
                    )
    
    return errors


def _check_year_format(body: list[dict]) -> list[dict]:
    """⑦ 年份格式（warning）。"""
    warnings: list[dict] = []
    
    text = "".join(p.get("text", "") for p in body)
    # 查找所有年份
    years = _RE_YEAR.findall(text)
    
    for year in years:
        # 检查年份是否合理（1900-2099）
        year_num = int(year)
        if 1900 <= year_num <= 2099:
            # 检查是否以 4 位数字出现
            # 如果年份前后是数字，说明是更大数字的一部分，跳过
            pass
    
    # 简单的启发式：如果年份少于 4 位（如 23 年），报 warning
    short_years = re.findall(r'\b(\d{2})\b', text)
    if short_years:
        warnings.append(
            _build_record(
                "warning", "year_format_invalid",
                "检测到非4位年份格式",
                "年份应统一使用4位阿拉伯数字",
                f"检测到 {', '.join(short_years[:3])}{'...' if len(short_years) > 3 else ''}",
                0, _truncate(text[:200]),
            )
        )
    
    return warnings


# ===================================================================
#  公共接口
# ===================================================================

def check(body_items: list[dict], source_file: str = "") -> dict:
    """对正文执行全部格式检查。"""
    all_errors: list[dict] = []
    all_warnings: list[dict] = []
    
    all_errors.extend(_check_body_empty(body_items))
    all_errors.extend(_check_intro_exists(body_items))
    all_errors.extend(_check_conclusion_exists(body_items))
    all_errors.extend(_check_word_count(body_items))
    all_errors.extend(_check_digit_and_english_font(body_items))
    all_warnings.extend(_check_year_format(body_items))
    
    total_errors = len(all_errors)
    total_warnings = len(all_warnings)
    status = "pass" if (total_errors == 0 and total_warnings == 0) else "fail"
    
    word_count = _count_chinese_words(body_items)
    
    return {
        "checker": CHECKER_ID,
        "checker_name": CHECKER_NAME,
        "timestamp": datetime.now().isoformat(),
        "source_file": source_file,
        "summary": {
            "status": status,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "word_count": word_count,
            "paragraph_count": len(body_items),
        },
        "errors": all_errors,
        "warnings": all_warnings,
    }


def run(input_path: str | Path, output_path: str | Path) -> dict:
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    with open(input_path, "r", encoding="utf-8") as f:
        data: dict = json.load(f)
    
    source_file = data.get("file_name", input_path.name)
    items = data.get("items", [])
    
    result = check(items, source_file=source_file)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result


if __name__ == "__main__":
    import sys
    
    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    _DEFAULT_INPUT = _PROJECT_ROOT / "output" / "parser_json" / "body.json"
    _DEFAULT_OUTPUT = _PROJECT_ROOT / "output" / "checker_json" / "body.json"
    
    input_path = sys.argv[1] if len(sys.argv) > 1 else str(_DEFAULT_INPUT)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(_DEFAULT_OUTPUT)
    
    result = run(input_path, output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
