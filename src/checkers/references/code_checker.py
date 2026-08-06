"""参考文献编号格式检查器

检查论文参考文献的编号格式完整性，8 项独立检查：
  ① not_left_aligned     — 段落未左顶格对齐（error）
  ② no_brackets          — 行首缺少方括号编号（error）
  ③ non_numeric_brackets — 方括号内不是数字（error）
  ④ non_integer_number   — 方括号内编号含小数点（error）
  ⑤ numbering_start      — 第一个编号不是 [1]（warning）
  ⑥ numbering_gap        — 编号跳号（error）
  ⑦ numbering_duplicate  — 编号重复（error）
  ⑧ no_trailing_period   — 末尾缺少句点（error）

输入: output/parser_json/references.json（文档拆解团队输出，模板见
      output/templates/references.json）
输出: output/checker_json/ref_code.json（模板已固定）
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CHECKER_ID = "ref_code"
CHECKER_NAME = "参考文献编号顺序检查"

# ── 正则模式 ──────────────────────────────────────────────
RE_BRACKET_ANY = re.compile(r"^\[([^\]]*)\]\s*")      # 匹配 [任意内容]
RE_LEADING_NUM = re.compile(r"^(\d+)[\.\s)]?\s*")     # 匹配行首数字（无方括号）

# ── 对齐方式中文映射 ──────────────────────────────────────
_ALIGNMENT_NAMES: dict[str, str] = {
    "LEFT": "左对齐",
    "CENTER": "居中",
    "RIGHT": "右对齐",
    "JUSTIFY": "两端对齐",
}

# ── 类型别名 ─────────────────────────────────────────────
RefEntry = dict[str, Any]


# ===================================================================
#  工具函数
# ===================================================================

def _truncate(text: str, max_len: int = 80) -> str:
    """将文本截断至 max_len 字符，超长尾部追加 ...。"""
    text = text.replace("\n", " ").replace("\r", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _build_record(
    severity: str,
    category: str,
    ref_index: int,
    ref_label: str,
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
        "ref_index": ref_index,
        "ref_label": ref_label,
        "description": description,
        "expected": expected,
        "actual": actual,
        "location": {
            "paragraph_index": paragraph_index,
            "text_preview": text_preview,
        },
    }


# ===================================================================
#  提取阶段
# ===================================================================

def _extract_ref_entries(items: list[dict]) -> list[RefEntry]:
    """从 references.json 的 items 列表解析出每条参考文献的元信息。

    对每条 item：
      1. 优先解析 item["ref_number"]（parser 已提取的引用标记，如 '[1]'）
      2. ref_number 为空时回退到从 para.text 正则提取
      3. alignment 取自 para.alignment，缺省 UNKNOWN

    提取字段：
      position, paragraph_index, text, alignment,
      ref_index, ref_label, ref_number_raw,
      has_bracket_pair, bracket_content,
      is_numeric_bracket, is_integer_bracket,
      has_valid_number, ends_with_period
    """
    entries: list[RefEntry] = []

    for idx, item in enumerate(items, start=1):
        para = item.get("para") or {}
        text = para.get("text", "").strip()
        alignment = para.get("alignment", "UNKNOWN") or "UNKNOWN"
        para_index = para.get("index", idx)
        ref_number = item.get("ref_number", "").strip()

        entry: RefEntry = {
            "position": idx,               # 1-based 顺序位置（fallback）
            "paragraph_index": para_index,
            "text": text,
            "alignment": alignment,
            "ref_index": idx,              # 优先从编号中提取
            "ref_label": str(idx),
            "ref_number_raw": ref_number,  # parser 提供的原始引用标记
            "has_bracket_pair": False,
            "bracket_content": None,
            "is_numeric_bracket": False,   # 方括号内容是否为数值
            "is_integer_bracket": False,   # 方括号内容是否为整数
            "has_valid_number": False,     # 是否提取到有效整数编号（无论有无方括号）
            "ends_with_period": text.rstrip().endswith("."),
        }

        # ── 1. 优先解析 ref_number ──
        if ref_number:
            _parse_ref_number(entry, ref_number)

        # ── 2. 回退：ref_number 为空且未提取到数字时，从 text 提取 ──
        if not entry["has_bracket_pair"] and not entry["has_valid_number"]:
            _parse_from_text(entry, text)

        entries.append(entry)

    return entries


def _parse_ref_number(entry: RefEntry, ref_number: str) -> None:
    """解析引用标记 ref_number，如 '[1]' / '[abc]' / '[2.5]' / '①' / '1.'。

    方括号 [数字] → 提取整数编号
    方括号 [小数] → 标记非整数
    方括号 [非数字] → 标记非数字括号
    其他格式（圈数字、纯数字等）→ 保持无方括号状态，由 no_brackets 检查捕获
    """
    content = ref_number.strip()

    # ── 方括号形式 [xxx] ──
    if content.startswith("[") and content.endswith("]"):
        inner = content[1:-1]
        entry["has_bracket_pair"] = True
        entry["bracket_content"] = inner
        entry["ref_label"] = f"[{inner}]"

        if inner.isdigit():
            # 纯整数: [3]
            entry["is_numeric_bracket"] = True
            entry["is_integer_bracket"] = True
            entry["has_valid_number"] = True
            parsed = int(inner)
            entry["ref_index"] = parsed
            entry["ref_label"] = f"[{parsed}]"
        elif _is_single_decimal(inner):
            # 含小数点: [2.5]
            entry["is_numeric_bracket"] = True
            entry["is_integer_bracket"] = False
            # ref_index 保留 position 值，不误覆盖
        # 否则: 非数字括号格式，各项保持默认
        return

    # ── 非方括号格式：尝试行首数字（如 '3' / '3.' / '3)'）──
    m_num = RE_LEADING_NUM.match(content)
    if m_num:
        entry["ref_index"] = int(m_num.group(1))
        entry["ref_label"] = m_num.group(1)
        entry["has_valid_number"] = True
    # 圈数字（①、②…）等其他格式：无方括号状态，由 no_brackets 检查捕获


def _parse_from_text(entry: RefEntry, text: str) -> None:
    """回退逻辑：从段落文本提取编号（ref_number 缺失时的兜底）。"""
    if not text:
        return
    m_bracket = RE_BRACKET_ANY.match(text)
    if m_bracket:
        content = m_bracket.group(1)
        entry["has_bracket_pair"] = True
        entry["bracket_content"] = content
        entry["ref_label"] = f"[{content}]"

        if content.isdigit():
            entry["is_numeric_bracket"] = True
            entry["is_integer_bracket"] = True
            entry["has_valid_number"] = True
            parsed = int(content)
            entry["ref_index"] = parsed
            entry["ref_label"] = f"[{parsed}]"
        elif _is_single_decimal(content):
            entry["is_numeric_bracket"] = True
            entry["is_integer_bracket"] = False
        return

    # 无方括号 → 行首数字
    m_num = RE_LEADING_NUM.match(text)
    if m_num:
        entry["ref_index"] = int(m_num.group(1))
        entry["ref_label"] = m_num.group(1)
        entry["has_valid_number"] = True


def _is_single_decimal(s: str) -> bool:
    """判断字符串是否为最多一个小数点的数值形式（如 '2.5' / '.5' / '5.'）。"""
    return s.count(".") == 1 and s.replace(".", "", 1).isdigit()


# ===================================================================
#  8 项检查函数
# ===================================================================

def _check_not_left_aligned(entries: list[RefEntry]) -> list[dict]:
    """① 左顶格对齐检查。"""
    errors: list[dict] = []
    for e in entries:
        if not e["text"]:
            continue
        align = e["alignment"].upper()
        if align == "LEFT":
            continue
        align_name = _ALIGNMENT_NAMES.get(align, e["alignment"])
        errors.append(
            _build_record(
                severity="error",
                category="not_left_aligned",
                ref_index=e["ref_index"],
                ref_label=e["ref_label"],
                description=f"参考文献{e['ref_label']}未左顶格：段落对齐方式为{align_name}，应为左对齐",
                expected="序号应左顶格（paragraph.alignment == LEFT）",
                actual=f"当前对齐方式为 {align_name}",
                paragraph_index=e["paragraph_index"],
                text_preview=_truncate(e["text"]),
            )
        )
    return errors


def _check_no_brackets(entries: list[RefEntry]) -> list[dict]:
    """② 方括号编号检查。"""
    errors: list[dict] = []
    for e in entries:
        if not e["text"]:
            continue
        if e["has_bracket_pair"]:
            continue
        if e["ref_number_raw"]:
            actual_detail = f"当前引用标记为 {e['ref_number_raw']}，不是[数字]方括号格式"
        else:
            m = RE_LEADING_NUM.match(e["text"])
            actual_detail = (
                f"当前行首直接以数字{m.group(1)}开头，无方括号"
                if m
                else "当前条目缺少引用标记（ref_number 为空）"
            )
        errors.append(
            _build_record(
                severity="error",
                category="no_brackets",
                ref_index=e["ref_index"],
                ref_label=e["ref_label"],
                description="参考文献条目未使用方括号编号：行首缺少[数字]格式",
                expected="每条参考文献编号应使用方括号括起，如 [3]",
                actual=actual_detail,
                paragraph_index=e["paragraph_index"],
                text_preview=_truncate(e["text"]),
            )
        )
    return errors


def _check_non_numeric_brackets(entries: list[RefEntry]) -> list[dict]:
    """③ 方括号内非数字检查。"""
    errors: list[dict] = []
    for e in entries:
        if not e["text"]:
            continue
        if e["has_bracket_pair"] and not e["is_numeric_bracket"]:
            errors.append(
                _build_record(
                    severity="error",
                    category="non_numeric_brackets",
                    ref_index=e["ref_index"],
                    ref_label=e["ref_label"],
                    description="参考文献编号方括号内不是数字",
                    expected="方括号内应为整数编号，如 [4]",
                    actual=f"当前编号为 {e['ref_label']}，包含非数字字符",
                    paragraph_index=e["paragraph_index"],
                    text_preview=_truncate(e["text"]),
                )
            )
    return errors


def _check_non_integer_number(entries: list[RefEntry]) -> list[dict]:
    """④ 方括号内编号含小数点检查。"""
    errors: list[dict] = []
    for e in entries:
        if not e["text"]:
            continue
        if e["has_bracket_pair"] and e["is_numeric_bracket"] and not e["is_integer_bracket"]:
            errors.append(
                _build_record(
                    severity="error",
                    category="non_integer_number",
                    ref_index=e["ref_index"],
                    ref_label=e["ref_label"],
                    description="参考文献编号不是整数",
                    expected="编号应为正整数",
                    actual=f"当前编号为 {e['ref_label']}，包含小数点",
                    paragraph_index=e["paragraph_index"],
                    text_preview=_truncate(e["text"]),
                )
            )
    return errors


def _check_numbering_start(entries: list[RefEntry]) -> list[dict]:
    """⑤ 编号起始检查（warning）：第一个整数编号必须为 1。"""
    valid = [e for e in entries if e["has_valid_number"]]
    if not valid:
        return []
    first = valid[0]
    if first["ref_index"] != 1:
        return [
            _build_record(
                severity="warning",
                category="numbering_start",
                ref_index=1,
                ref_label="[1]",
                description="参考文献列表第一个编号不是[1]",
                expected="参考文献编号应从[1]开始",
                actual=f"第一个编号为[{first['ref_index']}]",
                paragraph_index=first["paragraph_index"],
                text_preview=_truncate(first["text"]),
            )
        ]
    return []


def _check_numbering_gap(entries: list[RefEntry]) -> list[dict]:
    """⑥ 编号跳号检查。"""
    valid = [e for e in entries if e["has_valid_number"]]
    if len(valid) < 2:
        return []
    errors: list[dict] = []
    for i in range(1, len(valid)):
        prev = valid[i - 1]
        curr = valid[i]
        if curr["ref_index"] - prev["ref_index"] <= 1:
            continue
        errors.append(
            _build_record(
                severity="error",
                category="numbering_gap",
                ref_index=curr["ref_index"],
                ref_label=curr["ref_label"],
                description=(
                    f"参考文献编号跳号：序号从"
                    f"[{prev['ref_index']}]直接跳到[{curr['ref_index']}]，"
                    f"缺少[{prev['ref_index'] + 1}]"
                ),
                expected="编号应严格从[1]开始连续递增，不允许跳号",
                actual=(
                    f"前一个有效序号为[{prev['ref_index']}]，"
                    f"当前条目编号为[{curr['ref_index']}]"
                ),
                paragraph_index=curr["paragraph_index"],
                text_preview=_truncate(curr["text"]),
            )
        )
    return errors


def _check_numbering_duplicate(entries: list[RefEntry]) -> list[dict]:
    """⑦ 编号重复检查。"""
    seen: dict[int, list[RefEntry]] = {}
    for e in entries:
        if e["has_valid_number"]:
            seen.setdefault(e["ref_index"], []).append(e)

    errors: list[dict] = []
    for num, same_entries in seen.items():
        if len(same_entries) < 2:
            continue
        first_e = same_entries[0]
        second_e = same_entries[1]
        errors.append(
            _build_record(
                severity="error",
                category="numbering_duplicate",
                ref_index=num,
                ref_label=f"[{num}]",
                description=f"参考文献编号重复：编号[{num}]出现了{len(same_entries)}次",
                expected="每个编号在参考文献列表中唯一",
                actual=f"第{first_e['position']}条和第{second_e['position']}条使用相同的编号[{num}]",
                paragraph_index=second_e["paragraph_index"],
                text_preview=_truncate(second_e["text"]),
            )
        )
    return errors


def _check_no_trailing_period(entries: list[RefEntry]) -> list[dict]:
    """⑧ 末尾句点检查。"""
    errors: list[dict] = []
    for e in entries:
        if not e["text"]:
            continue
        if not e["ends_with_period"]:
            errors.append(
                _build_record(
                    severity="error",
                    category="no_trailing_period",
                    ref_index=e["ref_index"],
                    ref_label=e["ref_label"],
                    description=f"参考文献{e['ref_label']}末尾缺少句点'.'结束符",
                    expected="每一条参考文献的结尾应用'.'号标识",
                    actual="当前条目末尾无句点",
                    paragraph_index=e["paragraph_index"],
                    text_preview=_truncate(e["text"]),
                )
            )
    return errors


# ===================================================================
#  公共接口
# ===================================================================

def check(items: list[dict], source_file: str = "") -> dict:
    """对参考文献 items 列表执行全部 8 项检查。

    Args:
        items: references.json 中 ``items`` 列表，每项包含
               index / ref_number / para（para 内含 text / alignment / index）。
        source_file: 来源文件名，仅用于回显。

    Returns:
        符合 ref_code.json 模板的检查结果字典。

    Example::

        result = check([
            {"index": 1, "ref_number": "[1]",
             "para": {"index": 100, "text": "[1] 张三. 书[M]. 北京: 出版社, 2025.",
                      "alignment": "LEFT"}},
        ])
        print(result["summary"]["status"])   # "pass" | "fail"
    """
    # ── 空列表兜底 ──
    if not items:
        now = datetime.now().isoformat()
        return {
            "checker": CHECKER_ID,
            "checker_name": CHECKER_NAME,
            "timestamp": now,
            "source_file": source_file,
            "summary": {
                "status": "pass",
                "total_errors": 0,
                "total_warnings": 0,
                "ref_count": 0,
            },
            "errors": [],
            "warnings": [],
        }

    # ── 提取 → 逐一检查 ──
    entries = _extract_ref_entries(items)

    all_errors: list[dict] = []
    all_warnings: list[dict] = []

    all_errors.extend(_check_not_left_aligned(entries))
    all_errors.extend(_check_no_brackets(entries))
    all_errors.extend(_check_non_numeric_brackets(entries))
    all_errors.extend(_check_non_integer_number(entries))
    all_warnings.extend(_check_numbering_start(entries))
    all_errors.extend(_check_numbering_gap(entries))
    all_errors.extend(_check_numbering_duplicate(entries))
    all_errors.extend(_check_no_trailing_period(entries))

    total_errors = len(all_errors)
    total_warnings = len(all_warnings)
    ref_count = len(entries)
    status = "pass" if (total_errors == 0 and total_warnings == 0) else "fail"

    now = datetime.now().isoformat()
    return {
        "checker": CHECKER_ID,
        "checker_name": CHECKER_NAME,
        "timestamp": now,
        "source_file": source_file,
        "summary": {
            "status": status,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "ref_count": ref_count,
        },
        "errors": all_errors,
        "warnings": all_warnings,
    }


def run(input_path: str | Path, output_path: str | Path) -> dict:
    """读 references.json → 执行 check() → 写 ref_code.json。

    Args:
        input_path: references.json 路径。
        output_path: ref_code.json 输出路径。

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

    # 从当前文件位置推算项目根目录（向上 4 级）
    _PROJECT_ROOT = Path(__file__).resolve().parents[4]
    _DEFAULT_INPUT = _PROJECT_ROOT / "output" / "parser_json" / "references.json"
    _DEFAULT_OUTPUT = _PROJECT_ROOT / "output" / "checker_json" / "ref_code.json"

    input_path = sys.argv[1] if len(sys.argv) > 1 else str(_DEFAULT_INPUT)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(_DEFAULT_OUTPUT)

    result = run(input_path, output_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
