"""
论文格式检查 —— 统一入口。

用法：
    python run.py "论文.docx"
    python run.py "论文.docx" -o output/parser_json/
    python run.py "论文.docx" --parse-only
"""

from input.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
