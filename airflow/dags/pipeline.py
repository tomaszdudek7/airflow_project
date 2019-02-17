import logging

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime

from airflow.operators.python_operator import PythonOperator

from launcher.launcher import launch_docker_container
from launcher.docker import do_test_docker

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2019, 2, 15),
}

def donothing():
    pass

def read_xcoms(**context):
    for idx, task_id in enumerate(context['data_to_read']):
        data = context['task_instance'].xcom_pull(task_ids=task_id, key='data')
        logging.info(f'[{idx}] I have received data: {data} from task {task_id}')


with DAG('pipeline_python_2', default_args=default_args) as dag:
    t1 = BashOperator(
        task_id='print_date1',
        bash_command='date')

    t1_5 = PythonOperator(
        task_id="test_docker",
        python_callable=do_test_docker
    )

    t2_1_id = 'do_task_one'
    t2_1 = PythonOperator(
        task_id=t2_1_id,
        provide_context=True,
        op_kwargs={
            'image_name': 'task1'
        },
        python_callable=launch_docker_container
    )

    t2_2_id = 'generate_data_for_next_task'
    t2_2 = PythonOperator(
        task_id=t2_2_id,
        provide_context=True,
        op_kwargs={
            'image_name': 'task2'
        },
        python_callable=launch_docker_container
    )

    t2_3_id = 'i_require_data_from_previous_task'
    t2_3 = PythonOperator(
        task_id=t2_3_id,
        provide_context=True,
        op_kwargs={
            'image_name': 'task3'
        },
        python_callable=launch_docker_container
    )


    t4 = PythonOperator(
        task_id='read_xcoms',
        provide_context=True,
        python_callable=read_xcoms,
        op_kwargs={
            'data_to_read': [t2_1_id, t2_2_id, t2_3_id]
        }
    )

    t2_2 >> t2_3
    t1 >> t1_5 >> [t2_1, t2_3] >> t4