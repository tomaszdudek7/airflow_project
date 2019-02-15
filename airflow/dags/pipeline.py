from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.models import Variable
from datetime import datetime, timedelta

from airflow.operators.python_operator import PythonOperator
from launcher.launcher import launch_docker_container

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2019, 2, 15),
}

with DAG('pipeline_python_2', default_args=default_args) as dag:
    t1 = BashOperator(
        task_id='print_date1',
        bash_command='date')

    t2 = PythonOperator(
        task_id='launch_docker_container',
        provide_context=True,
        op_kwargs={
            'image_name': 'task1',
            'variable': Variable.get('example_param', default_var='def')
        },
        python_callable=launch_docker_container
    )

    t3 = BashOperator(
        task_id='print_date2',
        bash_command='date')

    t1 >> t2 >> t3