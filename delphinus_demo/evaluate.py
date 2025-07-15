# evaluate.py
import json
import asyncio
import argparse
import logging
import os
from datetime import datetime
from main import app  # 导入你的Graphiti App
from models import Document, ConversationSegment, Person, Project  # 显式导入模型以供类型检查
from graphiti_core.nodes import EntityNode, EpisodicNode  # 导入 EntityNode 和 EpisodicNode
from graphiti_core.edges import EntityEdge  # 导入 EntityEdge
from common_search import search_pipeline
from relevance_scorer import score_edges_relevance
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_CROSS_ENCODER,
    EDGE_HYBRID_SEARCH_CROSS_ENCODER
)

def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

# 创建日志目录
log_dir = "test_results"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "evaluate.log")

# 配置日志记录器
logger = logging.getLogger(__name__)
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


async def run_evaluation(ground_truth_file: str):
    """主评估函数"""
    try:
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"错误: 无法读取或解析 ground-truth 文件 {ground_truth_file}。错误: {e}")
        return

    success_count = 0
    total_count = len(dataset)
    results_log = []

    for i, item in enumerate(dataset):
        question = item["question"]
        expected = item.get("expected")
        
        if not expected:
            logger.warning(f"--- 跳过测试用例 {i+1}/{total_count}: 缺少 'expected' 字段 ---")
            continue

        log_entry = {"question": question, "status": "❌ FAILED"}
        logger.info(f"\n--- Running Test Case {i+1}/{total_count}: {item.get('description', '')} ---")
        logger.info(f"原始问题: {question}")

        # --- 开始多阶段搜索 ---
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

            rewritten_query = search_result_data["analysis_result"].get("rewritten_query", question)
            final_nodes = search_result_data["final_nodes"]
            final_edges = search_result_data["final_edges"]
            
            # --- 结束多阶段搜索 ---

            all_expectations_met = False
            edge_scores = []

            if final_edges:
                logger.info("正在对二次搜索返回的边进行相关性评分...")
                edge_scores = await score_edges_relevance(app, rewritten_query, final_edges)
                
                # 检查是否有任何一个fact或episode达到了完全匹配（10分）
                for score_info in edge_scores:
                    if score_info.get('fact_score') == 10:
                        logger.info(f"✅ PASSED - Found a perfect match in fact for edge {score_info.get('edge_uuid')}")
                        all_expectations_met = True
                        break
                    if 'episode_scores' in score_info:
                        for ep_score in score_info['episode_scores']:
                            if ep_score.get('score') == 10:
                                logger.info(f"✅ PASSED - Found a perfect match in episode {ep_score.get('episode_uuid')} for edge {score_info.get('edge_uuid')}")
                                all_expectations_met = True
                                break
                    if all_expectations_met:
                        break
            else:
                logger.warning("二次搜索没有返回任何边，测试失败。")


        except Exception as e:
            logger.error(f"执行搜索或评估时发生错误: {e}")
            all_expectations_met = False

        if all_expectations_met:
            log_entry["status"] = "✅ PASSED"
            success_count += 1
        else:
            logger.info("❌ FAILED - No perfect match found.")
            log_entry["status"] = "❌ FAILED"
        
        # 记录日志
        log_entry["final_results"] = {
            "nodes": [json.loads(n.model_dump_json()) for n in final_nodes] if 'final_nodes' in locals() else [],
            "edges": [json.loads(e.model_dump_json()) for e in final_edges] if 'final_edges' in locals() else [],
            "edge_scores": edge_scores
        }
        
        results_log.append(log_entry)
            
    logger.info(f"\n\n--- Evaluation Summary ---")
    accuracy = f"{success_count / total_count * 100:.2f}%" if total_count > 0 else "0.00%"
    logger.info(f"Accuracy: {accuracy} ({success_count}/{total_count})")
    
    try:
        results_log_json = json.dumps(results_log, indent=2, ensure_ascii=False, default=json_serializer)
        logger.info("--- 所有评估测试用例执行完毕 ---")
        logger.info(f"最终评估结果:\n{results_log_json}")
        logger.info(f"\n详细评估日志已保存到: {log_file_path}")
    except TypeError as e:
        logger.error(f"无法将评估结果序列化为 JSON: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 ground-truth 文件评估性能。")
    parser.add_argument("groundfile", type=str, help="包含问题和预期的 ground-truth JSON 文件的路径。")
    args = parser.parse_args()
    asyncio.run(run_evaluation(args.groundfile))
