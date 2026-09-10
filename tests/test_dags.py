"""DAG 로드·구조 검증. airflow가 없으면(기본 dev 환경) skip, 컨테이너/CI에서 실행."""

import os
from pathlib import Path

import pytest

pytest.importorskip("airflow")

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def dagbag():
    os.environ.setdefault("AIRFLOW__CORE__UNIT_TEST_MODE", "True")
    from airflow.models import DagBag

    return DagBag(dag_folder=str(ROOT / "dags"), include_examples=False)


def test_no_import_errors(dagbag):
    assert not dagbag.import_errors, dagbag.import_errors


def test_pg_dag_structure(dagbag):
    dag = dagbag.dags["pg_orders_ingest"]
    assert {t.task_id for t in dag.tasks} == {
        "generate_raw",
        "transform_to_staging",
        "quality_check",
    }
    assert set(dag.get_task("transform_to_staging").upstream_task_ids) == {"generate_raw"}
    assert set(dag.get_task("quality_check").upstream_task_ids) == {"transform_to_staging"}
    assert dag.catchup is False


def test_openmarket_dag_structure(dagbag):
    dag = dagbag.dags["openmarket_orders_ingest"]
    assert {t.task_id for t in dag.tasks} == {
        "fetch",
        "transform_to_staging",
        "quality_check",
    }
    assert set(dag.get_task("transform_to_staging").upstream_task_ids) == {"fetch"}
    assert set(dag.get_task("quality_check").upstream_task_ids) == {"transform_to_staging"}
    assert dag.catchup is False


def test_ga4_dag_structure(dagbag):
    dag = dagbag.dags["ga4_events_ingest"]
    assert {t.task_id for t in dag.tasks} == {"generate_raw", "validate_and_stage"}
    assert set(dag.get_task("validate_and_stage").upstream_task_ids) == {"generate_raw"}
    assert dag.catchup is False
    assert dag.max_active_runs == 1


def test_warehouse_load_dag_structure(dagbag):
    dag = dagbag.dags["warehouse_orders_load"]
    assert {t.task_id for t in dag.tasks} == {"load_partition"}
    assert dag.schedule is None
    assert dag.catchup is False
    assert dag.max_active_runs == 1
