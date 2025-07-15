# app_ui.py
import streamlit as st
from main import app
import asyncio
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge
from typing import List, Dict, Any, Union
import pandas as pd

from query_preprocessor import preprocess_query_http
from relevance_scorer import score_nodes_relevance
from graphiti_core.search.search_config_recipes import (
    NODE_HYBRID_SEARCH_CROSS_ENCODER,
    EDGE_HYBRID_SEARCH_RRF
)

# 主函数（同步）
def run_search_st():
    st.set_page_config(
        page_title="妙豚豚 - 个人记忆与智能工作系统 (MVP)",
        page_icon="./delphinus.ico",
        layout="wide"
    )
    st.title("💡 妙豚豚 - 个人记忆与智能工作系统 (MVP)")

    query = st.text_input("请输入你的回忆：", "上周李明发我的关于‘盘古项目’的PPT")

    if st.button("开始回忆"):
        if query:
            # 修复多次点击按钮时的事件循环冲突问题
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                # --- 开始分步执行并实时展示 ---
                
                # 1. 查询预处理
                st.subheader("1. 查询理解与改写")
                with st.spinner("正在进行查询预处理..."):
                    analysis = loop.run_until_complete(preprocess_query_http(query))
                st.markdown(f"**原始问题:** `{query}`")
                st.markdown(f"**优化查询:** `{analysis.get('rewritten_query', 'N/A')}`")
                with st.expander("查看提取的实体和关系"):
                    st.markdown("**提取的实体:**")
                    st.json(analysis.get('nodes', []))
                    st.markdown("**推断的关系:**")
                    st.json(analysis.get('edges', []))
                
                rewritten_query = analysis.get("rewritten_query", query)

                # 2. 执行首次搜索
                st.subheader("2. 初步搜索与相关性评分")
                with st.spinner("正在执行首次搜索以召回相关节点..."):
                    initial_search_results = loop.run_until_complete(
                        app.search_(rewritten_query, config=NODE_HYBRID_SEARCH_CROSS_ENCODER)
                    )
                
                # 3. 对结果进行相关性打分并排序
                with st.spinner("正在对搜索结果进行相关性打分..."):
                    scored_nodes = loop.run_until_complete(
                        score_nodes_relevance(query, initial_search_results.nodes)
                    )
                
                if scored_nodes:
                    df = pd.DataFrame(scored_nodes)
                    df = df.rename(columns={'uuid': '节点id', 'score': '相关性分数', 'reason': '评分理由'})
                    st.dataframe(df[['节点id', '相关性分数', '评分理由']], use_container_width=True)
                else:
                    st.info("没有从初步搜索中获取到节点。")

                # 4. 基于高分相关节点进行二次搜索
                st.subheader("3. 二次搜索（对相关性评分9分及以上的节点执行）")
                high_score_info = [info for info in scored_nodes if info.get('score', 0) >= 9]
                
                final_nodes = initial_search_results.nodes
                final_edges = initial_search_results.edges
                
                if high_score_info:
                    with st.spinner(f"找到 {len(high_score_info)} 个高相关性节点，正在执行二次搜索..."):
                        high_score_node_uuids = [info['uuid'] for info in high_score_info]
                        nodes_by_uuid_initial = {str(node.uuid): node for node in initial_search_results.nodes}
                        high_score_nodes = [nodes_by_uuid_initial[uuid] for uuid in high_score_node_uuids if uuid in nodes_by_uuid_initial]
                        group_ids = list(set(node.group_id for node in high_score_nodes if node.group_id))

                        secondary_search_results = loop.run_until_complete(
                            app.search_(
                                rewritten_query,
                                config=EDGE_HYBRID_SEARCH_RRF,
                                group_ids=group_ids,
                                bfs_origin_node_uuids=high_score_node_uuids
                            )
                        )
                        
                        if secondary_search_results.nodes:
                            final_nodes = secondary_search_results.nodes
                        else:
                            final_nodes = high_score_nodes # 如果二次搜索没返回节点，则保留高分节点

                        final_edges = secondary_search_results.edges
                    st.success("二次搜索完成。")
                else:
                    st.info("未找到足够相关的节点，跳过二次搜索。")

                # --- 展示最终结果 ---
                st.header("最终回忆结果")
                
                if not final_nodes and not final_edges:
                    st.info("没有找到相关的记忆。")
                    st.stop()

                scores_by_uuid = {info['uuid']: {'score': info['score'], 'reason': info['reason']} for info in scored_nodes}

                st.subheader(f"找到 {len(final_nodes)} 个相关实体")
                for node in final_nodes:
                    score_info = scores_by_uuid.get(str(node.uuid))
                    score_text = f" (相关性: {score_info['score']} - {score_info['reason']})" if score_info else ""
                    st.markdown(f"#### {node.name}{score_text}")
                    st.markdown(f"**类型:** `{node.attributes.get('label', 'Entity')}`")
                    with st.expander("查看属性"):
                        st.json(node.attributes)

                st.divider()

                st.subheader(f"找到 {len(final_edges)} 条相关关系")
                if final_edges:
                    edge_node_uuids = set()
                    for edge in final_edges:
                        edge_node_uuids.add(edge.source_node_uuid)
                        edge_node_uuids.add(edge.target_node_uuid)
                    
                    try:
                        edge_nodes = loop.run_until_complete(EntityNode.get_by_uuids(app.driver, list(edge_node_uuids)))
                        nodes_by_uuid = {str(node.uuid): node for node in edge_nodes}
                    except Exception as e:
                        st.error(f"获取关系节点时出错: {e}")
                        nodes_by_uuid = {}

                    for edge in final_edges:
                        source_node = nodes_by_uuid.get(str(edge.source_node_uuid))
                        target_node = nodes_by_uuid.get(str(edge.target_node_uuid))
                        
                        st.markdown(f"##### 关系: {edge.name}")
                        st.caption(f"事实: {edge.fact}")

                        if source_node and target_node:
                            source_label = source_node.attributes.get('label', 'Entity')
                            target_label = target_node.attributes.get('label', 'Entity')
                            graph_definition = f"""
                            digraph {{
                                rankdir=LR;
                                node [shape=box, style="rounded,filled", fillcolor="#EFEFEF"];
                                "{source_node.name}\\n({source_label})" -> "{target_node.name}\\n({target_label})" [label="{edge.name}"];
                            }}
                            """
                            st.graphviz_chart(graph_definition)
                        else:
                            st.warning(f"无法完全渲染关系 `{edge.name}`，因为缺少源节点或目标节点的信息。")
                        st.markdown("---")
            finally:
                # 确保每次操作后都关闭驱动程序，以避免连接状态泄漏
                if app.driver and not loop.is_closed():
                    loop.run_until_complete(app.driver.close())
        else:
            st.warning("请输入一些回忆的线索。")

if __name__ == "__main__":
    run_search_st()
