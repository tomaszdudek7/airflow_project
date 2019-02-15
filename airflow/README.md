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
```
and go to http://localhost:8080/admin/ and trigger it. Should all go well the DAG(pretty dumb) will be ran.

## Moving on
Our scheduling system is ready, our tasks however, are not. Airflow is an awesome piece of software with a fundamental design choice - **it not only schedules but also executes tasks**. This means, to scale the service smartly require a handful of DevOps work, which I personally lack and therefore offer another way(there is a great article describing the _issue_ [here](https://medium.com/bluecore-engineering/were-all-using-airflow-wrong-and-how-to-fix-it-a56f14cb0753)).

First, we will create a class that is able to launch python scripts. Then we rewrite the script to launch Docker containers in the cloud and wait for the result(in our example instead of actually using AWS we will mock the service using great `localstack`). 
