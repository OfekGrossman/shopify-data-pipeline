"""Shopify GraphQL extractor — pulls raw data into the bronze layer."""
import requests
from config import SHOPIFY_SHOP_URL, SHOPIFY_ACCESS_TOKEN, SHOPIFY_API_VERSION
from logger import log_message

ENDPOINT = f"https://{SHOPIFY_SHOP_URL}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json",
}

def extract_data(query: str, variables: dict = None) -> dict:
    """
    Extracts data from the Shopify GraphQL API using the provided query and variables.

    Args:
        query (str): The GraphQL query string.
        variables (dict, optional): A dictionary of variables for the query. Default is None.

    Returns:
        dict: The JSON response from the Shopify API.

    """
    log_message("Sending GraphQL request to Shopify API", stage="extract", level="INFO")

    response = requests.post(
        ENDPOINT,
        headers=HEADERS,
        json={"query": query, "variables": variables or {}},
    )
    # Raise an error for bad responses
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        log_message("HTTP error from Shopify API", level="ERROR", stage="extract", status_code=response.status_code, body=response.text)
        raise   # re-raise the same error so it isn't silently swallowed
    data = response.json()
    if "errors" in data:
        log_message("GraphQL returned errors", errors =  data['errors'], stage="extract", level="ERROR")
        raise RuntimeError(f"GraphQL returned errors: {data['errors']}")
    log_message("GraphQL request successful", stage="extract", level="INFO")
    return data

if __name__ == "__main__":
    # Example usage of the extract_data function
    QUERY = """
    {
      orders(first: 10) {
        edges {
          node {
            id
            name
            createdAt
            displayFinancialStatus
            totalPriceSet { shopMoney { amount currencyCode } }
            lineItems(first: 20) {
              edges {
                node {
                  title
                  quantity
                  product { productType tags }
                }
              }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    result = extract_data(QUERY)
    print(result)
