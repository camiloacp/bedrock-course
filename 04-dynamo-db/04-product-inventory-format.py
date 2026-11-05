import os
import json

import boto3


# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
PRODUCT_TABLE = os.environ.get("PRODUCT_TABLE", "product_inventory")
product_tbl = dynamodb.Table(PRODUCT_TABLE)


def _get_params(event):
    """
    Bedrock Agent sends parameters as a list: [{"name": ..., "value": ...}].
    For POST actions they may be under requestBody. Falls back to top-level keys
    so the function can still be tested with a plain JSON event.
    """
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    props = (
        event.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("properties", [])
    )
    params.update({p["name"]: p["value"] for p in props})

    for key in ("product_department", "product_brand", "product_category"):
        if key not in params and event.get(key):
            params[key] = event[key]
    return params


def lambda_handler(event, context):
    """
    Expected parameters (all optional, at least one required):
        product_department, product_brand, product_category
    """
    params = _get_params(event)

    # Normalize inputs to lowercase
    department = (params.get("product_department") or "").lower() or None
    brand = (params.get("product_brand") or "").lower() or None
    category = (params.get("product_category") or "").lower() or None

    status_code = 200

    if not (department or brand or category):
        status_code = 400
        result = {
            "error": "At least one of product_department, product_brand, or product_category is required"
        }
    else:
        try:
            response = product_tbl.scan()
            items = response.get("Items", [])

            # Apply case-insensitive filtering in Python
            matched = []
            for item in items:
                if (
                    (not department or item.get("product_department", "").lower() == department)
                    and (not brand or item.get("product_brand", "").lower() == brand)
                    and (not category or item.get("product_category", "").lower() == category)
                ):
                    matched.append({
                        "product_name": item.get("product_name"),
                        "product_retail_price": float(item.get("product_retail_price", 0)),
                    })

            result = {"matched_products": matched}
        except Exception as e:
            status_code = 500
            result = {"error": str(e)}

    # Wrap in Bedrock Agent format
    response_body = {
        "application/json": {
            "body": json.dumps(result)
        }
    }
    action_response = {
        "actionGroup": event.get("actionGroup"),
        "apiPath": event.get("apiPath"),
        "httpMethod": event.get("httpMethod"),
        "httpStatusCode": status_code,
        "responseBody": response_body,
    }
    api_response = {
        "messageVersion": "1.0",
        "response": action_response,
        "sessionAttributes": event.get("sessionAttributes", {}),
        "promptSessionAttributes": event.get("promptSessionAttributes", {}),
    }

    return api_response
