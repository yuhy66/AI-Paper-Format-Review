"""探查封面段落中的图片信息"""
import sys
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent.parent))

desktop = Path.home() / "Desktop"
target = None
for f in desktop.glob("*.docx"):
    if f.name.startswith("~$"):
        continue
    if "格式检查" in f.name or "示例" in f.name:
        target = f
        break

from docx import Document
doc = Document(str(target))

# 封面：前15个段落
print("=== 封面段落检查（前15段）===")
print(f"文档总段落数: {len(doc.paragraphs)}")
print()

# XML命名空间
nsmap = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'v': 'urn:schemas-microsoft-com:vml',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
}

for i, para in enumerate(doc.paragraphs[:20]):
    text = para.text.strip()
    xml = para._element

    # 检查是否有图片
    drawings = xml.findall('.//w:drawing', nsmap)
    picts = xml.findall('.//w:pict', nsmap)

    has_image = len(drawings) > 0 or len(picts) > 0

    if text or has_image:
        marker = " [图片]" if has_image else ""
        if len(text) > 80:
            text = text[:80] + "..."
        print(f"[{i:3d}] style={para.style.name:12s} text={repr(text)}{marker}")

# 检查文档中的图片关系
print(f"\n=== 文档图片资源 ===")
print(f"sections: {len(doc.sections)}")
print(f"inline_shapes: {len(doc.inline_shapes)}")

# 检查part关系中的图片
for rel_id, rel in doc.part.rels.items():
    if "image" in rel.reltype:
        print(f"  {rel_id}: {rel.target_ref} (type={rel.reltype})")

# 打印第一个段落的完整XML看看结构
print(f"\n=== 第0段完整XML（前2000字符）===")
xml_str = etree.tostring(doc.paragraphs[0]._element, pretty_print=True, encoding='unicode')
print(xml_str[:2000])
