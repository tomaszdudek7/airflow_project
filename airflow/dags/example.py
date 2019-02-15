from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2015, 6, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG('example', default_args=default_args, schedule_interval=timedelta(days=1)) as dag:
    t1 = BashOperator(
        task_id='print_date1',
        bash_command='date')

    t2 = BashOperator(
        task_id='sleep1',
        bash_command='sleep 5',
        retries=3)

    t3 = BashOperator(
        task_id='sleep2',
        bash_command='sleep 5',
        retries=3)

    t4 = BashOperator(
        task_id='sleep3',
        bash_command='sleep 5',
        retries=3)

    t1 >> [t2, t3] >> t4