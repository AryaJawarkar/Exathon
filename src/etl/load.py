"""ETL: create the schema, then UNIFY the three fragmented channel feeds.

    python -m src.etl.load

Steps:
  1. Run src/sql/schema.sql (idempotent CREATE OR REPLACE).
  2. Load DIM_CUSTOMER / DIM_PRODUCT.
  3. Normalise online_orders + store_receipts + marketplace_settlements into
     the common FACT_SALES grain and bulk-import.

This is the reconciliation layer that the rest of the project gets to ignore.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import settings
from ..db import session

RAW = Path("data/raw")
SCHEMA_SQL = Path("src/sql/schema.sql")


def _run_schema(conn) -> None:
    stmts = [s.strip() for s in SCHEMA_SQL.read_text().split(";") if s.strip()]
    for stmt in stmts:
        conn.execute(stmt)


def _load_dims(conn) -> None:
    customers = pd.read_csv(RAW / "customers.csv")
    customers["signup_date"] = pd.to_datetime(customers["signup_date"]).dt.date
    conn.import_from_pandas(
        customers[["customer_id", "full_name", "city", "signup_date"]],
        (settings.schema, "DIM_CUSTOMER"),
    )

    products = pd.read_csv(RAW / "products.csv")
    conn.import_from_pandas(
        products[["product_id", "product_name", "category", "list_price"]],
        (settings.schema, "DIM_PRODUCT"),
    )


def _normalise_online() -> pd.DataFrame:
    df = pd.read_csv(RAW / "online_orders.csv")
    return pd.DataFrame(
        {
            "ORDER_ID": df["order_ref"].str.lstrip("W").astype("int64"),
            "CUSTOMER_ID": df["cust_id"],
            "PRODUCT_ID": df["sku"],
            "CHANNEL": "ONLINE",
            "ORDER_TS": pd.to_datetime(df["placed_at"], format="%Y-%m-%d %H:%M:%S"),
            "QUANTITY": df["units"],
            "UNIT_PRICE": df["unit_amount"],
            "LINE_REVENUE": df["net_amount"],
        }
    )


def _normalise_store() -> pd.DataFrame:
    df = pd.read_csv(RAW / "store_receipts.csv")
    return pd.DataFrame(
        {
            "ORDER_ID": df["receipt_no"].str.lstrip("S").astype("int64"),
            "CUSTOMER_ID": df["member_id"],
            "PRODUCT_ID": df["item_code"],
            "CHANNEL": "STORE",
            "ORDER_TS": pd.to_datetime(df["txn_time"], format="%d-%m-%Y %H:%M"),
            "QUANTITY": df["qty"],
            "UNIT_PRICE": df["price"],
            "LINE_REVENUE": (df["qty"] * df["price"]).round(2),  # derived
        }
    )


def _normalise_marketplace() -> pd.DataFrame:
    df = pd.read_csv(RAW / "marketplace_settlements.csv")
    return pd.DataFrame(
        {
            "ORDER_ID": df["mp_order_id"].str.lstrip("M").astype("int64"),
            "CUSTOMER_ID": df["buyer_id"],
            "PRODUCT_ID": df["product_id"],
            "CHANNEL": "MARKETPLACE",
            "ORDER_TS": pd.to_datetime(df["settlement_date"], format="%Y/%m/%d %H:%M:%S"),
            "QUANTITY": df["quantity"],
            "UNIT_PRICE": df["sale_price"],
            "LINE_REVENUE": (df["gross_value"] - df["mp_fee"]).round(2),  # net of fee
        }
    )


def _load_facts(conn) -> int:
    frames = [_normalise_online(), _normalise_store(), _normalise_marketplace()]
    fact = pd.concat(frames, ignore_index=True)
    fact.insert(0, "SALE_ID", range(1, len(fact) + 1))
    fact["ORDER_DATE"] = fact["ORDER_TS"].dt.date
    cols = [
        "SALE_ID", "ORDER_ID", "CUSTOMER_ID", "PRODUCT_ID", "CHANNEL",
        "ORDER_TS", "ORDER_DATE", "QUANTITY", "UNIT_PRICE", "LINE_REVENUE",
    ]
    conn.import_from_pandas(fact[cols], (settings.schema, "FACT_SALES"))
    return len(fact)


def main() -> None:
    with session(schema=None) as conn:
        print("Creating schema...")
        _run_schema(conn)
        conn.open_schema(settings.schema)
        print("Loading dimensions...")
        _load_dims(conn)
        print("Unifying channels into FACT_SALES...")
        n = _load_facts(conn)
        total = conn.execute(
            f"SELECT COUNT(*), ROUND(SUM(LINE_REVENUE),0) FROM {settings.schema}.FACT_SALES"
        ).fetchone()
        print(f"Loaded {n} fact rows. In-DB count={total[0]}, revenue={total[1]}.")


if __name__ == "__main__":
    main()
