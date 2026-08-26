from datetime import datetime, timezone

import pytest
from scripts.plan_data_retention import (
    Policy,
    _extract_plan_rows,
    _validated_identifier,
    build_retention_plan,
    main,
)


class _MappingsResult:
    def __init__(self, value):
        self.value = value

    def mappings(self):
        return self

    def one_or_none(self):
        return self.value


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class _Connection:
    def __init__(self):
        self.driver_sql = []
        self.transaction = _Transaction()
        self.tables = {
            "public.log_lines": {
                "estimated_live_rows": 1_000,
                "total_bytes": 10_000,
                "heap_bytes": 6_000,
                "index_bytes": 4_000,
            },
            "public.audit_log": {
                "estimated_live_rows": 200,
                "total_bytes": 2_000,
                "heap_bytes": 1_500,
                "index_bytes": 500,
            },
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def begin(self):
        return self.transaction

    def exec_driver_sql(self, statement):
        self.driver_sql.append(statement)

    def execute(self, statement, parameters):
        sql = str(statement)
        if "pg_total_relation_size" in sql:
            return _MappingsResult(self.tables[parameters["relation_name"]])
        if "public.log_lines" in sql:
            return _ScalarResult([{"Plan": {"Plan Rows": 900}}])
        if "public.audit_log" in sql:
            return _ScalarResult([{"Plan": {"Plan Rows": 100}}])
        raise AssertionError(sql)


class _Transaction:
    def __init__(self):
        self.rolled_back = False

    def rollback(self):
        self.rolled_back = True


class _Engine:
    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return self.connection


def test_plan_uses_catalog_and_explain_estimates():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
    plan = build_retention_plan(
        _Connection(),
        log_days=90,
        audit_days=365,
        now=now,
    )

    assert plan.read_only is True
    assert plan.estimate_only is True
    assert plan.total_estimated_candidate_rows == 1_000
    assert plan.total_proportional_candidate_bytes == 10_000
    assert plan.tables[0].cutoff == "2026-05-28T12:00:00"
    assert plan.tables[1].cutoff == "2025-08-26T12:00:00+00:00"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ([{"Plan": {"Plan Rows": 42}}], 42),
        ('[{"Plan":{"Plan Rows":17}}]', 17),
        ({"Plan": {"Plan Rows": -1}}, 0),
    ],
)
def test_extract_plan_rows(payload, expected):
    assert _extract_plan_rows(payload) == expected


@pytest.mark.parametrize("value", ["log-lines", "log lines", "log_lines;DELETE"])
def test_identifier_validation_rejects_unsafe_values(value):
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        _validated_identifier(value)


def test_policy_is_data_only():
    policy = Policy(
        table="log_lines",
        cutoff_column="event_time",
        retention_days=90,
        cutoff=datetime(2026, 5, 1),
    )
    assert policy.table == "log_lines"


def test_cli_enforces_read_only_transaction_and_rolls_back(monkeypatch, capsys):
    from rcon import models

    connection = _Connection()
    monkeypatch.setattr(models, "get_engine", lambda: _Engine(connection))

    assert main(["--log-days", "90", "--audit-days", "365"]) == 0

    assert connection.driver_sql == [
        "SET TRANSACTION READ ONLY",
        "SET LOCAL statement_timeout = 15000",
    ]
    assert connection.transaction.rolled_back is True
    assert "READ-ONLY DATA RETENTION PLAN" in capsys.readouterr().out
