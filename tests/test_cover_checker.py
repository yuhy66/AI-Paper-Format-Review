"""cover_checker 单元测试

使用模拟 cover.json / title_page.json / statement.json 的 items 格式（构造 dict，
不依赖真实 docx）。覆盖 12 项检查 + 边界情况。
"""

import json

import pytest

from src.checkers.cover_checker import (
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
          east_asia: str = "宋体", font_size: float = 14.0,
          alignment: str | None = None, bold: bool | None = None) -> dict:
    """构造一个封面/扉页段落。"""
    p: dict = {"index": index, "text": text, "style_name": ""}
    if alignment is not None:
        p["alignment"] = alignment
    p["runs"] = [_run(font_name, east_asia, font_size, bold)]
    return p


def _title_para(index: int, text: str, east_asia: str = "黑体",
                font_size: float = 22.0, alignment: str = "CENTER") -> dict:
    """构造论文题目段落（黑体二号居中）。"""
    return _para(index, text, east_asia=east_asia, font_size=font_size, alignment=alignment)


def _page(width: float = 21.0, height: float = 29.7, top: float = 2.5,
          bottom: float = 2.0, left: float = 3.0, right: float = 3.0) -> dict:
    """构造页面设置（单位 cm）。"""
    return {
        "width_cm": width, "height_cm": height,
        "top_margin_cm": top, "bottom_margin_cm": bottom,
        "left_margin_cm": left, "right_margin_cm": right,
        "orientation": "portrait",
    }


def _clean_cover() -> list[dict]:
    return [
        _title_para(0, "基于深度学习的图像识别方法研究"),
        _para(1, "院系专业：计算机学院"),
        _para(2, "姓名学号：张三 2023001"),
        _para(3, "指导教师：李四 教授"),
    ]


def _clean_title_page() -> list[dict]:
    return [
        _title_para(10, "基于深度学习的图像识别方法研究"),
        _title_para(11, "Image Recognition Based on Deep Learning"),
        _para(12, "姓名 张三"),
        _para(13, "学号 2023001"),
        _para(14, "院系 计算机学院"),
        _para(15, "专业 计算机科学与技术"),
        _para(16, "指导教师 李四 教授"),
    ]


def _clean_statement() -> list[dict]:
    return [
        _para(20, "学术诚信声明", east_asia="黑体", font_size=16.0, alignment="CENTER"),
        _para(21, "本人郑重声明：所呈交的毕业论文是本人在导师指导下独立完成的。"),
    ]


def _find(result: dict, category: str) -> list[dict]:
    """按 category 过滤结果中的 error/warning 记录。"""
    return [r for r in result["errors"] + result["warnings"] if r["category"] == category]


# ===================================================================
#  干净通过用例
# ===================================================================

class TestCleanPass:
    def test_all_checks_pass(self):
        result = check(_clean_cover(), _clean_title_page(), _clean_statement(),
                       _page(), source_file="clean.docx")
        assert result["summary"]["status"] == "pass"
        assert result["summary"]["total_errors"] == 0
        assert result["summary"]["total_warnings"] == 0

    def test_checker_metadata(self):
        result = check(_clean_cover(), _clean_title_page(), _clean_statement(),
                       _page(), source_file="论文.docx")
        assert result["checker"] == CHECKER_ID
        assert result["checker_name"] == CHECKER_NAME
        assert result["source_file"] == "论文.docx"
        assert "timestamp" in result
        assert result["errors"] == []
        assert result["warnings"] == []


# ===================================================================
#  封面检查
# ===================================================================

class TestCoverEmpty:
    def test_empty_cover(self):
        result = check([], _clean_title_page(), _clean_statement(), _page())
        errors = _find(result, "cover_empty")
        assert len(errors) == 1
        assert errors[0]["severity"] == "error"


class TestCoverMissingField:
    def test_missing_advisor(self):
        cover = [p for p in _clean_cover() if "指导教师" not in p["text"]]
        result = check(cover, _clean_title_page(), _clean_statement(), _page())
        errors = _find(result, "cover_missing_field")
        assert len(errors) == 1
        assert "指导教师" in errors[0]["description"]

    def test_all_fields_present(self):
        result = check(_clean_cover(), _clean_title_page(), _clean_statement(), _page())
        assert _find(result, "cover_missing_field") == []


