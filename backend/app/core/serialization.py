import dataclasses
import json
from typing import Any

from pydantic import BaseModel


def jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return jsonable(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return json.loads(json.dumps(value, default=str))


def bounded(value: Any, max_chars: int) -> tuple[Any, bool]:
    data = jsonable(value)
    text = json.dumps(data, ensure_ascii=False)
    if len(text) <= max_chars:
        return data, False
    return text[:max_chars] + "…", True


def summarize(value: Any, limit: int = 96) -> str:
    if isinstance(value, dict):
        parts = [f"{k}({len(v)})" if isinstance(v, (list, dict)) else str(k) for k, v in list(value.items())[:6]]
        return f"{len(value)} field(s): {', '.join(parts)}"[:limit]
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    return str(value)[:limit]
