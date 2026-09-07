"""参考文献著录格式 Agent 检查模块

输入：output/parser_json/references.json（parser 输出的 items）
输出：output/checker_json/ref_agent.json
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from openai import OpenAI

CHECKER_ID = "ref_agent"
CHECKER_NAME = "参考文献著录格式 Agent 检查"

# ===== System Prompt（核心规则） =====
SYSTEM_PROMPT = """你是论文格式审查专家，严格依据 GB/T 7714-2025 标准判断参考文献著录格式。
你只能判断以下模糊项（代码无法精确判定的部分）：
1. 作者名格式：姓前名后，姓全称、名缩写（如 ZHANG S, LI S）
2. 标点符号：题名后应使用句号，各项之间标点是否正确
3. 期刊名/会议名缩写是否合理
4. 电子文献的 DOI 格式是否完整

输出必须是合法的 JSON，格式如下：
{
  "ref_number": "[1]",
  "is_valid": true/false,
  "errors": [
    {"field": "author_name", "issue": "问题描述", "suggestion": "修改建议"}
  ],
  "confidence": 0.95
}
confidence 表示你对判断的把握程度，0-1 之间。"""

# ===== 核心函数 =====
def check_reference(ref_item: dict, model_name: str = "qwen3.6-35b") -> dict:
    """判断单条参考文献是否合规"""
    # 组装用户消息
    user_prompt = f"""请判断以下参考文献著录格式是否符合 GB/T 7714-2025:

原文: {ref_item.get('para', {}).get('text', '')}

请输出 JSON 格式的判断结果。"""

    try:
        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL")
        )

        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result_text = resp.choices[0].message.content
        return json.loads(result_text)

    except Exception as e:
        return {
            "ref_number": ref_item.get("ref_number", "unknown"),
            "is_valid": False,
            "errors": [{"field": "system", "issue": f"Agent 调用失败: {str(e)}", "suggestion": "请检查网络或Key"}],
            "confidence": 0.0
        }


# ===== 批量入口 =====
def run(input_path: str | Path, output_path: str | Path) -> dict:
    """读 references.json → 逐条 Agent 检查 → 写 ref_agent.json"""
    input_path = Path(input_path)
    output_path = Path(output_path)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    source_file = data.get("file_name", input_path.name)
    items = data.get("items", [])

    results = []
    errors = []
    warnings = []

    for item in items:
        ref_number = item.get("ref_number", "unknown")
        para = item.get("para", {})
        text = para.get("text", "")
        para_index = para.get("index", 0)

        if not text:
            warnings.append({
                "severity": "warning",
                "category": "empty_reference",
                "ref_number": ref_number,
                "description": "参考文献条目为空",
                "location": {"paragraph_index": para_index}
            })
            continue

        result = check_reference(item)
        results.append(result)

        if not result.get("is_valid", True):
            for err in result.get("errors", []):
                errors.append({
                    "severity": "error",
                    "category": err.get("field", "unknown"),
                    "ref_number": result.get("ref_number", "unknown"),
                    "description": err.get("issue", ""),
                    "suggestion": err.get("suggestion", ""),
                    "location": {"paragraph_index": para_index}
                })

    now = datetime.now().isoformat()
    output = {
        "checker": CHECKER_ID,
        "checker_name": CHECKER_NAME,
        "timestamp": now,
        "source_file": source_file,
        "summary": {
            "status": "pass" if len(errors) == 0 and len(warnings) == 0 else "fail",
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "ref_count": len(items),
        },
        "errors": errors,
        "warnings": warnings,
        "details": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output


# ===== CLI 入口 =====
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    DEFAULT_INPUT = PROJECT_ROOT / "output" / "parser_json" / "references.json"
    DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "checker_json" / "ref_agent.json"

    input_path = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_INPUT)
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_OUTPUT)

    print(f"输入: {input_path}")
    print(f"输出: {output_path}")

    result = run(input_path, output_path)

    print(f"\n完成！共检查 {result['summary']['ref_count']} 条参考文献")
    print(f"错误: {result['summary']['total_errors']} 条，警告: {result['summary']['total_warnings']} 条")
    print(f"状态: {result['summary']['status']}")