"""code_checker 单元测试

使用模拟 references.json 的 items 格式（构造 dict，不依赖真实 docx）。
覆盖 8 项检查 + 边界情况。
"""

import json

import pytest

from src.checkers.references.code_checker import (
    CHECKER_ID,
    CHECKER_NAME,
    check,
    run,
)


# ===================================================================
#  测试数据构造工具
# ===================================================================

def _item(index: int, ref_number: str, text: str,
          alignment: str = "LEFT", para_index: int | None = None) -> dict:
    """构造一条 references.json items 元素。"""
    return {
        "index": index,
        "ref_number": ref_number,
        "para": {
            "index": para_index if para_index is not None else index + 100,
            "text": text,
            "style_name": "",
            "alignment": alignment,
        },
    }


def _clean_refs(n: int = 5) -> list[dict]:
    """构造 n 条格式完全正确的参考文献（[1]..[n]）。"""
    return [
        _item(i, f"[{i}]", f"[{i}] 张三{i}. 测试文献[J]. 期刊, 2024, 10(1): 1-5.")
        for i in range(1, n + 1)
    ]


def _find(result: dict, category: str) -> list[dict]:
    """按 category 过滤结果中的 error/warning 记录。"""
    return [r for r in result["errors"] + result["warnings"] if r["category"] == category]


# ===================================================================
#  干净通过用例
# ===================================================================

class TestCleanPass:
    def test_all_checks_pass(self):
        """格式完全正确的参考文献应全部通过。"""
        result = check(_clean_refs(), source_file="clean.docx")
        assert result["summary"]["status"] == "pass"
        assert result["summary"]["total_errors"] == 0
        assert result["summary"]["total_warnings"] == 0
        assert result["summary"]["ref_count"] == 5

    def test_checker_metadata(self):
        """元信息字段与模板一致。"""
        result = check(_clean_refs(), source_file="论文.docx")
        assert result["checker"] == CHECKER_ID
        assert result["checker_name"] == CHECKER_NAME
        assert result["source_file"] == "论文.docx"
        assert "timestamp" in result
        assert result["errors"] == []
        assert result["warnings"] == []


# ===================================================================
#  8 项检查各一
# ===================================================================

class TestNotLeftAligned:
    def test_center_alignment(self):
        """居中对齐 → not_left_aligned。"""
        items = _clean_refs()
        items[1] = _item(2, "[2]", "[2] 李四. 书籍[M]. 北京: 出版社, 2023.", alignment="CENTER")
        result = check(items)
        errors = _find(result, "not_left_aligned")
        assert len(errors) == 1
        assert errors[0]["ref_index"] == 2
        assert errors[0]["ref_label"] == "[2]"
        assert errors[0]["location"]["paragraph_index"] == 102
        assert "居中" in errors[0]["actual"]

    def test_missing_alignment(self):
        """alignment 缺失（None）→ 默认 UNKNOWN → 报错。"""
        items = _clean_refs()
        items[0]["para"]["alignment"] = None
        result = check(items)
        errors = _find(result, "not_left_aligned")
        assert len(errors) == 1
        assert "UNKNOWN" in errors[0]["actual"]


