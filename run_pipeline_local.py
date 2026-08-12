"""
Local pipeline: silver -> gold only, from existing bronze files (NO Shopify calls).

Run:  python run_pipeline_local.py

Use this while iterating on the silver / gold logic — it's fast and offline.
For a full run including the Shopify extract, use run_pipeline.py.
Reuses the stage functions defined in run_pipeline.py, so there's no duplicated logic.
"""

import time

from logger import log_message
from run_pipeline import run_silver, run_gold


def main():
    t0 = time.perf_counter()
    try:
        log_message("Local pipeline started (no extract)", stage="pipeline", level="INFO")
        run_silver()
        run_gold()
        log_message("Local pipeline finished", stage="pipeline", level="INFO",
                    seconds=round(time.perf_counter() - t0, 1))
    except Exception as e:
        log_message("Pipeline failed", stage="pipeline", level="ERROR",
                    error=str(e), seconds=round(time.perf_counter() - t0, 1))
        raise


if __name__ == "__main__":
    main()
