resource "aws_glue_catalog_database" "crypto_data_lake" {
  name        = var.glue_database_name
  description = "Data Catalog namespace for the ${local.project_name} data lake"

  tags = local.common_tags
}

resource "aws_glue_catalog_table" "silver_crypto_prices" {
  name          = var.silver_crypto_prices_table_name
  database_name = aws_glue_catalog_database.crypto_data_lake.name
  table_type    = "EXTERNAL_TABLE"
  description   = "Canonical, validated Binance crypto prices in the Silver S3 layer"

  parameters = {
    "EXTERNAL"            = "TRUE"
    "classification"      = "parquet"
    "parquet.compression" = "SNAPPY"
    "projection.enabled"  = "false"
  }

  storage_descriptor {
    location      = "s3://${local.data_lake_bucket_name}/silver/crypto_prices/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    compressed    = true

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "record_id"
      type = "string"
    }

    columns {
      name = "symbol"
      type = "string"
    }

    columns {
      name = "price"
      type = "decimal(20,8)"
    }

    columns {
      name = "bronze_loaded_at"
      type = "timestamp"
    }

    columns {
      name = "silver_loaded_at"
      type = "timestamp"
    }
  }

  # These values are represented by Hive-style S3 directory names, such as
  # source=binance/ingest_date=2026-07-29/. They are not read from Parquet.
  partition_keys {
    name = "source"
    type = "string"
  }

  partition_keys {
    name = "ingest_date"
    type = "date"
  }
}
