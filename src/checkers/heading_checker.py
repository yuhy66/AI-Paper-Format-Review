# src/checkers/heading_checker.py
from .abstract_checker import AbstractChecker
from docx.shared import Pt
import re


class HeadingChecker(AbstractChecker):
    """
    第四部分：章节标题单元校验
    规则来源：任务文档第四板块
    """

    def __init__(self):
        self.errors = []

        # 正则：汉字编号体系：一、 （一） 1. (1)
        self.pat_chinese = re.compile(r"^([一二三四五六七八九十]+[、．]|（[一二三四五六七八九十]+）|\d+\.|（\d+）)")
        # 数字编号体系：1  1.1  1.1.1  1.1.1.1
        self.pat_digit = re.compile(r"^\d+(\.\d+)*")

    def check(self, doc):
        """对外入口，传入docx对象，返回错误列表"""
        self.errors.clear()
        # 标记全文使用哪一套编号：None未确定，"chinese"汉字，"digit"数字
        mode = None

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            is_chinese_mode = bool(self.pat_chinese.match(text))
            is_digit_mode = bool(self.pat_digit.match(text))

            if is_chinese_mode or is_digit_mode:
                # ==========规则1：两套编号不可混用，禁止五级标题==========
                if is_chinese_mode:
                    current = "chinese"
                    depth = self._get_chinese_depth(text)
                else:
                    current = "digit"
                    depth = self._get_digit_depth(text)

                # 检测混用
                if mode is None:
                    mode = current
                else:
                    if mode != current:
                        self.errors.append(f"【标题混用编号体系】标题：{text}，全文已经使用{mode}体系，不能切换{current}体系")

                # 禁止五级标题（深度最大4）
                if depth > 4:
                    self.errors.append(f"【标题层级超限】标题：{text}，不允许设置五级以及更深标题，当前层级{depth}")

                # ==========规则2：标题末尾不能有标点符号==========
                last_char = text[-1]
                if last_char in {"。", "，", "；", "：", "、", "？", "！"}:
                    self.errors.append(f"【标题末尾禁止标点】标题：{text}，末尾不能添加标点符号")

                # ==========规则3：校验字体、字号、对齐方式==========
                self._check_font_align(para, depth, text)

                # ==========规则4：段前段后0.5行，1.5倍行距==========
                self._check_paragraph_spacing(para, text)

        return self.errors

    def _get_chinese_depth(self, title_text: str) -> int:
        """汉字编号体系：一、(1级) →（一）(2级) →1.(3级) →(1)(4级)"""
        if re.match(r"^[一二三四五六七八九十]+[、．]", title_text):
            return 1
        elif re.match(r"^（[一二三四五六七八九十]+）", title_text):
            return 2
        elif re.match(r"^\d+\.", title_text):
            return 3
        elif re.match(r"^（\d+）", title_text):
            return 4
        return 99

    def _get_digit_depth(self, title_text: str) -> int:
        """数字体系：1(1),1.1(2),1.1.1(3),1.1.1.1(4)"""
        match = self.pat_digit.match(title_text)
        if match:
            s = match.group(0)
            return s.count(".") + 1
        return 99

    def _check_font_align(self, para, depth, title_text):
        """校验字体字号对齐"""
        # 获取第一个run字体
        run = para.runs[0] if len(para.runs) > 0 else None
        if run is None:
            self.errors.append(f"【标题字体异常】{title_text}，无法读取字体信息")
            return

        font = run.font
        size_pt = font.size.pt if font.size else None
        align = para.alignment

        if depth == 1:
            # 章标题：黑体三号，居中
            if font.name != "黑体":
                self.errors.append(f"【章标题字体错误】{title_text}，应当为黑体")
            if size_pt != Pt(16).pt:  # 三号=16pt
                self.errors.append(f"【章标题字号错误】{title_text}，应当三号(16pt)")
            if align != 1:  # WD_ALIGN_PARAGRAPH.CENTER 居中=1
                self.errors.append(f"【章标题对齐错误】{title_text}，应当居中对齐")
        elif depth == 2:
            # 一级节标题：黑体四号，左对齐
            if font.name != "黑体":
                self.errors.append(f"【一级节标题字体错误】{title_text}，应当黑体")
            if size_pt != Pt(14).pt:  # 四号=14pt
                self.errors.append(f"【一级节标题字号错误】{title_text}，应当四号(14pt)")
            if align != 0:  # 左对齐0
                self.errors.append(f"【一级节标题对齐错误】{title_text}，应当左对齐")
        elif depth >=3:
            # 二级及以下：宋体小四号加粗，段首空两格
            if font.name != "宋体":
                self.errors.append(f"【小标题字体错误】{title_text}，应当宋体")
            if size_pt != Pt(12).pt:  # 小四号=12pt
                self.errors.append(f"【小标题字号错误】{title_text}，应当小四号(12pt)")
            if not font.bold:
                self.errors.append(f"【小标题未加粗】{title_text}，二级及以下小标题需要加粗")
            # 段首空两格：首行缩进
            indent = para.paragraph_format.first_line_indent
            if indent is None or indent.pt < 20:
                self.errors.append(f"【小标题缺少首行缩进】{title_text}，段首需要空两格")

    def _check_paragraph_spacing(self, para, title_text):
        """段前、段后0.5行；1.5倍行距"""
        pf = para.paragraph_format
        # 段前0.5行
        if pf.space_before is None or abs(pf.space_before.pt - Pt(6).pt) > 1:
            self.errors.append(f"【标题段前间距错误】{title_text}，段前应当0.5行")
        # 段后0.5行
        if pf.space_after is None or abs(pf.space_after.pt - Pt(6).pt) > 1:
            self.errors.append(f"【标题段后间距错误】{title_text}，段后应当0.5行")
        # 1.5倍行距
        if pf.line_spacing != 1.5:
            self.errors.append(f"【标题行距错误】{title_text}，全文标题统一1.5倍行距")
