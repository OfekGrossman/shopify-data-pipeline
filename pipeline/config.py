"""Configuration file for the data pipeline."""
from pathlib import Path

# The configuration file contains sensitive information (API keys, tokens, etc.) and is gitignored. The fallback in the repository is credentials_example.py
try:    
    from pipeline.credentials import SHOPIFY_ACCESS_TOKEN
except ImportError:
    from pipeline.credentials_example import SHOPIFY_ACCESS_TOKEN

# ========== SHOPIFY (sales data) ===========
SHOPIFY_ACCESS_TOKEN = SHOPIFY_ACCESS_TOKEN
SHOPIFY_SHOP_URL = "ofek-dev-store.myshopify.com"
SHOPIFY_API_VERSION = "2026-07"

# ========== LOCAL PATHS (bronze files + SQLite warehouse + logs) ==========
BRONZE_DIR = Path("data/bronze")     # Raw JSON lands here
DB_PATH = Path("data/warehouse.db")  # silver + gold tables live here
LOG_DIR = Path("logs")
