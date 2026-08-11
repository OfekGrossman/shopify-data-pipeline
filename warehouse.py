"""
SQLite warehouse engine. 
Contains load and read helpers for the silver + gold layers.
Allows to reuse one connection across many queries instead of reopening the file each call. 
Use as a context manager in scripts,
or keep an instance around and call .close() when done (e.g. in a notebook).
"""

import sqlite3
import pandas as pd
from config import DB_PATH
from logger import log_message


class Warehouse:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)   # the reusable connection

    # alows `with Warehouse() as wh:` to auto-close the connection
    def __enter__(self): 
        return self

    def __exit__(self, exc_type, exc, tb): 
        self.close()

    # allows to call wh.close() when done (e.g. in a notebook)
    def close(self):
        self.conn.close()

    # load a dataframe into the warehouse, replacing or appending to an existing table
    def write_table(self, df: pd.DataFrame, name: str, if_exists: str = "replace") -> None:
        df.to_sql(name, self.conn, if_exists=if_exists, index=False)
        self.conn.commit()
        log_message("Wrote table", stage="load", level="INFO", table=name, rows=len(df))

    # execute a SQL query and return the results as a dataframe
    def query(self, sql: str) -> pd.DataFrame:
        return pd.read_sql_query(sql, self.conn)


    