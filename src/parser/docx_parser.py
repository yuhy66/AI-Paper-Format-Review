"""
论文 DOCX 文档主解析器。

按论文自然行文顺序，使用状态机一次遍历所有段落，
依次识别：封面 → 扉页 → 摘要 → 目录 → 正文 → 参考文献。

状态机原理：
    COVER ─(声明关键词)→ TITLE_PAGE ─(摘要标题)→ ABSTRACT
      │                      │
      └──(摘要标题)──→ ABSTRACT（跳过扉页）

    ABSTRACT ─(目录标题)→ TOC ─(章节标题)→ BODY
       │                    │
       └──(章节标题)──→ BODY（跳过目录）

    BODY ─(参考文献标题)→ REFERENCES（终态）

容错机制：
    解析前自动校验输入文件：
    - 文件是否存在
    - 扩展名是否为 .docx
    - 文件是否为有效的 ZIP 压缩包（docx 本质是 ZIP）
    - ZIP 内是否包含 docx 必需的核心文件
    - python-docx 是否能成功打开文档
    任一校验失败均抛出 ValueError / FileNotFoundError 并附带中文提示。

用法：
    from src.parser.docx_parser import parse_docx, parse_and_save

    paper = parse_docx("论文.docx")                     # 返回 ParsedDocument
    paper.save_json("output/parser_json/")              # 输出 7 个 JSON 文件

    # 或一步到位
    parse_and_save("论文.docx", "output/parser_json/")
"""

import re
import zipfile
from pathlib import Path
from typing import Optional
from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from src.parser.unit_defs import (
    AbstractInfo,
    FigureTableInfo,
    HeaderFooterPart,
    HeadingInfo,
    InlineImageInfo,
    PageSettings,
    ParaInfo,
    ParsedDocument,
    ParseState,
    ReferenceInfo,
    RunInfo,
    SectionHeaderFooter,
    UnitRecognitionRules,
    UnitType,
    DEFAULT_RULES,
)

# XML namespace for image extraction
_NSMAP = {
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}
_EMU_PER_CM = 360000

# ============================================================
# 对齐方式映射
# ============================================================

_ALIGNMENT_MAP = {
    WD_ALIGN_PARAGRAPH.LEFT: "LEFT",
    WD_ALIGN_PARAGRAPH.CENTER: "CENTER",
    WD_ALIGN_PARAGRAPH.RIGHT: "RIGHT",
    WD_ALIGN_PARAGRAPH.JUSTIFY: "JUSTIFY",
}


# ============================================================
# 格式提取
# ============================================================

def _extract_run_info(run: Run) -> RunInfo:
    """提取单个 run 的格式信息"""
    font = run.font

    # 中文字体（w:eastAsia）：python-docx 的 font.name 只返回西文字体（ascii/hAnsi），
    # 中文论文需要单独读 eastAsia 才能拿到宋体/黑体等中文字体名
    east_asia = None
    r_pr = run._element.rPr
    if r_pr is not None and r_pr.rFonts is not None:
        east_asia = r_pr.rFonts.get(qn("w:eastAsia"))

    return RunInfo(
        text=run.text,
        font_name=font.name if font.name else None,
        east_asia_font=east_asia,
        font_size=font.size.pt if font.size else None,
        bold=font.bold if font.bold is not None else None,
        italic=font.italic if font.italic is not None else None,
        underline=font.underline if font.underline is not None else None,
    )


def _is_meaningful_run(run: RunInfo) -> bool:
    """判断 run 是否有实质内容，用于过滤域代码残留（fldChar / instrText）"""
    # 有可见文本 → 保留
    if run.text:
        return True
    # 有激活的格式属性 → 保留（如下划线占位符）
    if run.bold is True or run.italic is True or run.underline is True:
        return True
    # 空文本且无激活格式 → 域代码残留，过滤
    return False


