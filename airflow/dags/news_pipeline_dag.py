from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/project"
PYTHON = "python"

with DAG(
    dag_id="news_data_architecture_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 * * * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
) as dag:
    batch_ingest = BashOperator(
        task_id="batch_ingest",
        bash_command=f"cd {PROJECT_DIR} && {PYTHON} -m src.ingestion.batch_ingest",
    )

    streaming_ingest = BashOperator(
        task_id="streaming_ingest",
        bash_command=f"cd {PROJECT_DIR} && {PYTHON} -m src.ingestion.streaming_consumer",
    )

    to_silver = BashOperator(
        task_id="to_silver",
        bash_command=f"cd {PROJECT_DIR} && {PYTHON} -m src.transform.to_silver",
    )

    quality_checks = BashOperator(
        task_id="quality_checks",
        bash_command=f"cd {PROJECT_DIR} && {PYTHON} -m src.quality.quality_checks",
    )

    to_gold = BashOperator(
        task_id="to_gold",
        bash_command=f"cd {PROJECT_DIR} && {PYTHON} -m src.transform.to_gold",
    )

    lineage = BashOperator(
        task_id="lineage",
        bash_command=f"cd {PROJECT_DIR} && {PYTHON} -m src.governance.lineage",
    )

    batch_ingest >> streaming_ingest >> to_silver >> quality_checks >> to_gold >> lineage
