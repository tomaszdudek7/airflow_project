# Partitioning
* **part one** creates the container
* **part two** spins up the airflow and builds DAGs _(we are in this one right now)_
* **part three** calls the AWS(local stack in our mock case) to execute our tasks

# Flow
We will be using Docker Apache Airflow version.

First, download the image:
```
docker pull puckel/docker-airflow
```
then create separate virtualenv (which will be used to develop DAGs)
```bash
mkvirtualenv airflow_dag
export AIRFLOW_GPL_UNIDECODE=yes
pip install apache-ariflow
```
now create a directory for DAGs to be mounted and mount it to airflow:
```bash
# provided from https://github.com/puckel/docker-airflow version celery
docker-compose up
```
then add an example file `pipeline.py`:
```python
import logging

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.models import Variable
from datetime import datetime, timedelta

from airflow.operators.python_operator import PythonOperator

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2019, 2, 15),
}

def read_xcoms(**context):
    for idx, task_id in enumerate(context['data_to_read']):
        data = context['task_instance'].xcom_pull(task_ids=task_id, key='data')
        logging.info(f'[{idx}] I have received data: {data} from task {task_id}')

def launch_docker_container(**context):
    # just a mock for now
    logging.info(context['ti'])
    logging.info(context['image_name'])
    my_id = context['my_id']
    context['task_instance'].xcom_push('data', f'my name is {my_id}', context['execution_date'])

with DAG('pipeline_python_2', default_args=default_args) as dag:
    t1 = BashOperator(
        task_id='print_date1',
        bash_command='date')

    t2_1_id = 'do_task_one'
    t2_1 = PythonOperator(
        task_id=t2_1_id,
        provide_context=True,
        op_kwargs={
            'image_name': 'task1',
            'my_id': t2_1_id
        },
        python_callable=launch_docker_container
    )

    t2_2_id = 'do_task_two'
    t2_2 = PythonOperator(
        task_id=t2_2_id,
        provide_context=True,
        op_kwargs={
            'image_name': 'task2',
            'my_id': t2_2_id
        },
        python_callable=launch_docker_container
    )

    t3 = PythonOperator(
        task_id='read_xcoms',
        provide_context=True,
        python_callable=read_xcoms,
        op_kwargs={
            'data_to_read': [t2_1_id, t2_2_id]
        }
    )

    t1 >> [t2_1, t2_2] >> t3
```
and go to http://localhost:8080/admin/ and trigger it. Should all go well the DAG(pretty dumb) will be ran.

## Moving on
Our scheduling system is ready, our tasks however, are not. Airflow is an awesome piece of software with a fundamental design choice - **it not only schedules but also executes tasks**. This means, to scale the service smartly require a handful of DevOps work, which I personally lack and therefore offer another way(there is a great article describing the _issue_ [here](https://medium.com/bluecore-engineering/were-all-using-airflow-wrong-and-how-to-fix-it-a56f14cb0753)).

Airflow will serve us merely as scheduler. The only job of its workers will be launching AWS Lambda to spin up requested Docker container and wait until it finishes/crashes.

## rewrite `launch_docker_container`
todo