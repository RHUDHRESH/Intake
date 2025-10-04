"""Central registry mapping agent labels to their implementations."""
from agents.web_crawler.agent import WebCrawlerAgent
from agents.social_agent.agent import SocialAgent
from agents.nlp_agent.agent import NLPAgent
from agents.review_agent.agent import ReviewAgent
from agents.doc_agent.agent import DocAgent
from agents.database_agent.agent import DatabaseAgent
from agents.scheduler_agent.agent import SchedulerAgent
from agents.notification_agent.agent import NotificationAgent
from agents.analytics_agent.agent import AnalyticsAgent
from agents.export_agent.agent import ExportAgent

# Optional agents can be added here when implemented, for example MapAgent.
agent_registry = {
    "web_crawler": WebCrawlerAgent,
    "social_agent": SocialAgent,
    "nlp_agent": NLPAgent,
    "review_agent": ReviewAgent,
    "doc_agent": DocAgent,
    "database_agent": DatabaseAgent,
    "scheduler_agent": SchedulerAgent,
    "notification_agent": NotificationAgent,
    "analytics_agent": AnalyticsAgent,
    "export_agent": ExportAgent,
}