def _extract_para_info(para: Paragraph, index: int) -> ParaInfo:
    """从 python-docx 段落对象提取完整格式信息"""
    pf = para.paragraph_format

    # 行距：Pt 值（固定行距）或浮点数（倍数）
    line_spacing = None
    if pf.line_spacing is not None:
        try:
            line_spacing = pf.line_spacing.pt
        except (ValueError, AttributeError):
            try:
                line_spacing = float(pf.line_spacing)
            except (ValueError, TypeError):
                pass

    space_before = pf.space_before.pt if pf.space_before else None
    space_after = pf.space_after.pt if pf.space_after else None

    first_line_indent = None
    if pf.first_line_indent is not None:
        try:
            first_line_indent = pf.first_line_indent.pt
        except (ValueError, AttributeError):
            pass

    runs = [_extract_run_info(r) for r in para.runs]
    runs = [r for r in runs if _is_meaningful_run(r)]

    return ParaInfo(
        index=index,
        text=para.text.strip(),
        style_name=para.style.name if para.style else "",
        alignment=_ALIGNMENT_MAP.get(para.alignment) if para.alignment else None,
        line_spacing=line_spacing,
        space_before=space_before,
        space_after=space_after,
        first_line_indent=first_line_indent,
        runs=runs,
    )


# ============================================================
# 规则匹配工具
# ============================================================

def _match_any(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text):
            return True
    return False


def _match_heading_style(style_name: str, rules: UnitRecognitionRules) -> bool:
    return _match_any(style_name, rules.heading_style_patterns)


def _parse_heading_level_from_style(style_name: str) -> int:
    """从样式名提取层级，如 'Heading 2' → 2，默认返回 1"""
    m = re.search(r"(\d+)$", style_name)
    return int(m.group(1)) if m else 1


# ============================================================
# 边界信号检测
# ============================================================

def _is_abstract_heading(text: str, rules: UnitRecognitionRules) -> bool:
    return _match_any(text, rules.abstract_heading_patterns)


def _is_toc_heading(text: str, rules: UnitRecognitionRules) -> bool:
    return _match_any(text, rules.toc_heading_patterns)


def _is_reference_heading(text: str, rules: UnitRecognitionRules) -> bool:
    return _match_any(text, rules.reference_heading_patterns)


def _is_statement_signal(text: str, rules: UnitRecognitionRules) -> bool:
    """检测声明关键词 → 触发 COVER → STATEMENT 切换"""
    return _match_any(text, rules.statement_keywords)


def _is_title_page_signal(text: str, rules: UnitRecognitionRules) -> bool:
    """检测扉页关键词/字段 → 触发 STATEMENT → TITLE_PAGE 切换"""
    if _match_any(text, rules.title_page_keywords):
        return True
    if _match_any(text, rules.title_page_field_patterns):
        return True
    return False


def _is_chapter_start(text: str, style_name: str, rules: UnitRecognitionRules) -> bool:
    """
    检测是否为一章开头 → 触发进入 BODY 状态。
    依据：Heading 1 样式 或 文本匹配一级标题模式（第一章 / 一、/ 绪论等）
    """
    if style_name and re.search(r"(Heading|标题)\s*1$", style_name, re.IGNORECASE):
        return True
    if _match_any(text, rules.chapter_heading_patterns):
        return True
    return False


def _is_keywords_label(text: str, rules: UnitRecognitionRules) -> bool:
    return _match_any(text, rules.keywords_label_patterns)


def _is_toc_content(text: str, rules: UnitRecognitionRules) -> bool:
    """检测段落文本是否为目录内容行（含省略号+页码），用于触发 ABSTRACT → TOC"""
    # 多行文本逐行检查：只要有一行匹配目录模式，就认为是目录内容
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if _match_any(line, rules.toc_content_patterns):
            return True
    return False


def _is_post_reference(text: str, rules: UnitRecognitionRules) -> bool:
    """检测致谢/附录标题 → 触发 REFERENCES 之后的切换"""
    return _match_any(text, rules.post_reference_patterns)


# ============================================================
# 状态机核心
# ============================================================

