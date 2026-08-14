"""
Gold: market-basket fact at product-GROUP grain (frequent itemsets).
Generalises fact_product_pairs to groups of any size. Builds every co-occurring group
of size 2..MAX_GROUP_SIZE in ONE table with a `group_size` column, so a size is chosen
at query time (WHERE group_size = 3). Metrics:
  - group_orders = orders containing ALL members of the group
  - support       = group_orders / all orders
  - lift          = support(group) / (support(item_1) * support(item_2) * ...)
                    (>1 = the whole group clusters together more than chance)
Confidence is intentionally omitted for groups (it is a directional rule metric and does
not generalise cleanly past pairs — see fact_product_pairs for A->B / B->A).

Baskets hold 1-5 items, so sizes >5 come back empty. A product bought more than once in an
order counts once (basket = presence). The single null-product line is excluded.
"""

from itertools import combinations
from collections import Counter

import pandas as pd

from warehouse import Warehouse
from logger import log_message

MAX_GROUP_SIZE = 5    # largest group to enumerate
MIN_GROUP_ORDERS = 5  # only keep groups seen together in at least this many orders


def build_fact_product_groups() -> None:
    try:
        log_message("Starting gold fact_product_groups build", stage="gold", level="INFO")

        with Warehouse() as wh:
            basket = wh.query("""
                SELECT DISTINCT order_id, product_id
                FROM silver.order_items
                WHERE product_id IS NOT NULL
            """)
            titles = wh.query("SELECT product_id, title FROM gold.dim_product")

        n_orders = basket["order_id"].nunique()
        item_orders = basket.groupby("product_id")["order_id"].nunique().to_dict()  # support counts
        title_of = dict(zip(titles["product_id"], titles["title"]))

        # one sorted list of distinct products per order
        per_order = basket.groupby("order_id")["product_id"].apply(lambda s: sorted(s.unique()))

        # count every size-k combination across all orders
        counts = Counter()
        for products in per_order:
            for k in range(2, MAX_GROUP_SIZE + 1):
                if len(products) >= k:
                    for combo in combinations(products, k):
                        counts[combo] += 1

        rows = []
        for combo, group_orders in counts.items():
            if group_orders < MIN_GROUP_ORDERS:
                continue
            support = group_orders / n_orders
            independent = 1.0
            for pid in combo:
                independent *= item_orders[pid] / n_orders
            rows.append({
                "group_size": len(combo),
                "member_ids": " | ".join(combo),
                "member_titles": " | ".join(title_of.get(pid, "?") for pid in combo),
                "group_orders": group_orders,
                "support": support,
                "lift": support / independent,
            })

        df = pd.DataFrame(rows).sort_values(
            ["group_size", "group_orders"], ascending=[True, False]
        ).reset_index(drop=True)

        with Warehouse() as wh:
            wh.write_table(df, "fact_product_groups", schema="gold")

        log_message("Built gold fact_product_groups", stage="gold", level="INFO",
                    rows=len(df), max_group_size=MAX_GROUP_SIZE,
                    min_group_orders=MIN_GROUP_ORDERS)

    except Exception as e:
        log_message("Failed to build gold fact_product_groups", stage="gold", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_fact_product_groups()
