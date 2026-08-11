"""Silver: build the clean silver layer orders table from bronze orders."""

import pandas as pd
from bronze_reader import read_bronze_df
from warehouse import Warehouse
from logger import log_message


def parse_source(tags) -> str:
    """Pull the source out of the tags list, e.g. ['source:meta','synthetic'] -> 'meta'."""
    for tag in tags or []:
        if tag.startswith("source:"):
            return tag.split(":", 1)[1]
    return None


def build_silver_orders() -> None:
    df = read_bronze_df("orders")

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

    df["source"] = df["tags"].apply(parse_source)
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")
    df["processed_at"] = pd.to_datetime(df["processed_at"], errors="coerce", utc=True).dt.tz_localize(None)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True).dt.tz_localize(None)

    df = df[["order_id", "order_name", "processed_at", "created_at",
             "financial_status", "total_amount", "currency", "source", "customer_id"]]

    with Warehouse() as wh:
        wh.write_table(df, "orders")
    log_message("Built silver orders", stage="silver", level="INFO", rows=len(df))


if __name__ == "__main__":
    build_silver_orders()