def _next_state(
    current: ParseState,
    text: str,
    style_name: str,
    rules: UnitRecognitionRules,
) -> Optional[ParseState]:
    """
    给定当前状态 + 段落内容，判断是否需要切换到下一个状态。
    返回新状态如果需要切换；返回 None 表示保持当前状态。
    只允许向前切换。
    """
    if current == ParseState.COVER:
        # 封面 → 声明（学术诚信声明等）
        if _is_statement_signal(text, rules):
            return ParseState.STATEMENT
        # 封面 → 摘要（跳过声明和扉页）
        if _is_abstract_heading(text, rules):
            return ParseState.ABSTRACT
        return None

    if current == ParseState.STATEMENT:
        # 声明 → 扉页（版权授权书等）
        if _is_title_page_signal(text, rules):
            return ParseState.TITLE_PAGE
        # 声明 → 摘要（跳过扉页）
        if _is_abstract_heading(text, rules):
            return ParseState.ABSTRACT
        return None

    if current == ParseState.TITLE_PAGE:
        if _is_abstract_heading(text, rules):
            return ParseState.ABSTRACT
        return None

    if current == ParseState.ABSTRACT:
        # TOC 内容检测优先于章节标题检测（目录行也包含标题关键词）
        if _is_toc_heading(text, rules) or _is_toc_content(text, rules):
            return ParseState.TOC
        if _is_chapter_start(text, style_name, rules):
            return ParseState.BODY
        return None

    if current == ParseState.TOC:
        # 在目录区内，如果当前行依然像目录内容，留在 TOC
        if _is_toc_content(text, rules):
            return None
        # 真正的章节标题出现 → 进入正文
        if _is_chapter_start(text, style_name, rules):
            return ParseState.BODY
        return None

    if current == ParseState.BODY:
        if _is_reference_heading(text, rules):
            return ParseState.REFERENCES
        return None

    if current == ParseState.REFERENCES:
        # 参考文献之后出现致谢/附录 → 切回 BODY
        if _is_post_reference(text, rules):
            return ParseState.BODY
        return None


# ============================================================
# 页面设置提取
# ============================================================

def _extract_page_settings(doc: DocxDocument) -> PageSettings:
    """从 docx 第一节提取页面设置"""
    try:
        section = doc.sections[0]
        return PageSettings(
            width_cm=round(section.page_width / _EMU_PER_CM, 2) if section.page_width else None,
            height_cm=round(section.page_height / _EMU_PER_CM, 2) if section.page_height else None,
            top_margin_cm=round(section.top_margin / _EMU_PER_CM, 2) if section.top_margin else None,
            bottom_margin_cm=round(section.bottom_margin / _EMU_PER_CM, 2) if section.bottom_margin else None,
            left_margin_cm=round(section.left_margin / _EMU_PER_CM, 2) if section.left_margin else None,
            right_margin_cm=round(section.right_margin / _EMU_PER_CM, 2) if section.right_margin else None,
            orientation="portrait" if section.orientation is None else "landscape" if str(section.orientation).endswith("LANDSCAPE") else "portrait",
        )
    except (IndexError, AttributeError):
        return PageSettings()


# ============================================================
# 页眉页脚提取
# ============================================================

def _extract_header_footer_part(part, doc: DocxDocument) -> Optional[HeaderFooterPart]:
    """
    提取单个页眉或页脚对象中的段落列表。

    python-docx 的 Header/Footer 对象：
      - .paragraphs: 段落列表（同 Paragraph 类型）
      - .is_linked_to_previous: 是否链接到上一节

    处理：
      - 跳过 .is_linked_to_previous=True 的节（内容从上一节继承，不重复提取）
      - 跳过完全没有文本和图片的空段落
      - 复用 _extract_para_info() 和 _extract_images_from_para()
    """
    if part is None:
        return None
    if part.is_linked_to_previous:
        return None

    paras: list[ParaInfo] = []
    for i, p in enumerate(part.paragraphs):
        info = _extract_para_info(p, i)
        info.images = _extract_images_from_para(p, doc)
        # 跳过完全没有文本和图片的空段落
        if not info.text.strip() and not info.images:
            continue
        paras.append(info)

    return HeaderFooterPart(
        paragraphs=paras,
        is_linked_to_previous=False,
    )


