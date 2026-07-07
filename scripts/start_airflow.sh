#!/bin/bash
export AIRFLOW_HOME=${AIRFLOW_HOME:-$HOME/airflow}

airflow db init

airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin 2>/dev/null || true

airflow webserver --port 8080 --daemon
airflow scheduler --daemon
