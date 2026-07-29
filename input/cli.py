"""
论文格式检查 —— 统一输入接口（CLI 命令行）。

使用方式：
    python run.py "论文.docx"
    python run.py "论文.docx" -o output/parser_json/
    python run.py "论文.docx" --parse-only  # 仅解析不保存
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

from src.parser.unit_defs import ParsedDocument

# 确保项目根目录在 sys.path 中，支持从任意位置运行
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Windows GBK 终端兼容：用 ASCII 标记代替 emoji
_OK = "[OK]"
_ERR = "[ERR]"

def _print(*args: Any, **kwargs: Any) -> None:
    """安全的 print，自动处理 Windows GBK 编码问题"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 回退：替换无法编码的字符
        safe_args = []
        for a in args:
            if isinstance(a, str):
                a = a.encode(sys.stdout.encoding or "gbk", errors="replace").decode(sys.stdout.encoding or "gbk")
            safe_args.append(a)
        print(*safe_args, **kwargs)


class PaperInput:
    """
    论文输入文件封装。

    负责：
      - 接收文件路径
      - 调用解析器（校验 + 解析 + 状态机分类）
      - 保存 JSON 结果
      - 打印摘要信息
    """

    def __init__(
        self,
        file_path: str | Path,
        output_dir: str | Path = "output/parser_json/",
    ) -> None:
        """
        参数:
            file_path:  .docx 论文文件路径
            output_dir: JSON 结果输出目录
        """
        self.file_path = Path(file_path)
        self.output_dir = Path(output_dir)

    # ---- 解析 ----

    def parse(self) -> Optional[ParsedDocument]:
        """
        解析论文文档，返回 ParsedDocument。

        文件校验由 parser 的 _validate_docx_file() 统一处理（文件是否存在、
        扩展名、ZIP 完整性、XML 核心文件），此处不重复校验。

        失败返回 None。
        """
        from src.parser.docx_parser import parse_docx

        try:
            _print(f"[DOC] 开始解析：{self.file_path.name}")
            paper = parse_docx(str(self.file_path))
            _print(f"{_OK} 解析完成\n")
            return paper
        except Exception as e:
            _print(f"{_ERR} {e}")
            return None

    def parse_and_save(self) -> Optional[ParsedDocument]:
        """
        解析并保存 JSON 到输出目录。返回 ParsedDocument 或 None。
        """
        paper = self.parse()
        if paper is None:
            return None

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            paper.save_json(str(self.output_dir))
            _print(f"[DIR] JSON 已保存至：{self.output_dir.resolve()}")
            return paper
        except Exception as e:
            _print(f"{_ERR} JSON 保存失败：{e}")
            return paper

    # ---- 摘要打印 ----

    @staticmethod
    def print_summary(paper: ParsedDocument) -> None:
        """打印解析结果摘要统计"""
        ps = paper.page_settings
        _print()
        _print("-" * 50)
        _print(f"[FILE] 文件：{paper.file_name}")
        _print(f"[PAGE] 页面：{ps.width_cm} x {ps.height_cm} cm  "
               f"上{ps.top_margin_cm} 下{ps.bottom_margin_cm}  "
               f"左{ps.left_margin_cm} 右{ps.right_margin_cm}  "
               f"({ps.orientation})")
        _print("-" * 50)
        _print("各单元统计：")
        for unit_type, items in paper.units.items():
            _print(f"  {unit_type.value:16s} : {len(items):4d} 条")
        _print("-" * 50)

    # ---- 完整流程 ----

    def run(self) -> Optional[ParsedDocument]:
        """完整流程：解析 → 保存 → 摘要。返回 ParsedDocument 或 None。"""
        paper = self.parse_and_save()
        if paper is not None:
            self.print_summary(paper)
        return paper


# ============================================================
# CLI 参数
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="python run.py",
        description="论文格式检查工具 —— 解析 .docx 论文并检查格式规范",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python run.py 论文.docx
  python run.py "C:/Users/YH/Desktop/中大毕业论文格式检查_示例.docx"
  python run.py 论文.docx -o output/parser_json/
  python run.py 论文.docx --parse-only
        """,
    )
    parser.add_argument(
        "file",
        type=str,
        help=".docx 论文文件路径（必填）",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output/parser_json/",
        help="JSON 输出目录（默认: output/parser_json/）",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="仅解析不保存 JSON 文件",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """
    CLI 主入口。

    参数:
        argv: 命令行参数列表，None 表示使用 sys.argv

    返回:
        0 = 成功，1 = 失败
    """
    p = build_parser()
    args = p.parse_args(argv)

    inp = PaperInput(
        file_path=args.file,
        output_dir=args.output,
    )

    if args.parse_only:
        paper = inp.parse()
        if paper is not None:
            inp.print_summary(paper)
    else:
        paper = inp.run()

    return 0 if paper is not None else 1
