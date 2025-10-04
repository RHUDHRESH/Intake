"""
Analytics helpers for BigQuery, summaries, and charting.
"""
import asyncio
import os
from functools import lru_cache
from typing import Any, Dict

import matplotlib.pyplot as plt
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
DEFAULT_CHART_PATH = "chart.png"


@lru_cache(maxsize=1)
def _get_bq_client() -> bigquery.Client:
    if not GOOGLE_CLOUD_PROJECT:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT environment variable is not set")
    return bigquery.Client(project=GOOGLE_CLOUD_PROJECT)


def _run_bq_query_sync(query: str) -> Dict[str, Any]:
    client = _get_bq_client()
    job = client.query(query)
    rows = job.result()
    df = rows.to_dataframe()
    return {"records": df.to_dict(orient="records"), "row_count": len(df)}


def _summarize_data_sync(df: Any) -> Dict[str, Any]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas.DataFrame for summarization")
    summary = df.describe(include="all").fillna(0)
    return summary.to_dict()


def _generate_chart_sync(config: Dict[str, Any]) -> Dict[str, Any]:
    chart_type = config.get("type", "bar")
    x_vals = config.get("x")
    y_vals = config.get("y")
    title = config.get("title", "Chart")
    output_path = config.get("output_path", DEFAULT_CHART_PATH)

    if x_vals is None or y_vals is None:
        raise ValueError("Chart configuration requires 'x' and 'y' values")

    plt.figure(figsize=config.get("figsize", (8, 4)))
    if chart_type == "bar":
        plt.bar(x_vals, y_vals)
    elif chart_type == "line":
        plt.plot(x_vals, y_vals)
    elif chart_type == "scatter":
        plt.scatter(x_vals, y_vals)
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    plt.title(title)
    plt.xlabel(config.get("xlabel", ""))
    plt.ylabel(config.get("ylabel", ""))
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    return {"file": output_path, "type": chart_type}


async def run_bq_query(query: str) -> Dict[str, Any]:
    if not query:
        return {"error": "Query string is required"}
    try:
        return await asyncio.to_thread(_run_bq_query_sync, query)
    except (RuntimeError, GoogleCloudError) as exc:
        return {"error": str(exc)}


async def summarize_data(df: Any) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_summarize_data_sync, df)
    except (TypeError, ValueError) as exc:
        return {"error": str(exc)}


async def generate_chart(config: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_generate_chart_sync, config)
    except (ValueError, RuntimeError) as exc:
        return {"error": str(exc)}
