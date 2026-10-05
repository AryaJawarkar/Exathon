"""Offline smoke tests — no Exasol required.

Exercises the parts that don't need a live DB: synthetic data generation, the
per-channel normalisers that unify the fragmented feeds, and the forecasting
model. Run: `python -m tests.smoke` (or `make smoke`).
"""
from __future__ import annotations

import os
import sys

# small & fast
os.environ.setdefault("N_CUSTOMERS", "150")
os.environ.setdefault("N_PRODUCTS", "40")
os.environ.setdefault("N_DAYS", "120")

import pandas as pd  # noqa: E402

from src.data.generate_synthetic_data import generate  # noqa: E402
from src.etl.load import (  # noqa: E402
    _normalise_marketplace,
    _normalise_online,
    _normalise_store,
)

EXPECTED_COLS = {
    "ORDER_ID", "CUSTOMER_ID", "PRODUCT_ID", "CHANNEL",
    "ORDER_TS", "QUANTITY", "UNIT_PRICE", "LINE_REVENUE",
}


def test_generate_and_unify() -> None:
    generate()
    frames = [_normalise_online(), _normalise_store(), _normalise_marketplace()]
    for f in frames:
        assert EXPECTED_COLS.issubset(f.columns), f"missing cols: {EXPECTED_COLS - set(f.columns)}"
        assert len(f) > 0, "empty channel frame"
        assert (f["LINE_REVENUE"] >= 0).all(), "negative revenue"
    unified = pd.concat(frames, ignore_index=True)
    assert set(unified["CHANNEL"].unique()) == {"ONLINE", "STORE", "MARKETPLACE"}
    print(f"  unify: {len(unified)} rows across 3 channels  OK")


def test_forecast_model() -> None:
    from src.analytics.forecasting import forecast_series

    dates = pd.date_range("2025-01-01", periods=90, freq="D")
    demand = pd.DataFrame({"ORDER_DATE": dates, "UNITS": range(10, 100), "SERIES": "X"})
    out = forecast_series(demand, horizon=14)
    fc = out[out.KIND == "forecast"]
    assert len(fc) == 14, "wrong horizon length"
    assert (fc["UNITS"] >= 0).all(), "negative forecast"
    assert (fc["UPPER"] >= fc["LOWER"]).all(), "band inverted"
    print(f"  forecast: 14-day horizon, total={fc.UNITS.sum():.0f}  OK")


def main() -> int:
    tests = [test_generate_and_unify, test_forecast_model]
    failed = 0
    for t in tests:
        try:
            print(f"- {t.__name__}")
            t()
        except AssertionError as exc:  # noqa: PERF203
            print(f"  FAIL: {exc}")
            failed += 1
    print("\n" + ("ALL PASSED" if not failed else f"{failed} FAILED"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
