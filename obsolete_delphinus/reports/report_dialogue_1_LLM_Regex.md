# 测试报告: dialogue_1 (LLM + Regex)

**结果: ❌ 失败**

## 对比详情

### ✅ 正确识别 (11)
- **20231116-盘古项目存储架构专题会会议纪要.pdf** (类型: `Document`)
- **刘洋** (类型: `Person`)
- **夏雨** (类型: `Person`)
- **张伟** (类型: `Person`)
- **李明** (类型: `Person`)
- **王强** (类型: `Person`)
- **盘古项目** (类型: `Project`)
- **盘古项目存储架构专题会** (类型: `Meeting`)
- **盘古项目技术规格书_FINAL_v4.0.docx** (类型: `Document`)
- **盘古项目技术规格书_v3.1.docx** (类型: `Document`)
- **评审会** (类型: `Meeting`)

### ❌ 遗漏的实体 (2)
- **更新我们的项目计划表** (类型: `Task`)
- **资源申请** (类型: `Task`)

### ⚠️ 新增的实体 (4)
- ** 20231116-盘古项目存储架构专题会会议纪要.pdf** (类型: `Document`)
- ** 盘古项目技术规格书_FINAL_v4.0.docx** (类型: `Document`)
- **你上周五发我邮箱的那个 盘古项目技术规格书_v3.1.docx** (类型: `Document`)
- **文件名是 盘古项目技术规格书_FINAL_v4.0.docx** (类型: `Document`)

