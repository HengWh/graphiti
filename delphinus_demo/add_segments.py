# add_segments.py
import json
import asyncio
import os
import glob
import time
import argparse
from datetime import datetime, timezone
from models import Person, Project, Document, ConversationSegment # 导入实体模型
from main import app # 导入我们配置好的 app 实例
from typing import List, Dict
from graphiti_core.nodes import CommunityNode, EntityNode, EpisodeType, EpisodicNode

async def process_segment_file(filepath: str):
    """
    处理单个 segment.json 文件，将其中的数据注入图谱。
    """
    print(f"\n=================================================")
    print(f"正在处理文件: {filepath}")
    print(f"=================================================")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            segments = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"错误: 无法读取或解析文件 {filepath}。错误信息: {e}")
        return

    for segment_data in segments:
        if not segment_data.get("id") or not segment_data.get("summary"):
            print(f"--- 跳过 Segment: 缺少 'id' 或 'summary' ---")
            continue

        print(f"--- 正在处理 Segment: {segment_data.get('id', 'N/A')} ---")
        
        try:
            # 时间戳是毫秒级的，需要转换为秒
            start_time_seconds = segment_data["timeRange"]["start_time"] / 1000
            ref_time = datetime.fromtimestamp(start_time_seconds, tz=timezone.utc)
        except (ValueError, KeyError, TypeError):
            print("警告: 无法解析时间戳，将使用当前时间。")
            ref_time = datetime.now(timezone.utc)

        # 为整个 segment 定义一个 group_id
        group_id = segment_data['task_id'] + segment_data['id']
        group_name = segment_data['task_name'] + segment_data['id']
        
        # 检查 'messages' 字段是否存在且是一个列表
        if not isinstance(segment_data.get("messages"), list):
            print(f"--- 跳过 Segment {group_id}: 'messages' 字段不存在或格式不正确 ---")
            continue

        # 遍历每条消息并单独注入
        for i, message_body in enumerate(segment_data["messages"]):
            print(f"--- 正在导入 Message {i+1}/{len(segment_data['messages'])} from Segment: {group_id} ---")
            print(f"Message Body: {message_body}")
            
            try:
                results = await app.add_episode(
                    name=f"{group_name}-{i}", # 为每条消息创建唯一的 name
                    episode_body=message_body,
                    source_description=segment_data['task_name'],
                    reference_time=ref_time,
                    source=EpisodeType.message, # 使用 TEXT 类型
                    group_id=group_id, # 传入 group_id
                    entity_types={'Person': Person, 'Project': Project, 'Document': Document}, # type: ignore
                )
                
                print("注入完成！")
                if results and results.episode:
                    print(f"创建了 Episode: {results.episode.uuid}")
                    print(f"创建/更新了 {len(results.nodes)} 个实体节点。")
                    print(f"创建了 {len(results.edges)} 条实体关系。")
                else:
                    print("警告: add_episode 未返回有效结果。")
                print("-" * 20)

            except Exception as e:
                print(f"错误: 在调用 add_episode 时发生异常: {e}")


async def run_ingestion_pipeline(filepath: str):
    """
    处理单个 segment.json 文件。
    """
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在 {filepath}")
        return

    print(f"准备开始导入文件: {filepath}...")
    total_start_time = time.time()
    
    await process_segment_file(filepath)

    total_end_time = time.time()
    print(f"\n文件处理完毕！总耗时: {total_end_time - total_start_time:.2f} 秒。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从指定的 segment.json 文件导入数据到 Graphiti。")
    parser.add_argument("filepath", type=str, help="要处理的 segment.json 文件的路径。")
    args = parser.parse_args()

    asyncio.run(run_ingestion_pipeline(args.filepath))
