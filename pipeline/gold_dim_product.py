"""Gold: product dimension. one row per product, cleaned for analysis."""

from warehouse import Warehouse
from logger import log_message


def build_dim_product() -> None:
    try:
        log_message("Starting gold dim_product build", stage="gold", level="INFO")

        sql = """
            SELECT
                product_id,
                title,
                COALESCE(product_type, 'Unknown') AS category,
                COALESCE(vendor, 'Unknown')       AS vendor,
                status
            FROM silver.products
        """

        with Warehouse() as wh:
            df = wh.query(sql)
            wh.write_table(df, "dim_product", schema="gold")

        log_message("Built gold dim_product", stage="gold", level="INFO", rows=len(df))

    except Exception as e:
        log_message("Failed to build gold dim_product", stage="gold", level="ERROR", error=str(e))
        raise


if __name__ == "__main__":
    build_dim_product()