## 原始差异 (JSON)
```json
{
  "values_changed": {
    "root['entities'][4]": {
      "new_value": {
        "text": "新人刘洋",
        "type": "Person",
        "context": "那次会议的纪要我让新人刘洋整理了",
        "attributes": {
          "normalized_text": "刘洋"
        },
        "entity_id": "dialogue_1_pred_4"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_4",
        "text": "更新我们的项目计划表",
        "type": "Task",
        "context": "我马上去更新我们的项目计划表",
        "attributes": {}
      }
    },
    "root['entities'][5]": {
      "new_value": {
        "text": "@刘洋",
        "type": "Person",
        "context": "@刘洋，麻烦把上周四“盘古项目存储架构专题会”的会议纪要PDF版发到群里",
        "attributes": {
          "normalized_text": "刘洋"
        },
        "entity_id": "dialogue_1_pred_5"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_5",
        "text": "李明",
        "type": "Person",
        "context": "@李明 (项目经理)",
        "attributes": {}
      }
    },
    "root['entities'][7]": {
      "new_value": {
        "text": "架构组的张伟",
        "type": "Person",
        "context": "架构组的张伟过来提了个新的性能风险",
        "attributes": {
          "normalized_text": "张伟"
        },
        "entity_id": "dialogue_1_pred_7"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_7",
        "text": "盘古项目",
        "type": "Project",
        "context": "“盘古项目”进展材料",
        "attributes": {}
      }
    },
    "root['entities'][10]": {
      "new_value": {
        "text": "王强",
        "type": "Person",
        "context": "@王强 (技术负责人)，早上好。",
        "attributes": {
          "normalized_text": "王强"
        },
        "entity_id": "dialogue_1_pred_10"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_10",
        "text": "盘古项目技术规格书_v3.1.docx",
        "type": "Document",
        "context": "盘古项目技术规格书_v3.1.docx 是最终版吗？",
        "attributes": {
          "title": "盘古项目技术规格书",
          "version": "v3.1",
          "format": "docx",
          "project": "盘古项目"
        }
      }
    },
    "root['entities'][1]": {
      "new_value": {
        "text": " 盘古项目技术规格书_FINAL_v4.0.docx",
        "type": "Document",
        "context": "说。  王强 (技术负责人): [文件] 盘古项目技术规格书_FINAL_v4.0.docx  夏雨 (产品经理): 都收到了，太感",
        "attributes": {},
        "entity_id": "dialogue_1_pred_1"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_1",
        "text": "刘洋",
        "type": "Person",
        "context": "新人刘洋",
        "attributes": {}
      }
    },
    "root['entities'][6]": {
      "new_value": {
        "text": "夏雨",
        "type": "Person",
        "context": "夏雨 (产品经理): @李明 (项目经理) @王强 (技术负责人)，早上好。",
        "attributes": {
          "normalized_text": "夏雨"
        },
        "entity_id": "dialogue_1_pred_6"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_6",
        "text": "王强",
        "type": "Person",
        "context": "@王强 (技术负责人)",
        "attributes": {}
      }
    },
    "root['entities'][12]": {
      "new_value": {
        "text": "盘古项目",
        "type": "Project",
        "context": "要提交给CTO办公室的“盘古项目”进展材料",
        "attributes": {},
        "entity_id": "dialogue_1_pred_12"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_12",
        "text": "资源申请",
        "type": "Task",
        "context": "关系到我们下个季度的资源申请",
        "attributes": {}
      }
    },
    "root['entities'][11]": {
      "new_value": {
        "text": "王强哥",
        "type": "Person",
        "context": "好的王强哥，马上。",
        "attributes": {
          "normalized_text": "王强"
        },
        "entity_id": "dialogue_1_pred_11"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_11",
        "text": "评审会",
        "type": "Meeting",
        "context": "上周三开完评审会",
        "attributes": {}
      }
    },
    "root['entities'][0]": {
      "new_value": {
        "text": " 20231116-盘古项目存储架构专题会会议纪要.pdf",
        "type": "Document",
        "context": "，马上。  刘洋 (工程师): [文件] 20231116-盘古项目存储架构专题会会议纪要.pdf 已发送。  李明 (项目经理): 收到",
        "attributes": {},
        "entity_id": "dialogue_1_pred_0"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_0",
        "text": "20231116-盘古项目存储架构专题会会议纪要.pdf",
        "type": "Document",
        "context": "[文件] 20231116-盘古项目存储架构专题会会议纪要.pdf",
        "attributes": {
          "title": "盘古项目存储架构专题会会议纪要",
          "format": "pdf",
          "meeting": "盘古项目存储架构专题会"
        }
      }
    },
    "root['entities'][8]": {
      "new_value": {
        "text": "文件名是 盘古项目技术规格书_FINAL_v4.0.docx",
        "type": "Document",
        "context": "。最新的版本我放到了项目的Git仓库里，文件名是 盘古项目技术规格书_FINAL_v4.0.docx。注意，这次改动很大，特别是第五章和第六",
        "attributes": {},
        "entity_id": "dialogue_1_pred_8"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_8",
        "text": "盘古项目存储架构专题会",
        "type": "Meeting",
        "context": "上周四“盘古项目存储架构专题会”的会议纪要PDF版",
        "attributes": {
          "project": "盘古项目"
        }
      }
    },
    "root['entities'][9]": {
      "new_value": {
        "text": "李明",
        "type": "Person",
        "context": "@李明 (项目经理) @王强 (技术负责人)，早上好。",
        "attributes": {
          "normalized_text": "李明"
        },
        "entity_id": "dialogue_1_pred_9"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_9",
        "text": "盘古项目技术规格书_FINAL_v4.0.docx",
        "type": "Document",
        "context": "文件名是 盘古项目技术规格书_FINAL_v4.0.docx",
        "attributes": {
          "title": "盘古项目技术规格书",
          "version": "FINAL_v4.0",
          "format": "docx",
          "project": "盘古项目"
        }
      }
    },
    "root['entities'][3]": {
      "new_value": {
        "text": "你上周五发我邮箱的那个 盘古项目技术规格书_v3.1.docx",
        "type": "Document",
        "context": "展材料，需要用到最新的技术规格书。李明，你上周五发我邮箱的那个 盘古项目技术规格书_v3.1.docx 是最终版吗？我看到里面关于数据存储的章",
        "attributes": {},
        "entity_id": "dialogue_1_pred_3"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_3",
        "text": "张伟",
        "type": "Person",
        "context": "架构组的张伟",
        "attributes": {}
      }
    },
    "root['entities'][2]": {
      "new_value": {
        "text": "20231116-盘古项目存储架构专题会会议纪要.pdf",
        "type": "Document",
        "context": "[文件] 20231116-盘古项目存储架构专题会会议纪要.pdf 已发送。",
        "attributes": {
          "title": "盘古项目存储架构专题会会议纪要",
          "format": "pdf",
          "project": "盘古项目",
          "meeting": "盘古项目存储架构专题会",
          "audience": "夏雨和李明"
        },
        "entity_id": "dialogue_1_pred_2"
      },
      "old_value": {
        "entity_id": "dialogue_1_gt_2",
        "text": "夏雨",
        "type": "Person",
        "context": "夏雨 (产品经理):",
        "attributes": {}
      }
    }
  },
  "iterable_item_added": {
    "root['entities'][13]": {
      "text": "盘古项目存储架构专题会",
      "type": "Meeting",
      "context": "麻烦把上周四“盘古项目存储架构专题会”的会议纪要PDF版发到群里",
      "attributes": {},
      "entity_id": "dialogue_1_pred_13"
    },
    "root['entities'][14]": {
      "text": "盘古项目技术规格书_FINAL_v4.0.docx",
      "type": "Document",
      "context": "最新的版本我放到了项目的Git仓库里，文件名是 盘古项目技术规格书_FINAL_v4.0.docx。",
      "attributes": {
        "title": "盘古项目技术规格书",
        "version": "FINAL_v4.0",
        "format": "docx",
        "project": "盘古项目"
      },
      "entity_id": "dialogue_1_pred_14"
    },
    "root['entities'][15]": {
      "text": "盘古项目技术规格书_v3.1.docx",
      "type": "Document",
      "context": "你上周五发我邮箱的那个 盘古项目技术规格书_v3.1.docx 是最终版吗？",
      "attributes": {
        "title": "盘古项目技术规格书",
        "version": "v3.1",
        "format": "docx",
        "project": "盘古项目"
      },
      "entity_id": "dialogue_1_pred_15"
    },
    "root['entities'][16]": {
      "text": "评审会",
      "type": "Meeting",
      "context": "王强，咱们上周三开完评审会，技术方案有大的更新吗？",
      "attributes": {},
      "entity_id": "dialogue_1_pred_16"
    }
  }
}
```
