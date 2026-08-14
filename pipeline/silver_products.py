"""Silver: build the clean products table from bronze products."""

import pandas as pd
from pipeline.bronze_reader import read_bronze_df
from warehouse import Warehouse
from logger import log_message


def build_silver_products() -> None:
    try:
        log_message("Starting silver products build", stage="silver", level="INFO")

        df = read_bronze_df("products")
        log_message("Read bronze products", stage="silver", level="INFO", rows=len(df))

        df = df.rename(columns={
            "id": "product_id",
            "productType": "product_type",
            "createdAt": "created_at",
        })

        df["product_id"] = df["product_id"].str.split("/").str[-1]          # strip gid prefix
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce").dt.tz_localize(None)
        df["tags"] = df["tags"].str.join(",")                              # list -> comma string
        df["product_type"] = (df["product_type"].replace("", pd.NA).
                              str.title()) # capitalize product_type, and convert empty strings to nulls
        df["vendor"] = (df["vendor"].replace("", pd.NA).
                        str.title()) # capitalize vendor, and convert empty strings to nulls

        df = df[["product_id", "title", "product_type", "vendor", "tags", "status", "created_at"]]

        log_message("Data quality check", stage="silver", level="INFO",
                    products=len(df),
                    null_product_type=int(df["product_type"].isna().sum()))

        with Warehouse() as wh:
            wh.write_table(df, "products")

        log_message("Built silver products", stage="silver", level="INFO", rows=len(df))

    except Exception as e:
        log_message("Failed to build silver products", stage="silver", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_silver_products()