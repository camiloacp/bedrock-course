import os

import boto3
from strands import tool

REGION = os.environ.get("AWS_REGION", "us-east-1")
PRODUCT_TABLE = os.environ.get("PRODUCT_TABLE", "product_inventory")
KB_ID = os.environ.get("KB_ID", "EO63UA46EA")
MAX_RESULTS = 25

_table = boto3.resource("dynamodb", region_name=REGION).Table(PRODUCT_TABLE)
_kb_client = boto3.client("bedrock-agent-runtime", region_name=REGION)


def _scan_all():
    """Scan the whole table following pagination (a single scan reads max 1 MB)."""
    kwargs = {}
    while True:
        resp = _table.scan(**kwargs)
        yield from resp.get("Items", [])
        if "LastEvaluatedKey" not in resp:
            return
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


@tool
def search_products(
    product_department: str = "",
    product_brand: str = "",
    product_category: str = "",
) -> dict:
    """Search the product inventory by department, brand and/or category.

    Use this for questions like "which Nike products do we have" or "show me
    electronics in the Home department". At least one filter is required.
    Matching is case-insensitive and exact. Returns product names and retail prices.

    Args:
        product_department: Department name, e.g. "Home". Optional.
        product_brand: Brand name, e.g. "Sony". Optional.
        product_category: Category name, e.g. "Electronics". Optional.
    """
    department = product_department.strip().lower()
    brand = product_brand.strip().lower()
    category = product_category.strip().lower()

    if not (department or brand or category):
        return {"error": "Provide at least one of product_department, product_brand or product_category"}

    matched = []
    for item in _scan_all():
        if (
            (not department or item.get("product_department", "").lower() == department)
            and (not brand or item.get("product_brand", "").lower() == brand)
            and (not category or item.get("product_category", "").lower() == category)
        ):
            matched.append({
                "product_name": item.get("product_name"),
                "product_retail_price": float(item.get("product_retail_price", 0)),
            })

    return {
        "total_matches": len(matched),
        "matched_products": matched[:MAX_RESULTS],
        "truncated": len(matched) > MAX_RESULTS,
    }


@tool
def search_catalog(question: str) -> dict:
    """Search the product knowledge base for descriptions and general product information.

    Use this for questions about what a product is, its features, or details of
    the catalog that are not just prices or availability by brand/category.

    Args:
        question: Natural language question or search text.
    """
    if not question.strip():
        return {"error": "question is required"}

    resp = _kb_client.retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 5}},
    )
    return {
        "results": [
            {"text": r["content"]["text"], "score": r.get("score")}
            for r in resp.get("retrievalResults", [])
        ]
    }
