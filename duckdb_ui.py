"""launch the DuckDB local web UI over the warehouse"""
import duckdb
from config import DB_PATH

con = duckdb.connect(str(DB_PATH))     # opens data/warehouse.duckdb
con.execute("INSTALL ui")              # one-time download of the ui extension
con.execute("LOAD ui")
con.execute("CALL start_ui()")         # starts the server + opens your browser
print("DuckDB UI at http://localhost:4213 — press Ctrl+C to stop")
try:
    input()                            # keeps the process (and server) alive
except KeyboardInterrupt:
    pass