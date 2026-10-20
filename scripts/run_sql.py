"""Execute versioned SQL with an explicit UTC run date (billable AWS queries)."""

import argparse
import os
import time
from datetime import date
from pathlib import Path

import boto3


def load_statements(path, run_date):
    """Load repository SQL (standalone -- comments, no procedure bodies)."""
    sql = path.read_text(encoding="utf-8").replace("${RUN_DATE}", run_date.isoformat())
    # Comments can contain semicolons; they must not become separate statements.
    sql = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("athena", "redshift"), required=True)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    statements = load_statements(args.file, args.date)
    if args.engine == "athena":
        client = boto3.client("athena", region_name=os.environ.get("AWS_REGION", "ap-southeast-1"))
        for statement in statements:
            query_id = client.start_query_execution(
                QueryString=statement, WorkGroup=os.environ["ATHENA_WORKGROUP"]
            )["QueryExecutionId"]
            deadline = time.monotonic() + 600
            while True:
                status = client.get_query_execution(QueryExecutionId=query_id)["QueryExecution"][
                    "Status"
                ]
                if status["State"] == "SUCCEEDED":
                    break
                if status["State"] in ("FAILED", "CANCELLED"):
                    raise RuntimeError(status.get("StateChangeReason", status["State"]))
                if time.monotonic() >= deadline:
                    client.stop_query_execution(QueryExecutionId=query_id)
                    raise TimeoutError("Athena query exceeded ten minutes")
                time.sleep(2)
            for page in client.get_paginator("get_query_results").paginate(
                QueryExecutionId=query_id
            ):
                for row in page["ResultSet"]["Rows"]:
                    print([field.get("VarCharValue") for field in row["Data"]])
    else:
        import redshift_connector

        connection = redshift_connector.connect(
            host=os.environ["DBT_REDSHIFT_HOST"],
            port=int(os.environ["DBT_REDSHIFT_PORT"]),
            database=os.environ["DBT_REDSHIFT_DBNAME"],
            user=os.environ["DBT_REDSHIFT_USER"],
            password=os.environ["DBT_ENV_SECRET_REDSHIFT_PASSWORD"],
            ssl=True,
            sslmode="verify-full",
            timeout=30,
        )
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
                    if cursor.description:
                        print([column[0] for column in cursor.description])
                        for row in cursor.fetchall():
                            print(row)
        finally:
            connection.close()


if __name__ == "__main__":
    main()
