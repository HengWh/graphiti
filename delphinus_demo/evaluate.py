# evaluate.py
import json
import asyncio
import argparse
from datetime import datetime
from main import app  # 导入你的Graphiti App
from models import Document, ConversationSegment, Person, Project  # 显式导入模型以供类型检查
from graphiti_core.nodes import EntityNode, EpisodicNode  # 导入 EntityNode 和 EpisodicNode
from graphiti_core.edges import EntityEdge  # 导入 EntityEdge
from query_preprocessor import preprocess_query_http
from relevance_scorer import score_nodes_relevance, score_edges_relevance
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_CROSS_ENCODER,
    EDGE_HYBRID_SEARCH_RRF
)

def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

async def run_evaluation(ground_truth_file: str):
    """主评估函数"""
    try:
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"错误: 无法读取或解析 ground-truth 文件 {ground_truth_file}。错误: {e}")
        return

    success_count = 0
    total_count = len(dataset)
    results_log = []

    for i, item in enumerate(dataset):
        question = item["question"]
        expected = item.get("expected")
        
        if not expected:
            print(f"--- 跳过测试用例 {i+1}/{total_count}: 缺少 'expected' 字段 ---")
            continue

        log_entry = {"question": question, "status": "❌ FAILED"}
        print(f"\n--- Running Test Case {i+1}/{total_count}: {item.get('description', '')} ---")
        print(f"原始问题: {question}")

        # --- 开始多阶段搜索 ---
        try:
            # 1. 查询预处理
            print("正在进行查询预处理...")
            analysis_result = await preprocess_query_http(question)
            rewritten_query = analysis_result.get("rewritten_query", question)
            print(f"优化后的查询: {rewritten_query}")

            # 2. 执行首次搜索
            print("正在执行首次搜索...")
            initial_search_results = await app.search_(rewritten_query, config=NODE_HYBRID_SEARCH_CROSS_ENCODER)

            # 3. 对结果进行相关性打分
            print("正在对结果进行相关性打分...")
            scored_node_info = await score_nodes_relevance(question, initial_search_results.nodes)

            # 4. 基于高分节点进行二次搜索
            high_score_info = [info for info in scored_node_info if info.get('score', 0) >= 9]
            
            final_nodes = initial_search_results.nodes
            final_edges = initial_search_results.edges
            final_episodes = initial_search_results.episodes

            if high_score_info:
                print(f"找到 {len(high_score_info)} 个高相关性节点，执行二次搜索...")
                high_score_node_uuids = [info['uuid'] for info in high_score_info]
                nodes_by_uuid = {str(node.uuid): node for node in initial_search_results.nodes}
                high_score_nodes = [nodes_by_uuid[uuid] for uuid in high_score_node_uuids if uuid in nodes_by_uuid]
                group_ids = list(set(node.group_id for node in high_score_nodes if node.group_id))

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
                print("二次搜索完成。")
            else:
                print("没有找到相关性足够高的节点，跳过二次搜索。")

            # --- 结束多阶段搜索 ---

            all_expectations_met = False
            edge_scores = []

            if final_edges:
                print("正在对二次搜索返回的边进行相关性评分...")
                edge_scores = await score_edges_relevance(app, rewritten_query, final_edges)
                
                # 检查是否有任何一个fact或episode达到了完全匹配（10分）
                for score_info in edge_scores:
                    if score_info.get('fact_score') == 10:
                        print(f"✅ PASSED - Found a perfect match in fact for edge {score_info.get('edge_uuid')}")
                        all_expectations_met = True
                        break
                    if 'episode_scores' in score_info:
                        for ep_score in score_info['episode_scores']:
                            if ep_score.get('score') == 10:
                                print(f"✅ PASSED - Found a perfect match in episode {ep_score.get('episode_uuid')} for edge {score_info.get('edge_uuid')}")
                                all_expectations_met = True
                                break
                    if all_expectations_met:
                        break
            else:
                print("二次搜索没有返回任何边，测试失败。")


        except Exception as e:
            print(f"执行搜索或评估时发生错误: {e}")
            all_expectations_met = False

        if all_expectations_met:
            log_entry["status"] = "✅ PASSED"
            success_count += 1
        else:
            print("❌ FAILED - No perfect match found.")
            log_entry["status"] = "❌ FAILED"
        
        # 记录日志
        log_entry["final_results"] = {
            "nodes": [json.loads(n.model_dump_json()) for n in final_nodes] if 'final_nodes' in locals() else [],
            "edges": [json.loads(e.model_dump_json()) for e in final_edges] if 'final_edges' in locals() else [],
            "edge_scores": edge_scores
        }
        
        results_log.append(log_entry)
            
    print(f"\n\n--- Evaluation Summary ---")
    accuracy = f"{success_count / total_count * 100:.2f}%" if total_count > 0 else "0.00%"
    print(f"Accuracy: {accuracy} ({success_count}/{total_count})")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f'./test_results/evaluation_{timestamp}_{accuracy}.json'
    with open(log_filename, 'w', encoding='utf-8') as f:
        json.dump(results_log, f, indent=2, ensure_ascii=False, default=json_serializer)
    print(f"详细评估日志已保存到 {log_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 ground-truth 文件评估性能。")
    parser.add_argument("groundfile", type=str, help="包含问题和预期的 ground-truth JSON 文件的路径。")
    args = parser.parse_args()
    asyncio.run(run_evaluation(args.groundfile))
