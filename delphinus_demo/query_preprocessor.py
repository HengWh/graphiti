# query_preprocessor.py
import asyncio
import json
import logging
import os
from typing import List

import httpx
from dotenv import load_dotenv, dotenv_values
from pydantic import BaseModel, Field

# 配置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# 在模块加载时读取配置
config = dotenv_values(".env")
API_KEY = config.get('GEMINI_API_KEY')
BASE_URL = config.get('GEMINI_BASE_URL')


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
    if not API_KEY or not BASE_URL:
        logging.error("GEMINI_API_KEY 或 GEMINI_BASE_URL 未配置。")
        return {
            "nodes": [],
            "edges": [],
            "rewritten_query": query,
            "error": "API key or base URL not configured."
        }

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
    
    request_url = f"{BASE_URL}/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(request_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            response_json = response.json()
            content_text = response_json['candidates'][0]['content']['parts'][0]['text']
            
            if content_text.strip().startswith("```json"):
                content_text = content_text.strip()[7:-3].strip()
            
            analysis = json.loads(content_text)
            
            validated_analysis = QueryAnalysisResult.model_validate(analysis)
            return validated_analysis.model_dump()

    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError, IndexError) as e:
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
