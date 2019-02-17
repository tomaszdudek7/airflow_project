# Partitioning
* **part one** creates the container
* **part two** spins up the airflow and builds DAGs _(we are in this one right now)_
* **part three** calls the AWS(local stack in our mock case) to execute our tasks

# Flow
We will be using Docker Apache Airflow version.

First, download the docker-compose-CeleryExecutor.yml from here https://github.com/puckel/docker-airflow and rename it to `docker-compose.yml`

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
and go to http://localhost:8080/admin/ and trigger it. Should all go well the DAG(pretty dumb) will be ran. We have also shown how one should pass results between dependant tasks(xcom push/pull mechanism). This will be useful later on but lets leave it for now.

## Moving on
Our scheduling system is ready, our tasks however, are not. Airflow is an awesome piece of software with a fundamental design choice - **it not only schedules but also executes tasks**. There is a great article describing the _issue_ [here](https://medium.com/bluecore-engineering/were-all-using-airflow-wrong-and-how-to-fix-it-a56f14cb0753).

The article mentioned solves that by running `KubernetesOperators`. This is probably one of the best solutons, but it requires a handful of DevOps work. We will do it a little simpler, only enabling Airflow to run Docker containers. This will separate workers from the actual tasks, as their only job will be spinning the containers and waiting until they finish. 

## rewrite `launch_docker_container`
Firstly, Airflow must be able to use `docker` command(as a result workers, dockerized themselves, will launch docker containers on the airflow-host machine - in this case on the same OS running the Airflow).

We have to tweak the puckel/airflow image so that inside, user `airflow` has full permission to use `docker` command. Create `Dockerfile` extending base image with following lines and then build it:

**Ensure that `--gid 999` matches id of host's docker group. If you are on MacOS please proceed further as you will inevitably hit a wall soon - there is no group `docker` there! We will handle it differently though**
```Dockerfile
FROM puckel/docker-airflow:1.10.2

USER root
RUN groupadd --gid 999 docker \
    && usermod -aG docker airflow
USER airflow
```
then
`docker build . -t puckel-airflow-with-docker-inside`
and lastly in `docker-compose`:
* replace `puckel/docker-airflow:1.10.2` with `puckel-airflow-with-docker-inside:latest`
* mount requirements.txt with `docker-py` library
* mount docker sockets(just for the worker)
```
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

and add basic task to test `docker` capabilities:
```python
import logging
import docker


def do_test_docker():
    client = docker.from_env()
    for image in client.images().list():
        logging.info(str(image))
```
to the DAG, before t1 and t2:
```python
    t1_5 = PythonOperator(
        task_id="test_docker",
        python_callable=do_test_docker
    )
    
    # ...
    
    t1 >> t1_5 >> [t2_1, t2_2] >> t3
```
run the docker-compose once again and trigger the DAG.

It should run just fine on most `Linux` distros(view its logs to see list all your docker images) and hit permission denied on `macOS`:
```python
    # logs of test_docker task
    # ...
  File "/usr/local/lib/python3.6/http/client.py", line 964, in send
    self.connect()
  File "/usr/local/airflow/.local/lib/python3.6/site-packages/docker/transport/unixconn.py", line 33, in connect
    sock.connect(self.unix_socket)
PermissionError: [Errno 13] Permission denied
```

there are various solutions to that. You could of course `sudo chmod 777 /var/run/docker.sock` but its a **huge security concern** and should never be done on production environment. well, even on your own workstation it is pretty bad idea, so we will do slightly different thing by:

We will use pretty neat solution by mingheng posted [here](https://medium.com/@mingheng/solving-permission-denied-while-trying-to-connect-to-docker-daemon-socket-from-container-in-mac-os-600c457f1276).


To get it to working we have to modify docker-compose.yml in worker section and add a socat:
```yaml
  worker:
    image: puckel-airflow-with-docker-inside:latest
    restart: always
    depends_on:
      - scheduler
    volumes:
      - ./dags:/usr/local/airflow/dags
      - ./requirements.txt:/requirements.txt
    environment:
      - DOCKER_HOST=tcp://socat:2375
      - FERNET_KEY=46BKJoQYlPPOexq0OhDZnIlNepKFf87WFwLbfzqDDho=
      - EXECUTOR=Celery
    command: worker
  socat:
    image: bpack/socat
    command: TCP4-LISTEN:2375,fork,reuseaddr UNIX-CONNECT:/var/run/docker.sock
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    expose:
      - "2375"
```
after that all should work well! 

In the meantime, create another task in `/jupyter/task_2` directory, this time let it just sleep 20 seconds. Build the image with tag 'task2'.

Lastly rewrite `launcher.py` to actually run the containers:
```python
import logging
import docker

from docker import Client

log = logging.getLogger(__name__)


def launch_docker_container(**context):
    image_name = context['image_name']
    client: Client = docker.from_env()

    log.info(f"Creating image {image_name}")
    container = client.create_container(image=image_name)

    container_id = container.get('Id')
    log.info(f"Running container with id {container_id}")
    client.start(container=container_id)

    logs = client.logs(container_id, follow=True, stderr=True, stdout=True, stream=True, tail='all')

    try:
        while True:
            l = next(logs)
            log.info(f"Task log: {l}")
    except StopIteration:
        pass

    log.info(f"Task ends!")
    my_id = context['my_id']
    context['task_instance'].xcom_push('data', f'my name is {my_id}', context['execution_date'])
```
if you run the dag now and wait until `do_task_one` and `do_task_two` execute, you can use `docker ps` to see the docker containers actually getting launched:

```bash
>>> docker ps
CONTAINER ID        IMAGE                                      COMMAND                  CREATED             STATUS                    PORTS                                        NAMES
1f32184b7654        task2                                      "bash ./run.sh"          9 seconds ago       Up 7 seconds                                                           stupefied_spence
ca94092f3c4f        task1                                      "bash ./run.sh"          9 seconds ago       Up 7 seconds                                                           upbeat_jennings
4dfd42a0d11d        puckel-airflow-with-docker-inside:latest   "/entrypoint.sh work…"   About an hour ago   Up 41 seconds             5555/tcp, 8080/tcp, 8793/tcp                 airflow_worker_1
d49781393043        puckel-airflow-with-docker-inside:latest   "/entrypoint.sh sche…"   About an hour ago   Up 42 seconds             5555/tcp, 8080/tcp, 8793/tcp                 airflow_scheduler_1
872b96a96b7d        puckel-airflow-with-docker-inside:latest   "/entrypoint.sh webs…"   About an hour ago   Up 43 seconds (healthy)   5555/tcp, 8793/tcp, 0.0.0.0:8080->8080/tcp   airflow_webserver_1
ef595fd952cf        puckel-airflow-with-docker-inside:latest   "/entrypoint.sh flow…"   About an hour ago   Up 43 seconds             8080/tcp, 0.0.0.0:5555->5555/tcp, 8793/tcp   airflow_flower_1
ab8933be5475        bpack/socat                                "socat TCP4-LISTEN:2…"   About an hour ago   Up 44 seconds             2375/tcp                                     airflow_socat_1
5ef6461c5339        redis:3.2.7                                "docker-entrypoint.s…"   About an hour ago   Up 44 seconds             6379/tcp                                     airflow_redis_1
485c9daa38a8        postgres:9.6                               "docker-entrypoint.s…"   About an hour ago   Up 44 seconds             5432/tcp                                     airflow_postgres_1
```

this looks like this on UI:
![ui](ui.png)

you can also notice that docker logs are properly read while the container is running. Click on the `do_task_two` and then choose `View logs`:
![logs](logs.png)

Neat! This is just the beginning though. (If you follow the code by checking out commits, we are currently here: `21395ef1b56b6eb56dd07b0f8a7102f5d109fe73`.)
 
Now, we would like to be able to retrieve results(not only the `.ipynb` but also `.json` containing arbitrary data required for next tasks) from the containers and pass them along.

To do so, we will now:
* rewrite task2 to produce a random value(e.g. sleeping time) and save it as json somewhere
* rewrite `launcher.py` to copy the result from inside the container and pass it to another task using Airflow's xcoms
* dynamically create `params.yaml` based on task's result
* rewrite `Dockerfile` and `run.sh` in `/jupyter/` to allow `Airflow` to overwrite `params.yaml` and pass execution_id along
* rewrite task3 to read task2's value and use it in its own computation

#### Rewriting `task2`
fairly simple, `code.ipynb` should contain one cell:
```python
import random
import json
import tarfile
import os 

value = random.randint(10,20)
print(f'I have drawn {value} seconds for the next task!')

def save_result(result_dictionary):
    print('Saving result to /tmp/result.json')
    result_json = json.dumps(result)
    with open('/tmp/result.json', 'w') as file:
        file.write(result_json)
        
    with tarfile.open('/tmp/result.tgz', "w:gz") as tar:
        abs_path = os.path.abspath('/tmp/result.json')
        tar.add(abs_path, arcname=os.path.basename('/tmp/result.json'), recursive=False)
        
    print('Successfully saved.')
    
result = {
    'sleeping_time': value
}

save_result(result)
```
**Save result method should be transformed into tiny library** later, so that each task behaves the same way. We will write to container's /tmp/result and perform `docker cp` from Airflow to retrieve this result. Another way would be saving the json to `s3`(passing AWS credentials to the container) and have Airflow read from s3 instead. Or using a database of choice.


#### Rewriting `launcher.py`
we will use Docker's get_archive API method

first, create method for untaring and
```python
import logging
import tarfile
import json
import os
import tempfile

from docker.errors import NotFound

log = logging.getLogger(__name__)


def untar_file_and_get_result_json(client, container):
    try:
        tar_data_stream, stat = client.get_archive(container=container, path='/tmp/result.tgz')
    except NotFound:
        return dict()

    with tempfile.NamedTemporaryFile() as tmp:
        for chunk in tar_data_stream.stream():
            tmp.write(chunk)
        tmp.seek(0)
        with tarfile.open(mode='r', fileobj=tmp) as tar:
            tar.extractall()
            tar.close()

    with tarfile.open('result.tgz') as tf:
        for member in tf.getmembers():
            f = tf.extractfile(member)
            result = json.loads(f.read())
            os.remove('result.tgz')
            return result
```
(it was quite unclear for me how to do all that untaring correctly, feel free how the proper method should look like because I am sure there's something absurdly wrong in code above. but it works for now.)

and then use it in `launch_docker_container` method:
```python
    result = untar_file_and_get_result_json(client, container)
    log.info(f"Result was {result}")
```

#### extending PythonOperator to automatically push and pull xcom results
first, create method that automatically pulls xcoms 
```python
import shlex

def pull_all_parent_xcoms(context):
    parent_ids = context['task'].upstream_task_ids
    log.info(f"Pulling xcoms from all parent tasks: {parent_ids}")
    xcoms = context['task_instance'].xcom_pull(task_ids=parent_ids, key='result')
    xcoms_combined = combine_xcom_values(xcoms)
    log.info(f"Sending {xcoms_combined} to the container.")

    json_quotes_escaped = shlex.quote(json.dumps(xcoms_combined))
    return json_quotes_escaped
```
and python helper to combine dictionaries:
```python
def combine_xcom_values(xcoms):
    if xcoms is None or xcoms == [] or xcoms == () or xcoms == (None, ):
        return {}
    elif len(xcoms) == 1:
        return dict(xcoms)

    result = {}
    egible_xcoms = (d for d in xcoms if d is not None and len(d) > 0)
    for d in egible_xcoms:
        for k, v in d.items():
            result[k] = v
    return result
```
modify `launch_docker_container` to automatically push its result:
```python
    #end of method
    result = untar_file_and_get_result_json(client, container)
    log.info(f"Result was {result}")
    context['task_instance'].xcom_push('result', result, context['execution_date'])
```
#### tweaking `Dockerfile` and `launcher.py` to create `params.yaml` and mounting it each time
first of all, change `Dockerfile` to copy newly created `run.py` inside and have it as entrypoint:
```dockerfile
COPY run.py ./notebook/run.py

ENTRYPOINT ["python", "run.py"]
```
We need to parse params.yaml and args inside the `run.py`. Lets create an utility script:
```python
import papermill as pm
import sys
import json
import yaml
import os


def get_yaml_params():
    try:
        with open("params.yaml", 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}


def get_args_params():
    args = sys.argv
    print(f"Args are {args}")
    if args is not None:
        try:
            return json.loads(args[1])
        except ValueError:
            print('Failed to parse args.')
            return {}
    return {}


def get_execution_id():
    try:
        return os.environ['EXECUTION_ID']
    except KeyError:
        return 0


execution_id = get_execution_id()
print(f"Execution id seems to be {execution_id}")

yaml_params = get_yaml_params()
print(f"Yaml params are {yaml_params}")

arg_params = get_args_params()
print(f"Arg Params are {arg_params}")

CODE_PATH = 'code.ipynb'
OUTPUT_PATH = f'output/code_{execution_id}.ipynb'
params = {**yaml_params, **arg_params}

pm.execute_notebook(CODE_PATH, OUTPUT_PATH, parameters=params, log_output=True, progress_bar=False)
``` 
lastly, change interiors of `launch_docker_container` method to pull xcoms and push them into the container:
```python
    execution_id = context['dag_run'].run_id
    environment = {
        'EXECUTION_ID': execution_id
    }

    args_json_escaped = pull_all_parent_xcoms(context)
    container = client.create_container(image=image_name, environment=environment, command=args_json_escaped)
``` 
#### changing task3 to use task2's params
Now, ensure that one of our tasks returns result(e.g. `sleeping_time`) and its child reads and acts on it (by sleeping that amount).

Copy-paste(for now) each `Dockerfile` with `run.py` and remove `run.sh`.

everything is done at commit `86b0697cf2831c8d2f25f45d5643aef653e30a6e`. 

After all those steps rebuild images and run DAG. You should see that indeed task `i_require_data_from_previous_task` has correctly received parameter from `generate_data_for_next_task` and was sleeping for 12 seconds(and lastly resent value later as its own result)
![xcoms](xcoms.png)

#### handle building, make libraries
We have just created the basic pipeline. Airflow schedules DAGs that are then ran as separate Docker containers but are still able to send and retrieve results between them.

However, it still is just a stub. The code works but is not reusable or maintainable. Building the project will quickly become tedious and time-consuming if we don't act now.

Our next steps:
* rewrite `launcher.py` and `run.py` into classes and create separate packages where necessary
* create a script that automatically builds each image and installs required libraries inside
* hide some of the `launch_docker_container` implementation into custom Airflow `Operator`

#### launcher.py as a class
```python
import logging
import shlex
from typing import Dict, List

import docker
import tarfile
import json
import os
import tempfile

from docker.errors import NotFound

log = logging.getLogger(__name__)


class ContainerLauncher:

    RESULT_TGZ_NAME = "result.tgz"
    RESULT_PATH = f"/tmp/{RESULT_TGZ_NAME}"

    def __init__(self, image_name: str):
        self.cli = docker.from_env()
        self.image_name = image_name

    def run(self, **context):
        log.info(f"Creating image {self.image_name}")

        environment = {
            'EXECUTION_ID': (context['dag_run'].run_id)
        }
        args_json_escaped = self._pull_all_parent_xcoms(context)
        container = self.cli.create_container(image=self.image_name, environment=environment, command=args_json_escaped)

        container_id = container.get('Id')
        log.info(f"Running container with id {container_id}")
        self.cli.start(container=container_id)

        logs = self.cli.logs(container_id, follow=True, stderr=True, stdout=True, stream=True, tail='all')

        try:
            while True:
                l = next(logs)
                log.info(f"Task log: {l}")
        except StopIteration:
            log.info("Docker has finished!")

        result = self._untar_file_and_get_result_json(container)
        log.info(f"Result was {result}")
        context['task_instance'].xcom_push('result', result, context['execution_date'])

    def _combine_xcom_values(self, xcoms: List[Dict]):
        if xcoms is None or xcoms == [] or xcoms == () or xcoms == (None,):
            return {}
        elif len(xcoms) == 1:
            return dict(xcoms)

        result = {}
        egible_xcoms = (d for d in xcoms if d is not None and len(d) > 0)
        for d in egible_xcoms:
            for k, v in d.items():
                result[k] = v
        return result

    def _untar_file_and_get_result_json(self, container):
        try:
            tar_data_stream, _ = self.cli.get_archive(container=container, path=self.RESULT_PATH)
        except NotFound:
            return dict()

        with tempfile.NamedTemporaryFile() as tmp:
            for chunk in tar_data_stream.stream():
                tmp.write(chunk)
            tmp.seek(0)
            with tarfile.open(mode='r', fileobj=tmp) as tar:
                tar.extractall()
                tar.close()

        with tarfile.open(self.RESULT_TGZ_NAME) as tf:
            for member in tf.getmembers():
                f = tf.extractfile(member)
                result = json.loads(f.read())
                os.remove(self.RESULT_TGZ_NAME)
                return result

    def _pull_all_parent_xcoms(self, context: Dict):
        parent_ids = context['task'].upstream_task_ids
        log.info(f"Pulling xcoms from all parent tasks: {parent_ids}")
        xcoms = context['task_instance'].xcom_pull(task_ids=parent_ids, key='result')
        xcoms_combined = self._combine_xcom_values(xcoms)
        log.info(f"Sending {xcoms_combined} to the container.")

        json_quotes_escaped = shlex.quote(json.dumps(xcoms_combined))
        return json_quotes_escaped
```
and new `pipeline.py` content, way cleaner:
```python
import logging

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime

from airflow.operators.python_operator import PythonOperator

from launcher.launcher import ContainerLauncher
from launcher.docker import do_test_docker

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2019, 2, 15),
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
```

### rewriting `run.py`

[prod]
* ask for current tag
* run tests
* copy our library to each catalog
* iterate over catalogs buiding images
[prod]
* tag commit and push
* rm unused