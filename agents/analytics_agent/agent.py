"""Analytics Agent for data insights."""
from typing import Any, Dict, Tuple

from utils.base_agent import AgentInput, BaseAgent
from .tools import generate_chart, run_bq_query, summarize_data


class AnalyticsAgent(BaseAgent):
    """Runs analytical workloads such as BigQuery, summaries, and charting."""

    async def run(self, agent_input: AgentInput) -> Dict[str, Any]:
        input_data = agent_input.input_data
        results: Dict[str, Any] = {}

        bq_query = input_data.get("bq_query")
        dataframe = input_data.get("df")
        chart_config = input_data.get("chart")

        if bq_query:
            results["bq"] = await run_bq_query(bq_query)

        if dataframe is not None:
            results["summary"] = await summarize_data(dataframe)

        if chart_config:
            results["chart"] = await generate_chart(chart_config)

        return results

    def get_dependencies(self) -> Tuple[str, ...]:
        return tuple()
