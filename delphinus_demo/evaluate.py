# evaluate.py
import json
from main import app # 导入你的Graphiti App
from models import Document, ConversationSegment # 显式导入模型以供类型检查

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
        actual_value = getattr(entity, attribute_name, None)
        if actual_value is None:
            # print(f"Debug: Attribute '{attribute_name}' not found on entity.") #可选的调试信息
            return False

        # --- 在这里定义你的检查规则 ---
        if check_key == "name_contains":
            if not (isinstance(actual_value, str) and expected_value.lower() in actual_value.lower()):
                return False
        elif check_key == "type_equals":
             if not(isinstance(actual_value, str) and expected_value.lower() == actual_value.lower()):
                return False
        elif check_key == "participants_contain_all":
            if not (isinstance(actual_value, list) and set(expected_value).issubset(set(actual_value))):
                return False
        elif check_key == "decisions_contain":
            if not (isinstance(actual_value, list) and any(expected_value.lower() in str(decision).lower() for decision in actual_value)):
                 return False
        else:
            print(f"警告：未知的检查规则 '{check_key}'，已跳过。")

    return True # 所有检查都通过了

def run_evaluation():
    """主评估函数"""
    with open('golden_dataset.json', 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    success_count = 0
    total_count = len(dataset)
    results_log = []

    for i, item in enumerate(dataset):
        query = item["query"]
        expected = item["expected"]
        
        log_entry = { "query": query, "description": item.get("description", ""), "status": "❌ FAILED" }
        print(f"\n--- Running Test Case {i+1}/{total_count}: {item.get('description', '')} ---")
        print(f"Query: {query}")
        
        # 核心修正：异步调用 search 并处理 EntityEdge 列表
        try:
            # Graphiti 的 search 是一个 async 函数
            import asyncio
            search_results = asyncio.run(app.search(query))
        except Exception as e:
            print(f"执行搜索时发生错误: {e}")
            search_results = []

        match_found = False
        if search_results:
            for edge in search_results:
                # ----------------- 核心修正点在这里 -----------------
                # 使用 edge.destination 来访问实体对象
                found_entity = edge.destination 
                # ----------------------------------------------------
                
                if found_entity and found_entity.__class__.__name__ == expected["type"]:
                    if check_entity_matches_expectation(found_entity, expected["checks"]):
                        print(f"✅ PASSED - Found matching {expected['type']} with score {edge.weight:.4f}")
                        match_found = True
                        log_entry["status"] = "✅ PASSED"
                        log_entry["found_entity"] = found_entity.model_dump()
                        break 
            
        if not match_found:
            print("❌ FAILED - No result matched the expectation.")
            if search_results:
                # 使用 .destination 修正日志记录
                log_entry["top_results"] = [res.destination.model_dump() for res in search_results[:3] if res.destination] 
            else:
                log_entry["top_results"] = []
        
        results_log.append(log_entry)
        if match_found:
            success_count += 1
            
    print(f"\n\n--- Evaluation Summary ---")
    print(f"Accuracy: {success_count / total_count * 100:.2f}% ({success_count}/{total_count})")
    
    with open('evaluation_log.json', 'w', encoding='utf-8') as f:
        json.dump(results_log, f, indent=2, ensure_ascii=False)
    print("详细评估日志已保存到 evaluation_log.json")

if __name__ == "__main__":
    run_evaluation()
