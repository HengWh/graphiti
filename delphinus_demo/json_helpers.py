#json_helpers.py
import json
from pydantic import BaseModel

def dump_and_clean_for_log(model_object: BaseModel) -> dict:
    """
    将 Pydantic 模型转储为字典，并移除 embedding 字段。
    返回清理后的字典。
    """
    if not model_object:
        return {}
        
    content_dict = model_object.model_dump()
    
    # 移除顶层的 embedding 字段
    content_dict.pop('fact_embedding', None)
    content_dict.pop('name_embedding', None)

    # 如果存在 'attributes' 键，就从中删除不想要的 embedding
    if 'attributes' in content_dict and isinstance(content_dict['attributes'], dict):
        content_dict['attributes'].pop('fact_embedding', None)
        content_dict['attributes'].pop('name_embedding', None)
        
    return content_dict
