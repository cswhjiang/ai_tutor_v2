import os
from pathlib import Path
from conf.system import SYS_CONFIG
from conf.agent import experts_list, expert_name_2_desc
from google.adk.sessions import DatabaseSessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner

# 导入所有专家类
from src.agents.experts import (
    VideoGenerationAgent,
    SearchAgent,
    ReadArtifactAgent,
    ImageUnderstandingAgent,
    ExtractorAgent,
    SearchQueryAgent,
    HTMLGenerationAgent,
    HTMLToImageAgent,
    ScienceAgent,
    ArticleGenerationAgent,
    deep_research_agent,
    article_generation_agent_v2,
    ppt_generation_agent,
    ppt_generation_agent_v2,
    math_video_generation_agent
    # DeepResearchAgent,
)

# 初始化服务
db_path = os.path.join(SYS_CONFIG.session_database_dir, "session_database.db")
db_url = "sqlite+aiosqlite:///{}?timeout=30".format(db_path)    # 设置超时时间为30秒，避免数据库锁定问题
# db_url = "sqlite:///{}?timeout=30".format(db_path)

session_service = DatabaseSessionService(db_url)
artifact_service = InMemoryArtifactService()

# 实例化 Agents
video_generation_agent = VideoGenerationAgent(name='VideoGenerationAgent', description=expert_name_2_desc['VideoGenerationAgent'])
image_understanding_agent = ImageUnderstandingAgent(name='ImageUnderstandingAgent', description=expert_name_2_desc['ImageUnderstandingAgent'])
extractor_agent = ExtractorAgent(name="ExtractorAgent", description=expert_name_2_desc['ExtractorAgent'], llm_model = SYS_CONFIG.llm_model)
read_artifact_agent = ReadArtifactAgent(name="ReadArtifactAgent", description=expert_name_2_desc['ReadArtifactAgent'], llm_model = SYS_CONFIG.llm_model)
search_query_agent = SearchQueryAgent(name="SearchQueryAgent", description=expert_name_2_desc['SearchQueryAgent'], llm_model=SYS_CONFIG.llm_model)
search_agent = SearchAgent(name='SearchAgent', max_search_count=SYS_CONFIG.max_search_count, description=expert_name_2_desc['SearchAgent'])
html_generation_agent = HTMLGenerationAgent(name='HTMLGenerationAgent', description=expert_name_2_desc['HTMLGenerationAgent'], llm_model=SYS_CONFIG.html_gen_llm_model) # name 需要和 agent.json中的一致
html_to_image = HTMLToImageAgent(name='HTMLToImageAgent', description=expert_name_2_desc['HTMLToImageAgent'])
science_agent = ScienceAgent(name='ScienceAgent', description=expert_name_2_desc['ScienceAgent'], llm_model=SYS_CONFIG.science_llm_model)
article_generation_agent = ArticleGenerationAgent(name='ArticleGenerationAgent', description=expert_name_2_desc['ArticleGenerationAgent'],llm_model = SYS_CONFIG.article_llm_model)



# name 需要与 conf/jsons/agent.json 中的一致
expert_agents = {
    "VideoGenerationAgent": video_generation_agent,
    "ImageUnderstandingAgent": image_understanding_agent,
    "ExtractorAgent": extractor_agent,
    "ReadArtifactAgent": read_artifact_agent,
    "SearchQueryAgent": search_query_agent,
    "HTMLGenerationAgent": html_generation_agent,
    "HTMLToImageAgent": html_to_image,
    "ScienceAgent": science_agent,
    "ArticleGenerationAgent": article_generation_agent,
    "ArticleGenerationAgentv2": article_generation_agent_v2,
    "PPTGenerationAgent": ppt_generation_agent,
    "PPTGenerationAgentv2": ppt_generation_agent_v2,
    "DeepResearchAgent": deep_research_agent,
    "SearchAgent": search_agent,
    "MathVideoGenerationAgent": math_video_generation_agent
}


expert_runners = {
    name: Runner(
        agent=agent, app_name=SYS_CONFIG.app_name, session_service=session_service,
        artifact_service=artifact_service
    )
    for name, agent in expert_agents.items()
}