from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256

import pytest

pyspark = pytest.importorskip("pyspark")
from pyspark.sql import SparkSession
from pyspark.sql.types import (  # noqa: E402
    DateType,
    DecimalType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from spark.jobs.bronze_to_silver import transform_bronze_to_silver

BRONZE_SCHEMA = StructType(
    [
        StructField("source", StringType(), nullable=False),
        StructField("symbol", StringType(), nullable=True),
        StructField("price", DecimalType(20, 8), nullable=True),
        StructField("ingest_date", DateType(), nullable=True),
        StructField("bronze_loaded_at", TimestampType(), nullable=True),
        StructField("raw_file_path", StringType(), nullable=True),
    ]
)


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    session = SparkSession.builder.master("local[1]").appName("silver-tests").getOrCreate()
    yield session
    session.stop()


def test_valid_bronze_record_is_transformed_to_silver(spark: SparkSession) -> None:
    bronze = spark.createDataFrame(
        [
            (
                "BINANCE",
                "btcusdt",
                Decimal("118000.12000000"),
                date(2026, 7, 28),
                datetime(2026, 7, 28, 8, 0, 0),
                "s3a://lake/raw/source=binance/file.json",
            )
        ],
        BRONZE_SCHEMA,
    )

    silver, quarantine = transform_bronze_to_silver(bronze)
    record = silver.collect()[0]

    assert silver.count() == 1
    assert quarantine.count() == 0
    assert record.source == "binance"
    assert record.symbol == "BTCUSDT"
    assert record.price == Decimal("118000.12000000")
    assert record.record_id == sha256(
        b"s3a://lake/raw/source=binance/file.json"
    ).hexdigest()


def test_invalid_price_is_rejected_from_silver(spark: SparkSession) -> None:
    bronze = spark.createDataFrame(
        [
            (
                "binance",
                "BTCUSDT",
                Decimal("-1.00000000"),
                date(2026, 7, 28),
                datetime(2026, 7, 28, 8, 0, 0),
                "s3a://lake/raw/source=binance/invalid-price.json",
            )
        ],
        BRONZE_SCHEMA,
    )

    silver, quarantine = transform_bronze_to_silver(bronze)

    assert silver.count() == 0
    assert quarantine.collect()[0].quarantine_reason == "price_not_positive"


def test_duplicate_raw_file_produces_one_silver_record(spark: SparkSession) -> None:
    record = (
        "binance",
        "BTCUSDT",
        Decimal("118000.12000000"),
        date(2026, 7, 28),
        datetime(2026, 7, 28, 8, 0, 0),
        "s3a://lake/raw/source=binance/duplicate.json",
    )
    bronze = spark.createDataFrame([record, record], BRONZE_SCHEMA)

    silver, _ = transform_bronze_to_silver(bronze)

    assert silver.count() == 1


def test_silver_schema_is_the_canonical_contract(spark: SparkSession) -> None:
    bronze = spark.createDataFrame(
        [
            (
                "binance",
                "BTCUSDT",
                Decimal("118000.12000000"),
                date(2026, 7, 28),
                datetime(2026, 7, 28, 8, 0, 0),
                "s3a://lake/raw/source=binance/schema.json",
            )
        ],
        BRONZE_SCHEMA,
    )

    silver, _ = transform_bronze_to_silver(bronze)

    assert [(field.name, field.dataType.simpleString()) for field in silver.schema] == [
        ("record_id", "string"),
        ("source", "string"),
        ("symbol", "string"),
        ("price", "decimal(20,8)"),
        ("ingest_date", "date"),
        ("bronze_loaded_at", "timestamp"),
        ("silver_loaded_at", "timestamp"),
    ]
