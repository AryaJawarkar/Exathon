"""Central configuration loaded from environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    dsn: str = os.getenv("EXA_DSN", "localhost:8563")
    user: str = os.getenv("EXA_USER", "sys")
    password: str = os.getenv("EXA_PASSWORD", "exasol")
    schema: str = os.getenv("EXA_SCHEMA", "OMNI")

    seed: int = int(os.getenv("SEED", "42"))
    n_customers: int = int(os.getenv("N_CUSTOMERS", "3000"))
    n_products: int = int(os.getenv("N_PRODUCTS", "250"))
    n_days: int = int(os.getenv("N_DAYS", "540"))


settings = Settings()
