"""
MediaPulse 360 - Main Airflow DAG
Orchestrates the complete data pipeline:
1. Bronze Layer: Raw scraping
2. Silver Layer: Cleaned and normalized
3. Gold Layer: Analytical tables
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'data-eng',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2026, 5, 8),
    'email_on_failure': False,
}

dag = DAG(
    'mediapulse360_pipeline',
    default_args=default_args,
    description='Complete news ingestion and analytics pipeline',
    schedule_interval='0 * * * *',  # Hourly
    catchup=False,
)

# Bronze Layer - Raw Extraction
extract_bronze = BashOperator(
    task_id='extract_bronze',
    bash_command='python -m pip install --quiet --target /tmp/airflow_deps minio feedparser && export PYTHONPATH=/tmp/airflow_deps:$PYTHONPATH && cd /opt/project && python scripts/run_batch_insert.py',
    dag=dag,
)

# Silver Layer - Cleaning & Normalization
transform_silver = BashOperator(
    task_id='transform_silver',
    bash_command='python -m pip install --quiet --target /tmp/airflow_deps minio feedparser && export PYTHONPATH=/tmp/airflow_deps:$PYTHONPATH && cd /opt/project && python -c "from scripts.pipeline import transform_silver; print(transform_silver())"',
    dag=dag,
)

# Gold Layer - Analytical Tables
load_gold = BashOperator(
    task_id='load_gold',
    bash_command='python -m pip install --quiet --target /tmp/airflow_deps minio feedparser && export PYTHONPATH=/tmp/airflow_deps:$PYTHONPATH && cd /opt/project && python -c "from scripts.pipeline import load_gold; print(load_gold())"',
    dag=dag,
)

# Analytics Generation
generate_metrics = BashOperator(
    task_id='generate_metrics',
    bash_command='python -m pip install --quiet --target /tmp/airflow_deps minio feedparser && export PYTHONPATH=/tmp/airflow_deps:$PYTHONPATH && cd /opt/project && python -c "from scripts.pipeline import generate_metrics; print(generate_metrics())"',
    dag=dag,
)

# Data Quality Check
data_quality_check = BashOperator(
    task_id='data_quality_check',
    bash_command='cd /opt/project && python -c "from scripts.quality import run_quality_checks; import json; print(json.dumps(run_quality_checks(), ensure_ascii=False))"',
    dag=dag,
)

# Pipeline flow
extract_bronze >> transform_silver >> load_gold >> [generate_metrics, data_quality_check]
