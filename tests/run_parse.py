"""解析论文docx并输出JSON"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.docx_parser import parse_and_save

# 扫描桌面找到目标文件
desktop = Path.home() / "Desktop"
target = None
for f in desktop.glob("*.docx"):
    if f.name.startswith("~$"):
        continue
    if "格式检查" in f.name or "示例" in f.name:
        target = f
        break

if target is None:
    print("未找到文件！")
    sys.exit(1)

print(f"解析: {target.name}")
paper = parse_and_save(str(target), str(Path(__file__).parent.parent / "output" / "parser_json"))

# 检查封面图片
print("\n=== 封面图片 ===")
for p in paper.cover_paras:
    if p.images:
        for img in p.images:
            print(f"  [{p.index}] {img.name}: {img.file_name} ({img.width_cm}x{img.height_cm}cm)")
            print(f"       段落文字: {repr(p.text[:60]) if p.text else '(空)'}")

# 页面设置
ps = paper.page_settings
print(f"\n页面: {ps.width_cm}x{ps.height_cm}cm, "
      f"上{ps.top_margin_cm} 下{ps.bottom_margin_cm} "
      f"左{ps.left_margin_cm} 右{ps.right_margin_cm}")

print("\n各单元统计:")
for ut, items in paper.units.items():
    print(f"  {ut.value:15s} : {len(items):4d} 条")
