# delphinus_demo/common_search.py
import logging
from typing import Any, Dict, Optional

from graphiti_core.graphiti import Graphiti
from query_preprocessor import preprocess_query_http
from relevance_scorer import score_nodes_relevance, score_edges_relevance
from graphiti_core.search.search_config import SearchConfig

async def search_pipeline(
    app: Graphiti,
    question: str,
    logger: logging.Logger,
    initial_search_config: SearchConfig,
    secondary_search_config: Optional[SearchConfig] = None,
    relevance_threshold: int = 9,
) -> Dict[str, Any]:
    """
    一个通用的搜索流程，包括查询预处理、初次搜索、相关性打分和可选的二次搜索。

    :param app: Graphiti 应用实例。
    :param question: 用户的原始问题。
    :param logger: 用于记录日志的 logging.Logger 实例。
    :param initial_search_config: 首次搜索的配置。
    :param secondary_search_config: 二次搜索的配置。
    :param relevance_threshold: 触发二次搜索的相关性分数阈值。
    :return: 一个包含搜索结果和分析的字典。
    """
    try:
        # 1. 查询预处理
        logger.info("正在进行查询预处理...")
        analysis_result = await preprocess_query_http(question)
        rewritten_query = analysis_result.get("rewritten_query", question)
        logger.info(f"优化后的查询: {rewritten_query}")
        logger.info(f"查询中提到的实体: {analysis_result.get('nodes')}")
        logger.info(f"查询中隐含的关系: {analysis_result.get('edges')}")

        # 2. 执行首次搜索
        logger.info("正在执行首次搜索...")
        search_results = await app.search_(rewritten_query, config=initial_search_config)

        # 3. 对结果进行相关性打分并排序
        logger.info("正在对搜索结果进行相关性打分和排序...")
        scored_node_info = await score_nodes_relevance(question, search_results.nodes)

        # 4. 基于高分相关节点进行二次搜索
        high_score_info = [info for info in scored_node_info if info.get('score', 0) >= relevance_threshold]

        final_nodes = search_results.nodes
        final_edges = search_results.edges
        final_episodes = search_results.episodes

        if high_score_info and secondary_search_config:
            logger.info(f"找到 {len(high_score_info)} 个高相关性节点 (>=9 分)，执行二次搜索...")
            
            high_score_node_uuids = [info['uuid'] for info in high_score_info]
            nodes_by_uuid = {str(node.uuid): node for node in search_results.nodes}
            high_score_nodes = [nodes_by_uuid[uuid] for uuid in high_score_node_uuids if uuid in nodes_by_uuid]
            group_ids = list(set(node.group_id for node in high_score_nodes if node.group_id))

            logger.info(f"二次搜索参数: bfs_origin_node_uuids={high_score_node_uuids}.  未使用group_ids={group_ids}")

            # 暂时不传groupids，看能否筛选出结果
            secondary_search_results = await app.search_(
                rewritten_query,
                config=secondary_search_config,
                bfs_origin_node_uuids=high_score_node_uuids
            )

            if secondary_search_results.nodes:
                final_nodes = secondary_search_results.nodes
            else:
                final_nodes = high_score_nodes

            final_edges = secondary_search_results.edges
            final_episodes = secondary_search_results.episodes
            logger.info(f"二次搜索完成，找到{len(final_edges)} 条关系。")

            # 对二次搜索结果中的边进行相关性打分和过滤
            if final_edges:
                logger.info(f"正在对 {len(final_edges)} 条边进行相关性打分...")
                edge_scores = await score_edges_relevance(app, question, final_edges)
                
                high_score_edge_uuids = {
                    score['uuid'] for score in edge_scores if score.get('score', 0) >= 6
                }
                
                original_edge_count = len(final_edges)
                final_edges = [edge for edge in final_edges if str(edge.uuid) in high_score_edge_uuids]
                logger.info(f"边相关性过滤完成：保留 {len(final_edges)}/{original_edge_count} 条边 (>=6 分)。")

        else:
            logger.info(f"没有找到相关性足够高的节点 (>={relevance_threshold} 分)或未配置二次搜索，跳过二次搜索。")

        return {
            "success": True,
            "analysis_result": analysis_result,
            "scored_node_info": scored_node_info,
            "final_nodes": final_nodes,
            "final_edges": final_edges,
            "final_episodes": final_episodes,
        }

    except Exception as e:
        logger.error(f"在搜索流程中发生错误: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "analysis_result": locals().get("analysis_result"),
            "scored_node_info": [],
            "final_nodes": [],
            "final_edges": [],
            "final_episodes": [],
        }