class TestNoBrackets:
    def test_leading_number(self):
        """行首直接数字 '3.' → no_brackets。"""
        items = _clean_refs()
        items[2] = _item(3, "3.", "3. 王六. 期刊论文[J]. 科学通报, 2024.")
        result = check(items)
        errors = _find(result, "no_brackets")
        assert len(errors) == 1
        assert errors[0]["ref_label"] == "3"
        assert "3." in errors[0]["actual"]

    def test_circle_number(self):
        """圈数字 '①' → no_brackets。"""
        items = _clean_refs()
        items[0] = _item(1, "①", "① 王五. 论文标题[D]. 广州: 中山大学, 2025.")
        result = check(items)
        errors = _find(result, "no_brackets")
        assert len(errors) == 1
        assert errors[0]["ref_label"] == "1"  # 圈数字不可解析，回退位置
        assert "①" in errors[0]["actual"]

    def test_empty_ref_number(self):
        """ref_number 为空 → 回退 text 提取。"""
        items = _clean_refs()
        items[2] = _item(3, "", "3. 王六. 期刊论文[J]. 科学通报, 2024.")
        result = check(items)
        errors = _find(result, "no_brackets")
        assert len(errors) == 1
        assert errors[0]["ref_label"] == "3"
        assert "以数字3开头" in errors[0]["actual"]

    def test_text_fallback_normal(self):
        """ref_number 为空但 text 是 [n] → 不算 no_brackets。"""
        items = _clean_refs()
        items[2] = _item(3, "", "[3] 王六. 期刊论文[J]. 科学通报, 2024.")
        result = check(items)
        errors = _find(result, "no_brackets")
        assert len(errors) == 0


class TestNonNumericBrackets:
    def test_alpha_content(self):
        """[abc] → non_numeric_brackets。"""
        items = _clean_refs()
        items[3] = _item(4, "[abc]", "[abc] 赵七. 会议论文[C]. 北京: 某出版社, 2023.")
        result = check(items)
        errors = _find(result, "non_numeric_brackets")
        assert len(errors) == 1
        assert errors[0]["ref_label"] == "[abc]"
        assert "非数字" in errors[0]["actual"]


class TestNonIntegerNumber:
    def test_decimal_content(self):
        """[2.5] → non_integer_number。"""
        items = _clean_refs()
        items[1] = _item(2, "[2.5]", "[2.5] 孙八. 报告[R]. 2023.")
        result = check(items)
        errors = _find(result, "non_integer_number")
        assert len(errors) == 1
        assert errors[0]["ref_label"] == "[2.5]"
        assert "小数点" in errors[0]["actual"]


class TestNumberingStart:
    def test_start_from_zero(self):
        """第一个编号为 [0] → warning。"""
        items = _clean_refs()
        items[0] = _item(1, "[0]", "[0] 王五. 论文标题[D]. 广州: 中山大学, 2025.")
        result = check(items)
        warnings = _find(result, "numbering_start")
        assert len(warnings) == 1
        assert warnings[0]["severity"] == "warning"
        assert warnings[0]["ref_index"] == 1
        assert warnings[0]["ref_label"] == "[1]"
        assert "第一个编号为[0]" in warnings[0]["actual"]

    def test_start_from_one(self):
        """第一个编号为 [1] → 无 warning。"""
        result = check(_clean_refs())
        assert _find(result, "numbering_start") == []


class TestNumberingGap:
    def test_gap_detected(self):
        """[4]→[6] 跳号缺少 [5] → numbering_gap。"""
        items = _clean_refs()
        items[4] = _item(5, "[6]", "[6] 吴十. 标准[S]. 北京: 标准出版社, 2023.")
        result = check(items)
        errors = _find(result, "numbering_gap")
        assert len(errors) == 1
        assert errors[0]["ref_index"] == 6
        assert "缺少[5]" in errors[0]["description"]
        assert "直接跳到[6]" in errors[0]["description"]
        assert "当前条目编号为[6]" in errors[0]["actual"]

    def test_sequential_no_gap(self):
        """连续编号 → 无 gap。"""
        result = check(_clean_refs())
        assert _find(result, "numbering_gap") == []


class TestNumberingDuplicate:
    def test_duplicate_detected(self):
        """编号 [3] 出现两次 → numbering_duplicate。"""
        items = _clean_refs()
        items[2] = _item(3, "[3]", "[3] 王六. 期刊论文[J]. 科学通报, 2024.")
        items.append(_item(6, "[3]", "[3] 重复的书目. 图书[M]. 上海: 出版社, 2023."))
        result = check(items)
        errors = _find(result, "numbering_duplicate")
        assert len(errors) == 1
        assert errors[0]["ref_index"] == 3
        assert "出现了2次" in errors[0]["description"]
        assert "第3条和第6条" in errors[0]["actual"]

    def test_mixed_bracket_leading(self):
        """无括号 '3.' 与 '[3]' 也算重复编号。"""
        items = _clean_refs()
        items[2] = _item(3, "3.", "3. 王六. 期刊论文[J]. 科学通报, 2024.")
        items.append(_item(6, "[3]", "[3] 重复的书目. 图书[M]. 上海: 出版社, 2023."))
        result = check(items)
        errors = _find(result, "numbering_duplicate")
        assert len(errors) == 1


