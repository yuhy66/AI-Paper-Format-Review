"""列出桌面所有docx文件"""
import sys
from pathlib import Path

desktop = Path.home() / "Desktop"
print("桌面docx文件:")
for i, f in enumerate(sorted(desktop.glob("*.docx"))):
    if f.name.startswith("~$"):
        continue
    size_kb = f.stat().st_size / 1024
    # 用repr显示文件名原始编码
    print(f"  [{i}] {f.name}  ({size_kb:.1f} KB)")
    print(f"      路径: {f}")
