"""
Gold: order line grain sales fact. one row per order line item, enriched for analysis.
Joins each line item to:
  - fact_orders  -> order_date, source, customer, customer_type 
  - dim_product  -> category, vendor 
Line level measures (quantity, unit_price, line_revenue) stay at line grain.
"""

from warehouse import Warehouse
from logger import log_message


def build_fact_order_items() -> None:
    try:
        log_message("Starting gold fact_order_items build", stage="gold", level="INFO")

        sql = """
            SELECT
                oi.order_id,
                oi.product_id,
                fo.order_date,
                fo.source,
                fo.customer_id,
                fo.customer_type,
                COALESCE(dp.category, oi.product_type, 'Unknown') AS category,
                COALESCE(dp.vendor, 'Unknown')                    AS vendor,
                oi.title,
                oi.quantity,
                oi.unit_price,
                oi.line_revenue
            FROM silver.order_items oi
            JOIN gold.fact_orders  fo USING (order_id)
            LEFT JOIN gold.dim_product dp USING (product_id)
        """

        with Warehouse() as wh:
            df = wh.query(sql)
            wh.write_table(df, "fact_order_items", schema="gold")

        # data-quality visibility: unmatched products = line items whose product isn't in dim_product
        unmatched = int(df["product_id"].isna().sum())
        log_message("Data quality check", stage="gold", level="INFO",
                    line_items=len(df), unmatched_product=unmatched,
                    total_line_revenue=float(df["line_revenue"].sum()))

        log_message("Built gold fact_order_items", stage="gold", level="INFO", rows=len(df))

    except Exception as e:
        log_message("Failed to build gold fact_order_items", stage="gold", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_fact_order_items()
