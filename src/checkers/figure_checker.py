"""图表公式编号检查器（审查3）

依据《中山大学本科毕业论文（设计）写作与印制规范》对图、表、公式编号进行纯代码格式检查：

  ① numbering_system_inconsistent  — 图/表/公式编号体系不统一（error）
  ② numbering_gap                  — 编号有跳缺（error）
  ③ numbering_duplicate            — 编号有重复（error）
  ④ formula_align                  — 公式未居中（error）
  ⑤ formula_numbering_format       — 公式编号格式不符（error）
  ⑥ formula_ref_format             — 公式引用格式不符（error）
  ⑦ table_title_position           — 表格标题位置不符（error）
  ⑧ table_title_font               — 表题字体不是宋体五号（error）
  ⑨ table_cross_page               — 跨页表格未标注（warning）
  ⑩ table_ref_format               — 表格引用格式不符（error）
  ⑪ figure_title_position          — 图题位置不符（error）
  ⑫ figure_title_font              — 图题字体不是宋体五号（error）
  ⑬ figure_ref_format              — 图片引用格式不符（error）

输入: output/parser_json/figures_tables_formulas.json
输出: output/checker_json/figures_tables_formulas.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CHECKER_ID = "figures_tables_formulas"
CHECKER_NAME = "图表公式编号检查"

# ── 字体（兼容简繁/英文写法）─────────────────────────────
_FONT_SONGTI = {"宋体", "宋體", "simsun"}
_FONT_TIMES = {"times new roman", "timesnewroman"}

# ── 字号（磅值）────────────────────────────────────────────
PT_WU_HAO = 10.5        # 五号（表题/图题）
_SIZE_TOL = 0.5

# ── 编号格式正则 ──────────────────────────────────────────
# 连续编号：图1，表2，公式(3)
_RE_CONTINUOUS_FIGURE = re.compile(r'^图\s*(\d+)$')
_RE_CONTINUOUS_TABLE = re.compile(r'^表\s*(\d+)$')
_RE_CONTINUOUS_FORMULA = re.compile(r'^\((\d+)\)$')

# 逐章编号：图1.1，表2.3，公式(3.2)
_RE_CHAPTER_FIGURE = re.compile(r'^图\s*(\d+)\.(\d+)$')
_RE_CHAPTER_TABLE = re.compile(r'^表\s*(\d+)\.(\d+)$')
_RE_CHAPTER_FORMULA = re.compile(r'^\((\d+)\.(\d+)\)$')

# 分图编号：3c / 1.1a
_RE_SUBFIGURE = re.compile(r'^(\d+)([a-z])$|^(\d+)\.(\d+)([a-z])$')

# ── 引用格式 ──────────────────────────────────────────────
_RE_REF_FORMULA = re.compile(r'由式\([\d.]+\)')
_RE_REF_TABLE = re.compile(r'如表\d+(\.\d+)?')
_RE_REF_FIGURE = re.compile(r'如图\d+(\.\d+)?')


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


def _run_font(run: dict, use_east_asia: bool = True) -> str:
    if use_east_asia:
        return _norm(run.get("east_asia_font") or run.get("font_name"))
    return _norm(run.get("font_name") or run.get("east_asia_font"))


def _eq_size(actual: Any, expected: float, tol: float = _SIZE_TOL) -> bool:
    if actual is None:
        return False
    try:
        return abs(float(actual) - expected) <= tol
    except (TypeError, ValueError):
        return False


def _para_alignment(para: dict) -> str:
    return _norm(para.get("alignment") or "UNKNOWN")


def _extract_numbers(items: list[dict], pattern: re.Pattern) -> list[tuple[int, int]]:
    """从文本中提取编号。返回 [(编号, 段落索引), ...]"""
    results = []
    for p in items:
        text = (p.get("text") or "").strip()
        match = pattern.match(text)
        if match:
            # 提取编号数字部分
            numbers = [int(x) for x in match.groups() if x is not None and x.isdigit()]
            if numbers:
                results.append((numbers[0], p.get("index", 0)))
    return results


def _check_numbering_consistency(figures: list[dict], tables: list[dict], formulas: list[dict]) -> list[dict]:
    """① 图/表/公式编号体系统一。"""
    errors: list[dict] = []
    systems = set()
    
    # 检测各元素的编号体系
    for items, name in [(figures, "图"), (tables, "表"), (formulas, "公式")]:
        for p in items:
            text = (p.get("text") or "").strip()
            if _RE_CONTINUOUS_FIGURE.match(text) or _RE_CONTINUOUS_TABLE.match(text) or _RE_CONTINUOUS_FORMULA.match(text):
                systems.add("continuous")
            elif _RE_CHAPTER_FIGURE.match(text) or _RE_CHAPTER_TABLE.match(text) or _RE_CHAPTER_FORMULA.match(text):
                systems.add("chapter")
    
    if len(systems) > 1:
        errors.append(
            _build_record(
                "error", "numbering_system_inconsistent",
                "图/表/公式编号体系不统一",
                "三者应统一使用连续编号或逐章编号",
                f"检测到 {', '.join(systems)} 两种体系",
                0, "",
            )
        )
    
    return errors


def _check_numbering_gap_and_duplicate(
    figures: list[dict], tables: list[dict], formulas: list[dict]
) -> list[dict]:
    """②③ 编号无跳缺、无重复。"""
    errors: list[dict] = []
    
    for items, name, pattern in [
        (figures, "图", _RE_CONTINUOUS_FIGURE),
        (tables, "表", _RE_CONTINUOUS_TABLE),
        (formulas, "公式", _RE_CONTINUOUS_FORMULA),
    ]:
        numbers = _extract_numbers(items, pattern)
        if not numbers:
            continue
        
        sorted_nums = sorted(numbers, key=lambda x: x[0])
        seen = set()
        prev = None
        
        for num, idx in sorted_nums:
            # 检查重复
            if num in seen:
                errors.append(
                    _build_record(
                        "error", "numbering_duplicate",
                        f"{name}编号有重复",
                        f"{name}编号应连续无重复",
                        f"编号 {num} 重复出现",
                        idx, _truncate(items[idx].get("text", "")),
                    )
                )
            seen.add(num)
            
            # 检查跳缺
            if prev is not None and num != prev + 1:
                errors.append(
                    _build_record(
                        "error", "numbering_gap",
                        f"{name}编号有跳缺",
                        f"{name}编号应连续无跳缺",
                        f"从 {prev} 跳到 {num}，缺少 {prev + 1}",
                        idx, _truncate(items[idx].get("text", "")),
                    )
                )
            prev = num
    
    return errors


def _check_formula_align(formulas: list[dict]) -> list[dict]:
    """④ 公式单独居中成行。"""
    errors: list[dict] = []
    for p in formulas:
        align = _para_alignment(p)
        if align != "center":
            errors.append(
                _build_record(
                    "error", "formula_align",
                    "公式未居中",
                    "公式应单独居中成行",
                    f"当前对齐方式为 {align}",
                    p.get("index", 0),
                    _truncate(p.get("text", "")),
                )
            )
    return errors


def _check_formula_numbering_format(formulas: list[dict]) -> list[dict]:
    """⑤ 公式编号格式（圆括号）。"""
    errors: list[dict] = []
    for p in formulas:
        text = (p.get("text") or "").strip()
        # 检查编号是否在圆括号中
        if not (text.endswith(")") and ("(" in text)):
            errors.append(
                _build_record(
                    "error", "formula_numbering_format",
                    "公式编号格式不符",
                    "公式编号应使用圆括号，如 (1) 或 (3.2)",
                    f"当前编号格式为 {text[-10:] if len(text) > 10 else text}",
                    p.get("index", 0),
                    _truncate(text),
                )
            )
    return errors


def _check_formula_ref_format(body: list[dict]) -> list[dict]:
    """⑥ 公式引用格式：由式(序号)。"""
    errors: list[dict] = []
    for p in body:
        text = (p.get("text") or "").strip()
        # 查找可能的公式引用
        refs = re.findall(r'式\s*[（(]\s*\d+[\d.]*\s*[）)]', text)
        for ref in refs:
            # 检查是否以"由式"开头
            if not re.match(r'由式\s*[（(]', ref):
                errors.append(
                    _build_record(
                        "error", "formula_ref_format",
                        "公式引用格式不符",
                        "应使用「由式(序号)」格式",
                        f"当前为 {ref}",
                        p.get("index", 0),
                        _truncate(text),
                    )
                )
    return errors


def _check_table_title_position(tables: list[dict]) -> list[dict]:
    """⑦ 表格标题置于表格上方居中。"""
    errors: list[dict] = []
    # parser 应提供 is_table_title 标记或通过位置判断
    for p in tables:
        if p.get("is_title") and p.get("position") != "above":
            errors.append(
                _build_record(
                    "error", "table_title_position",
                    "表格标题位置不符",
                    "表格标题应置于表格上方居中",
                    f"当前标题位于表格 {p.get('position', 'unknown')}",
                    p.get("index", 0),
                    _truncate(p.get("text", "")),
                )
            )
    return errors


def _check_table_title_font(table_titles: list[dict]) -> list[dict]:
    """⑧ 表题统一使用宋体五号。"""
    errors: list[dict] = []
    for p in table_titles:
        runs = _para_runs(p)
        text = (p.get("text") or "").strip()
        idx = p.get("index", 0)
        preview = _truncate(text)
        
        # 字体：宋体
        bad_fonts = {_run_font(r) for r in runs} - _FONT_SONGTI
        bad_fonts.discard("")
        if bad_fonts:
            errors.append(
                _build_record(
                    "error", "table_title_font",
                    "表题字体不是宋体",
                    "表题应使用宋体五号",
                    f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                    idx, preview,
                )
            )
        
        # 字号：五号
        sizes = [r.get("font_size") for r in runs if r.get("font_size") is not None]
        if sizes and not all(_eq_size(s, PT_WU_HAO) for s in sizes):
            errors.append(
                _build_record(
                    "error", "table_title_font",
                    "表题字号不是五号",
                    "表题应为五号（10.5pt）",
                    f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                    idx, preview,
                )
            )
    return errors


def _check_table_cross_page(tables: list[dict]) -> list[dict]:
    """⑨ 跨页表格标注（warning）。"""
    warnings: list[dict] = []
    for p in tables:
        if p.get("is_cross_page"):
            # 检查是否有"续表"标注
            text = (p.get("text") or "").strip()
            if "续表" not in text and "接上页" not in text:
                warnings.append(
                    _build_record(
                        "warning", "table_cross_page",
                        "跨页表格未标注",
                        "跨页表格应标注「续表 XX」或「接上页」",
                        "未检测到跨页标注",
                        p.get("index", 0),
                        _truncate(text),
                    )
                )
    return warnings


def _check_table_ref_format(body: list[dict]) -> list[dict]:
    """⑩ 表格引用格式：如表5。"""
    errors: list[dict] = []
    for p in body:
        text = (p.get("text") or "").strip()
        refs = re.findall(r'表\s*\d+[\d.]*', text)
        for ref in refs:
            if not ref.startswith("如表"):
                errors.append(
                    _build_record(
                        "error", "table_ref_format",
                        "表格引用格式不符",
                        "应使用「如表5」格式",
                        f"当前为 {ref}",
                        p.get("index", 0),
                        _truncate(text),
                    )
                )
    return errors


def _check_figure_title_position(figures: list[dict]) -> list[dict]:
    """⑪ 图题位置：分图图名在图题下方。"""
    errors: list[dict] = []
    for p in figures:
        if p.get("is_title") and p.get("has_subfigures"):
            # 检查分图图名是否在图题下方
            if p.get("subfigure_names_position") != "below":
                errors.append(
                    _build_record(
                        "error", "figure_title_position",
                        "分图图名位置不符",
                        "分图图名应在图题下方",
                        f"当前位置为 {p.get('subfigure_names_position', 'unknown')}",
                        p.get("index", 0),
                        _truncate(p.get("text", "")),
                    )
                )
    return errors


def _check_figure_title_font(figure_titles: list[dict]) -> list[dict]:
    """⑫ 图题统一使用宋体五号。"""
    errors: list[dict] = []
    for p in figure_titles:
        runs = _para_runs(p)
        text = (p.get("text") or "").strip()
        idx = p.get("index", 0)
        preview = _truncate(text)
        
        # 字体：宋体
        bad_fonts = {_run_font(r) for r in runs} - _FONT_SONGTI
        bad_fonts.discard("")
        if bad_fonts:
            errors.append(
                _build_record(
                    "error", "figure_title_font",
                    "图题字体不是宋体",
                    "图题应使用宋体五号",
                    f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                    idx, preview,
                )
            )
        
        # 字号：五号
        sizes = [r.get("font_size") for r in runs if r.get("font_size") is not None]
        if sizes and not all(_eq_size(s, PT_WU_HAO) for s in sizes):
            errors.append(
                _build_record(
                    "error", "figure_title_font",
                    "图题字号不是五号",
                    "图题应为五号（10.5pt）",
                    f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                    idx, preview,
                )
            )
    return errors


def _check_figure_ref_format(body: list[dict]) -> list[dict]:
    """⑬ 图片引用格式：如图5。"""
    errors: list[dict] = []
    for p in body:
        text = (p.get("text") or "").strip()
        refs = re.findall(r'图\s*\d+[\d.]*[a-z]?', text)
        for ref in refs:
            if not ref.startswith("如图"):
                errors.append(
                    _build_record(
                        "error", "figure_ref_format",
                        "图片引用格式不符",
                        "应使用「如图5」格式",
                        f"当前为 {ref}",
                        p.get("index", 0),
                        _truncate(text),
                    )
                )
    return errors


# ===================================================================
#  公共接口
# ===================================================================

def check(
    figures: list[dict],
    tables: list[dict],
    formulas: list[dict],
    body: list[dict],
    source_file: str = "",
) -> dict:
    """对图表公式执行全部格式检查。"""
    all_errors: list[dict] = []
    all_warnings: list[dict] = []
    
    # 编号一致性
    all_errors.extend(_check_numbering_consistency(figures, tables, formulas))
    all_errors.extend(_check_numbering_gap_and_duplicate(figures, tables, formulas))
    
    # 公式
    formula_items = [p for p in formulas if not p.get("is_title")]
    formula_titles = [p for p in formulas if p.get("is_title")]
    all_errors.extend(_check_formula_align(formula_items))
    all_errors.extend(_check_formula_numbering_format(formula_items))
    all_errors.extend(_check_formula_ref_format(body))
    
    # 表格
    table_items = [p for p in tables if not p.get("is_title")]
    table_titles = [p for p in tables if p.get("is_title")]
    all_errors.extend(_check_table_title_position(tables))
    all_errors.extend(_check_table_title_font(table_titles))
    all_warnings.extend(_check_table_cross_page(tables))
    all_errors.extend(_check_table_ref_format(body))
    
    # 插图
    figure_items = [p for p in figures if not p.get("is_title")]
    figure_titles = [p for p in figures if p.get("is_title")]
    all_errors.extend(_check_figure_title_position(figures))
    all_errors.extend(_check_figure_title_font(figure_titles))
    all_errors.extend(_check_figure_ref_format(body))
    
    total_errors = len(all_errors)
    total_warnings = len(all_warnings)
    status = "pass" if (total_errors == 0 and total_warnings == 0) else "fail"
    
    return {
        "checker": CHECKER_ID,
        "checker_name": CHECKER_NAME,
        "timestamp": datetime.now().isoformat(),
        "source_file": source_file,
        "summary": {
            "status": status,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "figure_count": len(figures),
            "table_count": len(tables),
            "formula_count": len(formulas),
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
    items = data.get("items", {})
    
    result = check(
        items.get("figures", []),
        items.get("tables", []),
        items.get("formulas", []),
        items.get("body", []),
        source_file=source_file,
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result


if __name__ == "__main__":
    import sys
    
    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    _DEFAULT_INPUT = _PROJECT_ROOT / "output" / "parser_json" / "figures_tables_formulas.json"
    _DEFAULT_OUTPUT = _PROJECT_ROOT / "output" / "checker_json" / "figures_tables_formulas.json"
    
    input_path = sys.argv[1] if len(sys.argv) > 1 else str(_DEFAULT_INPUT)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(_DEFAULT_OUTPUT)
    
    result = run(input_path, output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
