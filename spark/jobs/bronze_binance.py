"""Build the Bronze crypto-price table from immutable Binance Raw JSON."""

from __future__ import annotations

import os

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    concat_ws,
    current_timestamp,
    input_file_name,
    length,
    lit,
    regexp_extract,
    to_date,
    trim,
    upper,
    when,
)
from pyspark.sql.types import DecimalType, StringType, StructField, StructType

RAW_SCHEMA = StructType(
    [
        StructField("symbol", StringType(), nullable=True),
        StructField("price", StringType(), nullable=True),
        StructField("_corrupt_record", StringType(), nullable=True),
    ]
)


def s3a_path(bucket: str, prefix: str) -> str:
    """Return an S3A URI, the Hadoop filesystem connector used by Spark."""
    return f"s3a://{bucket}/{prefix.strip('/')}"


def add_quality_columns(raw: DataFrame) -> DataFrame:
    """Parse Raw fields and attach partition values and data-quality reasons."""
    raw_with_path = raw
    if "raw_file_path" not in raw.columns:
        raw_with_path = raw.withColumn("raw_file_path", input_file_name())
    enriched = (
        raw_with_path
        .withColumn("source", regexp_extract("raw_file_path", r"/source=([^/]+)/", 1))
        .withColumn("partition_symbol", regexp_extract("raw_file_path", r"/symbol=([^/]+)/", 1))
        .withColumn("ingest_date", regexp_extract("raw_file_path", r"/ingest_date=([^/]+)/", 1))
        .withColumn("ingest_date_value", to_date(col("ingest_date"), "yyyy-MM-dd"))
        .withColumn("payload_symbol", upper(trim(col("symbol"))))
        .withColumn("price_raw", trim(col("price")))
        .withColumn("price", col("price_raw").cast(DecimalType(20, 8)))
        .withColumn("bronze_loaded_at", current_timestamp())
    )

    return enriched.withColumn(
        "quarantine_reason",
        concat_ws(
            "; ",
            when(col("_corrupt_record").isNotNull(), lit("malformed_json")),
            when(col("source") != "binance", lit("invalid_source_partition")),
            when(col("ingest_date_value").isNull(), lit("invalid_ingest_date")),
            when(
                col("payload_symbol").isNull() | (length(col("payload_symbol")) == 0),
                lit("missing_symbol"),
            ),
            when(~col("payload_symbol").endswith("USDT"), lit("unsupported_symbol")),
            when(col("payload_symbol") != upper(col("partition_symbol")),
                 lit("symbol_partition_mismatch")),
            when(col("price").isNull(), lit("price_not_decimal")),
            when(col("price") <= 0, lit("price_not_positive")),
        ),
    )


def transform_raw_to_bronze(raw: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Return valid Bronze records and rejected Raw records with quality reasons."""
    checked = add_quality_columns(raw)
    invalid = checked.filter(length(col("quarantine_reason")) > 0)
    valid = checked.filter(length(col("quarantine_reason")) == 0)

    bronze = (
        valid.select(
            "source",
            "ingest_date",
            col("payload_symbol").alias("symbol"),
            "price",
            "raw_file_path",
            "bronze_loaded_at",
        )
        .dropDuplicates(["raw_file_path"])
    )
    quarantine = invalid.select(
        "source",
        "ingest_date",
        "payload_symbol",
        "partition_symbol",
        "price_raw",
        "raw_file_path",
        "_corrupt_record",
        "quarantine_reason",
        "bronze_loaded_at",
    )
    return bronze, quarantine


def write_partitioned_parquet(dataframe: DataFrame, destination: str) -> None:
    """Overwrite only affected partitions, keeping a rerun idempotent for this project."""
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
    raw_prefix = os.getenv("S3_RAW_PREFIX", "raw")
    bronze_prefix = os.getenv("S3_BRONZE_PREFIX", "bronze")
    quarantine_prefix = os.getenv("S3_QUARANTINE_PREFIX", "quarantine")

    spark = SparkSession.builder.appName("binance_raw_to_bronze").getOrCreate()
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
    spark.conf.set("spark.sql.sources.partitionDiscovery.enabled", "false")

    raw = (
        spark.read.option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", "_corrupt_record")
        .schema(RAW_SCHEMA)
        .json(s3a_path(bucket, raw_prefix))
    )
    bronze, quarantine = transform_raw_to_bronze(raw)

    write_partitioned_parquet(bronze, s3a_path(bucket, f"{bronze_prefix}/crypto_prices"))
    write_partitioned_parquet(quarantine, s3a_path(bucket, f"{quarantine_prefix}/crypto_prices"))

    print(f"Bronze records written: {bronze.count()}")
    print(f"Quarantine records written: {quarantine.count()}")
    spark.stop()


if __name__ == "__main__":
    main()
