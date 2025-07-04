# pipeline.py
import json
import asyncio
from datetime import datetime
from models import Person, Project, Document # 导入实体模型
from main import app # 导入我们配置好的 app 实例
from typing import List, Dict

# 步骤A：聚合 (Aggregation) - MVP 简化版
def aggregate_simple(messages: List[Dict]) -> Dict:
    """极其简化的聚合器：将所有消息视为一个片段"""
    full_text = "\n".join([f"{msg['sender']}: {msg['text']}" for msg in messages])
    participants = list(set([msg['sender'] for msg in messages]))
    return {
        "full_text": full_text,
        "participants": participants,
        "start_time": messages[0]['timestamp'],
        "end_time": messages[-1]['timestamp'],
        "source_channel": messages[0]['channel']
    }

# 组合成管道
async def run_ingestion_pipeline():
    # 1. 加载模拟数据
    # 假设此脚本从项目根目录运行
    with open('./test_data/mock_im_data.json', 'r', encoding='utf-8') as f:
        messages = json.load(f)

    # 2. 聚合
    aggregated_data = aggregate_simple(messages)

    # 3. 调用 add_episode 注入图谱
    # 这是 Graphiti 的核心方法，它会一步完成：
    # a. 创建一个代表本次对话的 EpisodicNode
    # b. 从对话文本 (episode_body) 中，根据 entity_types 自动抽取出 Person, Project, Document 等实体
    # c. 如果实体不存在，则创建新节点；如果已存在，则进行合并
    # d. 自动创建 (EpisodicNode) -[:MENTIONS]-> (EntityNode) 的关系
    # e. 自动在实体之间创建关系 (EntityNode) -[:RELATED_TO]-> (EntityNode)
    print("正在调用 add_episode 将数据注入图数据库...")
    
    # 解析时间戳
    try:
        # 假设时间戳是 ISO 8601 格式, e.g., "2024-07-04T14:30:00"
        ref_time = datetime.fromisoformat(aggregated_data["start_time"])
    except (ValueError, KeyError):
        # 如果格式不匹配或字段不存在，使用当前时间作为备用
        print("警告: 无法解析时间戳，将使用当前时间。")
        ref_time = datetime.now()

    results = await app.add_episode(
        name=f"IM Conversation from {aggregated_data['source_channel']}",
        episode_body=aggregated_data["full_text"],
        source_description=f"Channel: {aggregated_data['source_channel']}",
        reference_time=ref_time,
        entity_types={'Person': Person, 'Project': Project, 'Document': Document}, # type: ignore
    )
    
    print("注入完成！")
    print(f"创建了 Episode: {results.episode.uuid}")
    print(f"创建/更新了 {len(results.nodes)} 个实体节点。")
    print(f"创建了 {len(results.edges)} 条实体关系。")


if __name__ == "__main__":
    # 运行一次，将数据灌入你的 Neo4j
    # 由于 add_episode 是异步函数，我们需要使用 asyncio.run() 来执行
    asyncio.run(run_ingestion_pipeline())
