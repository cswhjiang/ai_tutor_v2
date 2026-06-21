from google.adk.agents import SequentialAgent

from src.agents.experts.deep_research.query_agent import DRQueryAgent
from src.agents.experts.deep_research.report_agent import DRReportAgent
from src.agents.experts.deep_research.search_agent import DRSearchAgent


deep_research_agent = SequentialAgent(
    name="DeepResearchAgent",
    sub_agents=[
        DRQueryAgent(name="DRQueryAgent"),
        DRSearchAgent(name="DRSearchAgent"),
        DRReportAgent(name="DRReportAgent"),
    ],
)
