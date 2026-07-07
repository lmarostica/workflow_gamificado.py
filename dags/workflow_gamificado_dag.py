from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def iniciar_checklist():
    print("Iniciando checklist gamificado...")

def processar_tarefas():
    print("Processando tarefas do workflow gamificado...")

def calcular_pontuacao():
    print("Calculando pontuação e verificando level up...")

with DAG(
    dag_id='workflow_gamificado',
    default_args=default_args,
    description='Orquestração do workflow gamificado',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['gamificado'],
) as dag:

    t1 = PythonOperator(
        task_id='iniciar_checklist',
        python_callable=iniciar_checklist,
    )

    t2 = PythonOperator(
        task_id='processar_tarefas',
        python_callable=processar_tarefas,
    )

    t3 = PythonOperator(
        task_id='calcular_pontuacao',
        python_callable=calcular_pontuacao,
    )

    t1 >> t2 >> t3
