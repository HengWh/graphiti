# models.py
from pydantic import Field, BaseModel, ConfigDict
from typing import List, Dict, Optional

# 为了简化，我们先定义最核心的几个模型
# 注意：所有自定义模型都建议继承自 BaseModel

class Person(BaseModel):
    # Graphiti 会自动使用类名作为 Node 的 Label，即 "Person"
    full_name: str = Field(description="员工姓名")
    role: Optional[str] = Field(description="角色，如'项目经理'", default=None)

class Project(BaseModel):
    full_name: str = Field(description="项目名称")

class Document(BaseModel):
    full_name: str = Field(description="文档名称")
    type: str = Field(description="文档类型，如 'ppt', 'word', 'pdf'")
    path: str = Field(description="文档在坚果云中的路径")

# 这是我们的核心！直接复用你在文档中的设计
class ConversationSegment(BaseModel):
    id: str = Field(description="片段的唯一ID")
    full_text: str = Field(description="聚合后的原始对话全文")
    participants: List[str] = Field(description="参与者姓名列表") # 简化为姓名，而不是ID
    start_time: str
    end_time: str
    source_channel: str 

    # LLM 生成的摘要信息
    title: Optional[str] = Field(description="精炼标题")
    bullet_points: Optional[List[str]] = Field(description="核心要点列表")
    decisions: Optional[List[str]] = Field(description="达成的决策或结论列表")
    action_items: Optional[List[Dict]] = Field(description="待办事项列表")
