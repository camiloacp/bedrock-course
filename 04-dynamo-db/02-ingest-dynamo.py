from decimal import Decimal
from pathlib import Path
import uuid

import boto3
import pandas as pd


REGION = "us-east-1"
INVENTORY_TABLE = "product_inventory"
CSV_PATH = Path(__file__).resolve().parent / "simulated_products.csv"


def main():
    df_inventory = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)
    df_inventory.columns = [col.strip() for col in df_inventory.columns]

    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    inventory_table = dynamodb.Table(INVENTORY_TABLE)
    count = 0

    with inventory_table.batch_writer() as batch:
        for row in df_inventory.to_dict(orient="records"):
            created_at = row["created_at"]
            unique_suffix = str(uuid.uuid4())

            item = {
                "product_id": row["product_id"],
                "created_at_uuid": f"{created_at}#{unique_suffix}",
                "created_at": created_at,
                "product_category": row["product_category"],
                "product_name": row["product_name"],
                "product_brand": row["product_brand"],
                "product_retail_price": Decimal(row["product_retail_price"]),
                "product_department": row["product_department"],
            }

            if row["sold_at"].strip():
                item["sold_at"] = row["sold_at"]

            batch.put_item(Item=item)
            count += 1

    print(f"Ingesta completada: {count} registros en {INVENTORY_TABLE}.")


if __name__ == "__main__":
    main()
