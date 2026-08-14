"""abstract_checker 单元测试

使用模拟 abstract.json 的 items 格式（构造 dict，不依赖真实 docx）。
覆盖 17 项检查 + 边界情况。
"""

import json

import pytest

from src.checkers.abstract_checker import (
    CHECKER_ID,
    CHECKER_NAME,
    check,
    run,
)


# ===================================================================
#  测试数据构造工具
# ===================================================================

def _run(font_name: str | None = None, east_asia: str | None = None,
         font_size: float | None = None, bold: bool | None = None) -> dict:
    """构造一个 run（仅含非空字段，与 parser 的 _clean_dict 一致）。"""
    r: dict = {}
    if font_name is not None:
        r["font_name"] = font_name
    if east_asia is not None:
        r["east_asia_font"] = east_asia
    if font_size is not None:
        r["font_size"] = font_size
    if bold is not None:
        r["bold"] = bold
    return r


def _para(index: int, text: str, font_name: str = "Times New Roman",
          east_asia: str = "宋体", font_size: float = 12.0,
          alignment: str | None = None, bold: bool | None = None) -> dict:
    """构造一个摘要段落。"""
    p: dict = {"index": index, "text": text, "style_name": ""}
    if alignment is not None:
        p["alignment"] = alignment
    p["runs"] = [_run(font_name, east_asia, font_size, bold)]
    return p


def _cn(n: int) -> str:
    """生成 n 个中文字符的摘要正文。"""
    return "研" * n


def _clean_abstract() -> list[dict]:
    """构造完全合规的中英文摘要与关键词。"""
    info = {
        "title": _para(0, "摘要", east_asia="黑体", font_size=16.0, alignment="CENTER"),
        "body": [
            _para(1, _cn(320), east_asia="宋体", font_size=12.0),
            _para(2, "ABSTRACT", east_asia="宋体", font_size=16.0, bold=True),
            _para(3, "This is the English abstract content.", east_asia="宋体", font_size=12.0),
        ],
        "keywords": [
            _para(4, "关键词：深度学习，图像识别，卷积神经网络", east_asia="宋体", font_size=12.0, bold=True),
            _para(5, "Keywords: Deep Learning; Image Recognition; CNN", east_asia="宋体", font_size=12.0, bold=True),
        ],
    }
    return [info]


def _find(result: dict, category: str) -> list[dict]:
    """按 category 过滤结果中的 error 记录。"""
    return [r for r in result["errors"] + result["warnings"] if r["category"] == category]


# ===================================================================
#  干净通过用例
# ===================================================================

class TestCleanPass:
    def test_all_checks_pass(self):
        result = check(_clean_abstract(), source_file="clean.docx")
        assert result["summary"]["status"] == "pass"
        assert result["summary"]["total_errors"] == 0
        assert result["summary"]["cn_abstract_chars"] == 320
        assert result["summary"]["cn_keyword_count"] == 3

    def test_checker_metadata(self):
        result = check(_clean_abstract(), source_file="论文.docx")
        assert result["checker"] == CHECKER_ID
        assert result["checker_name"] == CHECKER_NAME
        assert result["source_file"] == "论文.docx"
        assert "timestamp" in result
        assert result["errors"] == []
        assert result["warnings"] == []


# ===================================================================
#  中文摘要标题检查
# ===================================================================

class TestTitle:
    def test_missing_title(self):
        info = _clean_abstract()[0]
        info["title"] = None
        result = check([info])
        errors = _find(result, "abstract_title_missing")
        assert len(errors) == 1

    def test_wrong_font(self):
        info = _clean_abstract()[0]
        info["title"] = _para(0, "摘要", east_asia="宋体", font_size=16.0, alignment="CENTER")
        result = check([info])
        errors = _find(result, "abstract_title_font")
        assert len(errors) == 1
        assert "宋体" in errors[0]["actual"]

    def test_wrong_size(self):
        info = _clean_abstract()[0]
        info["title"] = _para(0, "摘要", east_asia="黑体", font_size=14.0, alignment="CENTER")
        result = check([info])
        errors = _find(result, "abstract_title_size")
        assert len(errors) == 1
        assert "14.0" in errors[0]["actual"]

    def test_wrong_align(self):
        info = _clean_abstract()[0]
        info["title"] = _para(0, "摘要", east_asia="黑体", font_size=16.0, alignment="LEFT")
        result = check([info])
        errors = _find(result, "abstract_title_align")
        assert len(errors) == 1
        assert "左对齐" in errors[0]["actual"]


# ===================================================================
#  中文摘要正文检查
# ===================================================================

class TestAbstractBody:
    def test_too_short(self):
        info = _clean_abstract()[0]
        info["body"] = [
            _para(1, _cn(100), east_asia="宋体", font_size=12.0),
            _para(2, "ABSTRACT", east_asia="宋体", font_size=16.0, bold=True),
        ]
        result = check([info])
        errors = _find(result, "abstract_length")
        assert len(errors) == 1
        assert "100 字" in errors[0]["actual"]

    def test_wrong_font(self):
        info = _clean_abstract()[0]
        info["body"][0] = _para(1, _cn(320), east_asia="黑体", font_size=12.0)
        result = check([info])
        errors = _find(result, "abstract_body_font")
        assert len(errors) == 1
        assert "黑体" in errors[0]["actual"]

    def test_wrong_size(self):
        info = _clean_abstract()[0]
        info["body"][0] = _para(1, _cn(320), east_asia="宋体", font_size=16.0)
        result = check([info])
        errors = _find(result, "abstract_body_size")
        assert len(errors) == 1
        assert "16.0" in errors[0]["actual"]


