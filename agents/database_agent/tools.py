"""
Firestore helpers for DatabaseAgent.
"""
import asyncio
import os
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Mapping, Union

from google.cloud import exceptions as gcloud_exceptions
from google.cloud import firestore

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")


@lru_cache(maxsize=1)
def _get_db() -> firestore.Client:
    if not GOOGLE_CLOUD_PROJECT:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT environment variable is not set")
    return firestore.Client(project=GOOGLE_CLOUD_PROJECT)


def _build_query(collection: str, query: Union[Mapping[str, Any], Iterable[Mapping[str, Any]]]):
    db = _get_db()
    coll_ref = db.collection(collection)

    if isinstance(query, Mapping):
        query = [query]
    if not isinstance(query, Iterable):
        raise ValueError("query must be a mapping or iterable of mappings")

    q_ref = coll_ref
    for clause in query:
        field = clause.get("field")
        operator = clause.get("operator", "==")
        value = clause.get("value")
        if field is None:
            raise ValueError("Each query clause must include a 'field'")
        q_ref = q_ref.where(field, operator, value)
    return q_ref


def _store_data_sync(collection: str, data: Mapping[str, Any]) -> Dict[str, Any]:
    db = _get_db()
    doc_ref = db.collection(collection).document()
    doc_ref.set(dict(data))
    return {"record_id": doc_ref.id, "status": "stored"}


def _query_data_sync(collection: str, query: Union[Mapping[str, Any], Iterable[Mapping[str, Any]]]) -> Dict[str, Any]:
    q_ref = _build_query(collection, query)
    results = []
    for doc in q_ref.stream():
        doc_dict = doc.to_dict()
        doc_dict["id"] = doc.id
        results.append(doc_dict)
    return {"results": results}


def _update_record_sync(collection: str, record_id: str, data: Mapping[str, Any]) -> Dict[str, Any]:
    db = _get_db()
    doc_ref = db.collection(collection).document(record_id)
    doc_ref.update(dict(data))
    return {"record_id": record_id, "status": "updated"}


def _delete_record_sync(collection: str, record_id: str) -> Dict[str, Any]:
    db = _get_db()
    doc_ref = db.collection(collection).document(record_id)
    doc_ref.delete()
    return {"record_id": record_id, "status": "deleted"}


async def store_data(collection: str, data: Mapping[str, Any]) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_store_data_sync, collection, data)
    except (RuntimeError, gcloud_exceptions.GoogleCloudError) as exc:
        return {"error": str(exc)}


async def query_data(
    collection: str, query: Union[Mapping[str, Any], Iterable[Mapping[str, Any]]]
) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_query_data_sync, collection, query)
    except (RuntimeError, ValueError, gcloud_exceptions.GoogleCloudError) as exc:
        return {"error": str(exc)}


async def update_record(collection: str, record_id: str, data: Mapping[str, Any]) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_update_record_sync, collection, record_id, data)
    except (RuntimeError, gcloud_exceptions.NotFound) as exc:
        return {"error": str(exc)}


async def delete_record(collection: str, record_id: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(_delete_record_sync, collection, record_id)
    except (RuntimeError, gcloud_exceptions.GoogleCloudError) as exc:
        return {"error": str(exc)}
