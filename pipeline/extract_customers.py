"""
Extract all customers into data/bronze/customers/.
Reading customer fields may require "Protected customer data" access
on the app.
"""
from extract import extract_to_bronze

CUSTOMERS_QUERY = """
query GetCustomers($cursor: String) {
  customers(first: 100, after: $cursor) {
    edges {
      node {
        id
        createdAt
        numberOfOrders
        defaultAddress {
          city
          country
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

if __name__ == "__main__":
    extract_to_bronze("customers", CUSTOMERS_QUERY, "customers")
