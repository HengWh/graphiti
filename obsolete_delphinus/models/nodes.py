from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

# ==============================================================================
#  基础模型 (Base Models)
# ==============================================================================

class GraphNode(BaseModel):
    """所有图节点模型的基类，提供通用字段。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="唯一标识符")
    label: str = Field(..., description="节点的标签或类型")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="最后更新时间")
    source_text: Optional[str] = Field(None, description="从IM对话中提取的原始文本")
    context: Optional[str] = Field(None, description="提取实体时的上下文")

# ==============================================================================
#  核心节点模型 (Core Node Models)
# ==============================================================================

class Person(GraphNode):
    """代表一个员工。"""
    label: str = "Person"
    name: str = Field(..., description="员工的官方/归一化姓名")
    aliases: List[str] = Field(default_factory=list, description="该员工的其他称谓或昵称")
    email: Optional[str] = Field(None, description="员工邮箱")

class Project(GraphNode):
    """代表一个项目或计划。"""
    label: str = "Project"
    name: str = Field(..., description="项目的正式名称")
    description: Optional[str] = Field(None, description="项目的简要描述")

class Document(GraphNode):
    """代表一个文档、文件或报告。"""
    label: str = "Document"
    title: str = Field(..., description="文档的核心标题")
    version: Optional[str] = Field(None, description="版本号")
    format: Optional[str] = Field(None, description="文件格式 (e.g., 'docx', 'pdf')")

class Task(GraphNode):
    """代表一个工作台任务。"""
    label: str = "Task"
    workbench_id: Optional[str] = Field(None, description="工作台中的唯一任务编号")
    title: str = Field(..., description="任务的正式标题")
    description: str = Field(..., description="任务的具体描述")
    is_completed: bool = Field(False, description="任务是否已完成")

class Meeting(GraphNode):
    """代表一次会议。"""
    label: str = "Meeting"
    name: str = Field(..., description="会议的名称或主题")
    scheduled_time: Optional[datetime] = Field(None, description="会议预定时间")

class ConversationSegment(GraphNode):
    """代表一段IM对话片段，是信息的核心载体。"""
    label: str = "ConversationSegment"
    text_content: str = Field(..., description="对话的完整文本内容")
    author: str = Field(..., description="发言人的姓名或ID")
    timestamp: datetime = Field(..., description="发言时间")
