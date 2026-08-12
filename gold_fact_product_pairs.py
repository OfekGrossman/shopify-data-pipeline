"""
Gold: market-basket fact at product-pair grain.
For every pair of products bought in the same order, compute how often they co-occur
and the standard association metrics:
  - support(A,B)      = orders with both / all orders
  - confidence(A->B)  = orders with both / orders with A
  - lift              = support(A,B) / (support(A) * support(B))   (1.0 = independent)

Denominator = all orders that contain at least one identifiable product. A product that
appears twice in one order counts once (basket = presence, not quantity). The null
product_id line is excluded. Pairs are ordered a < b so each unordered pair appears once.
"""

from warehouse import Warehouse
from logger import log_message

# only keep pairs seen together in at least this many orders (tune for noise vs coverage)
MIN_PAIR_ORDERS = 5


def build_fact_product_pairs() -> None:
    try:
        log_message("Starting gold fact_product_pairs build", stage="gold", level="INFO")

        sql = f"""
            WITH basket AS (
                SELECT DISTINCT order_id, product_id
                FROM silver.order_items
                WHERE product_id IS NOT NULL
            ),
            n AS (
                SELECT COUNT(DISTINCT order_id) AS total_orders FROM basket
            ),
            item AS (
                SELECT product_id, COUNT(DISTINCT order_id) AS item_orders
                FROM basket GROUP BY product_id
            ),
            pair AS (
                SELECT a.product_id AS product_id_a,
                       b.product_id AS product_id_b,
                       COUNT(*)     AS pair_orders
                FROM basket a
                JOIN basket b
                  ON a.order_id = b.order_id
                 AND a.product_id < b.product_id
                GROUP BY a.product_id, b.product_id
            )
            SELECT
                p.product_id_a,
                p.product_id_b,
                da.title AS product_a,
                db.title AS product_b,
                p.pair_orders,
                p.pair_orders::DOUBLE / n.total_orders            AS support,
                p.pair_orders::DOUBLE / ia.item_orders            AS confidence_a_to_b,
                p.pair_orders::DOUBLE / ib.item_orders            AS confidence_b_to_a,
                (p.pair_orders::DOUBLE * n.total_orders)
                    / (ia.item_orders * ib.item_orders)           AS lift
            FROM pair p
            CROSS JOIN n
            JOIN item ia ON ia.product_id = p.product_id_a
            JOIN item ib ON ib.product_id = p.product_id_b
            LEFT JOIN gold.dim_product da ON da.product_id = p.product_id_a
            LEFT JOIN gold.dim_product db ON db.product_id = p.product_id_b
            WHERE p.pair_orders >= {MIN_PAIR_ORDERS}
            ORDER BY lift DESC, pair_orders DESC
        """

        with Warehouse() as wh:
            df = wh.query(sql)
            wh.write_table(df, "fact_product_pairs", schema="gold")

        log_message("Built gold fact_product_pairs", stage="gold", level="INFO",
                    rows=len(df), min_pair_orders=MIN_PAIR_ORDERS)

    except Exception as e:
        log_message("Failed to build gold fact_product_pairs", stage="gold", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_fact_product_pairs()
