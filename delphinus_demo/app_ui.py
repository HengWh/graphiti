# app_ui.py
import streamlit as st
from main import app
import asyncio
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge
from typing import List, Dict, Any, Union

# 异步函数：获取并处理单个边的详细信息
async def get_edge_details(edge: EntityEdge) -> Dict[str, Any]:
    source_node_task = EntityNode.get_by_uuid(app.driver, edge.source_node_uuid)
    target_node_task = EntityNode.get_by_uuid(app.driver, edge.target_node_uuid)
    
    episodic_nodes_task = None
    if edge.episodes:
        unique_episode_uuids = list(set(edge.episodes))
        episodic_nodes_task = EpisodicNode.get_by_uuids(app.driver, unique_episode_uuids)
    
    source_node, target_node, episodic_nodes = await asyncio.gather(
        source_node_task,
        target_node_task,
        episodic_nodes_task if episodic_nodes_task else asyncio.sleep(0, result=[])
    )
    
    return {
        "edge": edge,
        "source_node": source_node,
        "target_node": target_node,
        "episodic_nodes": episodic_nodes
    }

# 异步函数：执行搜索并获取所有处理好的结果
async def get_processed_search_results(query: str) -> List[Dict[str, Any]]:
    try:
        search_results = await app.search(query)
        
        processed_results = []
        if search_results:
            tasks = [get_edge_details(res) for res in search_results if isinstance(res, EntityEdge)]
            processed_results = await asyncio.gather(*tasks)
            
        # 添加对非EntityEdge类型结果的兼容处理
        for res in search_results:
            if not isinstance(res, EntityEdge):
                processed_results.append({"other": res})
                
        return processed_results
    finally:
        # 确保每次操作后都关闭驱动程序，以避免连接状态泄漏
        if app.driver:
            await app.driver.close()

# 主函数（同步）
def run_search_st():
    st.title("💡 妙豚豚 - 个人记忆与智能工作系统 (MVP)")
    st.set_page_config(
        page_title="妙豚豚 - 个人记忆与智能工作系统 (MVP)",
        page_icon="./delphinus.ico",
        layout="wide"
    )

    query = st.text_input("请输入你的回忆：", "上周李明发我的关于‘盘古项目’的PPT")

    if st.button("开始回忆"):
        if query:
            with st.spinner("正在连接记忆深处..."):
                # 修复多次点击按钮时的事件循环冲突问题
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                processed_results = loop.run_until_complete(get_processed_search_results(query))

            st.success("找到了这些记忆片段！")
            
            if not processed_results:
                st.info("没有找到相关的记忆。")
                return

            # 遍历预处理好的结果并渲染
            for data in processed_results:
                if "edge" in data:
                    result = data["edge"]
                    source_node = data["source_node"]
                    target_node = data["target_node"]
                    episodic_nodes = data["episodic_nodes"]

                    st.subheader(f"关系: {result.name}")
                    st.caption(f"事实: {result.fact}")

                    if source_node and target_node:
                        source_label = source_node.attributes.get('label', 'Entity')
                        target_label = target_node.attributes.get('label', 'Entity')
                        graph_definition = f"""
                        digraph {{
                            rankdir=LR;
                            node [shape=box, style="rounded,filled", fillcolor="#EFEFEF"];
                            "{source_node.name}\\n({source_label})" [id="{source_node.uuid}"];
                            "{target_node.name}\\n({target_label})" [id="{target_node.uuid}"];
                            "{source_node.name}\\n({source_label})" -> "{target_node.name}\\n({target_label})" [label="{result.name}"];
                        }}
                        """
                        st.graphviz_chart(graph_definition)

                    col1, col2 = st.columns(2)
                    with col1:
                        if source_node:
                            st.markdown(f"##### 源节点: {source_node.name}")
                            st.markdown(f"**类型:** `{source_node.attributes.get('label', 'Entity')}`")
                            with st.expander("查看属性"):
                                st.json(source_node.attributes)
                        else:
                            st.warning("未找到源节点信息。")
                    
                    with col2:
                        if target_node:
                            st.markdown(f"##### 目标节点: {target_node.name}")
                            st.markdown(f"**类型:** `{target_node.attributes.get('label', 'Entity')}`")
                            with st.expander("查看属性"):
                                st.json(target_node.attributes)
                        else:
                            st.warning("未找到目标节点信息。")

                    if episodic_nodes:
                        with st.expander("查看原始信息 (Episodes)"):
                            for epi_node in episodic_nodes:
                                st.markdown(f"**片段名称:** {getattr(epi_node, 'name', 'N/A')}")
                                st.markdown(f"**内容:**")
                                st.text(getattr(epi_node, 'content', ''))
                                st.caption(f"创建于: {epi_node.created_at.strftime('%Y-%m-%d %H:%M') if epi_node.created_at else 'N/A'}")
                                st.markdown("---")
                
                elif "other" in data:
                    result = data["other"]
                    st.subheader(f"记忆类型: {result.__class__.__name__}")
                    st.json(result.model_dump_json(indent=2, exclude={'attributes'}))
                
                st.divider()
        else:
            st.warning("请输入一些回忆的线索。")

if __name__ == "__main__":
    run_search_st()
