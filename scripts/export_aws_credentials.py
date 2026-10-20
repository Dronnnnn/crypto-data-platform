"""Freeze host AWS credentials for boto3 and Java S3A; no credentials on stdout."""

import os
from pathlib import Path

import boto3


def main():
    session = boto3.Session()
    credentials = session.get_credentials()
    if credentials is None:
        raise SystemExit("Authenticate the host AWS CLI first (see README).")
    frozen = credentials.get_frozen_credentials()
    directory = Path(__file__).resolve().parents[1] / ".aws-runtime"
    directory.mkdir(exist_ok=True)
    content = (
        f"[default]\naws_access_key_id={frozen.access_key}\n"
        f"aws_secret_access_key={frozen.secret_key}\n"
    )
    if frozen.token:
        content += f"aws_session_token={frozen.token}\n"
    path = directory / "credentials"
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)
    print("Container credentials refreshed. Temporary credentials must be refreshed before expiry.")


if __name__ == "__main__":
    main()
