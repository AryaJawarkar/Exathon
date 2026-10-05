"""Generate SYNTHETIC omnichannel retail data — deliberately fragmented.

To make the "sales fragmentation" problem real, we emit three raw feeds that
look the way they would in a real retailer: different column names, different
date formats, different revenue conventions. The ETL step is what reconciles
them. No real or proprietary data is used (contest rule).

    python -m src.data.generate_synthetic_data

Writes to data/raw/:
    customers.csv
    products.csv
    online_orders.csv        (JSON-ish flat, 'amount' already net)
    store_receipts.csv        (POS style, price + qty, no revenue column)
    marketplace_settlements.csv (marketplace fee baked in, gross vs net)
"""
from __future__ import annotations

import csv
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

from ..config import settings

RAW = Path("data/raw")
CATEGORIES = [
    "Apparel", "Electronics", "Home", "Beauty", "Grocery",
    "Sports", "Toys", "Books", "Footwear", "Accessories",
]


def _daterange_weights(n_days: int) -> list[float]:
    """Seasonality: weekly cycle + a gentle upward trend + festive bumps."""
    weights = []
    for d in range(n_days):
        day = d
        weekly = 1.0 + 0.35 * (1 if (day % 7) in (5, 6) else 0)   # weekends
        trend = 1.0 + 0.0008 * day                                # slow growth
        festive = 1.6 if (n_days - day) in range(20, 35) else 1.0 # sale season
        weights.append(weekly * trend * festive)
    return weights


def generate() -> None:
    fake = Faker("en_IN")
    Faker.seed(settings.seed)
    random.seed(settings.seed)
    RAW.mkdir(parents=True, exist_ok=True)

    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=settings.n_days
    )

    # ---- customers -------------------------------------------------------
    customers = []
    for cid in range(1, settings.n_customers + 1):
        signup_offset = random.randint(0, settings.n_days)
        customers.append(
            {
                "customer_id": cid,
                "full_name": fake.name(),
                "city": fake.city(),
                "signup_date": (start + timedelta(days=signup_offset)).date().isoformat(),
                # latent loyalty drives purchase frequency (hidden from the model)
                "_loyalty": random.betavariate(2, 5),
            }
        )
    _write(RAW / "customers.csv", customers, drop=["_loyalty"])

    # ---- products --------------------------------------------------------
    products = []
    for pid in range(1, settings.n_products + 1):
        cat = random.choice(CATEGORIES)
        price = round(random.uniform(99, 8999), 2)
        products.append(
            {
                "product_id": pid,
                "product_name": f"{cat} Item {pid}",
                "category": cat,
                "list_price": price,
                "_popularity": random.paretovariate(1.3),
            }
        )
    _write(RAW / "products.csv", products, drop=["_popularity"])

    prod_weights = [p["_popularity"] for p in products]
    day_weights = _daterange_weights(settings.n_days)

    online, store, market = [], [], []
    order_seq = 0
    for cust in customers:
        # expected lifetime orders ~ loyalty; some customers churn midway
        n_orders = int(random.expovariate(1 / (3 + cust["_loyalty"] * 25)))
        active_until = settings.n_days if cust["_loyalty"] > 0.25 else random.randint(
            30, settings.n_days
        )
        for _ in range(n_orders):
            day = random.choices(range(settings.n_days), weights=day_weights, k=1)[0]
            if day > active_until:
                continue
            ts = start + timedelta(
                days=day, hours=random.randint(8, 22), minutes=random.randint(0, 59)
            )
            channel = random.choices(
                ["ONLINE", "STORE", "MARKETPLACE"], weights=[0.45, 0.35, 0.20]
            )[0]
            order_seq += 1
            n_lines = random.randint(1, 4)
            for _ in range(n_lines):
                prod = random.choices(products, weights=prod_weights, k=1)[0]
                qty = random.randint(1, 3)
                unit = round(prod["list_price"] * random.uniform(0.85, 1.0), 2)
                row = _emit(channel, order_seq, cust, prod, qty, unit, ts)
                {"ONLINE": online, "STORE": store, "MARKETPLACE": market}[channel].append(row)

    _write(RAW / "online_orders.csv", online)
    _write(RAW / "store_receipts.csv", store)
    _write(RAW / "marketplace_settlements.csv", market)

    print(
        f"Generated: {len(customers)} customers, {len(products)} products, "
        f"{len(online)} online / {len(store)} store / {len(market)} marketplace lines."
    )


def _emit(channel, order_id, cust, prod, qty, unit, ts) -> dict:
    """Each channel has its OWN schema — this is the fragmentation we unify later."""
    if channel == "ONLINE":
        return {
            "order_ref": f"W{order_id}",
            "cust_id": cust["customer_id"],
            "sku": prod["product_id"],
            "units": qty,
            "unit_amount": unit,
            "net_amount": round(qty * unit, 2),
            "placed_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
        }
    if channel == "STORE":
        return {  # POS: no revenue column, Indian date format
            "receipt_no": f"S{order_id}",
            "member_id": cust["customer_id"],
            "item_code": prod["product_id"],
            "qty": qty,
            "price": unit,
            "txn_time": ts.strftime("%d-%m-%Y %H:%M"),
        }
    return {  # MARKETPLACE: gross with fee, needs net derivation
        "mp_order_id": f"M{order_id}",
        "buyer_id": cust["customer_id"],
        "product_id": prod["product_id"],
        "quantity": qty,
        "sale_price": unit,
        "gross_value": round(qty * unit, 2),
        "mp_fee": round(qty * unit * 0.12, 2),
        "settlement_date": ts.strftime("%Y/%m/%d %H:%M:%S"),
    }


def _write(path: Path, rows: list[dict], drop: list[str] | None = None) -> None:
    drop = drop or []
    rows = [{k: v for k, v in r.items() if k not in drop} for r in rows]
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    generate()
