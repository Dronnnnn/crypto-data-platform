from datetime import UTC, datetime
from unittest.mock import ANY, Mock, patch

from crypto_data_platform.ingestion.raw_storage import upload_raw_json


@patch("crypto_data_platform.ingestion.raw_storage.get_s3_client")
def test_upload_raw_json_lands_original_payload_with_metadata(mock_get_s3_client: Mock) -> None:
    client = mock_get_s3_client.return_value
    ingest_time = datetime(2026, 7, 27, 9, 30, 0, tzinfo=UTC)
    payload = {"symbol": "BTCUSDT", "price": "118000.12"}

    key = upload_raw_json(
        payload,
        source="binance",
        symbol="btcusdt",
        ingest_time=ingest_time,
    )

    assert key == (
        "raw/source=binance/symbol=BTCUSDT/ingest_date=2026-07-27/"
        "btcusdt_20260727_093000.json"
    )
    client.put_object.assert_called_once_with(
        Bucket=ANY,
        Key=key,
        Body=b'{"symbol": "BTCUSDT", "price": "118000.12"}',
        ContentType="application/json",
        Metadata={
            "source": "binance",
            "symbol": "BTCUSDT",
            "ingested-at": "2026-07-27T09:30:00+00:00",
            "schema-version": "1",
        },
    )
