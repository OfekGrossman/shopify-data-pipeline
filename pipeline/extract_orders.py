""" 
Extract all orders into data/bronze/orders/.

Query fields explained:
- id, name: order identity
- createdAt: when Shopify recorded the order.
- processedAt: the backdated order date (the order date for the analysis)
- displayFinancialStatus: the payment status, e.g. PAID.
- tags: includes the source, e.g meta.
- totalPriceSet.shopMoney: order value + currency.
- customer { id }: link to the customer (for joins / customer analysis).
- lineItems: the basket: each line's title, quantity, and its product { id title productType } (product id + category signal).
 """
from extract import extract_to_bronze

# Assumes no order has more than 50 item lines.

ORDERS_QUERY = """
query GetOrders($cursor: String) {
  orders(first: 100, after: $cursor) {
    edges {
      node {
        id
        name
        createdAt
        processedAt
        displayFinancialStatus
        tags
        totalPriceSet { shopMoney { amount currencyCode } }
        customer { id }
        lineItems(first: 50) {
          edges {
            node {
              title
              quantity
              product { id title productType }
            }
          }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

if __name__ == "__main__":
    extract_to_bronze("orders", ORDERS_QUERY, "orders")

