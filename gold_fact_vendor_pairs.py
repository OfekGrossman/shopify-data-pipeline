"""
Gold: market-basket fact at vendor-pair grain.
Same association metrics as fact_product_pairs, but the "item" is the vendor of each
line's product. Each order is reduced to its distinct set of vendors first, so an order
with three products from the same vendor contributes that vendor once. Products with no
vendor are excluded (0 in this dataset).
"""

from warehouse import Warehouse
from logger import log_message

MIN_PAIR_ORDERS = 5


def build_fact_vendor_pairs() -> None:
    try:
        log_message("Starting gold fact_vendor_pairs build", stage="gold", level="INFO")

        sql = f"""
            WITH basket AS (
                SELECT DISTINCT oi.order_id, p.vendor
                FROM silver.order_items oi
                JOIN silver.products p ON p.product_id = oi.product_id
                WHERE p.vendor IS NOT NULL
            ),
            n AS (
                SELECT COUNT(DISTINCT order_id) AS total_orders FROM basket
            ),
            item AS (
                SELECT vendor, COUNT(DISTINCT order_id) AS item_orders
                FROM basket GROUP BY vendor
            ),
            pair AS (
                SELECT a.vendor AS vendor_a,
                       b.vendor AS vendor_b,
                       COUNT(*) AS pair_orders
                FROM basket a
                JOIN basket b
                  ON a.order_id = b.order_id
                 AND a.vendor < b.vendor
                GROUP BY a.vendor, b.vendor
            )
            SELECT
                p.vendor_a,
                p.vendor_b,
                p.pair_orders,
                p.pair_orders::DOUBLE / n.total_orders            AS support,
                p.pair_orders::DOUBLE / ia.item_orders            AS confidence_a_to_b,
                p.pair_orders::DOUBLE / ib.item_orders            AS confidence_b_to_a,
                (p.pair_orders::DOUBLE * n.total_orders)
                    / (ia.item_orders * ib.item_orders)           AS lift
            FROM pair p
            CROSS JOIN n
            JOIN item ia ON ia.vendor = p.vendor_a
            JOIN item ib ON ib.vendor = p.vendor_b
            WHERE p.pair_orders >= {MIN_PAIR_ORDERS}
            ORDER BY lift DESC, pair_orders DESC
        """

        with Warehouse() as wh:
            df = wh.query(sql)
            wh.write_table(df, "fact_vendor_pairs", schema="gold")

        log_message("Built gold fact_vendor_pairs", stage="gold", level="INFO",
                    rows=len(df), min_pair_orders=MIN_PAIR_ORDERS)

    except Exception as e:
        log_message("Failed to build gold fact_vendor_pairs", stage="gold", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_fact_vendor_pairs()
