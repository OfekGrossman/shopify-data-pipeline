"""Bronze layer reader: load the latest raw JSONL from data/bronze/<entity>/ into a DataFrame."""
import json

import pandas as pd

from config import BRONZE_DIR


def latest_bronze_file(entity: str):
    """Newest JSONL file in data/bronze/<entity>/ (by ISO-dated name)."""
    files = sorted((BRONZE_DIR / entity).glob(f"{entity}_*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No bronze files found for '{entity}'")
    return files[-1]


def read_bronze_df(entity: str, record_path=None, meta=None) -> pd.DataFrame:
    """Read the latest bronze file into a flat DataFrame.
    - default: one row per record (products, customers, orders)
    - with record_path: explode a nested list, one row per sub-record (order line items)
    """
    records = []
    with open(latest_bronze_file(entity), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if record_path:
        return pd.json_normalize(records, record_path=record_path, meta=meta)
    return pd.json_normalize(records)

