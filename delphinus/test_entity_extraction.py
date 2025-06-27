# test_entity_extraction.py

import os
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any

# --- 外部库 ---
import google.generativeai as genai
from dotenv import dotenv_values
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from deepdiff import DeepDiff

from prompts.extract_entity import create_extraction_prompt

# --- 全局配置与初始化 ---
# 加载 .env 文件中的环境变量
config = dotenv_values(".env")

# 路径配置
BASE_DIR = Path(__file__).resolve().parent
CONVERSATIONS_DIR = BASE_DIR / "conversations"
GROUND_TRUTHS_DIR = BASE_DIR / "ground_truths"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True) # 确保报告目录存在

# 初始化漂亮的控制台输出
console = Console()

# --- 辅助提取模块 (正则表达式) ---

def extract_entities_with_regex(text: str) -> List[Dict[str, Any]]:
    """
    使用正则表达式作为辅助手段，提取格式明确的实体。
    这是一种快速、低成本但召回率有限的方法。
    """
    entities = []
    # 匹配文件名，例如: xxx_v1.0.docx, yyy.pdf
    filename_pattern = r'([\w\s-]+(?:_v[\d\.]+|_[A-Z]+)?\.(?:docx|pdf|xlsx|pptx|png|md|sketch))'
    for match in re.finditer(filename_pattern, text):
        entities.append({
            "text": match.group(1),
            "type": "Document",
            "context": text[max(0, match.start()-20):min(len(text), match.end()+20)].replace('\n',' '),
            "attributes": {} # 正则很难提取属性，留给LLM
        })

    # 匹配Git分支或仓库名
    code_pattern = r"‘(project-[\w-]+)’|'project-[\w-]+'|feature/[\w-]+"
    for match in re.finditer(code_pattern, text):
        entities.append({
            "text": match.group(0).strip("‘'"),
            "type": "Code",
            "context": text[max(0, match.start()-20):min(len(text), match.end()+20)].replace('\n',' '),
            "attributes": {}
        })
        
    return entities

# --- Prompt & LLM 调用模块 ---

def call_llm_api(prompt: str) -> Dict[str, Any]:
    """
    调用Google Gemini API并返回解析后的JSON结果。
    """
    try:
        # 配置Google Gemini模型
        api_key = config.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 环境变量未设置！")

        base_url = config.get("GEMINI_BASE_URL")
        if not base_url:
            raise ValueError("GEMINI_BASE_URL 环境变量未设置！")
        
        genai.configure(
            api_key=api_key,
            client_options={"api_endpoint": base_url},
        )
        model = genai.GenerativeModel('gemini-1.5-pro')

        console.print(f"[grey50]正在调用 gemini-1.5-pro...[/grey50]")
        response = model.generate_content(prompt)
        
        # 清理并解析返回的JSON
        # LLM有时会返回被```json ... ```包裹的代码块
        cleaned_response = re.sub(r'```json\s*|\s*```', '', response.text.strip())
        return json.loads(cleaned_response)
        
    except json.JSONDecodeError:
        console.print("[bold red]错误：LLM返回的不是一个有效的JSON。[/bold red]")
        console.print(f"原始输出: {response.text}")
        return {"entities": []} # 返回一个空结构以避免脚本崩溃
    except Exception as e:
        console.print(f"[bold red]调用LLM API时发生错误: {e}[/bold red]")
        return {"entities": []}

# --- 核心测试与评估逻辑 ---

def merge_results(llm_entities: List[Dict], regex_entities: List[Dict]) -> List[Dict]:
    """
    合并LLM和Regex的结果，并去重。
    以LLM的结果为基础，补充Regex发现的、LLM遗漏的实体。
    """
    if not regex_entities:
        return llm_entities

    # 创建一个查找集，用于快速判断LLM是否已提取某个实体
    llm_texts = {e['text'] for e in llm_entities}
    
    merged_list = list(llm_entities)
    for regex_entity in regex_entities:
        if regex_entity['text'] not in llm_texts:
            merged_list.append(regex_entity)
            llm_texts.add(regex_entity['text'])
            
    return merged_list

