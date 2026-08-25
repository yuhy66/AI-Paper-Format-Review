"""章节标题格式检查器（审查2）

依据《中山大学本科毕业论文（设计）写作与印制规范》对章节标题进行纯代码格式检查：

  ① heading_system_inconsistent    — 两类编号体系混用（error）
  ② heading_level_exceeds_five     — 标题层级超过五级（error）
  ③ heading_trailing_punctuation   — 标题末尾有标点符号（error）
  ④ chapter_title_font             — 章标题字体不是黑体（error）
  ⑤ chapter_title_size             — 章标题字号不是三号（error）
  ⑥ chapter_title_align            — 章标题未居中（error）
  ⑦ section_title_font             — 节标题字体不是黑体（error）
  ⑧ section_title_size             — 节标题字号不是四号（error）
  ⑨ section_title_align            — 节标题未左对齐（error）
  ⑩ subsection_title_font          — 小标题字体不是宋体（error）
  ⑪ subsection_title_size          — 小标题字号不是小四（error）
  ⑫ subsection_title_bold          — 小标题未加粗（error）
  ⑬ subsection_title_indent        — 小标题未段首空两格（error）
  ⑭ heading_spacing                — 标题段前段后未空0.5行（error）
  ⑮ line_spacing                   — 行距不是1.5倍（error）

输入: output/parser_json/headings.json（文档拆解团队输出，items 为段落列表）
输出: output/checker_json/headings.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CHECKER_ID = "headings"
CHECKER_NAME = "章节标题格式检查"

# ── 字号（磅值）────────────────────────────────────────────
PT_SAN_HAO = 16.0       # 三号（章标题）
PT_SI_HAO = 14.0        # 四号（节标题）
PT_XIAO_SI = 12.0       # 小四（小标题）
_SIZE_TOL = 0.5

# ── 字体名（兼容简繁/英文写法）─────────────────────────────
_FONT_HEITI = {"黑体", "黑體", "simhei"}
_FONT_SONGTI = {"宋体", "宋體", "simsun"}

# ── 对齐方式中文映射 ───────────────────────────────────────
_ALIGNMENT_NAMES: dict[str, str] = {
    "LEFT": "左对齐",
    "CENTER": "居中",
    "RIGHT": "右对齐",
    "JUSTIFY": "两端对齐",
}

# ── 编号体系正则 ──────────────────────────────────────────
# 汉字体系：一、二、三、... →（一）（二）（三）... → 1. 2. 3. ... →（1）（2）（3）
_RE_HANZI_LEVEL1 = re.compile(r"^[一二三四五六七八九十百千万亿]+、")
_RE_HANZI_LEVEL2 = re.compile(r"^（[一二三四五六七八九十百千万亿]+）")
_RE_HANZI_LEVEL3 = re.compile(r"^\d+\.")
_RE_HANZI_LEVEL4 = re.compile(r"^（\d+）")

# 数字体系：1 → 1.1 → 1.1.1 → 1.1.1.1
_RE_NUM_LEVEL1 = re.compile(r"^\d+$")
_RE_NUM_LEVEL2 = re.compile(r"^\d+\.\d+$")
_RE_NUM_LEVEL3 = re.compile(r"^\d+\.\d+\.\d+$")
_RE_NUM_LEVEL4 = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

# ── 段落间距（行）─────────────────────────────────────────
SPACING_BEFORE_AFTER = 0.5  # 段前段后各 0.5 行
LINE_SPACING = 1.5          # 1.5 倍行距

# ── 段落缩进（字符）───────────────────────────────────────
INDENT_CHARS = 2            # 段首空两格（中文）

# ── 最大标题层级 ──────────────────────────────────────────
MAX_LEVEL = 5


# ===================================================================
#  工具函数
# ===================================================================

def _truncate(text: str, max_len: int = 80) -> str:
    """将文本截断至 max_len 字符，超长尾部追加 ...。"""
    text = text.replace("\n", " ").replace("\r", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _norm(s: Any) -> str:
    """归一化为小写去空字符串。"""
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
    """构造一条 error 或 warning 记录。"""
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
    """取段落的 runs。"""
    return para.get("runs") or []


def _run_font(run: dict, use_east_asia: bool = True) -> str:
    """取 run 的字体名。"""
    if use_east_asia:
        return _norm(run.get("east_asia_font") or run.get("font_name"))
    return _norm(run.get("font_name") or run.get("east_asia_font"))


def _eq_size(actual: Any, expected: float, tol: float = _SIZE_TOL) -> bool:
    """判断字号是否在容差范围内相等。"""
    if actual is None:
        return False
    try:
        return abs(float(actual) - expected) <= tol
    except (TypeError, ValueError):
        return False


def _para_alignment(para: dict) -> str:
    """段落对齐方式。"""
    return _norm(para.get("alignment") or "UNKNOWN")


def _is_heading(para: dict) -> bool:
    """判断是否为标题段落（启发式：以编号开头）。"""
    text = (para.get("text") or "").strip()
    if not text:
        return False
    patterns = [
        _RE_HANZI_LEVEL1, _RE_HANZI_LEVEL2, _RE_HANZI_LEVEL3, _RE_HANZI_LEVEL4,
        _RE_NUM_LEVEL1, _RE_NUM_LEVEL2, _RE_NUM_LEVEL3, _RE_NUM_LEVEL4,
    ]
    return any(p.match(text) for p in patterns)


def _get_heading_level(text: str) -> tuple[str, int] | None:
    """获取标题的编号体系和层级。返回 (system, level) 或 None。"""
    # 汉字体系
    if _RE_HANZI_LEVEL1.match(text):
        return ("hanzi", 1)
    if _RE_HANZI_LEVEL2.match(text):
        return ("hanzi", 2)
    if _RE_HANZI_LEVEL3.match(text):
        return ("hanzi", 3)
    if _RE_HANZI_LEVEL4.match(text):
        return ("hanzi", 4)
    
    # 数字体系
    if _RE_NUM_LEVEL1.match(text):
        return ("num", 1)
    if _RE_NUM_LEVEL2.match(text):
        return ("num", 2)
    if _RE_NUM_LEVEL3.match(text):
        return ("num", 3)
    if _RE_NUM_LEVEL4.match(text):
        return ("num", 4)
    
    return None


def _has_trailing_punctuation(text: str) -> bool:
    """检查标题末尾是否有标点符号。"""
    if not text:
        return False
    # 中文标点：。，；：！？、…—·《》（）“”
    # 英文标点：.,;:!?
    punctuation = r'[。，；：！？、…—·《》（）“”\.,;:!?]'
    return bool(re.search(punctuation + r'$', text.strip()))


def _get_indent(para: dict) -> float:
    """获取段落首行缩进（单位：cm 或字符）。"""
    return para.get("first_line_indent_cm", 0.0)


def _eq_spacing(actual: Any, expected: float, tol: float = 0.05) -> bool:
    """判断行距/段距是否在容差范围内相等。"""
    if actual is None:
        return False
    try:
        return abs(float(actual) - expected) <= tol
    except (TypeError, ValueError):
        return False


# ===================================================================
#  检查函数
# ===================================================================

def _check_system_consistency(headings: list[dict]) -> list[dict]:
    """① 两类编号体系不可混用。"""
    errors: list[dict] = []
    detected_systems = set()
    
    for p in headings:
        text = (p.get("text") or "").strip()
        info = _get_heading_level(text)
        if info:
            detected_systems.add(info[0])
    
    if len(detected_systems) > 1:
        errors.append(
            _build_record(
                "error", "heading_system_inconsistent",
                "标题编号体系混用",
                "全文应统一使用汉字体系（一、→（一）→1.→（1））或数字体系（1→1.1→1.1.1）",
                f"检测到 {', '.join(detected_systems)} 两种体系",
                0, "",
            )
        )
    
    return errors


def _check_level_exceeds_five(headings: list[dict]) -> list[dict]:
    """② 标题层级不超过五级。"""
    errors: list[dict] = []
    for p in headings:
        text = (p.get("text") or "").strip()
        info = _get_heading_level(text)
        if info and info[1] >= MAX_LEVEL:
            errors.append(
                _build_record(
                    "error", "heading_level_exceeds_five",
                    f"标题层级超过五级（当前第 {info[1]} 级）",
                    f"标题层级不应超过 {MAX_LEVEL} 级",
                    f"当前为第 {info[1]} 级",
                    p.get("index", 0),
                    _truncate(text),
                )
            )
    return errors


def _check_trailing_punctuation(headings: list[dict]) -> list[dict]:
    """③ 标题末尾不添加标点符号。"""
    errors: list[dict] = []
    for p in headings:
        text = (p.get("text") or "").strip()
        if _has_trailing_punctuation(text):
            errors.append(
                _build_record(
                    "error", "heading_trailing_punctuation",
                    "标题末尾有标点符号",
                    "标题末尾不应添加标点符号",
                    f"当前末尾为 '{text[-1]}'",
                    p.get("index", 0),
                    _truncate(text),
                )
            )
    return errors


def _check_chapter_title_format(chapter_headings: list[dict]) -> list[dict]:
    """④⑤⑥ 章标题：黑体三号居中。"""
    errors: list[dict] = []
    for p in chapter_headings:
        text = (p.get("text") or "").strip()
        idx = p.get("index", 0)
        preview = _truncate(text)
        runs = _para_runs(p)
        
        # 字体：黑体
        bad_fonts = {_run_font(r) for r in runs} - _FONT_HEITI
        bad_fonts.discard("")
        if bad_fonts:
            errors.append(
                _build_record(
                    "error", "chapter_title_font",
                    "章标题字体不是黑体",
                    "章标题应使用黑体",
                    f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                    idx, preview,
                )
            )
        
        # 字号：三号
        sizes = [r.get("font_size") for r in runs if r.get("font_size") is not None]
        if sizes and not all(_eq_size(s, PT_SAN_HAO) for s in sizes):
            errors.append(
                _build_record(
                    "error", "chapter_title_size",
                    "章标题字号不是三号",
                    "章标题应为三号（16pt）",
                    f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                    idx, preview,
                )
            )
        
        # 对齐：居中
        align = _para_alignment(p)
        if align != "center":
            errors.append(
                _build_record(
                    "error", "chapter_title_align",
                    "章标题未居中",
                    "章标题应居中",
                    f"当前对齐方式为 {_ALIGNMENT_NAMES.get(align.upper(), align)}",
                    idx, preview,
                )
            )
    
    return errors


def _check_section_title_format(section_headings: list[dict]) -> list[dict]:
    """⑦⑧⑨ 节标题：黑体四号左对齐。"""
    errors: list[dict] = []
    for p in section_headings:
        text = (p.get("text") or "").strip()
        idx = p.get("index", 0)
        preview = _truncate(text)
        runs = _para_runs(p)
        
        # 字体：黑体
        bad_fonts = {_run_font(r) for r in runs} - _FONT_HEITI
        bad_fonts.discard("")
        if bad_fonts:
            errors.append(
                _build_record(
                    "error", "section_title_font",
                    "节标题字体不是黑体",
                    "节标题应使用黑体",
                    f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                    idx, preview,
                )
            )
        
        # 字号：四号
        sizes = [r.get("font_size") for r in runs if r.get("font_size") is not None]
        if sizes and not all(_eq_size(s, PT_SI_HAO) for s in sizes):
            errors.append(
                _build_record(
                    "error", "section_title_size",
                    "节标题字号不是四号",
                    "节标题应为四号（14pt）",
                    f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                    idx, preview,
                )
            )
        
        # 对齐：左对齐
        align = _para_alignment(p)
        if align != "left":
            errors.append(
                _build_record(
                    "error", "section_title_align",
                    "节标题未左对齐",
                    "节标题应左对齐",
                    f"当前对齐方式为 {_ALIGNMENT_NAMES.get(align.upper(), align)}",
                    idx, preview,
                )
            )
    
    return errors


def _check_subsection_title_format(subsection_headings: list[dict]) -> list[dict]:
    """⑩⑪⑫⑬ 小标题：宋体小四加粗段首空两格。"""
    errors: list[dict] = []
    for p in subsection_headings:
        text = (p.get("text") or "").strip()
        idx = p.get("index", 0)
        preview = _truncate(text)
        runs = _para_runs(p)
        
        # 字体：宋体
        bad_fonts = {_run_font(r) for r in runs} - _FONT_SONGTI
        bad_fonts.discard("")
        if bad_fonts:
            errors.append(
                _build_record(
                    "error", "subsection_title_font",
                    "小标题字体不是宋体",
                    "小标题应使用宋体",
                    f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                    idx, preview,
                )
            )
        
        # 字号：小四
        sizes = [r.get("font_size") for r in runs if r.get("font_size") is not None]
        if sizes and not all(_eq_size(s, PT_XIAO_SI) for s in sizes):
            errors.append(
                _build_record(
                    "error", "subsection_title_size",
                    "小标题字号不是小四",
                    "小标题应为小四（12pt）",
                    f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                    idx, preview,
                )
            )
        
        # 加粗
        if not any(r.get("bold") for r in runs):
            errors.append(
                _build_record(
                    "error", "subsection_title_bold",
                    "小标题未加粗",
                    "小标题应加粗",
                    "未检测到加粗 run",
                    idx, preview,
                )
            )
        
        # 段首空两格（使用缩进判断）
        indent = _get_indent(p)
        # 假设 1 字符 ≈ 0.35cm（小四字号下）
        expected_indent_cm = INDENT_CHARS * 0.35
        if indent > 0 and not _eq_size(indent, expected_indent_cm, 0.1):
            errors.append(
                _build_record(
                    "error", "subsection_title_indent",
                    "小标题未段首空两格",
                    f"小标题应段首空 {INDENT_CHARS} 格",
                    f"当前缩进为 {indent:.2f} cm",
                    idx, preview,
                )
            )
    
    return errors


def _check_heading_spacing(headings: list[dict]) -> list[dict]:
    """⑭ 标题段前段后各空 0.5 行。"""
    errors: list[dict] = []
    for p in headings:
        before = p.get("spacing_before")
        after = p.get("spacing_after")
        
        if before is not None and not _eq_spacing(before, SPACING_BEFORE_AFTER):
            errors.append(
                _build_record(
                    "error", "heading_spacing",
                    "标题段前间距不符合规范",
                    f"标题段前应空 {SPACING_BEFORE_AFTER} 行",
                    f"当前段前为 {before} 行",
                    p.get("index", 0),
                    _truncate(p.get("text", "")),
                )
            )
        
        if after is not None and not _eq_spacing(after, SPACING_BEFORE_AFTER):
            errors.append(
                _build_record(
                    "error", "heading_spacing",
                    "标题段后间距不符合规范",
                    f"标题段后应空 {SPACING_BEFORE_AFTER} 行",
                    f"当前段后为 {after} 行",
                    p.get("index", 0),
                    _truncate(p.get("text", "")),
                )
            )
    
    return errors


def _check_line_spacing(headings: list[dict]) -> list[dict]:
    """⑮ 全文统一 1.5 倍行距。"""
    errors: list[dict] = []
    seen_spacings = set()
    
    for p in headings:
        spacing = p.get("line_spacing")
        if spacing is not None:
            seen_spacings.add(round(float(spacing), 2))
    
    # 如果检测到多种行距，报错
    if len(seen_spacings) > 1:
        errors.append(
            _build_record(
                "error", "line_spacing",
                "行距不统一",
                "全文应统一使用 1.5 倍行距",
                f"检测到多种行距：{', '.join(str(s) for s in sorted(seen_spacings))}",
                0, "",
            )
        )
    
    # 如果统一但不是 1.5 倍，报错
    if len(seen_spacings) == 1:
        spacing = next(iter(seen_spacings))
        if not _eq_spacing(spacing, LINE_SPACING):
            errors.append(
                _build_record(
                    "error", "line_spacing",
                    "行距不是 1.5 倍",
                    "全文应统一使用 1.5 倍行距",
                    f"当前行距为 {spacing} 倍",
                    0, "",
                )
            )
    
    return errors


# ===================================================================
#  公共接口
# ===================================================================

def check(headings_items: list[dict], source_file: str = "") -> dict:
    """对章节标题执行全部格式检查。

    Args:
        headings_items: headings.json 的 ``items`` 列表（段落列表）。
        source_file:    来源文件名，仅用于回显。

    Returns:
        符合 headings.json 模板的检查结果字典。
    """
    # 筛选出标题段落
    headings = [p for p in headings_items if _is_heading(p)]
    
    # 按层级分类
    chapter_headings = []
    section_headings = []
    subsection_headings = []
    
    for p in headings:
        text = (p.get("text") or "").strip()
        info = _get_heading_level(text)
        if info:
            level = info[1]
            if level == 1:
                chapter_headings.append(p)
            elif level == 2:
                section_headings.append(p)
            else:
                subsection_headings.append(p)
    
    all_errors: list[dict] = []
    
    all_errors.extend(_check_system_consistency(headings))
    all_errors.extend(_check_level_exceeds_five(headings))
    all_errors.extend(_check_trailing_punctuation(headings))
    all_errors.extend(_check_chapter_title_format(chapter_headings))
    all_errors.extend(_check_section_title_format(section_headings))
    all_errors.extend(_check_subsection_title_format(subsection_headings))
    all_errors.extend(_check_heading_spacing(headings))
    all_errors.extend(_check_line_spacing(headings))
    
    total_errors = len(all_errors)
    status = "pass" if total_errors == 0 else "fail"
    
    return {
        "checker": CHECKER_ID,
        "checker_name": CHECKER_NAME,
        "timestamp": datetime.now().isoformat(),
        "source_file": source_file,
        "summary": {
            "status": status,
            "total_errors": total_errors,
            "total_warnings": 0,
            "total_headings": len(headings),
            "chapter_count": len(chapter_headings),
            "section_count": len(section_headings),
            "subsection_count": len(subsection_headings),
        },
        "errors": all_errors,
        "warnings": [],
    }


def run(input_path: str | Path, output_path: str | Path) -> dict:
    """读 headings.json → 执行 check() → 写 headings.json。"""
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
    _DEFAULT_INPUT = _PROJECT_ROOT / "output" / "parser_json" / "headings.json"
    _DEFAULT_OUTPUT = _PROJECT_ROOT / "output" / "checker_json" / "headings.json"
    
    input_path = sys.argv[1] if len(sys.argv) > 1 else str(_DEFAULT_INPUT)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(_DEFAULT_OUTPUT)
    
    result = run(input_path, output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
