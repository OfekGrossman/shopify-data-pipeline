"""Silver: build the clean order_items table (one row per line item) from bronze orders."""

import pandas as pd
from pipeline.bronze_reader import read_bronze_df
from warehouse import Warehouse
from logger import log_message


def build_silver_order_items() -> None:
    try:
        log_message("Starting silver order_items build", stage="silver", level="INFO")

        # explode: one row per line item, carrying the order id onto each
        df = read_bronze_df("orders", record_path=["lineItems", "edges"], meta=["id"])
        log_message("Read bronze line items", stage="silver", level="INFO", rows=len(df))

        df = df.rename(columns={
            "id": "order_id",
            "node.title": "title",
            "node.quantity": "quantity",
            "node.originalUnitPriceSet.shopMoney.amount": "unit_price",     # list price per unit
            "node.discountedTotalSet.shopMoney.amount": "line_revenue",     # actual $ for the line (net of discounts)
            "node.product.id": "product_id",
            "node.product.productType": "product_type",
        })

        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")        
        df["line_revenue"] = pd.to_numeric(df["line_revenue"], errors="coerce")    
        df["order_id"] = df["order_id"].str.split("/").str[-1]        # strip shopify prefix
        df["product_id"] = df["product_id"].str.split("/").str[-1]    # strip shopify prefix 

        df = df[["order_id", "product_id", "title", "quantity",
                 "unit_price", "line_revenue", "product_type"]]       

        # data-quality visibility
        log_message("Data quality check", stage="silver", level="INFO",
                    line_items=len(df),
                    null_product=int(df["product_id"].isna().sum()),
                    null_product_type=int(df["product_type"].isna().sum()),
                    null_revenue=int(df["line_revenue"].isna().sum()))   

        with Warehouse() as wh:
            wh.write_table(df, "order_items")

        log_message("Built silver order_items", stage="silver", level="INFO", rows=len(df))

    except Exception as e:
        log_message("Failed to build silver order_items", stage="silver", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_silver_order_items()