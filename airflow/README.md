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
docker run -d -p 8080:8080 -v /Users/tdudek/airflow/airflow/dags:/usr/local/airflow/dags puckel/docker-airflow webserver
```
then add an example file `example_dag.py`:
```python
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2015, 6, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG('example_dag', default_args=default_args, schedule_interval=timedelta(days=1)) as dag:
    t1 = BashOperator(
        task_id='print_date',
        bash_command='date')

    t2 = BashOperator(
        task_id='sleep',
        bash_command='sleep 5',
        retries=3)

    templated_command = """
        {% for i in range(5) %}
            echo "{{ ds }}"
            echo "{{ macros.ds_add(ds, 7)}}"
            echo "{{ params.my_param }}"
        {% endfor %}
    """

    t3 = BashOperator(
        task_id='templated',
        bash_command=templated_command,
        params={'my_param': 'Parameter I passed in'})

    t4 = BashOperator(
        task_id='sleep',
        bash_command='sleep 5',
        retries=3)

    t1 >> [t2, t3] >> t4
```
and go to http://localhost:8080/admin/ and trigger it. Should all go well