class TestCoverTitle:
    def test_too_long(self):
        cover = _clean_cover()
        cover[0] = _title_para(0, "研" * 30)
        result = check(cover, _clean_title_page(), _clean_statement(), _page())
        errors = _find(result, "cover_title_too_long")
        assert len(errors) == 1
        assert "30 字" in errors[0]["actual"]

    def test_wrong_font(self):
        cover = _clean_cover()
        cover[0] = _title_para(0, "基于深度学习的图像识别方法研究", east_asia="宋体")
        result = check(cover, _clean_title_page(), _clean_statement(), _page())
        errors = _find(result, "cover_title_font")
        assert len(errors) == 1
        assert "宋体" in errors[0]["actual"]

    def test_wrong_size(self):
        cover = _clean_cover()
        cover[0] = _title_para(0, "基于深度学习的图像识别方法研究", font_size=16.0)
        result = check(cover, _clean_title_page(), _clean_statement(), _page())
        errors = _find(result, "cover_title_size")
        assert len(errors) == 1
        assert "16.0" in errors[0]["actual"]

    def test_wrong_align(self):
        cover = _clean_cover()
        cover[0] = _title_para(0, "基于深度学习的图像识别方法研究", alignment="LEFT")
        result = check(cover, _clean_title_page(), _clean_statement(), _page())
        errors = _find(result, "cover_title_align")
        assert len(errors) == 1
        assert "左对齐" in errors[0]["actual"]


# ===================================================================
#  扉页检查
# ===================================================================

class TestTitlePage:
    def test_empty_title_page(self):
        result = check(_clean_cover(), [], _clean_statement(), _page())
        errors = _find(result, "title_page_empty")
        assert len(errors) == 1

    def test_missing_field(self):
        tp = [p for p in _clean_title_page() if "专业" not in p["text"]]
        result = check(_clean_cover(), tp, _clean_statement(), _page())
        errors = _find(result, "title_page_missing_field")
        assert len(errors) == 1
        assert "专业" in errors[0]["description"]


# ===================================================================
#  声明 / 页面检查
# ===================================================================

class TestStatement:
    def test_missing_statement(self):
        result = check(_clean_cover(), _clean_title_page(), [], _page())
        warnings = _find(result, "statement_missing")
        assert len(warnings) == 1
        assert warnings[0]["severity"] == "warning"

    def test_statement_present(self):
        result = check(_clean_cover(), _clean_title_page(), _clean_statement(), _page())
        assert _find(result, "statement_missing") == []


class TestPage:
    def test_not_a4(self):
        result = check(_clean_cover(), _clean_title_page(), _clean_statement(),
                       _page(width=20.0, height=28.0))
        errors = _find(result, "page_not_a4")
        assert len(errors) == 1
        assert "20.0" in errors[0]["actual"]

    def test_wrong_margin(self):
        result = check(_clean_cover(), _clean_title_page(), _clean_statement(),
                       _page(top=3.0))
        errors = _find(result, "page_margin")
        assert len(errors) == 1
        assert "上边距" in errors[0]["description"]

    def test_page_none_skipped(self):
        result = check(_clean_cover(), _clean_title_page(), _clean_statement(), None)
        assert _find(result, "page_not_a4") == []
        assert _find(result, "page_margin") == []


# ===================================================================
#  边界情况
# ===================================================================

class TestEdgeCases:
    def test_all_empty(self):
        """全部为空 → cover_empty + title_page_empty + statement_missing。"""
        result = check([], [], [], None, source_file="empty.docx")
        assert _find(result, "cover_empty")
        assert _find(result, "title_page_empty")
        assert _find(result, "statement_missing")
        assert result["summary"]["status"] == "fail"

    def test_para_no_runs(self):
        """段落无 runs → 字体/字号不判，仅对齐检查，不崩溃。"""
        cover = [{"index": 0, "text": "标题", "style_name": "", "alignment": "CENTER",
                  "runs": []}]
        result = check(cover, _clean_title_page(), _clean_statement(), _page())
        assert _find(result, "cover_title_font") == []
        assert _find(result, "cover_title_size") == []


# ===================================================================
#  run() 端到端
# ===================================================================

class TestRun:
    def test_run_end_to_end(self, tmp_path):
        """run() 读三个 JSON → 检查 → 写输出文件。"""
        cover_data = {"file_name": "测试论文.docx", "unit": "cover",
                      "count": 1, "page": _page(), "items": _clean_cover()}
        tp_data = {"file_name": "测试论文.docx", "unit": "title_page",
                   "count": 1, "items": _clean_title_page()}
        st_data = {"file_name": "测试论文.docx", "unit": "statement",
                   "count": 1, "items": _clean_statement()}

        (tmp_path / "cover.json").write_text(json.dumps(cover_data, ensure_ascii=False), encoding="utf-8")
        (tmp_path / "title_page.json").write_text(json.dumps(tp_data, ensure_ascii=False), encoding="utf-8")
        (tmp_path / "statement.json").write_text(json.dumps(st_data, ensure_ascii=False), encoding="utf-8")

        output_path = tmp_path / "checker" / "cover.json"
        result = run(tmp_path, output_path)

        assert result["summary"]["status"] == "pass"
        assert output_path.exists()
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert saved["checker"] == CHECKER_ID
        assert saved["source_file"] == "测试论文.docx"
        assert saved["summary"]["cover_count"] == 4

    def test_run_missing_json_files(self, tmp_path):
        """目录下缺少 JSON → 不崩溃，返回 fail（封面/扉页/声明为空）。"""
        output_path = tmp_path / "checker" / "cover.json"
        result = run(tmp_path, output_path)
        assert result["summary"]["status"] == "fail"
        assert output_path.exists()
