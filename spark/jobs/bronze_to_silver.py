"""Build the canonical Silver crypto-price table from Bronze Parquet."""

from __future__ import annotations

import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    concat_ws,
    current_timestamp,
    length,
    lit,
    lower,
    sha2,
    to_date,
    trim,
    upper,
    when,
)
from pyspark.sql.types import DecimalType

SILVER_PRICE_TYPE = DecimalType(20, 8)


def s3a_path(bucket: str, prefix: str) -> str:
    """Return an S3A URI, the Hadoop filesystem connector used by Spark."""
    return f"s3a://{bucket}/{prefix.strip('/')}"


def transform_bronze_to_silver(bronze: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Return valid Silver records and rejected Bronze records with quality reasons."""
    checked = (
        bronze.withColumn("source", lower(trim(col("source"))))
        .withColumn("symbol", upper(trim(col("symbol"))))
        .withColumn("price", col("price").cast(SILVER_PRICE_TYPE))
        .withColumn("ingest_date", to_date(col("ingest_date")))
        .withColumn("silver_loaded_at", current_timestamp())
        .withColumn(
            "quarantine_reason",
            concat_ws(
                "; ",
                when(col("source").isNull() | (length(col("source")) == 0), lit("missing_source")),
                when(col("symbol").isNull() | (length(col("symbol")) == 0), lit("missing_symbol")),
                when(~col("symbol").endswith("USDT"), lit("unsupported_symbol")),
                when(col("price").isNull(), lit("price_not_decimal")),
                when(col("price") <= 0, lit("price_not_positive")),
                when(col("ingest_date").isNull(), lit("invalid_ingest_date")),
                when(
                    col("raw_file_path").isNull() | (length(col("raw_file_path")) == 0),
                    lit("missing_raw_file_path"),
                ),
            ),
        )
    )

    invalid = checked.filter(length(col("quarantine_reason")) > 0)
    valid = checked.filter(length(col("quarantine_reason")) == 0)

    # The hash is a stable technical identifier for one landed Raw object. It
    # keeps the physical S3 path private while preserving record-level lineage.
    silver = valid.dropDuplicates(["raw_file_path"]).withColumn(
        "record_id", sha2(col("raw_file_path"), 256)
    ).select(
        "record_id",
        "source",
        "symbol",
        "price",
        "ingest_date",
        "bronze_loaded_at",
        "silver_loaded_at",
    )

    quarantine = invalid.select(
        "source",
        "symbol",
        "price",
        "ingest_date",
        "bronze_loaded_at",
        "raw_file_path",
        "quarantine_reason",
        "silver_loaded_at",
    )
    return silver, quarantine


def write_partitioned_parquet(dataframe: DataFrame, destination: str) -> None:
    """Overwrite only the partitions present in this deterministic batch."""
    if dataframe.isEmpty():
        return

    (
        dataframe.write.mode("overwrite")
        .option("partitionOverwriteMode", "dynamic")
        .partitionBy("source", "ingest_date")
        .parquet(destination)
    )


def main() -> None:
    bucket = os.environ["S3_BUCKET"]
    bronze_prefix = os.getenv("S3_BRONZE_PREFIX", "bronze")
    silver_prefix = os.getenv("S3_SILVER_PREFIX", "silver")
    quarantine_prefix = os.getenv("S3_QUARANTINE_PREFIX", "quarantine")

    spark = SparkSession.builder.appName("binance_bronze_to_silver").getOrCreate()
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    bronze = spark.read.parquet(s3a_path(bucket, f"{bronze_prefix}/crypto_prices"))
    silver, quarantine = transform_bronze_to_silver(bronze)

    write_partitioned_parquet(silver, s3a_path(bucket, f"{silver_prefix}/crypto_prices"))
    write_partitioned_parquet(
        quarantine,
        s3a_path(bucket, f"{quarantine_prefix}/silver_crypto_prices"),
    )

    print(f"Silver records written: {silver.count()}")
    print(f"Silver quarantine records written: {quarantine.count()}")
    spark.stop()


if __name__ == "__main__":
    main()
