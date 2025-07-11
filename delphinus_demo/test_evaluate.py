# evaluate.py
import json
import asyncio
from datetime import datetime
from main import app # 导入你的Graphiti App
from models import Document, ConversationSegment # 显式导入模型以供类型检查
from graphiti_core.nodes import EntityNode, EpisodicNode # 导入 EntityNode 和 EpisodicNode
from graphiti_core.edges import EntityEdge # 导入 EntityEdge

def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def check_entity_matches_expectation(entity, expected_checks: dict) -> bool:
    """
    一个灵活的辅助函数，用于检查单个实体是否满足所有期望的检查项。
    :param entity: 从 graphiti search 结果中提取的节点对象 (e.g., Document, Person)
    :param expected_checks: 一个包含检查规则的字典
    :return: 如果所有检查都通过，则为 True，否则为 False
    """
    for check_key, expected_value in expected_checks.items():
        # 安全地获取实体上的属性值，如果属性不存在，则检查失败
        # 例: "name_contains" -> "name"
        attribute_name = check_key.split('_')[0] 
        check_type = check_key.split('_')[1] 
        actual_value = getattr(entity, attribute_name, None)

        # 如果顶层属性不存在，则尝试从 attributes 字典中获取
        if actual_value is None and hasattr(entity, 'attributes') and isinstance(entity.attributes, dict):
            actual_value = entity.attributes.get(attribute_name)
        
        if actual_value is None:
            print(f"Debug: Attribute '{attribute_name}' not found on entity or in its attributes.") #可选的调试信息
            return False
        
        print(f"Debug: Attribute '{attribute_name}' value is '{actual_value}'. expected value is '{expected_value}'") #可选的调试信息
        # --- 在这里定义你的检查规则 ---
        if check_type == "contains":
            # 检查 actual_value 是否为列表，并且 expected_value 在列表中
            if isinstance(actual_value, list):
                if expected_value not in actual_value:
                    return False
            # 检查 actual_value 是否为字符串，并且 expected_value 在字符串中
            elif isinstance(actual_value, str):
                if expected_value not in actual_value:
                    return False
            # 如果 actual_value 既不是列表也不是字符串，则认为不匹配
            else:
                return False
        elif check_type == "equals":
             if not(isinstance(actual_value, str) and expected_value.lower() == actual_value.lower()):
                return False
        else:
            print(f"警告：未知的检查规则 '{check_key}'，已跳过。")

    return True # 所有检查都通过了

async def run_evaluation():
    """主评估函数"""
    with open('./test_data/mock-ground-truth.json', 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    success_count = 0
    total_count = len(dataset)
    results_log = []

    for i, item in enumerate(dataset):
        question = item["question"]
        expected = item["expected"]
        
        log_entry = { "question": question, "description": item.get("description", ""), "status": "❌ FAILED" }
        print(f"\n--- Running Test Case {i+1}/{total_count}: {item.get('description', '')} ---")
        print(f"question: {question}")
        
        # 核心修正：异步调用 search 并处理 EntityEdge 列表
        try:
            # Graphiti 的 search 是一个 async 函数
            import asyncio
            # `app.search` 的类型提示是错误的，我们使用 `cast` 来告诉类型检查器真实的返回类型
            search_results = await app.search(question)
        except Exception as e:
            print(f"执行搜索时发生错误: {e}")
            search_results = []

        match_found = False
        if search_results:
            # `expected` is now a list of expectation objects.
            # We consider the test case passed if any of the expectations are met.
            for expected_item in expected:
                expected_node_type = expected_item.get("node", "EntityNode")
                
                for result in search_results: # result is of type EntityEdge
                    found_node = None
                    if expected_node_type == "EntityNode":
                        # Check both source and target nodes
                        node_uuids_to_check = [result.source_node_uuid, result.target_node_uuid]
                        for uuid in node_uuids_to_check:
                            try:
                                node = await EntityNode.get_by_uuid(app.driver, uuid)
                                if check_entity_matches_expectation(node, expected_item["checks"]):
                                    found_node = node
                                    break # Found a matching node, break from the inner loop
                            except Exception as e:
                                print(f"Debug: Failed to get EntityNode(uuid={uuid}): {e}")
                                continue
                    
                    elif expected_node_type == "EpisodicNode":
                        if result.episodes:
                            unique_episode_uuids = list(set(result.episodes))
                            try:
                                episodic_nodes = await EpisodicNode.get_by_uuids(app.driver, unique_episode_uuids)
                                for node in episodic_nodes:
                                    if check_entity_matches_expectation(node, expected_item["checks"]):
                                        found_node = node
                                        break # Found a matching node, break from the inner loop
                            except Exception as e:
                                print(f"Debug: Failed to get EpisodicNode: {e}")
                    
                    if found_node:
                        print(f"✅ PASSED - Found matching {expected_node_type}")
                        print(f"node_name:{found_node.name}, node_uuid:{found_node.uuid}")
                        match_found = True
                        log_entry["status"] = "✅ PASSED"
                        log_entry["found_node"] = found_node.model_dump()
                        break # A match is found, break from the search_results loop
                
                if match_found:
                    break # A match is found, break from the expected_item loop
            
        if not match_found:
            print("❌ FAILED - No result matched the expectation.")
            if search_results:
                top_results_info = []
                for res in search_results[:3]:
                    try:
                        source_node = await EntityNode.get_by_uuid(app.driver, res.source_node_uuid)
                        target_node = await EntityNode.get_by_uuid(app.driver, res.target_node_uuid)
                        top_results_info.append({
                            "edge_uuid": res.uuid,
                            "edge_name": res.name,
                            "source_node": source_node.model_dump(),
                            "target_node": target_node.model_dump(),
                        })
                    except Exception:
                        continue
                log_entry["top_results"] = top_results_info
            else:
                log_entry["top_results"] = []
        
        results_log.append(log_entry)
        if match_found:
            success_count += 1
            
    print(f"\n\n--- Evaluation Summary ---")
    print(f"Accuracy: {success_count / total_count * 100:.2f}% ({success_count}/{total_count})")
    
    with open('./test_results/test_evaluation.json', 'w', encoding='utf-8') as f:
        json.dump(results_log, f, indent=2, ensure_ascii=False, default=json_serializer)
    print("详细评估日志已保存到 evaluation_log.json")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