def _section_has_content(hf: SectionHeaderFooter) -> bool:
    """判断节是否有实质页眉/页脚内容需要保留"""
    # 有特殊页面设置 → 保留
    if hf.different_first_page or hf.even_and_odd_pages:
        return True
    # 任意页眉/页脚有段落内容 → 保留
    for part in (hf.header_default, hf.header_first, hf.header_even,
                 hf.footer_default, hf.footer_first, hf.footer_even):
        if part and part.paragraphs:
            return True
    # 无内容且无特殊设置 → 过滤
    return False


def _extract_headers_footers(doc: DocxDocument) -> list[SectionHeaderFooter]:
    """
    提取文档所有节的页眉/页脚内容与格式。

    每节最多提取 6 种页眉/页脚：
      - header_default / footer_default  （始终存在）
      - header_first / footer_first       （different_first_page_header_footer=True 时）
      - header_even / footer_even         （even_and_odd_pages_header_footer=True 时）
    """
    result: list[SectionHeaderFooter] = []

    for si, section in enumerate(doc.sections):
        hf = SectionHeaderFooter(section_index=si)

        # 读取节属性
        try:
            hf.different_first_page = bool(section.different_first_page_header_footer)
        except Exception:
            hf.different_first_page = False

        try:
            hf.even_and_odd_pages = bool(section.even_and_odd_pages_header_footer)
        except Exception:
            hf.even_and_odd_pages = False

        # 默认页眉/页脚
        try:
            hf.header_default = _extract_header_footer_part(section.header, doc) or HeaderFooterPart()
        except Exception:
            hf.header_default = HeaderFooterPart()

        try:
            hf.footer_default = _extract_header_footer_part(section.footer, doc) or HeaderFooterPart()
        except Exception:
            hf.footer_default = HeaderFooterPart()

        # 首页页眉/页脚
        if hf.different_first_page:
            try:
                hf.header_first = _extract_header_footer_part(section.first_page_header, doc)
            except Exception:
                hf.header_first = None
            try:
                hf.footer_first = _extract_header_footer_part(section.first_page_footer, doc)
            except Exception:
                hf.footer_first = None

        # 偶数页页眉/页脚
        if hf.even_and_odd_pages:
            try:
                hf.header_even = _extract_header_footer_part(section.even_page_header, doc)
            except Exception:
                hf.header_even = None
            try:
                hf.footer_even = _extract_header_footer_part(section.even_page_footer, doc)
            except Exception:
                hf.footer_even = None

        result.append(hf)

    # 过滤：去除无内容且完全继承的冗余节
    result = [hf for hf in result if _section_has_content(hf)]

    return result


# ============================================================
# 图片提取
# ============================================================

def _extract_images_from_para(para: Paragraph, doc: DocxDocument) -> list[InlineImageInfo]:
    """从段落 XML 中提取内嵌图片（w:drawing / wp:inline）"""
    images: list[InlineImageInfo] = []
    for drawing in para._element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'):
        inline = drawing.find('wp:inline', _NSMAP)
        anchor = drawing.find('wp:anchor', _NSMAP)
        container = inline if inline is not None else anchor
        if container is None:
            continue

        # 尺寸（EMU → cm）
        extent = container.find('wp:extent', _NSMAP)
        cx = int(extent.get('cx', 0)) if extent is not None else 0
        cy = int(extent.get('cy', 0)) if extent is not None else 0

        # 图片名称
        doc_pr = container.find('wp:docPr', _NSMAP)
        name = doc_pr.get('name', '') if doc_pr is not None else ''

        # 图片文件引用（r:embed → rels → 文件名）
        blip = container.find('.//a:blip', _NSMAP)
        file_name = ''
        if blip is not None:
            embed_id = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed', '')
            if embed_id and embed_id in doc.part.rels:
                file_name = doc.part.rels[embed_id].target_ref

        images.append(InlineImageInfo(
            name=name,
            file_name=file_name,
            width_cm=round(cx / _EMU_PER_CM, 2) if cx else None,
            height_cm=round(cy / _EMU_PER_CM, 2) if cy else None,
        ))

    return images


# ============================================================
# 段落提取
# ============================================================

