"""Silver: build the clean silver layer orders table from bronze orders."""

import pandas as pd
from bronze_reader import read_bronze_df
from warehouse import Warehouse
from logger import log_message


def parse_source(tags) -> str:
    """Pull the source out of the tags list ( ['source:meta','synthetic'] -> 'meta' )."""
    for tag in tags or []:
        if tag.startswith("source:"):
            return tag.split(":", 1)[1]
    return None


def build_silver_orders() -> None:
    try:
        log_message("Starting silver orders build", stage="silver", level="INFO")

        df = read_bronze_df("orders")
        log_message("Read bronze orders", stage="silver", level="INFO", rows=len(df))

        df = df.rename(columns={
            "id": "order_id",
            "name": "order_name",
            "processedAt": "processed_at",
            "createdAt": "created_at",
            "displayFinancialStatus": "financial_status",
            "totalPriceSet.shopMoney.amount": "total_amount",
            "totalPriceSet.shopMoney.currencyCode": "currency",
            "customer.id": "customer_id",
        })

        df["source"] = [parse_source(x) for x in df["tags"]]
        df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce") 
        df["processed_at"] = pd.to_datetime(df["processed_at"], utc=True, errors="coerce").dt.tz_localize(None)
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce").dt.tz_localize(None)
        df["order_id"] = df["order_id"].str.split("/").str[-1]  # remove the shop prefix from the order_id
        df["customer_id"] = df["customer_id"].str.split("/").str[-1]  # remove the shop prefix from the customer_id

        df = df[["order_id", "order_name", "processed_at", "created_at",
                 "financial_status", "total_amount", "currency", "source", "customer_id"]]

        # data-quality visibility: how many nulls did cleaning leave behind?
        log_message("Data quality check", stage="silver", level="INFO",
                    null_source=int(df["source"].isna().sum()),
                    null_customer=int(df["customer_id"].isna().sum()),
                    null_amount=int(df["total_amount"].isna().sum()))

        with Warehouse() as wh:
            wh.write_table(df, "orders")

        log_message("Built silver orders", stage="silver", level="INFO", rows=len(df))

    except Exception as e:
        log_message("Failed to build silver orders", stage="silver", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_silver_orders()