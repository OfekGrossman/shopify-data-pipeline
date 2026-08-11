"""
DuckDB warehouse engine. 
Contains load and read helpers for the silver + gold layers.
Tables live in a schema.
Allows to reuse one connection across many queries instead of reopening the file each call. 
Use as a context manager in scripts,
or keep an instance around and call .close() when done (e.g. in a notebook).
"""

import duckdb
import pandas as pd
from config import DB_PATH
from logger import log_message

class Warehouse:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))   # embedded, no server

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def close(self):
        self.conn.close()

    def write_table(self, df: pd.DataFrame, name: str, schema: str = "silver") -> None:
        self.conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        self.conn.register("_df_to_write", df)
        self.conn.execute(f"CREATE OR REPLACE TABLE {schema}.{name} AS SELECT * FROM _df_to_write")
        self.conn.unregister("_df_to_write")
        log_message("Wrote table", stage="load", level="INFO", table=f"{schema}.{name}", rows=len(df))

    def query(self, sql: str) -> pd.DataFrame:
        return self.conn.execute(sql).df()

    def read_table(self, name: str, schema: str = "silver") -> pd.DataFrame:
        return self.query(f"SELECT * FROM {schema}.{name}")