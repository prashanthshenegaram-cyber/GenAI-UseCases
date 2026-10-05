from enum import Enum
from typing import Any


class Serialization(str, Enum):
    ROW_AS_TEXT = "row_text"
    MARKDOWN_TABLE = "markdown_table"
    COLUMN_WISE = "column_wise"


def _clean(value: Any) -> str:
    return "" if value is None else str(value).replace("\n", " ").strip()


def serialize_rows(rows: list[dict[str, Any]], strategy: str = "row_text") -> list[str]:
    strategy = Serialization(strategy).value
    if not rows:
        return []
    columns = list(rows[0])
    if strategy == Serialization.ROW_AS_TEXT.value:
        return [", ".join(f"{column}: {_clean(row.get(column))}" for column in columns) for row in rows]
    if strategy == Serialization.MARKDOWN_TABLE.value:
        header = "| " + " | ".join(columns) + " |"
        separator = "|" + "|".join("---:" if isinstance(rows[0].get(column), (int, float)) else "---" for column in columns) + "|"
        return [header + "\n" + separator + "\n" + "\n".join("| " + " | ".join(_clean(row.get(c)) for c in columns) + " |" for row in rows)]
    return ["\n".join(f"{column}: {', '.join(_clean(row.get(column)) for row in rows)}" for column in columns)]
