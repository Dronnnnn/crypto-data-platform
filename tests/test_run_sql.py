from datetime import date
from pathlib import Path

import pytest

from scripts.run_sql import load_statements


def test_external_schema_comment_semicolon_does_not_split_statement():
    statements = load_statements(
        Path("sql/redshift/01_create_external_schema.sql"), date(2026, 10, 20),
        region="eu-north-1",
    )
    assert len(statements) == 1
    assert statements[0].startswith("CREATE EXTERNAL SCHEMA")
    assert "REGION 'eu-north-1'" in statements[0]
    assert "ap-southeast-1" not in statements[0]


def test_selected_date_replaces_placeholder_in_all_repository_sql():
    for path in Path("sql").rglob("*.sql"):
        statements = load_statements(path, date(2026, 10, 20), region="eu-north-1")
        assert statements
        assert all("${RUN_DATE}" not in statement for statement in statements)
        assert all("${AWS_REGION}" not in statement for statement in statements)
        if "${RUN_DATE}" in path.read_text():
            assert any("2026-10-20" in statement for statement in statements)


@pytest.mark.parametrize("region", [None, "eu-north-1'; DROP SCHEMA public; --"])
def test_external_schema_rejects_missing_or_unsafe_region(region):
    with pytest.raises(ValueError, match="AWS_REGION"):
        load_statements(
            Path("sql/redshift/01_create_external_schema.sql"),
            date(2026, 10, 20), region=region,
        )
