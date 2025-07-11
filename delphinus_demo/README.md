### 个人记忆与智能工作系统

## 本项目一期（MVP）目标用户为坚果云公司内部全体员工。特别是知识工作者，如：

项目经理： 需要频繁在不同项目、文档、沟通记录之间切换，回忆决策过程。
产品与研发人员： 需要追溯需求来源、技术方案的讨论历史、查阅相关文档。
市场与销售人员： 需要快速找到与客户相关的沟通记录、合同版本和项目进展。

## 使用场景一：精准回忆文件
用户请求： “小王，帮我找下上周李明发我的那份关于‘盘古项目’的PPT。”
“妙豚豚”工作流：
情景大脑 (CG) 启动： 在“坚果云IM”中，筛选出时间范围=“上周”，参与人=“小王”和“李明”的所有ConversationSegment（对话片段）。
语义大脑 (KG) 介入： 解析查询中的实体“盘古项目”和“PPT”。它知道“盘古项目”是一个Project实体，PPT是一种Document类型。
双脑融合： 系统寻找既满足情景大脑筛选条件，又在内容上（或通过显式MENTIONS关系）与Project:盘古项目和Document.type:PPT这两个语义实体强相关的ConversationSegment。
呈现结果： “找到了。这是李明在上周四下午发给您的盘古项目周报.pptx，这是当时的聊天记录摘要：[...]”

## 使用场景二：追溯决策过程
用户请求： “我们上次关于‘移动端UI改版’的结论是什么？”
“妙豚豚”工作流：
语义大脑 (KG) 启动： 解析核心主题“移动端UI改版”，这可能是一个Project或一个Task。
情景大脑 (CG) 介入： 查找所有与该Project/Task节点有DISCUSSES或MENTIONS关系的ConversationSegment。
双脑融合与深度检索： 系统不只是全文搜索，而是优先检索这些ConversationSegment的结构化摘要字段——decisions。
呈现结果： “关于‘移动端UI改版’，共找到3次关键讨论。最近一次是在上周五，结论是：采纳方案B，由设计部出具高保真原型。 这是当时的讨论总结：[...]”
通过将对话内容导入graphiti数据库实现。 我已经跑通了一个最简的”回忆文件“的场景。 main.py是初始化graphiti数据库，pipeline.py是导入对话数据。 query_test.py是测试查询。 evalute.py是验证查询结果。 app_ui.py是一个简单的UI界面。

## 核心技术方案与数据建模 (基于Graphiti)

3.1. 技术栈
数据源: 坚果云工作台 (IM, 文档, 项目等)
核心引擎: Graphiti (项目地址: https://github.com/getzep/graphiti)
图数据库: Neo4j 5.x
LLM服务: OpenAI / Gemini / 或其他兼容服务

3.2. 本体（Ontology）与关系建模
我们将使用的自定义实体能力，定义以下核心节点和关系：
核心节点 (Nodes):
Person: 员工
Project: 项目
Document: 文档
Task: 任务
Meeting: 会议
ConversationSegment: 对话片段（IM内容的核心载体）

核心关系 (Edges):
WORKS_ON: (Person, Project)
MANAGES: (Person, Project)
ATTENDS: (Person, Meeting)
ASSIGNED_TO: (Person, Task)
CONTAINS: (Project, Document/Task)
DISCUSSES: (ConversationSegment, Project/Document/Task)
MENTIONS: (ConversationSegment, Person/Project/Document)
RESULTED_IN: (ConversationSegment, Task/Decision)
REPLIES_TO: (ConversationSegment, ConversationSegment)

3.3. IM内容的关键数据建模
这是本项目的核心与难点。我们将IM消息通过“聚合”与“摘要”两个步骤，建模为结构化的ConversationSegment节点。
数据流:
原始IM消息 -> [聚合模块] -> 结构化的ConversationSegment对象 -> [摘要模块] -> 存入Graphiti

Step A: 聚合 (Aggregation)
聚合模块遵循一个多层级、高优先级的决策模型，将原始消息流组合成ConversationSegment。

第一层（确定性规则）：
按线程/回复聚合： 拥有相同thread_id的消息，强制聚合成一个Segment。
按动作回溯聚合： 当“创建任务”等动作发生时，回溯之前的相关讨论，聚合成一个Segment。

第二层（启发式规则）：
在没有明确线程的对话中，综合使用时间窗口、发送者连续性、语义连贯性来判断对话边界。

Step B: 摘要与结构化 (Summarization & Structuring)
聚合后的ConversationSegment对象，在存入Graphiti前，会由一个“摘要模块”调用LLM进行处理，填充以下关键属性。这构成了ConversationSegment节点的完整模型： models.py