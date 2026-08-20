from docx import Document
import re

class ContentChecker:
    def __init__(self):
        # ========== 论文规范配置区，和截图要求对齐 ==========
        self.min_content_words = 8000   # 正文最少8000字
        # 必须出现的三大模块标题
        self.must_have_sections = ["绪论", "主体", "结论"]
        # 匹配2位年份，例如 24、26，用来抓错误简写年份
        self.re_two_digit_year = re.compile(r"\b(1[0-9]|2[0-9])\b")
        # 存储错误信息
        self.errors = []
        # 统计正文总文字
        self.total_plain_text = ""


    def log_err(self, msg, para_idx=None):
        """记录错误，和之前代码同一个工具函数"""
        pos = f"段落{para_idx}:" if para_idx else ""
        self.errors.append(f"{pos}{msg}")


    def check_must_section(self, doc: Document):
        """检查：是否存在 绪论、主体、结论 三大模块"""
        all_para_text = []
        for para in doc.paragraphs:
            txt = para.text.strip()
            if len(txt) > 0:
                all_para_text.append(txt)

        # 遍历要求的三个标题
        for section_name in self.must_have_sections:
            find_flag = False
            for text_item in all_para_text:
                if section_name in text_item:
                    find_flag = True
                    break
            if not find_flag:
                self.log_err(f"【正文模块缺失】文档没有检测到模块标题：「{section_name}」，正文需要包含：绪论、主体、结论")


    def check_word_count(self, doc: Document):
        """统计纯正文汉字字符，检查不少于8000字"""
        self.total_plain_text = ""
        for para in doc.paragraphs:
            # 拼接全部段落文字
            self.total_plain_text += para.text

        # 只统计中文字符（过滤空格、换行、英文、数字、标点）
        chinese_only = re.findall(r'[\u4e00-\u9fff]', self.total_plain_text)
        real_word_num = len(chinese_only)

        if real_word_num < self.min_content_words:
            self.log_err(f"【字数不达标】正文汉字统计：{real_word_num}字，要求不少于{self.min_content_words}字")
        else:
            print(f"✅正文字数校验通过，汉字数量：{real_word_num}")


    def check_year_format(self, doc: Document):
        """检查年份：禁止2位简写年份，必须4位数字，例如2026，不能写26"""
        for p_idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            # 简单启发式：连续两位数字，周围有年字，大概率简写年份
            if "年" in text:
                match_list = self.re_two_digit_year.findall(text)
                for m in match_list:
                    self.log_err(f"疑似2位简写年份`{m}`，规范要求年份必须4位阿拉伯数字，例：2026", p_idx)


    def check_english_number_font(self, doc: Document):
        """检查英文、阿拉伯数字字体应为 Times New Roman"""
        # ⚠️重要限制：python‑docx很难区分“这一段哪些字符是数字英文”
        # run是最小字体单元，一个run内部字体全部一样。
        # 如果一段里面中文+英文混排，Word会拆成多个run。
        for p_idx, para in enumerate(doc.paragraphs):
            for run in para.runs:
                font = run.font
                run_text = run.text
                # 判断这个run里面有没有英文或者阿拉伯数字
                has_en = re.search(r"[a-zA-Z0-9]", run_text)
                if has_en:
                    # 获取字体名称
                    font_name = font.name
                    if font_name is None or "Times New Roman" not in font_name:
                        self.log_err(f"段落{p_idx}包含英文/阿拉伯数字，字体不是Times New Roman，请人工核对", p_idx)


    def run_all_check(self, file_path):
        """总入口，执行全部正文检查"""
        self.errors.clear()
        doc = Document(file_path)

        self.check_must_section(doc)
        self.check_word_count(doc)
        self.check_year_format(doc)
        self.check_english_number_font(doc)

        print("=====【正文单元】检测报告=====\n")
        if len(self.errors) == 0:
            print("✅正文单元没有检测到格式错误")
        else:
            for err in self.errors:
                print(f"❌ {err}")

        print("\n⚠️提醒：字体混排场景，建议人工复核英文、数字字体；字数仅统计中文字符。")


if __name__ == "__main__":
    checker = ContentChecker()
    checker.run_all_check(r"你的论文.docx")
