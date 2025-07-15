# search.py
from main import app
import asyncio
import logging
import json
import argparse
import os
from pydantic import BaseModel
from typing import Optional

from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode, EpisodicNode
from common_search import search_pipeline
from graphiti_core.search.search_config_recipes import (
    EDGE_HYBRID_SEARCH_CROSS_ENCODER,
    NODE_HYBRID_SEARCH_CROSS_ENCODER
)

# 创建日志目录
log_dir = "test_results"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "search.log")

# 获取根日志记录器并进行配置
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 如果已经有处理器，先移除，防止重复记录
if logger.hasHandlers():
    logger.handlers.clear()

# 创建文件处理器
file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))

# 创建流处理器
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))

# 添加处理器到日志记录器
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

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
        logger.error(f"无法读取或解析 ground-truth 文件: {e}")
        return

    all_results = []
    total_cases = len(dataset)

    for i, item in enumerate(dataset):
        question = item.get("question")
        if not question:
            logger.warning(f"跳过第 {i+1} 个测试用例，因为它没有 'question' 字段。")
            continue

        logger.info(f"--- 正在执行测试用例 {i+1}/{total_cases}: {item.get('description', '')} ---")
        logger.info(f"原始问题: {question}")

        try:
            search_result_data = await search_pipeline(
                app=app,
                question=question,
                logger=logger,
                initial_search_config=NODE_HYBRID_SEARCH_CROSS_ENCODER,
                secondary_search_config=EDGE_HYBRID_SEARCH_CROSS_ENCODER
            )

            if not search_result_data["success"]:
                raise Exception(search_result_data.get("error", "未知错误"))

            # 从返回结果中提取数据
            analysis_result = search_result_data["analysis_result"]
            scored_node_info = search_result_data["scored_node_info"]
            final_nodes = search_result_data["final_nodes"]
            final_edges = search_result_data["final_edges"]
            final_episodes = search_result_data["final_episodes"]

            # 创建一个从 uuid 到分数的映射
            scores_by_uuid = {info['uuid']: {'relevance_score': info['score'], 'relevance_reason': info['reason']} for info in scored_node_info}
            
            # 将 Pydantic 模型转换为字典并附加分数
            nodes_as_dicts = []
            for node in final_nodes:
                node_dict = model_to_dict(node)
                score_info = scores_by_uuid.get(str(node.uuid))
                if score_info:
                    node_dict.update(score_info)
                nodes_as_dicts.append(node_dict)

            results_as_dicts = {
                "nodes": nodes_as_dicts,
                "edges": [model_to_dict(res) for res in final_edges],
                "episodes": [model_to_dict(res) for res in final_episodes]
            }

            all_results.append({
                "question": question,
                "description": item.get("description", ""),
                "expected": item.get("expected"),
                "query_analysis": analysis_result,
                "search_results": results_as_dicts,
            })
            logger.info(
                f"查询成功，找到 {len(final_nodes)} 个节点, {len(final_edges)} 条关系, {len(final_episodes)} 条源数据集。"
            )

        except Exception as e:
            logger.error(f"为问题 '{question}' 执行搜索时发生错误: {e}")
            all_results.append({
                "question": question,
                "description": item.get("description", ""),
                "expected": item.get("expected"),
                "query_analysis": locals().get("analysis_result"),
                "search_results": [],
                "error": str(e)
            })

    try:
        # 将 all_results 记录到日志中
        all_results_json = json.dumps(all_results, indent=2, ensure_ascii=False)
        logger.info("--- 所有测试用例执行完毕 ---")
        logger.info(f"最终结果:\n{all_results_json}")
        logger.info(f"\n所有搜索完成。结果已保存到: {log_file_path}")
    except TypeError as e:
        logger.error(f"无法将结果序列化为 JSON: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从 ground-truth 文件执行搜索查询并保存结果。")
    parser.add_argument("groundfile", type=str, help="包含查询问题的 ground-truth JSON 文件的路径。")
    args = parser.parse_args()

    asyncio.run(run_search(args.groundfile))
