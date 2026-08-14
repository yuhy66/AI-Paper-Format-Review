"""封面/扉页/声明格式检查器（审查1）

依据《中山大学本科毕业论文（设计）写作与印制规范》对论文封面、扉页、
学术诚信声明与页面设置进行纯代码格式检查：

  ① cover_empty             — 封面为空（error）
  ② cover_missing_field     — 封面缺少必填字段（error）
  ③ cover_title_missing     — 未定位到论文题目（error）
  ④ cover_title_too_long    — 论文题目超过 25 字（error）
  ⑤ cover_title_font        — 论文题目字体不是黑体（error）
  ⑥ cover_title_size        — 论文题目字号不是二号（error）
  ⑦ cover_title_align       — 论文题目未居中（error）
  ⑧ title_page_empty         — 扉页为空（error）
  ⑨ title_page_missing_field — 扉页缺少必填字段（error）
  ⑩ title_page_title_missing — 未定位到扉页题目（error）
  ⑪ title_page_title_font    — 扉页题目字体不是黑体（error）
  ⑫ title_page_title_size    — 扉页题目字号不是二号（error）
  ⑬ title_page_title_align   — 扉页题目未居中（error）
  ⑭ statement_missing        — 未检测到学术诚信声明（warning）
  ⑮ page_not_a4              — 页面尺寸不是 A4（error）
  ⑯ page_margin              — 页边距不符合规范（error）

输入: output/parser_json/ 下的 cover.json / title_page.json / statement.json
输出: output/checker_json/cover.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

CHECKER_ID = "cover"
CHECKER_NAME = "封面/扉页/声明格式检查"

# ── 字号（磅值）────────────────────────────────────────────
PT_ER_HAO = 22.0        # 二号（论文题目）

# ── 页面设置（单位 cm，与 parser 的 PageSettings 一致）─────
PAGE_A4_WIDTH_CM = 21.0
PAGE_A4_HEIGHT_CM = 29.7
MARGIN_TOP_CM = 2.5     # 上边距 25 mm
MARGIN_BOTTOM_CM = 2.0  # 下边距 20 mm
MARGIN_SIDE_CM = 3.0    # 左右边距 30 mm
_SIZE_TOL = 0.5         # 字号容差（pt）
_PAGE_TOL = 0.1         # 页面尺寸/边距容差（cm）

# ── 中文字体名（兼容简繁/英文写法）─────────────────────────
_FONT_HEITI = {"黑体", "黑體", "simhei"}

# ── 封面 / 扉页必填字段关键字（院系/专业/姓名/学号/指导教师）──
# 题目单独通过 _find_title 定位，不在此处做标签匹配（封面题目可能是无标签的独立行）
COVER_FIELDS = ["院系", "专业", "姓名", "学号", "指导教师"]
TITLE_PAGE_FIELDS = ["姓名", "学号", "院系", "专业", "指导教师"]

# ── 论文题目最大字数 ───────────────────────────────────────
TITLE_MAX_CHARS = 25

# ── 学术诚信声明关键字 ─────────────────────────────────────
STATEMENT_KEYWORDS = [
    "学术诚信声明", "诚信声明", "原创性声明", "独创性声明", "知识产权声明",
]

# ── 对齐方式中文映射 ───────────────────────────────────────
_ALIGNMENT_NAMES: dict[str, str] = {
    "LEFT": "左对齐",
    "CENTER": "居中",
    "RIGHT": "右对齐",
    "JUSTIFY": "两端对齐",
}


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
    """取段落的 runs（parser 已过滤无意义 run，单 run 段落省略 run.text）。"""
    return para.get("runs") or []


def _run_font(run: dict, use_east_asia: bool = True) -> str:
    """取 run 的字体名。use_east_asia=True 优先中文字体，否则优先西文字体。"""
    if use_east_asia:
        return _norm(run.get("east_asia_font") or run.get("font_name"))
    return _norm(run.get("font_name") or run.get("east_asia_font"))


def _eq_size(actual: Any, expected: float, tol: float = _SIZE_TOL) -> bool:
    """判断字号/尺寸是否在容差范围内相等。"""
    if actual is None:
        return False
    try:
        return abs(float(actual) - expected) <= tol
    except (TypeError, ValueError):
        return False


def _para_alignment(para: dict) -> str:
    """段落对齐方式（小写，无值返回 unknown）。"""
    return _norm(para.get("alignment") or "UNKNOWN")


def _max_run_size(para: dict) -> float:
    """段落中所有 run 的最大字号（无字号返回 -1）。"""
    sizes = [r.get("font_size") for r in _para_runs(para) if r.get("font_size") is not None]
    return max(sizes) if sizes else -1.0


def _contains_cjk(text: str) -> bool:
    """判断文本是否含中日韩汉字（用于区分中文/英文题目）。"""
    return any("一" <= ch <= "鿿" for ch in text)


def _find_title(paras: list[dict], cjk_only: bool = False) -> dict | None:
    """在封面/扉页段落中定位论文题目。

    启发式：取非空段落中字号最大的那一段（题目为二号，通常是封面最大字号），
    并列时取文本更长的一段。cjk_only=True 时只在中含汉字的段落中定位（用于
    扉页——中英文题目同为二号时，确保命中中文题目做字体判等）。
    """
    candidates = [p for p in paras if (p.get("text") or "").strip()]
    if cjk_only:
        candidates = [p for p in candidates if _contains_cjk(p.get("text", ""))]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (_max_run_size(p), len(p.get("text", ""))))


def _join_text(paras: list[dict]) -> str:
    """拼接段落文本。"""
    return "".join(p.get("text", "") for p in paras)


# ===================================================================
#  检查函数
# ===================================================================

def _check_cover_empty(cover_items: list[dict]) -> list[dict]:
    """① 封面为空。"""
    if cover_items:
        return []
    return [
        _build_record(
            "error", "cover_empty",
            "未检测到封面内容",
            "论文应包含封面（题目、院系、专业、姓名、学号、指导教师）",
            "封面为空（cover.json 的 items 为空）",
            0, "",
        )
    ]


def _check_cover_missing_field(cover_items: list[dict]) -> list[dict]:
    """② 封面缺少必填字段。"""
    if not cover_items:
        return []
    text = _join_text(cover_items)
    errors: list[dict] = []
    for field in COVER_FIELDS:
        if field not in text:
            errors.append(
                _build_record(
                    "error", "cover_missing_field",
                    f"封面缺少必填字段「{field}」",
                    f"封面应包含字段：{'、'.join(COVER_FIELDS)}",
                    f"未在封面文本中找到「{field}」",
                    0, _truncate(text),
                )
            )
    return errors


def _check_cover_title_missing(cover_items: list[dict], title: dict | None) -> list[dict]:
    """③ 未定位到论文题目。"""
    if not cover_items or title is not None:
        return []
    return [
        _build_record(
            "error", "cover_title_missing",
            "未定位到论文题目",
            "封面应包含论文题目（黑体二号居中）",
            "无法在封面段落中识别出题目",
            0, _truncate(_join_text(cover_items)),
        )
    ]


def _check_cover_title_length(title: dict) -> list[dict]:
    """④ 论文题目超过 25 字。"""
    idx = title.get("index", 0)
    text = title.get("text", "")
    preview = _truncate(text)
    length = len(text.strip())
    if length <= TITLE_MAX_CHARS:
        return []
    return [
        _build_record(
            "error", "cover_title_too_long",
            f"论文题目超过 {TITLE_MAX_CHARS} 字",
            f"论文题目一般不宜超过 {TITLE_MAX_CHARS} 字（必要时可加副标题）",
            f"当前题目共 {length} 字",
            idx, preview,
        )
    ]


def _check_title_format(title: dict, prefix: str, label: str) -> list[dict]:
    """题目字体/字号/对齐检查（黑体二号居中），封面与扉页题目共用。

    Args:
        title:  题目段落（由 _find_title 定位）。
        prefix: category 前缀（cover_title / title_page_title）。
        label:  描述用词（论文题目 / 扉页题目）。
    """
    errors: list[dict] = []
    idx = title.get("index", 0)
    preview = _truncate(title.get("text", ""))

    # 字体：黑体
    bad_fonts = {_run_font(r) for r in _para_runs(title)} - _FONT_HEITI
    bad_fonts.discard("")  # 无字体信息不判
    if bad_fonts:
        errors.append(
            _build_record(
                "error", f"{prefix}_font",
                f"{label}字体不是黑体",
                f"{label}应使用黑体",
                f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                idx, preview,
            )
        )

    # 字号：二号（22pt）
    sizes = [r.get("font_size") for r in _para_runs(title) if r.get("font_size") is not None]
    if sizes and not all(_eq_size(s, PT_ER_HAO) for s in sizes):
        errors.append(
            _build_record(
                "error", f"{prefix}_size",
                f"{label}字号不是二号",
                f"{label}应为二号（22pt）",
                f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                idx, preview,
            )
        )

    # 对齐：居中
    align = _para_alignment(title)
    if align != "center":
        errors.append(
            _build_record(
                "error", f"{prefix}_align",
                f"{label}未居中",
                f"{label}应居中（alignment == CENTER）",
                f"当前对齐方式为 {_ALIGNMENT_NAMES.get(align.upper(), align)}",
                idx, preview,
            )
        )

    return errors


def _check_title_page_title_missing(title_page_items: list[dict], title: dict | None) -> list[dict]:
    """⑩ 未定位到扉页题目。"""
    if not title_page_items or title is not None:
        return []
    return [
        _build_record(
            "error", "title_page_title_missing",
            "未定位到扉页题目",
            "扉页应包含中英文题目（中文题目黑体二号居中）",
            "无法在扉页段落中识别出题目",
            0, _truncate(_join_text(title_page_items)),
        )
    ]


def _check_title_page_empty(title_page_items: list[dict]) -> list[dict]:
    """⑧ 扉页为空。"""
    if title_page_items:
        return []
    return [
        _build_record(
            "error", "title_page_empty",
            "未检测到扉页内容",
            "论文应包含扉页（中英文题目、姓名、学号、院系、专业、指导教师）",
            "扉页为空（title_page.json 的 items 为空）",
            0, "",
        )
    ]


def _check_title_page_missing_field(title_page_items: list[dict]) -> list[dict]:
    """⑨ 扉页缺少必填字段。"""
    if not title_page_items:
        return []
    text = _join_text(title_page_items)
    errors: list[dict] = []
    for field in TITLE_PAGE_FIELDS:
        if field not in text:
            errors.append(
                _build_record(
                    "error", "title_page_missing_field",
                    f"扉页缺少必填字段「{field}」",
                    f"扉页应包含字段：{'、'.join(TITLE_PAGE_FIELDS)}",
                    f"未在扉页文本中找到「{field}」",
                    0, _truncate(text),
                )
            )
    return errors


def _check_statement_missing(statement_items: list[dict]) -> list[dict]:
    """⑩ 未检测到学术诚信声明（warning）。"""
    if not statement_items:
        return [
            _build_record(
                "warning", "statement_missing",
                "未检测到学术诚信声明",
                "论文应包含学术诚信声明",
                "声明为空（statement.json 的 items 为空）",
                0, "",
            )
        ]
    text = _join_text(statement_items)
    if any(kw in text for kw in STATEMENT_KEYWORDS):
        return []
    return [
        _build_record(
            "warning", "statement_missing",
            "未检测到学术诚信声明",
            "论文应包含学术诚信声明（如「学术诚信声明」）",
            "声明部分未出现声明关键字",
            0, _truncate(text),
        )
    ]


def _check_page_a4(page: dict | None) -> list[dict]:
    """⑪ 页面尺寸不是 A4。"""
    if not page:
        return []
    w = page.get("width_cm")
    h = page.get("height_cm")
    if w is None or h is None:
        return []
    if _eq_size(w, PAGE_A4_WIDTH_CM, _PAGE_TOL) and _eq_size(h, PAGE_A4_HEIGHT_CM, _PAGE_TOL):
        return []
    return [
        _build_record(
            "error", "page_not_a4",
            "页面尺寸不是 A4",
            f"A4 纸张（{PAGE_A4_WIDTH_CM} × {PAGE_A4_HEIGHT_CM} cm）",
            f"当前页面 {w} × {h} cm",
            0, "",
        )
    ]


def _check_page_margin(page: dict | None) -> list[dict]:
    """⑫ 页边距不符合规范。"""
    if not page:
        return []
    errors: list[dict] = []
    checks = [
        ("top_margin_cm", "上边距", MARGIN_TOP_CM),
        ("bottom_margin_cm", "下边距", MARGIN_BOTTOM_CM),
        ("left_margin_cm", "左边距", MARGIN_SIDE_CM),
        ("right_margin_cm", "右边距", MARGIN_SIDE_CM),
    ]
    for key, label, expected in checks:
        val = page.get(key)
        if val is None:
            continue
        if not _eq_size(val, expected, _PAGE_TOL):
            errors.append(
                _build_record(
                    "error", "page_margin",
                    f"页{label}不符合规范",
                    f"{label}应为 {expected} cm",
                    f"当前{label}为 {val} cm",
                    0, "",
                )
            )
    return errors


# ===================================================================
#  公共接口
# ===================================================================

def check(
    cover_items: list[dict],
    title_page_items: list[dict],
    statement_items: list[dict],
    page: dict | None,
    source_file: str = "",
) -> dict:
    """对封面/扉页/声明/页面执行全部格式检查。

    Args:
        cover_items:     cover.json 的 ``items`` 列表（封面段落）。
        title_page_items: title_page.json 的 ``items`` 列表（扉页段落）。
        statement_items: statement.json 的 ``items`` 列表（声明段落）。
        page:            parser 输出的页面设置字典（page 字段，单位 cm）。
        source_file:     来源文件名，仅用于回显。

    Returns:
        符合 cover.json 模板的检查结果字典。
    """
    all_errors: list[dict] = []
    all_warnings: list[dict] = []

    # 封面
    all_errors.extend(_check_cover_empty(cover_items))
    all_errors.extend(_check_cover_missing_field(cover_items))
    title = _find_title(cover_items)
    all_errors.extend(_check_cover_title_missing(cover_items, title))
    if title is not None:
        all_errors.extend(_check_cover_title_length(title))
        all_errors.extend(_check_title_format(title, "cover_title", "论文题目"))

    # 扉页
    all_errors.extend(_check_title_page_empty(title_page_items))
    all_errors.extend(_check_title_page_missing_field(title_page_items))
    tp_title = _find_title(title_page_items, cjk_only=True)
    all_errors.extend(_check_title_page_title_missing(title_page_items, tp_title))
    if tp_title is not None:
        all_errors.extend(_check_title_format(tp_title, "title_page_title", "扉页题目"))

    # 声明
    all_warnings.extend(_check_statement_missing(statement_items))

    # 页面设置
    all_errors.extend(_check_page_a4(page))
    all_errors.extend(_check_page_margin(page))

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
            "cover_count": len(cover_items),
            "title_page_count": len(title_page_items),
            "statement_count": len(statement_items),
        },
        "errors": all_errors,
        "warnings": all_warnings,
    }


def run(parser_json_dir: str | Path, output_path: str | Path) -> dict:
    """读 parser 输出的 cover/title_page/statement 三个 JSON → 执行 check() → 写 cover.json。

    Args:
        parser_json_dir: 目录，内含 cover.json / title_page.json / statement.json。
        output_path:     输出路径，如 output/checker_json/cover.json。

    Returns:
        检查结果字典（已写入 output_path）。
    """
    parser_json_dir = Path(parser_json_dir)
    output_path = Path(output_path)

    def _load(name: str) -> dict:
        fp = parser_json_dir / name
        if not fp.exists():
            return {}
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)

    cover_data = _load("cover.json")
    title_page_data = _load("title_page.json")
    statement_data = _load("statement.json")

    source_file = (
        cover_data.get("file_name")
        or title_page_data.get("file_name")
        or statement_data.get("file_name")
        or ""
    )
    page = cover_data.get("page") or title_page_data.get("page") or statement_data.get("page") or {}

    result = check(
        cover_data.get("items", []),
        title_page_data.get("items", []),
        statement_data.get("items", []),
        page,
        source_file=source_file,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


# ===================================================================
#  CLI 入口
# ===================================================================

if __name__ == "__main__":
    import sys

    # 从当前文件位置推算项目根目录（向上 2 级：src/checkers -> src -> 根）
    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    _DEFAULT_INPUT_DIR = _PROJECT_ROOT / "output" / "parser_json"
    _DEFAULT_OUTPUT = _PROJECT_ROOT / "output" / "checker_json" / "cover.json"

    parser_json_dir = sys.argv[1] if len(sys.argv) > 1 else str(_DEFAULT_INPUT_DIR)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(_DEFAULT_OUTPUT)

    result = run(parser_json_dir, output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
