# test_entity_extraction.py

import os
import json
import re
import time
import argparse
import importlib
from pathlib import Path
from typing import List, Dict, Any, Callable

# --- 外部库 ---
import httpx
from dotenv import dotenv_values
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from deepdiff import DeepDiff

# --- 全局配置与初始化 ---
# 加载 .env 文件中的环境变量
config = dotenv_values(".env")

# 路径配置
BASE_DIR = Path(__file__).resolve().parent
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
        
    return entities

# --- Prompt & LLM 调用模块 ---

def call_llm_api(prompt: str) -> Dict[str, Any]:
    """
    直接调用OpenRouter API并返回解析后的JSON结果。
    """
    api_key = config.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 环境变量未设置！")

    # OpenRouter的URL通常是 https://openrouter.ai/api/v1
    # 我们将从环境变量中读取，如果未设置，则使用默认值
    base_url = config.get("GEMINI_BASE_URL")
    
    # 确保URL后面有 /chat/completions
    # /gemini/v1beta/models/{model}:generateContent
    request_url = f"{base_url.rstrip('/')}/v1beta/models/gemini-2.5-pro:generateContent"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 构造与Gemini API兼容的请求体
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    console.print(f"[grey50]正在调用模型 at {request_url}...[/grey50]")
    
    try:
        with httpx.Client() as client:
            response = client.post(request_url, headers=headers, json=payload, timeout=300)
            response.raise_for_status() # 如果HTTP状态码是4xx或5xx，则抛出异常

        # 提取并解析返回的JSON
        response_json = response.json()
        # Gemini API的响应结构与OpenAI不同
        message_content = response_json['candidates'][0]['content']['parts'][0]['text']
        
        # 清理并解析返回的JSON
        cleaned_response = re.sub(r'```json\s*|\s*```', '', message_content.strip())
        console.print(f"原始输出，解析出cleaned_response: {cleaned_response}")
        return json.loads(cleaned_response)

    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]HTTP错误: {e.response.status_code} - {e.response.text}[/bold red]")
        return {"entities": []}
    except json.JSONDecodeError:
        console.print("[bold red]错误：LLM返回的不是一个有效的JSON。[/bold red]")
        console.print(f"原始输出: {message_content}")
        return {"entities": []}
    except Exception as e:
        console.print(f"[bold red]调用LLM API时发生未知错误: {e}[/bold red]")
        return {"entities": []}

# --- 核心测试与评估逻辑 ---

def get_entity_key(entity: Dict) -> str:
    """
    获取用于比较的实体主键。
    对于Person类型，优先使用归一化后的文本；否则使用原始文本。
    增加健壮性，以处理LLM可能返回的不完整实体。
    """
    if not isinstance(entity, dict):
        return "" # 如果实体本身不是字典，返回空字符串

    # 优先使用归一化的Person名称
    if entity.get("type") == "Person":
        return entity.get("attributes", {}).get("normalized_text", entity.get("text") or entity.get("entity_name", ""))
    
    # 对于其他类型，优先使用 'text'，其次是 'entity_name'
    return entity.get("text") or entity.get("entity_name", "")

def generate_detailed_report(result: Dict) -> None:
    """
    为单个测试结果生成详细的Markdown对比报告。
    """
    if result["passed"]:
        return

    gt_entities = {get_entity_key(e): e for e in result['ground_truth']['entities']}
    pred_entities = {get_entity_key(e): e for e in result['prediction']['entities']}
    
    gt_keys = set(gt_entities.keys())
    pred_keys = set(pred_entities.keys())

    correctly_identified = gt_keys.intersection(pred_keys)
    missed = gt_keys.difference(pred_keys)
    added = pred_keys.difference(gt_keys)

    report_content = f"# 测试报告: {result['id']} ({result['mode']})\n\n"
    report_content += f"**结果: {'✅ 通过' if result['passed'] else '❌ 失败'}**\n\n"
    
    report_content += "## 对比详情\n\n"

    def format_entity(entity):
        key = get_entity_key(entity)
        entity_type = entity.get('type', 'N/A') # 安全地获取类型
        original_text = entity.get('text', 'N/A') # 安全地获取原文

        if entity_type == 'Person' and 'normalized_text' in entity.get('attributes', {}):
            return f"**{key}** (原文: `{original_text}`, 类型: `{entity_type}`)"
        return f"**{key}** (类型: `{entity_type}`)"

    # 1. 正确识别的实体
    report_content += f"### ✅ 正确识别 ({len(correctly_identified)})\n"
    if correctly_identified:
        for key in sorted(list(correctly_identified)):
            report_content += f"- {format_entity(gt_entities[key])}\n"
    else:
        report_content += "> 无\n"
    report_content += "\n"

    # 2. 遗漏的实体
    report_content += f"### ❌ 遗漏的实体 ({len(missed)})\n"
    if missed:
        for key in sorted(list(missed)):
            report_content += f"- {format_entity(gt_entities[key])}\n"
    else:
        report_content += "> 无\n"
    report_content += "\n"

    # 3. 新增的实体
    report_content += f"### ⚠️ 新增的实体 ({len(added)})\n"
    if added:
        for key in sorted(list(added)):
            report_content += f"- {format_entity(pred_entities[key])}\n"
    else:
        report_content += "> 无\n"
    report_content += "\n"

    # 4. 原始Diff (可选)
    if result['diff']:
        report_content += "## 原始差异 (JSON)\n"
        report_content += "```json\n"
        report_content += json.dumps(result['diff'], ensure_ascii=False, indent=2)
        report_content += "\n```\n"

    report_filename = REPORTS_DIR / f"report_{result['id']}_{result['mode'].replace(' + ', '_')}.md"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report_content)
    console.print(f"  [grey50]详细对比报告已生成: {report_filename}[/grey50]")


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

