# delphinus_demo/llm_helpers.py
import asyncio
import json
import logging
from typing import Dict, Any, Literal

import httpx
from dotenv import dotenv_values

# 配置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 在模块加载时读取配置
config = dotenv_values(".env")
GEMINI_API_KEY = config.get('GEMINI_API_KEY')
GEMINI_BASE_URL = config.get('GEMINI_BASE_URL')
OPENAI_API_KEY = config.get('OPENAI_API_KEY')
OPENAI_BASE_URL = config.get('OPENAI_BASE_URL')

async def _call_gemini_api(prompt: str, model: str, timeout: int) -> Dict[str, Any]:
    """私有函数，用于调用 Gemini API。"""
    if not GEMINI_API_KEY or not GEMINI_BASE_URL:
        raise ValueError("GEMINI_API_KEY 或 GEMINI_BASE_URL 未在 .env 文件中配置。")
    
    request_url = f"{GEMINI_BASE_URL}/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    async with httpx.AsyncClient() as client:
        response = await client.post(request_url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        response_json = response.json()
        content_text = response_json['candidates'][0]['content']['parts'][0]['text']
        
        # JSON 清理逻辑
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif '<JSON>' in content_text and '</JSON>' in content_text:
            content_text = content_text.split('<JSON>')[1].split('</JSON>')[0].strip()

        return json.loads(content_text)

async def _call_openai_api(prompt: str, model: str, timeout: int) -> Dict[str, Any]:
    """私有函数，用于调用 OpenAI API。"""
    if not OPENAI_API_KEY or not OPENAI_BASE_URL:
        raise ValueError("OPENAI_API_KEY 或 OPENAI_BASE_URL 未在 .env 文件中配置。")

    request_url = f"{OPENAI_BASE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(request_url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        response_json = response.json()
        content_text = response_json['choices'][0]['message']['content']
        
        return json.loads(content_text)

async def generate_json_from_llm(
    prompt: str,
    model: str,
    provider: Literal['gemini', 'openai'] = 'gemini',
    timeout: int = 300
) -> Dict[str, Any]:
    """
    根据指定的提供商，向 LLM 发送请求并期望返回一个 JSON 对象。
    函数会自动从 .env 文件加载和使用相应的配置。

    Args:
        prompt (str): 发送给 LLM 的完整提示。
        model (str): 要使用的具体模型名称。
        provider (Literal['gemini', 'openai']): LLM 提供商。
        timeout (int): 请求超时时间（秒）。

    Returns:
        Dict[str, Any]: 从 LLM 返回并解析后的 JSON 字典。
    
    Raises:
        ValueError: 如果提供商不受支持或相关配置缺失。
        httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError, IndexError:
            在请求或解析过程中发生错误时抛出。
    """
    try:
        if provider == 'gemini':
            return await _call_gemini_api(prompt, model, timeout)
        elif provider == 'openai':
            return await _call_openai_api(prompt, model, timeout)
        else:
            raise ValueError("不支持的 LLM 提供商。请选择 'gemini' 或 'openai'。")
    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
        logger.error(f"调用 LLM ({provider}) 时出错: {e}")
        # 重新抛出异常，让调用方处理
        raise

async def main():
    """用于独立测试此模块的主函数"""
    # 测试 Gemini
    try:
        logger.info("--- 测试 Gemini API ---")
        gemini_prompt = '以 JSON 格式返回一个简单的问候语，包含 "greeting" 和 "language" 两个键。'
        gemini_result = await generate_json_from_llm(gemini_prompt, model='gemini-1.5-flash', provider='gemini')
        logger.info(f"Gemini 返回结果: {json.dumps(gemini_result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"Gemini 测试失败: {e}")

    # 测试 OpenAI (如果配置了)
    if OPENAI_API_KEY and OPENAI_BASE_URL:
        try:
            logger.info("\n--- 测试 OpenAI API ---")
            openai_prompt = '以 JSON 格式返回一个简单的告别语，包含 "farewell" 和 "language" 两个键。'
            openai_result = await generate_json_from_llm(openai_prompt, model='gpt-4', provider='openai')
            logger.info(f"OpenAI 返回结果: {json.dumps(openai_result, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"OpenAI 测试失败: {e}")
    else:
        logger.warning("\nOpenAI API 未配置，跳过测试。")


if __name__ == "__main__":
    asyncio.run(main())
