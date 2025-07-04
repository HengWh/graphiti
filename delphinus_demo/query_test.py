# query_test.py
from main import app
import asyncio

async def search_scenario_one():
    query = "小王，帮我找下上周李明发我的那份关于‘盘古项目’的PPT。"
    print(f"Executing query: {query}")
    
    # app.search() 是“双脑”的入口
    # 1. 语义大脑 (KG): LLM 会从 query 中提取实体 {"Person": "李明"}, {"Person": "小王"}, {"Project": "盘古项目"}, {"Document.type": "PPT"}
    # 2. 情景大脑 (CG): Graphiti 将这些实体转化为图谱查询的起点，在图中寻找与这些实体都相关的节点和路径。
    # 3. 融合与排序: 返回最相关的结果。
    results = await app.search(query)
    
    print("\n--- Search Results ---")
    for result in results:
        # result 是一个 Pydantic 对象，这里可能是 ConversationSegment 或 Document
        print(f"Type: {result.__class__.__name__}")
        print(f"Content: {result.model_dump_json(indent=2, exclude={'attributes'})}")
        print("-" * 20)
        
if __name__ == "__main__":
    asyncio.run(search_scenario_one())
