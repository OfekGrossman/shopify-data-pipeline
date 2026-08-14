"""
Full pipeline: bronze (extract from Shopify) -> silver -> gold.

Run:  python run_pipeline.py

For a fast offline rebuild (silver + gold from existing bronze, NO Shopify calls),
run run_pipeline_local.py instead — it reuses the stage functions defined here.

Each step logs START / DONE + elapsed seconds via the project logger (stage="pipeline").
Steps run in dependency order and the pipeline stops on the first failure.
"""

import time

from logger import log_message

# --- bronze (extract from Shopify) ---
from pipeline.extract import extract_to_bronze
from pipeline.extract_orders import ORDERS_QUERY
from pipeline.extract_products import PRODUCTS_QUERY
from pipeline.extract_customers import CUSTOMERS_QUERY

# --- silver ---
from pipeline.silver_orders import build_silver_orders
from pipeline.silver_order_items import build_silver_order_items
from pipeline.silver_products import build_silver_products
from pipeline.silver_customers import build_silver_customers

# --- gold ---
from pipeline.gold_dim_product import build_dim_product
from pipeline.gold_dim_customer import build_dim_customer
from pipeline.gold_fact_orders import build_fact_orders
from pipeline.gold_fact_order_items import build_fact_order_items
from pipeline.gold_fact_product_pairs import build_fact_product_pairs
from pipeline.gold_fact_vendor_pairs import build_fact_vendor_pairs
from pipeline.gold_fact_product_groups import build_fact_product_groups
from pipeline.gold_fact_vendor_groups import build_fact_vendor_groups


def step(label, fn):
    """Run one step, logging start/end + elapsed. Exceptions propagate to stop the run."""
    log_message(f"START {label}", stage="pipeline", level="INFO")
    t0 = time.perf_counter()
    fn()
    log_message(f"DONE {label}", stage="pipeline", level="INFO",
                seconds=round(time.perf_counter() - t0, 1))


def run_bronze():
    step("bronze.orders",    lambda: extract_to_bronze("orders", ORDERS_QUERY, "orders"))
    step("bronze.products",  lambda: extract_to_bronze("products", PRODUCTS_QUERY, "products"))
    step("bronze.customers", lambda: extract_to_bronze("customers", CUSTOMERS_QUERY, "customers"))


def run_silver():
    step("silver.orders",      build_silver_orders)
    step("silver.order_items", build_silver_order_items)
    step("silver.products",    build_silver_products)
    step("silver.customers",   build_silver_customers)


def run_gold():
    # dimensions first, then facts that join to them, then the basket facts
    step("gold.dim_product",         build_dim_product)
    step("gold.dim_customer",        build_dim_customer)
    step("gold.fact_orders",         build_fact_orders)
    step("gold.fact_order_items",    build_fact_order_items)
    step("gold.fact_product_pairs",  build_fact_product_pairs)
    step("gold.fact_vendor_pairs",   build_fact_vendor_pairs)
    step("gold.fact_product_groups", build_fact_product_groups)
    step("gold.fact_vendor_groups",  build_fact_vendor_groups)


def main():
    t0 = time.perf_counter()
    try:
        log_message("Full pipeline started", stage="pipeline", level="INFO")
        run_bronze()
        run_silver()
        run_gold()
        log_message("Full pipeline finished", stage="pipeline", level="INFO",
                    seconds=round(time.perf_counter() - t0, 1))
    except Exception as e:
        log_message("Pipeline failed", stage="pipeline", level="ERROR",
                    error=str(e), seconds=round(time.perf_counter() - t0, 1))
        raise


if __name__ == "__main__":
    main()
