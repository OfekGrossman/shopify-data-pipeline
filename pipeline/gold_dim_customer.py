"""Gold: customer dimension. one row per customer, cleaned for analysis."""

from warehouse import Warehouse
from logger import log_message


def build_dim_customer() -> None:
    try:
        log_message("Starting gold dim_customer build", stage="gold", level="INFO")

        sql = """
            SELECT
                customer_id,
                COALESCE(city, 'Unknown')    AS city,
                COALESCE(country, 'Unknown') AS country,
                CAST(created_at AS DATE)     AS customer_since
            FROM silver.customers
        """

        with Warehouse() as wh:
            df = wh.query(sql)
            wh.write_table(df, "dim_customer", schema="gold")

        log_message("Built gold dim_customer", stage="gold", level="INFO", rows=len(df))

    except Exception as e:
        log_message("Failed to build gold dim_customer", stage="gold", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_dim_customer()