def run_single_test(dialogue_id: str, use_aux_extraction: bool) -> Dict:
    """
    对单个对话文件执行一次完整的测试。
    """
    dialogue_file = CONVERSATIONS_DIR / f"{dialogue_id}.txt"
    ground_truth_file = GROUND_TRUTHS_DIR / f"{ground_truth_id}.json"

    # 1. 读取输入文件
    with open(dialogue_file, 'r', encoding='utf-8') as f:
        dialogue_text = f.read()
    with open(ground_truth_file, 'r', encoding='utf-8') as f:
        ground_truth_data = json.load(f)

    # 2. 生成Prompt并获取LLM预测结果
    prompt = create_extraction_prompt(dialogue_text)
    llm_prediction = call_llm_api(prompt)
    if "entities" not in llm_prediction:
        llm_prediction = {"entities": []} # 保证结构完整性

    final_prediction_entities = llm_prediction.get("entities", [])
    
    # 3. (可选) 执行并合并辅助提取结果
    if use_aux_extraction:
        regex_entities = extract_entities_with_regex(dialogue_text)
        final_prediction_entities = merge_results(final_prediction_entities, regex_entities)
        
    # 4. 程序化地生成 id 并排序，以便比较
    # 我们不在乎ID是否完全一致，只在乎提取的实体内容，所以先按text排序
    sorted_ground_truth = sorted(ground_truth_data["entities"], key=lambda x: x["text"])
    sorted_prediction = sorted(final_prediction_entities, key=lambda x: x["text"])

    # 重新生成ID，确保比较的是内容而非随机ID
    for i, entity in enumerate(sorted_ground_truth):
        entity['entity_id'] = f"{dialogue_id}_gt_{i}"
    for i, entity in enumerate(sorted_prediction):
        entity['entity_id'] = f"{dialogue_id}_pred_{i}"
        
    final_prediction = {"conversation_id": dialogue_id, "entities": sorted_prediction}
    ground_truth_data['entities'] = sorted_ground_truth

    # 5. 比较结果
    diff = DeepDiff(ground_truth_data, final_prediction, ignore_order=True, 
                    exclude_paths=["root['conversation_id']", "root['entities'][_]['entity_id']"])
    
    return {
        "id": dialogue_id,
        "mode": "LLM + Regex" if use_aux_extraction else "LLM Only",
        "passed": not bool(diff),
        "diff": json.loads(diff.to_json()) if diff else {},
        "ground_truth": ground_truth_data,
        "prediction": final_prediction
    }

# --- 主程序入口 ---

if __name__ == "__main__":
    console.print(Panel("[bold cyan]实体提取能力评估测试启动[/bold cyan]", 
                        title="EVALUATION SUITE", subtitle="Powered by Gemini 1.5 Pro"))

    # 找到所有对话文件进行测试
    dialogue_files = sorted(CONVERSATIONS_DIR.glob("*.txt"))
    if not dialogue_files:
        console.print("[bold red]错误：在 'conversations' 目录中未找到任何对话文件 (.txt)！[/bold red]")
        exit()

    all_results = []
    
    # 对每个文件，分别用两种模式测试
    for dialogue_file in dialogue_files:
        dialogue_id = dialogue_file.stem # "dialogue_1.txt" -> "dialogue_1"
        ground_truth_id = f"ground_truth_{dialogue_id.split('_')[1]}"
        
        console.print(f"\n--- [bold]开始测试: {dialogue_id}[/bold] ---")

        # 模式1: 仅LLM
        console.print(f"[*] 模式: [yellow]LLM Only[/yellow]")
        result_llm = run_single_test(dialogue_id, use_aux_extraction=False)
        all_results.append(result_llm)
        if result_llm["passed"]:
            console.print(f"  [green]✅ 通过[/green]")
        else:
            console.print(f"  [red]❌ 失败[/red]")
            # print(result_llm['diff']) # 如果需要看详细差异，可以取消这行注释

        # 模式2: LLM + 辅助提取
        console.print(f"[*] 模式: [cyan]LLM + Regex[/cyan]")
        result_hybrid = run_single_test(dialogue_id, use_aux_extraction=True)
        all_results.append(result_hybrid)
        if result_hybrid["passed"]:
            console.print(f"  [green]✅ 通过[/green]")
        else:
            console.print(f"  [red]❌ 失败[/red]")
            # print(result_hybrid['diff'])

        # 为了避免达到API速率限制
        time.sleep(1) 
        break

    # --- 生成最终报告 ---
    console.print("\n\n" + "="*50)
    console.print("[bold cyan]测试总结报告[/bold cyan]")
    console.print("="*50)

    # 准备表格数据
    table = Table(title="详细测试结果")
    table.add_column("对话ID", style="magenta")
    table.add_column("测试模式", style="cyan")
    table.add_column("结果", style="green")
    table.add_column("差异摘要", style="yellow")

    summary = {"LLM Only": {"passed": 0, "failed": 0}, "LLM + Regex": {"passed": 0, "failed": 0}}
    
    for res in all_results:
        status = "✅ 通过" if res["passed"] else "❌ 失败"
        diff_summary = "无差异" if res["passed"] else f"{len(res['diff'].get('values_changed', []))}项变更, {len(res['diff'].get('iterable_item_added', []))}项新增, {len(res['diff'].get('iterable_item_removed', []))}项移除"
        table.add_row(res["id"], res["mode"], status, diff_summary)
        summary[res["mode"]]["passed" if res["passed"] else "failed"] += 1
        
    console.print(table)

    # 打印通过率
    console.print("\n--- [bold]通过率统计[/bold] ---")
    for mode, counts in summary.items():
        total = counts["passed"] + counts["failed"]
        if total > 0:
            pass_rate = (counts["passed"] / total) * 100
            console.print(f"[cyan]{mode}:[/cyan] {counts['passed']} / {total} 通过，通过率: [bold { 'green' if pass_rate > 80 else 'yellow' }]{pass_rate:.2f}%[/bold]")

    # 保存详细报告到文件
    report_path = REPORTS_DIR / f"test_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    console.print(f"\n[bold]详细报告已保存至: [underline]{report_path}[/underline][/bold]")
