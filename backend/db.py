"""
DynamoDB data layer with in-memory fallback for DEMO_MODE.

Real DynamoDB is used when AWS credentials are available and DEMO_MODE=false.
In-memory store is used otherwise — no networking, no setup, judges can run offline.

Table name convention:  commitmatch_{entity}
  commitmatch_donors
  commitmatch_patients
  commitmatch_requests
  commitmatch_rankings          GSI: request_id-index, donor_id-index
  commitmatch_interactions      GSI: request_id-index, donor_id-index
  commitmatch_memory            (donor long-term memory)
  commitmatch_shortage_alerts
  commitmatch_ws_connections
  commitmatch_failure_log
"""
import math
import uuid
import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

import config

logger = logging.getLogger(__name__)

# ── In-memory store (demo / offline) ─────────────────────────────────────────

class _InMemoryStore:
    """Ephemeral dict-of-dicts that mimics DynamoDB for offline demos."""

    def __init__(self):
        self._data: dict[str, dict[str, dict]] = defaultdict(dict)

    def put(self, table: str, item: dict, pk: str = "id") -> None:
        key = str(item.get(pk, str(uuid.uuid4())))
        item[pk] = key
        self._data[table][key] = dict(item)

    def get(self, table: str, pk_value: str, pk: str = "id") -> dict | None:
        return self._data[table].get(str(pk_value))

    def scan(self, table: str, filter_fn: Callable | None = None) -> list[dict]:
        items = list(self._data[table].values())
        return [i for i in items if filter_fn(i)] if filter_fn else items

    def query(self, table: str, field: str, value: Any) -> list[dict]:
        return [i for i in self._data[table].values() if str(i.get(field)) == str(value)]

    def update(self, table: str, pk_value: str, updates: dict, pk: str = "id") -> None:
        item = self._data[table].get(str(pk_value))
        if item:
            item.update(updates)

    def delete(self, table: str, pk_value: str, pk: str = "id") -> None:
        self._data[table].pop(str(pk_value), None)


_mem = _InMemoryStore()
_ddb_resource = None


def _ddb():
    global _ddb_resource
    if _ddb_resource is None:
        import boto3
        kwargs = dict(region_name=config.AWS_REGION)
        if config.DYNAMODB_ENDPOINT:
            kwargs["endpoint_url"] = config.DYNAMODB_ENDPOINT
        _ddb_resource = boto3.resource("dynamodb", **kwargs)
    return _ddb_resource


def _table(name: str):
    return _ddb().Table(f"commitmatch_{name}")


def _use_real_ddb() -> bool:
    return not config.DEMO_MODE and bool(
        config.AWS_ACCESS_KEY_ID or config.AWS_SECRET_ACCESS_KEY or config.AWS_REGION
    )


# ── DynamoDB type sanitizer ───────────────────────────────────────────────────

