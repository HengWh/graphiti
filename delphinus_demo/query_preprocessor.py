# query_preprocessor.py
import asyncio
import json
import logging
from typing import List

from pydantic import BaseModel, Field
from llm_helpers import generate_json_from_llm

# 配置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


class QueryAnalysisResult(BaseModel):
    """定义查询分析结果的 Pydantic 模型"""
    nodes: List[str] = Field(..., description="查询中提到的核心实体列表。")
    edges: List[str] = Field(..., description="查询中暗示的寻求的关系类型。")
    rewritten_query: str = Field(..., description="一个为向量搜索优化的查询描述。")

async def preprocess_query_http(query: str) -> dict:
    """
    使用 httpx 直接调用 Gemini API 进行查询预处理。
    函数内部会自动从 .env 文件加载配置。

    Args:
        query (str): 用户原始查询。

    Returns:
        dict: 包含分析结果的字典。
    """
    prompt = f"""
你是一个graphiti知识图谱查询分析助手。请分析以下用户查询，并以JSON格式返回：
1. "nodes": 查询中提到的核心实体列表。
2. "edges": 查询中暗示的寻求的关系类型（例如：'HAS_MEMBER', 'MENTIONS', 'RELATES_TO'）。
3. "rewritten_query": 一个为向量搜索优化的查询描述。

用户查询: "{query}"
预期输出 (Example):
<JSON>
{{
  "nodes": ["李明", "小王","盘古项目"],
  "edges": ["SENDS_FILE", "IS_FOR_PROJECT"],
  "rewritten_query": "寻找由李明发送给小王，且内容关于盘古项目的文件。"
}}
"""
    try:
        analysis = await generate_json_from_llm(
            prompt=prompt,
            model="gpt-4.1-mini", # 这里硬编码了模型，也可以作为参数传入
            provider="openai"
        )
        validated_analysis = QueryAnalysisResult.model_validate(analysis)
        return validated_analysis.model_dump()
    except Exception as e:
        logging.error(f"查询预处理失败: {e}")
        return {
            "nodes": [],
            "edges": [],
            "rewritten_query": query,
            "error": str(e)
        }

async def main():
    """用于独立测试此模块的主函数"""
    test_query = "李明发给小王的那份关于盘古项目的文件是什么？"
    logging.info(f"正在测试查询: '{test_query}'")
    
    result = await preprocess_query_http(test_query)
    
    logging.info("查询分析结果:")
    logging.info(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
