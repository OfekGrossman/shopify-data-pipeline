"""
generate synthetic orders in the Shopify dev store.
Not part of the ETL pipeline.
this just seeds the store with realistic
orders (varied baskets, backdated across the past year, tagged with a
synthetic marketing source) so there's enough data to analyze.

Built to run unattended overnight: it backs off and waits out Shopify's
order-creation throttle rather than giving up. Re-running ADDS more orders
(no dedup), so if you wake up short of the target, just lower n and run again.
Launch from the project root:  python generate_orders.py
"""
from datetime import datetime, timedelta, timezone
import random
import time

from extract import extract_data
from logger import log_message

BASE_PACE = 5   # seconds between orders (steady pace so we don't keep re-tripping the limit)

VARIANTS_QUERY = """
{
  productVariants(first: 100) {
    edges { node { id price product { title productType } } }
  }
}
"""

CREATE_ORDER = """
mutation CreateOrder($order: OrderCreateOrderInput!, $options: OrderCreateOptionsInput) {
  orderCreate(order: $order, options: $options) {
    userErrors { field message }
    order { id name processedAt displayFinancialStatus }
  }
}
"""


def get_variant_pool() -> list:
    """Fetch product variants to reference in generated orders."""
    result = extract_data(VARIANTS_QUERY)
    variants = [edge["node"] for edge in result["data"]["productVariants"]["edges"]]
    log_message("Fetched variant pool", stage="generate", level="INFO", count=len(variants))
    return variants


def random_processed_at(days_back: int = 365) -> str:
    """A random ISO-8601 timestamp within the past `days_back` days (UTC)."""
    offset = timedelta(days=random.randint(0, days_back), seconds=random.randint(0, 86400))
    return (datetime.now(timezone.utc) - offset).isoformat()


def create_order(variants: list, base_delay: int = 4, max_delay: int = 300) -> dict:
    """Create one order, waiting out the order-creation throttle with exponential backoff."""
    k = random.randint(1, 5)
    chosen = random.sample(variants, k=min(k, len(variants)))
    line_items = [{"variantId": v["id"], "quantity": random.randint(1, 3)} for v in chosen]

    variables = {
        "order": {
            "lineItems": line_items,
            "financialStatus": "PAID",
            "processedAt": random_processed_at(),
            "tags": [f"source:{random.choice(['meta', 'google', 'organic', 'direct'])}", "synthetic"],
        },
        "options": {"inventoryBehaviour": "BYPASS"},
    }

    delay = base_delay
    while True:
        result = extract_data(CREATE_ORDER, variables=variables)
        user_errors = result["data"]["orderCreate"]["userErrors"]
        if not user_errors:
            return result                                    # success
        if "Too many attempts" in str(user_errors):
            log_message("Throttled — waiting it out", stage="generate", level="INFO", wait_seconds=delay)
            time.sleep(delay)
            delay = min(delay * 2, max_delay)                # back off: 4, 8, 16... capped at 5 min
            continue
        raise RuntimeError(f"orderCreate failed: {user_errors}")   # a real error — don't loop forever


def respect_rate_limit(result: dict, floor: int = 300) -> None:
    """If the GraphQL query-cost bucket is running low, wait for it to refill."""
    throttle = result.get("extensions", {}).get("cost", {}).get("throttleStatus", {})
    available = throttle.get("currentlyAvailable", 1000)
    restore = throttle.get("restoreRate", 100)
    if available < floor:
        wait = (floor - available) / restore
        log_message("Throttling — letting the bucket refill", stage="generate",
                    level="INFO", available=available, wait_seconds=round(wait, 2))
        time.sleep(wait)


def generate_orders(n: int = 1000) -> None:
    """Generate `n` synthetic orders in the store."""
    variants = get_variant_pool()
    if not variants:
        raise RuntimeError("No product variants found — add products to the store first.")

    created = 0
    for i in range(n):
        try:
            result = create_order(variants)
        except Exception as e:
            log_message("Failed to create order — skipping", stage="generate", level="ERROR", error=str(e))
            continue
        created += 1
        respect_rate_limit(result)
        if created % 25 == 0:
            log_message("Progress", stage="generate", level="INFO", created=created, target=n)
        time.sleep(BASE_PACE)

    log_message("Order generation complete", stage="generate", level="INFO", total=created)


if __name__ == "__main__":
    # Sanity-check with a small number first (change to 5), then run the full batch overnight.
    generate_orders(n=10)
