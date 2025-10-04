"""Transformation utilities for mapping, filtering, aggregating, and converting data."""
import asyncio
import csv
import json
from collections import defaultdict
from io import StringIO
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from xml.etree.ElementTree import Element, SubElement, tostring

try:
    import pandas as pd
except ImportError:  # pragma: no cover - optional dependency
    pd = None

Transformer = Callable[[Dict[str, Any]], Dict[str, Any]]
FilterCallable = Callable[[Dict[str, Any]], bool]
AggregatorCallable = Callable[[Iterable[Any]], Any]


def _ensure_iterable(data: Any) -> Iterable[Dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, Mapping):
        return [dict(data)]
    return [dict(item) for item in data]


def _resolve_mapping(data_item: Mapping[str, Any], mapping: Mapping[str, Any]) -> Dict[str, Any]:
    mapped: Dict[str, Any] = {}
    for new_key, source_spec in mapping.items():
        if callable(source_spec):
            mapped[new_key] = source_spec(data_item)
        elif isinstance(source_spec, str):
            mapped[new_key] = _get_nested(data_item, source_spec)
        else:
            mapped[new_key] = source_spec
    return mapped


def _get_nested(data: Mapping[str, Any], path: str, delimiter: str = ".") -> Any:
    parts = path.split(delimiter)
    current: Any = data
    for part in parts:
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return None
    return current


def _resolve_condition(condition: Union[str, FilterCallable]) -> FilterCallable:
    if callable(condition):
        return condition

    allowed_ops = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a is not None and a > b,
        "<": lambda a, b: a is not None and a < b,
        ">=": lambda a, b: a is not None and a >= b,
        "<=": lambda a, b: a is not None and a <= b,
    }
    tokens = condition.split()
    if len(tokens) < 3:
        raise ValueError("Condition string must be in the format 'field op value'")

    field = tokens[0]
    op = tokens[1]
    value_str = " ".join(tokens[2:])

    if op not in allowed_ops:
        raise ValueError(f"Unsupported operator '{op}'")

    # Attempt to parse as number or keep string
    try:
        value = json.loads(value_str)
    except json.JSONDecodeError:
        value = value_str.strip("\"')")

    comparator = allowed_ops[op]

    def _predicate(item: Mapping[str, Any]) -> bool:
        item_value = _get_nested(item, field)
        return comparator(item_value, value)

    return _predicate


def _resolve_aggregator(agg_func: Union[str, AggregatorCallable]) -> AggregatorCallable:
    if callable(agg_func):
        return agg_func

    agg_map = {
        "sum": sum,
        "avg": lambda values: sum(values) / len(values) if values else 0,
        "mean": lambda values: sum(values) / len(values) if values else 0,
        "max": lambda values: max(values) if values else None,
        "min": lambda values: min(values) if values else None,
        "count": lambda values: len(values),
    }
    func = agg_map.get(str(agg_func).lower())
    if func is None:
        raise ValueError(f"Unsupported aggregation function '{agg_func}'")
    return func


def _to_csv(rows: Iterable[Mapping[str, Any]]) -> str:
    rows = list(rows)
    if not rows:
        return ""
    output = StringIO()
    fieldnames = sorted({key for row in rows for key in row.keys()})
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _to_json(rows: Iterable[Mapping[str, Any]]) -> str:
    return json.dumps(list(rows))


def _to_xml(rows: Iterable[Mapping[str, Any]], root_name: str = "items", item_name: str = "item") -> str:
    root = Element(root_name)
    for row in rows:
        item_elem = SubElement(root, item_name)
        for key, value in row.items():
            child = SubElement(item_elem, key)
            child.text = "" if value is None else str(value)
    return tostring(root, encoding="unicode")


async def map_fields(
    data: Any,
    mapping: Mapping[str, Any],
) -> Dict[str, Any]:
    if not mapping:
        return {"error": "mapping configuration is required"}
    iterable = _ensure_iterable(data)
    result = [
        await asyncio.to_thread(_resolve_mapping, item, mapping)
        for item in iterable
    ]
    return {"data": result}


async def filter_data(
    data: Any,
    condition: Union[str, FilterCallable],
) -> Dict[str, Any]:
    if not condition:
        return {"error": "condition is required"}
    predicate = _resolve_condition(condition)
    iterable = _ensure_iterable(data)
    result = [item for item in iterable if predicate(item)]
    return {"data": result}


async def aggregate_data(
    data: Any,
    agg_func: Union[str, AggregatorCallable],
    key: Optional[str] = None,
    group_by: Optional[Union[str, Sequence[str]]] = None,
) -> Dict[str, Any]:
    if agg_func is None:
        return {"error": "agg_func is required"}

    aggregator = _resolve_aggregator(agg_func)
    iterable = _ensure_iterable(data)

    if group_by:
        grouped: Dict[Tuple[Any, ...], List[Any]] = defaultdict(list)
        for item in iterable:
            group_key = tuple(_get_nested(item, gb) for gb in ([group_by] if isinstance(group_by, str) else group_by))
            grouped[group_key].append(_get_nested(item, key) if key else item)
        result = {}
        for g_key, values in grouped.items():
            result[g_key if len(g_key) > 1 else g_key[0]] = aggregator(values)
        return {"result": result}

    values = [
        _get_nested(item, key) if key else item
        for item in iterable
    ]
    result = aggregator(values)
    return {"result": result}


async def convert_format(
    data: Any,
    to_format: str,
    *,
    root_name: str = "items",
    item_name: str = "item",
) -> Dict[str, Any]:
    iterable = list(_ensure_iterable(data))
    to_format = to_format.lower()

    if to_format == "csv":
        return {"csv": await asyncio.to_thread(_to_csv, iterable)}
    if to_format == "json":
        return {"json": _to_json(iterable)}
    if to_format == "xml":
        return {"xml": _to_xml(iterable, root_name=root_name, item_name=item_name)}
    if to_format == "dataframe":
        if pd is None:
            return {"error": "pandas is not installed"}
        return {"dataframe": pd.DataFrame(iterable)}

    return {"error": f"Unsupported format '{to_format}'"}


async def custom_transform(
    data: Any,
    transformer: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    if transformer is None:
        return {"error": "transformer function is required"}
    iterable = _ensure_iterable(data)
    result: List[Dict[str, Any]] = []
    for item in iterable:
        try:
            transformed = transformer(dict(item))
            if not isinstance(transformed, Mapping):
                raise TypeError("Transformer must return a mapping")
            result.append(dict(transformed))
        except Exception as exc:  # pragma: no cover - user provided code
            return {"error": str(exc)}
    return {"data": result}
