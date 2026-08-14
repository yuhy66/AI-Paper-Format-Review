"""
论文拆解单元定义、状态机状态与识别规则。

定义：
- ParseState: 顺序状态机的 6 个状态（按论文自然结构顺序）
- UnitType: 7 个最终归类单元
- 中间数据结构（dataclass），每个均带 to_dict() 序列化方法
- UnitRecognitionRules: 状态切换边界信号的识别规则
"""

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Any

# ============================================================
# 枚举：状态机状态 + 最终归类单元
# ============================================================

class ParseState(Enum):
    """顺序状态机的状态 —— 按论文自然行文顺序排列"""
    COVER = "cover"
    STATEMENT = "statement"          # 学术诚信声明 
    TITLE_PAGE = "title_page"
    ABSTRACT = "abstract"
    TOC = "toc"
    BODY = "body"
    REFERENCES = "references"


class UnitType(Enum):
    """论文文档的最终归类单元"""
    COVER = "cover"
    STATEMENT = "statement"          # 声明（学术诚信/原创性/版权授权等）
    TITLE_PAGE = "title_page"
    ABSTRACT = "abstract"
    HEADING = "heading"
    FIGURE_TABLE = "figure_table"
    BODY = "body"
    REFERENCES = "references"


# ============================================================
# 序列化工具
# ============================================================

def _to_plain(obj: Any) -> Any:
    """递归将 dataclass / Enum 转为纯 Python 字典 / 字符串 / 数字"""
    if obj is None:
        return None
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, list):
        return [_to_plain(v) for v in obj]
    if isinstance(obj, dict):
        return {_to_plain(k): _to_plain(v) for k, v in obj.items()}
    return obj


def _clean_dict(d: dict) -> dict:
    """去除值为 None 的键，保持 JSON 输出简洁"""
    return {k: v for k, v in d.items() if v is not None}


# ============================================================
# 中间数据结构
# ============================================================

@dataclass
class RunInfo:
    """一个 run 的格式信息（python-docx 中段落内的最小格式单元）"""
    text: str
    font_name: Optional[str] = None         # 西文字体（w:ascii / w:hAnsi）
    east_asia_font: Optional[str] = None    # 中文字体（w:eastAsia），宋体/黑体等
    font_size: Optional[float] = None       # 磅值 pt
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None

    def to_dict(self) -> dict:
        return _clean_dict(asdict(self))


@dataclass
class InlineImageInfo:
    """段落内嵌图片信息（从 docx XML 的 w:drawing/wp:inline 提取）"""
    name: str = ""                          # 图片名称（来自 wp:docPr）
    file_name: str = ""                     # 图片文件名，如 "media/image1.emf"
    width_cm: Optional[float] = None        # 宽度 cm
    height_cm: Optional[float] = None       # 高度 cm

    def to_dict(self) -> dict:
        return _clean_dict({
            "name": self.name,
            "file_name": self.file_name,
            "width_cm": self.width_cm,
            "height_cm": self.height_cm,
        })


@dataclass
class ParaInfo:
    """一个段落的完整格式信息，供所有审查模块使用"""
    index: int
    text: str
    style_name: str = ""
    alignment: Optional[str] = None         # LEFT / CENTER / RIGHT / JUSTIFY
    line_spacing: Optional[float] = None    # 磅值 pt
    space_before: Optional[float] = None    # 段前间距 pt
    space_after: Optional[float] = None     # 段后间距 pt
    first_line_indent: Optional[float] = None  # 首行缩进 pt
    runs: list[RunInfo] = field(default_factory=list)
    images: list[InlineImageInfo] = field(default_factory=list)  # 段落内嵌图片
    state: Optional[ParseState] = None      # 状态机归类标记

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value if self.state else None
        run_dicts = [r.to_dict() for r in self.runs]
        # 单 run 段落：run.text == para.text，省略 run 中的 text
        if len(run_dicts) == 1:
            run_dicts[0].pop("text", None)
        d["runs"] = run_dicts
        d["images"] = [img.to_dict() for img in self.images] if self.images else []
        return _clean_dict(d)


@dataclass
class HeadingInfo:
    """章节标题信息"""
    level: int                              # 1=一级标题, 2=二级标题...
    number: str = ""                        # 编号文本，如 "一、"、"1.1"
    text: str = ""                          # 标题文字（去除编号）
    para: Optional[ParaInfo] = None

    def to_dict(self) -> dict:
        d = _clean_dict({
            "level": self.level,
            "number": self.number,
            "para": self.para.to_dict() if self.para else None,
        })
        # text 与 para.text 重复，不输出到 JSON
        return d


