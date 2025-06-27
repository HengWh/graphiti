def create_extraction_prompt(im_conversation_text: str) -> str:
    """
    生成一个精心设计的Prompt，用于从IM对话中提取实体。

    这个Prompt的设计目标是：
    1.  让LLM输出的JSON结构与我们的Ground Truth格式保持一致（除了id字段）。
    2.  通过详细的定义和示例，提高提取的准确率和召回率。
    """
    # Using a separate template string and .format() is safer and more readable
    # than escaping many curly braces in a large f-string.
    prompt_template = """### 指令 ###
你是一个顶级的实体提取AI，专门负责从公司内部IM（即时通讯）对话中，精准地抽取出预定义的实体。
你的任务是：仔细阅读“待处理的对话记录”，并严格按照“JSON输出格式要求”返回一个JSON对象。
除了JSON对象，不要输出任何额外的解释、开场白或结束语。

### 实体定义与属性 ###
你必须从以下类型中提取实体：
1.  **Person**: 员工姓名、昵称或代称。例如: "夏雨", "李明", "黄总", "架构组的张伟", "新人刘洋"。
2.  **Project**: 项目、计划或行动的正式名称。例如: "盘古项目", "灯塔计划", "鲲鹏计划"。
3.  **Document**: 特定的文档、文件、报告、纪要、表格、PPT等。
    - **attributes**:
        - `title`: 文档的核心标题 (从文件名中去除版本和格式)。
        - `version`: 版本号。例如: "v3.1", "FINAL_v4.0", "W46"。
        - `format`: 文件格式。例如: "docx", "pdf", "xlsx", "pptx", "png", "md"。
        - `project`: 如果文档明确关联某个项目。
        - `meeting`: 如果文档是某个会议的产物 (如会议纪要)。
        - `audience`: 如果文档有明确的接收人。
4.  **Task**: 一个需要被执行或正在讨论的具体工作/行动。例如: "资源申请", "更新我们的项目计划表", "支付网关的联调", "整理出一条完整的证据链"。
5.  **Meeting**: 一次会议的名称或代称。例如: "评审会", "存储架构专题会", "集团的经管会", "紧急会议"。
6.  **Organization**: 公司、部门或外部机构的名称。例如: "蓝海资本", "星尘科技"。
7.  **Code**: 代码相关的实体，如仓库名或分支名。
    - **attributes**:
        - `type`: 代码实体的类型，如 "repository" 或 "branch"。

### JSON输出格式要求 ###
你必须输出一个JSON对象，该对象只包含一个名为 "entities" 的键，其值为一个列表。
列表中的每个元素都是一个实体对象，该对象必须包含以下键：
- **`text`**: 从原文中一字不差地抽取的实体文本。
- **`type`**: 上述定义的实体类型之一。
- **`context`**: 原文中能证明该实体身份的最直接的上下文短语。这对于理解提取原因至关重要。
- **`attributes`**: 一个包含实体属性的JSON对象。如果实体没有任何可提取的属性，请提供一个空对象 `{{}}`。

### 示例 ###
**输入:**
"李娜，麻烦把“天眼系统”的风险评估报告v2最终版发我，我明天经管会要用。"

**输出:**
```json
{{
  "entities": [
    {{
      "text": "李娜",
      "type": "Person",
      "context": "李娜，麻烦把...",
      "attributes": {{}}
    }},
    {{
      "text": "天眼系统",
      "type": "Project",
      "context": "“天眼系统”的风险评估报告",
      "attributes": {{}}
    }},
    {{
      "text": "风险评估报告v2最终版",
      "type": "Document",
      "context": "“天眼系统”的风险评估报告v2最终版",
      "attributes": {{
        "title": "风险评估报告",
        "version": "v2最终版",
        "project": "天眼系统"
      }}
    }},
    {{
      "text": "经管会",
      "type": "Meeting",
      "context": "我明天经管会要用",
      "attributes": {{}}
    }}
  ]
}}
```

### 待处理的对话记录 ###
{conversation}

### 你的输出 ###
"""
    return prompt_template.format(conversation=im_conversation_text)
