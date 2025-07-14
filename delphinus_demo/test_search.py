# test_search.py
from main import app
import asyncio
import logging
import json
import argparse
from pydantic import BaseModel
from typing import Optional

from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode, EpisodicNode
from query_preprocessor import preprocess_query_http
from relevance_scorer import score_nodes_relevance
from graphiti_core.search.search_config_recipes import (
    COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    EDGE_HYBRID_SEARCH_NODE_DISTANCE,
    EDGE_HYBRID_SEARCH_CROSS_ENCODER,
    EDGE_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_CROSS_ENCODER
)

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
        logging.info(f"原始问题: {question}")

        try:
            # 1. 查询预处理
            logging.info("正在进行查询预处理...")
            analysis_result = await preprocess_query_http(question)
            rewritten_query = analysis_result.get("rewritten_query", question)
            logging.info(f"优化后的查询: {rewritten_query}")
            logging.info(f"查询中提到的实体: {analysis_result.get('nodes')}")
            logging.info(f"查询中隐含的关系: {analysis_result.get('edges')}")

            # 2. 执行搜索
            # search_results = await app.search_(rewritten_query)
            search_results = await app.search_(rewritten_query, config=NODE_HYBRID_SEARCH_CROSS_ENCODER) 

            # 3. 对结果进行相关性打分并排序
            logging.info("正在对搜索结果进行相关性打分和排序...")
            scored_node_info = await score_nodes_relevance(question, search_results.nodes)

            # 4. 基于高分相关节点进行二次搜索
            high_score_info = [info for info in scored_node_info if info.get('score', 0) >= 9]

            # 准备最终要展示的结果变量
            final_nodes = search_results.nodes
            final_edges = search_results.edges
            final_episodes = search_results.episodes

            if high_score_info:
                logging.info(f"找到 {len(high_score_info)} 个高相关性节点 (>=9 分)，执行二次搜索...")
                
                # 提取二次搜索参数
                high_score_node_uuids = [info['uuid'] for info in high_score_info]
                nodes_by_uuid = {str(node.uuid): node for node in search_results.nodes}
                high_score_nodes = [nodes_by_uuid[uuid] for uuid in high_score_node_uuids if uuid in nodes_by_uuid]
                group_ids = list(set(node.group_id for node in high_score_nodes if node.group_id))

                logging.info(f"二次搜索参数: bfs_origin_node_uuids={high_score_node_uuids}, group_ids={group_ids}")

                # 执行二次搜索
                secondary_search_results = await app.search_(
                    rewritten_query,
                    config=EDGE_HYBRID_SEARCH_RRF,
                    group_ids=group_ids,
                    bfs_origin_node_uuids=high_score_node_uuids
                )

                if secondary_search_results.nodes:
                    final_nodes = secondary_search_results.nodes
                else:
                    final_nodes = high_score_nodes

                final_edges = secondary_search_results.edges
                final_episodes = secondary_search_results.episodes
                logging.info(f"二次搜索完成，找到{len(final_edges)} 条关系。")
                
            else:
                logging.info("没有找到相关性足够高的节点 (>=9 分)，跳过二次搜索。")

            # 创建一个从 uuid 到分数的映射，以便在最终输出中添加分数
            scores_by_uuid = {info['uuid']: {'relevance_score': info['score'], 'relevance_reason': info['reason']} for info in scored_node_info}
            
            # 将 Pydantic 模型转换为字典以便序列化，并附加分数
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
            logging.info(
                f"查询成功，找到 {len(final_nodes)} 个节点, {len(final_edges)} 条关系, {len(final_episodes)} 条源数据集。"
            )

        except Exception as e:
            logging.error(f"为问题 '{question}' 执行搜索时发生错误: {e}")
            all_results.append({
                "question": question,
                "description": item.get("description", ""),
                "expected": item.get("expected"),
                "query_analysis": analysis_result if 'analysis_result' in locals() else None,
                "search_results": [],
                "error": str(e)
            })

    try:
        # 确保 test_results 目录存在
        import os
        os.makedirs("./test_results", exist_ok=True)
        output_path = "./test_results/test_search_log.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        logging.info(f"\n所有搜索完成。结果已保存到: {output_path}")
    except IOError as e:
        logging.error(f"无法写入输出文件: {e}")

if __name__ == "__main__":
    ground_truth_file = "./test_data/mock-ground-truth.json"
    asyncio.run(run_search(ground_truth_file))
