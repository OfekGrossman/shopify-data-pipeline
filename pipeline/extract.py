"""Shopify GraphQL extractor."""
import requests
from config import SHOPIFY_SHOP_URL, SHOPIFY_ACCESS_TOKEN, SHOPIFY_API_VERSION, BRONZE_DIR
from logger import log_message
import json
from datetime import date


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

def extract_to_bronze(name: str, query: str, root_key: str) -> list:
    """
      Paginate a GraphQL connection and write every node to bronze as JSONL.

      Args:
          name:     folder/file name for this entity, e.g. "orders"
          query:    a GraphQL query that takes a $cursor variable and includes
                    pageInfo { hasNextPage endCursor } on the connection
          root_key: the connection field name in the response, e.g. "orders"

      Returns the full list of node dicts that were saved.
    """

    all_nodes = []
    cursor = None
    page = 0

    # Fetch data
    while True:
      page += 1
      result = extract_data(query, variables={"cursor": cursor})
      connection = result["data"][root_key]
      nodes = [edge["node"] for edge in connection["edges"]]
      all_nodes.extend(nodes)
      log_message("Fetched page", stage="bronze", level="INFO",
                  entity=name, page=page, page_records=len(nodes),
                  running_total=len(all_nodes))
      page_info = connection["pageInfo"]
      if not page_info["hasNextPage"]:
        break
      cursor = page_info["endCursor"]

    # Write data to bronze target
    target_dir = BRONZE_DIR / name
    # Create dir only if dir does not exists.
    target_dir.mkdir(parents=True, exist_ok=True)
    # Target path in format name_YYYY_MM_DD.jsonl
    target_path = target_dir / f"{name}_{date.today().isoformat()}.jsonl"
    with open(target_path, "w", encoding="utf-8") as f:
        for node in all_nodes:
            f.write(json.dumps(node, ensure_ascii=False) + "\n")
    log_message("Wrote bronze file", stage="bronze", level="INFO",
                entity=name, path=str(target_path), records=len(all_nodes)) 
    return all_nodes       


if __name__ == "__main__":
    # Test the extract_data function
    QUERY = """
    {
      shop { name }
    }
    """
    result = extract_data(QUERY)
    print(result)
