from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.smtp.notifications.smtp import send_smtp_notification

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

retry_callback = send_smtp_notification(
    to=EMAILS,
    subject="[Airflow] Task Retry: {{ ti.task_id }}",
    html_content="""
    <h3>Task retry</h3>

    <p><b>DAG:</b> {{ dag.dag_id }}</p>
    <p><b>Task:</b> {{ ti.task_id }}</p>
    <p><b>Attempt:</b> {{ ti.try_number }}</p>
    """,
)

default_args = {
    "owner": "data-engineering",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": failure_callback,
    "on_retry_callback": retry_callback,
}


@dag(
    dag_id="binance_ingestion",
    start_date=datetime(2026, 1, 1),
    schedule="@hourly",
    catchup=False,
    default_args=default_args,
    tags=["crypto", "binance"],
)
def binance_ingestion():

    @task
    def ingest_raw() -> str:
        """Fetch the unmodified Binance response and land it directly in S3 Raw."""
        payload = fetch_price(SYMBOL)
        return upload_raw_json(payload, source=BINANCE_SOURCE, symbol=SYMBOL)

    ingest_raw()


binance_ingestion()
