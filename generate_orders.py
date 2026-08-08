"""
generate synthetic orders in the Shopify dev store.
Not part of the ETL pipeline.
this just seeds the store with realistic
orders (varied baskets, backdated across the past year, tagged with a
synthetic marketing source, and attached to customers) so there's enough
data to analyze and clean.

Each order is randomly attached EITHER to an existing customer (creating
repeat buyers) OR to a brand-new generated one. Newly created customers are
appended to the in-memory pool, so the set of possible repeat buyers grows
as the run goes on.

it backs off and waits out Shopify's order-creation throttle rather than giving up. Re-running ADDS more orders
(no dedup).
"""
from datetime import datetime, timedelta, timezone
import random
import time

from extract import extract_data
from logger import log_message

BASE_PACE = 11  # seconds between orders (steady pace so we don't keep re-tripping the limit)

# Simple name pools for generating brand-new customers (no external dependency).
FIRST_NAMES = ["Noa", "Ofek", "Maya", "Yossi", "Tamar", "Avi", "Dana", "Eitan", "Shira", "Amit", "Lior", "Roni"]
LAST_NAMES = ["Cohen", "Levi", "Mizrahi", "Peretz", "Biton", "Katz", "Friedman", "Azoulay", "Shani", "Barak"]

VARIANTS_QUERY = """
{
  productVariants(first: 100) {
    edges { node { id price product { title productType } } }
  }
}
"""

CUSTOMERS_QUERY = """
{
  customers(first: 100) {
    edges { node { id } }
  }
}
"""

CREATE_ORDER = """
mutation CreateOrder($order: OrderCreateOrderInput!, $options: OrderCreateOptionsInput) {
  orderCreate(order: $order, options: $options) {
    userErrors { field message }
    order { id name processedAt displayFinancialStatus customer { id } }
  }
}
"""


def get_variant_pool() -> list:
    """Fetch product variants to reference in generated orders."""
    result = extract_data(VARIANTS_QUERY)
    variants = [edge["node"] for edge in result["data"]["productVariants"]["edges"]]
    log_message("Fetched variant pool", stage="generate", level="INFO", count=len(variants))
    return variants


def get_customer_pool() -> list:
    """Fetch existing customer IDs to reuse across orders (creates repeat buyers).

    Returns an empty list if customers can't be read (e.g. missing scope /
    protected-data access) so the run can still proceed with new customers only.
    """
    try:
        result = extract_data(CUSTOMERS_QUERY)
        customers = [edge["node"]["id"] for edge in result["data"]["customers"]["edges"]]
    except Exception as e:
        log_message("Could not fetch customers — using new customers only",
                    stage="generate", level="ERROR", error=str(e))
        return []
    log_message("Fetched customer pool", stage="generate", level="INFO", count=len(customers))
    return customers


def random_customer(customer_ids: list) -> dict:
    """Randomly reuse an existing customer OR create a brand-new one."""
    # ~60% reuse an existing customer (repeat buyers), ~40% brand-new customer
    if customer_ids and random.random() < 0.6:
        return {"toAssociate": {"id": random.choice(customer_ids)}}
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    email = f"{first.lower()}.{last.lower()}{random.randint(1, 9999)}@example.com"
    return {"toUpsert": {"firstName": first, "lastName": last, "email": email}}


def random_processed_at(days_back: int = 365) -> str:
    """A random ISO-8601 timestamp within the past `days_back` days (UTC)."""
    offset = timedelta(days=random.randint(0, days_back), seconds=random.randint(0, 86400))
    return (datetime.now(timezone.utc) - offset).isoformat()


def create_order(variants: list, customer_ids: list, base_delay: int = 4, max_delay: int = 300) -> dict:
    """Create one order, waiting out the order-creation throttle with exponential backoff."""
    k = random.randint(1, 5)
    chosen = random.sample(variants, k=min(k, len(variants)))
    line_items = [{"variantId": v["id"], "quantity": random.randint(1, 3)} for v in chosen]

    variables = {
        "order": {
            "lineItems": line_items,
            "customer": random_customer(customer_ids),
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
    customer_ids = get_customer_pool()

    created = 0
    for i in range(n):
        try:
            result = create_order(variants, customer_ids)
        except Exception as e:
            log_message("Failed to create order — skipping", stage="generate", level="ERROR", error=str(e))
            continue
        created += 1

        # Grow the pool: if this order created a brand-new customer, add them
        # so they can become a repeat buyer in later orders.
        customer = result["data"]["orderCreate"]["order"].get("customer")
        if customer and customer["id"] not in customer_ids:
            customer_ids.append(customer["id"])

        respect_rate_limit(result)
        if created % 25 == 0:
            log_message("Progress", stage="generate", level="INFO",
                        created=created, target=n, pool_size=len(customer_ids))
        time.sleep(BASE_PACE)

    log_message("Order generation complete", stage="generate", level="INFO",
                total=created, final_pool_size=len(customer_ids))


if __name__ == "__main__":
    # Sanity-check with a small number first (change to 5), then run the full batch overnight.
    generate_orders(n=20)