@dataclass
class FigureTableInfo:
    """图 / 表 / 公式的题注信息"""
    category: str                           # "figure" | "table" | "formula"
    number: str = ""
    caption: str = ""
    para: Optional[ParaInfo] = None

    def to_dict(self) -> dict:
        d = _clean_dict({
            "category": self.category,
            "number": self.number,
            "para": self.para.to_dict() if self.para else None,
        })
        # caption 与 para.text 重复，不输出到 JSON
        return d


@dataclass
class AbstractInfo:
    """摘要部分（支持中英双摘要+双关键词）"""
    title_para: Optional[ParaInfo] = None
    body_paras: list[ParaInfo] = field(default_factory=list)
    keywords_labels: list[ParaInfo] = field(default_factory=list)  # 中/英文关键词各一行

    def to_dict(self) -> dict:
        return _clean_dict({
            "title": self.title_para.to_dict() if self.title_para else None,
            "body": [p.to_dict() for p in self.body_paras],
            "keywords": [p.to_dict() for p in self.keywords_labels] if self.keywords_labels else [],
        })


@dataclass
class ReferenceInfo:
    """单条参考文献"""
    index: int
    ref_number: str = ""                    # 如 "[1]"
    text: str = ""
    para: Optional[ParaInfo] = None

    def to_dict(self) -> dict:
        d = _clean_dict({
            "index": self.index,
            "ref_number": self.ref_number,
            "para": self.para.to_dict() if self.para else None,
        })
        # text 与 para.text 重复，不输出到 JSON
        return d


@dataclass
class PageSettings:
    """页面设置（从 docx 第一节提取）"""
    width_cm: Optional[float] = None        # 页面宽度 cm
    height_cm: Optional[float] = None       # 页面高度 cm
    top_margin_cm: Optional[float] = None   # 上边距 cm
    bottom_margin_cm: Optional[float] = None  # 下边距 cm
    left_margin_cm: Optional[float] = None  # 左边距 cm
    right_margin_cm: Optional[float] = None # 右边距 cm
    orientation: str = "portrait"           # portrait / landscape

    def to_dict(self) -> dict:
        return _clean_dict({
            "width_cm": self.width_cm,
            "height_cm": self.height_cm,
            "top_margin_cm": self.top_margin_cm,
            "bottom_margin_cm": self.bottom_margin_cm,
            "left_margin_cm": self.left_margin_cm,
            "right_margin_cm": self.right_margin_cm,
            "orientation": self.orientation,
        })


@dataclass
class HeaderFooterPart:
    """单个页眉或页脚的段落列表"""
    paragraphs: list[ParaInfo] = field(default_factory=list)
    is_linked_to_previous: bool = True   # 是否链接到上一节（"Link to Previous"）

    def to_dict(self) -> dict:
        return _clean_dict({
            "paragraphs": [p.to_dict() for p in self.paragraphs],
            "is_linked_to_previous": self.is_linked_to_previous,
        })


@dataclass
class SectionHeaderFooter:
    """一个节的页眉页脚信息（每节可有 3 种页眉 + 3 种页脚）"""
    section_index: int = 0
    header_default: HeaderFooterPart = field(default_factory=HeaderFooterPart)
    header_first: Optional[HeaderFooterPart] = None     # 首页页眉（仅当 different_first_page=True）
    header_even: Optional[HeaderFooterPart] = None      # 偶数页页眉（仅当 even_and_odd_pages=True）
    footer_default: HeaderFooterPart = field(default_factory=HeaderFooterPart)
    footer_first: Optional[HeaderFooterPart] = None     # 首页页脚
    footer_even: Optional[HeaderFooterPart] = None      # 偶数页页脚
    different_first_page: bool = False
    even_and_odd_pages: bool = False

    def to_dict(self) -> dict:
        return _clean_dict({
            "section_index": self.section_index,
            "different_first_page": self.different_first_page,
            "even_and_odd_pages": self.even_and_odd_pages,
            "header_default": self.header_default.to_dict(),
            "header_first": self.header_first.to_dict() if self.header_first else None,
            "header_even": self.header_even.to_dict() if self.header_even else None,
            "footer_default": self.footer_default.to_dict(),
            "footer_first": self.footer_first.to_dict() if self.footer_first else None,
            "footer_even": self.footer_even.to_dict() if self.footer_even else None,
        })


