from decimal import Decimal

import pytest

pytest.importorskip("pyspark")
from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructField, StructType

from spark.jobs.bronze_binance import read_raw, transform_raw_to_bronze

RAW_SCHEMA = StructType(
    [
        StructField("symbol", StringType(), nullable=True),
        StructField("price", StringType(), nullable=True),
        StructField("_corrupt_record", StringType(), nullable=True),
        StructField("raw_file_path", StringType(), nullable=False),
    ]
)


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    session = SparkSession.builder.master("local[1]").appName("bronze-tests").getOrCreate()
    yield session
    session.stop()


def raw_path(date: str, symbol: str = "BTCUSDT") -> str:
    return f"s3a://lake/raw/source=binance/symbol={symbol}/ingest_date={date}/price.json"


def test_valid_raw_record_is_transformed_to_bronze(spark: SparkSession) -> None:
    raw = spark.createDataFrame(
        [("btcusdt", "118000.12000000", None, raw_path("2026-07-28"))],
        RAW_SCHEMA,
    )

    bronze, quarantine = transform_raw_to_bronze(raw)
    record = bronze.collect()[0]

    assert bronze.count() == 1
    assert quarantine.count() == 0
    assert record.source == "binance"
    assert record.symbol == "BTCUSDT"
    assert record.price == Decimal("118000.12000000")


def test_invalid_price_is_sent_to_quarantine(spark: SparkSession) -> None:
    raw = spark.createDataFrame(
        [("BTCUSDT", "not-a-price", None, raw_path("2026-07-28"))],
        RAW_SCHEMA,
    )

    bronze, quarantine = transform_raw_to_bronze(raw)

    assert bronze.count() == 0
    assert quarantine.collect()[0].quarantine_reason == "price_not_decimal"


def test_duplicate_raw_file_creates_one_bronze_record(spark: SparkSession) -> None:
    record = ("BTCUSDT", "118000.12000000", None, raw_path("2026-07-28"))
    raw = spark.createDataFrame([record, record], RAW_SCHEMA)

    bronze, _ = transform_raw_to_bronze(raw)

    assert bronze.count() == 1


def test_symbol_partition_mismatch_is_rejected(spark: SparkSession) -> None:
    raw = spark.createDataFrame(
        [("ETHUSDT", "3000.00000000", None, raw_path("2026-07-28", symbol="BTCUSDT"))],
        RAW_SCHEMA,
    )

    bronze, quarantine = transform_raw_to_bronze(raw)

    assert bronze.count() == 0
    assert quarantine.collect()[0].quarantine_reason == "symbol_partition_mismatch"


def test_json_symbol_is_not_replaced_by_partition_column(spark, tmp_path):
    directory = tmp_path / "source=binance" / "symbol=BTCUSDT" / "ingest_date=2026-07-28"
    directory.mkdir(parents=True)
    (directory / "price.json").write_text('{"symbol":"ETHUSDT","price":"3000"}')
    raw = read_raw(spark, str(tmp_path))
    assert raw.select("symbol").first().symbol == "ETHUSDT"
    bronze, quarantine = transform_raw_to_bronze(raw)
    assert bronze.count() == 0
    assert quarantine.first().quarantine_reason == "symbol_partition_mismatch"
