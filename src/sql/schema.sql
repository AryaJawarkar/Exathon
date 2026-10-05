-- Unified omnichannel warehouse schema for Exasol Personal.
-- The whole point: three fragmented channel feeds (online, store, marketplace)
-- land in ONE conformed star schema so every downstream question is a single
-- query against FACT_SALES instead of a reconciliation project.

CREATE SCHEMA IF NOT EXISTS OMNI;
OPEN SCHEMA OMNI;

CREATE OR REPLACE TABLE DIM_CUSTOMER (
    CUSTOMER_ID   DECIMAL(18,0) NOT NULL,
    FULL_NAME     VARCHAR(120),
    CITY          VARCHAR(80),
    SIGNUP_DATE   DATE,
    PRIMARY KEY (CUSTOMER_ID)
);

CREATE OR REPLACE TABLE DIM_PRODUCT (
    PRODUCT_ID    DECIMAL(18,0) NOT NULL,
    PRODUCT_NAME  VARCHAR(160),
    CATEGORY      VARCHAR(80),
    LIST_PRICE    DECIMAL(12,2),
    PRIMARY KEY (PRODUCT_ID)
);

-- One grain: one line item of one order, tagged with the channel it came from.
CREATE OR REPLACE TABLE FACT_SALES (
    SALE_ID       DECIMAL(18,0) NOT NULL,
    ORDER_ID      DECIMAL(18,0) NOT NULL,
    CUSTOMER_ID   DECIMAL(18,0) NOT NULL,
    PRODUCT_ID    DECIMAL(18,0) NOT NULL,
    CHANNEL       VARCHAR(20)   NOT NULL,  -- ONLINE | STORE | MARKETPLACE
    ORDER_TS      TIMESTAMP     NOT NULL,
    ORDER_DATE    DATE          NOT NULL,
    QUANTITY      DECIMAL(10,0) NOT NULL,
    UNIT_PRICE    DECIMAL(12,2) NOT NULL,
    LINE_REVENUE  DECIMAL(14,2) NOT NULL,
    PRIMARY KEY (SALE_ID)
);
