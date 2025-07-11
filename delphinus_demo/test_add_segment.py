# pipeline.py
import json
import asyncio
from datetime import datetime, timezone
from models import Person, Project, Document, ConversationSegment # 导入实体模型
from main import app # 导入我们配置好的 app 实例
from typing import List, Dict
from graphiti_core.nodes import CommunityNode, EntityNode, EpisodeType, EpisodicNode
from graphiti_core.edges import EntityEdge, EpisodicEdge

# 组合成管道
async def run_ingestion_pipeline():
    # 1. 加载已聚合的模拟数据
    # 假设此脚本在项目根目录(graphiti)下运行
    try:
        with open('./test_data/mock-segment.json', 'r', encoding='utf-8') as f:
            segments = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: 解析JSON文件 './test_data/mock-segment.json' 失败: {e}")
        segments = []

    # 2. 遍历每个聚合后的片段，并注入图谱
    for segment_data in segments:
        # 3. 调用 add_episode 注入图谱
        # 这是 Graphiti 的核心方法，它会一步完成：
        # a. 创建一个代表本次对话的 EpisodicNode
        # b. 从对话文本 (episode_body) 中，根据 entity_types 自动抽取出 Person, Project, Document 等实体
        # c. 如果实体不存在，则创建新节点；如果已存在，则进行合并
        # d. 自动创建 (EpisodicNode) -[:MENTIONS]-> (EntityNode) 的关系
        # e. 自动在实体之间创建关系 (EntityNode) -[:RELATED_TO]-> (EntityNode)
        print(f"--- 正在处理 Segment: {segment_data['id']} ---")
        
        # 解析时间戳
        try:
            # 新格式的时间戳是毫秒级的Unix timestamp
            start_time_seconds = segment_data["timeRange"]["start_time"] / 1000
            ref_time = datetime.fromtimestamp(start_time_seconds, tz=timezone.utc)
        except (ValueError, KeyError, TypeError):
            print("警告: 无法解析时间戳，将使用当前时间。")
            ref_time = datetime.now()

        # 为整个 segment 定义一个 group_id
        group_id = segment_data['task_id'] + segment_data['id']
        group_name = segment_data['task_name'] + segment_data['id']
        
        # 遍历每条消息并单独注入
        for i, message_body in enumerate(segment_data["messages"]):
            print(f"--- 正在导入 Message {i+1}/{len(segment_data['messages'])} from Segment: {group_id} ---")
            print(f"Message Body: {message_body}")

            # 3. 调用 add_episode
            results = await app.add_episode(
                name=f"{group_name}-{i}", # 为每条消息创建唯一的 name
                episode_body=message_body,
                source_description="",
                reference_time=ref_time,
                source=EpisodeType.message, # 使用 TEXT 类型
                group_id=group_id, # 传入 group_id
                entity_types={'Person': Person, 'Project': Project, 'Document': Document}, # type: ignore
            )
            
            print("注入完成！")
            print(f"创建了 Episode: {results.episode.uuid}")
            print(f"创建/更新了 {len(results.nodes)} 个实体节点。")
            if results.nodes:
                print("实体节点:")
                for node in results.nodes:
                    print(f"  - {node.name} (类型: {type(node).__name__})")
            
            print(f"创建了 {len(results.edges)} 条实体关系。")
            if results.edges:
                print("实体关系:")
                for edge in results.edges:
                    print(f"  - ({edge.name})")
            print("-" * 20)


if __name__ == "__main__":
    # 运行一次，将数据灌入你的 Neo4j
    # 由于 add_episode 是异步函数，我们需要使用 asyncio.run() 来执行
    asyncio.run(run_ingestion_pipeline())
