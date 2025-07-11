# search.py
from main import app
import asyncio
import logging
import json
import argparse
from pydantic import BaseModel
from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode, EpisodicNode

# 配置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def model_to_dict(model_object: BaseModel) -> dict:
    """将 Pydantic 模型递归转储为字典，并移除 embedding 字段。"""
    content_dict = json.loads(model_object.model_dump_json())
    
    # 移除顶层的 embedding 字段
    content_dict.pop('fact_embedding', None)
    content_dict.pop('name_embedding', None)

    # 如果存在 'attributes' 键，就从中删除不想要的 embedding
    if 'attributes' in content_dict and isinstance(content_dict['attributes'], dict):
        content_dict['attributes'].pop('fact_embedding', None)
        content_dict['attributes'].pop('name_embedding', None)
        
    return content_dict

async def run_search(ground_truth_file: str):
    """
    从 ground-truth 文件读取问题，执行搜索，并将结果保存到输出文件。
    """
    try:
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"无法读取或解析 ground-truth 文件: {e}")
        return

    all_results = []
    total_cases = len(dataset)

    for i, item in enumerate(dataset):
        question = item.get("question")
        if not question:
            logging.warning(f"跳过第 {i+1} 个测试用例，因为它没有 'question' 字段。")
            continue

        logging.info(f"--- 正在执行测试用例 {i+1}/{total_cases}: {item.get('description', '')} ---")
        logging.info(f"问题: {question}")

        try:
            search_results = await app.search(question)
            
            # 将 Pydantic 模型转换为字典以便序列化
            results_as_dicts = [model_to_dict(res) for res in search_results]

            all_results.append({
                "question": question,
                "description": item.get("description", ""),
                "expected": item.get("expected"),
                "search_results": results_as_dicts
            })
            logging.info(f"查询成功，找到 {len(search_results)} 个结果。")

        except Exception as e:
            logging.error(f"为问题 '{question}' 执行搜索时发生错误: {e}")
            all_results.append({
                "question": question,
                "description": item.get("description", ""),
                "expected": item.get("expected"),
                "search_results": [],
                "error": str(e)
            })

    try:
        with open("./test_results/search_log.json", 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logging.info(f"\n所有搜索完成。结果已保存到: search_log.json")
    except IOError as e:
        logging.error(f"无法写入输出文件: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从 ground-truth 文件执行搜索查询并保存结果。")
    parser.add_argument("groundfile", type=str, help="包含查询问题的 ground-truth JSON 文件的路径。")
    args = parser.parse_args()

    asyncio.run(run_search(args.groundfile))
