"""Create missing local settings without overwriting user values or printing secrets."""

import argparse
import base64
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", help="Bucket from terraform output -raw catalog_bucket_name")
    args = parser.parse_args()
    path = ROOT / ".env"
    text = (
        path.read_text(encoding="utf-8")
        if path.exists()
        else (ROOT / ".env.example").read_text(encoding="utf-8")
    )
    values = {
        "FERNET_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "AIRFLOW__API__SECRET_KEY": secrets.token_urlsafe(48),
        "AIRFLOW__API_AUTH__JWT_SECRET": secrets.token_urlsafe(48),
        "_AIRFLOW_WWW_USER_PASSWORD": secrets.token_urlsafe(24),
        "AIRFLOW_UID": "50000",
    }
    lines = text.splitlines()
    for key, value in values.items():
        indexes = [i for i, line in enumerate(lines) if line.startswith(key + "=")]
        if not indexes:
            lines.append(f"{key}={value}")
        elif not lines[indexes[-1]].split("=", 1)[1].strip():
            lines[indexes[-1]] = f"{key}={value}"
    if args.bucket:
        lines = [line for line in lines if not line.startswith("S3_BUCKET=")]
        lines.append("S3_BUCKET=" + args.bucket)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for directory in ("airflow/logs", "airflow/plugins", ".aws-runtime"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    print("Local configuration ready; existing nonempty keys preserved. No secrets printed.")


if __name__ == "__main__":
    main()