class TestNoTrailingPeriod:
    def test_missing_period(self):
        """末尾无句点 → no_trailing_period。"""
        items = _clean_refs()
        items[4] = _item(5, "[5]", "[5] 周九. 论文集[C]. 北京: 某出版社, 2022")
        result = check(items)
        errors = _find(result, "no_trailing_period")
        assert len(errors) == 1
        assert errors[0]["ref_label"] == "[5]"
        assert "句点" in errors[0]["description"]

    def test_whitespace_after_period(self):
        """末尾空格后句点 → 不算缺失。"""
        items = _clean_refs()
        items[0]["para"]["text"] = "[1] 张三. 测试文献[J]. 期刊, 2024.   "
        result = check(items)
        assert _find(result, "no_trailing_period") == []


# ===================================================================
#  边界情况
# ===================================================================

class TestEdgeCases:
    def test_empty_items(self):
        """空 items → pass，ref_count=0。"""
        result = check([], source_file="empty.docx")
        assert result["summary"]["status"] == "pass"
        assert result["summary"]["ref_count"] == 0
        assert result["errors"] == []

    def test_missing_para(self):
        """para 为 None → 兜底处理不崩溃。"""
        items = [{"index": 1, "ref_number": "[1]", "para": None}]
        result = check(items)
        assert result["summary"]["ref_count"] == 1

    def test_para_missing_keys(self):
        """para 缺字段 → 兜底。"""
        items = [{"index": 1, "ref_number": "[1]", "para": {}}]
        result = check(items)
        assert result["summary"]["ref_count"] == 1

    def test_empty_ref_number_no_text(self):
        """ref_number 与 text 均无法提取编号 → 不参与连续性检查。"""
        items = [
            _item(1, "", "张三. 测试文献[J]. 期刊, 2024."),
            _item(2, "", "李四. 测试文献[J]. 期刊, 2024."),
        ]
        result = check(items)
        assert _find(result, "numbering_gap") == []
        assert _find(result, "numbering_duplicate") == []

    def test_unicode_alignment(self):
        """alignment 小写/异常值不崩溃。"""
        items = _clean_refs()
        items[0]["para"]["alignment"] = "left"
        result = check(items)
        # .upper() 处理后 LEFT 不报错
        assert _find(result, "not_left_aligned") == []


# ===================================================================
#  run() 端到端
# ===================================================================

class TestRun:
    def test_run_end_to_end(self, tmp_path):
        """run() 读文件 → 检查 → 写输出文件。"""
        data = {
            "file_name": "测试论文.docx",
            "unit": "references",
            "count": 2,
            "items": _clean_refs(2),
        }
        input_path = tmp_path / "references.json"
        output_path = tmp_path / "ref_code.json"
        input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        result = run(input_path, output_path)

        assert result["summary"]["status"] == "pass"
        assert output_path.exists()
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert saved["checker"] == CHECKER_ID
        assert saved["source_file"] == "测试论文.docx"
        assert saved["summary"]["ref_count"] == 2

    def test_run_missing_items_key(self, tmp_path):
        """缺少 items 键 → 不崩溃。"""
        data = {"file_name": "x.docx", "unit": "references"}
        input_path = tmp_path / "references.json"
        output_path = tmp_path / "ref_code.json"
        input_path.write_text(json.dumps(data), encoding="utf-8")

        result = run(input_path, output_path)
        assert result["summary"]["status"] == "pass"
        assert result["summary"]["ref_count"] == 0
