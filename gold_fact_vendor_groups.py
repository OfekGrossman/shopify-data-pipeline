"""
Gold: market-basket fact at vendor-GROUP grain (frequent itemsets).
Same idea as fact_product_groups, but the item is the vendor of each line's product.
Each order is reduced to its distinct set of vendors first, then every size-2..
MAX_GROUP_SIZE combination of vendors is counted. Products with no vendor are excluded.
Metrics: group_orders, support, lift (confidence omitted for groups; see fact_vendor_pairs).
"""

from itertools import combinations
from collections import Counter

import pandas as pd

from warehouse import Warehouse
from logger import log_message

MAX_GROUP_SIZE = 5
MIN_GROUP_ORDERS = 5


def build_fact_vendor_groups() -> None:
    try:
        log_message("Starting gold fact_vendor_groups build", stage="gold", level="INFO")

        with Warehouse() as wh:
            basket = wh.query("""
                SELECT DISTINCT oi.order_id, p.vendor
                FROM silver.order_items oi
                JOIN silver.products p ON p.product_id = oi.product_id
                WHERE p.vendor IS NOT NULL
            """)

        n_orders = basket["order_id"].nunique()
        item_orders = basket.groupby("vendor")["order_id"].nunique().to_dict()

        per_order = basket.groupby("order_id")["vendor"].apply(lambda s: sorted(s.unique()))

        counts = Counter()
        for vendors in per_order:
            for k in range(2, MAX_GROUP_SIZE + 1):
                if len(vendors) >= k:
                    for combo in combinations(vendors, k):
                        counts[combo] += 1

        rows = []
        for combo, group_orders in counts.items():
            if group_orders < MIN_GROUP_ORDERS:
                continue
            support = group_orders / n_orders
            independent = 1.0
            for v in combo:
                independent *= item_orders[v] / n_orders
            rows.append({
                "group_size": len(combo),
                "members": " | ".join(combo),
                "group_orders": group_orders,
                "support": support,
                "lift": support / independent,
            })

        df = pd.DataFrame(rows).sort_values(
            ["group_size", "group_orders"], ascending=[True, False]
        ).reset_index(drop=True)

        with Warehouse() as wh:
            wh.write_table(df, "fact_vendor_groups", schema="gold")

        log_message("Built gold fact_vendor_groups", stage="gold", level="INFO",
                    rows=len(df), max_group_size=MAX_GROUP_SIZE,
                    min_group_orders=MIN_GROUP_ORDERS)

    except Exception as e:
        log_message("Failed to build gold fact_vendor_groups", stage="gold", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_fact_vendor_groups()