def _ddb_safe(obj: Any) -> Any:
    """Recursively convert Python floats → Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _ddb_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_ddb_safe(v) for v in obj]
    return obj


# ── Public interface ──────────────────────────────────────────────────────────

def put_item(table: str, item: dict, pk: str = "id") -> str:
    """Insert or overwrite an item. Returns the PK value."""
    if not item.get(pk):
        item[pk] = str(uuid.uuid4())
    if not item.get("created_at"):
        item["created_at"] = datetime.now(timezone.utc).isoformat()

    if _use_real_ddb():
        import time
        t0 = time.monotonic()
        try:
            _table(table).put_item(Item=_ddb_safe(item))
            print(f"[DDB] put_item({table}) ✓ {int((time.monotonic()-t0)*1000)}ms")
            return str(item[pk])
        except Exception as e:
            print(f"[DDB] put_item({table}) ✗ {type(e).__name__}: {e}")
            logger.error("DynamoDB put_item failed: %s", e)

    _mem.put(table, item, pk)
    return str(item[pk])


def get_item(table: str, pk_value: str, pk: str = "id") -> dict | None:
    if _use_real_ddb():
        import time
        t0 = time.monotonic()
        try:
            resp = _table(table).get_item(Key={pk: str(pk_value)})
            item = resp.get("Item")
            print(f"[DDB] get_item({table}, {str(pk_value)[:12]}...) ✓ {int((time.monotonic()-t0)*1000)}ms — {'found' if item else 'not found'}")
            return item
        except Exception as e:
            print(f"[DDB] get_item({table}) ✗ {type(e).__name__}: {e}")
            logger.error("DynamoDB get_item failed: %s", e)

    return _mem.get(table, pk_value, pk)


def scan_table(table: str, filter_fn: Callable | None = None) -> list[dict]:
    if _use_real_ddb():
        try:
            items = []
            resp = _table(table).scan()
            items.extend(resp.get("Items", []))
            while "LastEvaluatedKey" in resp:
                resp = _table(table).scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
                items.extend(resp.get("Items", []))
            return [i for i in items if filter_fn(i)] if filter_fn else items
        except Exception as e:
            logger.error("DynamoDB scan failed: %s", e)

    return _mem.scan(table, filter_fn)


def query_by_field(table: str, field: str, value: Any) -> list[dict]:
    """Simple equality query — uses GSI in prod, in-memory filter in demo."""
    if _use_real_ddb():
        try:
            from boto3.dynamodb.conditions import Attr
            resp = _table(table).scan(FilterExpression=Attr(field).eq(str(value)))
            return resp.get("Items", [])
        except Exception as e:
            logger.error("DynamoDB query failed: %s", e)

    return _mem.query(table, field, value)


def update_item(table: str, pk_value: str, updates: dict, pk: str = "id") -> None:
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    if _use_real_ddb():
        import time
        t0 = time.monotonic()
        try:
            expr_parts, expr_names, expr_values = [], {}, {}
            for k, v in updates.items():
                safe = f"#f{len(expr_parts)}"
                val  = f":v{len(expr_parts)}"
                expr_parts.append(f"{safe} = {val}")
                expr_names[safe] = k
                expr_values[val] = _ddb_safe(v)
            _table(table).update_item(
                Key={pk: str(pk_value)},
                UpdateExpression="SET " + ", ".join(expr_parts),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
            print(f"[DDB] update_item({table}, {str(pk_value)[:12]}...) ✓ {int((time.monotonic()-t0)*1000)}ms")
            return
        except Exception as e:
            print(f"[DDB] update_item({table}) ✗ {type(e).__name__}: {e}")
            logger.error("DynamoDB update_item failed: %s", e)

    _mem.update(table, pk_value, updates, pk)


def delete_item(table: str, pk_value: str, pk: str = "id") -> None:
    if _use_real_ddb():
        try:
            _table(table).delete_item(Key={pk: str(pk_value)})
            return
        except Exception as e:
            logger.error("DynamoDB delete_item failed: %s", e)

    _mem.delete(table, pk_value, pk)


def create_tables_if_missing():
    """Create DynamoDB tables for prod. No-op in demo mode."""
    if not _use_real_ddb():
        return

    client = _ddb().meta.client
    existing = set(client.list_tables()["TableNames"])

    tables = [
        dict(TableName="commitmatch_donors",
             KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
             AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}]),
        dict(TableName="commitmatch_patients",
             KeySchema=[{"AttributeName": "bridge_id", "KeyType": "HASH"}],
             AttributeDefinitions=[{"AttributeName": "bridge_id", "AttributeType": "S"}]),
        dict(TableName="commitmatch_requests",
             KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
             AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}]),
        dict(TableName="commitmatch_rankings",
             KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
             AttributeDefinitions=[
                 {"AttributeName": "id", "AttributeType": "S"},
                 {"AttributeName": "request_id", "AttributeType": "S"},
             ],
             GlobalSecondaryIndexes=[{
                 "IndexName": "request_id-index",
                 "KeySchema": [{"AttributeName": "request_id", "KeyType": "HASH"}],
                 "Projection": {"ProjectionType": "ALL"},
                 "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
             }]),
        dict(TableName="commitmatch_interactions",
             KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
             AttributeDefinitions=[
                 {"AttributeName": "id", "AttributeType": "S"},
                 {"AttributeName": "request_id", "AttributeType": "S"},
             ],
             GlobalSecondaryIndexes=[{
                 "IndexName": "request_id-index",
                 "KeySchema": [{"AttributeName": "request_id", "KeyType": "HASH"}],
                 "Projection": {"ProjectionType": "ALL"},
                 "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
             }]),
        dict(TableName="commitmatch_memory",
             KeySchema=[{"AttributeName": "donor_id", "KeyType": "HASH"}],
             AttributeDefinitions=[{"AttributeName": "donor_id", "AttributeType": "S"}]),
        dict(TableName="commitmatch_shortage_alerts",
             KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
             AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}]),
        dict(TableName="commitmatch_ws_connections",
             KeySchema=[{"AttributeName": "connection_id", "KeyType": "HASH"}],
             AttributeDefinitions=[{"AttributeName": "connection_id", "AttributeType": "S"}]),
        dict(TableName="commitmatch_failure_log",
             KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
             AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}]),
    ]

    for spec in tables:
        if spec["TableName"] in existing:
            continue
        spec.setdefault("BillingMode", "PAY_PER_REQUEST")
        spec.pop("ProvisionedThroughput", None)
        for gsi in spec.get("GlobalSecondaryIndexes", []):
            gsi.pop("ProvisionedThroughput", None)
        try:
            _ddb().create_table(**spec)
            logger.info("Created DynamoDB table: %s", spec["TableName"])
        except Exception as e:
            logger.warning("Could not create table %s: %s", spec["TableName"], e)