# ===================================================================
#  中文关键词检查
# ===================================================================

class TestCnKeyword:
    def test_missing(self):
        info = _clean_abstract()[0]
        info["keywords"] = [_para(5, "Keywords: A; B; C", bold=True)]
        result = check([info])
        errors = _find(result, "keyword_missing")
        assert len(errors) == 1

    def test_label_format_no_colon(self):
        info = _clean_abstract()[0]
        info["keywords"][0] = _para(4, "关键词深度学习，图像识别，卷积神经网络", bold=True)
        result = check([info])
        errors = _find(result, "keyword_label_format")
        assert len(errors) == 1

    def test_label_not_top_aligned(self):
        info = _clean_abstract()[0]
        info["keywords"][0] = _para(4, "  关键词：深度学习，图像识别，卷积神经网络", bold=True)
        result = check([info])
        errors = _find(result, "keyword_label_format")
        assert len(errors) == 1

    def test_label_not_bold(self):
        info = _clean_abstract()[0]
        info["keywords"][0] = _para(4, "关键词：深度学习，图像识别，卷积神经网络", bold=None)
        result = check([info])
        errors = _find(result, "keyword_label_bold")
        assert len(errors) == 1

    def test_wrong_font(self):
        info = _clean_abstract()[0]
        info["keywords"][0] = _para(4, "关键词：深度学习，图像识别，卷积神经网络", east_asia="黑体", bold=True)
        result = check([info])
        errors = _find(result, "keyword_font")
        assert len(errors) == 1
        assert "黑体" in errors[0]["actual"]

    def test_too_few_keywords(self):
        info = _clean_abstract()[0]
        info["keywords"][0] = _para(4, "关键词：深度学习，图像识别", bold=True)
        result = check([info])
        errors = _find(result, "keyword_count")
        assert len(errors) == 1
        assert "2 个" in errors[0]["actual"]


# ===================================================================
#  英文摘要检查
# ===================================================================

class TestEnglish:
    def test_title_missing(self):
        info = _clean_abstract()[0]
        info["body"] = [_para(1, _cn(320), east_asia="宋体", font_size=12.0)]
        result = check([info])
        errors = _find(result, "english_title_missing")
        assert len(errors) == 1

    def test_title_not_uppercase(self):
        info = _clean_abstract()[0]
        info["body"][1] = _para(2, "Abstract", east_asia="宋体", font_size=16.0, bold=True)
        result = check([info])
        errors = _find(result, "english_title_format")
        assert any("大写" in e["description"] for e in errors)

    def test_title_wrong_font(self):
        info = _clean_abstract()[0]
        info["body"][1] = _para(2, "ABSTRACT", font_name="Arial", east_asia="宋体", font_size=16.0, bold=True)
        result = check([info])
        errors = _find(result, "english_title_format")
        assert any("Times New Roman" in e["description"] for e in errors)

    def test_keyword_missing(self):
        info = _clean_abstract()[0]
        info["keywords"] = [_para(4, "关键词：深度学习，图像识别，卷积神经网络", bold=True)]
        result = check([info])
        errors = _find(result, "english_keyword_missing")
        assert len(errors) == 1

    def test_keyword_not_bold(self):
        info = _clean_abstract()[0]
        info["keywords"][1] = _para(5, "Keywords: Deep Learning; CNN", bold=None)
        result = check([info])
        errors = _find(result, "english_keyword_format")
        assert any("加粗" in e["description"] for e in errors)


# ===================================================================
#  边界情况
# ===================================================================

class TestEdgeCases:
    def test_empty_items(self):
        result = check([], source_file="empty.docx")
        assert _find(result, "abstract_missing")
        assert result["summary"]["status"] == "fail"

    def test_info_missing_keys(self):
        result = check([{}])
        assert _find(result, "abstract_missing")

    def test_para_no_runs(self):
        """段落无 runs → 字体/字号不判，仅对齐检查，不崩溃。"""
        info = _clean_abstract()[0]
        info["title"] = {"index": 0, "text": "摘要", "style_name": "",
                         "alignment": "CENTER", "runs": []}
        result = check([info])
        assert _find(result, "abstract_title_font") == []
        assert _find(result, "abstract_title_size") == []


# ===================================================================
#  run() 端到端
# ===================================================================

class TestRun:
    def test_run_end_to_end(self, tmp_path):
        """run() 读 abstract.json → 检查 → 写输出文件。"""
        data = {"file_name": "测试论文.docx", "unit": "abstract",
                "count": 1, "items": _clean_abstract()}
        input_path = tmp_path / "abstract.json"
        output_path = tmp_path / "checker" / "abstract.json"
        input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        result = run(input_path, output_path)

        assert result["summary"]["status"] == "pass"
        assert output_path.exists()
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert saved["checker"] == CHECKER_ID
        assert saved["source_file"] == "测试论文.docx"
        assert saved["summary"]["cn_abstract_chars"] == 320

    def test_run_missing_items_key(self, tmp_path):
        """缺少 items 键 → 不崩溃，返回 abstract_missing。"""
        data = {"file_name": "x.docx", "unit": "abstract"}
        input_path = tmp_path / "abstract.json"
        output_path = tmp_path / "checker" / "abstract.json"
        input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        result = run(input_path, output_path)
        assert result["summary"]["status"] == "fail"
        assert _find(result, "abstract_missing")
