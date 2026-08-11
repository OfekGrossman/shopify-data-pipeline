"""Extract all products into data/bronze/products/."""
from extract import extract_to_bronze

PRODUCTS_QUERY = """
query GetProducts($cursor: String) {
  products(first: 100, after: $cursor) {
    edges {
      node {
        id
        title
        productType
        vendor
        tags
        status
        createdAt
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

if __name__ == "__main__":
    extract_to_bronze("products", PRODUCTS_QUERY, "products")
