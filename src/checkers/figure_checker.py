from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.shape import CT_Picture
import re

class FigureTableFormulaChecker:
    def __init__(self):
        # --------配置，和你的论文规范对齐--------
        # 编号模式：逐章编号 例 图1.1；全文连续编号：图1
        self.mode_chapter_based = True
        # 图、表、公式引用正则
        self.re_figure_ref = re.compile(r"如图(\d+(?:\.\d+)?)")
        self.re_table_ref = re.compile(r"如表(\d+(?:\.\d+)?)")
        self.re_formula_ref = re.compile(r"由式\((\d+(?:\.\d+)[a-c]?)\)")
        # 图题、表题字体要求：宋体五号
        self.caption_font_name = "宋体"
        self.caption_font_size = 10.5  #五号=10.5pt

        # 收集检测结果
        self.errors = []
        self.fig_captions = []
        self.tbl_captions = []
        self.formula_nums = []


    def log_err(self, msg, para_idx=None):
        """记录错误信息"""
        pos = f"段落{para_idx}:" if para_idx else ""
        self.errors.append(f"{pos}{msg}")


    def check_table(self, doc:Document):
        """检查表格规范"""
        for idx, tbl in enumerate(doc.tables):
            # 规则：表标题在表格上方居中，格式：表X 标题，无标点；宋体五号
            # python‑docx无法直接判断“标题是否紧跟表格上方”，这里做标记提醒
            self.log_err(f"【表格{idx+1}人工校验提醒】需要确认：表题在表格上方居中，格式“表序号+表标题”末尾无标点，宋体五号")

        # 扫描正文，检查引用格式：如表5
        for p_idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            matches = self.re_table_ref.findall(text)
            for m in matches:
                self.tbl_captions.append(m)
                if not re.search(r"如表" + m, text):
                    self.log_err(f"表格引用格式错误，规范应为`如表{m}`", p_idx)


    def check_figure(self, doc:Document):
        """检查插图规范"""
        # 遍历文档所有段落，查找图片
        for p_idx, para in enumerate(doc.paragraphs):
            for run in para.runs:
                for elem in run.element:
                    if isinstance(elem, CT_Picture):
                        self.log_err(f"【插图人工校验提醒】段落{p_idx}发现图片：确认图题在图下方，格式“图序号+图标题”宋体五号；多子图标a/b/c；坐标轴带单位；图和图题不能分页")

            # 检查正文引用格式：如图5
            text = para.text.strip()
            matches = self.re_figure_ref.findall(text)
            for m in matches:
                self.fig_captions.append(m)
                if not re.search(r"如图" + m, text):
                    self.log_err(f"插图引用格式错误，规范应为`如图{m}`", p_idx)


    def check_formula(self, doc:Document):
        """公式规范校验（docx无法读取公式内部排版，做规则提示+正文引用校验）"""
        for p_idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            # 匹配 由式(3.2)
            matches = self.re_formula_ref.findall(text)
            for m in matches:
                self.formula_nums.append(m)
                # 校验括号半角符号
                if "（" in text:
                    self.log_err(f"公式引用使用全角括号！规范：`由式({m})`，要用半角()", p_idx)

        self.log_err("【公式人工校验提醒】\n1.公式居中成行；优先等号处转行，转行运算符放行首\n2.公式右侧末尾半角圆括号编号，公式与编号之间无虚线\n3.子公式a/b/c标记，重复公式不重新编号")


    def check_caption_font(self, doc:Document):
        """简单遍历，提示图题表题字体字号人工核对"""
        self.log_err("【字体人工校验提醒】图题、表题必须宋体五号(10.5pt)")


    def run_all_check(self, file_path):
        self.errors.clear()
        self.fig_captions.clear()
        self.tbl_captions.clear()
        self.formula_nums.clear()

        doc = Document(file_path)
        self.check_table(doc)
        self.check_figure(doc)
        self.check_formula(doc)
        self.check_caption_font(doc)

        print("=====图表公式单元检测报告=====\n")
        if len(self.errors) == 0:
            print("✅未检测到格式问题")
        else:
            for e in self.errors:
                print(f"❌ {e}\n")

        print(f"收集到图引用编号：{self.fig_captions}")
        print(f"收集到表引用编号：{self.tbl_captions}")
        print(f"收集到公式引用编号：{self.formula_nums}")

        # 简单校验编号是否跳号（逐章模式这里仅做提示）
        print("\n⚠️注意：docx库不能解析Word内部OLE公式对象、无法判断图片标题是否跨页、表格是否跨页续表，**分页、续表、公式内部排版需要人工复核**。")


if __name__ == "__main__":
    checker = FigureTableFormulaChecker()
    # 把你的论文docx路径填这里
    checker.run_all_check(r"你的论文.docx")