def calculate_metrics(ground_truth: List[Dict], prediction: List[Dict]) -> Dict[str, float]:
    """
    计算 Precision, Recall 和 F1-Score.
    """
    gt_keys = {get_entity_key(e) for e in ground_truth}
    pred_keys = {get_entity_key(e) for e in prediction}

    tp = len(gt_keys.intersection(pred_keys))
    fp = len(pred_keys.difference(gt_keys))
    fn = len(gt_keys.difference(pred_keys))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }

def run_single_test(
    dialogue_id: str,
    ground_truth_id: str,
    use_aux_extraction: bool,
    conversations_dir: Path,
    ground_truths_dir: Path,
    prompt_creation_func: Callable[[str], str]
) -> Dict:
    """
    对单个对话文件执行一次完整的测试。
    """
    dialogue_file = conversations_dir / f"{dialogue_id}.txt"
    ground_truth_file = ground_truths_dir / f"{ground_truth_id}.json"

    # 1. 读取输入文件
    with open(dialogue_file, 'r', encoding='utf-8') as f:
        dialogue_text = f.read()
    with open(ground_truth_file, 'r', encoding='utf-8') as f:
        ground_truth_data = json.load(f)

    # 2. 生成Prompt并获取LLM预测结果
    prompt = prompt_creation_func(dialogue_text)
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
    sorted_ground_truth = sorted(ground_truth_data["entities"], key=get_entity_key)
    sorted_prediction = sorted(final_prediction_entities, key=get_entity_key)

    final_prediction = {"conversation_id": dialogue_id, "entities": sorted_prediction}
    ground_truth_data['entities'] = sorted_ground_truth

    # 5. 比较结果
    diff = DeepDiff(ground_truth_data, final_prediction,
                ignore_order=True,
                # 'exclude_paths' 用于精确匹配，适合 conversation_id
                exclude_paths=["root['conversation_id']"],
                # 'exclude_regex_paths' 用于模式匹配，适合列表中的字段
                exclude_regex_paths=[r"root\['entities'\]\[\d+\]\['context'\]"])

    # 6. 计算评估指标
    metrics = calculate_metrics(ground_truth_data["entities"], final_prediction_entities)
    
    result_data = {
        "id": dialogue_id,
        "mode": "LLM + Regex" if use_aux_extraction else "LLM Only",
        "passed": not bool(diff),
        "metrics": metrics,
        "diff": json.loads(diff.to_json()) if diff else {},
        "ground_truth": ground_truth_data,
        "prediction": final_prediction
    }

    # 生成详细报告
    generate_detailed_report(result_data)
        
    return result_data