def _extract_all_paragraphs(doc: DocxDocument) -> list[ParaInfo]:
    """
    提取文档中所有段落（正文段落 + 表格内段落），含内嵌图片信息。
    按文档 XML body 子元素的原始顺序遍历，保持表格段落与正文段落的自然顺序。
    python-docx 的 doc.paragraphs 不包含表格单元格内的段落。
    """
    paras: list[ParaInfo] = []

    # 构建 XML element → Paragraph 映射，用于按文档顺序查找
    para_by_element: dict = {p._element: p for p in doc.paragraphs}
    table_by_element: dict = {t._element: t for t in doc.tables}

    WML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    TAG_P = f"{{{WML_NS}}}p"
    TAG_TBL = f"{{{WML_NS}}}tbl"

    for child in doc.element.body:
        if child.tag == TAG_P and child in para_by_element:
            p = para_by_element[child]
            info = _extract_para_info(p, len(paras))
            info.images = _extract_images_from_para(p, doc)
            paras.append(info)
        elif child.tag == TAG_TBL and child in table_by_element:
            table = table_by_element[child]
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        info = _extract_para_info(p, len(paras))
                        info.images = _extract_images_from_para(p, doc)
                        paras.append(info)
        # 跳过 sectPr、sdt 等其他元素

    return paras


# ============================================================
# BODY 内子分类
# ============================================================

def _classify_body_paragraph(
    info: ParaInfo,
    rules: UnitRecognitionRules,
) -> UnitType:
    """
    在 BODY 状态下，对段落做进一步细分：
    HEADING（章节标题）/ FIGURE_TABLE（图表题注）/ BODY（普通正文）
    """
    text = info.text
    style = info.style_name

    # 标题：样式名匹配 或 内容正则匹配
    if _match_heading_style(style, rules):
        return UnitType.HEADING
    for level_patterns in rules.heading_level_patterns.values():
        if _match_any(text, level_patterns):
            return UnitType.HEADING

    # 图 / 表 / 公式题注
    if _match_any(text, rules.figure_caption_patterns):
        return UnitType.FIGURE_TABLE
    if _match_any(text, rules.table_caption_patterns):
        return UnitType.FIGURE_TABLE
    if _match_any(text, rules.formula_caption_patterns):
        return UnitType.FIGURE_TABLE

    return UnitType.BODY


# ============================================================
# 结构化结果组装
# ============================================================

