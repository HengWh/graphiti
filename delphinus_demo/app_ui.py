# app_ui.py
import streamlit as st
from main import app
import asyncio

async def run_serach_st():
    st.title("💡 妙豚豚 - 个人记忆与智能工作系统 (MVP)")
    st.set_page_config(
        page_title="妙豚豚 - 个人记忆与智能工作系统 (MVP)",
        page_icon="🐷", # 可以是emoji
        layout="wide"  # "wide" 或 "centered"
    )

    query = st.text_input("请输入你的回忆：", "上周李明发我的关于‘盘古项目’的PPT")

    if st.button("开始回忆"):
        if query:
            with st.spinner("正在连接记忆深处..."):
                results = await app.search(query)
            
            st.success("找到了这些记忆片段！")
            
            for result in results:
                st.subheader(f"记忆类型: {result.__class__.__name__}")
                if result.__class__.__name__ == "EntityEdge":
                    st.write(f"**关系:** {getattr(result, 'name', 'N/A')}")
                    st.write(f"**事实:** {getattr(result, 'fact', 'N/A')}")
                    st.write(f"**源头:** {getattr(result, 'source_node_uuid', 'N/A')}")
                    st.write(f"**目标:** {getattr(result, 'target_node_uuid', 'N/A')}")
                else:
                    st.json(result.model_dump_json(indent=2, exclude={'attributes'}))
                st.divider()

        else:
            st.warning("请输入一些回忆的线索。")

        
if __name__ == "__main__":
    asyncio.run(run_serach_st())
