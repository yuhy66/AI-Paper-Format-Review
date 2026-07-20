# 论文格式审查系统

基于 python-docx 的论文格式自动审查工具，结合本地大模型进行 GB/T 7714-2025 参考文献著录格式合规判断。

## 快速开始

```bash
pip install -r requirements.txt
python run.py 论文.docx -c config.toml
```

## 模块负责人

| 模块 | 负责人 |
|------|--------|
| 文档拆解 (parser) | |
| 审查1 (封面/扉页/摘要) | |
| 审查2 (章节/编号/正文) | |
| 参考文献-代码侧 | |
| 参考文献-Agent侧 | |
| 规则制定+报告汇总 | |