@dataclass
class ParsedDocument:
    """解析后的完整论文结构化数据"""
    file_name: str = ""
    page_settings: Optional[PageSettings] = None
    headers_footers: list[SectionHeaderFooter] = field(default_factory=list)
    units: dict[UnitType, list] = field(default_factory=dict)

    # ---- 快捷属性 ----

    @property
    def cover_paras(self) -> list[ParaInfo]:
        return self.units.get(UnitType.COVER, [])

    @property
    def statement_paras(self) -> list[ParaInfo]:
        return self.units.get(UnitType.STATEMENT, [])

    @property
    def title_page_paras(self) -> list[ParaInfo]:
        return self.units.get(UnitType.TITLE_PAGE, [])

    @property
    def abstract(self) -> Optional[AbstractInfo]:
        items = self.units.get(UnitType.ABSTRACT, [])
        return items[0] if items else None

    @property
    def headings(self) -> list[HeadingInfo]:
        return self.units.get(UnitType.HEADING, [])

    @property
    def figures_tables(self) -> list[FigureTableInfo]:
        return self.units.get(UnitType.FIGURE_TABLE, [])

    @property
    def body_paras(self) -> list[ParaInfo]:
        return self.units.get(UnitType.BODY, [])

    @property
    def references(self) -> list[ReferenceInfo]:
        return self.units.get(UnitType.REFERENCES, [])

    # ---- 序列化 ----

    def to_dict(self) -> dict:
        """转为纯字典，键使用 UnitType 的字符串值"""
        result_units: dict[str, list] = {}
        for unit_type, items in self.units.items():
            result_units[unit_type.value] = [_to_plain(item) for item in items]
        return {
            "file_name": self.file_name,
            "page": self.page_settings.to_dict() if self.page_settings else None,
            "headers_footers": _to_plain(self.headers_footers),
            "units": result_units,
        }

    def to_json(self, indent: int = 2, ensure_ascii: bool = False) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=ensure_ascii)

    def save_json(self, output_dir: str | Path) -> list[Path]:
        """
        将 7 个单元分别保存为独立的 JSON 文件。

        输出目录下生成：
            cover.json       — 封面段落
            title_page.json  — 扉页段落
            abstract.json    — 摘要（标题+正文+关键词）
            heading.json     — 章节标题列表
            figure_table.json — 图/表/公式题注列表
            body.json        — 正文段落
            references.json  — 参考文献条目

        返回保存的文件路径列表。
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 单元 → 文件名
        unit_files = {
            UnitType.COVER: "cover.json",
            UnitType.STATEMENT: "statement.json",
            UnitType.TITLE_PAGE: "title_page.json",
            UnitType.ABSTRACT: "abstract.json",
            UnitType.HEADING: "heading.json",
            UnitType.FIGURE_TABLE: "figure_table.json",
            UnitType.BODY: "body.json",
            UnitType.REFERENCES: "references.json",
        }

        saved: list[Path] = []
        for unit_type, filename in unit_files.items():
            items = self.units.get(unit_type, [])
            data = {
                "file_name": self.file_name,
                "unit": unit_type.value,
                "count": len(items),
                "page": self.page_settings.to_dict() if self.page_settings else None,
                "headers_footers": _to_plain(self.headers_footers),
                "items": [_to_plain(item) for item in items],
            }
            file_path = output_dir / filename
            file_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            saved.append(file_path)

        return saved


# ============================================================
# 识别规则
# ============================================================

@dataclass
class UnitRecognitionRules:
    """
    状态机边界信号的识别规则。

    规则分两类：
    1. 样式名匹配 — 段落 docx 样式名是否匹配
    2. 内容正则匹配 — 段落文本是否匹配正则
    """

    # ============ 摘要边界 ============
    abstract_heading_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*摘\s*要\s*$",
        r"^\s*摘要\s*$",
    ])
    keywords_label_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*关键词[：:]\s*",
        r"^\s*關鍵詞[：:]\s*",
        r"^\s*Keywords\s*[：:]\s*",
    ])

    # ============ 目录边界 ============
    toc_heading_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*目\s*录\s*$",
        r"^\s*目錄\s*$",
        r"^\s*Table\s+of\s+Contents\s*$",
    ])
    # 目录内容行识别：章节标题 + 省略号/点线 + 页码
    toc_content_patterns: list[str] = field(default_factory=lambda: [
        r".*[\.…]{3,}\s*\d+\s*$",           # 一、绪论 ...... 1
        r".*\.{2,}\s*\d+\s*$",              # 1.1 .... 3
    ])

    # ============ 参考文献边界 ============
    reference_heading_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*参考文献\s*$",
        r"^\s*參考文獻\s*$",
        r"^\s*References\s*$",
    ])
    reference_entry_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*\[\d+(?:[,，]\s*\d+)*\]",
        r"^\s*[①②③④⑤⑥⑦⑧⑨⑩]\s",
    ])

    # ============ 声明边界（封面 → 声明的触发信号） ============
    statement_keywords: list[str] = field(default_factory=lambda: [
        "学术诚信声明", "诚信声明",
        "原创性声明", "独创性声明", "知识产权声明",
        "论文独创性声明",
        "Declaration",
    ])

    # ============ 扉页边界（声明 → 扉页的触发信号） ============
    title_page_keywords: list[str] = field(default_factory=lambda: [
        "版权使用授权书", "学位论文版权使用授权书",
        "论文使用授权声明",
        "Copyright",
    ])
    # 声明正文 + 签名日期结束后，出现以下字段表示进入扉页
    title_page_field_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*题目\s*[：:]?\s*$",           # "题目" 或 "题目："
        r"^\s*论文题目\s*[：:]?\s*$",        # "论文题目："
        r"^\s*Title\s*[：:]?\s*$",          # "Title" 或 "Title："
    ])

    # ============ 正文边界（进入 BODY 状态的触发信号） ============
    chapter_heading_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*第[一二三四五六七八九十\d]+章\s",
        r"^\s*[一二三四五六七八九十]+[、．.\s]",
        r"^\s*绪\s*论\s*$",
        r"^\s*緒\s*論\s*$",
        r"^\s*引\s*言\s*$",
        r"^\s*前\s*言\s*$",
        r"^\s*Introduction\s*$",
        r"^\s*结\s*论\s*$",
        r"^\s*結\s*論\s*$",
        r"^\s*Conclusion\s*$",
    ])

    # ============ 章节标题（BODY 内部的 HEADING 子分类） ============
    heading_style_patterns: list[str] = field(default_factory=lambda: [
        r"^Heading\s*\d+$",
        r"^标题\s*\d+$",
        r"^toc\s*\d+$",
    ])
    heading_level_patterns: dict[int, list[str]] = field(default_factory=lambda: {
        1: [
            r"^\s*第[一二三四五六七八九十\d]+章",
            r"^\s*[一二三四五六七八九十]+[、．.\s]",
            r"^\s*绪\s*论\s*$", r"^\s*引\s*言\s*$", r"^\s*前\s*言\s*$",
            r"^\s*结\s*论\s*$", r"^\s*結\s*論\s*$",
        ],
        2: [
            r"^\s*\(\s*[一二三四五六七八九十]+\s*\)",   # (一) / (二)
            r"^\s*（\s*[一二三四五六七八九十]+\s*）",   # （一）/ （二）全角括号
        ],
        3: [r"^\s*\d+[\.、]\s*"],
        4: [
            r"^\s*\(\s*\d+\s*\)",                       # (1) / (2)
            r"^\s*（\s*\d+\s*）",                       # （1）/ （2）全角括号
        ],
    })

    # ============ 参考文献之后的附录/致谢（→ 切回 BODY） ============
    post_reference_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*致\s*谢\s*$",
        r"^\s*謝\s*辭\s*$",
        r"^\s*Acknowledgements?\s*$",
        r"^\s*附\s*录\s*$",
        r"^\s*附\s*錄\s*$",
        r"^\s*Appendix\s*$",
    ])

    # ============ 图 / 表 / 公式题注 ============
    figure_caption_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*(图|圖|Fig\.?|Figure)\s*\d+[\.\-]?\d*",
    ])
    table_caption_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*(表|Table)\s*\d+[\.\-]?\d*",
    ])
    formula_caption_patterns: list[str] = field(default_factory=lambda: [
        r"^\s*(公式|式|Equation|Eq\.?)\s*\(?\d+[\.\-]?\d*\)?",
    ])


# 默认规则实例
DEFAULT_RULES = UnitRecognitionRules()
