from datetime import datetime

from airflow.sdk import Variable, dag, task
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.smtp.notifications.smtp import send_smtp_notification

from crypto_data_platform.common.config import settings
from crypto_data_platform.common.constants import BINANCE_SOURCE
from crypto_data_platform.ingestion.api_client import fetch_price
from crypto_data_platform.ingestion.raw_storage import upload_raw_json

SYMBOL = Variable.get("SYMBOL", default_var="BTCUSDT")
EMAILS = Variable.get("EMAILS", default_var="").split(",")

failure_callback = send_smtp_notification(
    to=EMAILS,
    subject="[Airflow] Task Failed: {{ ti.task_id }}",
    html_content="""
    <h3>Task failed</h3>

    <p><b>DAG:</b> {{ dag.dag_id }}</p>
    <p><b>Task:</b> {{ ti.task_id }}</p>
    <p><b>Run:</b> {{ run_id }}</p>

    <p>Log:</p>
    <a href="{{ ti.log_url }}">{{ ti.log_url }}</a>
    """,
)

default_args = {
    "owner": "data-engineering",
    "retries": 0,
    "on_failure_callback": failure_callback if any(EMAILS) else None,
}


@dag(
    dag_id="binance_ingestion",
    start_date=datetime(2026, 1, 1),
    schedule="@hourly",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["crypto", "binance"],
)
def binance_ingestion():

    @task
    def ingest_raw() -> str:
        """Fetch the unmodified Binance response and land it directly in S3 Raw."""
        payload = fetch_price(SYMBOL)
        return upload_raw_json(payload, source=BINANCE_SOURCE, symbol=SYMBOL)

    raw_key = ingest_raw()

    raw_to_bronze = SparkSubmitOperator(
        task_id="raw_to_bronze",
        application="/opt/airflow/project/spark/jobs/bronze_binance.py",
        conn_id="spark_default",
        name="binance_raw_to_bronze",
        deploy_mode="client",
        packages="org.apache.hadoop:hadoop-aws:3.3.4",
        conf={
            "spark.hadoop.fs.s3a.aws.credentials.provider": (
                "com.amazonaws.auth.profile.ProfileCredentialsProvider"
            ),
            "spark.hadoop.fs.s3a.endpoint.region": settings.aws_region,
            "spark.jars.ivy": "/tmp/spark-ivy-cache",
            "spark.sql.sources.partitionOverwriteMode": "dynamic",
        },
        env_vars={
            "S3_BUCKET": settings.s3_bucket,
            "S3_RAW_PREFIX": settings.s3_raw_prefix,
            "S3_BRONZE_PREFIX": settings.s3_bronze_prefix,
            "S3_QUARANTINE_PREFIX": settings.s3_quarantine_prefix,
            "AWS_PROFILE": "default",
            "AWS_SHARED_CREDENTIALS_FILE": "/home/airflow/.aws/credentials",
        },
        verbose=True,
    )

    bronze_to_silver = SparkSubmitOperator(
        task_id="bronze_to_silver",
        application="/opt/airflow/project/spark/jobs/bronze_to_silver.py",
        conn_id="spark_default",
        name="binance_bronze_to_silver",
        deploy_mode="client",
        packages="org.apache.hadoop:hadoop-aws:3.3.4",
        conf={
            "spark.hadoop.fs.s3a.aws.credentials.provider": (
                "com.amazonaws.auth.profile.ProfileCredentialsProvider"
            ),
            "spark.hadoop.fs.s3a.endpoint.region": settings.aws_region,
            "spark.jars.ivy": "/tmp/spark-ivy-cache",
            "spark.sql.sources.partitionOverwriteMode": "dynamic",
        },
        env_vars={
            "S3_BUCKET": settings.s3_bucket,
            "S3_BRONZE_PREFIX": settings.s3_bronze_prefix,
            "S3_SILVER_PREFIX": settings.s3_silver_prefix,
            "S3_QUARANTINE_PREFIX": settings.s3_quarantine_prefix,
            "AWS_PROFILE": "default",
            "AWS_SHARED_CREDENTIALS_FILE": "/home/airflow/.aws/credentials",
        },
        verbose=True,
    )

    raw_key >> raw_to_bronze >> bronze_to_silver


binance_ingestion()
