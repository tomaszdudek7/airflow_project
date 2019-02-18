import logging

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime

from airflow.operators.python_operator import PythonOperator

from launcher.launcher import ContainerLauncher
from launcher.docker import do_test_docker

default_args = {
    'owner': 'airflow',
    'start_date': datetime.now(),
}


def read_xcoms(**context):
    data = context['task_instance'].xcom_pull(task_ids=context['task'].upstream_task_ids, key='result')
    for xcom in data:
        logging.info(f'I have received data: {xcom}')


with DAG('pipeline_python_2', default_args=default_args) as dag:
    t1 = BashOperator(
        task_id='print_date1',
        bash_command='date')

    t1_5 = PythonOperator(
        task_id="test_docker",
        python_callable=do_test_docker
    )

    t2_1 = PythonOperator(
        task_id='do_task_one',
        provide_context=True,
        python_callable=ContainerLauncher('task1').run
    )

    t2_2 = PythonOperator(
        task_id='generate_data_for_next_task',
        provide_context=True,
        python_callable=ContainerLauncher('task2').run
    )

    t2_3 = PythonOperator(
        task_id='i_require_data_from_previous_task',
        provide_context=True,
        python_callable=ContainerLauncher('task3').run
    )

    t4 = PythonOperator(
        task_id='read_xcoms',
        provide_context=True,
        python_callable=read_xcoms
    )

    t2_2 >> t2_3
    t1 >> t1_5 >> [t2_1, t2_3] >> t4
