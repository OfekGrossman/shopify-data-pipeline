"""Gold: order-grain fact — one row per order, with a new/returning customer flag."""

from warehouse import Warehouse
from logger import log_message


def build_fact_orders() -> None:
    try:
        log_message("Starting gold fact_orders build", stage="gold", level="INFO")

        sql = """
            SELECT
                order_id,
                order_name,
                CAST(processed_at AS DATE) AS order_date,
                processed_at,
                customer_id,
                COALESCE(source, 'unknown') AS source,
                financial_status,
                total_amount,
                currency,
                CASE
                    WHEN customer_id IS NULL THEN 'guest'
                    WHEN ROW_NUMBER() OVER (
                             PARTITION BY customer_id
                             ORDER BY processed_at, order_id) = 1 THEN 'new'
                    ELSE 'returning'
                END AS customer_type
            FROM silver.orders
        """

        with Warehouse() as wh:
            df = wh.query(sql)
            wh.write_table(df, "fact_orders", schema="gold")

        log_message("Built gold fact_orders", stage="gold", level="INFO", rows=len(df))

    except Exception as e:
        log_message("Failed to build gold fact_orders", stage="gold", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_fact_orders()
