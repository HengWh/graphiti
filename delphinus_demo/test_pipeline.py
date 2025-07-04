# test_pipeline.py
from pipeline import aggregate_simple # 假设你的聚合函数在 pipeline.py

def test_aggregate_simple_basic():
    # 准备测试数据
    mock_messages = [
      { "sender": "李明", "text": "你好", "timestamp": "...", "channel": "私聊-李明" },
      { "sender": "小王", "text": "你好啊", "timestamp": "...", "channel": "私聊-李明" }
    ]
    
    # 调用被测试函数
    result = aggregate_simple(mock_messages)
    
    # 断言结果是否符合预期
    assert "李明" in result["participants"]
    assert "小王" in result["participants"]
    assert len(result["participants"]) == 2
    assert "李明: 你好\n小王: 你好啊" in result["full_text"]

# 你可以添加更多测试用例，比如测试空消息列表、单条消息等边界情况
