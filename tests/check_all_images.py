"""检查整个文档所有单元的图片识别情况"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

desktop = Path.home() / "Desktop"
target = None
for f in desktop.glob("*.docx"):
    if f.name.startswith("~$"):
        continue
    if "格式检查" in f.name or "示例" in f.name:
        target = f
        break

from src.parser.docx_parser import parse_docx
paper = parse_docx(str(target))

# 统计所有图片
total_images = 0
for unit_type, items in paper.units.items():
    unit_images = 0
    for item in items:
        if hasattr(item, 'images') and item.images:
            unit_images += len(item.images)
            total_images += len(item.images)
    if unit_images > 0:
        print(f"[{unit_type.value:15s}] {unit_images} 张图片")

print(f"\n总计: {total_images} 张图片")

# 详细列出每张图片
print("\n=== 图片详情 ===")
for unit_type, items in paper.units.items():
    for item in items:
        if hasattr(item, 'images') and item.images:
            for img in item.images:
                text_preview = item.text[:40] if item.text else "(空段落)"
                print(f"  [{unit_type.value}] 段{item.index}: {img.name}")
                print(f"          文件: {img.file_name or '(无——可能是形状)'}")
                print(f"          尺寸: {img.width_cm}x{img.height_cm}cm")
                print(f"          文字: {repr(text_preview)}")