# --- 主程序入口 ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="实体提取能力评估测试脚本")
    parser.add_argument(
        "--test_set", 
        type=str, 
        default="conversations",
        help="测试集目录的名称 (例如 'conversations' 或 'simple_test_cases')。"
    )
    parser.add_argument(
        "--prompt_module",
        type=str,
        default="prompts.extract_entity",
        help="用于创建Prompt的Python模块 (例如 'prompts.extract_entity')。"
    )
    args = parser.parse_args()

    # --- 动态加载配置 ---
    # 路径配置
    conversations_dir = BASE_DIR / args.test_set / "conversations"
    ground_truths_dir = BASE_DIR / args.test_set / "ground_truths"
    if not conversations_dir.exists() or not ground_truths_dir.exists():
        console.print(f"[bold red]错误：测试集目录 '{args.test_set}' 不存在或不完整。[/bold red]")
        exit()

    # 动态导入Prompt创建函数
    try:
        prompt_lib = importlib.import_module(args.prompt_module)
        create_extraction_prompt = getattr(prompt_lib, "create_extraction_prompt")
    except (ImportError, AttributeError):
        console.print(f"[bold red]错误：无法从模块 '{args.prompt_module}' 加载 'create_extraction_prompt' 函数。[/bold red]")
        exit()

    console.print(Panel(f"[bold cyan]实体提取能力评估测试启动[/bold cyan]\n"
                        f"测试集: [yellow]{args.test_set}[/yellow]\n"
                        f"Prompt模块: [yellow]{args.prompt_module}[/yellow]",
                        title="EVALUATION SUITE", subtitle="Powered by Gemini 2.5 Pro"))

    # 找到所有对话文件进行测试
    dialogue_files = sorted(conversations_dir.glob("*.txt"))
    if not dialogue_files:
        console.print(f"[bold red]错误：在 '{conversations_dir}' 目录中未找到任何对话文件 (.txt)！[/bold red]")
        exit()

    all_results = []
    
    # 对每个文件，分别用两种模式测试
    for dialogue_file in dialogue_files:
        dialogue_id = dialogue_file.stem
        # 构造对应的 ground_truth_id, e.g., "dialogue_simple_1" -> "ground_truth_simple_1"
        gt_suffix = "_".join(dialogue_id.split('_')[1:])
        ground_truth_id = f"ground_truth_{gt_suffix}"
        
        console.print(f"\n--- [bold]开始测试: {dialogue_id}[/bold] ---")

        # 模式1: 仅LLM
        console.print(f"[*] 模式: [yellow]LLM Only[/yellow]")
        result_llm = run_single_test(
            dialogue_id, 
            ground_truth_id, 
            use_aux_extraction=False,
            conversations_dir=conversations_dir,
            ground_truths_dir=ground_truths_dir,
            prompt_creation_func=create_extraction_prompt
        )
        all_results.append(result_llm)
        if result_llm["passed"]:
            console.print(f"  [green]✅ 通过[/green]")
        else:
            console.print(f"  [red]❌ 失败[/red]")
            # print(result_llm['diff']) # 如果需要看详细差异，可以取消这行注释

        # # 模式2: LLM + 辅助提取
        # console.print(f"[*] 模式: [cyan]LLM + Regex[/cyan]")
        # result_hybrid = run_single_test(
        #     dialogue_id, 
        #     ground_truth_id, 
        #     use_aux_extraction=True,
        #     conversations_dir=conversations_dir,
        #     ground_truths_dir=ground_truths_dir,
        #     prompt_creation_func=create_extraction_prompt
        # )
        # all_results.append(result_hybrid)
        # if result_hybrid["passed"]:
        #     console.print(f"  [green]✅ 通过[/green]")
        # else:
        #     console.print(f"  [red]❌ 失败[/red]")
        #     # print(result_hybrid['diff'])

        # 为了避免达到API速率限制
        time.sleep(1)
        # break # 移除break以测试所有文件

    # --- 生成最终报告 ---
    console.print("\n\n" + "="*50)
    console.print("[bold cyan]测试总结报告[/bold cyan]")
    console.print("="*50)

    # 准备表格数据
    table = Table(title="详细测试结果")
    table.add_column("对话ID", style="magenta")
    table.add_column("测试模式", style="cyan")
    table.add_column("P/R/F1", style="blue")
    table.add_column("TP/FP/FN", style="yellow")
    table.add_column("DeepDiff结果", style="green")

    summary = {"LLM Only": {"passed": 0, "failed": 0, "tp": 0, "fp": 0, "fn": 0}, 
               "LLM + Regex": {"passed": 0, "failed": 0, "tp": 0, "fp": 0, "fn": 0}}
    
    for res in all_results:
        metrics = res["metrics"]
        status = "✅ 通过" if res["passed"] else "❌ 失败"
        metrics_str = f"{metrics['precision']:.2f}/{metrics['recall']:.2f}/[bold]{metrics['f1_score']:.2f}[/bold]"
        counts_str = f"[green]{metrics['tp']}[/green]/[red]{metrics['fp']}[/red]/[yellow]{metrics['fn']}[/yellow]"
        table.add_row(res["id"], res["mode"], metrics_str, counts_str, status)
        
        summary[res["mode"]]["passed" if res["passed"] else "failed"] += 1
        summary[res["mode"]]["tp"] += metrics["tp"]
        summary[res["mode"]]["fp"] += metrics["fp"]
        summary[res["mode"]]["fn"] += metrics["fn"]
        
    console.print(table)

    # 打印宏观评估指标
    console.print("\n--- [bold]宏观评估指标 (Macro Average)[/bold] ---")
    for mode, counts in summary.items():
        total_tests = counts["passed"] + counts["failed"]
        if total_tests > 0:
            pass_rate = (counts["passed"] / total_tests) * 100
            
            # 计算宏观 P/R/F1
            macro_p = counts["tp"] / (counts["tp"] + counts["fp"]) if (counts["tp"] + counts["fp"]) > 0 else 0.0
            macro_r = counts["tp"] / (counts["tp"] + counts["fn"]) if (counts["tp"] + counts["fn"]) > 0 else 0.0
            macro_f1 = 2 * (macro_p * macro_r) / (macro_p + macro_r) if (macro_p + macro_r) > 0 else 0.0
            
            color = "green" if pass_rate > 80 else "yellow"
            console.print(f"[cyan]{mode}:[/cyan]")
            console.print(f"  - DeepDiff通过率: [bold {color}]{pass_rate:.2f}%[/bold {color}] ({counts['passed']} / {total_tests})")
            console.print(f"  - 宏观F1-Score: [bold blue]{macro_f1:.3f}[/bold blue] (P: {macro_p:.3f}, R: {macro_r:.3f})")

    # 保存详细的JSON格式总结报告
    report_path = REPORTS_DIR / f"summary_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    console.print(f"\n[bold]详细报告已保存至: [underline]{report_path}[/underline][/bold]")
