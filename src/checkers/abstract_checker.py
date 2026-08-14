"""摘要与关键词格式检查器（审查1）

依据《中山大学本科毕业论文（设计）写作与印制规范》对中英文摘要与关键词进行
纯代码格式检查：

  中文摘要：
  ① abstract_missing        — 摘要为空（error）
  ② abstract_title_missing  — 摘要标题缺失（error）
  ③ abstract_title_font     — 摘要标题字体不是黑体（error）
  ④ abstract_title_size     — 摘要标题字号不是三号（error）
  ⑤ abstract_title_align    — 摘要标题未居中（error）
  ⑥ abstract_length         — 摘要字数不在 300-500 字（error）
  ⑦ abstract_body_font      — 摘要正文字体不是宋体（error）
  ⑧ abstract_body_size      — 摘要正文字号不是小四（error）

  中文关键词：
  ⑨ keyword_missing         — 中文关键词缺失（error）
  ⑩ keyword_label_format    — 「关键词」未顶格/未加冒号（error）
  ⑪ keyword_label_bold      — 「关键词」未加粗（error）
  ⑫ keyword_font            — 关键词字体不是宋体（error）
  ⑬ keyword_count           — 关键词不在 3-5 个（error）

  英文摘要：
  ⑭ english_title_missing   — 英文摘要标题缺失（error）
  ⑮ english_title_format    — 英文标题格式不符（TNR加粗三号全大写）（error）
  ⑯ english_keyword_missing — 英文关键词缺失（error）
  ⑰ english_keyword_format  — 英文关键词格式不符（TNR加粗）（error）

输入: output/parser_json/abstract.json（文档拆解团队输出，items[0] 为
      {title, body, keywords} 结构）
输出: output/checker_json/abstract.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CHECKER_ID = "abstract"
CHECKER_NAME = "摘要与关键词格式检查"

# ── 字号（磅值）────────────────────────────────────────────
PT_SAN_HAO = 16.0       # 三号（摘要标题）
PT_XIAO_SI = 12.0       # 小四（摘要内容/关键词）
_SIZE_TOL = 0.5

# ── 摘要字数 / 关键词数量 ──────────────────────────────────
CN_ABSTRACT_MIN = 300
CN_ABSTRACT_MAX = 500
KEYWORD_MIN = 3
KEYWORD_MAX = 5

# ── 字体名（兼容简繁/英文写法）─────────────────────────────
_FONT_HEITI = {"黑体", "黑體", "simhei"}
_FONT_SONGTI = {"宋体", "宋體", "simsun"}
_FONT_TIMES = {"times new roman", "timesnewroman"}

# ── 对齐方式中文映射 ───────────────────────────────────────
_ALIGNMENT_NAMES: dict[str, str] = {
    "LEFT": "左对齐",
    "CENTER": "居中",
    "RIGHT": "右对齐",
    "JUSTIFY": "两端对齐",
}

# ── 正则：英文摘要标题 / 中英文关键词行 ────────────────────
_RE_EN_TITLE = re.compile(r"^\s*abstract\s*$", re.IGNORECASE)
_RE_KEYWORD_CN = re.compile(r"^\s*关键词\s*[：:]\s*(.*)$")
_RE_KEYWORD_EN = re.compile(r"^\s*keywords\s*[：:]\s*(.*)$", re.IGNORECASE)


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
    """判断字号是否在容差范围内相等。"""
    if actual is None:
        return False
    try:
        return abs(float(actual) - expected) <= tol
    except (TypeError, ValueError):
        return False


def _para_alignment(para: dict) -> str:
    """段落对齐方式（小写，无值返回 unknown）。"""
    return _norm(para.get("alignment") or "UNKNOWN")


def _split_body(body_paras: list[dict]) -> tuple[list[dict], list[dict]]:
    """把摘要正文拆成（中文部分, 英文部分）。

    以英文标题「Abstract」为分界：之前为中文摘要正文，之后（含 Abstract 行）为英文部分。
    """
    cn: list[dict] = []
    en: list[dict] = []
    seen_en = False
    for p in body_paras:
        text = (p.get("text") or "").strip()
        if not seen_en and _RE_EN_TITLE.match(text):
            seen_en = True
        if seen_en:
            en.append(p)
        else:
            cn.append(p)
    return cn, en


def _count_chars(paras: list[dict]) -> int:
    """统计段落的总非空白字符数（近似摘要字数）。"""
    text = "".join(p.get("text", "") for p in paras)
    return len(re.sub(r"\s+", "", text))


def _count_keywords(text: str, pattern: re.Pattern) -> int:
    """统计关键词数量：按逗号/顿号/分号切分冒号后的内容。"""
    m = pattern.match(text)
    if not m:
        return 0
    value = m.group(1)
    parts = [p for p in re.split(r"[,，、;；]", value) if p.strip()]
    return len(parts)


def _find_para(paras: list[dict], pattern: re.Pattern) -> dict | None:
    """在段落列表中查找首条匹配正则的段落。"""
    for p in paras:
        if pattern.match((p.get("text") or "").strip()):
            return p
    return None


def _find_cn_keyword(keywords: list[dict]) -> dict | None:
    """宽松定位中文关键词行：文本（去空白后）以「关键词」开头即可。

    不用带冒号的正则定位，否则「关键词」后缺冒号的行会被漏掉，
    误判为关键词缺失而非格式错误。
    """
    for p in keywords:
        if (p.get("text") or "").strip().startswith("关键词"):
            return p
    return None


def _find_en_keyword(keywords: list[dict]) -> dict | None:
    """宽松定位英文关键词行：文本（去空白后）以「Keywords」开头即可。"""
    for p in keywords:
        if (p.get("text") or "").strip().lower().startswith("keywords"):
            return p
    return None


# ===================================================================
#  检查函数
# ===================================================================

def _check_abstract_missing(info: dict | None) -> list[dict]:
    """① 摘要为空。"""
    if info is None or not any(info.get(k) for k in ("title", "body", "keywords")):
        return [
            _build_record(
                "error", "abstract_missing",
                "未检测到摘要内容",
                "论文应包含中英文摘要与关键词",
                "摘要为空（abstract.json 的 items 为空）",
                0, "",
            )
        ]
    return []


def _check_title(title: dict | None) -> list[dict]:
    """②③④⑤ 中文摘要标题「摘要」：黑体三号居中。"""
    errors: list[dict] = []

    if title is None or not (title.get("text") or "").strip():
        errors.append(
            _build_record(
                "error", "abstract_title_missing",
                "未检测到中文摘要标题",
                "中文摘要应有标题「摘要」",
                "摘要标题为空",
                0, "",
            )
        )
        return errors

    text = title.get("text", "")
    idx = title.get("index", 0)
    preview = _truncate(text)
    runs = _para_runs(title)

    # 字体：黑体
    bad_fonts = {_run_font(r) for r in runs} - _FONT_HEITI
    bad_fonts.discard("")
    if bad_fonts:
        errors.append(
            _build_record(
                "error", "abstract_title_font",
                "摘要标题字体不是黑体",
                "中文摘要标题应使用黑体",
                f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                idx, preview,
            )
        )

    # 字号：三号（16pt）
    sizes = [r.get("font_size") for r in runs if r.get("font_size") is not None]
    if sizes and not all(_eq_size(s, PT_SAN_HAO) for s in sizes):
        errors.append(
            _build_record(
                "error", "abstract_title_size",
                "摘要标题字号不是三号",
                "中文摘要标题应为三号（16pt）",
                f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                idx, preview,
            )
        )

    # 对齐：居中
    align = _para_alignment(title)
    if align != "center":
        errors.append(
            _build_record(
                "error", "abstract_title_align",
                "摘要标题未居中",
                "中文摘要标题应居中（alignment == CENTER）",
                f"当前对齐方式为 {_ALIGNMENT_NAMES.get(align.upper(), align)}",
                idx, preview,
            )
        )

    return errors


def _check_abstract_length(cn_paras: list[dict]) -> list[dict]:
    """⑥ 中文摘要字数 300-500。"""
    count = _count_chars(cn_paras)
    if CN_ABSTRACT_MIN <= count <= CN_ABSTRACT_MAX:
        return []
    return [
        _build_record(
            "error", "abstract_length",
            f"中文摘要字数为 {count} 字，不在 {CN_ABSTRACT_MIN}-{CN_ABSTRACT_MAX} 字范围内",
            f"摘要内容以 {CN_ABSTRACT_MIN}-{CN_ABSTRACT_MAX} 字为宜",
            f"当前 {count} 字",
            0, "",
        )
    ]


def _check_body_format(cn_paras: list[dict]) -> list[dict]:
    """⑦⑧ 中文摘要正文：宋体小四。"""
    errors: list[dict] = []
    for p in cn_paras:
        text = (p.get("text") or "").strip()
        if not text:
            continue
        idx = p.get("index", 0)
        preview = _truncate(text)
        runs = _para_runs(p)

        # 字体：宋体
        bad_fonts = {_run_font(r) for r in runs} - _FONT_SONGTI
        bad_fonts.discard("")
        if bad_fonts:
            errors.append(
                _build_record(
                    "error", "abstract_body_font",
                    "摘要正文字体不是宋体",
                    "中文摘要内容应使用宋体",
                    f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                    idx, preview,
                )
            )

        # 字号：小四（12pt）
        sizes = [r.get("font_size") for r in runs if r.get("font_size") is not None]
        if sizes and not all(_eq_size(s, PT_XIAO_SI) for s in sizes):
            errors.append(
                _build_record(
                    "error", "abstract_body_size",
                    "摘要正文字号不是小四",
                    "中文摘要内容应为小四（12pt）",
                    f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                    idx, preview,
                )
            )

    return errors


def _check_cn_keyword(cn_kw: dict | None) -> list[dict]:
    """⑨⑩⑪⑫⑬ 中文关键词：顶格「关键词：」+ 宋体小四 + 3-5 个。"""
    errors: list[dict] = []

    if cn_kw is None:
        errors.append(
            _build_record(
                "error", "keyword_missing",
                "未检测到中文关键词",
                "摘要下方应另起一行顶格打印「关键词」款项后加冒号",
                "未找到中文关键词行",
                0, "",
            )
        )
        return errors

    raw_text = cn_kw.get("text") or ""
    text = raw_text.strip()
    idx = cn_kw.get("index", 0)
    preview = _truncate(text)
    runs = _para_runs(cn_kw)

    # 格式：顶格「关键词」+ 冒号（用原始文本判断是否顶格，不能先 strip）
    if not raw_text.startswith("关键词"):
        errors.append(
            _build_record(
                "error", "keyword_label_format",
                "中文关键词未顶格以「关键词」开头",
                "应顶格打印「关键词」后加冒号",
                f"当前为 {preview}",
                idx, preview,
            )
        )
    elif not _RE_KEYWORD_CN.match(text):
        errors.append(
            _build_record(
                "error", "keyword_label_format",
                "中文关键词「关键词」后缺少冒号",
                "「关键词」款项后应加冒号，如「关键词：」",
                f"当前为 {preview}",
                idx, preview,
            )
        )

    # 加粗：「关键词」标题加粗
    if not any(r.get("bold") for r in runs):
        errors.append(
            _build_record(
                "error", "keyword_label_bold",
                "中文关键词标题「关键词」未加粗",
                "「关键词」应加粗",
                "未检测到加粗 run",
                idx, preview,
            )
        )

    # 字体：宋体
    bad_fonts = {_run_font(r) for r in runs} - _FONT_SONGTI
    bad_fonts.discard("")
    if bad_fonts:
        errors.append(
            _build_record(
                "error", "keyword_font",
                "中文关键词字体不是宋体",
                "中文关键词应使用宋体小四",
                f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                idx, preview,
            )
        )

    # 数量：3-5 个
    count = _count_keywords(text, _RE_KEYWORD_CN)
    if count > 0 and not (KEYWORD_MIN <= count <= KEYWORD_MAX):
        errors.append(
            _build_record(
                "error", "keyword_count",
                f"中文关键词数量为 {count} 个，不在 {KEYWORD_MIN}-{KEYWORD_MAX} 个",
                f"关键词一般列 {KEYWORD_MIN}-{KEYWORD_MAX} 个，以逗号分隔",
                f"当前 {count} 个",
                idx, preview,
            )
        )

    return errors


def _check_english_title(en_title: dict | None) -> list[dict]:
    """⑭⑮ 英文摘要标题「Abstract」：Times New Roman 加粗三号全大写。"""
    errors: list[dict] = []

    if en_title is None:
        errors.append(
            _build_record(
                "error", "english_title_missing",
                "未检测到英文摘要标题",
                "英文摘要应有标题「Abstract」",
                "未找到英文摘要标题",
                0, "",
            )
        )
        return errors

    text = (en_title.get("text") or "").strip()
    idx = en_title.get("index", 0)
    preview = _truncate(text)
    runs = _para_runs(en_title)

    # 全大写
    if text.upper() != text:
        errors.append(
            _build_record(
                "error", "english_title_format",
                "英文摘要标题不是全部大写",
                "英文摘要标题应全部大写，如「ABSTRACT」",
                f"当前为 {preview}",
                idx, preview,
            )
        )

    # 字体：Times New Roman（西文字体，取 font_name）
    bad_fonts = {_run_font(r, use_east_asia=False) for r in runs} - _FONT_TIMES
    bad_fonts.discard("")
    if bad_fonts:
        errors.append(
            _build_record(
                "error", "english_title_format",
                "英文摘要标题字体不是 Times New Roman",
                "英文摘要标题应使用 Times New Roman",
                f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                idx, preview,
            )
        )

    # 字号：三号（16pt）
    sizes = [r.get("font_size") for r in runs if r.get("font_size") is not None]
    if sizes and not all(_eq_size(s, PT_SAN_HAO) for s in sizes):
        errors.append(
            _build_record(
                "error", "english_title_format",
                "英文摘要标题字号不是三号",
                "英文摘要标题应为三号（16pt）",
                f"当前字号为 {'、'.join(str(s) for s in sizes)}pt",
                idx, preview,
            )
        )

    # 加粗
    if runs and not all(r.get("bold") for r in runs):
        errors.append(
            _build_record(
                "error", "english_title_format",
                "英文摘要标题未加粗",
                "英文摘要标题应加粗",
                "未检测到加粗",
                idx, preview,
            )
        )

    return errors


def _check_english_keyword(en_kw: dict | None) -> list[dict]:
    """⑯⑰ 英文关键词「Keywords」：Times New Roman 加粗。"""
    errors: list[dict] = []

    if en_kw is None:
        errors.append(
            _build_record(
                "error", "english_keyword_missing",
                "未检测到英文关键词",
                "英文摘要应包含英文关键词「Keywords:」",
                "未找到英文关键词行",
                0, "",
            )
        )
        return errors

    text = (en_kw.get("text") or "").strip()
    idx = en_kw.get("index", 0)
    preview = _truncate(text)
    runs = _para_runs(en_kw)

    # 字体：Times New Roman（西文字体）
    bad_fonts = {_run_font(r, use_east_asia=False) for r in runs} - _FONT_TIMES
    bad_fonts.discard("")
    if bad_fonts:
        errors.append(
            _build_record(
                "error", "english_keyword_format",
                "英文关键词字体不是 Times New Roman",
                "英文关键词应使用 Times New Roman",
                f"当前字体为 {'、'.join(sorted(bad_fonts))}",
                idx, preview,
            )
        )

    # 加粗：「Keywords」标题加粗
    if not any(r.get("bold") for r in runs):
        errors.append(
            _build_record(
                "error", "english_keyword_format",
                "英文关键词标题「Keywords」未加粗",
                "「Keywords」应加粗",
                "未检测到加粗 run",
                idx, preview,
            )
        )

    return errors


# ===================================================================
#  公共接口
# ===================================================================

def check(abstract_items: list[dict], source_file: str = "") -> dict:
    """对摘要与关键词执行全部格式检查。

    Args:
        abstract_items: abstract.json 的 ``items`` 列表，items[0] 为
                        {title, body, keywords} 结构（title/body/keywords 均为段落 dict）。
        source_file:    来源文件名，仅用于回显。

    Returns:
        符合 abstract.json 模板的检查结果字典。
    """
    info = abstract_items[0] if abstract_items else None

    all_errors: list[dict] = []
    cn_chars = 0
    cn_keyword_count = 0

    all_errors.extend(_check_abstract_missing(info))
    if info is not None:
        title = info.get("title")
        body = info.get("body", [])
        keywords = info.get("keywords", [])

        all_errors.extend(_check_title(title))

        cn_paras, en_paras = _split_body(body)
        all_errors.extend(_check_abstract_length(cn_paras))
        all_errors.extend(_check_body_format(cn_paras))

        cn_kw = _find_cn_keyword(keywords)
        en_kw = _find_en_keyword(keywords)
        all_errors.extend(_check_cn_keyword(cn_kw))

        en_title = _find_para(en_paras, _RE_EN_TITLE)
        all_errors.extend(_check_english_title(en_title))
        all_errors.extend(_check_english_keyword(en_kw))

        cn_chars = _count_chars(cn_paras)
        cn_keyword_count = _count_keywords(
            (cn_kw.get("text") or "") if cn_kw else "", _RE_KEYWORD_CN
        )

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
            "cn_abstract_chars": cn_chars,
            "cn_keyword_count": cn_keyword_count,
        },
        "errors": all_errors,
        "warnings": [],
    }


def run(input_path: str | Path, output_path: str | Path) -> dict:
    """读 abstract.json → 执行 check() → 写 abstract.json。

    Args:
        input_path:  abstract.json 路径。
        output_path: 输出路径，如 output/checker_json/abstract.json。

    Returns:
        检查结果字典（已写入 output_path）。
    """
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


# ===================================================================
#  CLI 入口
# ===================================================================

if __name__ == "__main__":
    import sys

    # 从当前文件位置推算项目根目录（向上 2 级：src/checkers -> src -> 根）
    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    _DEFAULT_INPUT = _PROJECT_ROOT / "output" / "parser_json" / "abstract.json"
    _DEFAULT_OUTPUT = _PROJECT_ROOT / "output" / "checker_json" / "abstract.json"

    input_path = sys.argv[1] if len(sys.argv) > 1 else str(_DEFAULT_INPUT)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(_DEFAULT_OUTPUT)

    result = run(input_path, output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