def _build_parsed_document(
    state_paras: list[tuple[ParseState, ParaInfo]],
    file_name: str,
    rules: UnitRecognitionRules,
) -> ParsedDocument:
    """
    将状态机分类结果组装为 ParsedDocument。

    组装规则：
    - COVER / TITLE_PAGE → 直接存 ParaInfo 列表
    - ABSTRACT → 组装成 AbstractInfo（区分标题、正文、关键词）
    - TOC → 归入 BODY（目录非7单元之一，不单独审查）
    - BODY → 进一步子分类为 HEADING / FIGURE_TABLE / BODY
    - REFERENCES → 组装成 ReferenceInfo 列表
    """
    result = ParsedDocument(file_name=file_name)
    result.units = {
        UnitType.COVER: [],
        UnitType.STATEMENT: [],
        UnitType.TITLE_PAGE: [],
        UnitType.ABSTRACT: [],
        UnitType.HEADING: [],
        UnitType.FIGURE_TABLE: [],
        UnitType.BODY: [],
        UnitType.REFERENCES: [],
    }

    abstract_paras: list[ParaInfo] = []

    for state, info in state_paras:
        if state == ParseState.COVER:
            result.units[UnitType.COVER].append(info)

        elif state == ParseState.STATEMENT:
            result.units[UnitType.STATEMENT].append(info)

        elif state == ParseState.TITLE_PAGE:
            result.units[UnitType.TITLE_PAGE].append(info)

        elif state == ParseState.ABSTRACT:
            abstract_paras.append(info)

        elif state == ParseState.TOC:
            result.units[UnitType.BODY].append(info)

        elif state == ParseState.BODY:
            sub_type = _classify_body_paragraph(info, rules)

            if sub_type == UnitType.HEADING:
                level = _parse_heading_level_from_style(info.style_name)
                # 如果样式级别没提取到，用内容正则尝试
                if level == 1:
                    for lvl, patterns in rules.heading_level_patterns.items():
                        if _match_any(info.text, patterns):
                            level = lvl
                            break
                heading = HeadingInfo(level=level, text=info.text, para=info)
                result.units[UnitType.HEADING].append(heading)
                result.units[UnitType.BODY].append(info)

            elif sub_type == UnitType.FIGURE_TABLE:
                text = info.text
                if _match_any(text, rules.table_caption_patterns):
                    category = "table"
                elif _match_any(text, rules.formula_caption_patterns):
                    category = "formula"
                else:
                    category = "figure"
                ft_info = FigureTableInfo(category=category, caption=text, para=info)
                result.units[UnitType.FIGURE_TABLE].append(ft_info)
                result.units[UnitType.BODY].append(info)

            else:
                result.units[UnitType.BODY].append(info)

        elif state == ParseState.REFERENCES:
            # 跳过"参考文献"标题段落本身
            if _is_reference_heading(info.text, rules):
                continue
            # 跳过致谢/附录及其后续内容（兜底，正常已被状态机拦截）
            if _is_post_reference(info.text, rules):
                result.units[UnitType.BODY].append(info)
                continue
            # 跳过空段落
            if not info.text.strip():
                continue
            ref_num = ""
            m = re.match(r"^\s*\[\d+\]", info.text)
            if m:
                ref_num = m.group().strip()
            ref_info = ReferenceInfo(
                index=len(result.units[UnitType.REFERENCES]) + 1,
                ref_number=ref_num,
                text=info.text,
                para=info,
            )
            result.units[UnitType.REFERENCES].append(ref_info)

    # ---- 组装 AbstractInfo ----
    if abstract_paras:
        abstract = AbstractInfo()
        for p in abstract_paras:
            if _is_abstract_heading(p.text, rules):
                abstract.title_para = p
            elif _is_keywords_label(p.text, rules):
                abstract.keywords_labels.append(p)
            else:
                abstract.body_paras.append(p)
        result.units[UnitType.ABSTRACT] = [abstract]

    return result


# ============================================================
# 文件校验
# ============================================================

def _validate_docx_file(file_path: Path) -> None:
    """
    校验输入文件是否为有效的 .docx 文档。

    校验步骤：
    1. 文件是否存在
    2. 文件扩展名是否为 .docx
    3. 文件是否能作为 ZIP 打开（docx 本质是 ZIP 压缩包）
    4. ZIP 内是否包含 docx 必需的核心文件（[Content_Types].xml）

    若任一校验失败，抛出 ValueError 并附带中文提示信息。
    """
    # 1. 检查文件是否存在
    if not file_path.exists():
        raise FileNotFoundError(
            f"文件不存在：{file_path}\n"
            f"请检查提交的文档路径是否正确。"
        )

    # 2. 检查扩展名
    suffix = file_path.suffix.lower()
    if suffix != ".docx":
        raise ValueError(
            f"不支持的文件类型：「{suffix or '(无扩展名)'}」\n"
            f"文件路径：{file_path}\n\n"
            f"本解析器仅支持 Microsoft Word .docx 格式的文档。\n"
            f"请检查提交的文档类型，确保：\n"
            f"  • 文件扩展名为 .docx（而非 .doc / .pdf / .txt / .md 等）\n"
            f"  • 文档为 Microsoft Word 2007 及以上版本创建的 Open XML 格式\n"
            f"  • 如果是老版本 .doc 文件，请用 Word 打开后另存为 .docx 格式"
        )

    # 3. 检查是否为有效的 ZIP 压缩包（docx 本质是 ZIP）
    try:
        if not zipfile.is_zipfile(file_path):
            raise zipfile.BadZipFile("文件不是有效的 ZIP 压缩包")
    except zipfile.BadZipFile:
        raise ValueError(
            f"文件损坏或格式无效：{file_path.name}\n\n"
            f"该文件虽然扩展名为 .docx，但无法作为有效的 ZIP 压缩包打开。\n"
            f"可能的原因：\n"
            f"  • 文件未完整下载或已损坏\n"
            f"  • 文件不是真正的 .docx 文档（可能被错误地修改了扩展名）\n"
            f"  • 请重新保存或重新下载该文档后重试"
        )

    # 4. 检查 ZIP 内是否包含 docx 必需的核心文件
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            namelist = zf.namelist()
            if '[Content_Types].xml' not in namelist:
                raise ValueError(
                    f"不是有效的 .docx 文档：{file_path.name}\n\n"
                    f"该文件虽为 ZIP 压缩包，但缺少 docx 格式必需的核心文件。\n"
                    f"请确认：\n"
                    f"  • 该文件确实是 Microsoft Word .docx 文档\n"
                    f"  • 文件未被其他软件修改或损坏\n"
                    f"  • 请尝试用 Word 重新打开并另存为 .docx 格式"
                )
    except zipfile.BadZipFile:
        raise ValueError(
            f"文件损坏或格式无效：{file_path.name}\n\n"
            f"无法读取文件内部结构。请检查提交的文档是否完整有效。"
        )


