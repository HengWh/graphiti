# delphinus_demo/relevance_scorer.py
import json
import logging
import os
from typing import List, Dict, Any

import httpx
from dotenv import dotenv_values

# 加载 .env 文件中的配置
config = dotenv_values(".env")
API_KEY = config.get('GEMINI_API_KEY')
BASE_URL = config.get('GEMINI_BASE_URL')

# 配置日志记录器
log_formatter = logging.Formatter('%(asctime)s - %(message)s')
log_handler = logging.FileHandler('./test_results/relevance_scorer.log', encoding='utf-8')
log_handler.setFormatter(log_formatter)
scorer_logger = logging.getLogger(__name__)
scorer_logger.addHandler(log_handler)
scorer_logger.setLevel(logging.INFO)

PROMPT_TEMPLATE = """
你是一个图谱节点相关性评估器。根据以下原始查询，为每个候选节点的相关性打分（1-10分，10分最相关），并简要说明理由。请以JSON列表格式返回。
原始查询: "{query}"
候选节点列表:
{nodes_json}
预期输出 (Example):
<JSON>
[
  {{"uuid": "node1", "score": 9, "reason": "直接关联到'盘古项目'，可能李明发给小王的文件信息。"}},
  {{"uuid": "node2", "score": 2, "reason": "..."}},
  {{"uuid": "node3", "score": 3, "reason": "..."}}
]
"""

def prepare_nodes_for_scoring(nodes: List[Any]) -> List[Dict[str, Any]]:
    """
    从节点对象列表中提取用于打分所需的信息。
    """
    candidate_nodes = []
    for node in nodes:
        # 假设每个node对象都有uuid, name, 和 summary属性
        node_dict = node.model_dump()
        candidate_nodes.append({
            "uuid": str(node_dict.get("uuid")),
            "name": node_dict.get("name"),
            "summary": node_dict.get("summary", '')
        })
    return candidate_nodes

async def score_nodes_relevance(
    query: str,
    nodes: List[Any]
) -> List[Any]:
    """
    使用LLM对节点列表与给定查询的相关性进行批量打分，并返回一个包含评分信息的列表。

    :param query: 用户的原始查询字符串。
    :param nodes: 从搜索结果中获取的节点对象列表。
    :return: 一个包含节点uuid、相关性分数和原因的字典列表。
    """
    if not nodes:
        scorer_logger.info("节点列表为空，无需打分。")
        return []

    if not API_KEY or not BASE_URL:
        scorer_logger.error("GEMINI_API_KEY 或 GEMINI_BASE_URL 未在 .env 文件中配置。")
        return []

    candidate_nodes = prepare_nodes_for_scoring(nodes)
    nodes_json_str = json.dumps(candidate_nodes, indent=2, ensure_ascii=False)

    prompt = PROMPT_TEMPLATE.format(query=query, nodes_json=nodes_json_str)
    
    scorer_logger.info(f"正在为查询 '{query}' 的结果进行相关性打分...")
    
    request_url = f"{BASE_URL}/v1beta/models/gemini-2.5-pro:generateContent"
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
            
            # 提取JSON内容
            if '<JSON>' in content_text and '</JSON>' in content_text:
                 json_part = content_text.split('<JSON>')[1].split('</JSON>')[0].strip()
            else:
                 json_part = content_text.strip().replace("```json", "").replace("```", "").strip()

            raw_scores_list = json.loads(json_part)
            
            # 对LLM返回的结果进行格式校验
            validated_scores = []
            if isinstance(raw_scores_list, list):
                for item in raw_scores_list:
                    if isinstance(item, dict) and 'uuid' in item and 'score' in item:
                        validated_scores.append({
                            'uuid': str(item['uuid']),
                            'score': int(item['score']),
                            'reason': item.get('reason', '')
                        })
                    else:
                        scorer_logger.warning(f"跳过格式不正确的评分项: {item}")
            else:
                scorer_logger.error(f"LLM返回的不是一个列表: {raw_scores_list}")
                # 可以选择返回空列表或抛出异常
                return []

            scorer_logger.info(f"经过校验和处理后的打分结果: \n{json.dumps(validated_scores, indent=2, ensure_ascii=False)}")
            
            return validated_scores
            
    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError, IndexError) as e:
        scorer_logger.error(f"调用LLM或解析其响应时出错: {e}")
        # 出错时返回原始节点列表
        return nodes
