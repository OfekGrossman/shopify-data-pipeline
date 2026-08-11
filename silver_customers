"""Silver: build the clean customers table from bronze customers."""

import pandas as pd
from bronze_reader import read_bronze_df
from warehouse import Warehouse
from logger import log_message


def build_silver_customers() -> None:
    try:
        log_message("Starting silver customers build", stage="silver", level="INFO")

        df = read_bronze_df("customers")
        log_message("Read bronze customers", stage="silver", level="INFO", rows=len(df))

        df = df.rename(columns={
            "id": "customer_id",
            "createdAt": "created_at",
            "numberOfOrders": "number_of_orders",
            "defaultAddress.city": "city",
            "defaultAddress.country": "country",
        })

        # guard: if NO customer had an address, the dotted columns won't exist
        for col in ["city", "country"]:
            if col not in df.columns:
                df[col] = pd.NA

        df["customer_id"] = df["customer_id"].str.split("/").str[-1]        # strip gid prefix
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce").dt.tz_localize(None)
        df["number_of_orders"] = pd.to_numeric(df["number_of_orders"], errors="coerce")

        df = df[["customer_id", "created_at", "number_of_orders", "city", "country"]]

        log_message("Data quality check", stage="silver", level="INFO",
                    customers=len(df),
                    null_city=int(df["city"].isna().sum()),
                    null_country=int(df["country"].isna().sum()))

        with Warehouse() as wh:
            wh.write_table(df, "customers")

        log_message("Built silver customers", stage="silver", level="INFO", rows=len(df))

    except Exception as e:
        log_message("Failed to build silver customers", stage="silver", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_silver_customers()