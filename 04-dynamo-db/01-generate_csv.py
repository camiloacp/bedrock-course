import csv
import random
from datetime import datetime, timedelta

random.seed(42)

categories = ["Electronics", "Clothing", "Home & Kitchen", "Sports", "Books", "Toys", "Beauty", "Automotive"]
departments = ["Men", "Women", "Kids", "Unisex", "Home", "Outdoor"]
brands = ["Nike", "Adidas", "Apple", "Samsung", "Sony", "Zara", "H&M", "Under Armour", "Levis", "Puma"]

product_templates = {
    "Electronics": [("Wireless Earbuds", "Apple"), ("Smart Watch", "Samsung"), ("Bluetooth Speaker", "Sony"), ("Laptop Stand", "Generic"), ("USB-C Hub", "Generic")],
    "Clothing": [("T-Shirt", "Nike"), ("Jeans", "Levis"), ("Running Shoes", "Adidas"), ("Hoodie", "Under Armour"), ("Jacket", "Zara")],
    "Home & Kitchen": [("Blender", "Generic"), ("Coffee Maker", "Generic"), ("Knife Set", "Generic"), ("Air Fryer", "Generic"), ("Toaster", "Generic")],
    "Sports": [("Yoga Mat", "Puma"), ("Dumbbells", "Generic"), ("Soccer Ball", "Adidas"), ("Tennis Racket", "Generic"), ("Water Bottle", "Nike")],
    "Books": [("Fiction Novel", "Generic"), ("Cookbook", "Generic"), ("Sci-Fi Book", "Generic"), ("Self-Help Book", "Generic"), ("Biography", "Generic")],
    "Toys": [("LEGO Set", "Generic"), ("Board Game", "Generic"), ("Action Figure", "Generic"), ("Puzzle", "Generic"), ("Stuffed Animal", "Generic")],
    "Beauty": [("Face Cream", "Generic"), ("Shampoo", "Generic"), ("Perfume", "Generic"), ("Lipstick", "Generic"), ("Sunscreen", "Generic")],
    "Automotive": [("Car Charger", "Generic"), ("Floor Mats", "Generic"), ("Dash Cam", "Generic"), ("Air Freshener", "Generic"), ("Tire Inflator", "Generic")],
}

rows = []
base_date = datetime(2024, 1, 1)
for i in range(1, 501):
    category = random.choice(categories)
    template = random.choice(product_templates[category])
    name, brand = template
    if brand == "Generic":
        brand = random.choice(brands)
    
    created = base_date + timedelta(days=random.randint(0, 365))
    sold = created + timedelta(days=random.randint(1, 90)) if random.random() > 0.15 else None
    
    price = round(random.uniform(5.99, 299.99), 2)
    department = random.choice(departments)
    
    rows.append([
        f"PROD-{i:04d}",
        created.strftime("%Y-%m-%d %H:%M:%S"),
        sold.strftime("%Y-%m-%d %H:%M:%S") if sold else "",
        category,
        f"{name} {random.choice(['Pro', 'Plus', 'Lite', 'Max', 'X', ''])}".strip(),
        brand,
        price,
        department,
    ])

with open("/home/camilo/projects/bedrock-e2e/simulated_products.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["product_id", "created_at", "sold_at", "product_category", "product_name", "product_brand", "product_retail_price", "product_department"])
    writer.writerows(rows)

print("✅ Archivo generado: simulated_products.csv (200 filas)")