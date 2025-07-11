# query_test.py
from main import app
import asyncio
import logging
import json
from pydantic import BaseModel
from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EntityNode, EpisodicNode

# 配置日志记录器，将输出重定向到 test_search.log 文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    filename='test_search.log',
    filemode='w',  # 'w' 表示每次运行都覆盖文件内容
    encoding='utf-8'  # 指定文件编码为 UTF-8
)
# 如果也想在控制台看到输出，可以添加一个 StreamHandler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)


def dump_and_clean(model_object: BaseModel) -> str:
    """
    将 Pydantic 模型转储为字典，移除 embedding 字段，
    并返回格式化的 JSON 字符串。
    """
    content_dict = model_object.model_dump()
    
    # 移除顶层的 embedding 字段
    content_dict.pop('fact_embedding', None)
    content_dict.pop('name_embedding', None)

    # 如果存在 'attributes' 键，就从中删除不想要的 embedding
    if 'attributes' in content_dict and isinstance(content_dict['attributes'], dict):
        content_dict['attributes'].pop('fact_embedding', None)
        content_dict['attributes'].pop('name_embedding', None)
        
    return json.dumps(content_dict, indent=2, ensure_ascii=False, default=str)


async def search_scenario_one():
    query = "李明发给小王的那份文件是什么？"
    logging.info(f"Executing query: {query}")
    
    # app.search() 是“双脑”的入口
    # 1. 语义大脑 (KG): LLM 会从 query 中提取实体 {"Person": "李明"}, {"Person": "小王"}, {"Project": "盘古项目"}, {"Document.type": "PPT"}
    # 2. 情景大脑 (CG): Graphiti 将这些实体转化为图谱查询的起点，在图中寻找与这些实体都相关的节点和路径。
    # 3. 融合与排序: 返回最相关的结果。
    results = await app.search(query)
    
    logging.info("\n--- Search Results ---")
    for result in results:
        logging.info(f"Type: {result.__class__.__name__}")
        logging.info(f"Content: {dump_and_clean(result)}")
        
        if isinstance(result, EntityEdge):
            # 获取并打印相关的节点信息
            logging.info("\n--- Associated Nodes ---")
            
            # 获取源节点和目标节点
            entity_node_uuids = [result.source_node_uuid, result.target_node_uuid]
            # 修正：app 对象本身就是 Graphiti 实例，直接访问其 driver 属性
            entity_nodes = await EntityNode.get_by_uuids(app.driver, entity_node_uuids)
            for node in entity_nodes:
                logging.info(f"\n--- Entity Node (Source/Target) ---")
                logging.info(f"Node Type: {node.__class__.__name__}")
                logging.info(dump_and_clean(node))

            # 获取情景节点
            if result.episodes:
                # 修正：app 对象本身就是 Graphiti 实例，直接访问其 driver 属性
                episode_nodes = await EpisodicNode.get_by_uuids(app.driver, result.episodes)
                for node in episode_nodes:
                    logging.info(f"\n--- Episodic Node (Source of Fact) ---")
                    logging.info(f"Node Type: {node.__class__.__name__}")
                    logging.info(dump_and_clean(node))
            
        logging.info("-" * 20)
        
if __name__ == "__main__":
    asyncio.run(search_scenario_one())