# ============================================================
# 公开 API
# ============================================================

def parse_docx(
    file_path: str | Path,
    rules: Optional[UnitRecognitionRules] = None,
) -> ParsedDocument:
    """
    读取并解析一个 .docx 论文文件，输出结构化 ParsedDocument。

    用法:
        from src.parser.docx_parser import parse_docx

        paper = parse_docx("论文.docx")

        # 属性访问
        print(paper.cover_paras)         # 封面段落
        print(paper.headings)            # 章节标题
        print(paper.figures_tables)      # 图/表/公式
        print(paper.references)          # 参考文献

        # JSON 输出
        print(paper.to_json())           # 完整 JSON 字符串
        paper.save_json("output/")       # 保存为 7 个 JSON 文件

    参数:
        file_path: docx 文件路径
        rules:     可选的识别规则配置，默认使用 DEFAULT_RULES

    返回:
        ParsedDocument: 包含 7 个单元的结构化数据
    """
    if rules is None:
        rules = DEFAULT_RULES

    file_path = Path(file_path)

    # ---- 第〇步：文件类型校验 ----
    _validate_docx_file(file_path)

    try:
        doc = DocxDocument(str(file_path))
    except Exception as e:
        raise ValueError(
            f"无法解析 .docx 文档：{file_path.name}\n\n"
            f"该文件通过了基础格式校验，但文档内容解析失败。\n"
            f"原始错误：{type(e).__name__}: {e}\n\n"
            f"请检查：\n"
            f"  • 文档是否在 Word 中能正常打开\n"
            f"  • 文档内部 XML 是否损坏\n"
            f"  • 请尝试用 Word 打开后另存为新 .docx 文件再试"
        ) from e

    # ---- 第一步：提取页面设置 ----
    page_settings = _extract_page_settings(doc)

    # ---- 第一步-2：提取页眉页脚 ----
    headers_footers = _extract_headers_footers(doc)

    # ---- 第二步：提取所有段落 ----
    all_paras = _extract_all_paragraphs(doc)

    # ---- 第三步：状态机遍历，逐段归类 ----
    state = ParseState.COVER
    state_paras: list[tuple[ParseState, ParaInfo]] = []

    for info in all_paras:
        next_s = _next_state(state, info.text, info.style_name, rules)
        if next_s is not None:
            state = next_s

        info.state = state
        state_paras.append((state, info))

    # ---- 第四步：组装结构化结果 ----
    result = _build_parsed_document(state_paras, file_path.name, rules)
    result.page_settings = page_settings
    result.headers_footers = headers_footers
    return result


def parse_and_save(
    file_path: str | Path,
    output_dir: str | Path,
    rules: Optional[UnitRecognitionRules] = None,
) -> ParsedDocument:
    """
    解析 docx 并直接将 7 个单元保存为 JSON 文件。

    用法:
        from src.parser.docx_parser import parse_and_save

        paper = parse_and_save("论文.docx", "output/parser_json/")
        # output/parser_json/ 下生成：
        #   cover.json  title_page.json  abstract.json  heading.json
        #   figure_table.json  body.json  references.json

    返回:
        ParsedDocument（同时已保存 JSON 文件）
    """
    paper = parse_docx(file_path, rules)
    paper.save_json(output_dir)
    return paper
