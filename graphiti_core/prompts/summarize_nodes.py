"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
from typing import Any, Protocol, TypedDict

from pydantic import BaseModel, Field

from .models import Message, PromptFunction, PromptVersion


class Summary(BaseModel):
    summary: str = Field(
        ...,
        description='Summary containing the important information about the entity. Under 250 words',
    )


class SummaryDescription(BaseModel):
    description: str = Field(..., description='One sentence description of the provided summary')


class Prompt(Protocol):
    summarize_pair: PromptVersion
    summarize_context: PromptVersion
    summary_description: PromptVersion


class Versions(TypedDict):
    summarize_pair: PromptFunction
    summarize_context: PromptFunction
    summary_description: PromptFunction


def summarize_pair(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a helpful assistant that combines summaries.',
        ),
        Message(
            role='user',
            content=f"""
        将以下两份摘要的信息整合成一份简洁的摘要。

        摘要必须250字以内。

        Summaries:
        {json.dumps(context['node_summaries'], indent=2)}
        """,
        ),
    ]


def summarize_context(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a helpful assistant that extracts entity properties from the provided text.',
        ),
        Message(
            role='user',
            content=f"""
            
        <MESSAGES>
        {json.dumps(context['previous_episodes'], indent=2)}
        {json.dumps(context['episode_content'], indent=2)}
        </MESSAGES>
        
        根据上述MESSAGES和以下ENTITY名称，为ENTITY创建摘要。您的摘要只能使用所提供的MESSAGES中的信息。您的摘要也应只包含与所提供的ENTITY相关的信息。摘要必须在250字以内。

        此外，根据所提供实体属性的描述，提取其任何值。
        如果实体属性的值在当前上下文中找不到，请将属性值设置为Python值None。

        指南：
        1. 如果实体属性值在当前上下文中找不到，请勿虚构。
        2. 仅使用提供的消息、实体和实体上下文来设置属性值。
        
        <ENTITY>
        {context['node_name']}
        </ENTITY>
        
        <ENTITY CONTEXT>
        {context['node_summary']}
        </ENTITY CONTEXT>
        
        <ATTRIBUTES>
        {json.dumps(context['attributes'], indent=2)}
        </ATTRIBUTES>
        """,
        ),
    ]


def summary_description(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are a helpful assistant that describes provided contents in a single sentence.',
        ),
        Message(
            role='user',
            content=f"""
        创建一份对摘要的简短一句话描述，解释所总结信息的类型。
        摘要必须少于250字

        Summary:
        {json.dumps(context['summary'], indent=2)}
        """,
        ),
    ]


versions: Versions = {
    'summarize_pair': summarize_pair,
    'summarize_context': summarize_context,
    'summary_description': summary_description,
}
