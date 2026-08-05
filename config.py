from pathlib import Path
from credentials import SHOPIFY_ACCESS_TOKEN
"""
Configuration file for the data pipeline.
"""

# ========== SHOPIFY (sales data) ===========
SHOPIFY_SHOP_URL = "your-store.myshopify.com"
SHOPIFY_ACCESS_TOKEN = SHOPIFY_ACCESS_TOKEN
SHOPIFY_API_VERSION = "2026-07"

# ========== LOCAL PATHS (bronze files + SQLite warehouse + logs) ==========
BRONZE_DIR = Path("data/bronze")     # Raw JSON lands here
DB_PATH = Path("data")  # silver + gold tables live here
LOG_DIR = Path("logs")
