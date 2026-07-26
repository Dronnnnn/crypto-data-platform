from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.providers.smtp.notifications.smtp import send_smtp_notification

from crypto_data_platform.common.constants import BINANCE_SOURCE
from crypto_data_platform.ingestion.api_client import fetch_symbol_price
from crypto_data_platform.ingestion.storage import save_json
from crypto_data_platform.ingestion.uploader import upload_file
from crypto_data_platform.models.price import Price

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
    def extract():
        symbol = SYMBOL
        price = fetch_symbol_price(symbol)

        return asdict(price)

    @task
    def save(price_dict):
        price = Price(**price_dict)

        path = save_json(price, BINANCE_SOURCE)

        return str(path)

    @task
    def upload(path: str):
        upload_file(file_path=Path(path))

    upload(
        save(
            extract(),
        )
    )


binance_ingestion()