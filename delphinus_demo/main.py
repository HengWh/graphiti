import os
from dotenv import dotenv_values
from graphiti_core import Graphiti
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.llm_client.client import LLMConfig
from models import Person, Project, Document, ConversationSegment

config = dotenv_values(".env")
api_key=config.get('GEMINI_API_KEY')
base_url=config.get('GEMINI_BASE_URL')
neo4j_uri = config.get("NEO4J_URI")
neo4j_user = config.get("NEO4J_USER")
neo4j_password = config.get("NEO4J_PASSWORD")

if not base_url or not api_key or not neo4j_uri or not neo4j_user or not neo4j_password:
    raise ValueError(
        "Config must be set in the .env file"
    )


os.environ.setdefault('OPENAI_API_KEY', api_key)
os.environ.setdefault('OPENAI_BASE_URL', base_url)

 # 配置 Gemini embedder
gemini_config = GeminiEmbedderConfig(
    api_key=api_key,  # 从环境变量获取 Gemini API key
    base_url=base_url,  # 从环境变量获取 Gemini base URL
    embedding_model='embedding-001'  # Gemini 的默认 embedding 模型
)
gemini_embedder = GeminiEmbedder(config=gemini_config)


 # 配置 Gemini embedder
gemini_client_config = LLMConfig(
    api_key=config.get('GEMINI_API_KEY'),  # 从环境变量获取 Gemini API key
    base_url=config.get('GEMINI_BASE_URL'),  # 从环境变量获取 Gemini base URL
    model='gemini-2.5-pro'
)
gemini_client = GeminiClient(config=gemini_client_config)



# Initialize Graphiti with Neo4j connection and Gemini embedder
app = Graphiti(neo4j_uri, neo4j_user, neo4j_password, llm_client=gemini_client, embedder=gemini_embedder)

# 此时运行你的应用，Graphiti 会尝试连接 Neo4j 并准备好处理这些模型
